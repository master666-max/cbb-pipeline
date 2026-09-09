
# -*- coding: utf-8 -*-
# Author batch 1: 次元/冬/BlackShift/维度系 entries -> _entries.json
import io, json, os

entries_file = '迷深清洗工作2/咏唱补录_entries.json'
entries = []
if os.path.exists(entries_file):
    entries = json.load(io.open(entries_file, encoding='utf-8'))

def add(**kw):
    entries.append(kw)

# ── 次元/冬系 ──
add(id='di_overwinter', caster='相川涡波', type='普通魔法咏唱（次元/冷气系）',
    chant='「这招才是正戏——魔法《过密次元的真冬（Di・OverWinter）》。」',
    jp='过密次元的真冬', en='Di・OverWinter',
    effect='将『次元之冬』压缩至精密程度的广域冷气压制魔法，可妨碍敌人行动',
    source='第九章 第447话 梦的奴隶 (md-0240)', edition='web_original',
    note='别名：魔法_过密次元的真冬／DiOverWinter；亦见「──魔法『过密次元的真冬』！」（第三章 第四章-公会里简单的工作 md-0049）、「──魔法『过密次元的真冬』！」（第九章 第443话 真正的始笔 md-0216）',
    aliases=['过密次元的真冬','魔法_过密次元的真冬','DiOverWinter'])

add(id='di_overwinter_mirror', caster='相川涡波', type='普通魔法咏唱（次元/冷气系·镜化）',
    chant='「解除不了的『异常状态』先搁着，『最深处的誓约者』！超出负荷的部分就用『并列思考』割下来！然后给大脑搞个新的人格，全都丢给他承受！根据需求，把相信的事物连同心灵替换掉也无妨！——现在的我有数不尽的对策！如果还是不够，就用侵蚀『理』的魔法强行扭曲它！先反转缇达的『不信』，再使之『静止』！用二重之理掩埋黑暗吧！！——《过密次元的真冬・镜化》！！」',
    jp='过密次元的真冬・镜化', en='Di・OverWinter・Mirror',
    effect='过密次元的真冬之镜化形态，冻结黑泥并为其刷上紫色；复合反转『不信』与『静止』的二重之理',
    source='第十章 第500话 第百二十之试炼『绊』 (md-0273)', edition='web_original',
    note='对缇达『不信』之理的侵蚀性镜化咏唱',
    aliases=['过密次元的真冬・镜化'])

add(id='di_reverent_night', caster='相川涡波／莉帕', type='普通魔法咏唱（次元/黑夜系）',
    chant='「——魔法《深渊次元的真夜（Di・ReverentNight）》。」',
    jp='深渊次元的真夜', en='Di・ReverentNight',
    effect='以黑夜统治世界的广域暗幕魔法，夺走视野与认知（类似过密次元的真冬的暗属性对应）',
    source='第九章 第454话 亡灵的梦、梦的亡灵 (md-0300)', edition='web_original',
    note='亦见「——『深渊次元的真夜』！！」（第7-2章 第310话 第一回合 7272md-0210）、「──『深渊次元的真夜』！」（第四章 第146话 剧 md-0080，莉帕使用）',
    aliases=['深渊次元的真夜','深渊次元的真夜(Di·ReverentNight)'])

add(id='the_night', caster='莉帕', type='普通魔法咏唱（次元/黑夜系）',
    chant='「──『次元之夜（The·Night）』。」',
    jp='次元之夜', en='The・Night',
    effect='『次元之冬』的亚种，用黑夜统治世界；范围可较涡波使用时放大数倍且无时间限制',
    source='第三章 第一章-番外战 (md-0170)', edition='web_reconstructed+web_original',
    aliases=['次元之夜'])

add(id='di_snow', caster='相川涡波', type='普通魔法咏唱（冰结/组合系）',
    chant='魔法『次元雪（Di・Snow）』',
    jp='次元雪', en='Di・Snow',
    effect='『泡沫』与『冻结』的组合技；因未能习得冰结魔法『Little Snow』而自行开发的替代品',
    source='第九章 第434话 和科学毫无差异 (md-0148)', edition='web_original',
    note='命名段：「这便是『泡沫』和『冻结』的组合技。要命个名的话，那就叫魔法『次元雪（Di·Sonw）』好了。」（第四章 第四章-队伍 md-0072）',
    aliases=['次元雪','次元雪(Di·Sonw)','次元雪(Di・Snow)'])

