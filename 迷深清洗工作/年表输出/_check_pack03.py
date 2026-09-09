# -*- coding: utf-8 -*-
"""检查 第二章_pack03.json 的 event_id 分布与结构问题"""
import json, re

p = r"D:/DeepSeek Harness专用！危险！！！！！/迷深清洗工作2/年表输出/_tmp_全/第二章_pack03.json"
s = open(p, encoding="utf-8").read()

idxs = [m.start() for m in re.finditer(r'"event_id"', s)]
print("event_id 出现次数:", len(idxs))
for i, ix in enumerate(idxs):
    seg = s[ix:ix+60]
    print(i, repr(seg))
