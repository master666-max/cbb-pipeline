# -*- coding: utf-8 -*-
"""test_ingest_diff.py — 批次 4·增量检测：new/changed/unchanged 三态与幂等。"""
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from cbb2 import extraction  # noqa: E402

MARKER = "^<<<CHAPTER (\\d{4}) \\| (.*?)>>>(?:\\s*\\[([A-Z]+:[^\\]]+)\\])?\\s*$"


def make_book(tmp: Path, chapters: dict[int, list[str]]):
    """chapters: {章号: [正文行]}。marker 行=第 1 行（迷深格式）。返回 config。"""
    lines = []
    for no in sorted(chapters):
        lines.append(f"<<<CHAPTER {no:04d} | 第{no}章>>>")
        lines.extend(chapters[no])
    (tmp / "corpus").mkdir(parents=True, exist_ok=True)
    (tmp / "corpus" / "full.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    raw = {"version": "1.0", "book": "测试书",
           "corpus": {"path": "corpus/full.txt"},
           "boundary_file": "boundary.json",
           "chapter_marker_regex": MARKER,
           "store_root": "store", "work_dir": "work", "panel_concurrency": 3,
           "plants": {"pairs": 2, "seed": 7}, "batch": {"chunk": 10},
           "gate": {"correct_min": 3, "capture_min": 0.8334}}
    p = tmp / "extraction.config.json"
    p.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    return extraction.load_config(p)


def body_sha(chapters: dict[int, list[str]], no: int) -> str:
    # 与引擎切片同口径：body 含 CHAPTER 标记行本身（marker_line-1 起切）
    body = "\n".join([f"<<<CHAPTER {no:04d} | 第{no}章>>>"] + chapters[no])
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def test_three_states(tmp_path):
    chapters = {1: ["一章正文甲。", "一章正文乙。"], 2: ["二章正文。"], 3: ["三章正文。"]}
    cfg = make_book(tmp_path, chapters)
    r = extraction.ingest_diff(cfg, state={})
    assert len(r["new"]) == 3 and r["changed"] == [] and r["unchanged"] == 0
    assert [c["chapter_no"] for c in r["new"]] == [1, 2, 3]
    assert (tmp_path / "boundary.json").exists()      # 边界表已刷新


def test_changed_detected(tmp_path):
    chapters = {1: ["一章正文甲。", "一章正文乙。"], 2: ["二章正文。"], 3: ["三章正文。"]}
    cfg = make_book(tmp_path, chapters)
    state = {"1": {"sha": body_sha(chapters, 1)},                 # 未变
             "2": {"sha": "0" * 64},                              # 已变（错哈希=模拟内容修订）
             "3": {"sha": body_sha(chapters, 3)}}                 # 未变
    r = extraction.ingest_diff(cfg, state=state)
    assert r["changed"] and r["changed"][0]["chapter_no"] == 2
    assert r["unchanged"] == 2 and len(r["new"]) == 0


def test_boundary_refresh_picks_new_chapter(tmp_path):
    chapters = {1: ["一章正文。"], 4: ["四章正文。"]}
    cfg = make_book(tmp_path, chapters)
    r1 = extraction.ingest_diff(cfg, state={})
    assert sorted(c["chapter_no"] for c in r1["new"]) == [1, 4]
    # 语料追加第 2 章 → 边界表刷新后可见
    corpus = cfg.corpus
    lines = corpus.read_text(encoding="utf-8").splitlines()
    lines.insert(2, "<<<CHAPTER 0002 | 第2章>>>")
    lines.insert(3, "二章正文。")
    corpus.write_text("\n".join(lines) + "\n", encoding="utf-8")
    r2 = extraction.ingest_diff(cfg, state={})
    nos = sorted(c["chapter_no"] for c in r2["new"])
    assert nos == [1, 2, 4], nos
