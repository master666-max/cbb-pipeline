
# -*- coding: utf-8 -*-
import io, json
entries_file = '迷深清洗工作2/咏唱补录_entries.json'
entries = json.load(io.open(entries_file, encoding='utf-8'))
def add(**kw):
    entries.append(kw)

# ── 星魔法 Reevan/Line 系 ──
add(id='reevan', caster='缇亚拉／诺瓦露（星之理的盗窃者）', type='普通魔法咏唱（星魔法）',
    chant='「——星魔法《Reevan（レヴァン）》」',
    jp='Reevan（星魔法）', en='Reevan',
    effect='星之魔法，产生白虹光芒，可强化与弱化（弥补鸿沟）；由千年后的继承者以『血之力』继承',
    source='第八章 第397话 『被造物』 (md-0230)', edition='web_original',
    note='别名：星魔法Reevan／Revan；诺瓦露从诺瓦露（レヴァン）继承术式（第十章 第488话 赫勒比勒夏因 md-0197）',
    aliases=['Reevan','星魔法Reevan','Revan'])

add(id='line', caster='缇亚拉／莱纳·赫勒比勒夏因', type='普通魔法咏唱（星魔法/血术·线）',
    chant='「『——我（私）们知晓了这个道理——血术《Line》』」',
    jp='Line（红『线』/魔石线）', en='Line',
    effect='星魔法/血术《Line》：以红『线』记录千年前编纂的文字并收束至『这个瞬间』，可造赤色庭院Field，改写命运之线',
    source='第十章 第499话 百二十『绊』，众魂相聚。 (md-0269)', edition='web_original',
    note='亦见「──咒术『Line・React』！！」（第7-1章 第275话 将军 7171md-0075）；P8 别名：血术《Line》／血术/咒术《Line》／Line·React／Line魔石线',
    aliases=['Line','血术《Line》','血术/咒术《Line》','Line·React','Line魔石线'])

add(id='tiara', caster='缇亚拉（千年前圣人）', type='研究魔法（时间跳跃/复制/不死）',
    chant='「『这就是魔法《Tiara》的价值所在……以时间跳跃为起点，再来是『复制』与『不死』』」',
    jp='Tiara', en='Tiara',
    effect='以时间跳跃为起点，实现『复制』与『不死』的魔法研究（制造血之人偶）',
    source='第八章 第404话 感想战 (md-0277)', edition='web_original',
    aliases=['Tiara'])

add(id='tales_lasttiara', caster='拉斯缇亚拉（现人神）／缇亚拉', type='真正魔法级咏唱（神圣·终焉）',
    chant='「——**魔法（・・）**《我的世界的物语（Tales・Lasttiara）》！！」',
    jp='我的世界的物语', en='Tales・Lasttiara',
    effect='将『拉斯缇亚拉人生的一切』（缇亚拉所撰写的故事）具现为神圣魔法的终焉级魔法；倾注拯救相川阳滝的愿望',
    source='第八章 第405话 神圣之理 (md-0287)', edition='web_original',
    note='P8 别名：我的世界的物语TalesLasttiara／tales_lasttiara／魔法_TalesLasttiara／魔法《我的世界的物语(Tales・Lasttiara)》',
    aliases=['我的世界的物语TalesLasttiara','tales_lasttiara','魔法_TalesLasttiara','魔法《我的世界的物语(Tales・Lasttiara)》'])

add(id='whose_yards_tiara', caster='阳滝', type='普通魔法咏唱（神圣·回复）',
    chant='「——**魔法（・・）**《愈阳之虹冠（Whose・yards・Tiara）》」',
    jp='愈阳之虹冠', en='Whose・yards・Tiara',
    effect='回复魔法，将无法根治的「吸引『魔之毒』的体质」轻易消去',
    source='第八章 第412话 冻狱百层，女子闭心。伊人将去，莫与君行。 (md-0333)', edition='web_original',
    aliases=['whose_yards_tiara'])

add(id='brave_fluorite', caster='诺瓦露（星之理的盗窃者）', type='普通魔法咏唱（星魔法）',
    chant='『——魔法《向流星奉上心愿（brave・fluorite）》啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊——！！！！！！！！』',
    jp='向流星奉上心愿', en='brave・fluorite',
    effect='向流星奉上心愿的星之魔法',
    source='第十章 第469话 青鸟 (md-0067)', edition='web_original',
    aliases=['向流星奉上心愿(brave・fluorite)'])

