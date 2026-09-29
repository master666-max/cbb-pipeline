# -*- coding: utf-8 -*-
"""test_v3_g24_boundary_count.py — G24 数章权威：init_project 章数=边界表（D-9 收口判据）。
判据：517 章边界表与计数值一致（真表 smoke）+ 表内自洽校验 + legacy/回落路径注记。
"""
import importlib
import io
import json
import sys
import tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

SCRIPTS = HERE.parents[1] / "cbb-pipeline-skill" / "cbb-pipeline" / "scripts"
sys.path.insert(0, str(SCRIPTS))
pytest.importorskip("yaml")
init_project = importlib.import_module("init_project")


def _mk_src(tmp, markers=5, prose_trap=True):
    p = Path(tmp) / "clean.txt"
    lines = [f"<<<CHAPTER {i}>>>" for i in range(markers)]
    if prose_trap:
        lines.append("他想起书中那行『<<<CHAPTER』的排版记号，不觉失笑。")  # D-9 误计源
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(p)


def test_boundary_table_is_authoritative():
    with tempfile.TemporaryDirectory() as td:
        src = _mk_src(td, markers=5)
        tbl = Path(td) / "boundary-table-v1.json"
        tbl.write_text(json.dumps({"chapter_count": 517,
                                   "chapters": [{"no": i} for i in range(517)]}),
                       encoding="utf-8")
        n, note = init_project.chapter_count_of(src, td, boundary=str(tbl))
        assert n == 517 and "边界表" in note


def test_inconsistent_table_rejected():
    with tempfile.TemporaryDirectory() as td:
        src = _mk_src(td, markers=5)
        tbl = Path(td) / "bad.json"
        tbl.write_text(json.dumps({"chapter_count": 3,
                                   "chapters": [{"no": i} for i in range(5)]}),
                       encoding="utf-8")
        with pytest.raises(SystemExit, match="自相矛盾"):
            init_project.chapter_count_of(src, td, boundary=str(tbl))


def test_fallback_and_legacy_annotate_non_authoritative():
    with tempfile.TemporaryDirectory() as td:
        src = _mk_src(td, markers=5)  # 含 1 处正文陷阱——标记口径会误计为 6
        n_fb, note_fb = init_project.chapter_count_of(src, td, boundary=None)
        assert n_fb == 6 and "非权威" in note_fb  # 误计如实发生+注记声明非权威
        n_lg, note_lg = init_project.chapter_count_of(src, td, legacy=True)
        assert n_lg == 6 and "--legacy" in note_lg


def test_real_boundary_table_517():
    tbl = HERE.parents[1] / "迷深实战-工作区" / "manifest" / "boundary-table-v1.json"
    if not tbl.exists():
        pytest.skip("真库边界表不在本机")
    data = json.loads(tbl.read_text(encoding="utf-8"))
    assert int(data["chapter_count"]) == 517
    chapters = data.get("chapters")
    if isinstance(chapters, list):
        assert len(chapters) == 517  # 表内自洽=判据原文
