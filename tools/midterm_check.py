# -*- coding: utf-8 -*-
"""midterm_check.py — 中期判定机械核验（位200 快照）
①引文全量回原文核验 ②跨距实体（早期章+晚期章同现=跨章身份维护） ③库存分型统计
只读，零写入。
"""
import glob, io, json, os, random, re, sys

LIB = r"D:\zcode专用！！！！危险！！！！！！！！！\正典库构建系统\迷深实战-本体库"
CORPUS = r"D:\zcode专用！！！！危险！！！！！！！！！\语料分析\corpus\clean_full.txt"
random.seed(20260922)

full = io.open(CORPUS, encoding="utf-8").read()
full_norm = re.sub(r"\s", "", full)  # 去所有空白做宽松匹配

def q_ok(q):
    if not q or len(q) < 8:
        return None  # 过短不判
    if q in full:
        return True
    if re.sub(r"\s", "", q) in full_norm:
        return True
    return False

recs = []
for p in glob.glob(os.path.join(LIB, "libraries", "*", "provisional", "*.json")):
    try:
        r = json.load(io.open(p, encoding="utf-8"))
    except Exception as e:
        recs.append({"_parse_error": f"{p}: {e}"})
        continue
    r["_path"] = p
    recs.append(r)

parse_err = [r for r in recs if "_parse_error" in r]
recs = [r for r in recs if "_parse_error" not in r]
print(f"记录总数={len(recs)} 解析错误={len(parse_err)}")
for e in parse_err[:3]: print("  ", e["_parse_error"][:120])

# 分型统计
from collections import Counter
by_lib = Counter(os.path.basename(os.path.dirname(os.path.dirname(r["_path"]))) for r in recs)
by_type = Counter((r.get("record_type") or r.get("type") or "?") for r in recs)
print("按库:", dict(by_lib))
print("按型:", dict(by_type))

# 引文核验 + 跨距
checked = pass_n = fail_n = short_n = 0
fails = []
span = {}  # canonical name -> set(chapters)
for r in recs:
    ev = r.get("evidence") or []
    if isinstance(ev, dict): ev = [ev]
    chs = set()
    for e in ev:
        q = e.get("quote") or e.get("引文") or ""
        ch = e.get("chapter") or e.get("章")
        if ch is not None:
            try: chs.add(int(ch))
            except Exception: pass
        ok = q_ok(q)
        if ok is None: short_n += 1; continue
        checked += 1
        if ok: pass_n += 1
        else:
            fail_n += 1
            if len(fails) < 8: fails.append((r["_path"].split(os.sep)[-1], q[:40], ch))
    name = r.get("canonical", {}).get("name") if isinstance(r.get("canonical"), dict) else r.get("name")
    if name and chs:
        span.setdefault(name, set()).update(chs)

print(f"引文核验: 受检={checked} 通过={pass_n} 失败={fail_n} 过短跳过={short_n}")
for f in fails: print("  失败样例:", f)
cross = [(n, min(c), max(c)) for n, c in span.items() if min(c) < 100 and max(c) > 150]
print(f"跨距实体(区分<100且>150章): {len(cross)} 个; 样例:")
for n, a, b in sorted(cross, key=lambda x: -(x[2]-x[1]))[:5]:
    print(f"   {n}: ch{a}~ch{b} 跨度{b-a}")

# 别名账
al = io.open(os.path.join(LIB, "aliases.jsonl"), encoding="utf-8").read().strip().splitlines()
print(f"别名账 {len(al)} 行; 样例3行:")
for l in al[-3:]:
    try:
        d = json.loads(l); print("   ", str(d)[:110])
    except Exception: print("   [坏行]", l[:80])
