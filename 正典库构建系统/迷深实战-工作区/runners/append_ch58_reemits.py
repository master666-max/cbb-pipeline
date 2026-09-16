# -*- coding: utf-8 -*-
"""append_ch58_reemits.py — ch0058 补发 4 个重发实体（一次性脚本）"""
import json
from pathlib import Path

p = Path('迷深实战-工作区/candidates/extraction-ch0058.json')
d = json.loads(p.read_text(encoding='utf-8'))
if any(c['canonical'].get('name') == '『ImpulseBreak』' for c in d['candidates'] if isinstance(c.get('canonical'), dict)):
    print('已补发过，跳过'); raise SystemExit

adds = [
 {"type": "entity", "library": "setting", "confidence": 0.9,
  "canonical": {"name": "『ImpulseBreak』", "entity_type": "技能魔法"}, "aliases_to_register": [],
  "observations": [{"category": "status_change", "chapter": 58, "text": "斯诺连人带惯性劈下的一击：正面吃下后黑暗被冲击振动整个掀飞、莉帕现形失去实体——与『Impulse』系谱关系待 R4（STATE 待确认②）"}],
  "evidence": [{"vol": 1, "chapter": 58, "line": 942, "quote": "「——『ImpulseBreak』！！」"},
                {"vol": 1, "chapter": 58, "line": 945, "quote": "正面吃下了斯诺连人带惯性劈下的一剑，黑暗因为冲击和振动被整个掀飞了，于是莉帕褪下黑暗的外衣现出了身影。"}]},
 {"type": "entity", "library": "setting", "confidence": 0.9,
  "canonical": {"name": "『新月琉璃制直剑』", "entity_type": "物品(武具)"}, "aliases_to_register": [],
  "observations": [{"category": "status_change", "chapter": 58, "text": "番外战主用剑：对莉帕镰刀迎击+感应回避连击+终局斩脚钉地（对缇达要领冰结固定）"}],
  "evidence": [{"vol": 1, "chapter": 58, "line": 586, "quote": "与之相应的，我也从『持有物品』中取出了『新月琉璃制直剑』，和莉帕一样摆好架势。"},
                {"vol": 1, "chapter": 58, "line": 979, "quote": "接着，我闭着眼睛用剑刺穿倒地的莉帕的左脚——把她钉在地上。"}]},
 {"type": "entity", "library": "setting", "confidence": 0.88,
  "canonical": {"name": "『Connection』", "entity_type": "技能魔法"}, "aliases_to_register": [],
  "observations": [{"category": "status_change", "chapter": 58, "text": "史诗探索者节点已被解除；涡波另留最信赖后手（内容未揭示）"}],
  "evidence": [{"vol": 1, "chapter": 58, "line": 627, "quote": "「尽快吧，涡波。不赶紧去『史诗探索者』那边的话，你妹妹会有危险的哦？不能用涡波的『Connection』直接去『史诗探索者』吗？」"}]},
 {"type": "entity", "library": "setting", "confidence": 0.88,
  "canonical": {"name": "舞斗大会", "entity_type": "概念"}, "aliases_to_register": [],
  "observations": [{"category": "status_change", "chapter": 58, "text": "决赛=涡波对诺文（其一直在瓦尔法拉顶点等待）；番外战无观众开幕收局"}],
  "evidence": [{"vol": 1, "chapter": 58, "line": 6, "quote": "『舞斗大会』的准决赛结束了。"}]},
]
d['candidates'].extend(adds)
p.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding='utf-8')
print('补发', len(adds), '总候选', len(d['candidates']))
