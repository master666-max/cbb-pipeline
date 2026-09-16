# -*- coding: utf-8 -*-
"""judge_exam.py — W1 漂移修正：m-prometheus 上岗考试（工单 v1.4 §0；U-C03.5 ③）。

考纲：金标候选好样（U-C00 cands-ch14-excerpt1，对金标 v5 实测 P=1.000）+ 注入坏引文坏样
（中文适配 TRAM/TimE 精神：逐字性/支撑度两轴判别）。分离度=同基项好样分>坏样分的对子占比，
≥0.70 上岗；考不过→judge 评分停用（保守路由：可疑候选全入隔离，宁滥勿漏）。

红线合规（LLM-judge-API-快速接入.md）：rubric 锚定显式必开／temp=0／条目稳定键排序送评
（canonical order）／分数只作内部比较不外报／缓存文件不删。
坏样注入均为机械确定性变异（无 RNG，可复现）：
  char_swap  交换第2/3字符（逐字性破坏·粗）
  punct_mut  括号/标点变体 「→『 等（逐字性破坏·细，判别硬度最高）
  mismatch   换同章他条记录引文（逐字在库但不支撑本断言）
  fabricated 断言文本伪装成引文（无中生有）
用法：py -X utf8 judge_exam.py [--base 12] [--base-url http://127.0.0.1:8080/v1]
产物：评分/judge-exam-<date>.json（全轨迹）+ 评分/llm_judge_cache_exam.json（缓存，不删）
"""
import argparse
import hashlib
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORK = HERE.parent
ROOT = WORK.parent
SCORE_DIR = WORK / "评分"
SLICE = WORK / "slice" / "ch0014.txt"
BASE_CANDS = WORK / "candidates" / "cands-ch14-excerpt1.json"
MODEL = "m-prometheus-14b.i1"

RUBRIC_PROMPT = """你是证据审核员（引文支撑度评分）。给你一条【断言】、一段【引文】和【原文上下文】。按以下锚定标准评分：
- 100：引文在【原文上下文】中逐字存在，且直接支撑断言；
- 70：引文逐字存在，但仅部分支撑断言；
- 40：引文逐字存在，但不支撑断言；
- 0：引文不是【原文上下文】中的原文（逐字性失败，无论内容多么相似）。
逐字=字符级完全一致（含标点与括号方向）。评分只依据引文与上下文/断言的关系，不使用任何外部知识。
只输出 JSON：{{"score": <0-100整数>, "verbatim": <true|false>, "supports": <true|false>}}
【断言】{assertion}
【引文】{quote}
【原文上下文】
{context}"""


