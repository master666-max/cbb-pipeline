
# -*- coding: utf-8 -*-
import io, json, os
entries_file = '迷深清洗工作2/咏唱补录_entries.json'
entries = json.load(io.open(entries_file, encoding='utf-8'))
def add(**kw):
    entries.append(kw)

# ── Sehr・Wind 系 ──
add(id='sehr_wind', caster='海因·赫勒比勒夏因／莱纳·赫勒比勒夏因／缇缇（风之理系）', type='普通魔法咏唱（风系高阶）',
    chant='「——《Sehr Wind》！！」',
    jp='Sehr・Wind', en='Sehr・Wind',
    effect='风之理的盗窃者系高阶风魔法（Sehr＝德语「非常」），风暴压制/开路',
    source='第7-3章 第336话 阶梯 (7373md-0112)', edition='web_original',
    note='别名：SehrWind／Sehr·Wind／Sehr・Wind／sehr_Wind／Sehr Wind／罗德_SehrWind／罗德_Wind；亦见「——碍事！『Sehr·Wind』！！」（第7-1章 第272话 妨碍 7171md-0056）、「——《sehr Wind》！！」（第八章 第394话 赫尔米娜‧涅夏的悲愿 md-0208）',
    aliases=['SehrWind','Sehr·Wind','Sehr・Wind','sehr_Wind','Sehr Wind','罗德_SehrWind','罗德_Wind'])

add(id='wind_madness', caster='海因·赫勒比勒夏因／莱纳（风系）', type='普通魔法咏唱（风系）',
    chant='「都压在这招上了！给我把所有人统统刮飞！！──魔法『Wind・Madness』！！」',
    jp='Wind・Madness', en='Wind・Madness',
    effect='将一切刮飞的风系暴乱魔法',
    source='第7-1章 第275话 将军 (7171md-0075)', edition='web_original',
    aliases=['WindMadness'])

add(id='sehr_wind_madness', caster='海莉·维斯普洛佩／莱纳·赫勒比勒夏因', type='普通魔法咏唱（风系）',
    chant='「我要前往最深部！没错，纵使要同你们争斗也无所谓！就算在此殒命亦无妨！──『SehrWind・Madness』！」',
    jp='SehrWind・Madness', en='SehrWind・Madness',
    effect='Sehr・Wind的狂乱形态，赌上性命的强袭风魔法',
    source='第四章 第146话 剧 (md-0079)', edition='web_original',
    note='亦见「──『Sehr Wind・Madness』！！我的攻击手段也不光有剑而已！艾德老师的教导，加上海莉的力量，我现在的风魔法正可谓是赫勒比勒夏因家的最强！！」（第五章 第179话 md-0260，莱纳）、「粉碎他的四肢！──『Sehr Wind・Madness』！！」（第五章 第179话 md-0262）',
    aliases=['SehrWindMadness'])

add(id='cannon_sehr', caster='海莉·维斯普洛佩', type='普通魔法咏唱（风系炮击）',
    chant='「是大小姐吗、真是蛮横啊！『CannonSehr』！」',
    jp='CannonSehr', en='Cannon Sehr',
    effect='Sehr・Wind的炮击形态',
    source='第四章 第146话 剧 (md-0080)', edition='web_original',
    note='亦见「──『Growth Extended』！鲜血魔法『海因・赫勒比勒夏因』！再加上『Cannon Sehr』！！」（md-0080）',
    aliases=['CannonSehr'])

add(id='cannon_sehr_madness', caster='海莉·维斯普洛佩', type='普通魔法咏唱（风系炮击·狂乱）',
    chant='「呋呋呋，还没完！我还能、继续！──『CannonSehr・Madness』！！」',
    jp='CannonSehr・Madness', en='Cannon Sehr・Madness',
    effect='双重展开的Cannon Sehr狂乱形态，可抵消冻结魔法',
    source='第四章 第146话 剧 (md-0082)', edition='web_original',
    aliases=['CannonSehrMadness'])

