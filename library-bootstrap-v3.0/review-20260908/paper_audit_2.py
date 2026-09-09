# -*- coding: utf-8 -*-
"""二轮：L8/L9 内容体交付覆盖 + 关键机制原文取证。"""
import json, importlib.util, re
from pathlib import Path

ROOT = Path(r"D:\zcode专用！！！！危险！！！！！！！！！")
SRC = ROOT / "library-bootstrap-v3.0" / "bootstrap_v3.py"
BODIES = ROOT / "library-bootstrap-v3.0" / "bootstrap_data" / "bodies.json"
spec = importlib.util.spec_from_file_location("bsv3", SRC)
bs = importlib.util.module_from_spec(spec); spec.loader.exec_module(bs)
bodies = json.loads(BODIES.read_text(encoding="utf-8"))

# 复刻 _deliver 的 prefix 构造，检查 L8/L9 下哪些内容体目录会被交付
def prefixes_for(level):
    n = int(level[1:])
    mods, missing = bs.resolve(level, [])
    pre = ["SKILL.md", "references", "adapters"]
    pre += [f"presets/L{i}.md" for i in range(n + 1)] + ["presets/CUSTOM.md"]
    for m in mods:
        if m.startswith("x:") or m in ("dirs", "laws"): continue
        pre += bs.MODULE_MAPPING.get(m, [])
    return sorted(set(pre))

def delivered(rel, pre):
    return any(rel == p or rel.startswith(p.rstrip("/") + "/") for p in pre)

all_src = []
for slot, items in bodies.items():
    if not isinstance(items, dict): continue
    for k, v in items.items():
        all_src.append((slot, v.get("src", "").replace("\\", "/")))

for lv in ("L7", "L8", "L9"):
    pre = prefixes_for(lv)
    print(f"===== {lv} 交付前缀: {pre}")
    top = {}
    for slot, rel in all_src:
        if rel.split("/")[0] in ("experimental-l8", "experimental-l9", "experimental"):
            head = "/".join(rel.split("/")[:2])
            top.setdefault(head, [0, 0])
            top[head][1] += 1
            if delivered(rel, pre): top[head][0] += 1
    for head in sorted(top):
        d, t = top[head]
        flag = "全交付" if d == t else ("部分 " + str(d) + "/" + str(t) if d else "★不交付")
        print(f"  {head:42s} {flag}")

# 关键机制原文取证
def find(keyword, n=2, width=160):
    out = []
    for slot, items in bodies.items():
        if not isinstance(items, dict): continue
        for k, v in items.items():
            t = v.get("body", "")
            for m in re.finditer(re.escape(keyword), t):
                s = max(0, m.start()-60); e = min(len(t), m.end()+width)
                out.append((k, t[s:e].replace("\n", " ")[:width+60]))
                if len(out) >= n: return out
    return out

for kw in ["心境一致", "唤起度", "PageRank", "PPR", "页调度", "热温冷", "艾宾浩斯", "NOOP", "去重", "双速率", "默认模式"]:
    hits = find(kw, 1)
    print(f"\n--- 「{kw}」 ---")
    for k, snip in hits: print(f"  [{k}] {snip}")
    if not hits: print("  (内容体中 0 命中)")
