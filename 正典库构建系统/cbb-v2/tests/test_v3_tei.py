# -*- coding: utf-8 -*-
"""test_v3_tei.py — G14 别名表 TEI schema + 亲属称谓内核。运行：py -X utf8 test_v3_tei.py"""
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from cbb2 import tei  # noqa: E402

NS = tei.TEI_NS
Q = lambda t: f"{{{NS}}}{t}"

# 真实在库形态样例（aliases.jsonl 2026-09-27 实测：str 形 534 条、dict 形 5 条，字段原样照录）
REAL_STR_ALIAS = {"alias": "基督", "entity_id": "cand-entity-0ae5575ed143",
                  "entity_type": "人物", "key": "基督|cand-entity-0ae5575ed143|人物"}
REAL_DICT_ALIAS = {"alias": {"confidence": 0.9, "kind": "proper_name", "name": "缇莉"},
                   "entity_id": "cand-entity-913913082231", "entity_type": "人物(魔法使)",
                   "key": "{'name': '缇莉', 'kind': 'proper_name', 'confidence': 0.9}|cand-entity-913913082231|人物(魔法使)"}
REGISTRY = {"cand-entity-0ae5575ed143": "基督·欧亚", "cand-entity-913913082231": "缇莉·略伦特"}


# ================= schema 正对照 =================

def test_valid_alias_parses_with_addname_nymref():
    xml = tei.to_tei([REAL_STR_ALIAS, REAL_DICT_ALIAS], REGISTRY)
    root = ET.fromstring(xml)  # 可被 xml.etree 解析
    assert root.tag == Q("TEI")
    persons = list(root.iter(Q("person")))
    assert len(persons) == 2
    # 规范名来自注册表（nymRef 指向规范名持有者）
    pers_names = [p.find(Q("persName")).text for p in persons]
    assert "基督·欧亚" in pers_names and "缇莉·略伦特" in pers_names
    addnames = list(root.iter(Q("addName")))
    assert {a.text for a in addnames} == {"基督", "缇莉"}
    for a in addnames:
        assert a.get("nymRef", "").startswith("#nym-cand-entity-")
    by_text = {a.text: a for a in addnames}
    assert by_text["基督"].get("nymRef") == "#nym-cand-entity-0ae5575ed143"
    assert by_text["缇莉"].get("nymRef") == "#nym-cand-entity-913913082231"


def test_dict_alias_maps_kind_to_type_and_confidence_to_cert():
    xml = tei.to_tei([REAL_DICT_ALIAS], REGISTRY)
    root = ET.fromstring(xml)
    a = next(root.iter(Q("addName")))
    assert a.get("type") == "proper_name"  # dict 形 kind → addName type
    assert a.get("cert") == "0.9"          # dict 形 confidence → cert


def test_attestation_empty_with_note_when_no_evidence():
    """真实字段无章回证据 ⇒ attestation 空元素 + 注记（工单 G14 口径）。"""
    xml = tei.to_tei([REAL_STR_ALIAS], REGISTRY)
    root = ET.fromstring(xml)
    a = next(root.iter(Q("addName")))
    att = a.find(Q("attestation"))
    assert att is not None and len(att) == 0  # 空元素
    note = a.find(Q("note"))
    assert note is not None and "无章回证据" in note.text


def test_attestation_bibl_when_evidence_present():
    """升级路径：记录带 evidence 字段时输出 bibl（首见章）。"""
    rec = dict(REAL_STR_ALIAS, evidence=[{"chapter": 14, "vol": 1}])
    xml = tei.to_tei([rec], REGISTRY)
    root = ET.fromstring(xml)
    att = next(root.iter(Q("attestation")))
    bibl = att.find(Q("bibl"))
    assert bibl is not None and bibl.text == "第14章"


# ================= schema 负对照（拒绝 + 原因码） =================

