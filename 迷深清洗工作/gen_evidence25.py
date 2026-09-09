# -*- coding: utf-8 -*-
import json, sys, os, re
sys.stdout.reconfigure(encoding='utf-8')
CL = r"D:/DeepSeek Harness专用！危险！！！！！/迷深清洗工作2/异世界迷宫最深部_知识库/分析/清洗标注版"
OUT = r"D:/DeepSeek Harness专用！危险！！！！！/迷深清洗工作2/异世界迷宫最深部_知识库/分析/_角色语料库/_25角色原文证据"

# alias maps: canonical -> [aliases (longest-first)]
# include special 'full' names with guards for substring conflicts
CHAR_ALIAS = json.load(open(r"D:/DeepSeek Harness专用！危险！！！！！/迷深清洗工作2/异世界迷宫最深部_知识库/分析/_角色语料库/_alias25.json", encoding="utf-8"))

# build a flat list of (alias, char) sorted by alias length desc; guard char sets
# Guard: avoid 缇娅拉 matching inside 拉丝缇娅拉 (preceded by 丝/拉); 缇达 not inside 缇娅拉/缇亚拉
def ok_pos(text, i, name, char):
    before = text[i-1] if i>0 else ''
    after = text[i+len(name)] if i+len(name)<len(text) else ''
    if char=='缇娅拉':
        if before in '丝斯拉斯': return False
        # 缇亚拉 also valid for 圣人, but ensure not part of 拉丝缇亚拉
        return True
    if char=='艾尔米拉德' and name=='艾尔':
        # standalone 艾尔 only when not followed by 米拉德/娜
        if after in '米娜': return False
        return True
    if char=='法芙纳' and name=='法夫纳':
        return True
    if char=='格连' and name=='沃克':
        # 沃克 as surname only when part of 格连・沃克 or followed by context; keep but guard
        return True
    return True

def find_char_in(text, start, end, char, alias):
    """find alias occurrence within [start,end) honoring ok_pos; return (pos, name) or None"""
    i = start
    while i < end:
        idx = text.find(alias, i, end)
        if idx == -1: break
        if ok_pos(text, idx, alias, char):
            return idx, alias
        i = idx + 1
    return None

# load 12 chapters, each split into episode blocks with 话号
files = sorted([f for f in os.listdir(CL) if f.endswith('_清洗标注版.md')])
print("chapters:", len(files))
episodes = []  # each: {ep, blocks:[{type, text}]}
for fn in files:
    ch_name = fn.replace('_清洗标注版.md','')
    txt = open(os.path.join(CL,fn),encoding='utf-8').read()
    lines = txt.split('\n')
    cur_ep = ch_name
    cur = []
    for l in lines:
        m = re.match(r'## block_id: (\S+)  episode: (.*?)  edition:', l)
        if m:
            if cur: episodes.append({'ep':cur_ep,'lines':cur})
            cur_ep = m.group(2).strip() if m.group(2) and m.group(2)!='None' else ch_name
            cur = [l]
        else:
            cur.append(l)
    if cur: episodes.append({'ep':cur_ep,'lines':cur})
print("episodes total:", len(episodes))

SPEAK_V = ['说','道','问','答','喊','叫','吼','应','回应','开口','附和','嘟囔','抱怨','怒吼','嚷嚷','低语','呢喃','耳语','招呼','搭话','喝道','质问','反问','答道','说道','问道','回答','提醒','补充','感叹','叹道','笑道','冷冷道','沉声道','轻声道','大声道','自言自语','呢喃道','低声道','嗤笑','笑道：','说：','道：']

# per char extraction
result = {}
for char, aliases in CHAR_ALIAS.items():
    quotes=[]   # {ep, line, lineIdx, type, tag}
    facts=[]
    for epi, ep in enumerate(episodes):
        ep_name = ep['ep']
        lines = ep['lines']
        for li, l in enumerate(lines):
            t = l.strip()
            if not t: continue
            # speech line types
            m = re.match(r'^\[([^\]]+)\]\s*(.+)$', t)
            is_speech = m is not None and m.group(1) in ('对白','内心独白','咏唱','闪回/记忆')
            if is_speech:
                tag = m.group(1); body = m.group(2)
                # attribution window: 120 chars before/after within this episode's joined text
                # build window = prev lines + this + next lines
                ctx_before = ''
                j = li-1
                while j>=0 and len(ctx_before) < 130:
                    ctx_before = lines[j] + '\n' + ctx_before
                    j -= 1
                ctx_after = ''
                j = li+1
                while j<len(lines) and len(ctx_after) < 130:
                    ctx_after = ctx_after + '\n' + lines[j]
                    j += 1
                window = ctx_before[-130:] + t + ctx_after[:130]
                # find nearest alias before/after with speak verb
                attributed = False
                # search in full window (both sides) for char alias near speak verb
                for alias in aliases:
                    pos = window.find(alias)
                    if pos==-1: continue
                    # within 120 chars of a speak verb
                    for verb in SPEAK_V:
                        vp = window.find(verb)
                        if vp==-1: continue
                        if abs(vp-pos) <= 120:
                            attributed=True; break
                    if attributed: break
                if attributed:
                    quotes.append({'ep':ep_name,'type':tag,'text':body[:400],'line':li,'epi':epi})
            elif char in t or any(a in t for a in aliases):
                # narrative fact line containing char name
                # filter out headers/block lines
                if t.startswith('#') or t.startswith('>') or t.startswith('---') or t.startswith('## block'):
                    continue
                if len(t) > 10:
                    facts.append({'ep':ep_name,'text':t[:300]})
    # dedupe quotes
    seen_q=set(); qq=[]
    for q in quotes:
        k=(q['ep'],q['type'],q['text'][:50])
        if k in seen_q: continue
        seen_q.add(k); qq.append(q)
    result[char]={'quotes':qq,'facts':facts[:600],'total_fact_lines':len(facts)}
    print(char, "台词", len(qq), "事实", len(facts))

with open(os.path.join(OUT,'_all25_evidence.json'),'w',encoding='utf-8') as f:
    json.dump(result,f,ensure_ascii=False,indent=1)
print("DONE")
