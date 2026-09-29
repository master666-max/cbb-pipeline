# -*- coding: utf-8 -*-
"""test_extraction_config.py — 批次 2·V1 抽取配置层：加载/校验/路径解析/R-030 值携带。"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from cbb2 import extraction  # noqa: E402

BASE = {"version": "1.0", "book": "测试书",
        "corpus": {"path": "corpus/full.txt"},
        "store_root": "store", "work_dir": "work", "panel_concurrency": 3}


def _write(tmp: Path, raw: dict):
    (tmp / "corpus").mkdir(exist_ok=True)
    p = tmp / "extraction.config.json"
    p.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    return p


def test_load_ok_and_resolution(tmp_path):
    p = _write(tmp_path, dict(BASE))
    cfg = extraction.load_config(p)
    assert cfg.book == "测试书"
    assert cfg.corpus == tmp_path / "corpus" / "full.txt"
    assert cfg.store_root == tmp_path / "store"
    assert cfg.concurrency == 3 and cfg.anchor_check is True


def test_optional_files_none_when_absent(tmp_path):
    p = _write(tmp_path, dict(BASE))
    cfg = extraction.load_config(p)
    assert cfg.vocab_file is None and cfg.precedent_file is None


def test_missing_required_rejected(tmp_path):
    bad = {k: v for k, v in BASE.items() if k != "corpus"}
    p = _write(tmp_path, bad)
    try:
        extraction.load_config(p)
        assert False, "缺 corpus 应抛错"
    except ValueError as e:
        assert "corpus" in str(e)


def test_bad_concurrency_rejected(tmp_path):
    bad = dict(BASE, panel_concurrency=0)
    p = _write(tmp_path, bad)
    try:
        extraction.load_config(p)
        assert False, "并发 0 应抛错"
    except ValueError as e:
        assert "并发" in str(e)


def test_r030_types_carried_not_judged(tmp_path):
    raw = dict(BASE, types={"libraries": ["character"], "_note": "彩排校准后值"})
    p = _write(tmp_path, raw)
    cfg = extraction.load_config(p)
    assert cfg.types["libraries"] == ["character"]   # 值原样携带——校准是 V4 夹具的事，加载器不判值
