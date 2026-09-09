
# -*- coding: utf-8 -*-
import io, json
entries_file = '迷深清洗工作2/咏唱补录_entries.json'
entries = json.load(io.open(entries_file, encoding='utf-8'))

def add(**kw):
    entries.append(kw)

# 最后一批：冰结寒冰 / GrandFall / 星属性告白 / 血海歌魔法 / 幻转大天体 / 逆映湖月梦之咒 / 代价咏唱
add(id='ice_cold', caster='相川涡波', type='普通魔法咏唱（冰结·寒冰）',
    chant='「我试试，上吧！冰结魔法《寒冰》！」',
    jp='寒冰（Ice Cold）', en='Ice Cold',
    effect='冰结魔法《寒冰》（效果与《冻结》相近，初期评价不高）',
    source='第一章 第一章-异世界迷宫 (md-0008)', edition='web_reconstructed',
    aliases=['ice-cold'])

add(id='grand_fall', caster='缇缇／莱纳（共鸣）', type='共鸣魔法（风·终坠）',
    chant='「共鸣魔法『Tows Schuss Wind·Grand Fall』！！」',
    jp='Tows Schuss Wind·Grand Fall', en='Tows Schuss Wind・Grand Fall',
    effect='风系共鸣魔法（Tows Schuss Wind的Grand Fall形态）',
    source='第五章 第227话 《迷宫最后的战斗》 (md-0311)', edition='web_original',
    aliases=['共鸣魔法_GrandFall'])

add(id='魔法_星属性咏唱_告白', caster='相川涡波（星属性咏唱）', type='咏唱（星属性·告白）',
    chant='（原文为告白句：「『我爱你』。我比这个世界上的任何人都更『爱拉斯缇亚拉』。」——星魔法相关咏唱段）',
    jp='星属性咏唱（告白）', en='—',
    effect='星属性咏唱（告白）：「我爱你，比世上任何人都更爱拉斯缇亚拉」',
    source='第九章 第451话 爱的告白 (md-0275~0278)', edition='web_original',
    aliases=['魔法_星属性咏唱_告白'])

add(id='血海歌魔法', caster='（血海歌魔法·呼名死者之声）', type='咏唱（血·组咒）',
    chant='（含组咒，原文未收录完整咏唱句；相关句「『——我杀死了母亲。我吃掉了父亲——』」）',
    jp='血海歌魔法（未知名，含组咒）', en='—',
    effect='血海歌魔法：呼名死者之声的组咒咏唱',
    source='第十章 第470话 开战 (md-0072~0073)', edition='web_original',
    aliases=['血海歌魔法','血海歌魔法(未知名,含组咒)'])

add(id='celestial_garden', caster='诺斯菲·弗茨亚茨（星魔法）', type='普通魔法咏唱（星魔法·大天体）',
    chant='「——星魔法『幻转大天体（Celestial·Garden）』！！」',
    jp='幻转大天体', en='Celestial・Garden',
    effect='星魔法幻转大天体（Celestial Garden），第六十之试炼反狱中的真髓星魔法',
    source='第7-3章 第345话 第六十之试炼『反狱』 (7373md-0162)', edition='web_original',
    aliases=['celestial_garden_幻转大天体'])

add(id='inverted_lagunequalia', caster='阳滝', type='普通魔法咏唱（梦·逆映）',
    chant='「——魔·法『逆映湖月梦之咒（Inverted·LaguneQualia）』！！」',
    jp='逆映湖月梦之咒', en='Inverted・LaguneQualia',
    effect='逆映湖月梦之咒（Inverted・LaguneQualia），与『代而亡逝之光』相互制衡的梦中咒',
    source='第7-3章 第345话 第六十之试炼『反狱』 (7373md-0166)', edition='web_original',
    aliases=['inverted_lagunequalia_逆映湖月梦之咒'])

add(id='代价咏唱火炎', caster='阿尔缇（火之理的盗窃者）', type='代价咏唱（记忆/感情/生命为代价）',
    chant='「将过去当做薪柴，令现在燃烧得更加旺盛。这正是火炎魔法的神髓。」「只要把没用的感情当做燃料就行了。把这不中用的身躯当做燃料就好了。」',
    jp='代价咏唱（记忆/感情/生命为代价）', en='—',
    effect='以记忆/感情/生命为代价的火炎咏唱（将过去当薪柴）',
    source='第三章 第三章『我』的圣诞祭的结束 (md-0173~0177)', edition='web_reconstructed+web_original',
    aliases=['代价咏唱(记忆/感情/生命为代价)'])

# ── 别名补丁 ──
def patch(entry_id, extra_aliases):
    for e in entries:
        if e['id'] == entry_id:
            al = set(e.get('aliases') or [])
            al.update(extra_aliases)
            e['aliases'] = sorted(al)
            return True
    return False

patch('wintry_dimension', ['魔法『冬之世界加速奔驰』'])
patch('level_up', ['咒术咏唱『汝者刮目自省而可也/识生命其辉华』'])
patch('完全治愈', ['治愈魔法之光'])
patch('■道落土', ['罗德_道落土'])
patch('di_gradient_battle', ['次元决战演算'])
patch('line', ['星魔法'])

io.open(entries_file, 'w', encoding='utf-8').write(json.dumps(entries, ensure_ascii=False, indent=1))
print('entries total:', len(entries))
# count aliases coverage again
import re
adds = json.load(io.open('迷深清洗工作2/年表输出/_tmp_全/_class_add.json', encoding='utf-8'))
def norm(s):
    return re.sub(r'[\s·・‧•　_\-—─=～~＊*（）()「」『』《》/\\]', '', str(s)).lower()
alias_set = set()
for e in entries:
    for a in (e.get('aliases') or []):
        alias_set.add(norm(a))
    alias_set.add(norm(e.get('jp','')))
    alias_set.add(norm(e.get('en','')))
    alias_set.add(norm(e.get('id','')))
uncovered = [ (n,c) for n,c in adds.items() if not (norm(n) in alias_set or any(al and (norm(n) in al or al in norm(n)) for al in alias_set)) ]
print('UNCOVERED now:', len(uncovered))
for n,c in uncovered: print('  ', c, n)
