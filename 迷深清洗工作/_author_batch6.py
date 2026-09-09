
# -*- coding: utf-8 -*-
import io, json
entries_file = '迷深清洗工作2/咏唱补录_entries.json'
entries = json.load(io.open(entries_file, encoding='utf-8'))
def add(**kw):
    entries.append(kw)

# ── 守护者开场白（补库 guardian_40/50/100）──
add(id='guardian_40_艾德', caster='艾德（木之理的盗窃者）· 第40层', type='守护者开场白',
    guardian_rank='第四十层',
    chant='「──必须要加以确认才行。如今的涡波大人究竟是『凡夫俗子』还是『英雄』，亦或是『王』吗，还是说是在这以上的什么呢?」',
    jp='第四十之试练『自狱』开场白', en='—',
    source='第四章 第158话 木之理的盗窃者 (md-0143~0144)', edition='web_original',
    effect='40层守护者艾德的开场白：确认涡波是凡夫俗子/英雄/王，开启第四十之试练',
    aliases=['guardian_40_艾德'])

add(id='guardian_40_缇缇', caster='缇缇（第40层·自狱篇）', type='守护者开场白',
    guardian_rank='第四十层',
    chant='「这里、这千年后的佩艾希亚正是四十层！因为这是由我创造出来的『支配之王』！当然也只有我才能将之打倒」',
    jp='第四十之试练『自狱』（缇缇）', en='—',
    source='第六章 第259话 自狱四十，二童归至。恆白物语，流溢于此。 (md-0231)', edition='web_original',
    effect='缇缇于40层自狱的开场白（支配之王由我创造，唯有我能打倒）',
    aliases=['guardian_40_缇缇'])

add(id='guardian_50_罗德', caster='罗德（缇缇·风之理的盗窃者）· 第50层', type='守护者开场白（牵制）',
    guardian_rank='第五十层',
    chant='「──『这・里』，这・除・孤・以・外・再・无・别・物・的・虚・无・之・空・便・是・五・十・层！接下来要开始的就是『第五十之试练』！」',
    jp='第五十之试练『天狱』开场白', en='—',
    source='第五章 第222话 第五十之试练『天狱』 (md-0230)', edition='web_original',
    effect='50层守护者罗德（缇缇）的开场白/牵制咏唱：宣告虚无之空便是第五十层',
    aliases=['guardian_50_罗德? 牵制'])

add(id='guardian_100_阳滝', caster='阳滝（水之理的盗窃者）· 第100层', type='守护者开场白',
    guardian_rank='第一百层',
    chant='「——『于生之起始寒冻，在死之静谧冰封』——」',
    jp='第百之试炼『冻狱』开场白', en='—',
    source='第八章 第411话 第百之试炼『冻狱』 (md-0331)', edition='web_original',
    effect='100层守护者阳滝的开场白（于生之起始寒冻，在死之静谧冰封）；接续真正魔法《冻结逝水流年的雪底坚冰（HeavenFall・Niflheim）》咏唱',
    note='完整咏唱：『于生之起始寒冻，在死之静谧冰封』→『我将孤身迎向终结』『甚至不曾与世界（你）相触』→魔法《HeavenFall・Niflheim》（md-0331 第411话）',
    aliases=['guardian_100_阳滝'])

# ── 木魔法系（艾德）──
add(id='wood_growth', caster='艾德（木之理的盗窃者）', type='普通魔法咏唱（木属性）',
    chant='「──魔法『Wood・Growth』」',
    jp='Wood・Growth', en='Wood・Growth',
    effect='木属性成长魔法（可碾碎国家级别的巨木）',
    source='第六章 第250话 静待归来 (md-0161)', edition='web_original',
    note='亦见「汝说决斗！？哈哈，还以为老夫会让汝争取到时间吗！用不了多久就会结束，汝这无礼之徒！——《wood growth》！」（第十章 第470话 开战 md-0069）',
    aliases=['Wood·Growth'])

add(id='trees_contact', caster='艾德（木之理的盗窃者）', type='普通魔法咏唱（木属性·联络）',
    chant='「──魔法──『Trees・Contact』」',
    jp='Trees・Contact', en='Trees・Contact',
    effect='树木联络魔法（树木接触传讯）',
    source='第六章 第250话 静待归来 (md-0162)', edition='web_original',
    aliases=['Trees·Contact'])

