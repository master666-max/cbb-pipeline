# -*- coding: utf-8 -*-
"""run_tier2_pipeline.py — Tier 2 原装 add_episode 管道验证
用法: DEEPSEEK_API_KEY=... NEO4J_PASSWORD=... venv312/Scripts/python.exe -X utf8 run_tier2_pipeline.py
叙事伪锚点：reference_time = 2000-01-01 + 集序i天（保章节顺序，不冒充真实日期——报告披露）
R6 领域规则经 add_episode 原生 custom_extraction_instructions 注入
"""
import asyncio, json, os, sys
from datetime import datetime, timedelta, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
OUT = os.path.join(ROOT, "结果", "tier2")
os.makedirs(OUT, exist_ok=True)

DS_KEY = os.environ.get("DEEPSEEK_API_KEY")
NEO_PASS = os.environ.get("NEO4J_PASSWORD")
if not DS_KEY or not NEO_PASS:
    sys.exit("FATAL: need DEEPSEEK_API_KEY + NEO4J_PASSWORD env")

EPISODES = [
    ("excerpt1-CHAPTER0014", "excerpt1-CHAPTER0014.md"),
    ("excerpt2-CHAPTER0038", "excerpt2-CHAPTER0038.md"),
    ("excerpt3-CHAPTER0114", "excerpt3-CHAPTER0114.md"),
    ("excerpt4-CHAPTER0001", "excerpt4-CHAPTER0001-序章型.md"),
]
SHA = {"excerpt1-CHAPTER0014": "08cc9036f03ec9ee", "excerpt2-CHAPTER0038": "15dc13a4c11870b0",
       "excerpt3-CHAPTER0114": "0dca88d75c99eaaa", "excerpt4-CHAPTER0001": "9b0d2d0c7b4d2c4b"}

from graphiti_core import Graphiti
from graphiti_core.llm_client import LLMConfig, OpenAIClient
from graphiti_core.embedder import OpenAIEmbedder, OpenAIEmbedderConfig
from graphiti_core.nodes import EpisodeType
from graphiti_core.cross_encoder.client import CrossEncoderClient
from neo4j import AsyncGraphDatabase

class NoopCrossEncoder(CrossEncoderClient):
    """Tier 2 只入库不检索：reranker 槽位用空转实现占位"""
    async def rank(self, cross_encoder_query, passages):
        return []

R6 = """领域规则（中文小说《迷深》正典库构建）：
1) 元文本（作者杂谈/翻译组公告/论坛吐槽/现实日期/话数卷数/平台与作品名）一律不得抽取任何实体或关系；
2) 无专名但固定出场且有关键行为的职务称呼（如店长）应抽取为实体；
3) 专有名词（人名/地名/魔法名/道具名）保留原文写法，不翻译不改写；
4) 信件/传闻/指控中的声称按文本事实抽取，并在 fact 中标注'据某某声称'。"""

async def main():
    llm_cfg = LLMConfig(api_key=DS_KEY, model="deepseek-flash",
                        base_url="https://api.deepseek.com/v1", small_model="deepseek-flash")
    llm = OpenAIClient(config=llm_cfg, max_tokens=32768)
    emb_cfg = OpenAIEmbedderConfig(api_key="lmstudio-local",
                                   embedding_model="text-embedding-qwen3-embedding-8b@q8_0",
                                   embedding_dim=4096, base_url="http://127.0.0.1:8080/v1")
    embedder = OpenAIEmbedder(config=emb_cfg)
    graphiti = Graphiti("bolt://localhost:7687", "neo4j", NEO_PASS,
                        llm_client=llm, embedder=embedder,
                        cross_encoder=NoopCrossEncoder())
    await graphiti.build_indices_and_constraints()
    print("[init] indices/constraints built", flush=True)
    drv = AsyncGraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", NEO_PASS))

    log = []
    for i, (name, fname) in enumerate(EPISODES):
        text = open(os.path.join(ROOT, "材料", fname), encoding="utf-8").read()
        ref = datetime(2000, 1, 1, tzinfo=timezone.utc) + timedelta(days=i)
        # 断点续跑：已入库的集跳过
        async with drv.session(database="neo4j") as s:
            chk = await s.run("MATCH (e:Episodic {name:$n}) RETURN count(e) AS c", n=name)
            rec = [r.data() async for r in chk]
            if rec and rec[0]["c"] > 0:
                log.append({"episode": name, "status": "skipped(已入库)"})
                print(f"[ep{i+1}] {name} SKIP(已入库)", flush=True)
                continue
        t0 = datetime.now()
        try:
            await graphiti.add_episode(
                name=name, episode_body=text,
                source_description="中文小说《迷深》正文切样（Step0-Tier2 实验）",
                reference_time=ref, source=EpisodeType.text,
                group_id="mishen-step0",
                custom_extraction_instructions=R6,
            )
            dt = (datetime.now() - t0).total_seconds()
            log.append({"episode": name, "status": "ok", "seconds": dt})
            print(f"[ep{i+1}] {name} OK {dt:.0f}s", flush=True)
        except Exception as e:
            log.append({"episode": name, "status": "error", "error": repr(e)[:300]})
            print(f"[ep{i+1}] {name} ERROR: {repr(e)[:200]}", flush=True)

    # ---- 导出全图 ----
    async with drv.session(database="neo4j") as session:
        nodes = await session.run("MATCH (n:Entity) RETURN n.name AS name, n.summary AS summary, labels(n) AS labels")
        ent_rows = [r.data() async for r in nodes]
        edges = await session.run("MATCH (a:Entity)-[r:RELATES_TO]->(b:Entity) "
                                  "RETURN a.name AS src, b.name AS dst, r.fact AS fact, "
                                  "r.valid_at AS valid_at, r.invalid_at AS invalid_at")
        edge_rows = [r.data() async for r in edges]
        ep_count = await session.run("MATCH (e:Episodic) RETURN count(e) AS c")
        ep_c = [r.data() async for r in ep_count]

    result = {"meta": {"model": "deepseek-flash", "embedder": "text-embedding-qwen3-embedding-8b@q8_0@LMStudio:4096",
                       "backend": "neo4j-docker", "r6": R6[:40] + "...",
                       "reference_time_policy": "2000-01-01+集序天(叙事伪锚点)"},
              "episode_log": log, "episodic_count": ep_c,
              "entities": ent_rows, "edges": edge_rows}
    with open(os.path.join(OUT, "tier2-graph-export.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1, default=str)
    print(f"[done] entities={len(ent_rows)} edges={len(edge_rows)} episodic={ep_c}", flush=True)

asyncio.run(main())