# ── Quartz/水晶・地 ──
add(id='quartz', caster='相川涡波（精制）', type='普通魔法咏唱（水晶魔法）',
    chant='「这、这样的话，我就将钻石精制一下！──水晶魔法『Quartz』！」',
    jp='Quartz（水晶魔法）', en='Quartz',
    effect='水晶精制/水晶攻击魔法',
    source='第五章 第189话 决定地下生活的方针 (md-0017)', edition='web_original',
    note='亦见「──水晶魔法『Quartz』──」（第五章 第139话 存钱攒经验 md-0046）、「——『Quartz』！还有【星之理】！！」（第7-3章 第324话 镜之魔力 7373md-0029）',
    aliases=['Quartz','水晶魔法_Quartz'])

add(id='quartz_shield', caster='诺文·阿雷亚斯（地之理的盗窃者）', type='普通魔法咏唱（水晶魔法·盾）',
    chant='「――《Quartz Shield》。」',
    jp='Quartz Shield', en='Quartz Shield',
    effect='水晶护盾魔法（亦可寄宿于戒指）',
    source='第7-3章 第320话 血之源泉 (7373md-0004)', edition='web_original',
    note='亦见寄宿着『Quartz Shield』力量的戒指（第五章 第141话 走上锻冶师之路 md-0055）',
    aliases=['水晶魔法_QuartzShield','Quartz Shield'])

add(id='quartz_blade', caster='诺文·阿雷亚斯（地之理的盗窃者）', type='普通魔法咏唱（水晶魔法·刃）',
    chant='「──『Quartz Blade・Size』！！」',
    jp='Quartz Blade・Size', en='Quartz Blade・Size',
    effect='水晶刃尺寸调整（剑刃水晶化）',
    source='第五章 第179话 自《牢狱》中超脱 (md-0260)', edition='web_original',
    aliases=['Quartz_Blade_Size'])

add(id='gravity_greed', caster='相川涡波（共鸣）', type='共鸣魔法（重力）',
    chant='「真是庞大且危险的『**魔力（・・）**』呢。但是，我并非孤身一人——共鸣魔法（・・・・）《Gravity・Greed》。」',
    jp='Gravity・Greed（重力・强欲）', en='Gravity・Greed',
    effect='重力系共鸣魔法，温柔地将对手压倒并令其失去意识',
    source='第十章 第502话 『败北』 (md-0287)', edition='web_original',
    note='亦见「——《gravity・greed》。温柔地将她压倒，让她失去意识吧。」（第十章 第498话 LastBattle md-0259）、「──魔法『Gravity・Field』哦哦哦！！」（第7-2章 第299话 再战 7272md-0128）',
    aliases=['Gravity','GravityGreed','Gravity・Greed','gravity_field'])

add(id='gravity_daemon', caster='（共鸣）', type='共鸣魔法（重力）',
    chant='「──共鸣魔法『Gravity・Daemon』！」',
    jp='Gravity・Daemon（重力・幽灵）', en='Gravity・Daemon',
    effect='重力幽灵共鸣魔法',
    source='第四章 第159话 交错 (md-0148)', edition='web_original',
    aliases=['Gravity·Daemon'])

add(id='dark_sphere', caster='缇亚拉／帕林库洛系（暗魔法）', type='普通魔法咏唱（暗属性）',
    chant='「──『Dark Sphere』」',
    jp='Dark Sphere', en='Dark Sphere',
    effect='暗属性球体魔法',
    source='第四章 第174话 《世界奉还阵》 (md-0230)', edition='web_original',
    note='亦见「喂喂，这玩应儿不妙过头了吧⋯⋯！『Dark Sphere』！！」（第四章 第173话 渴求着彼此的两人 md-0223）',
    aliases=['Dark Sphere'])

add(id='暗夜大盾', caster='帕林库洛·勒迦希（暗之理的盗窃者）', type='魔法（暗·防御）',
    chant='（叙事：深不见底的黑暗似乎要将所有的光明吞噬一样──形成了一面暗夜大盾）',
    jp='暗夜大盾', en='Night・Shield',
    effect='吞噬光明的暗夜大盾',
    source='第四章 第175话 暗之理与火之理 (md-0236)', edition='web_original',
    aliases=['暗夜大盾'])

