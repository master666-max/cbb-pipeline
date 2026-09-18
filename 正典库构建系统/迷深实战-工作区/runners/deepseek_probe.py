# -*- coding: utf-8 -*-
"""deepseek_probe.py — U-C03 段收口第三方抽检（工单 v1.8 补遗 §0；主抽取付费禁令的唯一例外）。

流程：选章（date 种子确定性抽样）→ deepseek-flash 独立重抽（紧凑契约提示词，D-004 凭证只走环境变量）
→ 与库内我方抽取机械比对（专名集合：一致/我方独有/DeepSeek独有）→ 分歧条目入隔离区
contradiction_pending（source=deepseek-probe，第三方对抗 R-019；只登记不裁决）→ 报告+费用台账。
红线：key 不落盘不输出；谷价费用为估算（工作单口径 ≈¥3.6/M token 混合价），累计达 ¥7 永久停用。
用法：py -X utf8 deepseek_probe.py --chapters 113,126 [--model deepseek-flash] [--base-url https://api.deepseek.com]
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORK = HERE.parent
ROOT = WORK.parent
STORE = ROOT / "迷深实战-本体库"
OUT_DIR = WORK / "评分" / "deepseek-probe"
sys.path.insert(0, str(ROOT / "cbb" / "contracts"))
sys.path.insert(0, str(ROOT / "cbb" / "cbb-store"))
sys.path.insert(0, str(ROOT / "cbb" / "cbb-quarantine"))
import cbb_store  # noqa: E402,F401  （先导入以初始化共享 sys.path）
from cbb_quarantine import QuarantineZone  # noqa: E402

PROMPT = """你是小说正典知识库的抽取审核员（第三方独立重抽，用于与另一抽取器交叉比对）。
从下面《章节文本》抽取正典事实，只输出 JSON（UTF-8，无围栏无解释）：
{"entities": [{"name": "专名", "entity_type": "人物|组织|地点|物品|技能魔法|概念|事件", "summary": "≤30字"}],
 "relations": [{"subject": "", "rel_type": "≤6字", "object": "", "claim": "≤20字"}],
 "events": [{"name": "事件名", "chapter": 章号, "summary": "≤30字"}]}
