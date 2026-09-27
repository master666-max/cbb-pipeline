# -*- coding: utf-8 -*-
"""test_v3_c4_input_audit.py — 波C·C4：考官输入审计白名单 + 锚定谓词单源回归。
"""
import importlib.util
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

# g16c_rejudge 在仓库根，用 spec 加载（避免把根目录当包）
_spec = importlib.util.spec_from_file_location(
    "g16c_rejudge", HERE.parents[1] / "g16c_rejudge.py")
g16c = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(g16c)  # 模块自身会把 cbb-v2 插进 sys.path

from cbb2 import anchor_check as ac  # noqa: E402


def test_payload_whitelist_accepts_quotes_only():
    rec = {"canonical": {"name": "甲"}, "evidence": [{"quote": "甲来了。"}]}
    payload = g16c.build_payload(rec, [{"quote": "甲笑了笑。"}])
    assert set(payload) <= g16c.ALLOWED_PAYLOAD_KEYS
    assert payload["evidence_quotes"] == ["甲来了。", "甲笑了笑。"]


def test_payload_excludes_non_whitelisted_record_fields():
    rec = {"canonical": {"name": "甲"}, "evidence": [{"quote": "甲来了。"}],
           "neighbors": ["乙"], "edges": [{"s": "甲"}], "graph_context": {"x": 1}}
    payload = g16c.build_payload(rec, [])  # 野键构造性不可入载荷——白名单即防线
    assert set(payload) == {"canonical", "evidence_quotes"}


def test_variants_single_char_name_not_empty():
    assert ac.variants("甲") == {"甲"}  # 负对照抓过的空集永缺 bug


def test_missing_keys_tolerant_matching():
    c = {"subject": "相川涡波", "object": "玛利亚"}
    quotes = ac.norm("涡波对玛利亚点了点头")  # 去姓变体命中
    assert ac.missing_keys("relation", c, quotes) == []
    assert ac.missing_keys("relation", c, ac.norm("玛利亚独自离开")) == ["相川涡波"]


def test_shacl_object_in_entities():
    rec = {"library": "relation", "canonical": {"object": "乙"}}
    assert ac.check_relation_object_in_entities(rec, {ac.norm("乙")}) == []
    ws = ac.check_relation_object_in_entities(rec, {ac.norm("丙")})
    assert ws[0]["code"] == "E-SHACL-OBJECT"


def test_span_grounding_maps_back_to_raw():
    raw = "「我是从法尼亚过来的，您知道吗？」她说。"
    n, idx = ac.norm_with_index(raw)
    pos = n.find("法尼亚")
    assert pos >= 0
    seg = raw[idx[pos]:idx[pos + 2] + 1]
    assert seg == "法尼亚"  # 规范化下标精确回落原文
