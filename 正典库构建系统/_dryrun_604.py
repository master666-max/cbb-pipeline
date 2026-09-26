# -*- coding: utf-8 -*-
"""_dryrun_604.py — 604 件矛盾积压 dry-run 分布报告（零写入，只读+出报告）"""
import json, sys, re, collections
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / 'cbb' / 'tools'))
import importlib
m = importlib.import_module('矛盾分流')

root = Path(__file__).resolve().parent / '迷深实战-本体库'
items = [json.loads(l) for l in (root / 'quarantine-zone' / 'items.jsonl').read_text(encoding='utf-8').splitlines() if l.strip()]
cons = [i for i in items if i.get('subclass') == 'contradiction_pending']
statuses = collections.Counter(i.get('status') for i in items)
print('总件数', len(items), '| 矛盾件', len(cons), '| 状态分布', dict(statuses))

# 官方解析器口径
fields = collections.Counter(); parsed = 0
samples = collections.defaultdict(list)
for i in cons:
    p = m.parse_dual_track_detail(i.get('detail', '') or '')
    if p:
        parsed += 1
        fields[p[0]] += 1
        if len(samples[p[0]]) < 2:
            samples[p[0]].append((i.get('detail', '')[:110]))

# 兜底正则口径（防官方解析器吃不下历史格式）
fb = collections.Counter()
for i in cons:
    d = i.get('detail', '') or ''
    if '入库=' in d:
        mt = re.match(r'\s*([^:：]+)[:：]', d)
        fb[mt.group(1).strip() if mt else 'UNKNOWN'] += 1

print('官方解析器可解析:', parsed, '/', len(cons))
for f, c in fields.most_common():
    print(f'  {f}: {c}  样例: {samples[f][0] if samples.get(f) else ""}')
print('兜底正则口径字段分布:', dict(fb.most_common()))

try:
    rep = m.propose(root)
    print('矛盾分流.propose by_cls:', json.dumps(rep.get('by_cls', {}), ensure_ascii=False))
    print('机械档 proposals:', len(rep.get('proposals', [])))
except Exception as e:
    print('propose 真库跑失败(不影响原始统计):', type(e).__name__, str(e)[:200])

out = {'total': len(items), 'contradiction': len(cons), 'status': dict(statuses),
       'parsed_by_official': parsed, 'fields_official': dict(fields),
       'fields_fallback': dict(fb), 'samples': {k: v for k, v in samples.items()}}
dest = Path(__file__).resolve().parent / '迷深实战-工作区' / 'logs' / '积压重分流-dryrun分布-20260926.json'
dest.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
print('报告已落盘', dest.name)