add(id='woodquake', caster='艾德（木之理的盗窃者）／涡波', type='普通魔法咏唱（木属性·地震）',
    chant='「来改变大圣堂的结构吧——魔法《Woodquake・创造（craft）》。」',
    jp='Wood Quake・创造', en='Wood Quake・Craft',
    effect='木地震创造魔法（改变建筑结构）',
    source='第九章 第446话 真正的研究者 (md-0233)', edition='web_original',
    note='亦见「——魔法《Wood Quake・创造》」（第九章 第414话 始笔 md-0002）',
    aliases=['WoodQuake创造','魔法_WoodQuake创造'])

add(id='吸魔圣木', caster='艾德（木之理的盗窃者）', type='魔法（植物·木）',
    chant='「德・丽菲特是被唤作『吸魔圣木』的植物！而这些是由作为『木之理的盗窃者』的鄙人精心改良过的品种！再加上『光之理的盗窃者』刻上的术式！就算是始祖也是无法用次元属性的魔力将之斩断的！来吧，就这样去将始祖吞噬！『吸魔圣木』！！」',
    jp='吸魔圣木', en='—',
    effect='吸取魔力的圣木（木之理盗窃者改良+光之理术式，无法被次元魔力斩断）',
    source='第六章 第255话 艾徳的战闘方式 (md-0194)', edition='web_original',
    aliases=['吸魔圣木'])

add(id='噬石常春藤', caster='艾德（木之理的盗窃者）', type='魔法（植物·木）',
    chant='「『噬石常春藤』！历史悠久而高贵的一族啊！以『木之理的盗窃者』之名在此请愿！将那曾经的剑圣夺下！！」',
    jp='噬石常春藤', en='—',
    effect='噬石的常春藤蔓（吊帘般垂挂无数藤蔓，缠夺剑圣诺文）',
    source='第六章 第255话 艾徳的战闘方式 (md-0196)', edition='web_original',
    aliases=['噬石常春藤'])

add(id='金刺毒花', caster='艾德（木之理的盗窃者）', type='魔法（植物·木）',
    chant='「接下来交给『金刺毒花』便足矣！大家可以去休息了！！」',
    jp='金刺毒花', en='—',
    effect='金刺毒花（毒花）魔法',
    source='第六章 第255话 艾徳的战闘方式 (md-0197)', edition='web_original',
    note='亦见「看这症状，是『金刺毒花』啊。既如此，那就多增加一些『金刺毒花』，至于其余的花种就可以减少一些了。」（md-0197）',
    aliases=['金刺毒花'])

add(id='wood_ymir', caster='艾德（木之理的盗窃者）', type='普通魔法咏唱（木属性·巨人）',
    chant='（P8 派生名：Wood・Ymir Kingdam；原文咏唱句未收录，叙事见「这第二株剔除了所有的缺点。这次不仅是区区一座城市，连一个国家都可以轻易碾碎」）',
    jp='Wood・Ymir Kingdam', en='Wood・Ymir Kingdam',
    effect='木属性巨人/王国级巨木魔法（Ymir）',
    source='第六章 第249-250话 作为宰相的自己/静待归来 (md-0160/md-0161)', edition='web_original',
    aliases=['Wood·Ymir Kingdam'])

# ── 地/水/雷/箭系 ──
add(id='earth', caster='诺文·阿雷亚斯（地之理的盗窃者）／涡波', type='普通魔法咏唱（地属性）',
    chant='「──地魔法『Earth』」',
    jp='Earth（地魔法）', en='Earth',
    effect='地属性魔法（Earth）',
    source='第五章 第139话 存钱攒经验 (md-0046)', edition='web_original',
    aliases=['地魔法_Earth'])

add(id='water_wire', caster='（水属性）', type='普通魔法咏唱（水系）',
    chant='「——《Ice Battering Ram》《Water Wire》《Flame Flamberge》《Rays·Wind》《Divine Arrow》《Earthquake》！！」',
    jp='Water Wire', en='Water Wire',
    effect='水线魔法（六属性连发之一）',
    source='第7-3章 第336话 阶梯 (7373md-0111)', edition='web_original',
    aliases=['WaterWire','魔法『WaterWire』'])

add(id='water_lightning', caster='相川涡波', type='普通魔法咏唱（水/雷基础）',
    chant='「——魔法《Water》、《Lightning》。」',
    jp='Water／Lightning', en='Water / Lightning',
    effect='水属性/雷属性基础魔法',
    source='第九章 第422话 异世界的舒适早晨 (md-0051)', edition='web_original',
    aliases=['magic_water_Water','magic_lightning_Lightning'])

