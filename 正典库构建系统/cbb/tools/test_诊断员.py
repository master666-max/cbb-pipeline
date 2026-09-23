# -*- coding: utf-8 -*-
"""test_诊断员.py — U-F08 测试：量尺执行＋红区隔离＋C2 升级闸"""
import importlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
诊 = importlib.import_module("诊断员")

ANOMALY = {"rule": "density_low", "detail": "密度脱带：连续 3 批候选密度低于下带", "backend": "file"}
SAMPLES = [{"record_id": f"r{i}", "text": f"样本 {i} 的内容"} for i in range(40)]  # 40>30 触发截断


def test_prepare_truncates_to_30_with_flag(tmp_path):
    pkg = 诊.prepare(ANOMALY, SAMPLES, today="2026-09-23")
    assert pkg["sample_count"] == 30 and pkg["truncated"] is True  # B2 量尺
    assert pkg["量尺"]["费"] == "≤8K/次" and pkg["量尺"]["色"].startswith("黄")  # D2/裁定


def test_c2_gate_initial_then_escalation(tmp_path):
    log = tmp_path / "decision-log.jsonl"
    pkg = 诊.prepare(ANOMALY, SAMPLES, today="2026-09-23")
    诊.record_decision(log, pkg, "归因：对话章占比高（合法波动），非引擎退化", [])
    # 复诊未确认 → 拒（C2 人工闸）
    try:
        诊.prepare(ANOMALY, SAMPLES, escalation=True, prior_packages=诊.prior_packages(log))
        raise AssertionError("未确认就升级应拒")
    except ValueError as e:
        assert "人工闸" in str(e)
    # 确认后 → 允许升级
    诊.confirm(log, pkg["package_id"], by="human", note="归因成立，复诊验证")
    pkg2 = 诊.prepare(ANOMALY, SAMPLES, escalation=True,
                      prior_packages=诊.prior_packages(log), today="2026-09-24")
    assert pkg2["escalation"] is True
    # 再升级 → 超限拒（每异常最多 1+1 批）
    诊.record_decision(log, pkg2, "复诊：归因维持", [])
    try:
        诊.prepare(ANOMALY, SAMPLES, escalation=True, prior_packages=诊.prior_packages(log))
        raise AssertionError("第三次诊断应拒")
    except ValueError as e:
        assert "超限" in str(e)


def test_red_zone_proposals_rejected():
    """红区隔离：越权建议必须被拒（机械闸），不得入账。"""
    for bad in ["建议直接宣布验收通过", "把该记录晋升为 confirmed", "修改契约 schema"]:
        try:
            诊.validate_attribution("归因", [bad])
            raise AssertionError(f"越权建议未被拒: {bad}")
        except ValueError as e:
            assert "红区" in str(e)


def test_record_decision_appends_and_references(tmp_path):
    log = tmp_path / "decision-log.jsonl"
    pkg = 诊.prepare(ANOMALY, SAMPLES, today="2026-09-23")
    e1 = 诊.record_decision(log, pkg, "归因：纯对话章聚集", ["建议下调本批探针频率"])
    lines = [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(lines) == 1 and lines[0]["type"] == "diagnosis"
    assert lines[0]["sample_refs"] == [s["record_id"] for s in pkg["samples"]][:30]  # 样本引用可核
    assert lines[0]["status"] == "待人工确认"  # 黄区：提案制，人确认才生效
    _ = e1


if __name__ == "__main__":
    import tempfile
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        if fn.__code__.co_argcount:
            with tempfile.TemporaryDirectory() as td:
                fn(Path(td))
        else:
            fn()
        print(f"OK {fn.__name__}")
    print(f"{len(fns)} tests PASS")
