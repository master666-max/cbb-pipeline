# -*- coding: utf-8 -*-
"""仅修复字符串内部的字面 \n / \r（控制字符），不动引号。"""
import json, sys

def fix(s):
    out = []
    in_str = False
    escaped = False
    fixes = 0
    i, n = 0, len(s)
    while i < n:
        ch = s[i]
        if in_str:
            if escaped:
                out.append(ch); escaped = False; i += 1; continue
            if ch == "\\":
                out.append(ch); escaped = True; i += 1; continue
            if ch == '"':
                out.append(ch); in_str = False; i += 1; continue
            if ch == "\n" or ch == "\r":
                out.append("\\n" if ch == "\n" else "\\r"); fixes += 1; i += 1; continue
            out.append(ch); i += 1; continue
        else:
            if ch == '"':
                in_str = True
            out.append(ch); i += 1; continue
    return "".join(out), fixes

path = sys.argv[1]
s = open(path, encoding="utf-8").read()
try:
    d = json.loads(s); print("原本有效:", len(d)); sys.exit(0)
except Exception:
    pass
s2, fixes = fix(s)
print("修复换行数:", fixes)
try:
    d = json.loads(s2)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    print("修复成功! 条数:", len(d), "已写回")
except json.JSONDecodeError as e:
    print("仍失败:", e)
    print("上下文:", repr(s2[max(0,e.pos-80):e.pos+80]))
