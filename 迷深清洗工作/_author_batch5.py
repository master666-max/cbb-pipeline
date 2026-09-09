
# -*- coding: utf-8 -*-
import io, json
entries_file = '迷深清洗工作2/咏唱补录_entries.json'
entries = json.load(io.open(entries_file, encoding='utf-8'))
def add(**kw):
    entries.append(kw)

# ── Default/行路渐歧系 ──
add(id='default', caster='相川涡波', type='普通魔法咏唱（空间·行路渐歧）',
    chant='「——De、《default》！」',
    jp='Default（行路渐歧）', en='Default',
    effect='扭曲距离的空间魔法（无法被闪避），令自身与对象距离趋近无限；与Torsion/DistanceMute并称三种最高位魔法',
    source='第九章 第423话 异世界的回忆 (md-0060)', edition='web_original',
    note='P8 别名：涡波_Default／Default_行路渐歧／Default(行路渐歧)／magic_default／default／行路渐歧；亦见「──魔法『Default（行路渐歧）』」（第7-2章 第285话 等级提升 7272md-0027）',
    aliases=['Default','涡波_Default','Default_行路渐歧','Default(行路渐歧)','magic_default','default','行路渐歧'])

add(id='default_armorbreak', caster='相川涡波', type='普通魔法咏唱（空间·武装破坏）',
    chant='「——魔法《Default・武装破坏（Armor Break）》」',
    jp='Default・武装破坏', en='Default・Armor Break',
    effect='Default系武装破坏（脱衣/解除武装）',
    source='第九章 第423话 异世界的回忆 (md-0063)', edition='web_original',
    aliases=['Default武装破坏','magic_default_armorbreak'])

add(id='default_field', caster='相川涡波', type='普通魔法咏唱（空间·领域）',
    chant='「——魔法《Default・Field》。」',
    jp='Default・Field', en='Default・Field',
    effect='Default的空间领域扩张形态',
    source='第九章 第446话 真正的研究者 (md-0237)', edition='web_original',
    aliases=['DefaultField'])

# ── Impulse系 ──
add(id='impulse', caster='相川涡波／侯普斯·约克尔系', type='普通魔法咏唱（无属性·冲击）',
    chant='「谢谢！！——《impulse》！！」',
    jp='Impulse', en='Impulse',
    effect='无属性冲击魔法，持续震动干扰对手行动',
    source='第十章 第467话 兽人 (md-0051)', edition='web_original',
    aliases=['Impulse','Impulse(无属性魔法)','impulse'])

add(id='impulse_break', caster='（众人共鸣）', type='普通魔法咏唱（无属性·冲击破裂）',
    chant='「——魔法《impulsebreak》」',
    jp='Impulse Break', en='Impulse Break',
    effect='Impulse的破裂形态，多重连锁（impulsebreak×N）；龙型派生《dragon・impulsebreak》使烟火炸裂扩大',
    source='第十章 第469话 青鸟 (md-0065)', edition='web_original',
    aliases=['Impulse_Break','Impulse Break','impulsebreak','dragon・impulsebreak'])

# ── 世界奉还阵/LevelUp系 ──
add(id='世界奉还阵', caster='希丝（使徒）／帕林库洛', type='咒术咏唱（终焉级）',
    chant='「——『苍穹既失，必由吾夺还』！！『苍穹既失，必由吾复苏』『除天地之戾气，还世界以晴天』！！ ——咒术《世界奉还阵》！！」',
    jp='世界奉还阵', en='World・Return',
    effect='将世界之毒奉还/夺还的终焉级咒术（例外对象可转变为『异邦人』）',
    source='第八章 第386话 新暦0011年、新暦0012年、新暦0013年 (md-0159)', edition='web_original',
    note='亦见「咒术构筑完毕──『世界奉还阵』启动」（第四章 第174话 md-0230）；与帕林库洛『世界奉还阵』之战为千年前传说',
    aliases=['世界奉还阵'])

add(id='level_up', caster='相川涡波（千年前发明）／赫尔米娜系', type='咒术咏唱（强化）',
    chant='「『我立誓偿还一切罪过』——咒术《Level Up》。」',
    jp='Level Up', en='Level Up',
    effect='提升等级/魂之上限的咒术；『魔力变换（Level up）』为其术式方向',
    source='第九章 第448话 真正的自己 (md-0252)', edition='web_original',
    note='亦见「『汝者，刮目自省而可也！识生命其辉华——』『咒术 Level Up。』」（第八章 第352话 始祖 md-0026）、「『罪孽的命运将逆游而上』『直至回朔到尽头之虚影』『我立誓偿还一切罪过』——咒术《Level Up》」（md-0252）',
    aliases=['LevelUp','Levelup','咒术LevelUp','Lave Up'])