def test_invalid_aliases_rejected_with_reason_codes():
    bad_missing = {"entity_id": "e1", "entity_type": "人物"}
    bad_type = {"alias": 123, "entity_id": "e1", "entity_type": "人物"}
    bad_empty = {"alias": "   ", "entity_id": "e1", "entity_type": "人物"}
    bad_dict_no_name = {"alias": {"confidence": 0.9}, "entity_id": "e1", "entity_type": "人物"}
    bad_no_entity = {"alias": "无名氏", "entity_type": "人物"}
    built = tei.build_tei([bad_missing, bad_type, bad_empty, bad_dict_no_name, bad_no_entity], REGISTRY)
    reasons = [r["reason"] for r in built["rejected"]]
    assert reasons == [tei.REASON_ALIAS_MISSING, tei.REASON_ALIAS_TYPE, tei.REASON_ALIAS_EMPTY,
                       tei.REASON_ALIAS_EMPTY, tei.REASON_ENTITY_MISSING]
    assert built["stats"]["valid"] == 0 and built["stats"]["rejected"] == 5
    # 非法件不进 XML
    xml = tei.to_tei([bad_type], REGISTRY)
    assert "123" not in xml


# ================= 悬挂 nymRef（只注记，不删不改，不崩） =================

def test_hanging_nymref_notes_without_crash():
    lonely = {"alias": "雷迪安特", "entity_id": "cand-entity-c4d221e71ea0", "entity_type": "人物"}
    xml = tei.to_tei([lonely], {"别的id": "别人"})  # 注册表查无此 entity_id
    root = ET.fromstring(xml)  # 不崩、可解析
    p = next(root.iter(Q("person")))
    note = p.find(Q("note"))
    assert note is not None and note.get("type") == "hanging"
    assert "cand-entity-c4d221e71ea0" in note.text
    assert p.find(Q("persName")).text == "cand-entity-c4d221e71ea0"  # 占位不改写
    assert next(root.iter(Q("addName"))).get("nymRef") == "#nym-cand-entity-c4d221e71ea0"


# ================= 亲属称谓内核（gate1 表真实条目） =================

def test_gate1_tables_single_source():
    inv, sym = tei.gate1_tables()
    assert inv["parent"] == "child" and inv["child"] == "parent"
    assert inv["mentor"] == "student"
    assert "spouse" in sym and "sibling" in sym
    assert len(inv) == 12 and len(sym) == 12  # 12 对 + 12 项（连续性巡检口径）


def test_gate1_missing_raises_valueerror():
    """gate1 不可导入 ⇒ 显式 ValueError 不静默。须真实制造"不可导入"：
    清模块缓存 + 隔离 sys.path（finally 恢复，勿污染其他测试）。"""
    saved_path = list(sys.path)
    saved_mod = sys.modules.pop("cbb_gate1", None)
    try:
        sys.path[:] = [p for p in sys.path if "cbb-gate1" not in str(p)]
        try:
            tei.gate1_tables(base=HERE / "__不存在__gate1__")
        except ValueError as e:
            assert "cbb-gate1" in str(e)
        else:
            raise AssertionError("gate1 不可导入时应显式 ValueError，不得静默")
    finally:
        sys.path[:] = saved_path
        if saved_mod is not None:
            sys.modules["cbb_gate1"] = saved_mod
        tei._G1_CACHE.clear()  # 清缓存，让后续测试重走真实导入


def test_expand_kinship_inverse_one_hop():
    r = tei.expand_kinship([
        {"source": "基督·欧亚", "type": "parent", "target": "小基督"},
        {"source": "老师傅", "type": "mentor", "target": "基督·欧亚"},
    ])
    edges = {(e["source"], e["type"], e["target"]): e["origin"] for e in r["edges"]}
    assert edges[("小基督", "child", "基督·欧亚")] == "inverse"        # 父→子逆
    assert edges[("基督·欧亚", "student", "老师傅")] == "inverse"      # 师→徒逆
    assert r["counts"]["inverse"] == 2 and r["counts"]["symmetric"] == 0


def test_expand_kinship_symmetric_one_hop():
    r = tei.expand_kinship([
        {"source": "甲", "type": "spouse", "target": "乙"},
        {"source": "甲", "type": "sibling", "target": "乙"},
    ])
    edges = {(e["source"], e["type"], e["target"]): e["origin"] for e in r["edges"]}
    assert edges[("乙", "spouse", "甲")] == "symmetric"   # 夫妻对称
    assert edges[("乙", "sibling", "甲")] == "symmetric"  # 兄弟对称
    assert r["counts"]["output"] == 4


