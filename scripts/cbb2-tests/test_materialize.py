# -*- coding: utf-8 -*-
"""test_materialize.py — 批次 5·物料化晋升执行（store 正门 status_transition 通道）。"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from cbb2 import materialize  # noqa: E402
from cbb2.store import Store  # noqa: E402


def _rec(rid: str, name: str, evidence=True) -> dict:
    ev = [{"vol": 1, "chapter": 3, "line": 10, "quote": f"{name}的引文。"}] if evidence else []
    return {"record_id": rid, "library": "character", "status": "provisional",
            "canonical": {"name": name, "entity_type": "人物", "fact": f"{name}设定"},
            "evidence": ev, "_aliases": [], "observations": []}


def _row(rid: str, verdict="promote", g="support", d="support", degraded=False) -> dict:
    votes = {"GLM": g, "DEEPSEEK": d}
    return {"record_id": rid, "verdict": verdict, "votes": votes, "need": 2,
            "against": sum(1 for v in votes.values() if v == "against"),
            "degraded": degraded, "is_plant": False}


def _seed(tmp: Path) -> tuple[Store, dict]:
    store = Store(tmp / "store")
    recs = {"cand-ok-1": _rec("cand-ok-1", "甲"),
            "cand-ok-2": _rec("cand-ok-2", "乙"),
            "cand-hold": _rec("cand-hold", "丙"),
            "cand-noev": _rec("cand-noev", "丁", evidence=False)}
    for rid, rec in recs.items():
        lib = rec["library"]
        d = store.root / "libraries" / lib / "provisional"
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{rid}.json").write_text(json.dumps(rec, ensure_ascii=False, sort_keys=True, indent=1),
                                       encoding="utf-8")
    rows = [_row("cand-ok-1"), _row("cand-ok-2"),
            _row("cand-hold", verdict="hold", g="support", d="unsure"),
            _row("cand-noev")]                       # 无证据件：gate1 应拦
    return store, {"recs": recs, "rows": rows}


def test_materialize_round(tmp_path):
    store, fx = _seed(tmp_path)

    def fake_gate1(rec):
        return [] if rec.get("evidence") else ["缺证据"]

    r = materialize.materialize_round(store_root=tmp_path / "store", rows=fx["rows"],
                                      tag="v22-50件验证轮", dry_run=True, gate1_fn=fake_gate1)
    assert r["dry_run"] is True and len(r["qualifying"]) == 2          # ok-1/ok-2

    r = materialize.materialize_round(store_root=tmp_path / "store", rows=fx["rows"],
                                      tag="v22-50件验证轮", dry_run=False, gate1_fn=fake_gate1)
    assert r["物料化"] == 2 and r["跳过"] == 2
    assert store.effective_status("cand-ok-1") == "confirmed"
    assert store.effective_status("cand-ok-2") == "confirmed"
    assert store.effective_status("cand-hold") == "provisional"        # hold 不动
    assert store.effective_status("cand-noev") == "provisional"        # gate1 拦截不动
    # R13 旁车日志：transitions.jsonl 有 promotion 记录
    tr = (tmp_path / "store" / "transitions.jsonl").read_text(encoding="utf-8").splitlines()
    entries = [json.loads(l) for l in tr if l.strip()]
    assert all(e["by"] == "promotion" and e["to"] == "confirmed" for e in entries)
    assert len(entries) == 2
    # 幂等重跑：已 confirmed 不重复迁移
    r2 = materialize.materialize_round(store_root=tmp_path / "store", rows=fx["rows"],
                                       tag="v22-50件验证轮", dry_run=False, gate1_fn=fake_gate1)
    assert r2["物料化"] == 0
