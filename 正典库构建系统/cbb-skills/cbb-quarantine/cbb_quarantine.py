# -*- coding: utf-8 -*-
"""cbb_quarantine.py — CBB B6 隔离区管理器（M1 骨架）

五类分组 + 阻塞下游计数排序 + "请你确认"报告 + 人工裁决通道（终态留档不删）。
落盘 append-only（items.jsonl / adjudications.jsonl）；登记幂等（item_id 内容哈希）；
报告确定性（无时钟字段）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

GROUPS = ("unresolved_time", "missing_anchor", "ambiguous_reference",
          "entity_unalignable", "low_confidence")
DECISIONS = ("confirmed", "rejected")  # Part V：quarantine ──人工裁决──→ confirmed|rejected（终态）
THREE_STATE_SINKS = ("confirmed", "provisional", "quarantine")


def _item_id(group: str, record_id: str, detail: str) -> str:
    h = hashlib.sha256(f"{group}|{record_id}|{detail}".encode("utf-8")).hexdigest()[:12]
    return f"q-{h}"


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
                 source: str = None, blocks: list | None = None):
        """登记隔离条目。幂等：同 (group,record_id,detail) 已在册 → (item_id, False)。"""
        if group not in GROUPS:
            raise ValueError(f"非法隔离分组 {group!r}，合法={GROUPS}")
        item_id = _item_id(group, record_id or "", detail)
        if any(it["item_id"] == item_id for it in self._load(self.items_path)):
            return item_id, False
        item = {
            "item_id": item_id,
            "group": group,
            "source": source,
            "record_id": record_id,
            "detail": detail,
            "blocks_downstream": sorted(set(blocks or [])),
            "status": "pending",
        }
        self._append(self.items_path, item)
        return item_id, True

    # ---- 裁决（人工通道） ----
    def adjudicate(self, item_id: str, decision: str, note: str = "", by: str = "human") -> dict:
        """人工裁决：confirmed | rejected。终态留档不删；同条不可二次裁决。"""
        if decision not in DECISIONS:
            raise ValueError(f"非法裁决 {decision!r}，合法={DECISIONS}")
        items = self._load(self.items_path)
        if not any(it["item_id"] == item_id for it in items):
            raise KeyError(f"隔离条目不存在: {item_id}")
        if any(a["item_id"] == item_id for a in self._load(self.adj_path)):
            raise ValueError(f"条目已裁决（终态不可再裁）: {item_id}")
        adj = {"item_id": item_id, "decision": decision, "note": note, "by": by}
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

    def by_group(self) -> dict:
        counts = {g: 0 for g in GROUPS}
        for it in self.pending():
            counts[it["group"]] = counts.get(it["group"], 0) + 1
        return counts

    # ---- 报告（第一产出） ----
    def report_markdown(self) -> str:
        pending = sorted(self.pending(),
                         key=lambda it: (-len(it["blocks_downstream"]), it["item_id"]))
        counts = self.by_group()
        lines = [
            "# 隔离区报告（请你确认清单）",
            "",
            f"> cbb-quarantine M1 ｜ 待裁决 {len(pending)} 项 ｜ 已裁决 {len(self.adjudicated())} 项",
            "> 纪律：显式隔离，绝不静默丢弃（B6）；以下条目按**阻塞下游计数降序**排列。",
            "",
            "## 分组统计",
        ]
        for g in GROUPS:
            if counts.get(g):
                lines.append(f"- **{g}**: {counts[g]} 项")
        if not any(counts.values()):
            lines.append("- （空）")
        lines += ["", "## 待裁决清单（按阻塞下游计数降序）"]
        for i, it in enumerate(pending, 1):
            lines += [
                "",
                f"### {i}. [{it['group']}] `{it['item_id']}`（阻塞下游 {len(it['blocks_downstream'])} 项）",
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


def three_state_write_stub(record: dict, out_root: Path, status: str):
    """三态写入桩（M1）：与其他 cbb-* 同纪律——三池分目录、ID 命名、已存在即跳过。"""
    if status not in THREE_STATE_SINKS:
        raise ValueError(f"非法三态 {status!r}")
    rid = record.get("record_id") or record.get("block_id")
    if not rid:
        raise ValueError("record 缺 record_id/block_id")
    sink = Path(out_root) / status
    sink.mkdir(parents=True, exist_ok=True)
    path = sink / f"{rid}.json"
    if path.exists():
        return path, False
    path.write_text(json.dumps(record, ensure_ascii=False, sort_keys=True, indent=1),
                    encoding="utf-8")
    return path, True


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="CBB B6 隔离区（M1 骨架）")
    ap.add_argument("--root", required=True, help="隔离区目录")
    ap.add_argument("--register", nargs=4, metavar=("GROUP", "DETAIL", "RECORD_ID", "SOURCE"),
                    help="登记一条隔离条目（RECORD_ID/SOURCE 可填 -）")
    ap.add_argument("--adjudicate", nargs=3, metavar=("ITEM_ID", "DECISION", "NOTE"),
                    help="人工裁决（confirmed|rejected）")
    ap.add_argument("--report", action="store_true", help="打印报告 markdown")
    args = ap.parse_args(argv)

    zone = QuarantineZone(Path(args.root))
    if args.register:
        group, detail, rid, source = args.register
        iid, created = zone.register(group, detail,
                                     record_id=None if rid == "-" else rid,
                                     source=None if source == "-" else source)
        print(f"[quarantine] item={iid} created={created}")
    if args.adjudicate:
        iid, decision, note = args.adjudicate
        zone.adjudicate(iid, decision, note)
        print(f"[quarantine] adjudicated {iid} -> {decision}")
    if args.report:
        print(zone.report_markdown())
    if not (args.register or args.adjudicate or args.report):
        print(f"[quarantine] pending={len(zone.pending())} adjudicated={len(zone.adjudicated())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
