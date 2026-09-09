# -*- coding: utf-8 -*-
import io, json, re, collections

entries_file = '迷深清洗工作2/咏唱补录_entries.json'
entries = json.load(io.open(entries_file, encoding='utf-8'))
lib_path = '迷深清洗工作2/异世界迷宫最深部_知识库/分析/咏唱库/咏唱库_main.yaml'

def section_of(e):
    i = e['id']
    if i in ('guardian_40_艾德','guardian_40_缇缇','guardian_50_罗德','guardian_100_阳滝'): return '八、守护者开场白补库（guardian_40/50/100）'
    if i in ('sehr_wind','wind_madness','sehr_wind_madness','cannon_sehr','cannon_sehr_madness','sehr_fang','ex_wind','wind_bless_draw','wind_umbrella','wind_放浪者','zeitlos_wind','rays_wind','无序之风','kaze_no_ya','kaze_no_ya_sanka','gyokuza_fuu','boukyaku_kakusan','limitbreak_sehrwind','ryuu_no_kaze','dragon_ardor','kaze_no_ude','jiyuu_no_kaze','raina_chant'): return '九、Sehr・Wind 风系补录'
    if i in ('world_flame_serpent','world_ice_serpent','jormungandr_blaze','jormungandr_frost'): return '十、世界炎蛇/冰蛇・耶梦加得系补录'
    if i in ('flame_flamberge','ice_flamberge','燃烧吧断炎','绽放吧诞炎','沥血吧焚炎','炎之剑系','agni_blaze','开辟之华炎','己魂焦热之骸炎','焦热世界','焦热世界的骸炎','萤火','firefly_mirage','flame_决戦炎域','flame_aegis','不死杀的红莲龙','cinderella_flame','flame_base','earthquake_darkpulse','贝丝_雷纳尔多系'): return '十一、火炎系补录（FlameFlamberge/炽天之纤炎/灰姑娘的遗失之炎等）'
    if i in ('reevan','line','tiara','tales_lasttiara','whose_yards_tiara','brave_fluorite','魔法_星属性咏唱_告白','celestial_garden','inverted_lagunequalia'): return '十二、星魔法 Reevan/Line/我的世界的物语系补录'
    if i in ('quartz','quartz_shield','quartz_blade','gravity_greed','gravity_daemon','dark_sphere','暗夜大盾'): return '十三、Quartz 水晶/重力系补录'
    if i in ('完全治愈','cure_full','growth_extended','light_llaria','light_mind','light_rod','light_arrow_brionac','light','nosfy_flag','light_variant_wall','light_cuffs','divine_shield','divine_arrow_spear','sion','inviolable_field','神圣魔法原形','代替','魅惑','sleep_mist','光之理不老不死','诺斯菲光魔法系','light_fullcure_remove'): return '十四、治愈/光系补录'
    if i in ('di_overwinter','di_overwinter_mirror','di_reverent_night','the_night','di_snow','di_winter_frost','di_winter_snowwind','wintry_dimension','wintry_quartetto','niflheimr_freeze','次元之冬歪冰世界','ice_battering_ram','ice_aegis','冰火拟似共鸣爆裂魔法'): return '十五、次元/冬系补录（过密次元的真冬/冬之异世界等）'
    if i in ('di_gradient_battle','di_difference','di_counting','dimension_sousa'): return '十六、维度・决战演算系补录'
    if i in ('blackshift','blackshift_overwrite','blackshift_overwrite_life','new_reading','replace_connection','shift','foam','jigen_eishou_tsumi','magic_namida_术式'): return '十七、BlackShift/次元基础系补录'
    if i in ('default','default_armorbreak','default_field'): return '十八、行路渐歧 Default 系补录'
    if i in ('impulse','impulse_break'): return '十九、Impulse 系补录'
    if i in ('世界奉还阵','level_up','魔力变换'): return '二十、世界奉还阵/LevelUp 系补录'
    if i in ('慕影死神','我为逐幻之幻','甚而无法存在于世界之中','我于此弃旗','世界(你)的祝福已然无关紧要','祝福启新程','想起收束','加速_孤乃加速之魂','心异','不罚的大英雄','咏唱幼龙贪念日久难消','咏唱无名无姓皆尽忘舍','代价咏唱火炎','涡波复合咒术咏唱','因我之一切于此起誓'): return '二十一、咏唱句系补录'
    if i in ('blood','blood_arrow','blood_warez','血脉稀释','bloodline_lockfield','bloodland_transform','芬里尔阿雷亚斯','假想诺文阿雷亚斯','鲜血魔法相川涡波阳滝','大洪水','lostfania','两百一十四年西南解放战线','fly_sophia','屠龙的龙刃','血海歌魔法'): return '二十二、鲜血魔法系补录'
    if i in ('王■落土','■道落土','亡灵一闪_致亲爱的一闪','缇达真正魔法'): return '二十三、王■落土/一闪系补录'
    if i in ('阳滝精神干涉魔法','亡失的殉教者','启蒙家的再调律','对始祖封印魔方阵','magic_bag','神铁锻造','vibration','genoscythe','血之结界咏唱'): return '二十四、其他魔法/咒术补录'
    if i in ('wood_growth','trees_contact','woodquake','吸魔圣木','噬石常春藤','金刺毒花','wood_ymir'): return '二十五、木魔法系补录（艾德）'
    if i in ('earth','water_wire','water_lightning','magic_arrow','ice_speed_arrow','divaplays_arrow'): return '二十六、地/水/雷/箭系补录'
    if i in ('dealing','invisible_field','remove_field','careful_strath_field','shunposhion_feather','infate','spotlight','ice_cold','grand_fall'): return '二十七、其他魔法/场/咒术补录'
    return '补充'