add(id='magic_arrow', caster='星魔法系／涡波系', type='普通魔法咏唱（魔法箭）',
    chant='「——星魔法《Magic Arrow》。」',
    jp='Magic Arrow（魔法箭）', en='Magic Arrow',
    effect='魔法箭（Magic Arrow），可共鸣',
    source='第八章 第398话 『我们』 (md-0236)', edition='web_original',
    note='亦见「——共鸣魔法《magic arrow（・・・・・・・）》。」（第十章 第469话 青鸟 md-0063）、「——共鸣魔法《Magicarrow——」（第十章 第508话 第零之试炼『一切的开端』 md-0328）',
    aliases=['Magic Arrow','magic arrow'])

add(id='ice_speed_arrow', caster='相川涡波', type='普通魔法咏唱（冰结·速箭）',
    chant='（P8 派生名：ice-speed-arrow；库内 ice_arrow『冰之矢』为加速变体，名称不同未入库）',
    jp='冰速箭（Ice・Speed・Arrow）', en='Ice・Speed・Arrow',
    effect='冰之矢的加速变体（冰速箭）',
    source='第一章 第二章-迷宫联合国 (md-0037~0041)', edition='web_reconstructed',
    aliases=['ice-speed-arrow'])

add(id='divaplays_arrow', caster='拉丝缇娅拉', type='普通魔法咏唱（神之矢）',
    chant='「我们未尝不知自己的力量有所不足！不过，力量不足的人也有力量不足的人特有的战斗方式！『永久浮沉矣』！『于无垠之魂中延展之梦兮』『听此咏诵森罗万象之赞歌』！──『Divaplays・Arrow』！」',
    jp='Divaplays・Arrow', en='Divaplays・Arrow',
    effect='神之矢（Divaplays・Arrow），咏诵森罗万象之赞歌',
    source='第六章 第247话 魔人返还 (md-0136)', edition='web_original',
    aliases=['Divaplays·Arrow'])

# ── 契约/场/其他 ──
add(id='dealing', caster='相川涡波', type='咒术（契约）',
    chant='「——咒术『Dealing』。很好，这样一来『契约』就成立了。不过，想把『支配之王』从『这里』带走的话，必须要把握好相应的时机。不然的话，就算将你带走，很快也会被赛鲁多拉和艾德带人追上的。必须要营造一个他们两个都无暇顾及的时机才可以……」',
    jp='Dealing（契约）', en='Dealing',
    effect='契约咒术（Dealing），与缇缇缔结逃离『支配之王』的契约',
    source='第五章 第224话 童の长い人生（后编） (md-0254)', edition='web_original',
    aliases=['Dealing'])

add(id='invisible_field', caster='缇亚拉（使徒）系', type='普通魔法咏唱（隐形场·奉还阵）',
    chant='「——《Invisible・Field・奉还阵（return）》！！」',
    jp='Invisible・Field（奉还阵）', en='Invisible・Field・Return',
    effect='隐形场（奉还阵/return）魔法',
    source='第十章 第494话 西斯与迪普拉库拉 (md-0230)', edition='web_original',
    note='亦见「——！？——『Invisible·Field』！」（第7-3章 第323话 认识死亡 7373md-0024）',
    aliases=['InvisibleField','Invisible·Field'])

add(id='remove_field', caster='艾德／缇缇系', type='普通魔法咏唱（消除场）',
    chant='「──『Remove・Field』哦哦哦哦！！」',
    jp='Remove・Field', en='Remove・Field',
    effect='消除场魔法（与库内 resonance_remove『Remove』×2共鸣同族）',
    source='第六章 第260话 最终章「艾徳・■■■・缇缇」 (md-0238)', edition='web_original',
    note='亦见第159话 艾德三连『CarefulField』『StrengthField』『RemoveField』（第四章 第159话 交错 md-0149）',
    aliases=['RemoveField','Remove·Field'])

add(id='careful_strath_field', caster='艾德（木之理的盗窃者）', type='普通魔法咏唱（场·辅助）',
    chant='「来吧，正戏才刚刚开始，这才是『木之理的盗窃者』的真本领⋯⋯！──『CarefulField』『StrengthField』『RemoveField』！！」',
    jp='CarefulField／StrathField', en='CarefulField / StrathField',
    effect='广域回复/辅助场魔法（Careful/Strength/Remove三连）',
    source='第四章 第159话 交错 (md-0149)', edition='web_original',
    note='亦见「⋯⋯嗯、好。──『Strathfield』」（md-0152）',
    aliases=['CarefulField','Strathfield'])

add(id='shunposhion_feather', caster='（位移羽）', type='普通魔法咏唱（位移）',
    chant='「再见了『基督』，魔法『Shunposhion・Feather』！」',
    jp='Shunposhion・Feather', en='Shunposhion・Feather',
    effect='位移羽魔法（瞬移/移动）',
    source='第四章 第162话 《失踪》 (md-0168)', edition='web_original',
    aliases=['Shunposhion·Feather'])

