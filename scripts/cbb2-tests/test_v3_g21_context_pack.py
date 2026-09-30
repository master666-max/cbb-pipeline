# -*- coding: utf-8 -*-
"""test_v3_g21_context_pack.py — G21 上下文包三缺陷回归（D-18/19/20）。
运行：py -X utf8 -m pytest cbb-v2/tests/test_v3_g21_context_pack.py -q
D-18 缺 import os（复核：已在位，本件锁回归）；D-19 判例指针参数化；D-20 预算正负对照。
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
_TOOLS = HERE.parent / "cbb" / "tools"  # 包内布局：tools 在 scripts/cbb/tools
sys.path.insert(0, str(_TOOLS))

import context_pack as cp  # noqa: E402 — v1 生产工具（cbb/tools/）
from cbb2 import context as c2ctx  # noqa: E402 — v2 上下文包（cbb-v2/cbb2/context.py）


def _mk_store(tmp: Path, n_ent: int = 3, n_fs: int = 1, n_roll: int = 2) -> Path:
    """夹具库：n_ent 个人物（各 1 次出场）、n_fs 条核心伏笔、n_roll 行滚动摘要。"""
    store = tmp / "store"
    ch = store / "libraries" / "character" / "provisional"
    fo = store / "libraries" / "foreshadow" / "provisional"
    ch.mkdir(parents=True, exist_ok=True)
    fo.mkdir(parents=True, exist_ok=True)
    for i in range(1, n_ent + 1):
        n = f"人物{i:03d}"
        (ch / f"cand-entity-{n}.json").write_text(json.dumps({
            "record_id": f"cand-entity-{n}", "record_type": "entity", "library": "character",
            "status": "provisional", "canonical": {"name": n, "entity_type": "人物"},
            "evidence": [{"vol": 1, "chapter": i, "line": 1, "quote": n}],
            "verified_against": {"path": "t", "sha": "0" * 7, "verified_at": "1970-01-01"},
            "version": 1, "supersedes": None}, ensure_ascii=False), encoding="utf-8")
    for i in range(1, n_fs + 1):
        (fo / f"cand-fs-{i}.json").write_text(json.dumps({
            "record_id": f"cand-fs-{i}", "record_type": "foreshadow", "library": "foreshadow",
            "status": "provisional",
            "canonical": {"name": f"伏笔{i:03d}手环之谜的真正用途是什么", "tier": "核心",
                          "setup_chapter": i, "payoff_chapter": None, "note": "注" * 30},
            "evidence": [{"vol": 1, "chapter": i, "line": 1, "quote": "x"}],
            "verified_against": {"path": "t", "sha": "0" * 7, "verified_at": "1970-01-01"},
            "version": 1, "supersedes": None}, ensure_ascii=False), encoding="utf-8")
    (store / "appearances.jsonl").write_text(
        "\n".join(json.dumps({"chapter": i, "entity": f"人物{i:03d}", "key": f"k{i}"},
                             ensure_ascii=False) for i in range(1, n_ent + 1)), encoding="utf-8")
    (store / "aliases.jsonl").write_text("", encoding="utf-8")
    rolling = tmp / "rolling-summary.md"
    rolling.write_text("\n".join(f"ch{i:04d}｜第{i}章提要一行内容" for i in range(1, n_roll + 1)),
                       encoding="utf-8")
    return store


# ---- D-18：import os（复核已不成立——import 在位、CLI --help 可用；本件锁回归防复发） ----

def test_d18_import_os_present_and_help_exits_zero():
    assert "import os" in (_TOOLS / "context_pack.py").read_text(encoding="utf-8")
    r = subprocess.run([sys.executable, "-X", "utf8", str(_TOOLS / "context_pack.py"), "--help"],
                       capture_output=True, timeout=60)
    assert r.returncode == 0, r.stderr.decode("utf-8", "replace")


# ---- D-19：判例指针参数化（显式参 > env CBB_PRECEDENT > 脚本同级默认） ----

def test_d19_precedent_param_overrides(monkeypatch):
    monkeypatch.delenv("CBB_PRECEDENT", raising=False)
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        store = _mk_store(tmp)
        rolling = tmp / "rolling-summary.md"
        # 默认：历史字面不变（cbb/tools/判例.md）
        base = cp.build(store, None, rolling)
        assert "- cbb/tools/判例.md（" in base
        # 显式参：外置判例显示全路径＋条目计数
        cust = tmp / "外置判例.md"
        cust.write_text("1. 甲判例\n2. 乙判例\n3. 丙判例\n", encoding="utf-8")
        txt = cp.build(store, None, rolling, precedent=cust)
        assert f"- {cust}（当前 3 条" in txt
        # env 覆盖：不传参也生效
        monkeypatch.setenv("CBB_PRECEDENT", str(cust))
        txt2 = cp.build(store, None, rolling)
        assert f"- {cust}（当前 3 条" in txt2


# ---- D-20：预算正负对照（正例=小库全量在内；负例=巨库裁剪后仍 ≤ 上限） ----

def test_d20_budget_positive_small_store():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        store = _mk_store(tmp, n_ent=3, n_fs=1, n_roll=2)
        txt = cp.build(store, None, tmp / "rolling-summary.md")
        assert len(txt) <= cp.BUDGET_CHARS          # 正例：预算内
        assert "人物001" in txt and "伏笔001" in txt  # 且内容未被裁剪


def test_d20_budget_negative_huge_store_truncated():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        store = _mk_store(tmp, n_ent=300, n_fs=60, n_roll=400)  # 远超预算的负例
        txt = cp.build(store, None, tmp / "rolling-summary.md")
        assert len(txt) <= cp.BUDGET_CHARS          # 负例反证：裁剪序兜底，包 ≤ 上限
        assert len(txt) > cp.BUDGET_CHARS // 2      # 且不是裁空（①人物册最后牺牲仍有内容）


def test_d20_cbb2_pack_budget_hard_cap():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        lib = tmp / "libraries" / "character" / "provisional"
        lib.mkdir(parents=True)
        for i in range(1, 31):
            (lib / f"e{i}.json").write_text(json.dumps({
                "record_type": "entity",
                "canonical": {"name": f"实体{i:02d}" * 6, "entity_type": "人物"},
                "evidence": [{"vol": 1, "chapter": 1, "line": 1, "quote": "q"}]},
                ensure_ascii=False), encoding="utf-8")
        big_tail = "尾" * 500
        pack = c2ctx.build_context_pack(tmp, chapter=2, prev_slice_tail=big_tail, budget=200)
        assert pack["budget_used"] <= pack["budget"]   # 负例：内容远超 200 字仍硬顶
        assert len(pack["近窗"]) <= 200 - 200 // 3      # 近窗配额先扣
        small = c2ctx.build_context_pack(tmp, chapter=2, prev_slice_tail="短尾", budget=2000)
        assert small["budget_used"] <= small["budget"]  # 正例：小输入预算内
        assert any("实体01" in c for c in small["实体卡"])  # 且卡片未被挤掉


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"OK {fn.__name__}")
    print(f"{len(fns)} tests PASS")
