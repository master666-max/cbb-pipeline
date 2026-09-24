# -*- coding: utf-8 -*-
"""exp_第五路对照.py — 预注册对照实验：四路基线 vs 四路+LightRAG 第五路（exp/lightrag-fifth-path 分支）。

子命令：
  gen   生成合成查询集 + 预注册判据（落盘后再跑——判据先于结果存在）
  run   执行三臂对照（A 基线四路 / B 四路+第五路RRF / C 第五路单路）并出结果

诚实条款（预注册时写死）：
  · 合成查询集（种子 20260925，机械生成）≠ 真实查询负载；结果只证明该算法在该合成
    分布上的相对增益，不证明生产增益；
  · 第五路以"零查询期 LLM"约束运行（机械关键词代理）——这是对 LightRAG 的下界测试：
    若败，不能得出"LightRAG 无用"（其设计前提是 LLM 抽关键词），只能得出"图游走本身
    在本纪律下无增量"；
  · 精排岗（8081）缺席 → 两臂同落 RRF 序（变量隔离，同形降级 T-5）。
判据（跑之前定死）：
  · 主判据：三查询类宏平均 hit@10——B 比 A 高 ≥5pp=胜（并轨继续）；≥0=平（保留按需件）；
    <0=负（实验件下架，结论落档）；
  · 副判据：类3（描述反查）hit@10 增量；llm_calls 必须=0；引文回落率两臂均=1.0；
    时延与嵌入调用数如实记录。
"""
from __future__ import annotations

import argparse
import base64
import json
import random
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys_path = str(HERE)
if sys_path not in __import__("sys").path:
    __import__("sys").path.insert(0, sys_path)
sys_path = str(HERE.parent / "cbb-store")
if sys_path not in __import__("sys").path:
    __import__("sys").path.insert(0, sys_path)

import 检索层 as jl  # noqa: E402
from neo4j_export import derive_password  # noqa: E402

ROOT = HERE.parent.parent
STORE = ROOT / "迷深实战-本体库"
INDEX = ROOT / "迷深实战-工作区" / "索引" / "lancedb"
EXPDIR = ROOT / "实验-第五路"
SEED = 20260925
BASE = "http://localhost:7695"
NEO4J_BASE = "http://localhost:7695"


# ---------- 查询集生成（确定性） ----------

def _entity_records():
    from neo4j_export import collect_graph
    g = collect_graph(STORE)
    ents, ent_ids = {}, {}
    for n in g["nodes"]:
        ents.setdefault(n["name"], n)
        ent_ids.setdefault(n["name"], n["record_id"])
    return g, ents, ent_ids


def _rec_text(rid: str) -> str:
    hits = list(STORE.glob(f"libraries/*/*/{rid}.json"))
    if not hits:
        return ""
    try:
        rec = json.loads(hits[0].read_text(encoding="utf-8"))
    except Exception:
        return ""
    obs = [o.get("text", "") for o in (rec.get("observations") or []) if o.get("text")]
    return "；".join(obs)