add(id='sehr_fang', caster='海莉·维斯普洛佩', type='普通魔法咏唱（风系獠牙）',
    chant='「『Sehr Fang』！」',
    jp='Sehr Fang', en='Sehr Fang',
    effect='Sehr・Wind的獠牙形态（近身风刃）',
    source='第四章 第146话 剧 (md-0081)', edition='web_original',
    aliases=['SehrFang'])

add(id='ex_wind', caster='莱纳·赫勒比勒夏因', type='普通魔法咏唱（风系）',
    chant='「——《EX・Wind》。」',
    jp='Ex・Wind', en='EX・Wind',
    effect='莱纳拿手的高阶风魔法，配合双剑斩击',
    source='第九章 第447话 梦的奴隶 (md-0241)', edition='web_original',
    note='别名：Ex Wind／EXWind／ExWind／罗德_ExWind／魔法『Ex・Wind』；亦见「——魔法《EX・WIND》喔喔喔喔喔喔喔喔喔喔喔！！」（第十章 第482话 边狱八十 md-0157）、「魔法『Ex・Wind』O噢噢噢噢噢噢噢噢噢噢────…」（第五章 第220话 空之魔王 md-0221，罗德）',
    aliases=['Ex Wind','EXWind','ExWind','罗德_ExWind','魔法『Ex・Wind』'])

add(id='wind_bless_draw', caster='海因·赫勒比勒夏因', type='普通魔法咏唱（风系祝福/牵引）',
    chant='「──『Wind・Bless』、『Wind・Draw』。」',
    jp='Wind・Bless／Wind・Draw', en='Wind・Bless / Wind・Draw',
    effect='风系祝福与牵引魔法，开路护送之用',
    source='第三章 第四章-玛利亚・■■■■■ (md-0191)', edition='web_reconstructed+web_original',
    aliases=['WindBless','WindDraw'])

add(id='wind_umbrella', caster='缇缇', type='普通魔法咏唱（风系防御）',
    chant='「别太小瞧人了啊！新任的『支配之王』！──『Wind・Umbrella』！！」',
    jp='Wind・Umbrella', en='Wind・Umbrella',
    effect='风之伞（圆盾防御），与阳滝同规格的青色魔力圆盾对撞',
    source='第六章 第259话 自狱四十，二童归至。恆白物语，流溢于此。 (md-0223)', edition='web_original',
    aliases=['Wind·Umbrella'])

add(id='wind_放浪者', caster='莱纳·赫勒比勒夏因', type='普通魔法咏唱（风系）',
    chant='「是啊！──『既临风王玉座，其人永无他路可行』魔法『Wind・放浪者』！」',
    jp='Wind・放浪者', en='Wind・Wanderer',
    effect='「既临风王玉座，其人永无他路可行」的辅助奔跑风魔法',
    source='第四章 第156话 柯尔库 (md-0136)', edition='web_original',
    aliases=['Wind放浪者'])

add(id='zeitlos_wind', caster='海因·赫勒比勒夏因／艾徳', type='普通魔法咏唱（风系）',
    chant='「──『Zeitlos・Wind』。」（译注：Zeitlos、德语的永恒）',
    jp='Zeitlos・Wind', en='Zeitlos・Wind',
    effect='永恒之风的魔法（Zeitlos＝德语「永恒」），可抵消冻结冷气',
    source='第五章 第五章-分岐点『前祭』 (md-0123)', edition='web_original',
    note='亦见「──『Zeitlos・Wind』！」（第六章 第260话 最终章「艾徳・■■■・缇缇」 md-0235，艾徳）',
    aliases=['Zeitlos・Wind'])

add(id='rays_wind', caster='海因·赫勒比勒夏因（风系）', type='普通魔法咏唱（风系）',
    chant='「──『Rays・Wind』！」',
    jp='Rays・Wind', en='Rays・Wind',
    effect='光线/放射状风魔法',
    source='第五章 第五章-分岐点『前祭』 (md-0124)', edition='web_original',
    note='亦见「──『Rays・Wind』！」（第三章 舞闘大会 md-0134）',
    aliases=['Rays・Wind'])

