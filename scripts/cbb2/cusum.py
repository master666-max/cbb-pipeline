# -*- coding: utf-8 -*-
"""cbb2.cusum — 批次 7·改判率 CUSUM 监控（G17 巡检圈常设哨）。

标准单向 CUSUM（上偏检测）：改判率 p 相对基线 p0 的正偏累计——
  S_0 = 0；S_t = max(0, S_{t-1} + (p_t - p0) - k)   （k=容许松弛，默认 0.002）
  S_t ≥ h ⇒ 告警（改判率显著高于基线=库在漂移）。
判读纪律（R-021）：告警=触发人工复验，不自动改判。
"""
from __future__ import annotations


def cusum_series(points: list[float], p0: float, k: float = 0.002,
                 h: float = 0.05) -> dict:
    """单向 CUSUM 序列（上偏）。points=按时间的改判率观测；返回序列/峰值/是否越限。
    p0 基线、k 松弛、h 告警阈——三者均须显式传入（预注册纪律）。"""
    if not 0 < p0 < 1:
        raise ValueError(f"p0 须在 (0,1)：{p0}")
    s = 0.0
    series = []
    for p in points:
        s = max(0.0, s + (p - p0) - k)
        series.append(round(s, 6))
    return {"series": series, "peak": round(max(series), 6),
            "越限": any(x >= h for x in series), "h": h}


def cusum_verdict(series: list[float], h: float) -> dict:
    """序列终判：peak ≥ h ⇒ 漂移告警（人工复验触发）。"""
    peak = max(series) if series else 0.0
    return {"peak": round(peak, 6), "h": h, "告警": peak >= h}


def feed_circle(rate: float, p0: float, k: float = 0.002, h: float = 0.05) -> dict:
    """单圈读数便捷口：给一圈改判率，返回该点 CUSUM 累计值与是否告警。"""
    s = cusum_series([rate], p0=p0, k=k, h=h)
    return {"改判率": rate, "累计偏移": s["series"][-1], "告警": s["越限"]}