# ── 治愈/光系 ──
add(id='完全治愈', caster='相川涡波（光/神圣魔法）', type='普通魔法咏唱（神圣·治愈）',
    chant='「──《完全治愈》。好了，治疗结束~。」',
    jp='完全治愈', en='Full Cure',
    effect='神圣治愈魔法（完全治愈）',
    source='第一章 第一章-异世界迷宫 (md-0015)', edition='web_reconstructed',
    note='亦见「──神圣魔法『完全治愈』。」（第六章 以异世界迷宫的最深部为目标 md-0083）',
    aliases=['完全治愈'])

add(id='cure_full', caster='（元老院/治疗系神圣魔法）', type='普通魔法咏唱（神圣·治愈）',
    chant='「好——魔法《Curefull》。」',
    jp='Cure Full', en='Cure Full',
    effect='神圣治愈魔法（Cure Full/FullCure），使『候补』不死并强化',
    source='第九章 第446话 真正的研究者 (md-0236)', edition='web_original',
    note='亦见「──魔法『Full Cure』。拉古涅也一起来用恢复魔法⋯⋯！」（第7-2章 第300话 坦率的心 7272md-0137）',
    aliases=['Cure','FullCure','Cure Full','CureFull(神圣魔法)','perfect-cure','full_cure'])

add(id='growth_extended', caster='诺斯菲·弗茨亚茨（神圣魔法）', type='普通魔法咏唱（神圣·强化）',
    chant='「不对，现在就是那个时候。我刚才对玛利亚也说过了，这可是诺斯菲为我准备的机会啊！──『Growth・Extended』！！」',
    jp='Growth・Extended', en='Growth・Extended',
    effect='神圣魔法Growth的扩展强化形态',
    source='第7-2章 第301话 地下街的战斗 (7272md-0144)', edition='web_original',
    note='亦见「我很清楚。所以、现在才要使用啊——共鸣魔法《Growth・Extended》。」（第八章 第398话 『我们』 md-0235）',
    aliases=['Growth(神圣魔法)','Growth_Extended','Growth·Extended'])

add(id='light_llaria', caster='诺斯菲·弗茨亚茨（光之理的盗窃者）', type='普通魔法咏唱（光系）',
    chant='「行了，差不多就是这样，赶紧开始战斗吧！不战斗的话事后一定会感到后悔的！自然，战斗了也一样会后悔吧！既如此，那么战与不战两相比较之下，还是战斗之后再后悔更划算！──魔法『Light・Llaria』！！呵呵，那就更无需多虑，接下来唯有一战而已，不是么！？作为『交流』的专家，由我来向诸位担保！」',
    jp='Light・Llaria', en='Light・Llaria',
    effect='光系魔法（交流型），引发战斗欲望',
    source='第六章 第253话 交流 (md-0186)', edition='web_original',
    note='亦见《Light・ilaia》（第九章 第449话 ＂恶龙讨伐＂ md-0256/md-0257）',
    aliases=['Light·Llaria','LightIlaia'])

add(id='light_mind', caster='诺斯菲·弗茨亚茨（光之理的盗窃者）', type='普通魔法咏唱（光·精神干涉）',
    chant='「我等被施加的是一种基本的光魔法──『Light Mind』！」',
    jp='Light Mind', en='Light Mind',
    effect='世界上最为知名的光系精神干涉魔法（令人坦率），由诺斯菲使用时效果惊人',
    source='第7-2章 第298话 旧识 (7272md-0125)', edition='web_original',
    aliases=['Light Mind','light_mind'])

add(id='light_rod', caster='诺斯菲·弗茨亚茨（光之理的盗窃者）', type='普通魔法咏唱（光系）',
    chant='「——《Light Rod》！」',
    jp='Light Rod', en='Light Rod',
    effect='光之杖魔法（光系攻击/治疗）',
    source='第7-3章 第336话 阶梯 (7373md-0112)', edition='web_original',
    note='亦见「——魔法『Light Rod』」（第7-2章 第312话 ■■六十，盈满■■ 7272md-0223）',
    aliases=['LightRod','诺斯菲_LightRod'])

