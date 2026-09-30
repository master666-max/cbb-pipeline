# -*- coding: utf-8 -*-
"""test_v3_phasec.py — Phase C：门控切分/承接摘要/三层上下文包/runner 总装。
运行：py -X utf8 test_v3_phasec.py"""
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from cbb2 import context, runner, splitting  # noqa: E402
from cbb2.store import identity_key  # noqa: E402


def mk_blocks(texts):
    return [{"block_id": f"v01c0001p{i:04d}", "vol": 1, "chapter": 1, "para": i,
             "line_start": i, "line_end": i, "text": t, "sha256": "0" * 64}
            for i, t in enumerate(texts, 1)]


def test_scene_tags_detect_separator_and_timejump():
    tags = splitting.scene_tags(mk_blocks(
        ["「你好啊。」她说", "* * *", "次日清晨，他醒来", "普通的叙述段落"]))
    assert tags["scene_count"] >= 2 and tags["time_jumps"] >= 1
    assert "口径" in tags  # 软标签声明


def test_split_decision_theta_and_flag(monkey_env=None):
    long_text = "字" * 13000
    d = splitting.split_decision(long_text, {"scene_count": 1})
    assert d["split"] and any("θ_len" in r for r in d["reasons"])
    short = splitting.split_decision("短文本", {"scene_count": 1})
    assert not short["split"]


def test_segment_blocks_boundary_and_even():
    blocks = mk_blocks([f"段{i}" for i in range(1, 11)])
    segs = splitting.segment_blocks(blocks, ["v01c0001p0005"])
    assert len(segs) == 2 and segs[1][0]["block_id"] == "v01c0001p0005"  # 边界块开新段
    segs2 = splitting.segment_blocks(blocks, [], target_chars=8)
    assert len(segs2) >= 2 and all(s for s in segs2)


def test_carry_summary_and_context_pack_budget():
    with tempfile.TemporaryDirectory() as td:
        st = []
        for nm in ("缇达", "卢卡"):
            st.append({"record_id": f"e-{nm}", "record_type": "entity", "library": "character",
                       "status": "provisional",
                       "canonical": {"name": nm, "entity_type": "人物", "status": "alive"},
                       "evidence": [{"vol": 1, "chapter": 9, "line": 1, "quote": "q"}],
                       "provenance": {}, "version": 1, "supersedes": None,
                       "verified_against": {"path": "t", "sha": "0" * 7, "verified_at": "1970-01-01"}})
        for r in st:
            (Path(td) / "libraries" / "character" / "provisional").mkdir(parents=True, exist_ok=True)
            (Path(td) / "libraries" / "character" / "provisional" / f"{r['record_id']}.json").write_text(
                json.dumps(r, ensure_ascii=False), encoding="utf-8")
        carry = context.carry_summary(Path(td), 9)
        assert "缇达" in carry and "第9章" in carry and len(carry) <= 200
        pack = context.build_context_pack(Path(td), 10, prev_slice_tail="上一章结尾文本……")
        assert pack["budget_used"] <= pack["budget"]
        assert any("缇达" in c for c in pack["实体卡"])
        # sticky：第二次构建仍在（粘滞），cooldown 剔除
        st2 = json.loads((Path(td) / context.STATE_FILE).read_text(encoding="utf-8"))
        assert st2["缇达"]["sticky_until"] >= 10


def test_runner_prepare_flag_off_on():
    with tempfile.TemporaryDirectory() as td:
        import os
        os.environ.pop("CBB_DYNAMIC_SPLIT", None)
        blocks = mk_blocks(["段"] * 5)
        card = runner.prepare_chapter(10, prev_chapter_text="尾", chapter_text="短",
                                      blocks=blocks, store=Path(td))
        assert card["动态切分"]["split"] is False and card["分段"] is None
        assert "先验非事实源" in card["上下文包"]["口径"]
        os.environ["CBB_DYNAMIC_SPLIT"] = "on"
        long_blocks = mk_blocks(["段落文本" * 30] * 400)
        card2 = runner.prepare_chapter(11, chapter_text="字" * 13000,
                                       blocks=long_blocks, store=Path(td))
        os.environ.pop("CBB_DYNAMIC_SPLIT", None)
        assert card2["动态切分"]["split"] is True and card2["分段"] and len(card2["分段"]) >= 2


def test_runner_finalize_tracks_and_checkpoint():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        base = {"record_id": "e1", "record_type": "entity", "library": "character",
                "status": "provisional",
                "canonical": {"name": "缇达", "entity_type": "人物", "status": "alive"},
                "evidence": [{"vol": 1, "chapter": 14, "line": 1, "quote": "q14"}],
                "provenance": {"extractor_confidence": 80}, "version": 1, "supersedes": None,
                "verified_against": {"path": "t", "sha": "0" * 7, "verified_at": "1970-01-01"}}
        dup = json.loads(json.dumps(base))
        dup["record_id"] = "e1-obs"; dup["evidence"] = [{"vol": 1, "chapter": 20, "line": 2, "quote": "q20"}]
        dup2 = json.loads(json.dumps(base))
        dup2["record_id"] = "e1-obs2"; dup2["evidence"] = [{"vol": 1, "chapter": 21, "line": 2, "quote": "q21"}]
        rep = runner.finalize_chapter(root, [base, dup, dup2], at="ch0020")
        assert rep["tracks"].get("on-create") == 1
        assert rep["tracks"].get("consistent-duplicate") == 2
        assert rep["checkpoint"] > 0
        assert not runner.refeed_needed(root) is None  # 检查点已提交（刚推进=无需重喂）
        assert runner.refeed_needed(root) is False
        # 幂等重放：同批再来一遍——consistent-duplicate 走 P-017 repeated
        rep2 = runner.finalize_chapter(root, [base, dup, dup2], at="ch0020")
        assert rep2["tracks"].get("consistent-duplicate") == 3


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"OK {fn.__name__}")
    print(f"{len(fns)} tests PASS")
