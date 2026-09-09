# -*- coding: utf-8 -*-
"""修复 第7-3章_pack02.json：
将损坏的 '",""\n' 段（description 错误闭合后多出的空字符串）修复为 '",\n'。"""
import json, re

p = r"D:/DeepSeek Harness专用！危险！！！！！/迷深清洗工作2/年表输出/_tmp_全/第7-3章_pack02.json"
s = open(p, encoding="utf-8").read()

# 模式：'", ""\n'——即前一个字符串闭合后出现 ', ""' 空字符串
s2, n = re.subn(r'",\s*""\n', '",\n', s)
print("替换数:", n)
if n == 0:
    # 尝试更宽松：找 ", "" 或 "" 独立出现
    for m in re.finditer(r'",\s*""', s):
        print("残留 @", m.start(), repr(s[m.start()-40:m.start()+20]))
    s2 = s

try:
    data = json.loads(s2)
    print("修复成功! 条数:", len(data))
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print("已写回")
except json.JSONDecodeError as e:
    print("仍失败:", e)
    print("位置上下文:", repr(s2[max(0,e.pos-60):e.pos+60]))