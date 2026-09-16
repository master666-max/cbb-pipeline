# -*- coding: utf-8 -*-
"""write_batch6_tail.py — ch0062/0063/0064/0065 抽取件落盘（一次性脚本）"""
import json
from pathlib import Path

WORK = Path('迷深实战-工作区/candidates')
VA = {"path": "语料分析/corpus/clean_full.txt", "sha": "e1a96061d25b0016094dd8daec82769ee80fc3bb", "verified_at": "2026-09-17"}
R6 = "领域规则（中文小说《迷深》正典库构建）：1) 元文本（作者杂谈/翻译组公告/论坛吐槽/现实日期/话数卷数/平台与作品名）一律不得抽取任何实体或关系；2) 无专名但固定出场且有关键行为的职务称呼（如店长）应抽取为实体；3) 专有名词（人名/地名/魔法名/道具名）保留原文写法，不翻译不改写；4) 信件/传闻/指控中的声称按文本事实抽取，并在 fact 中标注'据某某声称'。"

c62 = {"_meta": {
  "unit": "U-C03 批6 · CHAPTER 0062（第六卷-第五章Epilogue，摄入序50→tick50→2000-02-19）",
  "source": dict(VA, slice="行27630-27786（CHAPTER 0062，157行）"),
  "extractor": "ZCode 代理亲抽（GLM-5.3，工单 v1.4 §0）",
  "r6_verbatim": R6,
  "reference_time": "伪锚点 2000-01-01+i；本章摄入序=50→tick50→2000-02-19。禁墙钟。",
  "coordinate_line_note": "evidence.line=章内物理行（=文件行号-27629）。",
  "r6_decision": {"verdict": "正文正常抽取（尾声：购船与出航）", "reason": "全章连续剧情正文", "deterministic_check": "无译注/元文本"},
  "cross_chapter_notes": [
    "★帕林库洛=守护者缇达魔石宿主（L106）：『那家伙体内寄宿着守护者缇达的魔石』——魔石争夺线（弗茨亚茨高层急红眼）与追讨动机的合流点",
    "★七人船旅开幕：LivingLegend号（失败作魔导船/市价两倍现金购入/缇亚一人供几百魔法使级魔力出航/魔石易燃易爆+四人火灾隐患）；涡波赛后赌场以感应赚钱（拉丝缇娅拉逼的）；身份收束宣言=不再以基督·欧亚而以相川涡波身份生活"
  ],
  "alias_policy": "同 STATE 固化决议+判例4。无新增。", "confidence_calibration": "同 STATE 固化决议。", "observations_policy": "实体 observations 仅首入库存活。"
 }, "candidates": [
  {"type": "entity", "library": "setting", "confidence": 0.9, "canonical": {"name": "『LivingLegend号』", "entity_type": "设施(魔导船)"}, "aliases_to_register": ["活着的传说号"], "observations": [{"category": "summary", "chapter": 62, "text": "七人新据点：大量魔石建造不仰赖风浪的魔导船（失败作贱价出售/需几百名魔法使级魔力出航=缇亚一人即可/易燃易爆火种多）；拉丝缇娅拉命名（塞拉捍卫品味）；设 Connection 后船旅途中可随时往迷宫探索"}], "evidence": [{"vol": 1, "chapter": 62, "line": 67, "quote": "「那么，这艘船的名字就叫『LivingLegend号』了！没问题吧！？」"}, {"vol": 1, "chapter": 62, "line": 26, "quote": "「确实是这样……可是，它是要耗费几百名魔法使的魔力才能一度出海的东西，相当的不省油哦？之所以会贱价出售，正是因为无人问津。」"}]},
  {"type": "relation", "library": "relation", "confidence": 0.9, "canonical": {"subject": "帕林库洛", "rel_type": "魔石宿主(守护者缇达)", "object": "缇达", "claim": False}, "observations": [{"category": "relation", "chapter": 62, "text": "追讨动机合流点：守护者魔石寄宿强大力量（帕林库洛与玛利亚属性变化为证）；弗茨亚茨高层为得魔石急红眼；涡波最大动机=无法原谅（场面话自剥）"}], "evidence": [{"vol": 1, "chapter": 62, "line": 106, "quote": "「不能放任帕林库洛恣意妄为。那家伙体内寄宿着守护者缇达的魔石。」"}]},
  {"type": "relation", "library": "relation", "confidence": 0.9, "canonical": {"subject": "相川涡波", "rel_type": "追讨共识(七人同心)", "object": "帕林库洛", "claim": False}, "observations": [{"category": "relation", "chapter": 62, "text": "六人各自应诺：拉丝缇娅拉（一人去会生气）/缇亚（一剑之仇）/玛利亚（约好不再分开）/斯诺（搭档互助+帕也是我敌人）/莉帕（感觉超坏）/塞拉（为了大小姐）；涡波领悟=没有必要独自战斗"}], "evidence": [{"vol": 1, "chapter": 62, "line": 116, "quote": "「我想我和他必有一战……而在那场战斗中——」"}, {"vol": 1, "chapter": 62, "line": 119, "quote": "「我希望大家能助我一臂之力。」"}]},
  {"type": "event", "library": "event", "confidence": 0.9, "canonical": {"name": "古尔亚德港深夜购船", "kind": "交易", "tick": 50, "instant": None, "time_verbatim": "决赛逃亡当夜"}, "entities_involved": ["拉丝缇娅拉", "相川涡波", "缇亚", "古尔亚德国"], "observations": [{"category": "event", "chapter": 62, "text": "市价两倍现金非正规交易；资金=拉丝缇娅拉逼涡波赛后赌场用技能『感应』所赚；缇亚触船灌魔力启动（余波撼动海面/商人无言）；涡波+莉帕 Dimension 速读资料掌舵"}], "evidence": [{"vol": 1, "chapter": 62, "line": 24, "quote": "我现在是真的累得够呛，至于原因，那自然是拉丝缇娅拉所谓的「随便一赚」了，这些买船的钱都是她逼我去赚来的。我是真的想不到，自己居然会在和诺文的比赛之后跑去赌场，甚至使用技能『感应』在里面赚钱。"}, {"vol": 1, "chapter": 62, "line": 43, "quote": "缇亚将庞大的魔力灌进了船内。"}]},
  {"type": "event", "library": "event", "confidence": 0.9, "canonical": {"name": "LivingLegend号黎明出航(本土)", "kind": "出航", "tick": 50, "instant": None, "time_verbatim": "黎明"}, "entities_involved": ["相川涡波", "莉帕", "拉丝缇娅拉", "缇亚", "玛利亚·迪斯特拉斯", "斯诺·沃克", "塞拉·雷迪安特"], "observations": [{"category": "event", "chapter": 62, "text": "七人队伍首航（此前最多三人队）；Dimension 辅助航海+沿海岸线航行；身份收束：不再以基督·欧亚而以相川涡波身份生活——『迷失于异世界的相川涡波真正的冒险——此时此刻，终于开始了』"}], "evidence": [{"vol": 1, "chapter": 62, "line": 149, "quote": "「——大家，出发吧！就这样一路向『本土』进发！！」"}, {"vol": 1, "chapter": 62, "line": 152, "quote": "在这个异世界中，我不再以基督·欧亚，而是以相川涡波的身份继续生活。"}]},
  {"type": "foreshadow", "library": "foreshadow", "confidence": 0.88, "canonical": {"name": "本土追讨与三十层后探索双线", "setup_chapter": 62, "payoff_chapter": None, "tier": "核心", "note": "主目标=搜索帕林库洛（本土）；迷宫探索抽空推进（为妹妹往最深部的焦躁曾被帕林库洛利用——不会再搞错顺序）；阿尔缇+诺文的教诲已化为切实力量——下一卷主轴预告（卷七）", "chapter": 62}, "entities_involved": ["相川涡波", "帕林库洛", "阿尔缇", "诺文"], "observations": [{"category": "foreshadowing", "chapter": 62, "text": "『跨越了『试练』的我变强了』的自信宣言（对圣诞祭败北的翻盘预告）"}], "evidence": [{"vol": 1, "chapter": 62, "line": 103, "quote": "虽然路上打算抽时间推进迷宫探索，但基本上还是以搜索帕林库洛为要务的。"}, {"vol": 1, "chapter": 62, "line": 115, "quote": "『火之理的盗窃者阿尔缇』和『地之理的盗窃者诺文』两人都教会了我许多。他们的教诲已经转化为了切实的力量。"}]},
  {"type": "setting", "library": "setting", "confidence": 0.88, "canonical": {"name": "古尔亚德国的地理定位", "fact": "联合国南端·唯一临海国（港口众多）——七人逃亡首站与出海基地", "chapter": 62, "tick": 50}, "entities_involved": ["古尔亚德国"], "observations": [{"category": "knowledge", "chapter": 62, "text": "与 ch52 拉丝缇娅拉流亡潜伏地一致"}], "evidence": [{"vol": 1, "chapter": 62, "line": 3, "quote": "古尔亚德国位于联合国的南端。"}, {"vol": 1, "chapter": 62, "line": 4, "quote": "因为古尔亚德是联合国中唯一临海的国家，故而港口众多。"}]},
  {"type": "entity", "library": "character", "confidence": 0.9, "canonical": {"name": "相川涡波", "entity_type": "人物"}, "aliases_to_register": [], "observations": [{"category": "status_change", "chapter": 62, "text": "尾声定位：领队（七人队伍）；疲劳透支（比赛直后赌场赚钱）；不再孤独的实感宣言"}], "evidence": [{"vol": 1, "chapter": 62, "line": 137, "quote": "在这个广阔的异世界中，我并不是孤独的。"}]},
  {"type": "entity", "library": "character", "confidence": 0.88, "canonical": {"name": "缇亚", "entity_type": "人物"}, "aliases_to_register": [], "observations": [{"category": "appearance", "chapter": 62, "text": "魔力最强担当（船体启动一人代几百魔法使）；一剑之仇宣言"}], "evidence": [{"vol": 1, "chapter": 62, "line": 41, "quote": "「嗯，拜托了。因为缇亚是我们当中魔力最强的嘛。」"}]}
 ]}

