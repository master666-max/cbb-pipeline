# -*- coding: utf-8 -*-
"""P2 清洗标注版：对话/独白/通讯/时间线打标（机械规则，保留原文）"""
import re, os, json
SRC="D:/DeepSeek Harness专用！危险！！！！！/迷深清洗工作2/异世界迷宫最深部_知识库/分析/场景块语料"
DST="D:/DeepSeek Harness专用！危险！！！！！/迷深清洗工作2/异世界迷宫最深部_知识库/分析/清洗标注版"

TRUE_INC = re.compile(r"[—-]{2,}\s*『.+?』.*魔法")
COM_LINE = re.compile(r"^\s*[［\[][^\]［]{1,60}[\]］]\s*$")
FLASH = re.compile(r"(回忆|闪回|当初|那时|记忆|往事)")
INC_TEXT = re.compile(r"(魔法[《『]|作为『代替』|辞世|咏唱)")
TL_PRE = re.compile(r"(千年前|境界战争|始祖|古代)")
TL_MIX = re.compile(r"千年前.*(?:涡波|其)|(?:涡波|其).*千年前")

def tag_block(blk):
    lines = blk["text"].split("\n")
    out = []
    for ln in lines:
        s = ln.strip()
        if not s: out.append(""); continue
        if "「" in s and "」" in s:
            out.append("[对白] "+s); continue
        if COM_LINE.match(s):
            out.append("[通讯/内心自白] "+s); continue
        if FLASH.search(s):
            out.append("[闪回/记忆] "+s); continue
        if TRUE_INC.search(s) or INC_TEXT.search(s):
            out.append("[咏唱] "+s); continue
        if (s.startswith("──") or s.startswith("——")) and ("我" in s or "自己" in s):
            out.append("[内心独白] "+s); continue
        out.append(s)
    text = "\n".join(out)
    tl = "千年前后交错" if TL_MIX.search(blk["text"]) else ("千年前" if TL_PRE.search(blk["text"]) else "千年后")
    header = "block_id: "+blk["block_id"]+"  episode: "+str(blk["episode"])+"  edition: "+blk["edition"]+"  timeline: "+tl
    return "## "+header+"\n"+text

def main():
    os.makedirs(DST, exist_ok=True)
    total=0
    for fn in os.listdir(SRC):
        if not fn.endswith(".json"): continue
        data=json.load(open(os.path.join(SRC,fn),encoding="utf-8"))
        parts=[]
        for blk in data["blocks"]:
            parts.append(tag_block(blk)); total+=1
        cname=fn.replace("_场景块.json","")
        with open(os.path.join(DST,f"{cname}_清洗标注版.md"),"w",encoding="utf-8") as f:
            f.write("\n\n---\n\n".join(parts))
        print(cname,"done")
    print("TOTAL tagged blocks:",total)
if __name__=='__main__': main()