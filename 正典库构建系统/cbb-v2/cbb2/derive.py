# -*- coding: utf-8 -*-
"""cbb2.derive — 投影派生层（Phase B）：归属单键 + 双时序 + 投影检查点 + 导出债务。

D-13 根治：写侧 SET 与读侧过滤**共用 NS_PROPERTY 单键常量**——归属判据不许有两个名字。
D-14 根治：导出债务 carry incur/repay 语义（append-only 双向行），open_count 可归零——
     "曾经缺过"与"现在还缺"分离，终审前置=开放债务=0 可达。
双时序：t_valid/t_invalid（叙事时间，源自 Phase A 契约）随节点/边落图——
     "第 N 章时 X 的状态"一条 Cypher 可答，无需 Graphiti（裁④）。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

# ---- U-B02 归属单键（D-13 根治：唯一键名，写读同源） ----
NS_PROPERTY = "group_id"


def ns_of() -> str:
    from .config import namespace
    return namespace()


def upsert_node_cypher(rec: dict, ns: str, invalidation: dict | None = None) -> tuple[str, dict]:
    """实体记录→节点 upsert（MERGE 键=group_id+name+lib，稳定业务键免疫悬空 ID 坑）。
    双时序：valid_at=t_valid；invalid_at=失效记账登记值 > 记录自带值（后者为兼容字段）。"""
    c = rec.get("canonical") or {}
    name = c.get("name") or rec.get("record_id")
    invalid_at = (invalidation or {}).get("t_invalid") or rec.get("t_invalid") or None
    cypher = (
        f"MERGE (e:Entity {{name:$name, {NS_PROPERTY}:$ns}}) "
        "ON CREATE SET e.created_at=$at "
        f"SET e.`{NS_PROPERTY}`=$ns, "
        "e.entity_type=$entity_type, e.lib=$lib, "
        "e.valid_at=$valid_at, "
        "e.invalid_at=CASE WHEN $invalid_at IS NULL THEN e.invalid_at ELSE $invalid_at END"
    )
    params = {"name": name, "ns": ns, "at": rec.get("at"), "entity_type": c.get("entity_type"),
              "lib": rec.get("library"), "valid_at": rec.get("t_valid"), "invalid_at": invalid_at}
    return cypher, params


def upsert_edge_cypher(rec: dict, ns: str, invalidation: dict | None = None) -> tuple[str, dict]:
    """关系记录→边挂接（B1 修复：端点用 MATCH 不 MERGE——绝不自动创建空实体节点；
    端点缺席时语句零生效，调用方据 results 计数登记 ER 缺口）。"""
    c = rec.get("canonical") or {}
    invalid_at = (invalidation or {}).get("t_invalid") or rec.get("t_invalid") or None
    cypher = (
        f"MATCH (s:Entity {{name:$subject, `{NS_PROPERTY}`:$ns}}) "
        f"MATCH (o:Entity {{name:$object, `{NS_PROPERTY}`:$ns}}) "
        "MERGE (s)-[r:REL {edge_id:$edge_id}]->(o) "
        f"SET r.`{NS_PROPERTY}`=$ns, r.rel_type=$rel_type, "
        "r.valid_at=$valid_at, "
        "r.invalid_at=CASE WHEN $invalid_at IS NULL THEN r.invalid_at ELSE $invalid_at END"
    )
    edge_id = rec.get("record_id")
    params = {"subject": c.get("subject"), "object": c.get("object"), "edge_id": edge_id,
              "ns": ns, "rel_type": c.get("rel_type"),
              "valid_at": rec.get("t_valid"), "invalid_at": invalid_at}
    return cypher, params


def ownership_verify_cypher(ns: str) -> tuple[str, dict]:
    """读侧归属判定——与写侧**同键**（D-13：v1 时代写 ns/读 group_id 的分裂在此终结）。"""
    cypher = (f"MATCH (n) WHERE n.`{NS_PROPERTY}`=$ns RETURN count(n) AS owned")
    return cypher, {"ns": ns}


# ---- U-B01 投影检查点（崩溃重放代替 mtime 猜测） ----

class ProjectionCheckpoint:
    """视图投影检查点：{view, ledger_offset, sha, at}——投影成功才推进，崩溃从 offset 重放。"""

    def __init__(self, store_root: Path, view: str):
        self.dir = Path(store_root) / "投影检查点"
        self.path = self.dir / f"{view}.json"

    def load(self) -> dict | None:
        if not self.path.exists():
            return None
        return json.loads(self.path.read_text(encoding="utf-8"))

    def commit(self, ledger_offset: int, sha: str, at: str) -> dict:
        self.dir.mkdir(parents=True, exist_ok=True)
        cp = {"view": self.path.stem, "ledger_offset": ledger_offset, "sha": sha, "at": at}
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(cp, ensure_ascii=False, sort_keys=True, indent=1),
                       encoding="utf-8")
        tmp.replace(self.path)  # 原子写
        return cp

    def replay_needed(self, current_ledger_rows: int) -> bool:
        """B2 修复：检查点偏移 ≠ 当前账本行数（无论前进还是回卷）⇒ 视图需要重放/重喂。"""
        cp = self.load()
        if cp is None:
            return True
        return cp["ledger_offset"] != current_ledger_rows


# ---- U-B03 导出债务（D-14 根治：incur/repay 双向行，open 可归零） ----

class DebtLedger:
    """append-only 双向行：incur（欠下）与 repay（清偿，FIFO 核销最旧 open 项）。"""

    def __init__(self, store_root: Path):
        self.path = Path(store_root) / "导出债务.jsonl"

    def _rows(self) -> list[dict]:
        if not self.path.exists():
            return []
        return [json.loads(x) for x in self.path.read_text(encoding="utf-8").splitlines() if x.strip()]

    def _append(self, row: dict):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    def incur(self, target: str, reason: str, at: str) -> dict:
        did = "debt-" + hashlib.sha256(f"{target}|{reason}|{at}|incur".encode()).hexdigest()[:12]
        row = {"op": "incur", "id": did, "target": target, "reason": reason, "at": at}
        self._append(row)
        return row

    def repay(self, target: str, at: str, note: str = "") -> dict | None:
        open_rows = self.open_items(target)
        if not open_rows:
            return None
        oldest = open_rows[0]
        row = {"op": "repay", "id": "repay-" + hashlib.sha256(
            f"{oldest['id']}|{at}".encode()).hexdigest()[:12],
            "repays": oldest["id"], "target": target, "note": note, "at": at}
        self._append(row)
        return row

    def open_items(self, target: str | None = None) -> list[dict]:
        rows = self._rows()
        repaid = {r["repays"] for r in rows if r["op"] == "repay"}
        return [r for r in rows
                if r["op"] == "incur" and r["id"] not in repaid
                and (target is None or r["target"] == target)]

    def open_count(self, target: str | None = None) -> int:
        return len(self.open_items(target))
