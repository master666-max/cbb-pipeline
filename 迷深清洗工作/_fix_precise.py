# -*- coding: utf-8 -*-
import io, json
root = '迷深清洗工作2/年表输出/_tmp_全/'
entries = json.load(io.open('迷深清洗工作2/咏唱补录_entries.json', encoding='utf-8'))
by_id = {e['id']: e for e in entries}

# Exact corpus lines (verified by grep above)
fixes = {
 'new_reading': '「图书馆是穿越剧的固定项目呢，稍后我们再一起去赛尔德拉在的图书馆吧？总之先……——魔法《New・Reading》。」',
 'foam': '「容我稍微使用下魔法吧。──魔法『泡沫』。」',
 'gyokuza_fuu': '「哈哈、哈哈哈哈哈！既然这样那事情就简单了。──『玉座既临路一条』。『残躯已化风千束』、『孤以此生铭此愿』『遍历悠世凭徒步』！」',
 'kaze_no_ude': '**『风之腕（・・・）』**',
 '焦热世界': '「基督！你让我回想起了过去，让我想起了千·年·前·啊！你的面影，让我想起了往事！只要将你打倒的话，我的悲恋终于也能实现了！──魔法『Flame・决战炎域』、魔法『焦热世界』！！」',
 '不死杀的红莲龙': '「『『——**魔法**《不死杀的红莲龙》（Sin・BloodFafnir）——』』」',
 'light_mind': '「不过啊，涡波！现在我等三人被诺斯菲施加了魔法，所以这也是没有办法的事！我等被施加的是一种基本的光魔法──『Light Mind』！这虽然是世界上最为知名的精神干涉魔法，但由诺斯菲来使用的话也效果太惊人了！！」',
 '魔力变换': '（叙事：被奉为魔法之始祖的『异邦人』开发出了分解『魔之毒』的办法，亦即被称为『魔力变换（Level UP）』的魔法──准确来说是咒术）',
 '加速_孤乃加速之魂': '『加速』、『加速』『加速』『加速』。……『孤乃加速之魂』',
 '不罚的大英雄': '【最终防卫术式：暗魔法『不罚的大英雄』发动了】',
 'blood': '「咿嘻嘻，我有些想要的东西呐……所以我就收下了——魔法《Blood》。」',
 'lostfania': '「好啊涡波！你刚才说的是众人的灵魂对吧！既然如此，那就先来接受这道『试炼』吧！——鲜血魔法《旧历四年魔障研究院下层（LostFania・LaboratoryJail）》！」',
 '两百一十四年西南解放战线': '「——鲜血魔法『二百一十四年西南解放战线』。',
 'water_wire': '「我们的话还没说完呢！——《Ice Battering Ram》《Water Wire》《Flame Flamberge》《Rays·Wind》《Divine Arrow》《Earthquake》！！」',
 'dealing': '「——咒术『Dealing』。很好，这样一来『契约』就成立了。不过，想把『支配之王』从『这里』带走的话，必须要把握好相应的时机。不然的话，就算将你带走，很快也会被赛鲁多拉和艾德带人追上的。必须要营造一个他们两个都无暇顾及的时机才可以……」',
 'ice_aegis': '「共鸣魔法『冰・Aegis（守护冰）』',
 '涡波复合咒术咏唱': '「——『于此起誓，种种罪过，吾当清偿』『纵此世之终结至来，此誓亦无毁弃之日』——」',
}

# verify each fix exists in corpus (whitespace-normalized) or is marked narrative
import re
corpus = re.sub(r'\s+','', io.open(root + '_corpus_text.txt', encoding='utf-8').read())
for eid, txt in fixes.items():
    if txt.startswith('（叙事'):
        print('NARR  ', eid, 'OK'); continue
    core = re.sub(r'\s+','', txt)
    if core in corpus:
        print('VERIFY', eid, 'OK')
    else:
        print('VERIFY', eid, 'MISSING from corpus:', core[:60])

for eid, txt in fixes.items():
    if eid in by_id:
        by_id[eid]['chant'] = txt
        by_id[eid]['chant_verbatim_fixed'] = True

io.open('迷深清洗工作2/咏唱补录_entries.json', 'w', encoding='utf-8').write(json.dumps(entries, ensure_ascii=False, indent=1))
print('applied fixes')