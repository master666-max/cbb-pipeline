# -*- coding: utf-8 -*-
"""graphiti_spike.py — Graphiti 双时序框架接线 spike（P2 准备件 · 2026-09-25）。

目的：打通"正典语料切片 → Graphiti episode → 双时序图"的最小管道，验证
graphiti-core 0.30.2 + 本地 LM Studio（14B 抽取 / qwen3 嵌入 4096 维）+ 独立 Neo4j
实例（neo4j-graphiti 容器 7693，与正典图 7695/7694 完全隔离）可用。
纪律：
  · spike 只写 graphiti 专用实例，正典图（neo4j-step0）与正典库零接触；
  · reference_time 用章伪锚点（禁墙钟入图——与 neo4j_export 同纪律）；
  · 抽取质量不在本 spike 判据内（判据=管道通、图有节点边）。
"""
from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
from neo4j_export import derive_password  # noqa: E402

# 路线开关=环境变量（换路线不改码）：SPIKE_LLM_MODEL / SPIKE_LLM_BASE 可覆盖；
# DeepSeek 路线：SPIKE_LLM_MODEL=deepseek-chat SPIKE_LLM_BASE=https://api.deepseek.com
# key 只走环境变量 DEEPSEEK_API_KEY（D-004 不落文件；本地路线填 "local" 占位）
import os as _os
LLM_BASE = _os.environ.get("SPIKE_LLM_BASE", "http://127.0.0.1:8080/v1")
LLM_MODEL = _os.environ.get("SPIKE_LLM_MODEL", "tifa-deepsex-14b-cot-chat")
API_KEY = _os.environ.get("DEEPSEEK_API_KEY", "local")
EMB_MODEL = "text-embedding-qwen3-embedding-8b@q4_k_m"   # 嵌入恒本地（DeepSeek 无嵌入端点）
EMB_BASE = _os.environ.get("SPIKE_EMB_BASE", "http://127.0.0.1:8080/v1")  # 嵌入端点恒本地，不随 LLM 路线走
BOLT = "bolt://localhost:7693"


async def main() -> dict:
    from graphiti_core import Graphiti
    from graphiti_core.llm_client.config import LLMConfig
    from graphiti_core.llm_client.openai_generic_client import OpenAIGenericClient
    from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
    from graphiti_core.nodes import EpisodeType

    pw = derive_password(None)
    llm_cfg = LLMConfig(api_key=API_KEY, model=LLM_MODEL, base_url=LLM_BASE,
                        small_model=LLM_MODEL)
    from graphiti_core.cross_encoder.openai_reranker_client import OpenAIRerankerClient
    graphiti = Graphiti(uri=BOLT, user="neo4j", password=pw,
                        llm_client=OpenAIGenericClient(
                            config=llm_cfg,
                            structured_output_mode=_os.environ.get(
                                "SPIKE_STRUCTURED", "json_schema")),  # DeepSeek 只吃 json_object
                        embedder=OpenAIEmbedder(config=OpenAIEmbedderConfig(
                            api_key="local", base_url=EMB_BASE,
                            embedding_model=EMB_MODEL, embedding_dim=4096)),
                        cross_encoder=OpenAIRerankerClient(config=llm_cfg))  # 缺省会用 OPENAI_API_KEY，显式随路线
    await graphiti.build_indices_and_constraints()

    # 真章节切片（第三章前 600 字）+ 伪锚点参考时间（第3章=序2 → 2000-01-03）
    slice_p = HERE.parent.parent / "迷深实战-工作区" / "slice" / "ch0003.txt"
    body = (slice_p.read_text(encoding="utf-8")[:600] if slice_p.exists()
            else "缇达在迷宫边缘拔出了剑。卢卡守在地下城三层的入口。")
    ref = datetime(2000, 1, 3, tzinfo=timezone.utc)

    USAGE = {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0}
    _orig_create = graphiti.llm_client.client.chat.completions.create

    async def _counting_create(*a, **kw):
        r = await _orig_create(*a, **kw)
        u = getattr(r, "usage", None)
        if u is not None:
            USAGE["calls"] += 1
            USAGE["prompt_tokens"] += getattr(u, "prompt_tokens", 0) or 0
            USAGE["completion_tokens"] += getattr(u, "completion_tokens", 0) or 0
        return r

    graphiti.llm_client.client.chat.completions.create = _counting_create

    t0 = asyncio.get_event_loop().time()
    await graphiti.add_episode(name=f"spike-ch0003-{_os.environ.get('SPIKE_GROUP', 'local14b')}",
                               episode_body=body,
                               source=EpisodeType.text,
                               source_description="迷深 第三章切片（接线 spike）",
                               reference_time=ref,
                               group_id=_os.environ.get("SPIKE_GROUP") or None)
    dt = asyncio.get_event_loop().time() - t0

    # 结果清点（graphiti 专用实例）
    from neo4j import AsyncGraphDatabase
    driver = AsyncGraphDatabase.driver(BOLT, auth=("neo4j", pw))
    counts = {}
    async with driver.session(database="neo4j") as s:
        for label in ("Episode", "Entity", "RELATES_TO"):
            q = (f"MATCH (n:{label}) RETURN count(n) AS c" if label != "RELATES_TO"
                 else f"MATCH ()-[r:{label}]->() RETURN count(r) AS c")
            result = await s.run(q)
            rec = await result.single()
            counts[label] = rec["c"]
    await driver.close()
    return {"model": LLM_MODEL, "episode_s": round(dt, 1), "counts": counts,
            "usage": USAGE, "body_head": body[:40]}


if __name__ == "__main__":
    rep = asyncio.run(main())
    print(json.dumps(rep, ensure_ascii=False, indent=1))
