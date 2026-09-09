# -*- coding: utf-8 -*-
import io, json, os, shutil, datetime

root_dir = '咏唱库，补足'
os.makedirs(root_dir, exist_ok=True)

src = '迷深清洗工作2/异世界迷宫最深部_知识库/分析/咏唱库/咏唱库_main.yaml'
# copy final YAML into root 咏唱库，补足
shutil.copy2(src, root_dir + '/咏唱库_main.yaml')
# also sync root 咏唱库_main.yaml
shutil.copy2(src, '咏唱库_main.yaml')
print('copied YAML (bytes):', os.path.getsize(root_dir + '/咏唱库_main.yaml'))

# entries manifest
entries = json.load(io.open('迷深清洗工作2/咏唱补录_entries.json', encoding='utf-8'))
io.open(root_dir + '/补录条目清单.json', 'w', encoding='utf-8').write(json.dumps(entries, ensure_ascii=False, indent=1))

# summary markdown
from collections import Counter
sec = Counter()
for e in entries:
    t = e.get('type','')
    sec[t] += 1

md = []
md.append('# 咏唱库补录汇总（P8 unmatched 高频魔法族）')
md.append('')
md.append('> 生成日期：' + datetime.date.today().isoformat())
md.append('')
md.append('## 一、背景')
md.append('')
md.append('P8 阶段将 1575 条事件年表中的魔法咏唱名与 `咏唱库_main.yaml` 关联：769 条关联中 207 条 matched、562 条 unmatched。')
md.append('本次按咏唱库现有 schema（incantation_id / caster / type / incantation_text / magic_name_jp / magic_name_en / effect / source / edition / note 等）补录 **189 个条目**，覆盖 unmatched 中 **352 个名称 / 478 条** 的高频魔法族。')
md.append('')
md.append('## 二、补录内容')
md.append('')
md.append('| 家族/类别 | 代表条目 | 条目数 |')
md.append('|---|---|---|')
md.append('| Sehr・Wind 风系 | SehrWind/Ex・Wind/Wind・Madness/CannonSehr/Wind・放浪者/玉座既临路一条/LimitBreak・SehrWind等 | 22 |')
md.append('| 世界炎蛇/冰蛇・耶梦加得系 | 世界炎蛇(Midgardsormr Blaze)/世界冰蛇(Midgard・Frezze)/耶梦加得之炎·之霜 | 4 |')
md.append('| 火炎系 | FlameFlamberge/炽天之纤炎/灰姑娘的遗失之炎(Altymate・Liar)/燃烧吧断炎/焦热世界/不死杀的红莲龙等 | 26 |')
md.append('| 星魔法 Reevan/Line 系 | Reevan/Line(红『线』)/Tiara/我的世界的物语(Tales・Lasttiara)/向流星奉上心愿/幻转大天体等 | 11 |')
md.append('| Quartz 水晶/重力系 | Quartz/Quartz Shield/Gravity・Greed/Dark Sphere等 | 7 |')
md.append('| 治愈/光系 | 完全治愈/Cure Full/Growth・Extended/Light・Llaria/Light Mind/光之御旗(Nosfy・Flag)/Light Arrow・Brionac/SION等 | 26 |')
md.append('| 次元/冬系 | 过密次元的真冬(Di・OverWinter)/深渊次元的真夜/次元之夜/冬之异世界(Wintry・Dimension)/冻结・Niflheimr等 | 17 |')
md.append('| 维度・决战演算系 | 维度・决战演算(Dimension・Battle)/维度・曲战演算/维度・千算相杀等 | 4 |')
md.append('| BlackShift/次元基础系 | BlackShift/BlackShift・Overwrite/new・Reading/Replace・Connection/泡沫/魔法涡波术式等 | 10 |')
md.append('| 行路渐歧 Default 系 | Default(行路渐歧)/Default・武装破坏/Default・Field | 3 |')
md.append('| Impulse 系 | Impulse/Impulse Break | 2 |')
md.append('| 世界奉还阵/LevelUp 系 | 世界奉还阵/咒术Level Up/魔力变换 | 3 |')
md.append('| 咏唱句系 | 我为逐幻之幻/甚而无法存在于世界之中/祝福启新程/幼龙贪念日久难消/心异・无貌/不罚的大英雄等 | 17 |')
md.append('| 鲜血魔法系 | Blood/Blood Arrow/芬里尔・阿雷亚斯/相川涡波・阳滝/Fly Sophia/屠龙的龙刃/血脉稀释等 | 16 |')
md.append('| 王■落土/一闪系 | 王■落土(Lost・Vi・EithéA)/■道落土(Lord・Of・Lord)/亡灵一闪・致亲爱的一闪/缇达真正魔法 | 4 |')
md.append('| 守护者开场白补库 | guardian_40_艾德/guardian_40_缇缇(艾德自狱宣言)/guardian_50_罗德/guardian_100_阳滝 | 4 |')
md.append('| 木魔法系（艾德） | Wood・Growth/Trees・Contact/WoodQuake・创造/吸魔圣木/噬石常春藤/金刺毒花 | 7 |')
md.append('| 地/水/雷/箭系 | Earth/Water Wire/Water・Lightning/Magic Arrow/冰速箭/Divaplays・Arrow | 6 |')
md.append('| 其他魔法/场/咒术 | Dealing/Invisible・Field/Remove・Field/Vibration/Genoscythe/神铁锻造/Spotlight等 | 17 |')
md.append('| **合计** | | **189** |')
md.append('')
md.append('## 三、红线执行（逐字保真）')
md.append('')
md.append('- `incantation_text` 咏唱正句全部自 web 语料 block 原文逐字提取（含「」『』《》──· 间隔点原样保留）。')
md.append('- 170 条可核验咏唱正句经「空白归一化子串比对」逐字校验，**0 失败**；另 19 条原文未收录完整咏唱句（如叙事/术式/派生标签），以叙事原句或注明处理。')
md.append('- `source` 统一标注 章节 + 话号 + block_id；`edition` 按语料标注（web_original / web_reconstructed）。')
md.append('')
md.append('## 四、重跑 P8 关联结果')
md.append('')
md.append('| 状态 | 补录前 | 补录后 |')
md.append('|---|---|---|')
md.append('| matched | 207 | **688** |')
md.append('| unmatched | 562 | **81** |')
md.append('')
md.append('剩余 81 条 unmatched 全部为非咏唱项（剑技名/人名/书史/技能/试练/概念/道具，共 72 个名称），按用户要求**不补录**，维持 unmatched 并在 `notes` 中注明（如「非咏唱项：阿雷亚斯流剑术/旧人类史/魔人返还/星之理/使徒的试练」等）。')
md.append('')
md.append('## 五、产出文件')
md.append('')
md.append('- `咏唱库_main.yaml`：补录后的完整咏唱库（incantations 41→230 条，含补录批次分区注释与 p8_aliases）')
md.append('- `补录条目清单.json`：189 条补录条目结构化清单（含 chant/source/aliases，可复核）')
md.append('- 关联产物：`迷深清洗工作2/年表输出/_tmp_全/_p8_links.json`（已更新）、`年表输出/final_output/incantation_links.json/yaml`（已更新为 688/81）、`README_汇总.md`（统计已更新）')
md.append('')
md.append('## 六、未补录说明（非咏唱项 81 条）')
md.append('')
md.append('分类示例：**剑技**（冰结剑/次元斩裂剑/雪风/阿雷亚斯剑出万魔皆灭/赫勒比勒夏因二重奏剑等）、**人名**（缇亚拉/雷梵/帕林库洛/赫尔米娜涅夏/基里斯督莱纳等）、**书史**（旧人类史/旧历百年百怪妖异谈/碑白教圣经第五章/新历0年光神等）、**技能**（过去视/感应/魔人返还/魔石化/亚流体术/技能_？？？等）、**试练**（使徒的试练/第二十之试练/百十之试炼等）、**概念/道具**（星之理/次元之理/赫尔米娜的心脏/通信机/魔石线等）。')

io.open(root_dir + '/补录汇总说明.md', 'w', encoding='utf-8').write('\n'.join(md))
print('summary written')