# -*- coding: utf-8 -*-
"""cbb_store.py — CBB 三态写入+版本化+双轨合并存储（本体版 v2，jsonl-file 后端）

保留（v1.0，16 仓无更优完整替代）：三态写入纪律（confirmed/provisional 入库、
  quarantine 走隔离区）、旁车 transitions.jsonl（append-only，文件写后不改）、
  supersedes 版本化（新版本新文件+索引旁车，旧件字节不动）、置信度路由
  （confirmed 永不因置信度单独达成）。
重构（U-B07）：**双轨合并**——一致重复→confidence 上调合并（经 supersede 出新版本，
  证据并集）；矛盾→quarantine+Verdict（**不静默合并**，冲突两派并陈入裁决文书）。
吸收（U-A17 §3；webnovel-writer 为 GPL 仓——按其详报合规提示，本实现按设计重写，
  零源码引用，详报为唯一转述层）：
  - UNIQUE 约束族（schema 层防重）：别名复合 PK(alias,entity_id,entity_type)/
    关系三元组唯一(subject,rel_type,object)/出场唯一(entity,chapter)；
  - verified_against 漂移钩子（story-systems）：源 SHA 变更→记录 stale→重验门；
  - ON CREATE/ON MATCH 幂等（neo4j MERGE 语义的文件后端等价）= admit_or_merge；
  - 时序回放查询（chapter<=? ORDER BY 顺序覆盖，state_changes 追加日志范式）；
  - 写入安全围栏：根围栏（写出 root 即拒）+符号链接拒绝+命令白名单思想
    （CLI 仅暴露声明动词，store 层不发起任何 shell 调用）；
  - cbb-merge 并入（用户裁决：规模小不拆独立技能）：多版本对齐合并
    Keep/Range/Flag/Pick+冲突表（claude-book merger 词汇）。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "contracts"))
sys.path.insert(0, str(HERE.parent / "cbb-quarantine"))
import cbb_contracts  # noqa: E402
from cbb_quarantine import QuarantineZone  # noqa: E402

# Part XI 名义阈值（P2 由置信度校准器标定取代）
# —— v1.4 漂移修正 W4（2026-09-17，U-C03.5）：三档显式化 + B3 再校准挂钩 ——
# 语义（三档两边界，宁滥勿漏）：
#   τ_confirmed  = 0.97：confirmed 参考带顶（B1：confirmed 永不因置信度单独达成，
#                  须门2b/人工通道；此常量只作校准报告的带顶基准，不驱动路由晋级）；
#   τ_provisional= 0.85：provisional 带地板（≥ 于此值入库 provisional）；
#   τ_quarantine = 0.85：quarantine 边界（< 于此值路由隔离区 low_confidence）。
#   τ_quarantine 与 τ_provisional 同值=设计决定（B1 保守：两带之间无灰区；
#   调整属审核线裁决，B3 校准报告只呈建议，不自动改）。
TAU_CONFIRMED = 0.97
TAU_PROVISIONAL = 0.85
TAU_QUARANTINE = 0.85
THRESHOLDS = {
    "tau_confirmed": TAU_CONFIRMED,
    "tau_provisional": TAU_PROVISIONAL,
    "tau_quarantine": TAU_QUARANTINE,
    "corroboration_bump": 2.0,
    "note": "confirmed 永不因置信度单独达成（B1）；调整=审核线建议制（W4/B3）",
}
CORROBORATION_BUMP = 2.0  # 一致重复每见一次独立佐证的置信度上调步长（CBB 定约，封顶 100）

LIBRARIES = ("event", "character", "timeline", "relation", "setting", "foreshadow")
ADMIT_DECISIONS = ("confirmed", "provisional", "quarantine")
TRANSITION_BYS = ("human", "shadow", "promotion")  # Record.provenance.status_history.by 枚举

UNIQUE_CONSTRAINTS = (
    "aliases_pk(alias,entity_id,entity_type)",       # 别名复合 PK
    "relations_unique(subject,rel_type,object)",     # 关系三元组唯一
    "appearances_unique(entity,chapter)",            # 出场唯一
)


def route_by_confidence(confidence: float) -> str:
    """三档显式路由（W4）：≥τ_provisional → provisional；<τ_quarantine → quarantine。
    confirmed 永不因置信度单独达成（门2b/人工通道缺席时的 B1 保守纪律）。
    τ_quarantine..τ_provisional 之间当前不可达（两阈值同值=设计决定）；若审核线
    日后拉开两阈值，该区间的保守路由=隔离（宁滥勿漏）。"""
    if confidence >= TAU_PROVISIONAL:
        return "provisional"
    if confidence < TAU_QUARANTINE:
        return "quarantine"
    return "quarantine"  # 灰区保守：隔离（当前不可达分支，W4 留位）


def identity_key(record: dict) -> tuple:
    """记录身份键：entity=库名+canonical.name；relation=三元组；其余=record_id（内容寻址）。"""
    rt = record.get("record_type")
    c = record.get("canonical") or {}
    if rt == "entity" and c.get("name"):
        return ("entity", record.get("library"), c["name"])
    if rt == "relation" and all(c.get(k) for k in ("subject", "rel_type", "object")):
        return ("relation", c["subject"], c["rel_type"], c["object"])
    return ("id", record.get("record_id"))


def canonical_conflicts(a: dict, b: dict) -> list[dict]:
    """双轨判轨：双方 canonical 同键不同值 → 冲突清单（空=一致重复）。"""
    ca, cb = a.get("canonical") or {}, b.get("canonical") or {}
    out = []
    for k in sorted(set(ca) & set(cb)):
        if ca[k] != cb[k]:
            out.append({"field": k, "incoming": ca[k], "stored": cb[k]})
    return out


def _chain_base(record_id: str) -> str:
    """版本链基名：剥除尾部累积的 -m / -m{N} 版本后缀（core_id 十六进制段不含 '-m'，
    剥后必为链首 id）。2026-09-20 Windows MAX_PATH 修复配套（见 dual_track 注）。"""
    rid = record_id
    while True:
        if rid.endswith("-m"):
            rid = rid[:-2]
            continue
        i = rid.rfind("-m")
        if i != -1 and rid[i + 2:].isdigit():
            rid = rid[:i]
            continue
        return rid


def multiversion_merge(records: list[dict]) -> dict:
    """多版本对齐合并（cbb-merge 并入；claude-book 四动作词汇）。

    逐字段分派（确定性规则）：
      Keep  —— 全源同值 → 保留为规则值；
      Range —— 全源均为数值且波动 → min-max 区间串；
      Flag  —— 仅单源有该字段 → 保留值+标记单源待证；
      Pick  —— 多源异值 → 取最长值（信息量最大，CBB 定约）；
    冲突表：凡 Pick/Flag 字段登记 {field, values, sources}（Sources vary 并陈纪律）。
    """
    if not records:
        return {"merged": {}, "actions": {}, "conflicts": []}
    names = [r.get("source_name", f"src{i}") for i, r in enumerate(records)]
    fields = sorted({k for r in records for k in (r.get("canonical") or {})})
    merged, actions, conflicts = {}, {}, []
    for f in fields:
        pairs = [(n, r["canonical"][f]) for n, r in zip(names, records) if f in (r.get("canonical") or {})]
        vals = [v for _, v in pairs]
        if len(pairs) == 1:
            merged[f] = vals[0]
            actions[f] = "flag"  # 单源特有：记录不强制（待证）——先于 all-equal 判定（单值恒自等）
            conflicts.append({"field": f, "values": vals, "sources": [pairs[0][0]]})
            continue
        if all(v == vals[0] for v in vals):
            merged[f] = vals[0]
            actions[f] = "keep"
            continue
        if len(vals) > 1 and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in vals):
            merged[f] = f"{min(vals)}-{max(vals)}"
            actions[f] = "range"
            continue
        merged[f] = sorted(vals, key=lambda v: (-len(str(v)), str(v)))[0]
        actions[f] = "pick"  # 各源最佳：取最长（信息量最大）
        conflicts.append({"field": f, "values": vals, "sources": [n for n, _ in pairs]})
    return {"merged": merged, "actions": actions, "conflicts": conflicts}


class ThreeStateStore:
    def __init__(self, root: Path, backend: str = "jsonl-file"):
        if backend != "jsonl-file":
            raise NotImplementedError(
                "本体版实现 jsonl-file 后端。P2 接 Neo4j/Graphiti（Step0 Tier2 已验证配置："
                "bolt://localhost:7687 + DeepSeek + LM Studio 嵌入），凭证走环境变量（D-004）。")
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.zone = QuarantineZone(self.root / "quarantine-zone")
        self.iter_skipped = []  # 全库遍历不可读文件名（超长路径），显式披露非静默

    # ---- 写入安全围栏：根围栏+符号链接拒绝 ----
    def _assert_within_root(self, path: Path) -> Path:
        """写路径必须解析后仍在 root 内；任何祖先级符号链接一律拒绝（宁可拒写不可逃逸）。"""
        p = Path(path)
        for part in [p, *p.parents]:
            if part.is_symlink():
                raise PermissionError(f"安全围栏：符号链接路径拒绝写入 {part}")
        resolved = p.resolve()
        root_resolved = self.root.resolve()
        if root_resolved != resolved and root_resolved not in resolved.parents:
            raise PermissionError(f"安全围栏：写出库根 {resolved}（root={root_resolved}）")
        return resolved

    # ---- 基元 ----
    def _append(self, name: str, obj: dict) -> None:
        p = self.root / name
        self._assert_within_root(p)
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False, sort_keys=True) + "\n")

    def _load_all(self, name: str) -> list[dict]:
        p = self.root / name
        if not p.exists():
            return []
        return [json.loads(ln) for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]

    def _lib_path(self, library: str, status: str, record_id: str) -> Path:
        return self.root / "libraries" / library / status / f"{record_id}.json"

    def _write_immutable(self, path: Path, obj: dict):
        self._assert_within_root(path)
        if path.exists():
            return path, False
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=1),
                        encoding="utf-8")
        return path, True

    # ---- UNIQUE 约束族（schema 层防重的文件后端等价） ----
    def register_alias(self, alias: str, entity_id: str, entity_type: str):
        """别名复合 PK(alias,entity_id,entity_type)：同键已存在→(key,False) 不重复登记。"""
        key = f"{alias}|{entity_id}|{entity_type}"
        if any(a["key"] == key for a in self._load_all("aliases.jsonl")):
            return key, False
        self._append("aliases.jsonl", {"key": key, "alias": alias,
                                       "entity_id": entity_id, "entity_type": entity_type})
        return key, True

    def relation_triple_exists(self, subject: str, rel_type: str, object: str) -> bool:
        return any(identity_key({"record_type": "relation",
                                 "canonical": {"subject": subject, "rel_type": rel_type,
                                               "object": object}}) == identity_key(r)
                   for r in self.iter_records())

    def record_appearance(self, entity: str, chapter: int):
        """出场唯一(entity,chapter)：同实体同章只记一次。"""
        key = f"{entity}|ch{chapter}"
        if any(a["key"] == key for a in self._load_all("appearances.jsonl")):
            return key, False
        self._append("appearances.jsonl", {"key": key, "entity": entity, "chapter": chapter})
        return key, True

    # ---- 三态入库（保留面） ----
    def admit(self, record: dict, decision: str, gate_trace_entry: dict | None = None,
              quarantine_group: str | None = None, quarantine_detail: str = ""):
        """candidate → confirmed/provisional/quarantine。
        confirmed/provisional：严格契约校验（status 置为目标态）+ status_history 初始条目；
        quarantine：不进 library，登记隔离区（B1：库中只有 confirmed/provisional）。"""
        if decision not in ADMIT_DECISIONS:
            raise ValueError(f"非法入库决定 {decision!r}，合法={ADMIT_DECISIONS}")
        rid = record.get("record_id")
        if not rid:
            raise ValueError("record 缺 record_id")

        if decision == "quarantine":
            iid, created = self.zone.register(
                group=quarantine_group or "low_confidence",
                detail=quarantine_detail or "门1 拦截件",
                record_id=rid, source="cbb-store",
                blocks=[],
            )
            return iid, created

        stored = dict(record)
        stored["status"] = decision
        hist_entry = {"from": "candidate", "to": decision, "by": "promotion"}
        stored.setdefault("provenance", {})
        stored["provenance"].setdefault("status_history", []).append(hist_entry)
        if gate_trace_entry:
            stored["provenance"].setdefault("gate_trace", []).append(gate_trace_entry)
        cbb_contracts.validate_record(stored)  # 严格：库内态必须全契约合规
        path = self._lib_path(stored["library"], decision, rid)
        return self._write_immutable(path, stored)

    # ---- 双轨合并（U-B07 重构核心） ----
    def find_by_identity(self, record: dict) -> dict | None:
        """按身份键找**活版本**（未被取代的最高版本；全部被取代则取最高版本）。"""
        key = identity_key(record)
        matches = [r for r in self.iter_records() if identity_key(r) == key]
        if not matches:
            return None
        superseded = {e["old_id"] for e in self._load_all("supersede-index.jsonl")}
        live = [m for m in matches if m["record_id"] not in superseded]
        pool = live or matches
        return max(pool, key=lambda m: m.get("version", 1))

    def contradiction_verdict(self, incoming: dict, existing: dict,
                              conflicts: list[dict], school: str = "documented_variance") -> dict:
        """矛盾轨裁决文书：critique 先行+label=conflict+分带一致+裁决规则表（两派并陈）。"""
        field_names = ", ".join(c["field"] for c in conflicts)
        confidence = 95.0
        verdict = {
            "issue_id": f"dual-track-{identity_key(incoming)}",
            "critique": f"身份键相同但字段冲突（{field_names}）：候选与库内记录均带原文证据，须裁决孰是孰非",
            "label": "conflict",
            "confidence": confidence,
            "confidence_band": cbb_contracts.confidence_band(confidence),
            "rule_applied": {"school": school, "field": field_names,
                             "rationale": "Sources vary：并陈双方待人工裁决（冲突表已登记）"},
            "judge_id": "cbb-store-dual-track",
            "reasoning": "双轨合并矛盾轨：不静默合并（B1）",
            "evidence_check": {"incoming_evidence": len(incoming.get("evidence") or []),
                               "existing_evidence": len(existing.get("evidence") or [])},
        }
        cbb_contracts.validate_verdict(verdict)
        return verdict

    def dual_track(self, incoming: dict, school: str = "documented_variance") -> dict:
        """双轨合并主入口：
        一致重复 → confidence 上调合并（supersede 出新版本，证据并集）；
        矛盾     → quarantine(contradiction_pending)+Verdict（不静默合并）；
        无既存   → ON CREATE（新写入，provisional 起步）。"""
        existing = self.find_by_identity(incoming)
        if existing is None:
            path, created = self.admit(incoming, "provisional")
            return {"track": "on-create", "path": str(path), "created": created}
        conflicts = canonical_conflicts(incoming, existing)
        if not conflicts:
            # 幂等守卫（P-017）：incoming 证据已被活版本完全包含 → 该观察已合并过，
            # 不再叠新版本（重放同批次零副作用——append-only 旁车之外的库文件不增殖）
            def _ev_set(rec):
                return {(e.get("vol"), e.get("chapter"), e.get("line"), e.get("quote"))
                        for e in (rec.get("evidence") or [])}
            if _ev_set(incoming) <= _ev_set(existing):
                return {"track": "consistent-duplicate", "new_id": existing["record_id"],
                        "confidence": (existing.get("provenance") or {}).get(
                            "extractor_confidence"),
                        "created": False, "repeated": True}
            # 一致重复轨：confidence 上调 + 证据并集，经 supersede 出新版本（旧件不动）
            merged = dict(existing)
            old_conf = (existing.get("provenance") or {}).get("extractor_confidence", 0) or 0
            new_conf = (incoming.get("provenance") or {}).get("extractor_confidence", 0) or 0
            merged.setdefault("provenance", {})["extractor_confidence"] = min(
                100.0, max(old_conf, new_conf) + CORROBORATION_BUMP)
            seen_q, ev = set(), list(existing.get("evidence") or [])
            for e in incoming.get("evidence") or []:
                k = (e.get("vol"), e.get("chapter"), e.get("line"), e.get("quote"))
                if k not in seen_q:
                    seen_q.add(k)
                    ev.append(e)
            merged["evidence"] = ev
            # 2026-09-20 Windows MAX_PATH 修复：旧法 record_id+"-m" 逐次累加，高频实体
            # 77 次合并后路径 261 字符>260 上限写入失败（ch0143 首案）。改为紧凑版本后缀
            # -m{N}（N=新版本号，链内严格递增=唯一性等价；剥旧后缀取链基名，旧链文件不动；
            # supersede-index/resolve_latest 按 id 等值工作，不受文件名形态影响）。
            new_ver = existing.get("version", 1) + 1
            merged["record_id"] = f"{_chain_base(existing['record_id'])}-m{new_ver}"
            path, created = self.supersede(existing["record_id"], merged)
            return {"track": "consistent-duplicate", "new_id": merged["record_id"],
                    "confidence": merged["provenance"]["extractor_confidence"],
                    "path": str(path), "created": created}
        # 矛盾轨：隔离+裁决文书
        detail = "；".join(f"{c['field']}: 入库={c['incoming']!r} vs 库内={c['stored']!r}"
                          for c in conflicts)
        iid, created = self.zone.register(
            group="entity_unalignable", detail=detail,
            record_id=incoming.get("record_id"), source="cbb-store-dual-track",
            subclass="contradiction_pending")
        verdict = self.contradiction_verdict(incoming, existing, conflicts, school=school)
        return {"track": "contradiction", "quarantine_item": iid, "created": created,
                "verdict": verdict}

    def admit_or_merge(self, record: dict) -> dict:
        """ON CREATE/ON MATCH 幂等（neo4j MERGE 语义的文件后端等价）：
        身份键无既存→CREATE；既存且一致→MATCH 上调合并；既存且矛盾→隔离+Verdict。"""
        return self.dual_track(record)

    # ---- verified_against 漂移钩子（story-systems） ----
    def drift_check(self, record: dict, current_sha: str) -> dict:
        """源 SHA 与记录验证时 SHA 不一致 → stale（须重验：重读场景→更新声明→bump 版本）。"""
        va = record.get("verified_against") or {}
        return {"record_id": record.get("record_id"), "path": va.get("path"),
                "verified_sha": va.get("sha"), "current_sha": current_sha,
                "stale": bool(va.get("sha")) and va.get("sha") != current_sha}

    def stale_records(self, current_shas: dict[str, str]) -> list[dict]:
        """全库漂移扫描：{path: 当前 SHA} → stale 记录清单（重验门输入）。"""
        return [d for r in self.iter_records()
                if (d := self.drift_check(r, current_shas.get(
                    (r.get("verified_against") or {}).get("path"), "")))["stale"]]

    # ---- 时序回放（state_changes 追加日志+顺序覆盖） ----
    def log_state_change(self, entity: str, field: str, new_value, chapter: int,
                         reason: str = "") -> None:
        self._append("state_changes.jsonl",
                     {"entity": entity, "field": field, "new_value": new_value,
                      "chapter": chapter, "reason": reason,
                      "seq": len(self._load_all("state_changes.jsonl"))})

    def entity_state_at_chapter(self, entity: str, chapter: int) -> dict:
        """时序回放：state_changes WHERE entity=? AND chapter<=?
        ORDER BY chapter ASC, seq ASC 顺序覆盖 field→new_value（任意章状态快照）。"""
        changes = [c for c in self._load_all("state_changes.jsonl")
                   if c["entity"] == entity and c["chapter"] <= chapter]
        changes.sort(key=lambda c: (c["chapter"], c["seq"]))
        state = {}
        for c in changes:
            state[c["field"]] = c["new_value"]  # 顺序覆盖
        return state

    # ---- 状态迁移（旁车日志，文件不动；保留面） ----
    def status_transition(self, record_id: str, to_status: str, by: str = "human",
                          note: str = "") -> dict:
        """provisional→confirmed（人工/交叉印证/门2b）或 confirmed→provisional（影子审计降级）。
        迁移落 transitions.jsonl；record 文件字节不动（文件后端的 status_history 等价物）。"""
        if by not in TRANSITION_BYS:
            raise ValueError(f"非法 by {by!r}")
        if to_status not in ("confirmed", "provisional"):
            raise ValueError("文件后端迁移仅限库内两态；quarantine/rejected 走隔离区裁决通道")
        current = self._find(record_id)
        if current is None:
            raise KeyError(f"记录不在库: {record_id}")
        if self.effective_status(record_id) == to_status:
            return {"record_id": record_id, "from": to_status, "to": to_status,
                    "by": by, "note": note, "repeated": True}  # 幂等：目标态已达则不重复入账
        entry = {"record_id": record_id, "from": current["status"], "to": to_status,
                 "by": by, "note": note}
        self._append("transitions.jsonl", entry)
        return entry

    def effective_status(self, record_id: str) -> str | None:
        """文件态 + 旁车迁移的最终态。"""
        rec = self._find(record_id)
        if rec is None:
            return None
        status = rec["status"]
        for t in self._load_all("transitions.jsonl"):
            if t["record_id"] == record_id:
                status = t["to"]
        return status

    # ---- 版本化 supersedes（B5；保留面） ----
    def supersede(self, old_id: str, new_record: dict):
        """以 new_record 取代 old_id：新文件 version=old.version+1、supersedes=old_id；
        旧件字节不动；supersede-index.jsonl 登记链。返回 (new_path, created)。"""
        old = self._find(old_id)
        if old is None:
            raise KeyError(f"被取代记录不在库: {old_id}")
        if new_record.get("record_id") == old_id:
            raise ValueError("新版本必须换 record_id（旧件不可覆盖）")
        new = dict(new_record)
        if new.get("status") not in ("confirmed", "provisional"):
            new["status"] = "provisional"  # 修订版默认 provisional 待重过门（B1 保守）
        new["version"] = old["version"] + 1
        new["supersedes"] = old_id
        new.setdefault("provenance", {}).setdefault("status_history", []).append(
            {"from": "superseded:" + old_id, "to": new.get("status", "provisional"),
             "by": "promotion"})
        cbb_contracts.validate_record(new)
        path = self._lib_path(new["library"], new["status"], new["record_id"])
        result = self._write_immutable(path, new)
        if result[1]:
            self._append("supersede-index.jsonl",
                         {"old_id": old_id, "new_id": new["record_id"],
                          "version": new["version"]})
        return result

    def resolve_latest(self, record_id: str) -> dict | None:
        """沿 supersedes 链取最新版本。"""
        chain = {e["old_id"]: e["new_id"] for e in self._load_all("supersede-index.jsonl")}
        cur = record_id
        seen = set()
        while cur in chain and cur not in seen:
            seen.add(cur)
            cur = chain[cur]
        return self._find(cur)

    # ---- 查询 ----
    def iter_records(self):
        """遍历全库记录。2026-09-22 U-C04 段收口修复：批20 前旧连缀命名的超长路径文件
        （如 77×'-m'，绝对路径>Windows 260）glob 可枚举但 open 失败——收集进 iter_skipped
        显式披露（非静默跳过），供 calibration_report 等全库遍历调用方附带报告。"""
        for lib in LIBRARIES:
            for status in ("confirmed", "provisional"):
                d = self.root / "libraries" / lib / status
                if d.exists():
                    for p in sorted(d.glob("*.json")):
                        try:
                            yield json.loads(p.read_text(encoding="utf-8"))
                        except OSError:
                            self.iter_skipped.append(p.name)

    def _find(self, record_id: str):
        for lib in LIBRARIES:
            for status in ("confirmed", "provisional"):
                p = self._lib_path(lib, status, record_id)
                if p.exists():
                    return json.loads(p.read_text(encoding="utf-8"))
        return None

    def stats(self) -> dict:
        out = {"libraries": {}, "quarantine_pending": len(self.zone.pending()),
               "unique_constraints": list(UNIQUE_CONSTRAINTS)}
        for lib in LIBRARIES:
            counts = {}
            for status in ("confirmed", "provisional"):
                d = self.root / "libraries" / lib / status
                counts[status] = len(list(d.glob("*.json"))) if d.exists() else 0
            if any(counts.values()):
                out["libraries"][lib] = counts
        return out

    # ---- W4/B3 校准报告（段收口钩子；建议制，不自动改阈值） ----
    def calibration_report(self) -> dict:
        """库内置信分布+隔离区分布 vs 三阈值假设：
        ① 分布：≥τ_confirmed / provisional 带 / 库内 <τ_quarantine 遗存计数；
        ② 隔离：pending 按 group/subclass 计数（矛盾/低置信/超期各归其位=十查⑥输入）；
        ③ 假设核对与机械建议（建议制呈报审核线，阈值不自动改）。"""
        confs = []
        for r in self.iter_records():
            c = (r.get("provenance") or {}).get("extractor_confidence")
            if isinstance(c, (int, float)) and not isinstance(c, bool):
                confs.append(float(c))
        dist = {
            "records_with_confidence": len(confs),
            "ge_tau_confirmed": sum(1 for c in confs if c >= TAU_CONFIRMED),
            "provisional_band": sum(1 for c in confs if TAU_PROVISIONAL <= c < TAU_CONFIRMED),
            "below_tau_quarantine_in_library": sum(1 for c in confs if c < TAU_QUARANTINE),
            "min": min(confs) if confs else None,
            "max": max(confs) if confs else None,
            "mean": round(sum(confs) / len(confs), 4) if confs else None,
            "iter_skipped_unreadable": list(self.iter_skipped),
        }
        q_group = self.zone.by_group()
        q_sub = self.zone.by_subclass()
        checks, suggestions = [], []
        if dist["below_tau_quarantine_in_library"]:
            checks.append(f"库内存在 {dist['below_tau_quarantine_in_library']} 条 <τ_quarantine 置信记录"
                          "（合并上调/历史口径遗存）——U-C09 R1 对账项")
        total_q = sum(q_group.values())
        if dist["records_with_confidence"]:
            ratio = total_q / (total_q + dist["records_with_confidence"])
            checks.append(f"隔离/入库比={ratio:.3f}（pending {total_q} vs 库内 "
                          f"{dist['records_with_confidence']}）")
            if ratio > 0.5:
                suggestions.append("隔离占比>50%：若持续，建议审核线复核 τ_quarantine 或抽取规范置信校准表")
        if dist["min"] is not None and dist["min"] >= TAU_PROVISIONAL and q_group.get("low_confidence"):
            checks.append("路由边界执行一致：库内置信全部 ≥τ_provisional，低置信候选均已在隔离区")
        return {
            "thresholds": THRESHOLDS,
            "library_confidence_distribution": dist,
            "quarantine_by_group": q_group,
            "quarantine_by_subclass": q_sub,
            "assumption_checks": checks,
            "suggestions": suggestions,
            "decision_rule": "阈值调整=审核线建议制呈报，不自动改（W4/B3）",
        }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="CBB 三态+双轨合并存储（本体版 v2）")
    ap.add_argument("--root", required=True, help="库根目录")
    ap.add_argument("--stats", action="store_true", help="打印库统计")
    ap.add_argument("--calibration", action="store_true",
                    help="打印 W4/B3 校准报告（置信/隔离分布 vs 三阈值假设，建议制）")
    args = ap.parse_args(argv)
    store = ThreeStateStore(Path(args.root))
    if args.stats:
        print(json.dumps(store.stats(), ensure_ascii=False, indent=1))
        return 0
    if args.calibration:
        print(json.dumps(store.calibration_report(), ensure_ascii=False, indent=1))
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
