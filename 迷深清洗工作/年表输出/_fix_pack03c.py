# -*- coding: utf-8 -*-
"""修复 JSON 中字符串内部的字面换行/回车：扫描时跟踪 in-string 状态，
将字符串内的原始 \n / \r 转义为 \\n / \\r，其余保持原样。"""
import json, sys

p = r"D:/DeepSeek Harness专用！危险！！！！！/迷深清洗工作2/年表输出/_tmp_全/第二章_pack03.json"
s = open(p, encoding="utf-8").read()

out = []
in_str = False
escaped = False
fixes = 0
for ch in s:
    if in_str:
        if escaped:
            out.append(ch)
            escaped = False
            continue
        if ch == "\\":
            out.append(ch)
            escaped = True
            continue
        if ch == '"':
            out.append(ch)
            in_str = False
            continue
        if ch == "\n" or ch == "\r":
            # 字符串内的字面换行 → 转义
            out.append("\\n" if ch == "\n" else "\\r")
            fixes += 1
            continue
        out.append(ch)
        continue
    else:
        if ch == '"':
            in_str = True
            out.append(ch)
            continue
        out.append(ch)

print("字符串内字面换行转义数:", fixes)
s2 = "".join(out)
try:
    data = json.loads(s2)
    print("修复成功! 条数:", len(data))
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("已写回")
except json.JSONDecodeError as e:
    print("仍失败:", e)
    print("错误处:", repr(s2[e.pos-60:e.pos+60]))
    sys.exit(1)
