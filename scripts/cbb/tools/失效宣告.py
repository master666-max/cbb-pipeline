# -*- coding: utf-8 -*-
"""失效宣告.py — 事实演化的"宣告失效"写入件（2026-09-22 用户裁定 ①A 严格三情形）

语义（裁定 ①A，逐条执行）：
  **允许写入 invalid_at 的三种情形（kind）**：
    value_conflict  值冲突型——同主体同字段两值互斥、双方证据均有效、**人工裁决 confirmed**
    superseded      取代型——新版本经双轨取代（supersede）且新旧均为事实陈述
    termination     终止型——关系终止/状态结束且**人工确认**
  **禁止写入（kind）**——这三类是"从来没对过"，不是"曾经为真"，写进失效史=冒充：
    extraction_error  抽错返工
    alias_unaligned   别名未对齐
    granularity       粒度差异
  **失效章语义**（照 Zep/Graphiti）：invalid_at = 新说法最早证据章；旧事实永久保留不删。
  **写入载体**：store 根下 `invalidations.jsonl`（append-only；幂等键=record_id|kind|invalid_at）。
  **旧件字节不动**：本件不改任何记录文件；派生视图由 `apply_to_edges()` 合成输出到新文件。

机械闸（无模型参与，全部可复算）：
  - value_conflict / termination → `by` 必须为 "human"（人工确认硬条款）
  - value_conflict / superseded  → `evidence_sides` 必须 == 2（双方）；termination ≥ 1
  - `verdict_ref` 必填（裁决件/取代件指针；无指针不落账——T-5：每个数带口径）
"""
from __future__ import annotations

import json
import sys
from datetime import date as _date
from pathlib import Path

ALLOWED_KINDS = ("value_conflict", "superseded", "termination")
FORBIDDEN_KINDS = ("extraction_error", "alias_unaligned", "granularity")
FORBIDDEN_WHY = {
    "extraction_error": "抽错返工：记录从未正确过，无'曾为真'可言",
    "alias_unaligned": "别名未对齐：同一事实的两份写法，不是事实变更",
    "granularity": "粒度差异：'人物'vs'人物(迷宫生物)'是口径问题，不是事实推翻",
}


def _today() -> str:
    return _date.today().isoformat()


def _load(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def write_invalidation(store_root: Path | str, *, record_id: str, invalid_at: int,
                       kind: str, verdict_ref: str, evidence_sides: int,
                       by: str, at: str | None = None) -> tuple[dict, bool]:
    """写入一条失效宣告（append-only，幂等）。返回 (记录, 是否新写入)。
    违反裁定 ①A 的情形一律 ValueError，绝不静默放行。"""
    if kind in FORBIDDEN_KINDS:
        raise ValueError(f"禁止写入的失效 kind={kind!r}：{FORBIDDEN_WHY[kind]}")
    if kind not in ALLOWED_KINDS:
        raise ValueError(f"未知 kind={kind!r}，合法={ALLOWED_KINDS}＋禁止={FORBIDDEN_KINDS}")
    if not record_id or not verdict_ref:
        raise ValueError("record_id 与 verdict_ref 必填（无裁决/取代指针不落账——T-5）")
    if not isinstance(invalid_at, int) or isinstance(invalid_at, bool) or invalid_at < 0:
        raise ValueError(f"invalid_at 必须为非负整数（失效章），实为 {invalid_at!r}")
    if kind in ("value_conflict", "termination") and by != "human":
        raise ValueError(f"kind={kind} 属人工确认情形，by 必须为 'human'，实为 {by!r}")
    if kind in ("value_conflict", "superseded") and evidence_sides != 2:
        raise ValueError(f"kind={kind} 要求双方证据（evidence_sides==2），实为 {evidence_sides}")
    if kind == "termination" and evidence_sides < 1:
        raise ValueError(f"kind=termination 至少 1 侧证据，实为 {evidence_sides}")

    root = Path(store_root)
    root.mkdir(parents=True, exist_ok=True)
    path = root / "invalidations.jsonl"
    rows = _load(path)
    key = (record_id, kind, invalid_at)
    for r in rows:
        if (r["record_id"], r["kind"], r["invalid_at"]) == key:
            return r, False  # 幂等：已在账
    rec = {"record_id": record_id, "invalid_at": invalid_at, "kind": kind,
           "verdict_ref": verdict_ref, "evidence_sides": evidence_sides,
           "by": by, "at": at or _today()}
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec, True


def load_invalidations(store_root: Path | str) -> list[dict]:
    return _load(Path(store_root) / "invalidations.jsonl")


def apply_to_edges(edges_path: Path | str, invalidations: list[dict],
                   out_path: Path | str) -> dict:
    """把失效宣告并入图边视图：匹配 record_id 的边写 invalid_at=min(现值, 宣告值)。
    **输入文件字节不动**，结果写 out_path（派生层可重建——真源是账本）。"""
    edges_path, out_path = Path(edges_path), Path(out_path)
    by_rec: dict[str, list[dict]] = {}
    for inv in invalidations:
        by_rec.setdefault(inv["record_id"], []).append(inv)
    rows = [json.loads(x) for x in edges_path.read_text(encoding="utf-8").splitlines() if x.strip()]
    hit = already = 0
    for r in rows:
        for inv in by_rec.get(r.get("record_id"), []):
            cur = r.get("invalid_at")
            if cur is None:
                r["invalid_at"] = inv["invalid_at"]
                r["invalidation_ref"] = inv["verdict_ref"]
                hit += 1
            elif inv["invalid_at"] < cur:
                r["invalid_at"] = inv["invalid_at"]
                r["invalidation_ref"] = inv["verdict_ref"]
                hit += 1
            else:
                already += 1  # 现值更早或相等：保留更早失效章
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return {"edges": len(rows), "invalidated": hit, "kept_earlier": already,
            "口径": "invalid_at=min(现值,宣告值)；输入未动，输出为新文件"}


def main(argv=None) -> int:  # pragma: no cover
    import argparse
    ap = argparse.ArgumentParser(description="失效宣告（裁定①A）")
    ap.add_argument("--store", required=True)
    ap.add_argument("--edges")
    ap.add_argument("--out")
    ns = ap.parse_args(argv)
    invs = load_invalidations(ns.store)
    print(f"失效宣告在账 {len(invs)} 条")
    if ns.edges and ns.out:
        print(apply_to_edges(ns.edges, invs, ns.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
