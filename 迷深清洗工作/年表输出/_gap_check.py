# -*- coding: utf-8 -*-
"""对照各章 pack 的 block 范围与已提取覆盖，输出缺口"""
import json, glob, os, re

BASE = r"D:/DeepSeek Harness专用！危险！！！！！/迷深清洗工作2/年表输出"
PACKS = os.path.join(BASE, "_packs")
TMP = os.path.join(BASE, "_tmp_全")

def pack_blocks(f):
    ids = []
    for line in open(f, encoding="utf-8"):
        m = re.search(r"block_id[:\s]*[^\s]*?(\d+)", line)
        if m:
            ids.append(int(m.group(1)))
    return ids

# 各章 pack 前缀与 block 前缀
CHAPTERS = {
    "第一章_挑战的开始": "md-",
    "第二章_于圣诞祭的最后": "md-",
    "第三章_为了得不到报偿的你": "md-",
    "第四章_我与你存在于此的证明": "md-",
    "第五章_庭师与无名者的物语": "md-",
    "第六章_仅此二人的家庭": "md-",
    "第7-1章_爱的告白": "71md-",
    "第7-2章_生命的价值": "72md-",
    "第7-3章_比起爱与生命": "73md-",
    "第八章_最终章": "md-",
    "第九章_无尽的梦之延续": "md-",
    "第十章_致以久远的天空为目标的人们": "md-",
}

def extracted_blocks():
    """返回 dict: (章标签) -> set(block int)"""
    out = {}
    for fp in glob.glob(os.path.join(TMP, "*.json")):
        try:
            d = json.load(open(fp, encoding="utf-8"))
        except Exception:
            continue
        for e in d:
            sa = e.get("story_anchor", "") or ""
            for m in re.finditer(r"(?:\d+)?(?:md-)(\d+)", sa):
                pass
        # 直接找 md-(\d+) 与 7Xmd-(\d+)
        for e in d:
            sa = e.get("story_anchor", "") or ""
            mm = re.findall(r"md-(\d+)", sa)
            for x in mm:
                b = int(x)
                key = None
                # 判断归属章节：优先看文件前缀
                bn = os.path.basename(fp)
                if bn.startswith("第一章"): key = "第一章_挑战的开始"
                elif bn.startswith("第二章"): key = "第二章_于圣诞祭的最后"
                elif bn.startswith("第三章"): key = "第三章_为了得不到报偿的你"
                elif bn.startswith("第四章"): key = "第四章_我与你存在于此的证明"
                elif bn.startswith("第五章"): key = "第五章_庭师与无名者的物语"
                elif bn.startswith("第六章"): key = "第六章_仅此二人的家庭"
                elif bn.startswith("第7-1"): key = "第7-1章_爱的告白"
                elif bn.startswith("第7-2"): key = "第7-2章_生命的价值"
                elif bn.startswith("第7-3"): key = "第7-3章_比起爱与生命"
                elif bn.startswith("第八章"): key = "第八章_最终章"
                elif bn.startswith("第九章"): key = "第九章_无尽的梦之延续"
                elif bn.startswith("第十章"): key = "第十章_致以久远的天空为目标的人们"
                if key:
                    out.setdefault(key, set()).add(b)
    return out

def main():
    extracted = extracted_blocks()
    for ch, pref in CHAPTERS.items():
        d = os.path.join(PACKS, ch)
        if not os.path.isdir(d):
            continue
        packs = sorted(glob.glob(os.path.join(d, "pack_*.md")),
                       key=lambda x: int(re.search(r"pack_(\d+)", x).group(1)))
        # 计算总 block 范围
        allb = []
        for f in packs:
            allb.extend(pack_blocks(f))
        lo, hi = (min(allb), max(allb)) if allb else (0, 0)
        ext = extracted.get(ch, set())
        # 缺口：在 [lo,hi] 内未被覆盖
        missing = sorted(set(range(lo, hi+1)) - ext)
        # 排除 0
        missing = [x for x in missing if x > 0]
        print(f"{ch}: pack{len(packs)} block {lo}~{hi}, 已提取{len(ext)}块, 缺口{len(missing)}: {missing[:20]}{'...' if len(missing)>20 else ''}")

if __name__ == "__main__":
    main()
