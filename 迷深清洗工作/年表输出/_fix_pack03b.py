# -*- coding: utf-8 -*-
"""修复 第二章_pack03.json：剔除字符串值中的非法控制字符（<0x20 且非 \n \r \t），
保留其余全部内容。"""
import json, sys

p = r"D:/DeepSeek Harness专用！危险！！！！！/迷深清洗工作2/年表输出/_tmp_全/第二章_pack03.json"
s = open(p, encoding="utf-8").read()

# 找出所有控制字符（允许 \n \r \t）
bad = []
for i, ch in enumerate(s):
    o = ord(ch)
    if o < 0x20 and ch not in "\n\r\t":
        bad.append((i, o))

print("控制字符数:", len(bad))
for i, o in bad[:20]:
    print(f"  pos {i} code {o}")

if bad:
    # 逐个剔除
    cleaned = list(s)
    for i, o in reversed(bad):
        del cleaned[i]
    s2 = "".join(cleaned)
    try:
        data = json.loads(s2)
        print("修复成功! 条数:", len(data))
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("已写回")
    except json.JSONDecodeError as e:
        print("仍失败:", e)
        sys.exit(1)
else:
    print("无非法控制字符")