def gen(outdir: Path = EXPDIR) -> None:
    g, ents, ent_ids = _entity_records()
    rng = random.Random(SEED)
    names = sorted(ents)
    picked = rng.sample(names, 60)
    queries: list[dict] = []
    # 类1：实体名直查（校准组）
    for nm in picked[:15]:
        queries.append({"cls": "实体名直查", "q": f"「{nm}」的设定是什么？", "gt": [nm]})
    # 类3：描述反查（去掉实体名的观测文本）
    made3 = 0
    for nm in picked[15:]:
        if made3 >= 15:
            break
        txt = _rec_text(ent_ids[nm])
        snippet = txt.replace(nm, "□").strip("；。 ，")
        if len(snippet) < 12:
            continue
        queries.append({"cls": "描述反查", "q": f"{snippet[:40]}——这是关于谁的设定？", "gt": [nm]})
        made3 += 1
    # 类2：关系对查
    edges = [e for e in g["edges"] if e["subject"] in ents and e["object"] in ents
             and e["subject"] != e["object"]]
    for e in rng.sample(edges, 15):
        queries.append({"cls": "关系对查", "q": f"「{e['subject']}」和「{e['object']}」之间有什么关系？",
                        "gt": [e["subject"], e["object"]]})
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "查询集-v1.json").write_text(json.dumps(
        {"seed": SEED, "n": len(queries), "queries": queries}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    (outdir / "预注册-v1.md").write_text(f"""# 预注册 · 第五路对照实验 v1（2026-09-25，分支 exp/lightrag-fifth-path）

## 判据（生成于跑实验之前）
- 主判据：三查询类宏平均 hit@10——**B（四路+第五路RRF）比 A（四路基线）高 ≥5pp = 胜（并轨继续）；≥0 = 平（保留按需件）；<0 = 负（实验件下架，结论落档）**。
- 副判据：类3（描述反查）hit@10 增量；llm_calls 必须 = 0（零查询期 LLM 验证）；引文回落率两臂均 = 1.0；时延/嵌入调用数如实记录。

## 环境（预注册时点）
- 嵌入端点 127.0.0.1:8080（qwen3-embedding-8b@q4_k_m，4096 维）= up（实验前由 lms 启动）
- 精排端点 8081 = down → 两臂同落 RRF 序（同形降级，变量隔离）
- Neo4j {NEO4J_BASE} = up（基线路④真实接线：别名种子 1-hop）
- LightRAG 1.5.7（pip lightrag-hku）；副本 = 迷深实战-工作区/索引/lightrag-exp（insert_custom_kg 喂入：660 实体/1579 关系/2319 chunks；66 自环/悬挂边跳过已披露）
- 检索层实验钩子：hybrid_search(extra_paths=…)（默认 None 行为不变）

## 诚实条款
1. 合成查询集（种子 {SEED}，机械生成，n={len(queries)}：类1 实体名直查 15 / 类2 关系对查 15 / 类3 描述反查 15）≠ 真实查询负载；结果只证明相对增益。
2. 第五路以**零查询期 LLM**运行（机械关键词=别名命中+标点切分项）——对 LightRAG 是**下界测试**：败≠LightRAG 无用，只=图游走在本纪律下无增量。
3. hit 口径：类1/类3 = GT 实体名进 top-10；类2 = GT 两端名**都在** top-10。
""", encoding="utf-8")
    print(f"✓ 预注册落盘：{outdir/'查询集-v1.json'} + 预注册-v1.md（{len(queries)} 查询）")


# ---------- Neo4j 1-hop（基线路④真实接线） ----------

_PW = None


def _cypher(statement: str, params: dict) -> list[dict]:
    global _PW
    if _PW is None:
        _PW = derive_password(None)
        if not _PW:
            raise RuntimeError("Neo4j 凭据不可得（docker inspect/env）——基线路④无法接线")
    body = json.dumps({"statements": [{"statement": statement, "parameters": params}]}).encode("utf-8")
    req = urllib.request.Request(NEO4J_BASE + "/db/neo4j/tx/commit", data=body,
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Basic " + base64.b64encode(
                                              f"neo4j:{_PW}".encode()).decode()})
    with urllib.request.urlopen(req, timeout=20) as r:
        out = json.loads(r.read().decode("utf-8"))
    if out.get("errors"):
        raise RuntimeError(f"Cypher 错误: {out['errors'][:1]}")
    return out["results"][0]["data"]


def graph_expand_1hop(seeds: list[str]) -> list[str]:
    ext: list[str] = []
    for s in seeds:
        rows = _cypher("MATCH (e:Entity {name:$n})-[r:REL]-(o:Entity) "
                       "WHERE o.name <> $n RETURN o.name AS n LIMIT 8", {"n": s})
        for d in rows:
            n = d["row"][0]
            if n not in ext:
                ext.append(n)
    return ext


# ---------- 三臂对照 ----------

def _hit(gt: list[str], top: list[str]) -> tuple[bool, int]:
    ranks = [top.index(g) + 1 for g in gt if g in top]
    return (len(ranks) == len(gt)), (min(ranks) if ranks else 0)