add(id='light_arrow_brionac', caster='诺斯菲·弗茨亚茨（光之理的盗窃者）', type='普通魔法咏唱（光·箭）',
    chant='「我、我们现在已经在战斗了！！作为敌人！作为涡波大人『最大的敌人』，我现在就在和您战斗！——『Light Arrow·Brionac』！！」',
    jp='Light Arrow・Brionac（光矢布里欧纳克）', en='Light Arrow・Brionac',
    effect='光之箭魔法（Light Arrow），布里欧纳克（Brionac）强化形态',
    source='第7-2章 第314话 (7272md-0232)', edition='web_original',
    note='亦见「——『Light Arrow』！！」（第7-2章 第313话 7272md-0230）、「──『Light Brionac』！！」（第7-2章 第299话 再战 7272md-0134）、「『光啊、闪耀吧』『Light Arrow·Brionac』！」',
    aliases=['LightArrow','Light Arrow','Light_Brionac','light_brionac','光枪Brionac','光矢布里欧纳克(Light Arrow·Brionac)','光魔法_Shine_Arrow'])

add(id='light', caster='诺斯菲·弗茨亚茨（光之理的盗窃者）', type='普通魔法咏唱（光系）',
    chant='「——魔法『Light』！『Light Field』！『光之御旗（Nosfy·Flag）』！！」',
    jp='Light／Light Field', en='Light / Light Field',
    effect='光系基础魔法与光之领域（三连咏唱之一）',
    source='第7-3章 第334话 旗手 (7373md-0095)', edition='web_original',
    aliases=['Light','Light Field','LightField'])

add(id='nosfy_flag', caster='诺斯菲·弗茨亚茨（光之理的盗窃者）', type='普通魔法咏唱（光·旗帜）',
    chant='「——魔法《光之御旗（Nosfy·Flag）》。」',
    jp='光之御旗', en='Nosfy・Flag',
    effect='承担所有伤/魔力/恐惧的旗帜魔法（南方联盟『光之御旗』）',
    source='第7-3章 第338话 城堡的顶端 (7373md-0120)', edition='web_original',
    aliases=['光之御旗','光之御旗Nosfy·Flag','光之御旗(NosfyFlag)','诺斯菲_光之御旗'])

add(id='light_variant_wall', caster='诺斯菲（光系）', type='普通魔法咏唱（光·壁）',
    chant='「就凭这种程度的魔法！──『Light・Variant Wall』！！」',
    jp='Light・Variant Wall', en='Light・Variant Wall',
    effect='光之变形壁魔法',
    source='第五章 第227话 《迷宫最后的战斗》 (md-0311)', edition='web_original',
    aliases=['Light_Variant_Wall'])

add(id='light_cuffs', caster='缇娅拉（光系）', type='普通魔法咏唱（光·束缚）',
    chant='「好的，那么首先是这个。──魔法『Light・Cuffs』。」',
    jp='Light・Cuffs', en='Light・Cuffs',
    effect='光之束缚手铐魔法',
    source='第7-1章 第268话 圣人式特训 (7171md-0025)', edition='web_original',
    aliases=['Light·Cuffs'])

add(id='divine_shield', caster='缇亚（神圣魔法）', type='普通魔法咏唱（神圣·盾）',
    chant='「──Di、『DivineShield』！！」',
    jp='DivineShield', en='Divine Shield',
    effect='神圣护盾魔法',
    source='第四章 第166话 再会帕林库洛 (md-0184)', edition='web_original',
    aliases=['DivineShield'])

add(id='divine_arrow_spear', caster='缇亚（神圣魔法）', type='普通魔法咏唱（神圣·箭矛）',
    chant='「『Divine Arrow・Spear（神圣之箭・矛）』⋯⋯」',
    jp='Divine Arrow・Spear', en='Divine Arrow・Spear',
    effect='神圣之箭/矛魔法',
    source='第7-2章 第285话 等级提升 (7272md-0030)', edition='web_original',
    aliases=['Divine Arrow・Spear(神圣之箭・矛)'])

add(id='sion', caster='（双人共鸣·神圣魔法）', type='共鸣魔法（神圣）',
    chant='「「——『万物皆为崭新旅途之祝福』『未来啊光辉啊游魂啊怜爱啊』」！——共鸣神圣魔法《SION》!」',
    jp='SION', en='SION',
    effect='共鸣神圣魔法（万物皆为崭新旅途之祝福）',
    source='第十章 第494话 西斯与迪普拉库拉 (md-0234)', edition='web_original',
    note='亦见「神圣魔法『Sion』」（第四章 第159话 交错 md-0148）',
    aliases=['神圣魔法Sion','SION'])