c63 = {"_meta": {
  "unit": "U-C03 批6 · CHAPTER 0063（第六卷-第六章-梦的尾声，摄入序51→tick51→2000-02-20）",
  "source": dict(VA, slice="行27787-27840（CHAPTER 0063，54行）"),
  "extractor": "ZCode 代理亲抽（GLM-5.3，工单 v1.4 §0）",
  "r6_verbatim": R6,
  "reference_time": "伪锚点 2000-01-01+i；本章摄入序=51→tick51→2000-02-20。禁墙钟。",
  "coordinate_line_note": "evidence.line=章内物理行（=文件行号-27786）。",
  "r6_decision": {"verdict": "正文正常抽取（诺文临终幻视=剧情内事实，作 event/setting 提取）", "reason": "全章连续剧情正文（第三人称终章）", "deterministic_check": "无译注/元文本"},
  "cross_chapter_notes": ["★诺文临终梦=真愿的最终具象：破宅庭院+平民孩子们（非贵族）+木枝代剑+『好厉害啊！真努力啊！』的赞扬（千年前未得之物）+黑发二挚友在场道别→世界终结中满足入睡——『这个微笑就是他的人生并非没有意义的证明』"],
  "alias_policy": "同 STATE 固化决议。", "confidence_calibration": "同 STATE 固化决议。", "observations_policy": "实体 observations 仅首入库存活。"
 }, "candidates": [
  {"type": "event", "library": "event", "confidence": 0.9, "canonical": {"name": "诺文的临终梦(庭院的朋友们)", "kind": "临终幻视", "tick": 51, "instant": None, "time_verbatim": "消失途中的一瞬间"}, "entities_involved": ["诺文", "莉帕", "相川涡波"], "observations": [{"category": "event", "chapter": 63, "text": "梦的延续：破宅召集朋友（平民孩子们非贵族——没打进贵族圈却得到更出色的朋友）；木枝代剑游戏少年技术第一；赞扬声中含两名黑发挚友——『之所以一直在挥剑，都是为了这个』；与挚友道别后独留宅邸迎来世界终结，满足入睡"}], "evidence": [{"vol": 1, "chapter": 63, "line": 15, "quote": "「好厉害啊！」「真努力啊！」"}, {"vol": 1, "chapter": 63, "line": 24, "quote": "之所以一直在挥剑，都是为了这个——"}]},
  {"type": "setting", "library": "setting", "confidence": 0.9, "canonical": {"name": "诺文梦的报偿结构(赞扬即真愿)", "fact": "临终梦揭示真愿最终形态：每日修练的报偿=孩子们的赞扬（好厉害/真努力）+挚友在场——非荣光非家名；愿望实现/报偿得到/留恋消失→人生最幸福笑容的道别与安眠；『这个微笑就是他的人生并非没有意义的证明』（千年时光后终得报偿）", "chapter": 63, "tick": 51}, "entities_involved": ["诺文"], "observations": [{"category": "interpretation", "chapter": 63, "text": "与 ch60『微小的光』宣言/ch61 消失辞完全同构——三层收束"}], "evidence": [{"vol": 1, "chapter": 63, "line": 49, "quote": "这个微笑就是他的人生并非没有意义的证明。"}, {"vol": 1, "chapter": 63, "line": 50, "quote": "经过了千年的时光、栗发的少年诺文·阿雷亚斯得到了报偿。"}]},
  {"type": "relation", "library": "relation", "confidence": 0.88, "canonical": {"subject": "诺文", "rel_type": "临终道别(黑发挚友们)", "object": "相川涡波", "claim": False}, "observations": [{"category": "relation", "chapter": 63, "text": "梦中黑发二挚友（涡波与莉帕）在赞扬者之中；人生最幸福笑容的最棒『再见』——守护下的消解完成"}], "evidence": [{"vol": 1, "chapter": 63, "line": 19, "quote": "两名黑发的挚友。千真万确地可以称作挚友的存在就在这里。"}, {"vol": 1, "chapter": 63, "line": 33, "quote": "所以他能用人生最幸福的笑容同两人道别。"}]}
 ]}