add(id='魔力变换', caster='相川涡波', type='神圣魔法（魔力变换/LevelUP方向）',
    chant='「神圣魔法『魔力变换（Level UP）』！！」',
    jp='魔力变换（Level UP）', en='Mana・Transform',
    effect='将魔力变换/升级的术式（Level Up方向），与『魔之毒』结合强化身体机能；可摘除魂（Level）的上限',
    source='第九章 第459话 第百十之试练『恋』 (md-0335)', edition='web_original',
    aliases=['LevelUP_魔力变换','魔力变换_LevelUP','魔力变换'])

# ── 慕影死神/咏唱句系 ──
add(id='慕影死神', caster='相川涡波（仿缇亚拉制作的魔法生命体）', type='魔法/咒（影）',
    chant='「──『我正是那』，『慕影死神（Grim·R·Reaper）』。」',
    jp='慕影死神', en='Grim・R・Reaper',
    effect='模仿缇亚拉制作出的魔法生命体/诅咒（影慕死神），与死神同依特殊规则行动',
    source='第三章 第四章-公会里简单的工作 (md-0053)', edition='web_reconstructed+web_original',
    note='亦见「──魔法『维度・黑泡沫』，魔法『泡沫・深渊』！！」（第一章 第一章-于是，开始 md-0109）、《影慕死神(Grim・R・Reaper)》为始祖涡波孤独时催生的代用品（第八章 第401话 始祖 md-0258）',
    aliases=['慕影死神','curse_慕影死神','影慕死神'])

add(id='我为逐幻之幻', caster='拉古涅·卡伊库欧拉（星之理的盗窃者）', type='咏唱（两节魔法·上句）',
    chant='「——『我为逐幻之幻』——」',
    jp='我为逐幻之幻', en='—',
    effect='拉古涅两节咏唱之上句（我为追逐幻影的幻影）',
    source='第7-3章 第331话 究竟是于何日踏上歧路 (7373md-0078)', edition='web_original',
    note='与『甚而无法存在于世界（你）之中』并称两节咏唱（拉古涅启程夺顶/反转取回湖凪之名）',
    aliases=['我为逐幻之幻','逐幻之幻'])

add(id='甚而无法存在于世界之中', caster='拉古涅·卡伊库欧拉（星之理的盗窃者）', type='咏唱（两节魔法·下句）',
    chant='「——『甚而无法存在于世界（你）之中』——」',
    jp='甚而无法存在于世界之中', en='—',
    effect='拉古涅两节咏唱之下句（甚而无法存在于世界（你）之中）',
    source='第7-3章 第331话 究竟是于何日踏上歧路 (7373md-0078)', edition='web_original',
    aliases=['甚而无法存在于世界之中'])

add(id='我于此弃旗', caster='诺斯菲／阳滝系', type='咏唱（弃旗）',
    chant='「——『我于此弃旗』——」',
    jp='我于此弃旗', en='—',
    effect='弃旗咏唱（与世界/战斗诀别）',
    source='第7-3章 第326话 再次 (7373md-0039)', edition='web_original',
    aliases=['我于此弃旗'])

add(id='世界(你)的祝福已然无关紧要', caster='诺斯菲·弗茨亚茨（光之理的盗窃者）', type='咏唱（祝福/无祝福）',
    chant='「『世界（你）的祝福已然无关紧要』『我才是未得降诞生命的祝福之光』——魔法（・・）《代而亡逝之光（NoLife・Nosfy）》」',
    jp='世界（你）的祝福已然无关紧要', en='NoLife・Nosfy',
    effect='「世界（你）的祝福已然无关紧要」的祝福/诅咒咏唱，化为代而亡逝之光',
    source='第十章 第501话 『真正的丝线』 (md-0281)', edition='web_original',
    note='亦见「——『世界（你）的祝福已然无关紧要』——」（第7-3章 第326话 再次 7373md-0045）',
    aliases=['世界(你)的祝福已然无关紧要'])

