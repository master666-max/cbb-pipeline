
# -*- coding: utf-8 -*-
import io, json
entries_file = '迷深清洗工作2/咏唱补录_entries.json'
entries = json.load(io.open(entries_file, encoding='utf-8'))
def add(**kw):
    entries.append(kw)

# ── 世界炎蛇/冰蛇・耶梦加得系 ──
add(id='world_flame_serpent', caster='玛莉亚（阿尔缇所授）', type='普通魔法咏唱（火炎系·世界蛇）',
    chant='「──『璀璨星辰，无限远泛，饕餮殄灭』！『世界炎蛇』！！」',
    jp='世界炎蛇', en='Midgardsormr Blaze',
    effect='同时消耗HP和MP的高强度火炎魔法（阿尔缇传授），玛莉亚输出最高之魔法',
    source='第五章 第五章-分岐点『前祭』 (md-0108)', edition='web_original',
    note='别名：魔法_世界炎蛇／世界炎蛇(Midgardsormr Blaze)／世界炎蛇(昔日玛利亚戒打法)；亦见「──火炎魔法《世界炎蛇》。」（第九章 第458话 百一十『恋』 md-0334）、「辛苦了。——『世界炎蛇』。」（第八章 第356话 异世界的居所 md-0042）',
    aliases=['世界炎蛇','魔法_世界炎蛇','世界炎蛇(Midgardsormr Blaze)','世界炎蛇(昔日玛利亚戒打法)'])

add(id='world_ice_serpent', caster='相川涡波（冰系）', type='普通魔法咏唱（冰结系·世界蛇）',
    chant='「——魔法《世界冰蛇（Midgard・Frezze）》。」',
    jp='世界冰蛇', en='Midgard・Frezze',
    effect='世界级冰蛇魔法，可将对手撞入深海',
    source='第九章 第447话 梦的奴隶 (md-0240)', edition='web_original',
    note='亦见「──冰结魔法《世界冰蛇》。」（第九章 第458话 百一十『恋』 md-0334）',
    aliases=['世界冰蛇','MidgardFrezze'])

add(id='jormungandr_blaze', caster='玛莉亚', type='普通魔法咏唱（火炎系·衔尾蛇）',
    chant='「──『我自衔尾，逡巡蹒跚，如梦似幻』『璀璨星辰，无限远泛，饕餮殄灭』、『耶梦加得之炎』－！！」',
    jp='耶梦加得之炎', en='Jörmungandr・Blaze',
    effect='衔尾之蛇（耶梦加得）之炎，世界蛇火炎咏唱',
    source='第四章 第168话 帕林库洛·勒伽西对Living-Legend-Party (md-0197)', edition='web_original',
    note='亦见「──『耶梦加得之炎』！」（第四章 第174话 《世界奉还阵》 md-0230）、「──『耶梦加得之炎』」（第六章 第246话 走失児童 md-0121）',
    aliases=['耶梦加得之炎','魔法_世界火蛇'])

add(id='jormungandr_frost', caster='相川涡波（冰系）', type='普通魔法咏唱（冰结系·衔尾蛇）',
    chant='「──冻结魔法『耶梦加得之霜』！」',
    jp='耶梦加得之霜', en='Jörmungandr・Frost',
    effect='冰蛇跃出的冻结魔法（衔尾蛇之霜）',
    source='第四章 第158话 木之理的盗窃者 (md-0146)', edition='web_original',
    note='亦见「──『耶梦加得之霜』！！」（第四章 第138话 33层、34层 md-0042）、「──冻结魔法『耶梦加得之霜』！」（第四章 第173话 渴求着彼此的两人 md-0219）',
    aliases=['耶梦加得之霜'])

# ── FlameFlamberge／炎剑系 ──
add(id='flame_flamberge', caster='玛莉亚／阿尔缇', type='普通魔法咏唱（火炎剑系）',
    chant='「在剑身上蔓延开来！——魔法《Flame・flamberge》！！」',
    jp='Flame・Flamberge', en='Flame・Flamberge',
    effect='火焰剑魔法（阿尔缇传授），与『世界炎蛇』并称消耗HP和MP的两种魔法；可令火炎在剑身蔓延',
    source='第十章 第486话 地狱七十，亡灵引路。愿君亦能 (md-0178)', edition='web_original',
    note='亦见「——《FlameFlamberge》。」（第九章 第459话 第百十之试练『恋』 md-0336）、「——《Flame Flamberge》《Water Wire》《Ice Battering Ram》…」（第7-3章 第336话 阶梯 7373md-0111）',
    aliases=['FlameFlamberge','Flame・flamberge'])

