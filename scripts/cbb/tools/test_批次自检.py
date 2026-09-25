# -*- coding: utf-8 -*-
"""test_批次自检.py — 十项断言的正负对照（栽好的问题必须被抓，干净的必须全绿）"""
import importlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
自检 = importlib.import_module("批次自检")


def _mk(ws: Path, store: Path, *, quote_ok: bool, wallclock: bool, meta: bool,
        bad_va: bool, ghost_chapter: bool, state_name: str = "BUILD-STATE.md",
        write_state: bool = True):
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
    # 默认写**裸名** BUILD-STATE.md —— init_project.py 的真实产出名。
    # 旧夹具写的是 `迷深实战-BUILD-STATE.md`，恰好与被检出的硬编码缺陷同形，
    # 于是"三方对账"在三条测试里全绿、到真项目上永远读不到 STATE（外部审计 2026-09-25）。
    if write_state:
        (ws.parent / state_name).write_text("**游标：3＝ch0004**", encoding="utf-8")
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


def test_c1_两种惯例名的STATE都认(tmp_path):
    """裸名（init_project 默认产出）与带项目前缀名都要找得到。"""
    for name in ("BUILD-STATE.md", "迷深实战-BUILD-STATE.md", "终末停滞委员会-BUILD-STATE.md"):
        root = tmp_path / name.replace(".", "_")
        corpus = _mk(root / "ws", root / "store", quote_ok=True, wallclock=False,
                     meta=False, bad_va=False, ghost_chapter=False, state_name=name)
        rep = 自检.run(root / "store", root / "ws", corpus)
        st, detail = rules(rep)[1]
        assert st != "SKIP", (name, detail)
        assert "游标=3" in detail, (name, detail)   # 真读到了，不是"恰好不查"


def test_c1_无STATE判SKIP并进未达项(tmp_path):
    """三方缺一角 ⇒ SKIP（旧实现读不到 STATE 仍返回 PASS＝"缺席/为空/通过"三者同形）。"""
    corpus = _mk(tmp_path / "ws", tmp_path / "store", quote_ok=True, wallclock=False,
                 meta=False, bad_va=False, ghost_chapter=False, write_state=False)
    rep = 自检.run(tmp_path / "store", tmp_path / "ws", corpus)
    st, detail = rules(rep)[1]
    assert st == "SKIP", detail
    assert "无 STATE 可判" in detail, detail
    assert any(x.startswith("#1 ") for x in rep["未达项"]), rep["未达项"]


def test_c1_git判不了不得记True(tmp_path):
    """临时目录不是 git 仓 ⇒ git 侧不可判，记 WARN（旧实现按 stdout 空判成"干净"）。"""
    corpus = _mk(tmp_path / "ws", tmp_path / "store", quote_ok=True, wallclock=False,
                 meta=False, bad_va=False, ghost_chapter=False)
    rep = 自检.run(tmp_path / "store", tmp_path / "ws", corpus)
    st, detail = rules(rep)[1]
    assert st == "WARN", detail
    assert "不可判" in detail or "不在 git 仓" in detail, detail
    assert "git-clean=True" not in detail, detail


def test_c8_c9_空库不刷绿(tmp_path):
    """零候选/零记录 ⇒ SKIP，不是 PASS（"回落 0 条失败 0 条"曾判通过）。"""
    ws, store = tmp_path / "ws", tmp_path / "store"
    ws.mkdir(parents=True)
    (ws / "candidates").mkdir()
    (ws / "slice").mkdir()
    store.mkdir(parents=True)
    (store / "ledger.jsonl").write_text('{"seq": 1}\n', encoding="utf-8")
    (tmp_path / "BUILD-STATE.md").write_text("游标：1", encoding="utf-8")
    rep = 自检.run(store, ws, None)
    rr = rules(rep)
    assert rr[8][0] == "SKIP", rr[8]
    assert rr[9][0] == "SKIP", rr[9]
    assert rep["skip"] >= 2 and rep["exit_hint"] == 0


if __name__ == "__main__":
    import tempfile
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        with tempfile.TemporaryDirectory() as td:
            fn(Path(td))
        print(f"OK {fn.__name__}")
    print(f"{len(fns)} tests PASS")
