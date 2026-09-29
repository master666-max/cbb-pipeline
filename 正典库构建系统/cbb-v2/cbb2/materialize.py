# -*- coding: utf-8 -*-
"""cbb2.materialize — 批次 5·物料化晋升执行（store 正门 status_transition 通道）。

晋升资格（三关全过才动状态位）：
  ①轮次关：判词 promote（GLM∧DS 双 support ∧ 零 against ∧ 非 degraded）且该轮植株捕获门 PASS；
  ②状态关：effective_status == provisional（已 confirmed 幂等跳过）；
  ③gate1 关：check_record 零违例（可注入 gate1_fn 供测试；生产用真模块）。
写入走 Store.status_transition(by="promotion")——R13 旁车日志（transitions.jsonl），文件不动；
effective_status 自此读作 confirmed；物料化台账 append materialize-log.jsonl。
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from .store import Store


def load_round(path: Path) -> list[dict]:
    """判词台账取每记录最新一行（append-only 末行胜出），滤出可物料化的 promote 行。"""
    latest: dict[str, dict] = {}
    order: list[str] = []
    for l in Path(path).read_text(encoding="utf-8").splitlines():
        s = l.strip()
        if not s:
            continue
        r = json.loads(s)
        rid = r["record_id"]
        if rid not in latest:
            order.append(rid)
        latest[rid] = r
    return [latest[rid] for rid in order
            if latest[rid].get("verdict") == "promote"
            and not latest[rid].get("degraded")
            and not latest[rid].get("is_plant")]


def _real_gate1(rec: dict, store: Store) -> list:
    """生产 gate1：cbb-gate1.check_record（迷深/发布树同源）。ctx 由库内全记录构建。"""
    import sys
    gate_dir = Path(__file__).resolve().parents[2] / "cbb" / "cbb-gate1"
    if str(gate_dir) not in sys.path:
        sys.path.insert(0, str(gate_dir))
    from cbb_gate1 import check_record
    all_recs = [json.loads(f.read_text(encoding="utf-8"))
                for f in (store.root / "libraries").glob("*/*/*.json")]
    by_id = {r["record_id"]: r for r in all_recs}
    ctx = {"blocks": None, "known_ids": set(by_id), "records_by_id": by_id,
           "all_records": all_recs, "entities_by_name": {}, "seen_statuses": set(),
           "current_chapter": None}
    v = check_record(rec, ctx)
    if isinstance(v, dict):
        return v.get("violations") or []
    return list(v) if v else []


def materialize_round(store_root: Path, rows: list[dict], tag: str = "",
                      dry_run: bool = False, gate1_fn=None,
                      require_pass_snapshot: Path | None = None) -> dict:
    store = Store(Path(store_root))
    if gate1_fn is None:
        gate1_fn = lambda rec: _real_gate1(rec, store)  # noqa: E731
    store = Store(Path(store_root))
    if require_pass_snapshot:
        snap = json.loads(Path(require_pass_snapshot).read_text(encoding="utf-8"))
        if str(snap.get("捕获门")) != "PASS":
            return {"物料化": 0, "跳过": len(rows), "gate1_blocked": 0,
                    "拒绝": "轮次植株捕获门非 PASS——不许物料化"}

    qualifying, skipped = [], []
    gate1_blocked = 0
    for r in rows:
        rid = r["record_id"]
        rec = store._find(rid)
        if rec is None:
            skipped.append({"record_id": rid, "reason": "记录不在库"})
            continue
        eff = store.effective_status(rid)
        if eff == "confirmed":
            skipped.append({"record_id": rid, "reason": "已 confirmed（幂等跳过）"})
            continue
        if eff != "provisional":
            skipped.append({"record_id": rid, "reason": f"状态 {eff} 非 provisional"})
            continue
        v = gate1_fn(rec)
        votes = r.get("votes") or {}
        against = sum(1 for x in votes.values() if x == "against")
        dual = (votes.get("GLM") == "support" and votes.get("DEEPSEEK") == "support")
        if not dual or against > 0 or r.get("degraded"):
            # 防御性票门：引擎不信任调用方过滤——非双票一致/有 against/degraded 一律不物料化
            skipped.append({"record_id": rid, "reason": "非双票一致行（votes 不满足晋升语义）"})
            continue
        if v:
            gate1_blocked += 1
            skipped.append({"record_id": rid, "reason": f"gate1 违例 {str(v)[:80]}"})
            continue
        qualifying.append({"record_id": rid, "row": r})

    if dry_run:
        return {"dry_run": True, "qualifying": [q["record_id"] for q in qualifying],
                "物料化": len(qualifying), "跳过": len(skipped), "gate1_blocked": gate1_blocked}

    materialized = 0
    logf = Path(store_root) / "materialize-log.jsonl"
    done = []
    for q in qualifying:
        rid = q["record_id"]
        ent = store.status_transition(rid, "confirmed", by="promotion",
                                      note=f"批次5物料化 {tag}（双票一致∧零against∧gate1零违例）")
        done.append((rid, ent))
        materialized += 1
    with logf.open("a", encoding="utf-8") as f:
        for rid, ent in done:
            f.write(json.dumps({"record_id": rid, "round": tag, "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                                "transition": ent}, ensure_ascii=False, sort_keys=True) + "\n")
    return {"物料化": materialized, "跳过": len(skipped), "gate1_blocked": gate1_blocked,
            "台账": str(logf)}
