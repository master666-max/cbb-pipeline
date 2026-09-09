# -*- coding: utf-8 -*-
"""分析 _tmp_全/ 各产出文件的 block 覆盖，输出每章的 block 覆盖区间，辅助判断补跑"""
import json, re, os, glob

TMP = r"D:/DeepSeek Harness专用！危险！！！！！/迷深清洗工作2/年表输出/_tmp_全"

def block_range(evs):
    ids = set()
    for e in evs:
        m = re.findall(r"md-(\d+)", e.get("story_anchor", "") or "")
        for x in m:
            ids.add(int(x))
    return (min(ids), max(ids), len(ids)) if ids else (None, None, 0)

for fp in sorted(glob.glob(os.path.join(TMP, "*.json"))):
    try:
        d = json.load(open(fp, encoding="utf-8"))
        lo, hi, n = block_range(d)
        print(f"{os.path.basename(fp):28s} {len(d):3d}条  block: {lo}~{hi} ({n}块)")
    except Exception as e:
        print(f"{os.path.basename(fp):28s} ERR {e}")
