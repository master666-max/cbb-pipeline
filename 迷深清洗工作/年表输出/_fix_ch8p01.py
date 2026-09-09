# -*- coding: utf-8 -*-
"""诊断并修复 JSON 字符串内非法控制字符（字面换行/未转义引号等）"""
import json, sys

p = r"D:/DeepSeek Harness专用！危险！！！！！/迷深清洗工作2/年表输出/_tmp_全/第八章_pack01.json"
s = open(p, encoding="utf-8").read()
try:
    d = json.loads(s)
    print("OK valid:", len(d))
    sys.exit(0)
except json.JSONDecodeError as e:
    print("ERR:", e)
    print("上下文:", repr(s[max(0,e.pos-100):e.pos+80]))
