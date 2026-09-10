# -*- coding: utf-8 -*-
"""Cfg2 轻量副本（与自演化离线实验 proto/evolve20.Cfg2 同构，避免全量依赖）"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Cfg2:
    w_kw: float = 3.0
    w_content: float = 1.0
    w_imp: float = 1.0
    w_age: float = 0.1
    w_len: float = 0.0
    w_fmt: float = 0.0
    w_den: float = 0.0
    w_cit: float = 0.0
    filter_zero: int = 0
    deep: int = 0