add(id='无序之风', caster='莱纳（风系）／海莉·维斯普洛佩／缇缇系', type='普通魔法咏唱（风系）',
    chant='「──『无序之风』！」',
    jp='无序之风', en='Disorder・Wind',
    effect='扰乱次元之冬的风魔法，与冷气相互络合',
    source='第四章 第158话 木之理的盗窃者 (md-0144)', edition='web_original',
    note='亦见「──『维度』/『无序之风』──」（第四章 第146话 剧 md-0079）、「那个，禁止呦。『无序之风』」（第五章 第186话 Epilogue-新的开始地点 md-0005）',
    aliases=['无序之风'])

add(id='kaze_no_ya', caster='莱纳／缇缇（风系）', type='普通魔法咏唱（风系）',
    chant='「──『风之矢』！！」',
    jp='风之矢', en='Wind・Arrow',
    effect='风系箭矢魔法（魔弹）',
    source='第五章 第202话 魔王大人和勇者大人关系超棒 (md-0106)', edition='web_original',
    note='亦见「唔姆！跟人对射的话我可是不会输的！你的道路就让姐姐来开辟！──魔弹『风之矢』！！」（第六章 第260话 最终章「艾徳・■■■・缇缇」 md-0234）',
    aliases=['风魔法_风之矢','风之矢'])

add(id='kaze_no_ya_sanka', caster='罗德（缇缇）', type='普通魔法咏唱（风系·散花）',
    chant='「『加速、而后进溅』、『花碎之瓣全数作风驱驰』！──魔弹（Fly Shoots）『风之矢・散花（Fall Flower）』！！」',
    jp='风之矢・散花', en='Wind・Arrow・Fall Flower',
    effect='风之矢散花形态（Fall Flower），无数绿点尽为风之矢',
    source='第五章 第220话 空之魔王 (md-0218)', edition='web_original',
    aliases=['罗德_风之矢散花'])

add(id='gyokuza_fuu', caster='罗德（缇缇）', type='咏唱（风之咏唱/咒术）',
    chant='「──『玉座既临路一条』。『残躯已化风千束』、『孤以此生铭此愿』『遍历悠世凭徒步』！」',
    jp='玉座既临路一条（风之咏唱）', en='—',
    effect='罗德（缇缇）传授「咏唱即咒术」之秘的代表风之咏唱（玉座へ続く道）',
    source='第五章 第217话 千及百一十一年铸此轻薄之集大成 (md-0199)', edition='web_original',
    note='亦见『玉座既临路一条』（第五章 第192话 咒术『咏唱』 md-0039）',
    aliases=['风之咏唱_玉座既临路一条'])

add(id='boukyaku_kakusan', caster='罗德（缇缇）', type='咒术咏唱',
    chant='「一群早已崩壊只会机械式（擅自）行动的人偶！只要安静地待在空中就够了！！──咒术『忘却扩散（Reverse）』！！」',
    jp='忘却扩散', en='Reverse',
    effect='使行动的人偶安静下来的咒术（忘却扩散）',
    source='第五章 第218话 天狱五十，孤臣堕坠。唯愿奏此、幼王终曲。 (md-0205)', edition='web_original',
    aliases=['罗德_忘却扩散'])

add(id='limitbreak_sehrwind', caster='缇缇', type='普通魔法咏唱（风系·突破）',
    chant='「唔姆，看到了！那么、人家想想哦～，这里就多少尊敬一下涡涡的审美。──风魔法『LimitBreak・SehrWind・G・EndBurst』哦哦！！」',
    jp='LimitBreak・SehrWind・G・EndBurst', en='LimitBreak・SehrWind・G・EndBurst',
    effect='缇缇的风龙卷极限突破技',
    source='第六章 第240话 海路 (md-0078)', edition='web_original',
    aliases=['风魔法『LimitBreak・SehrWind・G・EndBurst』'])

