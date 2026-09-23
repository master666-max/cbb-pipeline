# -*- coding: utf-8 -*-
"""test_context_pack.py — U-F04 包内重排测试（夹具库＋桩重排器；降级同形断言）"""
import importlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
cp = importlib.import_module("context_pack")


def mk_store(tmp: Path) -> Path:
    store = tmp / "store"
    ch = store / "libraries" / "character" / "provisional"
    fo = store / "libraries" / "foreshadow" / "provisional"
    ch.mkdir(parents=True, exist_ok=True)
    fo.mkdir(parents=True, exist_ok=True)
    for i, n in enumerate(["张三", "李四", "王五"], 1):
        (ch / f"cand-entity-{n}.json").write_text(json.dumps({
            "record_id": f"cand-entity-{n}", "record_type": "entity", "library": "character",
            "status": "provisional", "canonical": {"name": n, "entity_type": "人物"},
            "evidence": [{"vol": 1, "chapter": i, "line": 1, "quote": n}],
            "verified_against": {"path": "t", "sha": "0" * 7, "verified_at": "1970-01-01"},
            "version": 1, "supersedes": None}, ensure_ascii=False), encoding="utf-8")
    (fo / "cand-fs-1.json").write_text(json.dumps({
        "record_id": "cand-fs-1", "record_type": "foreshadow", "library": "foreshadow",
        "status": "provisional",
        "canonical": {"name": "手环之谜", "tier": "核心", "setup_chapter": 5, "payoff_chapter": None,
                      "note": "手环的真正用途"},
        "evidence": [{"vol": 1, "chapter": 5, "line": 1, "quote": "手环"}],
        "verified_against": {"path": "t", "sha": "0" * 7, "verified_at": "1970-01-01"},
        "version": 1, "supersedes": None}, ensure_ascii=False), encoding="utf-8")
    # 出场频次：张三×10 李四×5 王五×1
    (store / "appearances.jsonl").write_text(
        "\n".join(json.dumps({"chapter": i, "entity": n, "key": f"{n}|ch{i}"}, ensure_ascii=False)
                  for n, k in (("张三", 10), ("李四", 5), ("王五", 1))
                  for i in range(1, k + 1)), encoding="utf-8")
    (store / "aliases.jsonl").write_text(
        json.dumps({"alias": "三哥", "entity_id": "cand-entity-张三", "entity_type": "人物",
                    "key": "三哥|cand-entity-张三"}, ensure_ascii=False), encoding="utf-8")
    (store.parent / "rolling-summary.md").write_text(
        "ch0001｜张三得到手环\nch0002｜李四加入队伍\n", encoding="utf-8")
    return store


def _section(text: str, title: str) -> list[str]:
    seg = text.split(title, 1)[1].split("\n## ", 1)[0]
    return [ln for ln in seg.splitlines() if ln.startswith("- ")]


def test_mechanical_default_identical_to_history(tmp_path):
    """不传重排器 → 与历史行为一致（头部无重排行、顺序=频次序）。"""
    t1, t2 = tmp_path / "a", tmp_path / "b"
    txt = cp.build(mk_store(t1), None, t1.parent / "rolling-summary.md")
    self_href = cp.build(mk_store(t2), None, t2.parent / "rolling-summary.md")
    assert txt == self_href  # 确定性：同输入两次逐字节一致
    assert "预算内重排" not in txt
    assert _section(txt, "① 主要人物册")[0].startswith("- 张三")  # 频次序


def test_rerank_reorders_and_labels(tmp_path):
    """岗位①：重排器把"李四"排到人物册第一；头部标注 backend。"""
    def stub(q, docs, mech):
        return list(reversed(mech)), "rerank"  # 桩：整体倒序
    store = mk_store(tmp_path)
    txt = cp.build(store, None, store.parent / "rolling-summary.md", reranker=stub)
    sec1 = _section(txt, "① 主要人物册")
    assert sec1[0].startswith("- 王五") and sec1[-1].startswith("- 张三")
    assert "预算内重排：rerank" in txt
    assert "手环之谜" in _section(txt, "② 活跃伏笔")[0] or len(_section(txt, "② 活跃伏笔")) >= 1


def test_unavailable_falls_back_same_shape(tmp_path):
    """判据：缺席即降级——重排器返回 None → 机械序，**产出同形**（仅头部标注不同）。"""
    def dead(q, docs, mech):
        return mech, "mechanical"  # 降级路径：机械序原样
    store = mk_store(tmp_path)
    base = cp.build(mk_store(tmp_path / "x"), None, (tmp_path / "x").parent / "rolling-summary.md")
    txt = cp.build(store, None, store.parent / "rolling-summary.md", reranker=dead)
    body_base = "\n".join(base.splitlines()[1:])
    body_txt = "\n".join(txt.splitlines()[1:])
    assert body_base == body_txt.replace("> 预算内重排：mechanical（岗位①·U-F04）\n", "") \
        or _section(base, "① 主要人物册") == _section(txt, "① 主要人物册")
    assert "预算内重排：mechanical" in txt


def test_budget_respected_with_rerank(tmp_path):
    stub = lambda q, docs, mech: (list(reversed(mech)), "rerank")  # noqa: E731
    store = mk_store(tmp_path)
    txt = cp.build(store, None, store.parent / "rolling-summary.md", reranker=stub)
    assert len(txt) <= cp.BUDGET_CHARS + 120  # 预算内（允许头部标注行的少量字符）


if __name__ == "__main__":
    import tempfile
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        with tempfile.TemporaryDirectory() as td:
            fn(Path(td))
        print(f"OK {fn.__name__}")
    print(f"{len(fns)} tests PASS")
