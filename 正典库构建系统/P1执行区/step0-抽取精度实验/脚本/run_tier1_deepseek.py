# -*- coding: utf-8 -*-
"""run_tier1_deepseek.py — Tier 1 DeepSeek 抽取（graphiti 真实提示词装配）
用法: DEEPSEEK_API_KEY=sk-xxx <venv312>/Scripts/python.exe -X utf8 run_tier1_deepseek.py
key 只从环境变量读取，不写入任何文件（D-004）。
"""
import json, os, sys, re, time
import httpx

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
EXCERPTS = {
    "excerpt1": "excerpt1-CHAPTER0014.md",
    "excerpt2": "excerpt2-CHAPTER0038.md",
    "excerpt3": "excerpt3-CHAPTER0114.md",
    "excerpt4": "excerpt4-CHAPTER0001-序章型.md",
}
NAME = sys.argv[1] if len(sys.argv) > 1 else "excerpt1"
EXCERPT = os.path.join(ROOT, "材料", EXCERPTS[NAME])
OUT = os.path.join(ROOT, "结果", f"extraction-tier1-{NAME}-deepseek-flash.json")

API = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-flash"
KEY = os.environ.get("DEEPSEEK_API_KEY")
if not KEY:
    sys.exit("FATAL: DEEPSEEK_API_KEY not set")

from graphiti_core.prompts import extract_nodes as EN
from graphiti_core.prompts import extract_edges as EE

ENTITY_TYPES = """人物 - 具名的角色或人物（同一人的别名/称谓归并于主名）
地点 - 具名的场所、区域、国度，以及迷宫本身与其各层级
组织 - 具名的团体、机构、店铺
物品 - 具名的物件
技能魔法 - 具名的技能、魔法、招式
概念 - 具名的独特术语或专有概念"""

def to_dicts(messages):
    out = []
    for m in messages:
        if isinstance(m, dict):
            out.append({"role": m["role"], "content": m["content"]})
        else:
            out.append({"role": m.role, "content": m.content})
    return out

MISSING = set()
class Ctx(dict):
    """缺键返回空串并记录——模板可选项的兜底（透明：缺失键会打印）"""
    def __missing__(self, k):
        MISSING.add(k)
        return ""

def call(client, messages, max_tokens=32768, use_json_mode=True):
    payload = {"model": MODEL, "messages": messages, "temperature": 0, "max_tokens": max_tokens}
    if use_json_mode:
        payload["response_format"] = {"type": "json_object"}
    r = client.post(API, json=payload, headers={"Authorization": f"Bearer {KEY}"}, timeout=480)
    if r.status_code in (429, 500, 502, 503):
        time.sleep(20)
        r = client.post(API, json=payload, headers={"Authorization": f"Bearer {KEY}"}, timeout=480)
    r.raise_for_status()
    data = r.json()
    ch = data["choices"][0]
    content = (ch["message"].get("content") or "").strip()
    txt = content
    m = re.search(r"```(?:json)?\s*(.*?)```", txt, re.S)
    if m:
        txt = m.group(1).strip()
    return txt, data.get("usage", {}), ch.get("finish_reason")

def parse_json(txt):
    try:
        return json.loads(txt)
    except Exception as e:
        raise SystemExit(f"JSON parse failed: {e}\n--- head 500 ---\n{txt[:500]}")

def pick_list(obj, *keys):
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        for k in (*keys,):
            if k in obj and isinstance(obj[k], list):
                return obj[k]
        for v in obj.values():
            if isinstance(v, list):
                return v
    return []

def main():
    text = open(EXCERPT, encoding="utf-8").read()
    client = httpx.Client()

    # ---- 阶段1: 实体抽取（graphiti extract_message 原装模板） ----
    ctx1 = Ctx({"entity_types": ENTITY_TYPES, "previous_episodes": [], "episode_content": text})
    msgs1 = to_dicts(EN.extract_message(ctx1))
    print(f"[nodes] missing_keys={sorted(MISSING)}", flush=True)
    print(f"[nodes] messages={len(msgs1)} prompt_chars={sum(len(m['content']) for m in msgs1)}", flush=True)
    try:
        txt1, usage1, fin1 = call(client, msgs1)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 400 and "json" in e.response.text.lower():
            txt1, usage1, fin1 = call(client, msgs1, use_json_mode=False)
        else:
            raise
    print(f"[nodes] finish={fin1} usage={json.dumps(usage1)}", flush=True)
    nodes_raw = parse_json(txt1)
    entities = pick_list(nodes_raw, "entities", "nodes")
    print(f"[nodes] extracted entities={len(entities)}", flush=True)

    # ---- 阶段2: 关系抽取（graphiti edge 原装模板） ----
    ctx2 = Ctx({
        "previous_episodes": [],
        "episode_content": text,
        "nodes": entities,
        "reference_time": "2026-09-14T00:00:00Z",
    })
    MISSING.clear()
    msgs2 = to_dicts(EE.edge(ctx2))
    print(f"[edges] missing_keys={sorted(MISSING)}", flush=True)
    print(f"[edges] messages={len(msgs2)} prompt_chars={sum(len(m['content']) for m in msgs2)}", flush=True)
    try:
        txt2, usage2, fin2 = call(client, msgs2)
        if fin2 == "length":  # 思维链吃光预算 → 翻倍重试
            print("[edges] length-capped, retry max_tokens=65536", flush=True)
            txt2, usage2, fin2 = call(client, msgs2, max_tokens=65536)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 400 and "json" in e.response.text.lower():
            txt2, usage2, fin2 = call(client, msgs2, use_json_mode=False)
        else:
            raise
    if fin2 == "length":
        # 仍截断 → 对半分块抽边合并
        print("[edges] still length-capped -> chunk into halves", flush=True)
        mid = len(text) // 2
        cut = text.rfind("\n", 0, mid)
        halves = [text[:cut], text[cut:]]
        edges = []
        usage2, fin2 = {}, "chunked"
        for hi, h in enumerate(halves):
            cx = Ctx({"previous_episodes": [], "episode_content": h, "nodes": entities,
                      "reference_time": "2026-09-14T00:00:00Z"})
            t, u, f = call(client, to_dicts(EE.edge(cx)))
            usage2[f"chunk{hi}"] = u
            pr = parse_json(t)
            edges.extend(pick_list(pr, "edges", "facts"))
        edges_raw = {"edges": edges, "chunked": True}
    else:
        edges_raw = parse_json(txt2)
    edges = pick_list(edges_raw, "edges", "facts")
    print(f"[edges] extracted edges={len(edges)}", flush=True)

    result = {
        "meta": {
            "model": MODEL,
            "endpoint": "https://api.deepseek.com",
            "temperature": 0,
            "prompt_source": "graphiti_core.prompts extract_message / edge（原装模板装配，自定义实体类型）",
            "excerpt": EXCERPTS[NAME],
            "excerpt_sha256_16": {"excerpt1": "08cc9036f03ec9ee", "excerpt2": "15dc13a4c11870b0",
                                   "excerpt3": "0dca88d75c99eaaa", "excerpt4": "9b0d2d0c7b4d2c4b"}[NAME],
            "usage_nodes": usage1,
            "usage_edges": usage2,
        },
        "entities": entities,
        "edges": edges,
        "raw_nodes": nodes_raw,
        "raw_edges": edges_raw,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print(f"[done] entities={len(result['entities'])} edges={len(result['edges'])} -> {OUT}", flush=True)

if __name__ == "__main__":
    main()