def test_expand_kinship_dedupes_preexisting_reverse():
    """输入已含反向边 ⇒ 去重不重复补。"""
    r = tei.expand_kinship([
        {"source": "甲", "type": "spouse", "target": "乙"},
        {"source": "乙", "type": "spouse", "target": "甲"},
    ])
    assert r["counts"]["output"] == 2


def test_expand_kinship_accepts_library_shape_and_passes_unknown():
    """在库形键（subject/rel_type/object）兼容；库内自由中文词表未命中 gate1 表
    ⇒ 原样保留不静默丢弃（实测 1544 种 rel_type 无一命中 gate1 英文词表）。"""
    r = tei.expand_kinship([
        {"subject": "相川涡波", "rel_type": "家人定位(视为妹妹)", "object": "玛利亚"},
        {"subject": "甲", "rel_type": "朋友", "object": "乙"},  # gate1 收 friend，不收"朋友"
    ])
    edges = {(e["source"], e["type"], e["target"]) for e in r["edges"]}
    assert ("相川涡波", "家人定位(视为妹妹)", "玛利亚") in edges
    assert ("甲", "朋友", "乙") in edges
    assert r["counts"]["unknown_type"] == 2  # 均未展开
    assert r["counts"]["output"] == 2


# ================= 库级导出（报告 + 样件 + 永不覆盖） =================

def _mini_store(root: Path):
    lib = root / "libraries" / "character" / "provisional"
    lib.mkdir(parents=True)
    (lib / "cand-entity-0ae5575ed143.json").write_text(
        json.dumps({"record_id": "cand-entity-0ae5575ed143",
                    "canonical": {"name": "基督·欧亚", "entity_type": "人物"}},
                   ensure_ascii=False), encoding="utf-8")
    (root / "aliases.jsonl").write_text(
        json.dumps(REAL_STR_ALIAS, ensure_ascii=False) + "\n" +
        json.dumps({"alias": "   ", "entity_id": "e1"}, ensure_ascii=False) + "\n", encoding="utf-8")


def test_export_store_writes_report_and_sample(tmp_path):
    store = tmp_path / "store"
    store.mkdir()
    _mini_store(store)
    r = tei.export_store(store, out_dir=store, sample_limit=50)
    assert (store / "G14-TEI样件.xml").exists() and (store / "G14-TEI别名报告.json").exists()
    report = json.loads((store / "G14-TEI别名报告.json").read_text(encoding="utf-8"))
    assert report["aliases总数"] == 2
    assert report["TEI导出样件字节数"] == r["xml_bytes"] > 0
    assert report["亲属表条目数"] == 24  # 12 对 + 12 项
    assert report["金标状态"] == "缺源【待确认】"  # 未提供 workdir ⇒ 缺源如实登记
    assert "生成时间" in report
    xml = (store / "G14-TEI样件.xml").read_text(encoding="utf-8")
    ET.fromstring(xml)
    assert "addName" in xml


def test_export_store_never_overwrites(tmp_path):
    store = tmp_path / "store"
    store.mkdir()
    _mini_store(store)
    tei.export_store(store, out_dir=store)
    try:
        tei.export_store(store, out_dir=store)
    except FileExistsError:
        pass
    else:
        raise AssertionError("目标已存在应抛 FileExistsError（铁律：永不覆盖）")


def test_export_store_gold_standard_integration(tmp_path):
    """集成：真实库 + 真实金标日志（读-only，产物写 tmp）。库不在时跳过。"""
    repo = HERE.parent.parent
    store = repo / "迷深实战-本体库"
    workdir = repo / "迷深实战-工作区"
    if not (store / "aliases.jsonl").exists() or not (workdir / "logs" / "graph-audit-20260925.json").exists():
        import pytest
        pytest.skip("真实库/金标日志不在本机")
    r = tei.export_store(store, workdir=workdir, out_dir=tmp_path, sample_limit=50)
    report = r["report"]
    assert report["aliases总数"] == 539
    assert report["亲属表条目数"] == 24
    assert report["金标状态"] == "65例金标在案"
    assert report["金标明细"]["计数"] == 65 and report["金标明细"]["名单样例数"] == 20