add(id='ice_flamberge', caster='（冰系魔法使）', type='普通魔法咏唱（冰结剑系）',
    chant='「……库！——魔、魔法《Iceflamberge》！」',
    jp='Ice・Flamberge', en='Ice・Flamberge',
    effect='冰之火焰剑（冰剑），用以排出理的盗窃者的魔石',
    source='第十章 第486话 地狱七十 (md-0177)', edition='web_original',
    note='亦见「——《Ice flamberge》。」（第八章 第398话 『我们』 md-0237）、「那么……——《Ice・Flamberge》。」（第八章 第402话 身高相较 md-0262）',
    aliases=['Iceflamberge'])

add(id='燃烧吧断炎', caster='玛莉亚', type='咏唱（火炎/诅咒）',
    chant='「抱歉，我现在要强化『诅咒』的效力……！——『燃烧吧断炎』『随彼纤纤，逡巡蹒跚，如梦似幻』『将我一饮而尽』――！！」',
    jp='燃烧吧断炎', en='—',
    effect='玛莉亚强化『忘却』诅咒效力的火炎咏唱（衔尾之蛇系列）',
    source='第八章 第371话 读书 (md-0077)', edition='web_original',
    note='亦见「立刻把一切都返还给她！『燃烧吧断炎』！！——咒术『Flame』！！」（第八章 第367话 缇达此人 md-0068）',
    aliases=['燃烧吧断炎'])

add(id='绽放吧诞炎', caster='阿尔缇／玛莉亚', type='咏唱（火炎·圣火）',
    chant='「──『绽放吧诞炎』，『原初原罪之万障圣火』！『开辟之华炎』！！」',
    jp='绽放吧诞炎', en='—',
    effect='火炎系咏唱上句（诞炎），接续『开辟之华炎』',
    source='第三章 第四章-鍊狱十层，英雄来兮。异形之物，静待君临。 (md-0217)', edition='web_reconstructed+web_original',
    note='亦见「『绽放吧诞炎』、『沥血吧焚炎』──」（第三章 第三章『我』的圣诞祭的结束 md-0183）、「『绽放吧诞炎』『燃炽吧闪炎』——」（第八章 第360话 草草读过的时间 md-0054）',
    aliases=['绽放吧诞炎'])

add(id='沥血吧焚炎', caster='阿尔缇／玛莉亚', type='咏唱（火炎）',
    chant='「『绽放吧诞炎』、『沥血吧焚炎』──」',
    jp='沥血吧焚炎', en='—',
    effect='火炎系咏唱下句（焚炎）',
    source='第三章 第三章『我』的圣诞祭的结束 (md-0183)', edition='web_reconstructed+web_original',
    aliases=['沥血吧焚炎'])

add(id='炎之剑系', caster='玛莉亚／贝丝系', type='普通魔法咏唱（火炎剑系）',
    chant='「──『闪耀吧炎剑』，──『火焰剑』。」',
    jp='燃烧吧炎剑／闪耀吧炎之剑／火焰剑／炎之剑', en='Flame・Sword',
    effect='火焰剑系近身魔法（火炎缠绕剑身）',
    source='第三章 第四章-鍊狱十层，英雄来兮。异形之物，静待君临。 (md-0220)', edition='web_reconstructed+web_original',
    note='P8 拆分：燃烧吧炎剑／闪耀吧炎之剑／火焰剑／炎之剑，实为同族；亦见「──『闪耀吧炎之剑』！！」（第四章 第175话 暗之理与火之理 md-0235）、「──『炎之剑』！」（第四章 第162话 《失踪》 md-0166）、「──『噬咬侵蚀之』！『炎之剑』！！」（第五章 第214话 诺斯菲 md-0179）',
    aliases=['燃烧吧炎剑','闪耀吧炎之剑','火焰剑','炎之剑'])

add(id='agni_blaze', caster='相川涡波（火系）／阿尔缇', type='普通魔法咏唱（火炎·纤炎）',
    chant='「『燃炽吧闪炎』，『衔尾之蛇，以彼纤纤，吞天噬地』。──『炽天之纤炎』。」',
    jp='炽天之纤炎', en='Agni-Blaze',
    effect='衔尾之蛇以彼纤纤吞天噬地的火炎纤炎魔法',
    source='第三章 第一章-番外战 (md-0171)', edition='web_reconstructed+web_original',
    note='亦见「——《炽天之纤炎（Agni-Blaze）》。」（第九章 第459话 第百十之试练『恋』 md-0336）',
    aliases=['炽天之纤炎'])