add(id='祝福启新程', caster='相川涡波', type='咏唱（原创·命名咏唱）',
    chant='「——『缥缈而失矣』『无论过去的时间、不论怀念的故乡、毋论苦楚的悲伤』，『祝福启新程』——」',
    jp='祝福启新程', en='—',
    effect='涡波将其创造的『咏唱』定名的第一段原创咏唱（缥缈而失矣/祝福启新程）',
    source='第八章 第352话 始祖 (md-0023)', edition='web_original',
    aliases=['祝福启新程','涡波原创咏唱_祝福启新程'])

add(id='想起收束', caster='迷宫（系统）', type='技能/机制（Drop）',
    chant='（叙事：迷宫将过去的道具/魔石『想起收束（Drop）』——回收机制）',
    jp='想起收束', en='Drop',
    effect='迷宫将逝去者/道具的魔力与魔石回收的机制（Drop）',
    source='第六章 第181话 物语迎来终末之后的结局 (md-0272)', edition='web_original',
    aliases=['想起收束'])

add(id='加速_孤乃加速之魂', caster='缇缇', type='咏唱（加速）',
    chant='「『孤乃加速之魂』」',
    jp='加速（孤乃加速之魂）', en='—',
    effect='缇缇以咏唱加速磨损自我、加速消逝的咏唱',
    source='第五章 第224话 童の长い人生（后编） (md-0266~0271)', edition='web_original',
    aliases=['加速_孤乃加速之魂'])

add(id='心异', caster='缇达（暗之理的盗窃者）', type='普通魔法咏唱（暗·心异系）',
    chant='「——『心异·无貌（Variable·Faceless）』。」',
    jp='心异・无貌／心异・暗洗', en='Variable・Faceless / Variable・Curse',
    effect='缇达暗魔法心异系（无貌/暗洗），可变貌/清洗',
    source='第八章 第365话 英雄的约定 (md-0064)', edition='web_original',
    note='亦见「『心异·暗洗（Variable·Curse）』」确认语感（md-0064）；缇达暗魔法《心异・无貌／Variable・Faceles》织出黑色外套（第八章 第401话 始祖 md-0255）',
    aliases=['心异·暗洗(Variable·Curse)','Variable(心异)','心异·无貌'])

add(id='不罚的大英雄', caster='缇娅拉系（拉丝缇娅拉防御咏唱）', type='暗魔法（最终防卫术式）',
    chant='「【最终防卫术式：暗魔法『不罚的大英雄』发动了】」',
    jp='不罚的大英雄', en='—',
    effect='缇娅拉系最终防卫术式（暗魔法），守护不罚的大英雄（涡波）',
    source='第四章 第四章-拉丝缇娅拉・弗茨亚茨的战闘 (md-0147)', edition='web_original',
    aliases=['不罚的大英雄'])

add(id='咏唱幼龙贪念日久难消', caster='相川涡波', type='咏唱（幼龙·赦罪）',
    chant='「『幼龙贪念　日久难消』……『偿罪之欲延烧之时，凶邪之念断灭之刻』……经年累月，终于澈悟。『所谓人者，无人有权予其宽恕，赦罪之人仅为自己』……『逝者之声由魂震奏』，若此声不灭，刀山火海，欣然赴往——」',
    jp='咏唱『幼龙贪念日久难消』', en='—',
    effect='涡波的幼龙咏唱（偿罪之欲/赦罪之人仅为自己）',
    source='第十章 第505话 真正的『咏唱』 (md-0308)', edition='web_original',
    note='亦见 md-0172（第十章 第484话 诅咒的心臟）',
    aliases=['咏唱『幼龙贪念日久难消』'])

add(id='咏唱无名无姓皆尽忘舍', caster='涡波／赛尔德拉系', type='咏唱（无名）',
    chant='「——『无名无姓』『皆尽忘舍』『故而为无』——」',
    jp='咏唱『无名无姓、皆尽忘舍、故而为无』', en='—',
    effect='「无名无姓/皆尽忘舍/故而为无」的无之咏唱',
    source='第十章 第485话 那些骑士名为 (md-0175)', edition='web_original',
    aliases=['咏唱『无名无姓、皆尽忘舍、故而为无』'])