def load_base_items(n_base: int) -> list[dict]:
    """金标候选好样：每条取一条可在切片中逐字定位的引文 + 断言文本 + 上下文窗。"""
    cands = json.loads(BASE_CANDS.read_text(encoding="utf-8"))["candidates"]
    slice_lines = SLICE.read_text(encoding="utf-8").split("\n")

    def assertion_of(rec):
        c = rec["canonical"]
        obs = rec.get("observations") or []
        fact = next((o["text"] for o in obs if o.get("text")), "")
        if rec["record_type"] == "entity":
            return f"{c.get('name')}为{c.get('entity_type')}——{fact}"
        if rec["record_type"] == "relation":
            tag = "（声称）" if c.get("claim") else ""
            return f"{c.get('subject')}与{c.get('object')}存在关系「{c.get('rel_type')}」{tag}——{fact}"
        ents = "、".join(c.get("entities") or [])
        return f"{rec['record_type']}记录（涉事：{ents}）——{fact}"

    out = []
    for rec in sorted(cands, key=lambda r: r["record_id"]):
        for ev in rec.get("evidence") or []:
            hits = [i for i, ln in enumerate(slice_lines) if ev["quote"] in ln]
            if not hits:
                continue
            li = hits[0]
            ctx = "\n".join(slice_lines[max(0, li - 8):li + 9])
            out.append({"record_id": rec["record_id"], "type": rec["record_type"],
                        "assertion": assertion_of(rec), "quote": ev["quote"],
                        "context": ctx, "slice_line": li + 1})
            break
    # 类型配额：关系/实体各 40%，事件/伏笔/其余 20%（金标好样主体是关系与实体）
    by_t = {}
    for it in out:
        by_t.setdefault(it["type"], []).append(it)
    quota = {"relation": max(1, n_base * 2 // 5), "entity": max(1, n_base * 2 // 5)}
    picked = []
    for t, q in quota.items():
        picked.extend(by_t.get(t, [])[:q])
    rest = [it for it in out if it not in picked]
    picked.extend(rest[: n_base - len(picked)])
    return sorted(picked, key=lambda x: x["record_id"])[:n_base]


def corruptions(base: dict, all_bases: list[dict]) -> dict:
    """机械确定性坏样×4。逐字性破坏类必须满足『不在上下文窗内』（考卷自检）。"""
    q = base["quote"]
    ctx = base["context"]
    out = {}
    # a. char_swap：交换第2/3字符
    cs = q[0] + q[2] + q[1] + q[3:] if len(q) >= 4 else q
    if cs != q and cs not in ctx:
        out["char_swap"] = cs
    # b. punct_mut：括号/标点细变体
    pm = q
    for a, b in (("「", "『"), ("」", "』"), ("。", "，"), ("、", "，"), ("？", "￮")):
        if a in pm:
            pm = pm.replace(a, b, 1)
            break
    if pm != q and pm not in ctx:
        out["punct_mut"] = pm
    # c. mismatch：同章他条记录引文（须不在本上下文窗内）
    for other in all_bases:
        if other["record_id"] != base["record_id"] and other["quote"] not in ctx:
            out["mismatch"] = other["quote"]
            break
    # d. fabricated：断言文本伪装引文（须不在切片内=无中生有）
    fab = "「" + re.sub(r"[——（）()]|（声称）", "", base["assertion"])[:40] + "」"
    if fab not in ctx:
        out["fabricated"] = fab
    return out


def call_judge(base_url: str, item: dict, cache: dict, key: str) -> dict:
    if key in cache:
        return cache[key]
    prompt = RUBRIC_PROMPT.format(assertion=item["assertion"], quote=item["quote"],
                                  context=item["context"])
    body = json.dumps({"model": MODEL, "temperature": 0,
                       "messages": [{"role": "user", "content": prompt}],
                       "response_format": {"type": "json_schema", "json_schema": {
                           "name": "evidence_verdict", "strict": True,
                           "schema": {"type": "object",
                                      "properties": {"score": {"type": "integer"},
                                                     "verbatim": {"type": "boolean"},
                                                     "supports": {"type": "boolean"}},
                                      "required": ["score", "verbatim", "supports"],
                                      "additionalProperties": False}}}}).encode("utf-8")
    req = urllib.request.Request(base_url.rstrip("/") + "/chat/completions", data=body,
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer lm-studio"})
    raw = None
    for attempt in (1, 2):  # 解析失败重试一次（红线：失败>5%停跑）
        with urllib.request.urlopen(req, timeout=120) as r:
            out = json.load(r)
        raw = out["choices"][0]["message"]["content"]
        try:
            m = re.search(r"\{.*\}", raw, re.S)
            parsed = json.loads(m.group(0))
            score = max(0, min(100, float(parsed["score"])))
            rec = {"score": score, "verbatim": bool(parsed.get("verbatim")),
                   "supports": bool(parsed.get("supports")), "raw": raw[:200]}
            cache[key] = rec
            return rec
        except Exception:
            if attempt == 2:
                rec = {"score": None, "parse_error": True, "raw": (raw or "")[:300]}
                cache[key] = rec
                return rec
            time.sleep(1)


def ck(*parts) -> str:
    return hashlib.sha256(json.dumps(parts, ensure_ascii=False, sort_keys=True)
                          .encode("utf-8")).hexdigest()[:16]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", type=int, default=12)
    ap.add_argument("--base-url", default="http://127.0.0.1:8080/v1")
    ap.add_argument("--date", default=time.strftime("%Y-%m-%d"))
    args = ap.parse_args()

    SCORE_DIR.mkdir(exist_ok=True)
    cache_path = SCORE_DIR / "llm_judge_cache_exam.json"
    cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}

    bases = load_base_items(args.base)
    items = []  # (base_record_id, variant, item_dict)  稳定键排序送评=canonical order
    for b in bases:
        items.append((b["record_id"], "good", {"assertion": b["assertion"],
                                               "quote": b["quote"], "context": b["context"]}))
        for var, badq in corruptions(b, bases).items():
            items.append((b["record_id"], var, {"assertion": b["assertion"],
                                                "quote": badq, "context": b["context"]}))
    items.sort(key=lambda x: ck(*x))

    results = {}
    for rid, var, item in items:
        key = ck(MODEL, item["assertion"], item["quote"], item["context"])
        results[(rid, var)] = call_judge(args.base_url, item, cache, key)
    cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")

    # 判卷：分离对 = 同基项 (good, bad_i)；good.score > bad.score 记分离
    pairs, per_type = [], {}
    parse_fail = 0
    for (rid, var), r in results.items():
        if r.get("parse_error"):
            parse_fail += 1
    for rid, var, _ in items:
        if var == "good":
            continue
        g = results.get((rid, "good"), {}).get("score")
        b = results.get((rid, var), {}).get("score")
        ok = None if (g is None or b is None) else (g > b)
        pairs.append(ok)
        per_type.setdefault(var, []).append(ok)
    sep = (sum(1 for p in pairs if p is True) / len(pairs)) if pairs else 0.0
    parse_rate = parse_fail / max(1, len(results))

    good_scores = [results[(rid, "good")]["score"] for rid, var, _ in items if var == "good"]
    bad_scores = [r["score"] for (rid, var), r in results.items() if var != "good"]
    report = {
        "exam": "W1-m-prometheus-上岗考试", "date": args.date, "model": MODEL,
        "threshold": "separation>=0.70", "n_base": len(bases), "n_calls": len(items),
        "parse_failure_rate": round(parse_rate, 4),
        "separation": round(sep, 4), "pass": sep >= 0.70 and parse_rate <= 0.05,
        "good_mean": round(sum(good_scores) / len(good_scores), 2) if good_scores else None,
        "bad_mean": round(sum(bad_scores) / len(bad_scores), 2) if bad_scores else None,
        "separation_by_variant": {v: round(sum(1 for p in ps if p is True) / len(ps), 4)
                                  for v, ps in per_type.items() if ps},
        "decision_rule": "考过→judge 评分上岗；考不过→评分停用，低分路由改保守默认（可疑候选全入隔离）",
        "trace": [{"base": rid, "variant": var,
                   "score": results[(rid, var)].get("score"),
                   "verbatim": results[(rid, var)].get("verbatim"),
                   "supports": results[(rid, var)].get("supports")}
                  for rid, var, _ in items],
    }
    out_path = SCORE_DIR / f"judge-exam-{args.date}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("separation", "pass", "good_mean", "bad_mean",
                                             "separation_by_variant", "parse_failure_rate",
                                             "n_base", "n_calls")}, ensure_ascii=False))
    print(f"artifact: {out_path}")
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
