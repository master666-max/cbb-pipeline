# -*- coding: utf-8 -*-
import json

p = r"D:/DeepSeek Harness专用！危险！！！！！/迷深清洗工作2/年表输出/_tmp_全/第7-3章_pack02.json"
s = open(p, encoding="utf-8").read()
# 找紧邻 ',\n "characters"' 前面的 '"",' 或 ',""'
import re
for m in re.finditer(r'",\s*"",\s*\n\s*"characters"', s):
    print("模式1 @", m.start(), repr(s[m.start()-60:m.start()+40]))
for m in re.finditer(r'"",\s*\n\s*"characters"', s):
    print("模式2 @", m.start(), repr(s[m.start()-50:m.start()+40]))
# 找characters前50
i = s.find('"characters"')
print("首个characters@", i, repr(s[i-70:i+20]))