add(id='开辟之华炎', caster='阿尔缇／玛莉亚', type='普通魔法咏唱（火炎·圣火）',
    chant='「──『绽放吧诞炎』，『原初原罪之万障圣火』！『开辟之华炎』！！」',
    jp='开辟之华炎', en='—',
    effect='原初原罪之万障圣火的开辟华炎',
    source='第三章 第四章-鍊狱十层，英雄来兮。异形之物，静待君临。 (md-0217)', edition='web_reconstructed+web_original',
    aliases=['开辟之华炎'])

add(id='己魂焦热之骸炎', caster='阿尔缇／玛莉亚', type='普通魔法咏唱（火炎·骸炎）',
    chant='「──魔法『己魂焦热之骸炎』！！」',
    jp='己魂焦热之骸炎', en='Teana・Blaze',
    effect='以己魂为薪的火炎骸炎魔法',
    source='第三章 第四章-鍊狱十层，英雄来兮。异形之物，静待君临。 (md-0218)', edition='web_reconstructed+web_original',
    aliases=['己魂焦热之骸炎','Teana·Blaze(自魂焦热之骸炎)'])

add(id='焦热世界', caster='阿尔缇', type='普通魔法咏唱（火炎·领域）',
    chant='「──魔法『Flame・决战炎域』、魔法『焦热世界』！！」',
    jp='焦热世界', en='Scorch・World',
    effect='火炎领域魔法（焦热世界）',
    source='第三章 第四章-鍊狱十层，英雄来兮。异形之物，静待君临。 (md-0214)', edition='web_reconstructed+web_original',
    aliases=['焦热世界'])

add(id='焦热世界的骸炎', caster='玛莉亚', type='普通魔法咏唱（火炎·骸炎）',
    chant='「——《焦热世界的骸炎（In・Lavos-Blaze）》。」',
    jp='焦热世界的骸炎', en='In・Lavos-Blaze',
    effect='焦热世界的骸炎（In・Lavos-Blaze）',
    source='第九章 第459话 第百十之试练『恋』 (md-0337)', edition='web_original',
    aliases=['焦热世界的骸炎'])

add(id='萤火', caster='相川涡波', type='普通魔法咏唱（火属性）',
    chant='「──fi、『萤火』！」',
    jp='萤火', en='Firefly',
    effect='火属性魔法（萤火），与缇亚共鸣扩大范围',
    source='第一章 第二章-谁才是奴隷 (md-0043)', edition='web_reconstructed',
    note='亦见「──魔法『Flame・决战炎域』、『萤火』」（第四章 第137话 31层、32层 md-0035，与缇亚共鸣）',
    aliases=['萤火','萤火(火属性魔法)','共鸣魔法_萤火'])

add(id='firefly_mirage', caster='玛莉亚', type='普通魔法咏唱（火炎·幻影系）',
    chant='「──『Firefly·蜃气楼』、『Firefly·幻影』。」',
    jp='Firefly・蜃气楼／Firefly・幻影', en='Firefly・Mirage / Firefly・Phantom',
    effect='蜃气楼以温度差影响光的折射扰乱距离感；幻影以火焰创造人形幻影',
    source='第五章 第五章-分岐点『前祭』 (md-0108)', edition='web_original',
    aliases=['Firefly・蜃气楼','Firefly・幻影'])

add(id='flame_决戦炎域', caster='阿尔缇／拉丝缇娅拉（共鸣）', type='普通魔法咏唱/共鸣魔法（火炎·领域）',
    chant='「──『Flame・决战炎域』！！」',
    jp='Flame・决战炎域', en='Flame・Battlefield',
    effect='火炎决战领域魔法',
    source='第四章 第172话 《我》的最后一战 (md-0215)', edition='web_original',
    note='亦见「──魔法『Flame・决战炎域』、魔法『焦热世界』！！」（第三章 第四章-鍊狱十层 md-0214）',
    aliases=['Flame·决战炎域','共鸣魔法_Flame决战炎域'])

