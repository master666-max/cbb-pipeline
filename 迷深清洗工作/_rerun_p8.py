# -*- coding: utf-8 -*-
# Re-run P8 matching: match P8 unmatched names against updated library
import io, json, re, yaml, collections

root = '迷深清洗工作2/年表输出/_tmp_全/'
lib = yaml.safe_load(io.open('迷深清洗工作2/异世界迷宫最深部_知识库/分析/咏唱库/咏唱库_main.yaml', encoding='utf-8'))

def norm(s):
    s = str(s)
    s = s.replace('・','.').replace('·','.').replace('‧','.').replace('•','.').replace('\u3000','')
    s = re.sub(r'[\s_\-—─=～~＊*「」『』《》（）()【】/\\]', '', s)
    return s.lower()

# Build library search keys
lib_keys = []  # (norm_key, entry)  -- entry provides id/jp/en
for e in lib['incantations']:
    eid = e.get('incantation_id','')
    keys = [eid]
    for f in ('magic_name_jp','magic_name_en'):
        if e.get(f): keys.append(e[f])
    for a in (e.get('p8_aliases') or []):
        keys.append(a)
    # also extract names from incantation_text 《...》 and 『...』
    txt = e.get('incantation_text') or ''
    for m in re.findall(r'《([^》]+)》|『([^』]+)』', txt):
        nm = m[0] or m[1]
        if len(nm) > 1 and not re.match(r'^[\w\s.]+$', nm):
            keys.append(nm)
    for k in keys:
        if k: lib_keys.append((norm(k), eid))

# load unmatched
p8 = json.load(io.open(root + '_p8_links.json', encoding='utf-8'))
unmatched = [x for x in p8 if isinstance(x, dict) and x.get('status') == 'unmatched']

def match_name(name):
    nn = norm(name)
    if not nn: return None
    # exact
    for k, eid in lib_keys:
        if k == nn: return eid
    # containment: library key contains name or name contains key (len>=2)
    best = None; bestlen = 0
    for k, eid in lib_keys:
        if len(k) < 2 or len(nn) < 2: continue
        if nn in k or k in nn:
            # prefer longer key overlap
            ov = min(len(nn), len(k))
            if ov > bestlen:
                best = eid; bestlen = ov
    return best

matched = 0; still_unmatched = 0; unmatched_names = collections.Counter()
for x in unmatched:
    eid = match_name(x.get('incantation_name',''))
    if eid:
        x['status'] = 'matched'
        x['incantation_id'] = eid
        x['match_method'] = '补充库匹配'
        x['notes'] = (x.get('notes') or '') + ' | 补录库命中:' + eid
        matched += 1
    else:
        still_unmatched += 1
        unmatched_names[x.get('incantation_name')] += 1

print('matched in re-run:', matched, 'still unmatched:', still_unmatched)
print('remaining unmatched distinct:', len(unmatched_names))
print()
print('=== REMAINING UNMATCHED (top 60) ===')
for name, c in unmatched_names.most_common(60):
    print(f'{c:3d}  {name}')

# save updated links
io.open(root + '_p8_links.json', 'w', encoding='utf-8').write(json.dumps(p8, ensure_ascii=False, indent=1))
io.open(root + '_p8_unmatched_remaining.json', 'w', encoding='utf-8').write(json.dumps(dict(unmatched_names), ensure_ascii=False, indent=1))
print('saved _p8_links.json updated')