add(id='infate', caster='（膨胀魔法）', type='普通魔法咏唱（神圣·膨胀）',
    chant='「——神圣魔法《Infate》。」',
    jp='Infate', en='Infate',
    effect='膨胀魔法（Infate）',
    source='第九章 第446话 真正的研究者 (md-0232)', edition='web_original',
    aliases=['Infate'])

add(id='spotlight', caster='相川涡波', type='普通魔法咏唱（聚光）',
    chant='「魔法《Spotlight》。」',
    jp='Spotlight', en='Spotlight',
    effect='聚光灯魔法（Spotlight）',
    source='第九章 第448话 真正的自己 (md-0254)', edition='web_original',
    aliases=['Spotlight'])

add(id='次元之冬歪冰世界', caster='相川涡波', type='普通魔法咏唱（次元之冬·变体）',
    chant='「──全魔法解放！『次元之冬·歪冰世界』！！」',
    jp='次元之冬・歪冰世界', en='Di・Winter・Niflheim',
    effect='次元之冬的歪冰世界变体（Di・Winter・Niflheim），全魔法解放级',
    source='第三章 第三章『一之月联合国综合骑士团舞闘大会』 (md-0208)', edition='web_reconstructed+web_original',
    aliases=['魔法『次元之冬·歪冰世界』'])

add(id='ice_battering_ram', caster='相川涡波（冰系）', type='普通魔法咏唱（冰结·攻城槌）',
    chant='「──等的就是这个，『冰Battering Ram（冰霜破城槌）』！！」',
    jp='Ice Battering Ram（冰霜破城槌）', en='Ice Battering Ram',
    effect='冰霜破城槌魔法（冰结攻城槌）',
    source='第四章 第138话 33层、34层 (md-0042)', edition='web_original',
    aliases=['冰BatteringRam','Ice Battering Ram','魔法_冰BatteringRam'])

add(id='ice_aegis', caster='拉丝缇娅拉／涡波（共鸣）', type='共鸣魔法（冰·守护）',
    chant='「共鸣魔法『冰・Aegis（守护冰）』」',
    jp='冰・Aegis（守护冰）', en='Ice・Aegis',
    effect='冰之守护共鸣魔法（守护冰）',
    source='第四章 第138话 33层、34层 (md-0041)', edition='web_original',
    note='亦见「共鸣魔法『冰・Aegis』」（第四章 第144话 忐忑不安的时间 md-0070）',
    aliases=['冰Aegis','共鸣魔法_冰Aegis','共鸣魔法_冰Aegis守护冰'])

add(id='冰火拟似共鸣爆裂魔法', caster='涡波／拉丝缇娅拉（拟似共鸣）', type='共鸣魔法（拟似）',
    chant='（叙事：那是我们昨天商讨研究出的新的魔法组合。是为了不管帕林库洛做什么都能让我们战胜他而考虑出的拟似共鸣魔法）',
    jp='冰火拟似共鸣爆裂魔法', en='—',
    effect='冰与火拟似共鸣的爆裂魔法（为对帕林库洛而设计的组合）',
    source='第四章 第173话 渴求着彼此的两人 (md-0222)', edition='web_original',
    aliases=['冰火拟似共鸣爆裂魔法'])

add(id='涡波复合咒术咏唱', caster='相川涡波（复合咒术）', type='咏唱（誓句·复合）',
    chant='「──『于此起誓，种种罪过，吾当清偿』『纵此世之终结至来，此誓亦无毁弃之日』──」',
    jp='涡波复合咒术咏唱（誓句）', en='—',
    effect='涡波复合咒术咏唱（起誓清偿罪过之誓句）',
    source='第五章 第216话 誓言 (md-0197)', edition='web_original',
    aliases=['涡波_复合咒术咏唱'])

add(id='light_fullcure_remove', caster='诺斯菲·弗茨亚茨（光之理的盗窃者）', type='普通魔法咏唱（光/治愈/消除三连）',
    chant='「接下来是他们……——『Light』『Full Cure』『Remove』。」',
    jp='Light／Full Cure／Remove（三连）', en='Light / Full Cure / Remove',
    effect='光/完全治愈/消除的三连咏唱',
    source='第7-3章 第323话 认识死亡 (7373md-0020)', edition='web_original',
    aliases=['Light/Full Cure/Remove'])

io.open(entries_file, 'w', encoding='utf-8').write(json.dumps(entries, ensure_ascii=False, indent=1))
print('entries total:', len(entries))
