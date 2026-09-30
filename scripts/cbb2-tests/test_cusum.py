# -*- coding: utf-8 -*-
"""test_cusum.py — 批次 7·改判率 CUSUM 监控：序列/峰值/越限三态。"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from cbb2 import cusum  # noqa: E402


def test_stable_series_stays_zero():
    r = cusum.cusum_series([0.02, 0.02, 0.02], p0=0.02, k=0.002, h=0.05)
    assert all(x == 0.0 for x in r["series"]) and not r["越限"]


def test_sustained_drift_trips():
    r = cusum.cusum_series([0.05, 0.05, 0.05], p0=0.02, k=0.002, h=0.05)
    assert r["越限"] and r["peak"] > 0


def test_single_spike_recovers():
    # 单点尖峰 0.04（一步累计 +0.018 < h=0.05）：瞬时波动不告警，回落归零
    r = cusum.cusum_series([0.02, 0.045, 0.02, 0.02], p0=0.02, k=0.002, h=0.05)
    assert not r["越限"]
    # 对照：单点大幅尖峰 0.09（一步 +0.068）应触发——告警系统对大幅突变的灵敏度
    r2 = cusum.cusum_series([0.02, 0.09, 0.02, 0.02], p0=0.02, k=0.002, h=0.05)
    assert r2["越限"], "大幅尖峰应触发（告警系统灵敏度自检）"


def test_p0_validation():
    try:
        cusum.cusum_series([0.5], p0=1.5, k=0.002, h=0.05)
        assert False, "p0 越界应抛错"
    except ValueError:
        pass


def test_feed_circle_convenience():
    r = cusum.feed_circle(rate=0.45, p0=0.02, k=0.002, h=0.05)
    assert "改判率" in r and "累计偏移" in r and "告警" in r
