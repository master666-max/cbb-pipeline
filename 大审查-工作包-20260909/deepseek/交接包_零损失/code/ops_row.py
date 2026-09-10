# -*- coding: utf-8 -*-
"""ops_row.py — 行层算子提案器(append-only; quick 档未启用, 预留给 dup-drift 消融)

能力边界: 引擎只能经 b3 公开写函数 append/retire 落盘; 算子提案 = 新条目/链接/失效,
绝不 in-place 改写既有文件(铁律1/S3)。
"""


def propose_link_graft(rng, entries, topic, gen):
    """同组首领与其副本间的补链提案(本骨架返回空; 需 usage 轨迹支撑时启用)"""
    return []


def propose_merge(entries, topic, gen, thr=0.7):
    """把同主题内 content 高重叠(近似重复)的成员折叠提案(仅 dup-drift 场景有意义)"""
    proposals = []
    return proposals
