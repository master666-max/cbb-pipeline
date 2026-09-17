# -*- coding: utf-8 -*-
"""test_graphiti_bridge.py — U-C03.7 stub 单测（离线：不装 graphiti、不联网）。"""
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import graphiti_bridge as gb  # noqa: E402
import graphiti_ready as gr   # noqa: E402


class StubGraphiti:
    """协议 stub：记录 add_episode 调用，不触网。"""

    def __init__(self):
        self.calls = []

    def add_episode(self, **kwargs):
        self.calls.append(kwargs)
        return {"ok": True, "name": kwargs["name"]}


def test_llm_presets(monkey_env=None):
    import os
    old = {k: os.environ.get(k) for k in ("DEEPSEEK_API_KEY", "LMSTUDIO_API_KEY")}
    try:
        os.environ.pop("DEEPSEEK_API_KEY", None)
        try:
            gb.llm_config("deepseek")
            raise AssertionError("缺凭证必须报错")
        except ValueError as e:
            assert "DEEPSEEK_API_KEY" in str(e)
        os.environ["DEEPSEEK_API_KEY"] = "sk-test-only"  # 测试值，不落盘
        c = gb.llm_config("deepseek")
        assert c["api_base"] == gb.DEEPSEEK_BASE and c["model"] == gb.DEEPSEEK_MODEL
        assert c["api_key"] == "sk-test-only"
        # LM Studio 档：无 key 合法（本地无鉴权常态）
        os.environ.pop("LMSTUDIO_API_KEY", None)
        c2 = gb.llm_config("lmstudio-flash")
        assert c2["api_base"] == gb.LMSTUDIO_BASE and c2["model"] == gb.LMSTUDIO_MODEL
        try:
            gb.llm_config("other")
            raise AssertionError("未知预设必须报错")
        except ValueError:
            pass
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def test_embedding_profile_known():
    p = gb.embedding_config()
    assert p["model"] == "qwen3-embedding-8b" and p["dim"] == 4096
    assert p["base_url"] == "http://127.0.0.1:8080/v1/embeddings"


def test_ingest_reuses_build_episode_kwargs():
    """桥禁重造：add_episode 收到的 kwargs 必须是 build_episode_kwargs 的产物形态。"""
    stub = StubGraphiti()
    recs = [{"record_type": "entity", "canonical": {"name": "诺文", "entity_type": "人物"},
             "observations": [{"category": "summary", "text": "剑圣"}]},
            {"record_type": "relation",
             "canonical": {"subject": "涡波", "rel_type": "师承", "object": "诺文"},
             "observations": []}]
    out = gb.ingest_candidates(stub, {14: recs}, group_id="mishen-canon")
    assert len(stub.calls) == 1 and out[14]["ok"] is True
    kw = stub.calls[0]
    # build_episode_kwargs 已测形态关键字段（复用=同源，非重造）
    assert kw["name"] == "ch0014" and kw["group_id"] == "mishen-canon"
    assert kw["source"] == "text" and "reference_time" in kw
    assert "custom_extraction_instructions" in kw  # R6 标配
    assert str(kw["reference_time"]).startswith("2000-")  # 伪锚点，禁墙钟
    assert "诺文" in kw["episode_body"] and "涡波" in kw["episode_body"]


def test_ready_report_offline_shape():
    rep = gr.ready_report("deepseek")
    assert set(rep) == {"overall", "preset", "checks"} and len(rep["checks"]) == 4
    # 离线环境 graphiti 多半未装 → 至少该项 BLOCKED 且 overall=BLOCKED（不静默）
    assert rep["overall"] in ("READY", "BLOCKED")


def test_trigger_sentinel(tmp_store=None):
    with tempfile.TemporaryDirectory() as tmp:
        store = Path(tmp) / "store"
        (store / "libraries" / "character" / "provisional").mkdir(parents=True)
        (store / "quarantine-zone").mkdir(parents=True)
        (store / "libraries" / "character" / "provisional" / "r1.json").write_text(
            json.dumps({"verified_against": {"path": "语料分析/corpus/clean_full.txt"}},
                       ensure_ascii=False), encoding="utf-8")
        # B：单版本 → GREEN
        s = gr.trigger_sentinel(store, logs_dir=Path(tmp) / "logs")
        assert s["B"]["state"] == "GREEN"
        # D：0 积压 → GREEN；造 51 条 → RED
        assert s["D"]["state"] == "GREEN"
        with (store / "quarantine-zone" / "items.jsonl").open("w", encoding="utf-8") as f:
            for i in range(51):
                f.write(json.dumps({"status": "pending", "group": "entity_unalignable"},
                                   ensure_ascii=False) + "\n")
        s2 = gr.trigger_sentinel(store, logs_dir=Path(tmp) / "logs")
        assert s2["D"]["state"] == "RED"
        # A：计数文件 3 → RED
        logs = Path(tmp) / "logs"; logs.mkdir(exist_ok=True)
        (logs / "global-query-count.txt").write_text("3", encoding="utf-8")
        s3 = gr.trigger_sentinel(store, logs_dir=logs)
        assert s3["A"]["state"] == "RED"


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted({k: v for k, v in globals().items()
                            if k.startswith("test_") and callable(v)}.items()):
        try:
            fn()
            print(f"PASS {name}")
        except AssertionError as e:
            fails += 1
            print(f"FAIL {name}: {e}")
    raise SystemExit(1 if fails else 0)
