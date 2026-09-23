# -*- coding: utf-8 -*-
"""cbb_quarantine.py — CBB B6 隔离区管理器（本体版 v2）

保留（v1.0）：五类分组请你确认报告 + append-only 裁决通道（终态留档不删）+
登记幂等（item_id 内容哈希）+ 报告确定性（无时钟字段）。
吸收（U-A17 §3，三子类为用户裁决案）：
  - **quarantine 三子类**：contradiction_pending（矛盾待裁决）/
    extrapolation_unverified（外推待证）/ overdue_omission（超期遗漏）——
    五分组保留为细粒度入口（gate1/anchor 原因码），三子类为分流层（路由与统计）；
  - **urgency 公式**（webnovel-writer status_reporter.py:507-546 转译）：
    urgency=(已过章节/目标回收章节)×层级权重——核心 3.0（必须回收否则剧情崩塌）/
    支线 2.0（否则显得作者健忘）/装饰 1.0（可回收可不回收仅增加真实感）；
    状态 🔴已超期（current≥target）/🟡警告（进度比≥0.8，CBB 定约）/
    🟢正常；top_urgent 只取前 N 条（写前注入 urgent_loops 前 3 条同思想）；
  - **🔴超期态（遗漏告警）**（danghuangshang）：超期项在报告中置顶且带 🔴；
  - **`[?]` 内联标记+行号汇总报告**（graphify-novel）：字段级轻量隔离——
    scan_inline_unsure 扫描 `[?]` 标记按行号汇总，供人工裁决（与记录级隔离互补）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date as _date
from pathlib import Path

GROUPS = ("unresolved_time", "missing_anchor", "ambiguous_reference",
          "entity_unalignable", "low_confidence")
SUBCLASSES = ("contradiction_pending", "extrapolation_unverified", "overdue_omission")
SUBCLASS_CN = {"contradiction_pending": "矛盾待裁决",
               "extrapolation_unverified": "外推待证",
               "overdue_omission": "超期遗漏"}
# 五分组 → 三子类默认分流（gate1 已带子类时以其为准）
GROUP_TO_SUBCLASS = {
    "unresolved_time": "extrapolation_unverified",
    "missing_anchor": "extrapolation_unverified",
    "ambiguous_reference": "extrapolation_unverified",
    "entity_unalignable": "contradiction_pending",  # 实体不可归一=潜在同名冲突，须裁决
    "low_confidence": "extrapolation_unverified",
}
DECISIONS = ("confirmed", "rejected")  # Part V：quarantine ──人工裁决──→ confirmed|rejected（终态）

# urgency 层级权重（webnovel-writer config.py:305-307 语义转译）
URGENCY_TIERS = {"core": 3.0, "subplot": 2.0, "decorative": 1.0}
URGENCY_WARNING_RATIO = 0.8  # 🟡 警戒线：进度比 ≥0.8（CBB 定约：🔴=current≥target）
TOP_URGENT_N = 3             # 写前注入只取前 3 条（urgent_loops 同思想）


def _today() -> str:
    """今日日期（审计日期位用；与故事伪锚点禁墙钟无关——那是故事时间，这是记账时间）。"""
    return _date.today().isoformat()


def _item_id(group: str, record_id: str, detail: str) -> str:
    h = hashlib.sha256(f"{group}|{record_id}|{detail}".encode("utf-8")).hexdigest()[:12]
    return f"q-{h}"


def urgency_of(item: dict, current_chapter: int) -> float | None:
    """urgency=(已过章节/目标回收章节)×层级权重。
    需 item 带 tier/planted_chapter/target_chapter 与 current_chapter；否则 None。"""
    tier = item.get("tier")
    planted, target = item.get("planted_chapter"), item.get("target_chapter")
    if tier not in URGENCY_TIERS or not all(isinstance(x, int) for x in (planted, target, current_chapter)):
        return None
    span = target - planted
    if span <= 0:
        return None  # 目标不晚于埋设：期限数据非法，不参与排序（交给 gate1 时序域）
    ratio = (current_chapter - planted) / span
    return ratio * URGENCY_TIERS[tier]


def urgency_status(item: dict, current_chapter: int) -> str | None:
    """🔴已超期（current≥target，到点即超期——与 anchor.countdowns_due 同口径）/
    🟡警告（进度比≥0.8）/🟢正常；非期限项返回 None。"""
    target = item.get("target_chapter")
    if not (isinstance(target, int) and isinstance(current_chapter, int)):
        return None
    if current_chapter >= target:
        return "🔴"
    u = urgency_of(item, current_chapter)
    if u is not None and u / URGENCY_TIERS[item["tier"]] >= URGENCY_WARNING_RATIO:
        return "🟡"
    return "🟢"


def scan_inline_unsure(text: str) -> list[dict]:
    """`[?]` 内联标记扫描（graphify-novel 字段级轻量隔离）：返回 [{line, excerpt}]。
    行号=物理行 1-based；标记不删不改（P-003：半角方括号是标记不可删）。"""
    hits = []
    for i, ln in enumerate((text or "").split("\n"), 1):
        if "[?]" in ln:
            hits.append({"line": i,
                         "excerpt": ln.strip()[:60]})
    return hits


def inline_report(scans: dict[str, list[dict]]) -> str:
    """`[?]` 行号汇总报告：{文件名: scan_inline_unsure 结果} → markdown。"""
    total = sum(len(v) for v in scans.values())
    lines = [f"## `[?]` 内联不确定标记汇总（{total} 处，待人工裁决）", ""]
    for fname, hits in sorted(scans.items()):
        for h in hits:
            lines.append(f"- {fname} — line {h['line']}: {h['excerpt']}")
    if total == 0:
        lines.append("- （无）")
    return "\n".join(lines)


class QuarantineZone:
    """隔离区：register / adjudicate / report。同一 root 可多实例（每次读盘对账）。"""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.items_path = self.root / "items.jsonl"
        self.adj_path = self.root / "adjudications.jsonl"

    # ---- 落盘基元（append-only） ----
    def _append(self, path: Path, obj: dict) -> None:
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False, sort_keys=True) + "\n")

    def _load(self, path: Path) -> list[dict]:
        if not path.exists():
            return []
        return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]

    # ---- 登记 ----
    def register(self, group: str, detail: str, record_id: str = None,
                 source: str = None, blocks: list | None = None,
                 subclass: str = None, tier: str = None,
                 planted_chapter: int = None, target_chapter: int = None,
                 at: str = None):
        """登记隔离条目。幂等：同 (group,record_id,detail) 已在册 → (item_id, False)。
        subclass 三子类：显式传入（gate1 携带）或按五分组默认分流；
        tier/planted/target 为期限项（超期遗漏类）参数，供 urgency 计算。
        at=登记日期（v2.1 裁决②附带，2026-09-22）：裁决滞后计算依赖此位；
        缺省=今日；item_id 不含 at（幂等键不变，旧库兼容）。"""
        if group not in GROUPS:
            raise ValueError(f"非法隔离分组 {group!r}，合法={GROUPS}")
        if tier is not None and tier not in URGENCY_TIERS:
            raise ValueError(f"非法层级 {tier!r}，合法={tuple(URGENCY_TIERS)}")
        sub = subclass or GROUP_TO_SUBCLASS[group]
        if sub not in SUBCLASSES:
            raise ValueError(f"非法子类 {sub!r}，合法={SUBCLASSES}")
        if tier is not None:  # 期限项自动归超期遗漏子类（除非显式指定）
            sub = subclass or "overdue_omission"
        item_id = _item_id(group, record_id or "", detail)
        if any(it["item_id"] == item_id for it in self._load(self.items_path)):
            return item_id, False
        item = {
            "item_id": item_id,
            "group": group,
            "subclass": sub,
            "source": source,
            "record_id": record_id,
            "detail": detail,
            "blocks_downstream": sorted(set(blocks or [])),
            "status": "pending",
            "at": at or _today(),  # v2.1：登记日期位（滞后计算依赖；历史件无此位）
        }
        if tier is not None:
            item.update(tier=tier, planted_chapter=planted_chapter,
                        target_chapter=target_chapter)
        self._append(self.items_path, item)
        return item_id, True

    # ---- 裁决（人工通道） ----
    def adjudicate(self, item_id: str, decision: str, note: str = "", by: str = "human",
                   at: str = None) -> dict:
        """人工裁决：confirmed | rejected。终态留档不删；同条不可二次裁决。
        at=裁决日期（v2.1 裁决②附带）：触发器 D 的"裁决滞后"由此可算；
        缺省=今日；历史补录只许填实际日期，不得编造。"""
        if decision not in DECISIONS:
            raise ValueError(f"非法裁决 {decision!r}，合法={DECISIONS}")
        items = self._load(self.items_path)
        if not any(it["item_id"] == item_id for it in items):
            raise KeyError(f"隔离条目不存在: {item_id}")
        if any(a["item_id"] == item_id for a in self._load(self.adj_path)):
            raise ValueError(f"条目已裁决（终态不可再裁）: {item_id}")
        adj = {"item_id": item_id, "decision": decision, "note": note, "by": by,
               "at": at or _today()}  # v2.1：裁决日期位
        self._append(self.adj_path, adj)
        return adj

    # ---- 视图 ----
    def pending(self) -> list[dict]:
        done = {a["item_id"] for a in self._load(self.adj_path)}
        return [it for it in self._load(self.items_path) if it["item_id"] not in done]

    def adjudicated(self) -> list[dict]:
        items = {it["item_id"]: it for it in self._load(self.items_path)}
        out = []
        for a in self._load(self.adj_path):
            merged = dict(a)
            merged["group"] = items.get(a["item_id"], {}).get("group")
            out.append(merged)
        return out

    def status_report(self, today: str = None) -> dict:
        """状态对账（v2.1 裁决②附带，2026-09-22）：未裁/已裁两数可分＋裁决滞后可算。
        滞后口径（T-5：标签与量对账）＝今日 − 最早未裁条目的登记日（仅计带 at 位的条目）；
        历史件无 at 位不计入，并在口径中如实披露计入比例。"""
        from datetime import date as _date
        t = today or _today().isoformat()
        pend, adj = self.pending(), self.adjudicated()
        dated = [it["at"] for it in pend if it.get("at")]
        if dated:
            d0 = min(dated)
            lag = (_date.fromisoformat(t) - _date.fromisoformat(d0)).days
            lag_out = {"days": lag, "since": d0,
                       "口径": f"按最早未裁登记日计；带日期位 {len(dated)}/{len(pend)} 条"}
        else:
            lag_out = {"days": None, "since": None,
                       "口径": "UNKNOWN（在库条目均无日期位——历史件，不得编造）"}
        return {"pending_total": len(pend), "adjudicated_total": len(adj),
                "裁决滞后": lag_out,
                "adjudicated_with_date": sum(1 for a in adj if a.get("at"))}

    def by_group(self) -> dict:
        counts = {g: 0 for g in GROUPS}
        for it in self.pending():
            counts[it["group"]] = counts.get(it["group"], 0) + 1
        return counts

    def by_subclass(self) -> dict:
        counts = {s: 0 for s in SUBCLASSES}
        for it in self.pending():
            counts[it.get("subclass")] = counts.get(it.get("subclass"), 0) + 1
        return counts

    def top_urgent(self, current_chapter: int, n: int = TOP_URGENT_N) -> list[dict]:
        """urgency 排序前 N 条（只取前 3 条纪律）：🔴 超期优先（遗漏告警置顶），
        同 urgency 按 item_id 确定性排序。"""
        scored = []
        for it in self.pending():
            u = urgency_of(it, current_chapter)
            if u is None:
                continue
            scored.append((u, it["item_id"], it))
        scored.sort(key=lambda t: (-t[0], t[1]))
        return [it for _, _, it in scored[:n]]

    # ---- 报告（第一产出） ----
    def report_markdown(self, current_chapter: int | None = None) -> str:
        pending = sorted(self.pending(),
                         key=lambda it: (-len(it["blocks_downstream"]), it["item_id"]))
        counts = self.by_group()
        subs = self.by_subclass()
        lines = [
            "# 隔离区报告（请你确认清单）",
            "",
            f"> cbb-quarantine v2 ｜ 待裁决 {len(pending)} 项 ｜ 已裁决 {len(self.adjudicated())} 项",
            "> 纪律：显式隔离，绝不静默丢弃（B6）；以下条目按**阻塞下游计数降序**排列。",
            "",
            "## 三子类分流统计",
        ]
        for s in SUBCLASSES:
            lines.append(f"- **{SUBCLASS_CN[s]}**（{s}）: {subs.get(s, 0)} 项")
        lines += ["", "## 分组统计"]
        for g in GROUPS:
            if counts.get(g):
                lines.append(f"- **{g}**: {counts[g]} 项")
        if not any(counts.values()):
            lines.append("- （空）")

        if current_chapter is not None:
            lines += ["", f"## 🔴 超期与 urgency 排序（当前章={current_chapter}，只列前 {TOP_URGENT_N} 条）"]
            top = self.top_urgent(current_chapter)
            if top:
                for it in top:
                    u = urgency_of(it, current_chapter)
                    st = urgency_status(it, current_chapter)
                    lines.append(f"- {st} `{it['item_id']}` [{it.get('tier')}] "
                                 f"urgency={u:.2f}（第{it.get('planted_chapter')}章埋设→"
                                 f"目标第{it.get('target_chapter')}章）：{it['detail']}")
            else:
                lines.append("- （无期限项）")

        lines += ["", "## 待裁决清单（按阻塞下游计数降序）"]
        for i, it in enumerate(pending, 1):
            lines += [
                "",
                f"### {i}. [{it['group']}→{SUBCLASS_CN.get(it.get('subclass'), it.get('subclass'))}] "
                f"`{it['item_id']}`（阻塞下游 {len(it['blocks_downstream'])} 项）",
                f"- 详情：{it['detail']}",
                f"- 来源：{it['source'] or '（未注明）'} ｜ 关联记录：{it['record_id'] or '（无）'}",
            ]
            if it["blocks_downstream"]:
                lines.append(f"- 阻塞：{', '.join(it['blocks_downstream'])}")
            lines.append("- **请你确认**：该条应判 confirmed 入库，还是 rejected 作废？")
        adj = self.adjudicated()
        lines += ["", "## 已裁决（终态留档，不删）"]
        if adj:
            for a in adj:
                lines.append(f"- `{a['item_id']}` → **{a['decision']}**（{a['by']}）：{a['note'] or '无注记'}")
        else:
            lines.append("- （无）")
        lines.append("")
        return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="CBB B6 隔离区（本体版 v2 · 三子类+urgency）")
    ap.add_argument("--root", required=True, help="隔离区目录")
    ap.add_argument("--register", nargs=4, metavar=("GROUP", "DETAIL", "RECORD_ID", "SOURCE"),
                    help="登记一条隔离条目（RECORD_ID/SOURCE 可填 -）")
    ap.add_argument("--adjudicate", nargs=3, metavar=("ITEM_ID", "DECISION", "NOTE"),
                    help="人工裁决（confirmed|rejected）")
    ap.add_argument("--current-chapter", type=int, default=None,
                    help="当前推进章号（urgency 排序/超期态判定）")
    ap.add_argument("--report", action="store_true", help="打印报告 markdown")
    args = ap.parse_args(argv)

    zone = QuarantineZone(Path(args.root))
    if args.register:
        group, detail, rid, source = args.register
        iid, created = zone.register(group, detail,
                                     record_id=None if rid == "-" else rid,
                                     source=None if source == "-" else source)
        print(f"[quarantine] item={iid} created={created} subclass={GROUP_TO_SUBCLASS[group]}")
    if args.adjudicate:
        iid, decision, note = args.adjudicate
        zone.adjudicate(iid, decision, note)
        print(f"[quarantine] adjudicated {iid} -> {decision}")
    if args.report:
        print(zone.report_markdown(current_chapter=args.current_chapter))
    if not (args.register or args.adjudicate or args.report):
        print(f"[quarantine] pending={len(zone.pending())} adjudicated={len(zone.adjudicated())} "
              f"by_subclass={zone.by_subclass()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
