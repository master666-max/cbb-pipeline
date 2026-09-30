# -*- coding: utf-8 -*-
"""test_v3_governance.py — Phase F·G08-G15 治理闭环测试。"""
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from cbb2 import governance  # noqa: E402


def test_classify_manual_bucket():
    items = [
        {"detail": "嵌入相似度存疑 0.88"},
        {"detail": ""},
        {"detail": "entity_type: 入库='人物' vs 库内='组织'"},
        {"detail": "嵌入相似度 0.92"},
    ]
    r = governance.classify_manual_bucket(items)
    assert len(r["artifact"]) == 2 and len(r["empty_claim"]) == 1 and len(r["unknown"]) == 1


def test_conformal_calibrate_and_predict():
    cal = governance.ConformalNLICalibrator(alpha=0.1)
    labeled = [{"predicted": "contradicts", "label": "contradicts", "score": 0.9} for _ in range(6)] + \
              [{"predicted": "neutral", "label": "entails", "score": 0.3} for _ in range(4)]
    r = cal.calibrate(labeled)
    assert r["n"] == 10 and r["threshold"] > 0
    # 高分正确→采纳
    p1 = cal.predict(0.95, "contradicts")
    assert not p1["abstain"]
    # 低分→弃权
    p2 = cal.predict(0.05, "contradicts")
    assert p2["abstain"]


def test_examiner_quality_tracking():
    tr = governance.ExaminerQualityTracker()
    tr.record("good", True)
    tr.record("good", True)
    tr.record("bad", False)
    assert tr.quality("good") > tr.quality("bad")
    assert tr.quality("unknown") == 0.5  # 无数据=中性
    assert tr.all_quality()["good"] == 1.0


def test_wire_gap_queue_idempotent():
    with tempfile.TemporaryDirectory() as td:
        findings = [{"type": "词表缺口", "evidence": "q-x", "proposed_action": "升级"}]
        n1 = governance.wire_gap_queue(Path(td), findings)
        n2 = governance.wire_gap_queue(Path(td), findings)
        assert n1 == 1 and n2 == 0  # 幂等
        q = Path(td) / "缺口队列.jsonl"
        assert len(q.read_text(encoding="utf-8").splitlines()) == 1


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"OK {fn.__name__}")
    print(f"{len(fns)} tests PASS")
