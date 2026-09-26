# -*- coding: utf-8 -*-
"""cbb2.contract — 契约 v3：profile 加载 + 断言/陈述位分类 + 时间位校验（U-A01）。

六库 profile 草案见 profiles/（_review 栏=待人工审定标记）。
分类保守序：unclassified → 按 immutable 处理（真矛盾走闸，绝不自动失效——R10 攻击面封堵）。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

PROFILE_DIR = Path(__file__).resolve().parent / "profiles"
PSEUDO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$|^ch\d{1,5}$", re.IGNORECASE)
_cache: dict = {}

KEYS = ("assertion_fields", "statement_fields", "mutable_assertions", "immutable_assertions")


def load_profile(library: str) -> dict:
    if library in _cache:
        return _cache[library]
    p = PROFILE_DIR / f"{library}.json"
    if not p.exists():
        raise KeyError(f"缺 profile: {library}（cbb2/profiles/{library}.json）")
    prof = json.loads(p.read_text(encoding="utf-8"))
    for k in KEYS:
        prof.setdefault(k, [])
    prof.setdefault("identity", {"entity": "name", "relation": "triple", "default": "record_id"})
    _cache[library] = prof
    return prof


def field_kind(profile: dict, field: str) -> str:
    """statement | mutable | immutable | unclassified。"""
    if field in profile["statement_fields"]:
        return "statement"
    if field in profile["mutable_assertions"]:
        return "mutable"
    if field in profile["immutable_assertions"]:
        return "immutable"
    if field in profile["assertion_fields"]:
        return "immutable"  # 声明为断言但未定可变性：保守按不可变
    return "unclassified"


def classify_conflicts(profile: dict, incoming: dict, stored: dict) -> list[dict]:
    """v3 比对域=双方 canonical 同键（扣除身份键 name）；返回 {field, kind, in, stored} 排序清单。"""
    ca, cb = incoming.get("canonical") or {}, stored.get("canonical") or {}
    out = []
    for k in sorted((set(ca) & set(cb)) - {"name"}):
        if ca[k] != cb[k]:
            out.append({"field": k, "kind": field_kind(profile, k), "in": ca[k], "stored": cb[k]})
    return out


def check_time_fields(record: dict, *, writing: bool) -> list[str]:
    """宽容读旧：读路径（writing=False）缺时间位不报错；写路径缺 at 报错（D-2/D-24，禁墙钟）。"""
    if not writing:
        return []
    if not record.get("at"):
        return ["缺 at（v3 写路径强制，伪锚点日历取值）——禁墙钟"]
    return []


def is_pseudo_date(v) -> bool:
    return bool(PSEUDO_RE.match(str(v)))