add(id='ryuu_no_kaze', caster='斯诺·沃克（龙人化）', type='普通魔法咏唱（龙风系）',
    chant='「——『龙之风』呦，乘载我的魔力吧。」',
    jp='龙之风', en='Dragon・Wind',
    effect='龙人化后释放的龙之风，可乘载魔力',
    source='第九章 第433话 高度发展的魔法技术 (md-0140)', edition='web_original',
    note='亦见「——『龙之风』啊。」（第十章 第467话 兽人 md-0050）',
    aliases=['龙之风'])

add(id='dragon_ardor', caster='斯诺·沃克／格连·沃克（龙化）', type='普通魔法咏唱（龙炎系）',
    chant='「——『Dragon·Ardor』！！」',
    jp='Dragon・Ardor（龙之咆哮）', en='Dragon・Ardor',
    effect='龙人化后的龙之咆哮/龙炎魔法',
    source='第7-3章 第335话 第二回合 (7373md-0107)', edition='web_original',
    note='别名：龙之咆哮/龙之风(Dragon·Ardor)／Dragoon_Ardour／Dragoon_Arder／Dragoon·Arder；亦见「——《Dragoon・Ardour》阿阿阿阿！！」（第八章 第395话 代理 md-0212）、「『无度贪求直至荒芜』！——《Dragoon・Arder》！！」（第八章 第398话 『我们』 md-0236）',
    aliases=['Dragon·Ardor','龙之咆哮/龙之风(Dragon·Ardor)','Dragoon_Ardour','Dragoon_Arder','Dragoon·Arder'])

add(id='kaze_no_ude', caster='莱纳·赫勒比勒夏因（继承海因／海莉之臂腕）', type='技能/魔法（风系）',
    chant='「**『风之腕（・・・）』**」',
    jp='风之腕', en='Wind・Arm',
    effect='由风构成的手臂，为已故骑士海因与魔石人类海莉之臂腕的继承；从背后伸入体内发动次元魔法',
    source='第八章 第402话 身高相较 (md-0260)', edition='web_original',
    aliases=['风之腕'])

add(id='jiyuu_no_kaze', caster='缇缇（风之理的盗窃者所盗取）', type='普通魔法咏唱（风系）',
    chant='「为了人家的剑上啊！『自由之风』哟！──『风』！」',
    jp='自由之风', en='Free・Wind',
    effect='风之理的盗窃者盗取的『自由之风』，为佩艾希亚建国之风',
    source='第六章 第234话 始祖和魔王的共同作业 (md-0040)', edition='web_original',
    note='亦见「孤的属性为风……『风之理的盗窃者（罗德・缇缇）』盗取了『自由之风』。」（第五章 第212话 罗德（Lord） md-0172）',
    aliases=['自由之风','罗德_自由之风'])

add(id='raina_chant', caster='莱纳·赫勒比勒夏因', type='咏唱（誓句）',
    chant='「啊啊，没错！而这就是我・的・魔・法！为了拯救守护者（你们）而存在的魔法──！！」',
    jp='莱纳咏唱（为守护者而存在的魔法）', en='—',
    effect='莱纳为拯救守护者（理的盗窃者）而咏唱的誓句魔法',
    source='第五章 第222话 第五十之试练『天狱』 (md-0235)', edition='web_original',
    note='P8 拆分为 莱纳_咏唱／莱纳_加速咏唱，实为同一咏唱；加速咏唱形态见 第五章 第216话 誓言 (md-0196/0197)',
    aliases=['莱纳_咏唱','莱纳_加速咏唱'])

add(id='因我之一切于此起誓', caster='相川涡波', type='咏唱（誓句）',
    chant='「——『因我之一切于此起誓』。『我会将这本书一直读下去』，『纵至此世终结亦然』——」',
    jp='因我之一切于此起誓', en='—',
    effect='以自身一切起誓的咏唱句（读书/坚持之誓）',
    source='第八章 第373话 欲望 (md-0087)', edition='web_original',
    aliases=['因我之一切于此起誓'])

io.open(entries_file, 'w', encoding='utf-8').write(json.dumps(entries, ensure_ascii=False, indent=1))
print('entries total:', len(entries))
