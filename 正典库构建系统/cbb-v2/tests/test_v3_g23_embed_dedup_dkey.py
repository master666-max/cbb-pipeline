# -*- coding: utf-8 -*-
"""test_v3_g23_embed_dedup_dkey.py — G23 embed_dedup_scan 字段归一（D-10）。
运行：py -X utf8 -m pytest cbb-v2/tests/test_v3_g23_embed_dedup_dkey.py -q
判据：非空候选断言——候选/库内记录只带 `type`（无 record_type）也能入扫描面。
"""
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "cbb" / "tools"))

import embed_dedup_scan as eds  # noqa: E402 — v1 生产工具（cbb/tools/）


def _store_with(tmp: Path, rec: dict) -> Path:
    store = tmp / "store"
    lib = store / "libraries" / "character" / "provisional"
    lib.mkdir(parents=True)
    (lib / "r1.json").write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
    return store


def test_g23_type_key_candidate_nonempty():
    """非空候选断言：候选只带 type=entity → 仍进扫描面（D-10 反例转绿）。"""
    cands = {"candidates": [{"type": "entity", "canonical": {"name": "缇妠"}}]}
    with tempfile.TemporaryDirectory() as td:
        cand, lib = eds.collect_entity_names(cands, _store_with(Path(td), {"type": "entity"}))
    assert cand == ["缇妠"]          # 判据：非空候选


def test_g23_type_key_library_and_alias():
    """库侧只带 type 的记录也收；别名表照旧。"""
    cands = {"candidates": [{"record_type": "entity", "canonical": {"name": "缇亚"}}]}
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        store = _store_with(tmp, {"type": "entity", "canonical": {"name": "缇妠"}})
        (store / "aliases.jsonl").write_text(
            json.dumps({"alias": "妲", "entity_id": "r1"}, ensure_ascii=False), encoding="utf-8")
        cand, lib = eds.collect_entity_names(cands, store)
    assert cand == ["缇亚"]
    assert {"缇妠", "妲"} <= set(lib)


def test_g23_record_type_still_wins():
    """主键优先：record_type 与 type 冲突时以 record_type 为准，不误收。"""
    cands = {"candidates": [{"record_type": "relation", "type": "entity",
                             "canonical": {"name": "假实体"}}]}
    with tempfile.TemporaryDirectory() as td:
        cand, _ = eds.collect_entity_names(cands, Path(td))
    assert cand == []


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"OK {fn.__name__}")
    print(f"{len(fns)} tests PASS")