add(id='di_winter_frost', caster='相川涡波', type='普通魔法咏唱（冰结系）',
    chant='「──魔法『次元之冬·终霜（Di·Winter·Frost）』。」',
    jp='次元之冬·终霜', en='Di・Winter・Frost',
    effect='次元之冬系列的终霜变体，冻结收束',
    source='第三章 第四章-公会里简单的工作 (md-0041)', edition='web_reconstructed+web_original',
    note='亦见「──魔法《次元之冬·终霜》！！」（第三章 第二章『一之月联合国综合骑士团舞闘大会』 md-0131）',
    aliases=['次元之冬·终霜','魔法_次元之冬终霜'])

add(id='di_winter_snowwind', caster='相川涡波（共鸣）', type='共鸣魔法',
    chant='「冬之风啊，将黑暗冻结！！共鸣魔法『次元之冬・朔风』！！」',
    jp='次元之冬・朔风', en='Di・Winter・SnowWind',
    effect='将黑暗冻结的共鸣型次元之冬，席卷帕林库洛全身',
    source='第四章 第179话 自《牢狱》中超脱 (md-0262)', edition='web_original',
    aliases=['次元之冬朔风'])

add(id='wintry_dimension', caster='相川阳滝（使用哥哥涡波的魔法）', type='真正魔法级咏唱（冰封世界）',
    chant='「请你好好休息吧……『冬之世界直至寻获无以掠夺之物，迷失之人终将发觉已然无以所失』——魔法《冬之异世界（wintry・dimension）》」',
    jp='冬之异世界', en='Wintry・Dimension',
    effect='将整个世界（异世界）冰封包裹的终焉级魔法；阳滝用以冰封大陆/异世界，并令涡波『遗忘』',
    source='第八章 第396话 冬 (md-0222)', edition='web_original',
    note='涡波所创、阳滝发扬；别名 冬之异世界Wintory／wintry_dimension／WintryDimension／冬季之异世界Wintory·dimension／魔法『冬之异世界(Wintry·Dimension)』；亦见「──魔法『冬之异世界（Wintry·Dimension）』！」（第三章 舞闘大会决赛 md-0202）、「你已经可以不用战斗了……魔法《冬之异世界（wintry・dimension）》。」（第八章 第396话 冬 md-0222）',
    aliases=['冬之异世界','冬之异世界Wintory','wintry_dimension','WintryDimension','冬季之异世界Wintory·dimension','魔法『冬之异世界(Wintry·Dimension)』'])

add(id='wintry_quartetto', caster='相川涡波／拉丝缇娅拉／斯诺／玛莉亚（四重奏）', type='共鸣魔法（四人）',
    chant='『冬之异世界・四重奏（Winter 维度 Quartetto）』',
    jp='冬之异世界・四重奏', en='Winter 维度 Quartetto',
    effect='四人共鸣的冬之异世界升华形态，将水域化为冰沙、妨碍敌人行动',
    source='第四章 第144话 忐忑不安的时间 (md-0074)', edition='web_original',
    aliases=['冬之异世界四重奏'])

add(id='niflheimr_freeze', caster='相川阳滝', type='普通魔法咏唱（水/冻结系）',
    chant='「──『冻结・Niflheimr』」',
    jp='冻结・Niflheimr', en='Freeze・Niflheimr',
    effect='冻结/停止系冰结魔法，用以束缚对手令其『停止』',
    source='第六章 第260话 最终章「艾徳・■■■・缇缇」 (md-0235)', edition='web_original',
    note='亦见「停止。──『冻结・Niflheimr』」（第六章 第259话 md-0225）',
    aliases=['冻结·Niflheimr'])

