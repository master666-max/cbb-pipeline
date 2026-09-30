# -*- coding: utf-8 -*-
"""test_v3_phased.py — Phase D：票数晋升/对样双轨/植物捕获/缺口队列/ER 归一。
运行：py -X utf8 test_v3_phased.py"""
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from cbb2 import audit, er, gaps, plant, promote  # noqa: E402


class FakeExaminer:
    def __init__(self, kind, verdicts):
        self.kind = kind
        self.verdicts = verdicts  # [ev-first 结论, concl-first 结论]

    def __call__(self, conclusion, evidence, order="ev-first"):
        return self.verdicts[0] if order == "ev-first" else self.verdicts[1]


def test_vote_majority_and_swap_guard():
    panel = [FakeExaminer("L", ["support", "support"]),
             FakeExaminer("D", ["support", "support"]),
             FakeExaminer("Q", ["support", "support"])]
    r = promote.vote("断言", "证据", panel)
    assert r["verdict"] == "promote" and r["need"] == 2 and not r["degraded"]
    # 对调不一致 → unsure → 票面不齐 → hold（位置偏见纠偏生效）
    panel2 = [FakeExaminer("L", ["support", "unsure"]),
              FakeExaminer("D", ["support", "support"]),
              FakeExaminer("Q", ["support", "support"])]
    r2 = promote.vote("断言", "证据", panel2)
    assert r2["verdict"] == "promote" and r2["votes"]["L"] == "unsure"  # 摇摆票不计入，两干净票≥2/3


def test_vote_against_blocks_and_degrade():
    panel = [FakeExaminer("L", ["support", "support"]),
             FakeExaminer("D", ["against", "against"]),
             FakeExaminer("Q", ["support", "support"])]
    assert promote.vote("断言", "证据", panel)["verdict"] == "human"
    r = promote.vote("断言", "证据", [panel[0]])
    # B13 修复：需票按满编制算——单考官 support=1 < need=2 ⇒ hold（缩员不自动降门槛）
    assert r["verdict"] == "hold" and r["degraded"]


def test_promotion_check_gates():
    rec = {"canonical": {"name": "缇达"}, "evidence": [{"quote": "q"}]}
    panel = [FakeExaminer("L", ["support", "support"]), FakeExaminer("D", ["support", "support"])]
    assert promote.promotion_check(rec, panel, tenure_ok=False)["verdict"] == "hold"
    assert promote.promotion_check(rec, panel, tenure_ok=True, gate_clean=False)["verdict"] == "hold"
    assert promote.promotion_check(rec, panel, tenure_ok=True)["verdict"] == "promote"
    empty = promote.promotion_check({"canonical": {}, "evidence": []}, panel, tenure_ok=True)
    assert empty["verdict"] == "hold" and "证据为空" in empty["口径"]


def test_examiner_env_qwen_fallback():
    import os
    saved = {k: os.environ.get(k) for k in ("EXAMINER_QWEN_API_KEY", "DASHSCOPE_API_KEY",
                                            "EXAMINER_QWEN_BASE", "EXAMINER_QWEN_MODEL")}
    try:
        for k in saved:
            os.environ.pop(k, None)
        cfg = ops_env("QWEN")
        assert cfg["key"] == ""  # 全缺→空（BLOCKED），不硬编码
        os.environ["DASHSCOPE_API_KEY"] = "test-dummy"
        cfg = ops_env("QWEN")
        assert cfg["key"] == "test-dummy" and cfg["key_source"] == "DASHSCOPE_API_KEY"
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def ops_env(kind):
    from cbb2 import ops
    return ops.examiner_env(kind)


def test_audit_wilson_and_dual_track():
    lo, hi = audit.wilson(30, 30)
    assert 0.88 < lo < 0.90 and hi == 1.0  # 30 全过的 Wilson 下限 ≈0.887——远够不到 0.95 门槛
    rep = audit.report(20, 20, gate=0.95)
    assert rep["gate"] == "FAIL"  # 20/20 区间下限 ~0.85 不到 0.95
    recs = [{"record_id": f"r{i}", "provenance": {"extractor_confidence": 100 - i},
             "evidence": [{"quote": "x"}], "verified_against": {"sha": "a" * 7}}
            for i in range(10)]
    ranked = audit.suspicious_rank(recs)
    assert ranked[0]["record_id"] == "r9"  # 置信最低的最可疑
    strat = audit.stratified_sample(recs, lambda r: r["record_id"] < "r5", 2)
    assert len(strat) == 4
    lq = audit.lqas(passed=19, n=19, p0=0.95)
    assert lq["verdict"] == "accept"


def test_plant_capture_roundtrip():
    with tempfile.TemporaryDirectory() as td:
        plant.plant(Path(td), [{"name": "金标甲", "expect": {"entity_type": "人物(迷宫生物)"},
                                "source_chapter": 30}], at="ch0030")
        miss = plant.capture_rate(Path(td), [], chapter=30)
        assert miss["rate"] == 0.0 and len(miss["miss"]) == 1
        hit = plant.capture_rate(Path(td), [{"canonical": {"name": "金标甲", "entity_type": "人物(迷宫生物)"}}],
                                 chapter=30)
        assert hit["rate"] == 1.0


def test_gaps_foreshadow_and_vocab():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        fs = root / "libraries" / "foreshadow" / "provisional"
        fs.mkdir(parents=True)
        (fs / "f1.json").write_text(json.dumps(
            {"record_id": "f1", "canonical": {"name": "古剑伏笔", "setup_chapter": 5,
                                              "payoff_chapter": None}}, ensure_ascii=False), encoding="utf-8")
        qz = root / "quarantine-zone"
        qz.mkdir()
        (qz / "items.jsonl").write_text(json.dumps(
            {"item_id": "q-x", "subclass": "contradiction_pending",
             "detail": "entity_type: 入库='自创类' vs 库内='人物'"}, ensure_ascii=False), encoding="utf-8")
        rows = gaps.scan_foreshadow_overdue(root, current_chapter=20)
        assert rows and rows[0]["type"] == "契诃夫超期"
        vrows = gaps.scan_vocab_gaps(root)
        assert vrows and vrows[0]["type"] == "词表缺口"
        rows2 = gaps.scan_plant_miss(root, {"miss": [{"plant_id": "plant-1", "name": "金标甲"}]})
        assert rows2[0]["type"] == "植物miss"
        assert len(gaps.load_queue(root)) >= 3


def test_er_normalize_margin_and_merge_log():
    assert er.normalize_name("诺斯菲・弗茨亚茨（血族）") == "诺斯菲・弗茨亚茨"
    assert er.normalize_name("ｑｕｅｅｎ") == "queen"  # NFKC 全半角
    d = er.margin_decision({"人物(迷宫生物)": 0.91, "人物(传说)": 0.89}, min_margin=0.05)
    assert d["certain"] is False and d["target"] is None  # margin 不足→人审
    with tempfile.TemporaryDirectory() as td:
        ml = er.MergeLog(Path(td))
        ml.merge("诺斯菲", "诺斯菲丽德", rule="stored-vocab", confidence=0.9, at="ch0010")
        assert ml.resolve("诺斯菲丽德") == "诺斯菲"
        ml.split("诺斯菲丽德", at="ch0011", note="对样判定误并")
        assert ml.resolve("诺斯菲丽德") == "诺斯菲丽德"  # 拆分回滚是一等公民
        g = ml.groups()
        assert "诺斯菲" in g and "诺斯菲丽德" not in g.get("诺斯菲", [])


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"OK {fn.__name__}")
    print(f"{len(fns)} tests PASS")
