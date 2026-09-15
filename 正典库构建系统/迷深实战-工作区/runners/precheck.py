# -*- coding: utf-8 -*-
"""precheck.py — 抽取源件引文预检（对全部块；防止笔误进入管线循环）。
用法: py -X utf8 precheck.py <extraction.json> <slice.txt>
"""
import json, sys
sys.path.insert(0, r'cbb/cbb-coordinate')
sys.path.insert(0, r'cbb/contracts')
from pathlib import Path
import cbb_coordinate as cc

ext_path, slice_path = sys.argv[1], sys.argv[2]
blocks = cc.coordinate(Path(slice_path).read_text(encoding='utf-8'), vol=1)['blocks']
full = '\n'.join(b['text'] for b in blocks)
ext = json.load(open(ext_path, encoding='utf-8'))
bad = 0
for c in ext['candidates']:
    for ev in c.get('evidence', []):
        if ev['quote'] not in full:
            bad += 1
            print('DANGLING:', c['canonical'].get('name') or c['canonical'].get('subject'), '| line', ev['line'], '|', repr(ev['quote'][:36]))
print('dangling:', bad, '/ candidates', len(ext['candidates']))
