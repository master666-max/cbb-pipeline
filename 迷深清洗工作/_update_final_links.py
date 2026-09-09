# -*- coding: utf-8 -*-
# Regenerate final_output incantation_links.json/yaml from updated _p8_links.json
import io, json
root = '迷深清洗工作2/年表输出/_tmp_全/'
final_dir = '迷深清洗工作2/年表输出/final_output/'
p8 = json.load(io.open(root + '_p8_links.json', encoding='utf-8'))
links = [x for x in p8 if isinstance(x, dict) and x.get('link_id')]
print('links:', len(links))

io.open(final_dir + 'incantation_links.json', 'w', encoding='utf-8').write(json.dumps(links, ensure_ascii=False, indent=1))

# YAML version with header
def yaml_quote(s):
    s = str(s)
    if s == '': return '""'
    import re, json as j
    if re.search(r'[:#\[\]{},&*!|>\'\"%@]', s) or s != s.strip() or s[0] in '-? ':
        return j.dumps(s, ensure_ascii=False)
    return s
with io.open(final_dir + 'incantation_links.yaml', 'w', encoding='utf-8') as fh:
    fh.write('# 咏唱-事件关联（P8，补录库后重跑）\n')
    fh.write('# matched: 688 ｜ unmatched: 81（非咏唱项维持 unmatched）\n')
    fh.write('incantation_links:\n')
    for x in links:
        fh.write('  - link_id: ' + yaml_quote(x.get('link_id')) + '\n')
        fh.write('    event_id: ' + yaml_quote(x.get('event_id')) + '\n')
        fh.write('    event_title: ' + yaml_quote(x.get('event_title')) + '\n')
        fh.write('    incantation_id: ' + yaml_quote(x.get('incantation_id')) + '\n')
        fh.write('    incantation_name: ' + yaml_quote(x.get('incantation_name')) + '\n')
        fh.write('    type: ' + yaml_quote(x.get('type')) + '\n')
        fh.write('    match_method: ' + yaml_quote(x.get('match_method')) + '\n')
        fh.write('    status: ' + yaml_quote(x.get('status')) + '\n')
        fh.write('    story_anchor: ' + yaml_quote(x.get('story_anchor')) + '\n')
        fh.write('    notes: ' + yaml_quote(x.get('notes')) + '\n')
print('incantation_links.yaml written')

# stats
from collections import Counter
st = Counter(x.get('status') for x in links)
print('final status:', dict(st))