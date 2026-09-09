# -*- coding: utf-8 -*-
"""通用 JSON 修复器：
1. 字符串内部的字面 \n / \r → 转义为 \\n / \\r
2. 字符串内部未转义的半角双引号（其后为中文/全角/字母内容）→ 转义为 \\"
用法: py _fix_generic.py <file>
"""
import json, sys

def fix(s):
    out = []
    in_str = False
    escaped = False
    fixes = [0, 0]  # [换行, 引号]
    i, n = 0, len(s)
    while i < n:
        ch = s[i]
        if in_str:
            if escaped:
                out.append(ch); escaped = False; i += 1; continue
            if ch == "\\":
                out.append(ch); escaped = True; i += 1; continue
            if ch == '"':
                nxt = s[i+1] if i+1 < n else ""
                if nxt and nxt != "," and nxt != "}" and nxt != "]" and not nxt.isspace():
                    out.append('\\"'); fixes[1] += 1; i += 1; continue
                out.append(ch); in_str = False; i += 1; continue
            if ch == "\n" or ch == "\r":
                out.append("\\n" if ch == "\n" else "\\r"); fixes[0] += 1; i += 1; continue
            out.append(ch); i += 1; continue
        else:
            if ch == '"':
                in_str = True
            out.append(ch); i += 1; continue
    return "".join(out), fixes

def main(path):
    s = open(path, encoding="utf-8").read()
    try:
        d = json.loads(s)
        print("原本有效:", len(d))
        return
    except Exception:
        pass
    s2, fixes = fix(s)
    print("修复: 换行%d 引号%d" % tuple(fixes))
    try:
        d = json.loads(s2)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
        print("修复成功! 条数:", len(d), "已写回")
    except json.JSONDecodeError as e:
        print("仍失败:", e)
        print("上下文:", repr(s2[max(0,e.pos-80):e.pos+80]))

if __name__ == "__main__":
    main(sys.argv[1])