def run(outdir: Path = EXPDIR, top_k: int = 10) -> None:
    import asyncio
    qset = json.loads((outdir / "查询集-v1.json").read_text(encoding="utf-8"))
    queries = qset["queries"]
    import lightrag_bridge as lb

    # 环境预拨：Neo4j 鉴权/图扩展必须真实可用（失败=中止，不让基线静默缺路④）
    g0, ents0, _ = _entity_records()
    probe = graph_expand_1hop([sorted(ents0)[0]])
    print(f"环境预拨：图扩展 1-hop 返回 {len(probe)} 项")

    results = {"arms": {}, "env": {}}

    def _acc(store: dict, arm: str, qi: int, q: dict, top: list[str], lat: float):
        c = store[arm].setdefault(q["cls"], {"n": 0, "hits": 0, "ranks": [], "cases": []})
        ok, rank = _hit(q["gt"], top)
        c["n"] += 1
        c["hits"] += int(ok)
        if rank:
            c["ranks"].append(rank)
        c["cases"].append({"q": q["q"], "gt": q["gt"], "top": top, "hit": ok, "first_rank": rank})

    # ---- 臂 A：基线四路（无 asyncio 参与） ----
    arm = "A_基线四路"
    results["arms"][arm] = {"per_cls": {}}
    lat_a = []
    for qi, q in enumerate(queries):
        t0 = time.perf_counter()
        rep = jl.hybrid_search(q["q"], STORE, INDEX, top_k=top_k, rerank=True,
                               graph_expand=graph_expand_1hop)
        lat_a.append(time.perf_counter() - t0)
        _acc(results["arms"], arm, qi, q, [t["name"] for t in rep["top"]],
             lat_a[-1])

    # ---- 臂 B/C：共用同一事件循环（跨 loop 会撞 LightRAG 存储锁） ----
    for arm in ("B_四路加第五路", "C_第五路单路"):
        results["arms"][arm] = {"per_cls": {}}
    lat_bc = {a: [] for a in ("B_四路加第五路", "C_第五路单路")}

    async def _drive():
        for arm in ("B_四路加第五路", "C_第五路单路"):
            for qi, q in enumerate(queries):
                t0 = time.perf_counter()
                if arm == "C_第五路单路":
                    rep = await lb.fifth_recall_async(q["q"], STORE, top_k=top_k)
                    top = list(rep["names"])[:top_k]
                    if qi == 0:
                        results["env"]["fifth_sample"] = {k: v for k, v in rep.items()
                                                          if k != "names"}
                else:
                    f = await lb.fifth_recall_async(q["q"], STORE, top_k=top_k)
                    rep = jl.hybrid_search(q["q"], STORE, INDEX, top_k=top_k, rerank=True,
                                           graph_expand=graph_expand_1hop,
                                           extra_paths=[list(f["names"])])
                    top = [t["name"] for t in rep["top"]]
                lat_bc[arm].append(time.perf_counter() - t0)
                _acc(results["arms"], arm, qi, q, top, lat_bc[arm][-1])

    asyncio.run(_drive())

    for arm, r in results["arms"].items():
        p = r["per_cls"]
        r["per_cls"] = {k: {"n": v["n"], "hit@10": round(v["hits"] / v["n"], 4),
                            "MRR": round(sum(1 / rr for rr in v["ranks"]) / v["n"], 4)
                            if v["ranks"] else 0.0}
                        for k, v in p.items()}
        lat = lat_a if arm.startswith("A") else lat_bc[arm]
        r["macro_hit@10"] = round(sum(s["hit@10"] for s in r["per_cls"].values())
                                  / len(r["per_cls"]), 4)
        r["latency_avg_s"] = round(sum(lat) / len(lat), 3)
    results["env"].update({
        "llm_calls": lb.CNT["llm_calls"], "fifth_emb_calls": lb.CNT["emb_calls"],
        "fifth_emb_texts": lb.CNT["emb_texts"],
        "口径": "精排端点缺席→两臂 RRF 序；名字均源于库内实体→引文回落率恒 1.0（不区分臂）"})
    a = results["arms"]["A_基线四路"]["macro_hit@10"]
    b = results["arms"]["B_四路加第五路"]["macro_hit@10"]
    verdict = "胜（并轨继续）" if b - a >= 0.05 else ("平（保留按需件）" if b >= a else "负（实验件下架）")
    results["verdict"] = {"A": a, "B": b, "delta_pp": round((b - a) * 100, 2), "判定": verdict}
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "结果-v1.json").write_text(json.dumps(results, ensure_ascii=False, indent=1),
                                         encoding="utf-8")
    lines = [f"# 第五路对照实验结果 v1（{time.strftime('%Y-%m-%d %H:%M')}）", "",
             f"**判定：{verdict}**（A {a:.1%} → B {b:.1%}，Δ={results['verdict']['delta_pp']}pp）", "",
             "| 臂 | 实体名直查 | 关系对查 | 描述反查 | 宏平均 | 时延/查询 |", "|---|---|---|---|---|---|"]
    for arm, r in results["arms"].items():
        p = r["per_cls"]
        lines.append(f"| {arm} | {p['实体名直查']['hit@10']:.1%} | {p['关系对查']['hit@10']:.1%} "
                     f"| {p['描述反查']['hit@10']:.1%} | **{r['macro_hit@10']:.1%}** "
                     f"| {r['latency_avg_s']}s |")
    lines += ["", f"llm_calls={results['env']['llm_calls']}（必须 0）｜第五路嵌入调用 "
              f"{results['env']['fifth_emb_calls']} 次/{results['env']['fifth_emb_texts']} 文本",
              "", "口径：" + results["env"]["口径"]]
    (outdir / "结果-v1.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["gen", "run"])
    ns = ap.parse_args()
    {"gen": gen, "run": run}[ns.cmd]()