# ── 维度・决战演算系 ──
add(id='di_gradient_battle', caster='相川涡波', type='普通魔法咏唱（次元演算·早期变体）',
    chant='「──魔法『维度・决战演算』！」',
    jp='维度・决战演算', en='Dimension・Battle',
    effect='次元决战演算系列的早期变体，演算/预判战局',
    source='第一章 第一章-异世界迷宫 (md-0006)', edition='web_reconstructed',
    note='别名：维度·决战演算／维度决战演算／涡波_维度决战演算／dimension-battle；亦见「──魔法『维度・决战演算』、魔法『泡沫』。」（第一章 md-0055）、「──魔法『维度・决战演算』、魔法『次元之冬』！！」（第五章 md-0214）',
    aliases=['维度・决战演算','维度·决战演算','维度决战演算','涡波_维度决战演算','dimension-battle'])

add(id='di_difference', caster='相川涡波', type='普通魔法咏唱（次元演算·变体）',
    chant='「──『维度・曲战演算（Difference）』！！」',
    jp='维度・曲战演算', en='Dimension・Difference',
    effect='维度决战演算系列的曲战变体（Difference），弯折演算战局',
    source='第五章 第204话 乱战 (md-0113)', edition='web_original',
    note='亦见「──『维度・曲战演算』！！」（第五章 第217话 md-0203、第五章 第222话 第五十之试练『天狱』 md-0230）',
    aliases=['维度_曲战演算'])

add(id='di_counting', caster='相川涡波', type='普通魔法咏唱（次元演算·变体）',
    chant='「──『维度・千算相杀（Counting）』」',
    jp='维度・千算相杀', en='Dimension・Counting',
    effect='以千万次演算相杀抵消对手魔法的次元演算变体',
    source='第六章 第236话 新魔法的力量 (md-0053)', edition='web_original',
    note='亦见「不可以用魔法！──魔法『维度・千算相杀』！！」（第7-1章 第276话 是真是假 7171md-0084）',
    aliases=['维度・千算相杀(Counting)','维度·千算相杀'])

add(id='dimension_sousa', caster='相川涡波', type='普通魔法咏唱（索敌/基础）',
    chant='「──次元魔术、《维度》！」',
    jp='维度', en='Dimension',
    effect='展开次元魔术《维度》索敌/感知周边（与库内 dimension_origin 同源，早期展开形）',
    source='第一章 第一章-异世界迷宫 (md-0012)', edition='web_reconstructed',
    aliases=['维度'])

# ── BlackShift系 ──
add(id='blackshift', caster='相川涡波', type='普通魔法咏唱（次元·无化）',
    chant='「——次元魔法《BlackShift》。」',
    jp='BlackShift（黑移）', en='BlackShift',
    effect='将指定对象『化为无物』的次元魔法；并非万能，须精密控制对象',
    source='第九章 第427话 欢乐的异世界 (md-0096)', edition='web_original',
    note='别名：blackshift／次元魔法《BlackShift》／魔法_BlackShift；亦见「——次元魔法《BlackShift》。」（第九章 第453话 灵梦 md-0290）、「——次元魔法《BlackShift》！！」（第九章 第460话 マ莉亚・迪斯特拉斯的终点 md-0343）',
    aliases=['BlackShift','blackshift','次元魔法《BlackShift》','魔法_BlackShift'])

add(id='blackshift_overwrite', caster='相川涡波', type='真正魔法级咏唱（次元·无化）',
    chant='「啊啊。交过手的我是明白的……真正的『魔法』都是无法回避的终极魔法。然而，那样的真正『魔法』也只剩这个了……只要跨越这个……！就不会再出现了！抹除这最后的垂死挣扎吧！——《BlackShift・Overwrite》！！」',
    jp='BlackShift・Overwrite', en='BlackShift・Overwrite',
    effect='BlackShift的覆盖形态，将『化为无物』的对象扩大至时间/世界级',
    source='第十章 第500话 第百二十之试炼『绊』 (md-0273)', edition='web_original',
    note='亦见「——《BlackShift・OverWrite》！」（第十章 第505话 真正的『咏唱』 md-0305/md-0308）',
    aliases=['BlackShift_Overwrite','BlackShift・Overwrite'])

