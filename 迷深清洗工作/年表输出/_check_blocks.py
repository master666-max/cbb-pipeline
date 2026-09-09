# -*- coding: utf-8 -*-
"""确认各章 pack 总 block 范围"""
import re, glob, os

BASE = r"D:/DeepSeek Harness专用！危险！！！！！/迷深清洗工作2/年表输出/_packs"
CHS = ["第一章_挑战的开始","第二章_于圣诞祭的最后","第三章_为了得不到报偿的你",
       "第四章_我与你存在于此的证明","第五章_庭师与无名者的物语","第六章_仅此二人的家庭",
       "第7-1章_爱的告白","第7-2章_生命的价值","第7-3章_比起爱与生命",
       "第八章_最终章","第九章_无尽的梦之延续","第十章_致以久远的天空为目标的人们"]

def blocks_of(f):
    ids = []
    for line in open(f, encoding="utf-8"):
        m = re.search(r"block_id[:\s]*[^\s]*?(\d+)", line)
        if m:
            ids.append(int(m.group(1)))
    return ids

for ch in CHS:
    d = os.path.join(BASE, ch)
    packs = sorted(glob.glob(os.path.join(d, "pack_*.md")),
                   key=lambda x: int(re.search(r"pack_(\d+)", x).group(1)))
    if not packs:
        print(ch, "无包")
        continue
    fb = blocks_of(packs[0])
    lb = blocks_of(packs[-1])
    lo = fb[0] if fb else "?"
    hi = lb[-1] if lb else "?"
    print("%-32s %2d包 block %s ~ %s" % (ch, len(packs), lo, hi))
