# -*- coding: utf-8 -*-
"""test_批次自检.py — 十项断言的正负对照（栽好的问题必须被抓，干净的必须全绿）"""
import importlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
自检 = importlib.import_module("批次自检")


def _mk(ws: Path, store: Path, *, quote_ok: bool, wallclock: bool, meta: bool,
        bad_va: bool, ghost_chapter: bool):
    ws.mkdir(parents=True, exist_ok=True)
    (ws / "candidates").mkdir(exist_ok=True)
    (ws / "slice").mkdir(exist_ok=True)
    chs = [1, 2, 99] if ghost_chapter else [1, 2]
    for ch in chs:
        quote = "甲说：今天天气不错。" if quote_ok else "这句引文切片里根本没有。"
        extras = []
        if wallclock:
            extras.append({"note": "2026-01-01 收录"})
        if meta:
            extras.append({"note": "求月票！"})
        cand = {"_meta": {"source": "t"}, "candidates": [
            {"record_id": f"e-{ch}", "record_type": "entity",
             "evidence": [{"vol": 1, "chapter": ch, "line": 1, "quote": quote}]}]}
        cand.update({"extras": extras})
        (ws / "candidates" / f"extraction-ch{ch:04d}.json").write_text(
            json.dumps(cand, ensure_ascii=False), encoding="utf-8")
        (ws / "slice" / f"ch{ch:04d}.txt").write_text("甲说：今天天气不错。\n乙说：是啊。", encoding="utf-8")
    store.mkdir(parents=True, exist_ok=True)
    rec = {"record_id": "e-1", "record_type": "entity", "library": "character",
           "canonical": {"name": "甲"}, "version": 1, "supersedes": None,
           "evidence": [{"vol": 1, "chapter": 1, "line": 1, "quote": "甲说：今天天气不错。"}]}
    if not bad_va:
        rec["verified_against"] = {"path": "t", "sha": "a" * 8, "verified_at": "1970-01-01"}
    (store / "libraries" / "character" / "provisional").mkdir(parents=True, exist_ok=True)
    (store / "libraries" / "character" / "provisional" / "e-1.json").write_text(
        json.dumps(rec, ensure_ascii=False), encoding="utf-8")
    (store / "ledger.jsonl").write_text(
        json.dumps({"seq": 5, "op": "append"}, ensure_ascii=False) + "\n", encoding="utf-8")
    (ws.parent / "迷深实战-BUILD-STATE.md").write_text("**游标：3＝ch0004**", encoding="utf-8")
    corpus = ws.parent / "corpus.txt"
    corpus.write_text("<<<CHAPTER 0001 | a>>>\n甲\n<<<CHAPTER 0002 | b>>>\n乙\n<<<CHAPTER 0003 | c>>>\n丙",
                      encoding="utf-8")
    return corpus


def rules(rep):
    return {r["no"]: (r["status"], r["detail"]) for r in rep["checks"]}


def test_planted_violations_all_caught(tmp_path):
    """负对照大满贯：五类栽好的问题必须全部现形。"""
    corpus = _mk(tmp_path / "ws", tmp_path / "store", quote_ok=False, wallclock=True,
                 meta=True, bad_va=True, ghost_chapter=True)
    rep = 自检.run(tmp_path / "store", tmp_path / "ws", corpus)
    rr = rules(rep)
    assert rr[3][0] == "FAIL", rr[3]   # 元文本
    assert rr[4][0] == "FAIL", rr[4]  # 墙钟
    assert rr[8][0] == "FAIL", rr[8]  # 引文落不回
    assert rr[9][0] == "FAIL", rr[9]  # 三件套缺失
    assert rr[2][0] == "FAIL", rr[2]  # 幽灵章号（99 不在声明面）
    assert rep["exit_hint"] == 1


def test_clean_fixture_all_green(tmp_path):
    """正对照：干净夹具 → 十项全 PASS/WARN 且零 FAIL。"""
    corpus = _mk(tmp_path / "ws", tmp_path / "store", quote_ok=True, wallclock=False,
                 meta=False, bad_va=False, ghost_chapter=False)
    rep = 自检.run(tmp_path / "store", tmp_path / "ws", corpus)
    fails = [r for r in rep["checks"] if r["status"] == "FAIL"]
    assert fails == [], f"干净夹具出现 FAIL: {[f['name'] for f in fails]}"
    assert rep["exit_hint"] == 0


def test_gap_reported_as_warn(tmp_path):
    """缺号章 → WARN（登记件待 U-D10），不是静默 PASS。"""
    corpus = _mk(tmp_path / "ws", tmp_path / "store", quote_ok=True, wallclock=False,
                 meta=False, bad_va=False, ghost_chapter=False)
    # 跳章夹具：候选只写 ch1、ch3 → 语料 ch2 无候选且序列有洞
    (tmp_path / "ws" / "candidates" / "extraction-ch0002.json").write_text(
        json.dumps({"_meta": {"source": "t"}, "candidates": []}, ensure_ascii=False), encoding="utf-8")  # 空候选=章2零候选
    (tmp_path / "ws" / "candidates" / "extraction-ch0003.json").write_text(
        json.dumps({"_meta": {"source": "t"}, "candidates": [
            {"record_id": "e-3", "record_type": "entity",
             "evidence": [{"vol": 1, "chapter": 3, "line": 1, "quote": "甲说：今天天气不错。"}]}]},
            ensure_ascii=False), encoding="utf-8")  # ch3 有候选 → ch2 是范围内零候选
    rep = 自检.run(tmp_path / "store", tmp_path / "ws", corpus)
    rr = rules(rep)
    assert rr[5][0] == "WARN" and "零候选章" in rr[5][1], rr[5]  # 缺号章=空单元登记问题（c5）


if __name__ == "__main__":
    import tempfile
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        with tempfile.TemporaryDirectory() as td:
            fn(Path(td))
        print(f"OK {fn.__name__}")
    print(f"{len(fns)} tests PASS")