# ── 鲜血魔法系 ──
add(id='blood', caster='相川涡波', type='普通魔法咏唱（血属性基础）',
    chant='「我有些想要的东西呐……所以我就收下了——魔法《Blood》。」',
    jp='Blood（血）', en='Blood',
    effect='血属性基础魔法；经涡波海量魔力增幅可把血海劈成两半',
    source='第九章 第436话 格连 (md-0162)', edition='web_original',
    aliases=['Blood','incantation_blood','incantation_Blood(鲜血魔法)'])

add(id='blood_arrow', caster='法夫纳（血之理的盗窃者）', type='普通魔法咏唱（鲜血魔法）',
    chant='「──鲜血魔法『Blood・GrowthField』『BloodHeal』『Blood Arrow』。」',
    jp='Blood Arrow', en='Blood Arrow',
    effect='鲜血魔法组合（血之成长领域/血之治疗/血之箭）',
    source='第7-2章 第294话 理の力 (7272md-0095)', edition='web_original',
    note='亦见「——《Blood Arrow》！」（第八章 第398话 『我们』 md-0236）',
    aliases=['BloodArrow(血之力咒术)','Blood_Arrow','Blood Arrow'])

add(id='blood_warez', caster='（血魔法）', type='普通魔法咏唱（鲜血魔法）',
    chant='「……哈哈，对我也是、吗。你还真是擅长这种事啊。……我知道了。如果这个回答就是你的愿望的话，那我就协助你吧。倒不如说，反正身体也会擅自动起来啊。――《Blood·Warez》。」',
    jp='Blood・Warez', en='Blood・Warez',
    effect='血魔法（Ware/程序型）',
    source='第7-3章 第321话 暗杀的失格 (7373md-0009)', edition='web_original',
    aliases=['Blood·Warez'])

add(id='血脉稀释', caster='赛尔德拉（无之理的盗窃者）', type='术式（基因/血脉）',
    chant='「正确来说，是把异世界的放射线治疗技术编入我在学习弑神的过程中习得的『屠龙魔法』，也就是我独自改良的『基因恢复（・・）魔法』……地上不是有在传播轻量版的《血脉稀释》（Changelock）吗？这个魔法就是那个的源头。」',
    jp='血脉稀释', en='Changelock',
    effect='基因恢复/血脉稀释术式（Changelock），地上流传轻量版',
    source='第十章 第472话 骗小孩的 (md-0085)', edition='web_original',
    aliases=['血脉稀释(Changelock)'])

add(id='bloodline_lockfield', caster='（民众共鸣·对龙人封印阵）', type='共鸣魔法（封印阵）',
    chant='「「「「「我、『我们那端坐于天顶的神啊』『恳请您将神圣的魔法赐予我等』――《bloodline・lockfield》。」」」」」',
    jp='bloodline・lockfield', en='Bloodline・Lockfield',
    effect='简易世界奉还阵的改良版——对龙人封印阵（民众齐声歌颂神明）',
    source='第十章 第468话 迪普拉库拉 (md-0059)', edition='web_original',
    aliases=['bloodline・lockfield'])

add(id='bloodland_transform', caster='格连·沃克', type='代价咏唱（血之理代行者变身）',
    chant='「——『盗窃了血之理的罪人将迎来第二度的死亡』『只因我乃背负一次死亡亦无法偿清罪孽的大罪人』——」「『呜呼，我正是那犯下死罪者』『血之理的盗窃者』——」',
    jp='bloodland transform（血之理代行者咏唱）', en='—',
    effect='格连继承『赫尔米娜的心脏』成为血之理盗窃者代行者的变身咏唱（红云蔽日/血雨倾盆）',
    source='第九章 第436话 格连 (md-0161)', edition='web_original',
    aliases=['bloodland_transform'])

add(id='芬里尔阿雷亚斯', caster='相川涡波（借血）／法夫纳系', type='普通魔法咏唱（鲜血魔法·剑圣）',
    chant='「总之『芬里尔』也记录在我的血里，借用下他的技术学起来会不会更快呢？──鲜血魔法『芬里尔・阿雷亚斯』」',
    jp='芬里尔・阿雷亚斯', en='Fenrir・Arias',
    effect='借剑圣芬里尔·阿雷亚斯之血的鲜血魔法',
    source='第五章 第139话 存钱攒经验 (md-0044)', edition='web_original',
    note='亦见「──鲜血魔法『芬里尔·阿雷亚斯』！」（第三章 第四章-拉丝缇娅拉・弗茨亚茨的战闘 md-0144）',
    aliases=['芬里尔·阿雷亚斯','鲜血魔法_芬里尔阿雷亚斯'])

