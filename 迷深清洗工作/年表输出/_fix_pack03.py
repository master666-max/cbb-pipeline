# -*- coding: utf-8 -*-
"""修复 第二章_pack03.json 中第10条 description 的未转义换行/引号问题"""
import json, re, sys

p = r"D:/DeepSeek Harness专用！危险！！！！！/迷深清洗工作2/年表输出/_tmp_全/第二章_pack03.json"
s = open(p, encoding="utf-8").read()
try:
    data = json.loads(s)
    print("OK already valid:", len(data))
    sys.exit(0)
except json.JSONDecodeError as e:
    print("ERR:", e)
    # 定位错误行
    lines = s.split("\n")
    lineno = e.lineno
    print("错误行号:", lineno)
    for i in range(max(0,lineno-3), min(len(lines), lineno+3)):
        print(i+1, "|", lines[i][:120])
