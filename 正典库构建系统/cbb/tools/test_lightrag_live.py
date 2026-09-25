# -*- coding: utf-8 -*-
"""test_lightrag_live.py — 实时同步哨三段实测（temp store，零网络依赖端点除外）：首喂/幂等/增量。"""
import asyncio
import json
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "cbb-store"))
sys.path.insert(0, str(HERE.parent / "cbb-quarantine"))

import lightrag_live as lv  # noqa: E402
import lightrag_export as le  # noqa: E402


def mk(rid, name, etype="人物"):
    return {"record_id": rid, "record_type": "entity", "library": "character",
            "status": "provisional", "version": 1,
            "canonical": {"name": name, "entity_type": etype},
            "evidence": [{"vol": 1, "chapter": 1, "line": 1, "quote": f"{name}出场"}],
            "observations": [{"text": f"{name}的实时同步验证文本。"}]}


def main():
    td = tempfile.mkdtemp()
    store = Path(td) / "store"
    d = store / "libraries" / "character" / "provisional"
    d.mkdir(parents=True)
    (d / "e1.json").write_text(json.dumps(mk("e1", "甲"), ensure_ascii=False), encoding="utf-8")
    (d / "e2.json").write_text(json.dumps(mk("e2", "乙"), ensure_ascii=False), encoding="utf-8")
    work = Path(td) / "work"
    holder: dict = {}

    async def setup():
        from lightrag import LightRAG
        from lightrag.utils import EmbeddingFunc
        rag = LightRAG(working_dir=str(work),
                       embedding_func=EmbeddingFunc(embedding_dim=4096, func=le._embed_batch),
                       llm_model_func=le._llm_stub, llm_model_name="stub")
        await rag.initialize_storages()
        holder.update({"rag": rag, "loop": asyncio.get_running_loop()})

    async def drive():
        await setup()
        state = {"last_poll": -1.0}
        r1 = await lv.poll_once(store, work, holder, state)       # 首喂
        assert r1["delta_entities"] == 2 and r1["fed"], r1
        assert r1["llm_calls"] == 0
        time.sleep(1.1)
        r2 = await lv.poll_once(store, work, holder, state)       # 幂等：无新 mtime
        assert r2["changed"] == 0 and not r2["fed"], r2
        (d / "e3.json").write_text(json.dumps(mk("e3", "丙"), ensure_ascii=False), encoding="utf-8")
        await asyncio.sleep(0.05)
        r3 = await lv.poll_once(store, work, holder, state)       # 增量：只喂新件
        assert r3["delta_entities"] == 1 and r3["fed"] and r3["llm_calls"] == 0, r3
        return r1, r2, r3

    r1, r2, r3 = asyncio.run(drive())
    print(json.dumps({"首喂": r1["delta_entities"], "幂等轮变更": r2["changed"],
                      "增量": r3["delta_entities"], "llm总调用": le.CNT["llm_calls"]},
                     ensure_ascii=False))
    print("OK live_sync 三段全过（首喂2E / 幂等0 / 增量1E）")


if __name__ == "__main__":
    main()