add(id='假想诺文阿雷亚斯', caster='相川涡波', type='复合鲜血魔法',
    chant='「──复合鲜血魔法『假想诺文・阿雷亚斯』！」',
    jp='复合鲜血魔法・假想诺文・阿雷亚斯', en='—',
    effect='复合鲜血魔法（拟似诺文·阿雷亚斯）',
    source='第四章 第144话 忐忑不安的时间 (md-0070)', edition='web_original',
    aliases=['复合鲜血魔法_假想诺文阿雷亚斯'])

add(id='鲜血魔法相川涡波阳滝', caster='缇亚拉（血之力）／拉古涅', type='普通魔法咏唱（鲜血魔法·人名）',
    chant='「──鲜血・魔・法『相川涡波/相川阳滝』」',
    jp='鲜血魔法『相川涡波/相川阳滝』', en='—',
    effect='以相川兄妹之名为血之魔法（千年前编缀的鲜血咏唱）',
    source='第五章 第227话 《迷宫最后的战斗》 (md-0309)', edition='web_original',
    note='亦见「她当时确实吟唱了鲜血魔法『相川涡波/相川・阳滝』」（第7-2章 第304话 友人 7272md-0164）',
    aliases=['鲜血魔法_相川涡波/相川阳滝'])

add(id='大洪水', caster='水栖Boss怪物伽鲁夫纳多杰里', type='技能（怪物技）',
    chant='（Boss技能名：『大洪水』——水栖Boss怪物伽鲁夫纳多杰里的技能，水中忽视等级差距）',
    jp='大洪水', en='Flood',
    effect='水栖Boss伽鲁夫纳多杰里的『大洪水』技能',
    source='第四章 第144话 忐忑不安的时间 (md-0069/md-0070)', edition='web_original',
    aliases=['大洪水(伽鲁夫纳多杰里)'])

add(id='lostfania', caster='法夫纳（血之理的盗窃者）', type='普通魔法咏唱（鲜血魔法·召唤）',
    chant='「——鲜血魔法《旧历四年魔障研究院下层（LostFania・LaboratoryJail）》！」',
    jp='旧历四年魔障研究院下层', en='LostFania・LaboratoryJail',
    effect='从血之房间召唤大量『血之人偶』的鲜血魔法',
    source='第九章 第439话 次元的再上升 (md-0184)', edition='web_original',
    aliases=['LostFaniaLabourJail'])

add(id='两百一十四年西南解放战线', caster='法夫纳（血之理的盗窃者）', type='普通魔法咏唱（鲜血魔法·战争名）',
    chant='「——鲜血魔法『二百一十四年西南解放战线』。」',
    jp='二百一十四年西南解放战线', en='—',
    effect='以战争之名命名的鲜血魔法',
    source='第7-2章 第293话 血之理的盗窃者 (7272md-0090)', edition='web_original',
    aliases=['两百一十四年西南解放战线'])

add(id='fly_sophia', caster='斯诺·沃克', type='普通魔法咏唱（鲜血魔法·飞行）',
    chant='「我不需要。谁叫我一点也不怕涡波呢——鲜血魔法《Fly Sofia》。」',
    jp='Fly Sophia', en='Fly Sophia',
    effect='飞行鲜血魔法（Fly Sophia/Fly Sofia）',
    source='第十章 第468话 迪普拉库拉 (md-0058)', edition='web_original',
    note='亦见「——魔法《Fly Sophia》」（第十章 第469话 青鸟 md-0064）、「这一次我要把神的力量通通吞入腹中——魔法《flysophia》。」（第十章 第479话 库因菲利翁 md-0141）',
    aliases=['Fly Sofia','Fly Sophia','incantation_fly_sophia'])

add(id='屠龙的龙刃', caster='赛尔德拉（无之理的盗窃者）', type='古代复合魔法（屠龙）',
    chant='「——古代复合（・・）魔法《屠龙的龙刃（dragongenosize・Arder）》喔喔喔喔喔喔喔！！」',
    jp='屠龙的龙刃', en='Dragongenosize・Arder',
    effect='屠龙魔法/基因魔法（dragongenosys），上句「『强欲为求生之根本』『无欲为灭亡之泉源』『无度贪求直至荒芜』啊啊啊啊!!」',
    source='第十章 第471话 赛尔德拉 (md-0084)', edition='web_original',
    aliases=['屠龙的龙刃(dragongenosys・Arder)','屠龙的龙刃(dragongenosize・Arder)'])

