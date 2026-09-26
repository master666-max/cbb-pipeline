# -*- coding: utf-8 -*-
"""test_v3_ops_nli.py — U-A04 运行契约闸四条件 + NLI 双通道（mock 通道，零网络）。
运行：py -X utf8 test_v3_ops_nli.py"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from cbb2 import nli, ops  # noqa: E402


class FakeChannel:
    name = "fake"

    def __init__(self, verdict=None, unavailable=False):
        self.verdict = verdict
        self.unavailable = unavailable

    def available(self):
        return not self.unavailable

    def judge(self, premise, hypothesis):
        if self.unavailable:
            raise nli.ChannelUnavailable("fake 不可用")
        return self.verdict


def test_gate_four_conditions_and_selftest():
    g = ops.capability_gate("embed", endpoint_alive=True, artifact_exists=True,
                            wired=True, receipt_present=True)
    assert g["state"] == "READY" and g["missing"] == []
    g2 = ops.capability_gate("embed", endpoint_alive=True, artifact_exists=False,
                             wired=False, receipt_present=False)
    assert g2["state"] == "BLOCKED" and g2["missing"] == ["artifact_exists", "wired", "receipt_present"]
    st = ops.selftest()
    assert st["ok"], "哨兵自检不过=闸不会响，数据作废"


def test_dual_judge_agree_disagree_degrade():
    a = FakeChannel("contradicts")
    b = FakeChannel("contradicts")
    r = nli.dual_judge("前提", "假设", [a, b])
    assert r["verdict"] == "contradicts" and r["agree"] and not r["human_queue"]
    c = FakeChannel("neutral")
    r2 = nli.dual_judge("前提", "假设", [a, c])
    assert r2["verdict"] is None and r2["human_queue"]  # 不一致才人审
    r3 = nli.dual_judge("前提", "假设", [FakeChannel(unavailable=True), FakeChannel("entails")])
    assert r3["degraded"] and r3["verdict"] == "entails" and r3["unavailable"]


def test_dual_judge_all_unavailable_blocks():
    r = nli.dual_judge("前提", "假设", [FakeChannel(unavailable=True), FakeChannel(unavailable=True)])
    assert r["verdict"] is None and r["degraded"] and r["human_queue"]


def test_exam_separation_threshold_and_calibration():
    cases = [{"premise": "p", "hypothesis": "h", "label": "contradicts"}] * 8 + \
            [{"premise": "p", "hypothesis": "h", "label": "entails"}] * 2

    def good(p, h):
        return ("contradicts", 0.93)  # 8/10 对，置信 0.93 全落同一桶

    rep = nli.exam(good, cases)
    assert rep["separation"] == 0.8 and rep["pass"]
    assert rep["calibration"]["0.9"]["n"] == 10 and rep["calibration"]["0.9"]["accuracy"] == 0.8

    def bad(p, h):
        return ("entails", None)  # 2/10 对且无置信 → uncalibrated 桶

    rep2 = nli.exam(bad, cases)
    assert not rep2["pass"] and rep2["separation"] == 0.2
    assert "uncalibrated" in rep2["calibration"]


def test_llm_channel_unavailable_raises_not_crash():
    ch = nli.LLMChannel(base="", model="")
    assert not ch.available()
    try:
        ch.judge("p", "h")
        raise AssertionError("未配置通道应 raise ChannelUnavailable")
    except nli.ChannelUnavailable:
        pass


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"OK {fn.__name__}")
    print(f"{len(fns)} tests PASS")
