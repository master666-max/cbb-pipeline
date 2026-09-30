# -*- coding: utf-8 -*-
"""cbb2.anchor_check — 实体锚定谓词·单一来源（收束期二批 C2/C3）。

所有锚定判定（回填件/gate1 E-ANCHOR-ENTITIES/巡检抽检）都 import 本模块，
禁止各处复制正则漂移。库分形谓词：
  character/setting → canonical.name 必须可在引文集锚定
  relation          → subject∧object
  event/foreshadow  → entities 全员（name 为标签型豁免——见预调研路 5/研讨报告 §2.2）
"""
from __future__ import annotations

import re

_DROP = re.compile(r"[『』「」\[\]（）()………\.\.\—─\-、，。？！?!：:；;\s\"\"''~～·　]")


def norm(s) -> str:
    return _DROP.sub("", str(s))


def norm_with_index(s: str):
    """规范化 + 原文下标映射（span 精确回落用）。"""
    out, idx = [], []
    for i, ch in enumerate(s):
        if _DROP.match(ch):
            continue
        out.append(ch)
        idx.append(i)
    return "".join(out), idx


def variants(k: str) -> set:
    """容错变体：全名/去双字姓/末二字/末三字（G14 调研路 5 的变体归一机械段）。
    单字符名（甲/乙类）变体集=自身——过滤成空集会把永远命中的判成永缺（负对照抓过）。"""
    vs = {k}
    if len(k) >= 4:
        vs.add(k[:-2])
    if len(k) >= 3:
        vs.add(k[-2:])
    if len(k) >= 4:
        vs.add(k[-3:])
    vs = {v for v in vs if len(v) >= 2}
    return vs or {k}


def anchor_keys(lib: str, canonical: dict) -> list:
    """库分形：返回必须可锚定的表面名 keys（标签型 name 不在其中）。"""
    if lib == "relation":
        return [norm(canonical.get(k, "")) for k in ("subject", "object") if canonical.get(k)]
    if lib in ("event", "foreshadow"):
        return [norm(e) for e in (canonical.get("entities") or [])]
    k = norm(canonical.get("name", ""))
    return [k] if k else []


def missing_keys(lib: str, canonical: dict, quotes_normed: str) -> list:
    return [k for k in anchor_keys(lib, canonical)
            if not any(v in quotes_normed for v in variants(k))]


def anchored(lib: str, canonical: dict, evidence: list) -> bool:
    quotes = norm("；".join(e.get("quote", "") for e in (evidence or [])))
    keys = anchor_keys(lib, canonical)
    return bool(keys) and not missing_keys(lib, canonical, quotes)


def check_anchor_entities(rec: dict) -> list:
    """gate1 E-ANCHOR-ENTITIES（warn 级）：候选断言实体在引文集零命中即告警。
    返回 warn 字典列表（不进 violations——不拦截，降置信语义在调用侧）。"""
    lib = rec.get("library") or ""
    c = rec.get("canonical") or {}
    quotes = norm("；".join(e.get("quote", "") for e in (rec.get("evidence") or [])))
    warns = []
    for k in missing_keys(lib, c, quotes):
        warns.append({"code": "E-ANCHOR-ENTITIES", "detail": f"实体 {k!r} 在引文集零命中",
                      "key": k})
    return warns


def check_relation_object_in_entities(rec: dict, entity_names: set) -> list:
    """C3 SHACL 固化：关系 object 应在实体表（名称级；变体容错）。
    entity_names=规范名集合（已 norm）。缺则 warn——实体可能后建，由调用侧定严级。"""
    if (rec.get("library") or "") != "relation":
        return []
    c = rec.get("canonical") or {}
    obj = norm(c.get("object", ""))
    if not obj:
        return []
    if any(v in entity_names for v in variants(obj)):
        return []
    return [{"code": "E-SHACL-OBJECT", "detail": f"关系 object {obj!r} 不在实体表"}]
