# -*- coding: utf-8 -*-
"""graphiti_ingest.py — 全章摄入（P2 生产件 · 抽取自管 + graphiti 双时序存储）。

管线（2026-09-25 裁定架构）：切片全文 → DeepSeek 裸调用抽取（json_object，schema 入 prompt）
→ 三元组 → graphiti add_episode(fact_triple, reference_time=伪锚点) → 独立实例落图。
纪律：
  · 正典图（7695/7694）零接触——只写 graphiti 专用实例（7693）；
  · reference_time=伪锚点（禁墙钟入图，同 neo4j_export）；
  · key 只从环境/注册表进（D-004）；抽取原文不入任何输出（只出三元组与计数）。
用法：
  py -X utf8 graphiti_ingest.py --chapter 3 [--dry-run] [--group grp]
  py -X utf8 graphiti_ingest.py --chapter 3 --dump   # 只看已摄入内容
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import winreg
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "cbb-anchor"))

from neo4j_export import derive_password  # noqa: E402
from cbb_anchor import pseudo_anchor  # noqa: E402

ROOT = HERE.parent.parent
WORK = ROOT / "迷深实战-工作区"
BOLT = "bolt://localhost:7693"
EMB_BASE = "http://127.0.0.1:8080/v1"          # 钉死本地（经验②）
EMB_MODEL = "text-embedding-qwen3-embedding-8b@q4_k_m"
EPISODIC_LABEL = "Episodic"                    # 经验③


def _key() -> str:
    env = os.environ.get("DEEPSEEK_API_KEY")
    if env:
        return env
    try:
        return winreg.QueryValueEx(winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment"),
                                   "DEEPSEEK_API_KEY")[0]
    except FileNotFoundError:
        raise SystemExit("DEEPSEEK_API_KEY 未设：setx DEEPSEEK_API_KEY \"sk-...\"（D-004 不落文件）")


def extract(chapter_text: str) -> tuple[list[dict], list[dict], dict]:
    """DeepSeek 裸调用抽取（json_object + schema 入 prompt）→ (实体, 关系, 用量)。"""
    from openai import OpenAI
    client = OpenAI(api_key=_key(), base_url="https://api.deepseek.com")
    r = client.chat.completions.create(
        model="deepseek-chat",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": (
                "从小说文本抽取实体与关系，只输出 JSON："
                '{"entities": [{"name": "...", "type": "人物|地点|物品|组织|概念"}], '
                '"relations": [{"source": "...", "rel": "...", "target": "...", "fact": "..."}]}'
                "。要求：实体名用原文写法、单指实体（人/地/物/组织/称号），抽具体名词"
                "（数值/武器/建筑/阵营）；关系带一句 fact（原文依据的转写）；宁缺勿滥。")},
            {"role": "user", "content": chapter_text}])
    u = r.usage
    d = json.loads(r.choices[0].message.content)
    ents = [{"name": e["name"], "type": e.get("type", "概念")} for e in d.get("entities", [])]
    rels = [{"source": x["source"], "rel": x["rel"], "target": x["target"],
             "fact": x.get("fact", x["rel"])} for x in d.get("relations", [])]
    return ents, rels, {"prompt_tokens": u.prompt_tokens, "completion_tokens": u.completion_tokens,
                        "calls": 1}


async def _feed(group: str, chapter: int, ents: list[dict], rels: list[dict]) -> dict:
    from graphiti_core import Graphiti
    from graphiti_core.llm_client.config import LLMConfig
    from graphiti_core.llm_client.openai_generic_client import OpenAIGenericClient
    from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
    from graphiti_core.cross_encoder.openai_reranker_client import OpenAIRerankerClient
    from graphiti_core.nodes import EpisodeType
    pw = derive_password(None)
    key = _key()
    llm_cfg = LLMConfig(api_key=key, model="deepseek-chat", base_url="https://api.deepseek.com",
                        small_model="deepseek-chat")
    graphiti = Graphiti(uri=BOLT, user="neo4j", password=pw,
                        llm_client=OpenAIGenericClient(config=llm_cfg, structured_output_mode="json_object"),
                        embedder=OpenAIEmbedder(config=OpenAIEmbedderConfig(
                            api_key="local", base_url=EMB_BASE,
                            embedding_model=EMB_MODEL, embedding_dim=4096)),
                        cross_encoder=OpenAIRerankerClient(config=llm_cfg))
    await graphiti.build_indices_and_constraints()
    triples = [{"fact": f"{r['source']}{r['rel']}{r['target']}——{r['fact']}"} for r in rels]
    if not triples:
        return {"fed": False, "口径": "零三元组，不喂空集"}
    ref = datetime.combine(pseudo_anchor(chapter - 1), datetime.min.time(), tzinfo=timezone.utc)
    await graphiti.add_episode(name=f"ch{chapter:04d}",
                               episode_body=json.dumps(triples, ensure_ascii=False),
                               source=EpisodeType.fact_triple,
                               source_description=f"迷深 第{chapter}章 自管抽取三元组",
                               reference_time=ref, group_id=group)
    from neo4j import AsyncGraphDatabase
    driver = AsyncGraphDatabase.driver(BOLT, auth=("neo4j", pw))
    async with driver.session(database="neo4j") as s:
        n = await (await s.run("MATCH (n:Entity) WHERE n.group_id=$g RETURN count(n) AS c",
                               {"g": group})).single()
        r = await (await s.run("MATCH (a:Entity)-[x:RELATES_TO]->(b:Entity) "
                               "WHERE a.group_id=$g AND b.group_id=$g RETURN count(x) AS c",
                               {"g": group})).single()
        e = await (await s.run(f"MATCH (n:{EPISODIC_LABEL}) WHERE n.group_id=$g RETURN count(n) AS c",
                               {"g": group})).single()
    await driver.close()
    return {"fed": True, "entities": n["c"], "relations": r["c"], "episodes": e["c"]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chapter", type=int, required=True)
    ap.add_argument("--group", default=None)
    ap.add_argument("--dry-run", action="store_true", help="只抽取不喂入（打印三元组计数与样例）")
    ap.add_argument("--dump", action="store_true", help="只查该 group 已摄入内容")
    ns = ap.parse_args(argv)
    group = ns.group or f"ch{ns.chapter:04d}-deepseek"
    if ns.dump:
        from graphiti_dump import dump
        print(json.dumps(asyncio.run(dump(group)), ensure_ascii=False, indent=1))
        return 0
    slice_p = WORK / "slice" / f"ch{ns.chapter:04d}.txt"
    if not slice_p.exists():
        raise SystemExit(f"切片缺席：{slice_p}")
    text = slice_p.read_text(encoding="utf-8")
    ents, rels, usage = extract(text)
    print(json.dumps({"chapter": ns.chapter, "字数": len(text),
                      "实体": len(ents), "关系": len(rels),
                      "usage": usage,
                      "样例": {"实体": [e["name"] for e in ents][:8],
                               "关系": [f"{r['source']}-{r['rel']}->{r['target']}" for r in rels][:5]}},
                     ensure_ascii=False, indent=1))
    if ns.dry_run:
        return 0
    rep = asyncio.run(_feed(group, ns.chapter, ents, rels))
    print(json.dumps(rep, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