# ── 王■落土/一闪系 ──
add(id='王■落土', caster='相川涡波（弟）', type='真正魔法级咏唱（守护归宿）',
    chant='「——**魔法（・・）**《王■落土（Lost・Vi・EithéA）》。」',
    jp='王■落土', en='Lost・Vi・EithéA',
    effect='弟弟「持续守护归宿」的魔法（Lost・Vi・EithéA），上句「──『此身乃无名无姓孑然一身的孩童之魂』──！」',
    source='第十章 第501话 『真正的丝线』 (md-0278)', edition='web_original',
    aliases=['王■落土(Lost·Vi·EithéA)','王■落土','王落土LostViEitheA'])

add(id='■道落土', caster='相川阳滝（姐）', type='真正魔法级咏唱（循线坠落）',
    chant='「──魔法（・・）《■道落土（Lord・Of・Lord）》」',
    jp='■道落土', en='Lord・Of・Lord',
    effect='姐姐「循着路线坠落」的魔法（Lord・Of・Lord），为兄妹首次真正魔法',
    source='第十章 第501话 『真正的丝线』 (md-0279)', edition='web_original',
    note='亦见「──魔・法『■道落土（Lord・Of・Lord）』！！」（第五章 第222话 第五十之试练『天狱』 md-0233）、「──魔・法『■道落土（Lord・Of・Lord）』！！」（第五章 第222话 md-0233）',
    aliases=['■道落土(Lord・Of・Lord)','■道落土(Lord·of·Lord)'])

add(id='亡灵一闪_致亲爱的一闪', caster='相川涡波', type='剑技魔法（升华）',
    chant='「——魔法（・・）《亡灵一闪（Von・A・Wraith）》。」',
    jp='亡灵一闪／致亲爱的一闪', en='Von・A・Wraith / Di・A・Wraith',
    effect='千锤百炼的一剑超越时空；可升华成《致亲爱的一闪（Di・A・Wraith）》，包含传达思念的愿望',
    source='第十章 第501话 『真正的丝线』 (md-0278)', edition='web_original',
    note='升华形态「——**魔法（・・）**《致亲爱的一闪（Di・A・Wraith）》。」（第八章 第404话 感想战 md-0280）；上句「──『至亲之友、在此作别』。『被世界拒绝的剑啊』『由我们来继承』──」',
    aliases=['亡灵一闪(Von・A・Wraith)','魔法『亡灵一闪』','致亲爱的一闪','致亲爱的一闪DiAWraith','魔法『致亲爱的一闪』'])

add(id='缇达真正魔法', caster='缇达·兰斯（暗之理的盗窃者）', type='真正魔法（咏唱起始）',
    chant='「——『世界(你)背信于我』——」',
    jp='缇达・兰斯真正魔法（咏唱起始）', en='—',
    effect='暗之理的盗窃者缇达・兰斯真正魔法的咏唱起始句（世界（你）背信于我）',
    source='第十章 第500话 第百二十之试炼『绊』 (md-0271)', edition='web_original',
    aliases=['缇达・兰斯真正魔法(咏唱起始)'])

# ── 其他 ──
add(id='阳滝精神干涉魔法', caster='相川阳滝', type='魔法（精神干涉）',
    chant='（叙事：她要抹去涡波心中所有重要的事物，再以自己取而代之）',
    jp='阳滝精神干涉魔法', en='—',
    effect='阳滝以精神干涉魔法抹去涡波心中重要事物并以自己取而代之',
    source='第7-3章 第333话 今后的日子 (7373md-0085)', edition='web_original',
    aliases=['阳滝精神干涉魔法'])

add(id='亡失的殉教者', caster='帕林库洛', type='普通魔法咏唱（咒）',
    chant='「──魔法『亡失的殉教者』！──魔法『启蒙家的再调律』！！」',
    jp='亡失的殉教者', en='—',
    effect='帕林库洛的咒魔法（亡失的殉教者），连涡波也难以抵抗',
    source='第三章 第七章『清算』 (md-0238)', edition='web_reconstructed+web_original',
    note='亦见「就算是涡波小哥也没法抵抗缇达的魔法吧？──魔法『亡失的殉教者』。」（第三章 第六章-圣诞祭结束 md-0230）',
    aliases=['魔法_亡失的殉教者'])