add(id='inviolable_field', caster='拉丝缇娅拉（大圣堂系）', type='普通魔法咏唱（神圣·结界）',
    chant='「──神圣魔法『Inviolable・Field』！」',
    jp='Inviolable・Field', en='Inviolable・Field',
    effect='不可侵犯的结界型神圣魔法（与库内 resonance_inviolable_ice 同系）',
    source='第四章 第四章-鍊狱三十，亲友至矣。孤高之剑，择卿为主 (md-0216)', edition='web_reconstructed+web_original',
    aliases=['神圣魔法『Inviolable・Field』'])

add(id='神圣魔法原形', caster='相川涡波（千年前）', type='魔法开发（神圣魔法原形）',
    chant='（原文未收录完整咏唱句；相关句：「结果到头来，我创造的并非『魔法』而是『咒术』啊」「将世界的黑暗转化为光明的魔法。那一定会是无比温柔、神圣的魔法」）',
    jp='神圣魔法（原形）', en='—',
    effect='千年前城堡魔法开发的雏形（后判明为咒术）',
    source='第四章 第160话 推测 (md-0155)', edition='web_original',
    aliases=['神圣魔法(原形)'])

add(id='代替', caster='诺斯菲·弗茨亚茨', type='代价咏唱（代替之光）',
    chant='「作为『代替』，将国民的『魔之毒』集于我身——作为『代替』，将病痛与扭曲集于我身——作为『代替』，将不幸与悲伤集于我身——作为『代替』，将憎恨与战意集于我身——作为『代替』，将所有的思念集于我身——！」',
    jp='代替（咏唱）', en='—',
    effect='以自身为『代替』承接国民病痛/魔之毒/思念的代价咏唱（与库内 relife_northfield 同源）',
    source='第7-2章 第312话 ■■六十，盈满■■ (7272md-0223)', edition='web_original',
    aliases=['代替'])

add(id='魅惑', caster='诺斯菲·弗茨亚茨（光之理的盗窃者）', type='魔法（精神干涉）',
    chant='（叙事：看到我身上散发出的光，对魔法的抵抗力较低的人就会被『魅惑』而醉心于我）',
    jp='魅惑', en='Charm',
    effect='光之理的盗窃者的常驻魅惑（精神干涉），抵抗力低者醉心于她',
    source='第7-2章 第298话 旧识 (7272md-0126)', edition='web_original',
    aliases=['魅惑'])

add(id='sleep_mist', caster='相川涡波', type='普通魔法咏唱（睡眠）',
    chant='「──魔法『Sleep Mist』。」',
    jp='Sleep Mist', en='Sleep Mist',
    effect='睡眠迷雾魔法',
    source='第7-1章 第271话 仪式开始 (7171md-0047)', edition='web_original',
    note='亦见「──『Sleep』。姑且先让领队像海莉大人一样先睡下吧」（第四章 第158话 木之理的盗窃者 md-0143）',
    aliases=['Sleep','SleepMist'])

add(id='光之理不老不死', caster='诺斯菲·弗茨亚茨（光之理的盗窃者）', type='魔法（不老不死·第一次尝试）',
    chant='（叙事：如果借助立足于我盗取的世界之理的魔法的话，我能够赋予唯一一人——赋予他『不老不死』的特性）',
    jp='光之理（不老不死魔法·第一次尝试）', en='—',
    effect='借盗取的世界之理赋予『不老不死』特性的第一次尝试（光之理）',
    source='第7-2章 第305话 圣女的始点 (7272md-0167)', edition='web_original',
    aliases=['光之理(不老不死魔法·第一次尝试)'])

add(id='诺斯菲光魔法系', caster='诺斯菲·弗茨亚茨（光之理的盗窃者）', type='普通魔法咏唱（光系·派生）',
    chant='（P8 派生名：光魔法_一再反转之光／光魔法_Shine_Arrow／诺斯菲第三节咏唱／诺斯菲_LightKnife／诺斯菲_LightStuff；原文咏唱散见，未收录完整咏唱句）',
    jp='诺斯菲光魔法派生（一再反转之光・Shine Arrow・第三节咏唱等）', en='—',
    effect='诺斯菲光魔法派生系列（一再反转之光/光之箭/第三节咏唱/光之刃/光之杖）',
    source='第7-2章 第298-312话 / 第7-3章 第334-338话', edition='web_original',
    aliases=['光魔法_一再反转之光','光魔法_Shine_Arrow','诺斯菲第三节咏唱','诺斯菲_LightKnife','诺斯菲_LightStuff'])

io.open(entries_file, 'w', encoding='utf-8').write(json.dumps(entries, ensure_ascii=False, indent=1))
print('entries total:', len(entries))
