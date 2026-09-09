# -*- coding: utf-8 -*-
"""修复 JSON 字符串值内未转义的半角双引号。
策略：进入字符串后，若遇到紧跟中文字符（前/后是中文或标点）的 '"'，
视为内容引号，替换为全角「」或转义。为稳妥，直接扫描所有 '"' 出现，
检测是否为未转义且非结构化分隔。
"""
import json, re

p = r"D:/DeepSeek Harness专用！危险！！！！！/迷深清洗工作2/年表输出/_tmp_全/第八章_pack01.json"
s = open(p, encoding="utf-8").read()

# 方法：逐字符扫描，跟踪 in_string / escaped。
# 收集所有"字符串内容中疑似未转义引号"位置。
out = []
in_str = False
escaped = False
fixes = 0
i = 0
n = len(s)
while i < n:
    ch = s[i]
    if in_str:
        if escaped:
            out.append(ch); escaped = False; i += 1; continue
        if ch == "\\":
            out.append(ch); escaped = True; i += 1; continue
        if ch == '"':
            # 字符串内引号：判断是否可能是内容引号（其后有中文或闭合后不合法）
            nxt = s[i+1] if i+1 < n else ""
            # 若下一字符是中文/全角标点/引号，则视为内容引号（未转义）
            if nxt and (not nxt.isspace()) and nxt not in ',}]':
                # 视为内容引号，转义
                out.append('\\"')
                fixes += 1
                i += 1
                continue
            out.append(ch); in_str = False; i += 1; continue
        out.append(ch); i += 1; continue
    else:
        if ch == '"':
            in_str = True
            out.append(ch); i += 1; continue
        out.append(ch); i += 1; continue

print("修复引号数:", fixes)
s2 = "".join(out)
try:
    d = json.loads(s2)
    print("修复成功! 条数:", len(d))
    with open(p, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    print("已写回")
except json.JSONDecodeError as e:
    print("仍失败:", e)
    print("上下文:", repr(s2[max(0,e.pos-80):e.pos+80]))