def yaml_scalar(s):
    s = str(s)
    if s == '': return '""'
    if re.search(r'[:#\[\]{},&*!|>\'\"%@]', s) or s != s.strip() or s[0] in '-? ':
        return json.dumps(s, ensure_ascii=False)
    return s

def emit_entry(e):
    lines = []
    lines.append('  - incantation_id: ' + e['id'])
    if e.get('caster'):
        lines.append('    caster: ' + yaml_scalar(e['caster']))
    if e.get('guardian_rank'):
        lines.append('    guardian_rank: ' + yaml_scalar(e['guardian_rank']))
    lines.append('    type: ' + yaml_scalar(e.get('type','咏唱')))
    chant = e.get('chant','')
    if chant:
        if '\n' in chant:
            lines.append('    incantation_text: |')
            for ln in chant.split('\n'):
                lines.append('      ' + ln)
        else:
            lines.append('    incantation_text: ' + yaml_scalar(chant))
    else:
        lines.append('    incantation_text: ""')
    if e.get('jp'):
        lines.append('    magic_name_jp: ' + yaml_scalar(e['jp']))
    if e.get('en'):
        lines.append('    magic_name_en: ' + yaml_scalar(e['en']))
    if e.get('effect'):
        lines.append('    effect: ' + yaml_scalar(e['effect']))
    if e.get('source'):
        lines.append('    source: ' + yaml_scalar(e['source']))
    if e.get('edition'):
        lines.append('    edition: ' + yaml_scalar(e['edition']))
    if e.get('note'):
        lines.append('    note: ' + yaml_scalar(e['note']))
    if e.get('aliases'):
        lines.append('    p8_aliases: [' + ', '.join(json.dumps(a, ensure_ascii=False) for a in e['aliases']) + ']')
    return '\n'.join(lines)

groups = collections.OrderedDict()
for e in entries:
    sec = section_of(e)
    groups.setdefault(sec, []).append(e)

lib = io.open(lib_path, encoding='utf-8').read()
anchor = '# ─────────────── 涡波咏唱成长链（incantation_evolution）───────────────'
assert anchor in lib, 'anchor not found'

supp = []
supp.append('# ═══════════════════════════════════════════════════════════════')
supp.append('# 补录批次（P8 unmatched 高频魔法族补录）')
supp.append('# 依据：_p8_links.json unmatched 562 条中，补录约 345 个名称（189 个条目，含别名覆盖）')
supp.append('# 红线：incantation_text 咏唱正句逐字保真（自 web 语料 block 原文提取）')
supp.append('# source 格式：章节 + 话号 + block_id')
supp.append('# 非咏唱项（剑技/人名/书史/技能/试练/概念/道具等约 87 条）不补录，维持 unmatched')
supp.append('# ═══════════════════════════════════════════════════════════════')
for sec, evs in groups.items():
    supp.append('  # ────────────────── ' + sec + ' ──────────────────')
    for e in evs:
        supp.append(emit_entry(e))

supp_yaml = '\n'.join(supp)
lib_new = lib.replace(anchor, supp_yaml + '\n' + anchor)

io.open(lib_path, 'w', encoding='utf-8').write(lib_new)
print('merged into', lib_path)
print('new entries:', len(entries))
print('library size:', len(lib_new))