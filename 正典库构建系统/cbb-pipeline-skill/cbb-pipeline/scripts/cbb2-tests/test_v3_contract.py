# -*- coding: utf-8 -*-
"""test_v3_contract.py — U-A01 profile 加载/字段分类/时间位校验。运行：py -X utf8 test_v3_contract.py"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from cbb2 import contract  # noqa: E402


def test_load_profile_ok_and_missing():
    p = contract.load_profile("character")
    assert p["assertion_fields"] and "status" in p["mutable_assertions"]
    try:
        contract.load_profile("no-such-lib")
        raise AssertionError("缺 profile 未拒")
    except KeyError:
        pass


def test_field_kind_four_way():
    p = contract.load_profile("character")
    assert contract.field_kind(p, "status") == "mutable"
    assert contract.field_kind(p, "entity_type") == "mutable"  # 实证：随剧情精化（U-A07 彩排）
    assert contract.field_kind(p, "unknown_field") == "unclassified"
    pe = contract.load_profile("event")
    assert contract.field_kind(pe, "kind") == "immutable"
    pr = contract.load_profile("relation")
    assert contract.field_kind(pr, "claim") == "statement"


def test_classify_conflicts_common_keys_sorted():
    pr = contract.load_profile("relation")
    a = {"canonical": {"subject": "卢卡", "rel_type": "同盟", "object": "缇达", "claim": "乙"}}
    b = {"canonical": {"subject": "卢卡", "rel_type": "同盟", "object": "缇达", "claim": "甲"}}
    out = contract.classify_conflicts(pr, a, b)
    assert [o["field"] for o in out] == ["claim"] and out[0]["kind"] == "statement"


def test_time_fields_lenient_read_strict_write():
    errs = contract.check_time_fields({"at": "ch0014", "t_valid": "ch0014"}, writing=True)
    assert errs == []
    assert contract.check_time_fields({}, writing=False) == []  # 宽容读旧
    errs = contract.check_time_fields({"t_valid": "ch0014"}, writing=True)
    assert errs and "at" in errs[0]


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"OK {fn.__name__}")
    print(f"{len(fns)} tests PASS")
