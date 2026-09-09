
# -*- coding: utf-8 -*-
import io, json, collections

root = '迷深清洗工作2/年表输出/_tmp_全/'
unmatched = json.load(io.open(root + '_p8_unmatched_dump.json', encoding='utf-8'))
names = collections.Counter(x['name'] for x in unmatched)

SKIP = set('''
缇亚拉 雷梵 基里斯督莱纳 帕林库洛 赫尔米娜涅夏 赫尔米娜涅西亚 赫尔米娜的心脏 诺文 海因·赫勒比勒夏因 紫苑
旧人类史 旧人类史的英雄谭 旧历百年百怪妖异谈 旧历之终结… 新历0年光神… 新历3年始祖… 新历1013英雄… 碑白教圣经第五章
阿雷亚斯流的剑术 阿雷亚斯家的宝剑诺文 阿雷伊斯家的宝剑诺文 阿雷亚斯家的宝剑诺文(剑技) 莱纳_赫勒比勒夏因二重奏剑 赫勒比勒夏因・三重奏剑 helberan_duetist
冰结剑 冰结剑冰刃 次元斩裂剑 魔法『次元斩裂剑』 罗德_重崩色之非风剑 将地平线一同斩裂 纤指一划，云散海裂 冲天巨木亦可斩断 阿雷亚斯剑出，万魔皆灭 剑与剑相连之际，真正的英雄现身
技能_？？？ 技能_？？？被封印 技能_？？？退环 最深部之誓约者 skill_最深部之誓约者 过去视 感应 注视鉴定 魔人返还 魔石化 过载 咒印 亚流体术 降灵 读书 反转 In Fight
星之理 次元之理 星之魔力
使徒的试练 第二十之试练 百十之试炼 第六十之试练(光)
通信机 魔石线 黑线/魔石线 阳滝丝线 Line魔石线 契约 预付咒术书(魔法文字/术式)
咏唱 无咏唱 - 次元魔法 异邦人(???)/素体(???) 请不要走
'''.split())

adds = {}; skips = {}
for name, cnt in names.items():
    n = name.strip()
    (skips if n in SKIP else adds)[n] = cnt

print('ADD distinct:', len(adds), 'occurrences:', sum(adds.values()))
print('SKIP distinct:', len(skips), 'occurrences:', sum(skips.values()))
print('total:', len(adds)+len(skips), sum(adds.values())+sum(skips.values()))
io.open(root + '_class_add.json','w',encoding='utf-8').write(json.dumps(adds, ensure_ascii=False, indent=1))
io.open(root + '_class_skip.json','w',encoding='utf-8').write(json.dumps(skips, ensure_ascii=False, indent=1))
# print ADD names only (sorted by family guess)
print()
for name, cnt in sorted(adds.items(), key=lambda x:-x[1]):
    print(f'{cnt:3d}  {name}')