noise = {
 64: ("第六卷-后记", "行27841-27855", "作者后记：舞斗大会篇完结感言/书名自嘲/第七卷预告（迷宫探索主轴·七人队伍·航海与本土）+卡牌游戏兴趣谈+致谢——R6 规则1 作者杂谈零抽取（七卷预告=出版侧元评论不入库）", "R6 规则1 作者杂谈+下卷出版预告"),
 65: ("第六卷-封面说明（内含剧透）", "行27856-27883", "封面注释：核心主题引诺文外传（宅邸少年仰望青空/英雄荣光信条）+构图象征解读（遗剑=退场/颠茄=莉帕诅咒与留恋消解/彼岸花/三途川与守渡人/桥=心意相通）——作者级象征解读整章排除，ch0054 同判；外传引文不作正典证据", "R6 规则1 封面美术说明=作品侧元评论；剧透内容不入库"),
}
for no, (title, sl, verdict, reason) in noise.items():
    globals()[f"c{no}"] = {"_meta": {
      "unit": f"U-C03 批6 · CHAPTER {no:04d}（{title}，摄入序{no-14}）",
      "source": dict(VA, slice=f"{sl}（CHAPTER {no:04d}）"),
      "extractor": "ZCode 代理亲抽（GLM-5.3，工单 v1.4 §0）",
      "r6_verbatim": R6,
      "reference_time": f"伪锚点 2000-01-01+i；本章摄入序={no-14}→tick{no-14}→伪锚点 2000-02-{no-14-31+1:02d}。禁墙钟。",
      "coordinate_line_note": "evidence.line=章内物理行；本章零候选。",
      "r6_decision": {"verdict": verdict, "reason": reason, "deterministic_check": f"清洗版 NOISE 标记+boundary noise=true（ch{no:04d}）"},
      "cross_chapter_notes": [], "alias_policy": "同 STATE 固化决议。", "confidence_calibration": "同 STATE 固化决议。", "observations_policy": "实体 observations 仅首入库存活。"
    }, "candidates": []}

for no in (62, 63, 64, 65):
    p = WORK / f"extraction-ch{no:04d}.json"
    p.write_text(json.dumps(globals()[f"c{no}"], ensure_ascii=False, indent=1), encoding="utf-8")
    print("written", p.name, "candidates", len(globals()[f"c{no}"]["candidates"]))
