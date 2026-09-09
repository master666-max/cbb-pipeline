# -*- coding: utf-8 -*-
import json, sys, os, re
sys.stdout.reconfigure(encoding='utf-8')
CL = r"D:/DeepSeek Harness专用！危险！！！！！/迷深清洗工作2/异世界迷宫最深部_知识库/分析/清洗标注版"
OUT = r"D:/DeepSeek Harness专用！危险！！！！！/迷深清洗工作2/异世界迷宫最深部_知识库/分析/_角色语料库/_25角色原文证据"
CHAR_ALIAS = json.load(open(r"D:/DeepSeek Harness专用！危险！！！！！/迷深清洗工作2/异世界迷宫最深部_知识库/分析/_角色语料库/_alias25.json", encoding="utf-8"))

def ok_pos(text, i, name, char):
    before = text[i-1] if i>0 else ''
    after = text[i+len(name)] if i+len(name)<len(text) else ''
    if char=='缇娅拉' and before in '丝斯拉斯': return False
    if char=='艾尔米拉德' and name=='艾尔' and after in '米娜': return False
    return True

def find_in(text, start, end, char, alias):
    i=start
    while i<end:
        idx=text.find(alias,i,end)
        if idx==-1: break
        if ok_pos(text,idx,alias,char): return idx
        i=idx+1
    return -1

SPEAK_V=['说','道','问','答','喊','叫','吼','应','回应','开口','附和','嘟囔','抱怨','怒吼','嚷嚷','低语','呢喃','耳语','招呼','搭话','喝道','质问','反问','答道','说道','问道','回答','提醒','补充','感叹','叹道','笑道','冷冷道','沉声道','轻声道','大声道','自言自语','呢喃道','低声道','嗤笑','喝道：','说：','道：']

files = sorted([f for f in os.listdir(CL) if f.endswith('_清洗标注版.md')])
episodes=[]
for fn in files:
    ch=fn.replace('_清洗标注版.md','')
    lines=open(os.path.join(CL,fn),encoding='utf-8').read().split('\n')
    cur_ep=ch; cur=[]
    for l in lines:
        m=re.match(r'## block_id: (\S+)  episode: (.*?)  edition:',l)
        if m:
            if cur: episodes.append({'ep':cur_ep,'lines':cur})
            cur_ep=m.group(2).strip() if m.group(2) and m.group(2)!='None' else ch
            cur=[l]
        else: cur.append(l)
    if cur: episodes.append({'ep':cur_ep,'lines':cur})

result={}
for char,aliases in CHAR_ALIAS.items():
    quotes=[]
    for ep in episodes:
        lines=ep['lines']; epn=ep['ep']
        for li,l in enumerate(lines):
            t=l.strip()
            m=re.match(r'^\[([^\]]+)\]\s*(.+)$',t)
            if not m or m.group(1) not in ('对白','内心独白','咏唱','闪回/记忆'): continue
            tag=m.group(1); body=m.group(2)
            # nearest-pair attribution: scan outward from line for char alias near speak verb
            # search window: accumulate up to ~150 chars each side, then check
            def get_window():
                before=''; j=li-1
                while j>=0 and len(before)<150:
                    before=lines[j]+'\n'+before; j-=1
                after=''; j=li+1
                while j<len(lines) and len(after)<150:
                    after=after+'\n'+lines[j]; j+=1
                return before[-150:]+t+after[:150]
            win=get_window()
            # nearest alias to line center; but must pair with speak verb within 120
            attributed=None
            for alias in aliases:
                # find all alias positions in win
                start=0
                while True:
                    p=win.find(alias,start)
                    if p==-1: break
                    if ok_pos(win,p,alias,char):
                        # find nearest speak verb
                        best=None
                        for v in SPEAK_V:
                            vi=win.find(v)
                            if vi!=-1 and abs(vi-p)<=120:
                                if best is None or abs(vi-p)<abs(best):
                                    best=vi
                        if best is not None:
                            if attributed is None or abs(best-p)<attributed[1]:
                                attributed=(alias,abs(best-p))
                        break
                    start=p+1
                if attributed and len(attributed)==2 and attributed[1]<=120: pass
            if attributed and attributed[1]<=120:
                quotes.append({'ep':epn,'type':tag,'text':body[:400]})
    # dedupe
    seen=set(); qq=[]
    for q in quotes:
        k=(q['ep'],q['type'],q['text'][:40])
        if k in seen: continue
        seen.add(k); qq.append(q)
    result[char]=qq
    print(char,"台词",len(qq))

with open(os.path.join(OUT,'_all25_quotes_v2.json'),'w',encoding='utf-8') as f:
    json.dump(result,f,ensure_ascii=False,indent=1)
print("DONE")
