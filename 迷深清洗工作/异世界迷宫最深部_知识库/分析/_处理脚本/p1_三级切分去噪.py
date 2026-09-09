# -*- coding: utf-8 -*-
"""P1c 三级切分+去噪+场景块, ep/translator/cast 正确归属"""
import re, os, json
SRC = "D:/DeepSeek Harness专用！危险！！！！！/迷深清洗工作2/异世界迷宫最深部_知识库/文字/04_web版"
OUT = "D:/DeepSeek Harness专用！危险！！！！！/迷深清洗工作2/异世界迷宫最深部_知识库/分析/场景块语料"
EDITION = {"第一章_挑战的开始.md":"web_reconstructed","第二章_于圣诞祭的最后.md":"web_reconstructed","第三章_为了得不到报偿的你.md":"web_reconstructed+web_original"}
for n in ["第四章_我与你存在于此的证明.md","第五章_庭师与无名者的物语.md","第六章_仅此二人的家庭.md","第7-1章_爱的告白.md","第7-2章_生命的价值.md","第7-3章_比起爱与生命.md","第八章_最终章.md","第九章_无尽的梦之延续.md","第十章_致以久远的天空为目标的人们.md"]: EDITION[n]="web_original"
INCANT = re.compile(r"[—-]{2,}\s*『.+?』|[《『][^》』]{1,24}魔法|作为『代替』|燃烧.{0,8}记忆|支付.{0,8}代价|以.{1,10}为代价|辞世|这·里·")
STATUS_START = re.compile(r"^【(Status|状态|技能|持有物品|Item)】")
LATIN_LINE = re.compile(r"^[A-Z][A-Za-z0-9.·・ ]{1,44}$")
CAST_NAMES = ("涡波","缇娅拉","拉丝缇娅拉","玛利亚","斯诺","诺斯菲","阳诺斯菲","阳滝","缇缇","艾德","海因","莱纳","帕林库洛","古奈尔","赛尔德拉","法夫纳","诺伊","莉帕","格连","芙兰琉莱","基督","缇娅","拉古涅")

def split_file(full, chapter_key):
    lines = open(full,encoding="utf-8").read().split("\n")
    edition = EDITION.get(os.path.basename(full),"web_original")
    meta={"h1":lines[0].strip() if lines and lines[0].startswith("# ") else os.path.basename(full),"edition":edition}
    blocks=[]; cur_episode=None; translator=None; cast=set(); paragraphs=[]; cur_para=[]
    def para_flush():
        if cur_para: paragraphs.append("\n".join(cur_para)); cur_para.clear()
    def emit_episode_blocks():
        chunks=[]; cur=[]; clen=0
        for p in paragraphs:
            if not p.strip(): continue
            plen=len(p)
            if cur and clen+plen>1500:
                chunks.append("\n\n".join(cur)); cur=[p]; clen=plen
            else:
                cur.append(p); clen+=plen
        if cur: chunks.append("\n\n".join(cur))
        slug=re.sub(r"[^A-Za-z0-9]","",chapter_key)[-22:]
        for ck in chunks:
            if len(ck.strip())<2: continue
            blocks.append({"chapter":meta["h1"],"episode":cur_episode,"edition":edition,"block_id":f"{slug}-{len(blocks)+1:04d}","translator":translator,"cast":sorted(cast),"text":ck,"char_len":len(ck)})
        paragraphs.clear(); cast.clear()
    i=0; panel_accum=[]; panel_open=False
    while i < len(lines):
        line=lines[i]; st=line.strip()
        if "![" in line and "](" in line: para_flush(); i+=1; continue
        if st.startswith("翻译君"):
            translator=st.replace("翻译君","").lstrip(":：").strip(); para_flush(); i+=1; continue
        if line.startswith("## ") or line.startswith("### "):
            para_flush(); emit_episode_blocks(); cur_episode=st.lstrip("# ").strip(); i+=1; continue
        if st.startswith("◆"):
            para_flush(); emit_episode_blocks(); i+=1; continue
        if STATUS_START.match(st) or (panel_open and (LATIN_LINE.match(st) or st.startswith(("Name","Str","等级","力量","状态","经验","装备","技能","持有")))):
            panel_accum.append(st); panel_open=True; i+=1; continue
        else:
            if panel_open:
                join="\n".join(panel_accum)
                para_flush()
                paragraphs.append(join if INCANT.search(join) else "【面板略】（重复系统面板已占位）")
                panel_accum=[]; panel_open=False
            if st=="":
                para_flush()
            else:
                for c in CAST_NAMES:
                    if c in line: cast.add(c)
                cur_para.append(line)
            i+=1
    para_flush(); emit_episode_blocks()
    return blocks, meta

def main():
    os.makedirs(OUT, exist_ok=True)
    chapters=[(os.path.join(r,f),os.path.relpath(os.path.join(r,f),SRC).replace("\\","/")) for r,d,fs in os.walk(SRC) for f in fs if f.endswith(".md")]
    total=0
    for full,key in chapters:
        blocks,meta=split_file(full,key)
        cname=os.path.basename(full).replace(".md","")
        with open(os.path.join(OUT,f"{cname}_场景块.json"),"w",encoding="utf-8") as f:
            json.dump({"meta":meta,"blocks":blocks},f,ensure_ascii=False,indent=1)
        eps=len(set(b["episode"] for b in blocks))
        print(cname,"| blocks",len(blocks),"| eps",eps)
        total+=len(blocks)
    print("TOTAL",total)
if __name__=='__main__': main()