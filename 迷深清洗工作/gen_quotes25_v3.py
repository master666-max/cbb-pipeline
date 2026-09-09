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

def find_aliases_in(text, char, aliases):
    """all alias positions honoring guards"""
    out=[]
    for a in aliases:
        i=0
        while True:
            p=text.find(a,i)
            if p==-1: break
            if ok_pos(text,p,a,char): out.append((p,a))
            i=p+1
    return out

# speak verb patterns: name + 说/道/问/答/喊/叫/吼/应... within 20 chars (usually adjacent: XX说)
VERBS=['说道','说：','道：','问道','答道','说道：','笑道','叹道','喝道','低声道','沉声道','轻声道','大声道','冷冷道','呢喃道','自言自语','开口道','应道','答曰','回答','说','道','问','答','喊','叫','吼','应','开口','附和','嘟囔','抱怨','怒吼','嚷嚷','招呼','搭话','低语','呢喃','耳语','提醒','补充','感叹','反问','质问','回应']

def speak_distance(text, pos, char):
    """find nearest verb start; return distance or None if >25"""
    best=None
    for v in VERBS:
        # search verb within [pos, pos+30] after name (name SAYS pattern)
        vi=text.find(v, pos+1, pos+30)
        if vi!=-1:
            d=vi-pos
            if best is None or d<best: best=d
    return best

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
            # context: 2 lines before + this + 2 lines after (for attribution)
            ctx=[]
            for j in range(max(0,li-2), li): ctx.append(lines[j])
            ctx.append(t)
            for j in range(li+1, min(len(lines),li+3)): ctx.append(lines[j])
            joined='\n'.join(ctx)
            # find char alias in joined; check speak verb right after it (name SAYS)
            found=False
            for p,a in find_aliases_in(joined, char, aliases):
                d=speak_distance(joined, p, char)
                if d is not None:
                    found=True; break
            if found:
                quotes.append({'ep':epn,'type':tag,'text':body[:400]})
    # dedupe
    seen=set(); qq=[]
    for q in quotes:
        k=(q['ep'],q['type'],q['text'][:40])
        if k in seen: continue
        seen.add(k); qq.append(q)
    result[char]=qq
    print(char,"台词",len(qq))

with open(os.path.join(OUT,'_all25_quotes_v3.json'),'w',encoding='utf-8') as f:
    json.dump(result,f,ensure_ascii=False,indent=1)
print("DONE")