add(id='flame_aegis', caster='拉丝缇娅拉', type='共鸣魔法（守护炎）',
    chant='「不错呢。这个魔法是为了守护涡波先生的魔法。──那就叫它共鸣魔法『Flame・Aegis（守护炎）』好了」',
    jp='Flame・Aegis（守护炎）', en='Flame・Aegis',
    effect='为守护涡波而命名的共鸣魔法（火焰守护之盾）',
    source='第一章 第四章-二十层阶处，魍魉沉影池。盼求君临至，直至黯逝时。 (md-0038)', edition='web_reconstructed',
    note='亦见「──共鸣魔法『Flame・Ageis』！」（第四章 第158话 木之理的盗窃者 md-0147）',
    aliases=['共鸣魔法_FlameAegis守护炎','Flame·Ageis'])

add(id='不死杀的红莲龙', caster='法夫纳／格连（血魔法）', type='真正魔法级咏唱（血·红莲龙）',
    chant='「『『——**魔法**《不死杀的红莲龙》（Sin・BloodFafnir）——』』」',
    jp='不死杀的红莲龙', en='Sin・BloodFafnir',
    effect='血魔法；第三个效果为透过『黑线』令当事人无意识地使用魔法',
    source='第十章 第487话 第七十之试炼『地狱』 (md-0189)', edition='web_original',
    aliases=['不死杀的红莲龙'])

add(id='cinderella_flame', caster='玛莉亚（第百十之试炼）', type='真正魔法级咏唱（火炎·终焉）',
    chant='「——魔法（・・）《灰姑娘的遗失之炎（Altymate・Liar）》。」',
    jp='灰姑娘的遗失之炎', en='Altymate・Liar',
    effect='蕴含失恋怒火的第百十之试炼魔法，烧尽『忘却』之祝福/诅咒，为挚友阿尔缇而发动',
    source='第九章 第459话 第百十之试练『恋』 (md-0340)', edition='web_original',
    note='上句「『所谓人者，非唯躯骸』『倘此胸鼓动尚在，则心中灯火不灭』」；亦见「——那便是这个『第百十之试炼』，亦即**魔法（・・）**《灰姑娘的遗失之炎（Altymate・Liar）》。」（第九章 第460话 マ莉亚・迪斯特拉斯的终点 md-0346）、「——**魔法（・・）**《灰姑娘的遗失之炎（Altymate・Liar）》。」（第十章 第501话 『真正的丝线』 md-0278）',
    aliases=['灰姑娘的遗失之炎Altymate_Liar','灰姑娘的遗失之炎(Altymate・Liar)'])

add(id='flame_base', caster='缇亚（火属性）', type='普通魔法咏唱/咒术（火属性基础）',
    chant='「知道了！──『Flame（火焰）』！！」',
    jp='Flame（火焰）', en='Flame',
    effect='火属性基础魔法/咒术',
    source='第7-2章 第285话 等级提升 (7272md-0027)', edition='web_original',
    note='亦见「立刻把一切都返还给她！『燃烧吧断炎』！！——咒术『Flame』！！」（第八章 第367话 缇达此人 md-0068）',
    aliases=['Flame','flame','Flame(火焰)'])

add(id='earthquake_darkpulse', caster='格连·沃克', type='普通魔法咏唱（地属性）',
    chant='「——魔法《Earthquake・黑脉（darkpulse）》！！」',
    jp='Earthquake・黑脉', en='Earthquake・Darkpulse',
    effect='将99层宽广地面转换为格连之翼的地震魔法',
    source='第十章 第474话 格连・沃克 (md-0095)', edition='web_original',
    aliases=['贝丝_Earthquake'])

add(id='贝丝_雷纳尔多系', caster='贝丝（猫耳少女）／雷纳尔多·沃尔斯（老工匠）', type='普通魔法咏唱（火属性·66层篇）',
    chant='（P8 派生名：贝丝_FlameAccel／贝丝_炎之剑／贝丝_Earthquake／贝丝_FullBlazing／雷纳尔多_FullBlazing；原文咏唱散见 第五章 66层篇，未收录完整咏唱句）',
    jp='贝丝／雷纳尔多系魔法（FlameAccel・FullBlazing等）', en='—',
    effect='66层地下篇中贝丝与雷纳尔多使用的火属性魔法（加速火焰/火焰剑/地震/全燃）',
    source='第五章 第187-189话（66层篇） (md-0008/md-0016)', edition='web_original',
    aliases=['贝丝_FlameAccel','贝丝_炎之剑','贝丝_Earthquake','雷纳尔多_FullBlazing','贝丝_FullBlazing'])

io.open(entries_file, 'w', encoding='utf-8').write(json.dumps(entries, ensure_ascii=False, indent=1))
print('entries total:', len(entries))