add(id='启蒙家的再调律', caster='帕林库洛', type='普通魔法咏唱（咒）',
    chant='「包在我身上。正好让我适应下新的力量。──魔法『启蒙家的再调律』。」',
    jp='启蒙家的再调律', en='—',
    effect='帕林库洛的咒魔法（启蒙家的再调律）',
    source='第三章 第七章『清算』 (md-0233)', edition='web_reconstructed+web_original',
    aliases=['魔法_启蒙家的再调律'])

add(id='对始祖封印魔方阵', caster='缇亚拉（千年前布设）', type='魔方阵（封印术式）',
    chant='（叙事：在城内蠢动的植物全部变作了文字，由此形成了『对始祖封印魔方阵』）',
    jp='对始祖封印魔方阵', en='—',
    effect='为封印始祖涡波而自千年前准备的魔方阵（植物化作文字）',
    source='第六章 第257话 无名的孩子的—— (md-0209)', edition='web_original',
    aliases=['对始祖封印魔方阵'])

add(id='magic_bag', caster='缇亚拉／使徒勒迦希（共同研发）', type='咒术（持有物）',
    chant='「英雄大人，您把我忘了吗？还是说我早就入不了您的法眼了？不过，『持有物』可是缇亚拉大人和使徒勒迦希共同研发的魔法。正式名称为，咒术《Magic Bag》——」',
    jp='Magic Bag（持有物）', en='Magic Bag',
    effect='『持有物』咒术（Magic Bag），可被与缇亚拉缘分匪浅者（诺瓦露）干涉',
    source='第十章 第501话 『真正的丝线』 (md-0280)', edition='web_original',
    aliases=['咒术《Magic Bag》'])

add(id='神铁锻造', caster='缇娅拉（千年前）', type='咒术/技能（锻造）',
    chant='（叙事：我硬是没让它完成。为了隐藏真正的『职责』、写下的『术式』、积累的『代价』……它将在千年后经由『我们』的手完成）',
    jp='神铁锻造', en='—',
    effect='铸造Rokh Bringer的咒术/技能，千年后经『我们』之手完成，成为唯一能触碰阳滝的武器（吸收阳滝魔之毒）',
    source='第八章 第381话 新暦0004年 (md-0127)', edition='web_original',
    aliases=['咒术:神铁锻造','神铁锻造'])

add(id='vibration', caster='赛尔德拉', type='咒术（振动）',
    chant='「不对，这并非『无之力』。是我在芙茨亚茨偷偷——错了，是我学来的一项技术。尽管期待吧罗密斯。这世界还留有很多有意思的东西喔——咒术《Vibration》。」',
    jp='Vibration（振动）', en='Vibration',
    effect='振动咒术（可隔绝海下震动）；《Vibration・field》/《di・vibration》为派生',
    source='第九章 第434话 和科学毫无差异 (md-0149)', edition='web_original',
    note='亦见「阿阿......——魔法《di・vibration》」（第八章 第374话 最终章来到后半 md-0089）、『——《Vibration・field》』（第十章 第483话 第八十之试炼『边狱』 md-0164）',
    aliases=['Vibration','di·vibration','Vibration・field'])

add(id='genoscythe', caster='赛尔德拉（无之理的盗窃者）', type='普通魔法咏唱（基因/放射线）',
    chant='「——魔法《Nuclear・主锁断裂（Genoscythe）》。」',
    jp='Nuclear・主锁断裂', en='Genoscythe',
    effect='切断DNA（魔法之线）的放射线/基因魔法，可剿灭群敌',
    source='第九章 第433话 高度发展的魔法技术 (md-0140)', edition='web_original',
    aliases=['Nuclear主锁断裂/Genoscythe'])

add(id='血之结界咏唱', caster='缇达／暗之系', type='咏唱（结界）',
    chant='（原文未收录完整咏唱句；相关句「那我就来瘫痪掉血之结界好了。」）',
    jp='血之结界咏唱', en='—',
    effect='暗/血之结界咏唱（瘫痪结界）',
    source='第八章 第365话 英雄的约定 (md-0064)', edition='web_original',
    aliases=['血之结界咏唱'])

io.open(entries_file, 'w', encoding='utf-8').write(json.dumps(entries, ensure_ascii=False, indent=1))
print('entries total:', len(entries))
