# -*- coding: utf-8 -*-
"""embed_dedup_scan.py — 批收口嵌入相似度查重扫描（工单 v1.2 §0②；U-C01 工具件1）。

新候选实体 vs 库内实体：Qwen3-Embedding-8B（LM Studio /v1/embeddings，127.0.0.1:8080）+余弦。
分档（工单裁决阈值）：≥0.95 疑似重复（走 cbb-store 双轨合并流程复核）；0.85~0.95 存疑
（登记 quarantine 只提示不静默合并）；<0.85 放行。探活失败=blocked 退出码 2，不阻塞主链。

纯函数核心（cosine/bucket/scan）零网络零依赖，单测见 test_embed_dedup_scan.py。

用法：
  py -X utf8 cbb/tools/embed_dedup_scan.py --cands <cands.json> --store <本体库根> \
      [--api http://127.0.0.1:8080] [--out scan.json] [--model Qwen3-Embedding-8B]
"""
import argparse
import json
import math
import sys
import urllib.request
from pathlib import Path

DUP_TAU = 0.95
UNCERTAIN_TAU = 0.85


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0


def bucket(sim: float) -> str:
    if sim >= DUP_TAU:
        return "dup_suspect"
    if sim >= UNCERTAIN_TAU:
        return "uncertain"
    return "ok"


def scan(cand_texts: list[str], lib_texts: list[str], embed_fn) -> dict:
    """embed_fn(texts:list[str])->list[vector]；返回 {dup_suspect:[…], uncertain:[…], pairs:[[cand,lib,sim],…]}。
    纯对比层：不做任何合并动作（只提示不静默）。"""
    if not cand_texts or not lib_texts:
        return {"dup_suspect": [], "uncertain": [], "pairs": []}
    vecs_c = embed_fn(cand_texts)
    vecs_l = embed_fn(lib_texts)
    dup, unc, pairs = [], [], []
    for ci, ct in enumerate(cand_texts):
        best = max(((cosine(vecs_c[ci], vecs_l[li]), li) for li in range(len(lib_texts))),
                   key=lambda t: t[0])
        pairs.append([ct, lib_texts[best[1]], round(best[0], 4)])
        b = bucket(best[0])
        if b == "dup_suspect":
            dup.append({"candidate": ct, "library_match": lib_texts[best[1]], "similarity": round(best[0], 4)})
        elif b == "uncertain":
            unc.append({"candidate": ct, "library_match": lib_texts[best[1]], "similarity": round(best[0], 4)})
    return {"dup_suspect": dup, "uncertain": unc, "pairs": pairs}


# ---- HTTP 层（LM Studio /v1/embeddings，stdlib urllib） ----

def http_get(url: str, timeout: int = 4) -> dict | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return None


def http_embed(api: str, texts: list[str], model: str, timeout: int = 120) -> list[list[float]]:
    body = json.dumps({"input": texts, "model": model}).encode("utf-8")
    req = urllib.request.Request(f"{api.rstrip('/')}/v1/embeddings", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode("utf-8"))
    order = {d["index"]: d["embedding"] for d in data["data"]}
    return [order[i] for i in range(len(texts))]


def probe(api: str) -> str | None:
    """探活并取当前模型 id；服务不在/非嵌入模型 → None（调用方标 blocked）。"""
    j = http_get(f"{api.rstrip('/')}/v1/models")
    if not j or not j.get("data"):
        return None
    return j["data"][0].get("id")


def collect_entity_names(cands: dict, store_root: Path) -> tuple[list[str], list[str]]:
    """候选实体名（本批）与库内活实体名（含别名表）。"""
    cand = [c["canonical"]["name"] for c in cands.get("candidates", [])
            if c.get("record_type") == "entity" and isinstance(c.get("canonical"), dict)
            and c["canonical"].get("name")]
    lib = set()
    for f in Path(store_root).glob("libraries/*/provisional/*.json"):
        rec = json.loads(f.read_text(encoding="utf-8"))
        if rec.get("record_type") == "entity" and (rec.get("canonical") or {}).get("name"):
            lib.add(rec["canonical"]["name"])
    for f in Path(store_root).glob("libraries/*/confirmed/*.json"):
        rec = json.loads(f.read_text(encoding="utf-8"))
        if rec.get("record_type") == "entity" and (rec.get("canonical") or {}).get("name"):
            lib.add(rec["canonical"]["name"])
    for ln in (Path(store_root) / "aliases.jsonl").read_text(encoding="utf-8").splitlines() if \
            (Path(store_root) / "aliases.jsonl").exists() else []:
        a = json.loads(ln)
        lib.add(a["alias"])
    return cand, sorted(lib)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="批收口嵌入相似度查重（≥0.95 疑重/0.85~0.95 存疑，只提示不静默）")
    ap.add_argument("--cands", required=True)
    ap.add_argument("--store", required=True)
    ap.add_argument("--api", default="http://127.0.0.1:8080")
    ap.add_argument("--model", default="Qwen3-Embedding-8B")
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    model_id = probe(args.api)
    if model_id is None:
        print(json.dumps({"status": "blocked", "reason": f"LM Studio {args.api} 探活失败（嵌入档未载入）"}, ensure_ascii=False))
        return 2
    if "embed" not in (model_id or "").lower():
        print(json.dumps({"status": "blocked", "reason": f"当前模型 {model_id} 非嵌入模型（显存调度：载入 Qwen3-Embedding-8B 后重试）"}, ensure_ascii=False))
        return 2
    cands = json.loads(Path(args.cands).read_text(encoding="utf-8"))
    cand_names, lib_names = collect_entity_names(cands, Path(args.store))
    result = scan(cand_names, lib_names, lambda ts: http_embed(args.api, ts, model_id))
    result["status"] = "ok"
    result["model"] = model_id
    result["counts"] = {"candidates": len(cand_names), "library": len(lib_names),
                        "dup_suspect": len(result["dup_suspect"]), "uncertain": len(result["uncertain"])}
    if args.out:
        Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(result["counts"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