add(id='blackshift_overwrite_life', caster='赛尔德拉（无之理的盗窃者）', type='真正魔法级咏唱（次元·无化·时间）',
    chant='「……没用的，赛尔德拉。这样一来所有的战斗就都会成为『无物』。不、是『我会使其化为无物』『我会使其化为无物』『我绝对会使一切都化为无物』——《blackshift・over write・life》！！」',
    jp='blackshift・over write・life', en='BlackShift・OverWrite・Life',
    effect='以时间为对象的BlackShift，将一切战斗『化为无物』的反涡波魔法',
    source='第十章 第483话 第八十之试炼『边狱』 (md-0166)', edition='web_original',
    aliases=['blackshift・over write・life'])

# ── 次元基础/其他 ──
add(id='new_reading', caster='相川涡波', type='普通魔法咏唱（翻译）',
    chant='「——魔法《New・Reading》。」',
    jp='New・Reading（新・阅览）', en='New・Reading',
    effect='翻译异界史书/语言的魔法，与《Reading・Shift》共用',
    source='第九章 第418话 西暦3032年 (md-0026)', edition='web_original',
    aliases=['New·Reading'])

add(id='replace_connection', caster='相川阳滝／赛尔德拉', type='普通魔法咏唱（连接改写）',
    chant='「——《replace・connection》。这个魔法明显只能在这个『世界』使用。那我只需要把战场换到其他『世界』就可以了。」',
    jp='Replace・Connection（替换・连接）', en='Replace・Connection',
    effect='改写《Connection》联结对象的魔法；用于连接原世界/异世界，将战场切换到其他世界',
    source='第八章 第404话 感想战 (md-0279)', edition='web_original',
    aliases=['Replace·Connection','Replace_connection'])

add(id='shift', caster='相川涡波', type='普通魔法咏唱（次元转移）',
    chant='「──次元魔术『Shift』」',
    jp='Shift（移位）', en='Shift',
    effect='次元魔术移位，用于空间转移/体感时间延长',
    source='第六章 第242话 这就是斯诺 (md-0094)', edition='web_original',
    aliases=['次元魔术『Shift』'])

add(id='foam', caster='相川涡波', type='普通魔法咏唱（次元/泡沫系）',
    chant='「──魔法『泡沫』。」',
    jp='泡沫', en='Foam',
    effect='次元魔术基础系（泡沫）；与『冻结』组合成『次元雪』，与『连接』并列为早期仅有的两个次元魔术',
    source='第一章 第一章-异世界迷宫 (md-0008)', edition='web_reconstructed',
    note='亦见「容我稍微使用下魔法吧。──魔法『泡沫』。」（第一章 第一章-劳拉维亚国的全新物语 md-0008）',
    aliases=['泡沫','Foam(次元魔术·泡沫)'])

add(id='jigen_eishou_tsumi', caster='相川涡波', type='咏唱句（次元咏唱）',
    chant='「——『罪孽的命运将逆游而上』『直至回溯到尽头之虚影』——」',
    jp='次元咏唱（罪孽的命运／直至回朔到尽头）', en='—',
    effect='『魔法涡波』构筑中的核心次元咏唱句',
    source='第九章 第452话 梦 (md-0283)', edition='web_original',
    note='P8 拆分为两条：次元咏唱罪孽的命运／次元咏唱直至回朔到尽头，实为同一咏唱之上下句',
    aliases=['次元咏唱罪孽的命运','次元咏唱直至回朔到尽头'])

add(id='magic_namida_术式', caster='缇亚拉（术式主谋）／相川涡波', type='咒术/术式（将涡波魔法化）',
    chant='（『魔法涡波』为将『相川涡波』作为魔法构筑的千年咒术/术式，原文未收录单一咏唱正句）',
    jp='魔法涡波（术式）', en='Magic・Namida',
    effect='以『相川涡波』为魔法本体的千年计划，欲令其超越所有『理』成为真正的『魔法』',
    source='第九章 第461话 于是、前往100层 (md-0353)', edition='web_original',
    note='中心与根基为次元魔法《Dimension》；仪式若圆满完成即可让『魔法涡波』令众人更加『幸福』',
    aliases=['魔法涡波'])

io.open(entries_file, 'w', encoding='utf-8').write(json.dumps(entries, ensure_ascii=False, indent=1))
print('entries total:', len(entries))
