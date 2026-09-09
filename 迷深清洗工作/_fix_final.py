# -*- coding: utf-8 -*-
import io, json, re
root = '迷深清洗工作2/年表输出/_tmp_全/'
entries = json.load(io.open('迷深清洗工作2/咏唱补录_entries.json', encoding='utf-8'))
by_id = {e['id']: e for e in entries}

fixes = {
 'di_overwinter_mirror': '「解除不了的『异常状态』先搁着，『最深处的誓约者』！超出负荷的部分就用『并列思考』割下来！然后给大脑搞个新的人格，全都丢给他承受！根据需求，把相信的事物连同心灵替换掉也无所谓！——现在的我有数不尽的对策！如果还是不够，就用侵蚀『理』的魔法强行扭曲它！先反转缇达的『不信』，再使之『静止』！用二重之理掩埋黑暗吧！！——《过密次元的真冬・镜化》！！」',
 'kaze_no_ude': '不对，正确来说是莱纳肩膀长出了由风构成的手臂——『**风之腕（・・・）**』——从我背后伸进体内，使我发动了次元魔法。',
 'tiara': '——这就是魔法《Tiara》的价值所在。',
 'light_llaria': '「行了，差不多就是这样，赶紧开始战斗吧！不战斗的话事后一定会感到后悔的！自然，战斗了也一样会后悔吧！既如此，那么战与不战两相比较之下，还是战斗之后再后悔更划算！──魔法『Light・Llaria』！！呵呵，那就更无需多虑，接下来唯有一战而已，不是么！？作为『交流』的专家，由我来向诸位担保！彼此互搏和相杀，才是至高无上的『交流』！！」',
 '咏唱幼龙贪念日久难消': '「——『幼龙贪念　日久难消』……『偿罪之欲延烧之时，凶邪之念断灭之刻』……经年累月，终于澈悟。『所谓人者，无人有权予其宽恕，赦罪之人仅为自己』……『逝者之声由魂震奏』，若此声不灭，刀山火海，欣然赴往——」',
 'bloodland_transform': '「——『盗窃了血之理的罪人将迎来第二度的死亡』『只因我乃背负一次死亡亦无法偿清罪孽的大罪人』——」',
 'guardian_40_艾德': '「──必须要加以确认才行。如今的涡波大人究竟是『凡夫俗子』还是『英雄』，亦或是『王』吗，还是说是在这以上的什么呢？如果他还是和以前一样的话，到那时候──」',
 'guardian_40_缇缇': '「这・里、这・千・年・后・的・佩・艾・希・亚・正・是・四・十・层！正所谓是克服自己心中弱小的战场！！而这四十层，此时终于迎来了挑战者！！那便是我『自己』！应当接受这由我所准备的试练的、既不是涡波大人也不是缇缇姐姐大人！而是我『自己（艾德）』啊！没错，我一开始就明白的！唯有这场『试练』，我不能交由其它任何一人！因为我自己才是要跨越这场『试练』的挑战者啊！！」',
 'guardian_50_罗德': '「──『这・里』，这・除・孤・以・外・再・无・别・物・的・虚・无・之・空・便・是・五・十・层！『风之理的盗窃者』的阶层！与徒具空壳的孤简直再相配不过了不是吗！？理所当然啊，因为孤什么都没有！既无法赶工建造，也做不到强行借用的『这里』就是孤的一切！！来吧，虽然此处空无一物，不过不必拘礼！接下来要开始的就是『第五十之试练』！孤定要战胜于你，将『这里』引至真正的和平！！」',
 'grand_fall': '「共鸣魔法『Tows Schuss Wind・Grand Fall』！！」',
 'celestial_garden': '——星魔法『幻转大天体（Celestial·Garden）』！！',
 '代价咏唱火炎': '「将过去当做薪柴，令现在燃烧得更加旺盛。这正是火炎魔法的神髓。我传授给你的咏唱里就包含着那样的术式。」\n只要把没用的感情当做燃料就行了。把这不中用的身躯当做燃料就好了。',
}

corpus = io.open(root + '_corpus_text.txt', encoding='utf-8').read()
def norm_ws(s): return re.sub(r'\s+','', str(s))
for eid, txt in fixes.items():
    lines_ok = all(norm_ws(seg) in norm_ws(corpus) for seg in txt.split('\n'))
    print(('VERIFY' if lines_ok else 'MISSING'), eid)
    by_id[eid]['chant'] = txt
    by_id[eid]['chant_verbatim_fixed'] = True
# note for guardian_40_缇缇
by_id['guardian_40_缇缇']['note'] = 'P8 标签归为 缇缇，实为艾德于40层『自狱』的开场白（艾德既作守护者亦作挑战者的宣言）'

io.open('迷深清洗工作2/咏唱补录_entries.json', 'w', encoding='utf-8').write(json.dumps(entries, ensure_ascii=False, indent=1))

# full strict re-check
fail = []; checked = 0; skip = 0
for e in entries:
    ch = e.get('chant','')
    if not ch: continue
    if ch.startswith('（') or '(原文未收录' in ch or '（原文未收录' in ch or '（P8 派生' in ch or '(P8 派生' in ch or '（含组咒' in ch or '（叙事' in ch or '（P8 拆分' in ch:
        skip += 1; continue
    checked += 1
    segs = ch.split('\n')
    if not all(norm_ws(sg) in norm_ws(corpus) for sg in segs):
        fail.append((e['id'], ch[:50]))
print('checked:', checked, 'skip:', skip, 'FAIL:', len(fail))
for f in fail: print('  FAIL', f[0], '|', f[1])