纪律：只抽正文事实（人名/地名/组织/道具/魔法/关键事件与关系）；忽略翻译组署名/吐槽注/插图行；
实体名保留『』书名号内原文；宁缺勿编造。逐字引用不需要——本轮只比对专名集合与关系骨架。
《章节文本》
"""


def _norm_name(s: str) -> str:
    """括号/空白归一（『』《》「」与首尾空白——比对层伪差消除，不改动任何一侧原始名）。"""
    return re.sub(r"^[『』《》「」\s]+|[『』《》「」\s]+$", "", str(s or ""))


def call_deepseek(base_url, model, chapter_text, timeout=300):
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        raise SystemExit("缺环境变量 DEEPSEEK_API_KEY（D-004：凭证只走环境变量，不落盘）")
    body = json.dumps({
        "model": model, "temperature": 0, "max_tokens": 24000,
        "messages": [{"role": "user", "content": PROMPT + chapter_text}],
    }).encode("utf-8")
    req = urllib.request.Request(base_url.rstrip("/") + "/chat/completions", data=body,
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {key}"})
    t0 = time.time()
    parsed, content, usage = None, "", {}
    for attempt in (1, 2):  # JSON 解析失败重试一次（judge_exam 同款纪律）
        with urllib.request.urlopen(req, timeout=timeout) as r:
            out = json.load(r)
        content = out["choices"][0]["message"]["content"]
        usage = out.get("usage") or {}
        m = re.search(r"\{.*\}", content, re.S)
        try:
            if m:
                parsed = json.loads(m.group(0))
                break
        except json.JSONDecodeError:
            if attempt == 2:
                parsed = None
    return parsed, {"prompt_tokens": usage.get("prompt_tokens"),
                    "completion_tokens": usage.get("completion_tokens"),
                    "elapsed_s": round(time.time() - t0, 1),
                    "hour_local": datetime.datetime.now().hour,
                    "raw_head": content[:200]}


def our_names(ch_no: int) -> dict:
    """我方侧名集合=canonical 名 ∪ 库内别名（别名感知比对——'基督'/'基督·欧亚' 类伪差消除）。"""
    cands = json.loads((WORK / "candidates" / f"cands-ch{ch_no:04d}.json").read_text(encoding="utf-8"))
    ents, rels = set(), set()
    for c in cands["candidates"]:
        cn = c.get("canonical") or {}
        if c["record_type"] == "entity" and cn.get("name"):
            ents.add(cn["name"])
        elif c["record_type"] == "relation":
            rels.add((cn.get("subject"), cn.get("rel_type"), cn.get("object")))
    id2name = {}
    for lib in ("character", "setting"):
        d = STORE / "libraries" / lib / "provisional"
        for f in d.glob("*.json") if d.exists() else []:
            try:
                r = json.loads(f.read_text(encoding="utf-8"))
                id2name[r["record_id"]] = (r.get("canonical") or {}).get("name")
            except Exception:
                continue
    for a in [json.loads(x) for x in
              (STORE / "aliases.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]:
        if isinstance(a.get("alias"), str):
            ents.add(a["alias"])
            nm = id2name.get(a.get("entity_id"))
            if nm:
                ents.add(nm)
    return {"entities": ents, "relations": rels}


def probe(ch_no: int, base_url: str, model: str, register: bool) -> dict:
    slice_path = WORK / "slice" / f"ch{ch_no:04d}.txt"
    text = slice_path.read_text(encoding="utf-8")
    theirs, meta = call_deepseek(base_url, model, text)
    if theirs is None:
        return {"chapter": ch_no, "status": "parse_error", **meta}
    # 比对层括号归一（原始名留档 theirs_entities_raw）
    raw_ents = [e.get("name") for e in theirs.get("entities", []) if e.get("name")]
    t_ents = {_norm_name(n) for n in raw_ents}
    t_rels = {(_norm_name(r.get("subject")), r.get("rel_type"), _norm_name(r.get("object")))
              for r in theirs.get("relations", []) if r.get("subject") and r.get("object")}
    ours = our_names(ch_no)
    ours_n = {_norm_name(n) for n in ours["entities"]}
    agree = sorted(ours_n & t_ents)
    ours_only = sorted(ours_n - t_ents)
    theirs_only = sorted(t_ents - ours_n)
    # 三元组骨架比对：主体+宾体对齐（rel_type 措辞差异不算分歧；括号归一后比对）
    ours_pair = {(_norm_name(s), _norm_name(o)) for s, _, o in ours["relations"]}
    theirs_pair = {(s, o) for s, _, o in t_rels}
    rel_agree = len(ours_pair & theirs_pair)
    rel_disagree = sorted(
        f"{s}→{o}" for s, o in (ours_pair ^ theirs_pair))[:40]
    # 分歧登记（第三方对抗，只登记不裁决）
    zone = QuarantineZone(STORE / "quarantine-zone")
    reg = []
    if register:
        for n in theirs_only:
            iid, _ = zone.register(
                group="entity_unalignable",
                detail=f"第三方抽检分歧：DeepSeek 独有实体 {n!r}（我方 ch{ch_no:04d} 未抽）",
                record_id=f"deepseek-ch{ch_no:04d}", source="deepseek-probe",
                subclass="contradiction_pending")
            reg.append(iid)
    return {"chapter": ch_no, "status": "ok",
            "entity_counts": {"ours": len(ours_n), "theirs": len(t_ents),
                              "agree": len(agree)},
            "entity_agreement": round(len(agree) / max(1, len(ours_n | t_ents)), 4),
            "ours_only": ours_only[:40], "theirs_only": theirs_only[:60],
            "theirs_entities_raw": raw_ents,
            "theirs_only_registered": len(reg),
            "relation_pairs": {"ours": len(ours_pair), "theirs": len(theirs_pair),
                               "agree": rel_agree, "disagree_sample": rel_disagree},
            "quarantine_registered": reg, "usage": meta}


def pick_chapters(seed: str, pool: list[int], k: int = 2) -> list[int]:
    h = hashlib.sha256(seed.encode()).hexdigest()
    idx = sorted({int(h[i:i + 4], 16) % len(pool) for i in range(0, len(h) - 4, 4)})[:k]
    return [pool[i] for i in idx]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chapters", help="逗号分隔章号；缺省=date 种子确定性抽样")
    ap.add_argument("--model", default="deepseek-flash")
    ap.add_argument("--base-url", default="https://api.deepseek.com")
    ap.add_argument("--no-register", action="store_true")
    args = ap.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.chapters:
        chapters = [int(x) for x in args.chapters.split(",")]
    else:
        pool = sorted({int(p.stem[2:]) for p in (WORK / "slice").glob("ch*.txt")
                       if p.stem[2:].isdigit()
                       and (WORK / "candidates" / f"cands-{p.stem}.json").exists()
                       and len((WORK / "candidates" / f"cands-{p.stem}.json").read_text(encoding="utf-8")) > 2000})
        chapters = pick_chapters(f"U-C03-segment-{time.strftime('%Y-%m-%d')}", pool)
    results = [probe(c, args.base_url, args.model, register=not args.no_register)
               for c in chapters]
    # 费用台账（谷价混合估算 ≈¥3.6/M token；峰时 9-12/14-18 点 ×2——本窗口为闲时任务=谷时段）
    tot_in = sum((r.get("usage") or {}).get("prompt_tokens") or 0 for r in results)
    tot_out = sum((r.get("usage") or {}).get("completion_tokens") or 0 for r in results)
    cost = round((tot_in + tot_out) / 1e6 * 3.6, 4)
    report = {"date": time.strftime("%Y-%m-%d"), "model": args.model,
              "chapters": chapters, "results": results,
              "ledger": {"in_tokens": tot_in, "out_tokens": tot_out,
                         "est_cost_valley_rmb": cost,
                         "note": "累计估算达 ¥7 即永久停用（工单 v1.9 预算制）；key 走环境变量不落盘"},
              }
    out = OUT_DIR / f"deepseek-probe-{time.strftime('%Y%m%d')}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"chapters": chapters, "cost_rmb": cost,
                      "entity_agreement": [r.get("entity_agreement") for r in results],
                      "theirs_only_registered": [r.get("theirs_only_registered") for r in results],
                      "out": str(out.name)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
