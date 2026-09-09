# -*- coding: utf-8 -*-
import json, sys, os

BASE = r"D:\DeepSeek Harness专用！危险！！！！！\迷深清洗工作2\异世界迷宫最深部_知识库\分析\酒馆导入v3\角色卡"
LQ, RQ = "\u201c", "\u201d"  # curly double quotes used in card texts

# (file, field, tag, old, new)
EDITS = []

# ── 帕林库洛 ──
F = "帕林库洛・勒伽西_card.json"
EDITS += [
    (F, "scenario", "G1",
     "战后回顾——洗脑（L5981）、",
     "战后回顾线：后期线详见专属世界书手动条目（剧情推进后启用）。"),
    (F, "scenario", "G2",
     "与涡波决战（一年前），战斗中提及『亲和』一词（L2107）；",
     "一年前决战与『亲和』条件线：后期线详见专属世界书手动条目（剧情推进后启用）；"),
    (F, "personality", "G3",
     "洗脑/幕后——冷峻、令人恐惧的沉默威压",
     "对局/幕后——冷峻、令人恐惧的沉默威压"),
    (F, "description", "G4",
     "涡波——他断言" + LQ + "不会加入任何人的队伍、终将成为会长" + RQ + "的救命恩人兼战斗前辈，半调侃半恳切的栽培对象",
     "涡波——由他引入公会、一手栽培的战斗后辈，也是他唯一收不住真挚的期许所在"),
    (F, "scenario", "G5",
     "教导海因系后辈「将自己的人生视作戏剧观赏」（L6066）",
     "与海因一同向拉丝缇娅拉传授「将自己的人生视作戏剧观赏」（L6066）"),
    (F, "personality", "G6",
     "「伤到一点就算输」「那不过是激将法而已」（第三章 L588/L623）",
     "「伤到一点就算输」（第三章 L588，叙述转述）「那不过是激将法而已」（第三章 L623）"),
]

# ── 佩露修娜 ──
F = "佩露修娜_card.json"
EDITS += [
    (F, "scenario", "G7",
     "**对大灾厄的知情者**（第7-3章 比起爱与生命 L2613）：为拉古涅故乡西多雅村说明大灾厄毁灭真相——偏僻小村遭交易中断与绝收而废弃，村民完成避难转移。\n**半人马总长战**（第7-2章 生命的价值）：总长亲自出击，同队对抗涡波一行被擒（L13018-L13021）。",
     "**大灾厄知情与总长战结局**：后期线详见专属世界书手动条目（剧情推进后启用）。"),
    (F, "scenario", "G8",
     "道破两位会长身份",
     "道破芙兰与涡波二人身份"),
    (F, "personality", "G9",
     "对外人用敬称「拉古涅」「艾尔米拉德卿」「希达尔克卿」「涡波君」「相川涡波殿下」",
     "对尊长用敬称、对后辈同袍（拉古涅、诺瓦露、芙兰、格连）直呼其名"),
    (F, "description", "G10",
     "观战者称之为「工作中毒」",
     "观战者称之为「工作中毒」（涡波吐槽语）"),
]

# ── 塞拉 ──
F = "塞拉・雷迪安特_card.json"
EDITS += [
    (F, "scenario", "G11-scenario",
     "察觉涡波" + LQ + "可能还没有放弃将圣人的力量据为己有" + RQ + "的可疑举止（第7-1章 L459）",
     "察觉斐勒卢托「可能还没有放弃将圣人的力量据为己有」的可疑举止（第7-1章 L459）"),
    (F, "post_history_instructions", "G11-PI",
     "对涡波「觊觎圣人力量」的疑心",
     "对斐勒卢托「觊觎圣人力量」的疑心"),
    (F, "scenario", "G12",
     "**『大灾厄』亲历**：向拉古涅讲述将本土半壁卷入其中的『大灾厄』与故乡变故（第7-3章 L4950）。",
     "**大灾厄亲历线**：后期线详见专属世界书手动条目（剧情推进后启用）。"),
    (F, "scenario", "G13a",
     "以两人配置迎战上千警备规模的威胁",
     "以两人配置接手原需上千警备的仪式护卫"),
    (F, "scenario", "G13b",
     "决定回家打招呼、载人战斗蓄势（第7-1章 L518、第7-3章）",
     "决定回家打招呼（L519）"),
    (F, "mes_example", "G14",
     "被『洗脑』的忠犬",
     "中了邪的忠犬"),
    (F, "personality", "G15",
     "「我扬声许下骑士的誓言，以求摘除塞拉的不安。」（旁白描述其誓言分量）",
     "「我扬声许下骑士的誓言，以求摘除塞拉的不安。」（涡波视角旁白，仅作关系注脚）"),
    (F, "description", "G16",
     "获称「狼形兽人女骑士」「巨狼塞拉」",
     "有「巨狼──塞拉小姐」等描述性称呼"),
]

# ── 赛尔德拉 ──
F = "赛尔德拉・库因非里翁 _ 赛鲁多拉_card.json"
EDITS += [
    (F, "description", "G17",
     "公开身份：南北联合总司令代理代行人、与相川涡波同行的可靠同伴",
     "公开身份：龙人战士、与相川涡波同行的可靠同伴（终局要职见手动条目）"),
    (F, "description", "G18a",
     "内里是千年来不断逃避悲伤、终被涡波看穿『留恋』的古老龙人",
     "内里是千年来靠「不回头」回避悲伤、从未向人敞开的古老龙人（后期线见手动条目）"),
    (F, "description", "G18b",
     "【性格・深层】一只活了千年、靠「不回头」来回避悲伤的龙。真正的『留恋』被涡波看穿之后，漫长的旅程才被划下句点；如今他正学着在安稳的日常里品味「幸福的余味」，而不是再逃。",
     "【性格・深层】千年来靠「不回头」回避悲伤、从未向人敞开的古老龙人（后期线见手动条目）。"),
    (F, "description", "G18c",
     "也不会说出自己比涡波强之类的话，他对那一战输得心服口服；",
     "也不会说出自己比涡波强之类的话；"),
    (F, "personality", "G19a",
     "- 语言指纹例句（原文）：「没有将自己可以能做到的事彻底完成就会催生出『留恋』，这正是我们『理的盗窃者』的难处啊。」",
     "- 语言指纹例句（原文）：「涡波，我可以正常地战斗。即使如此你还是要做吗？」（L5360）"),
    (F, "personality", "G19b",
     "口头禅/高频词：『留恋』、『理的盗窃者』、涡波、正常地战斗、声纳、血陆。",
     "口头禅/高频词：『理的盗窃者』、涡波、正常地战斗、声纳、血陆。"),
    (F, "scenario", "G20",
     "在『原来的世界』与涡波的认真一战（L1616、L3181、L3188），败北感成为「已经输了的证据」。\n涡波看穿他真正的『留恋』，为「龙人赛尔德拉・库因非里翁漫长的旅程划下了句点」（L977）。\n至今未变魔石的秘密：涡波为他「『执笔』」后续（L978）。\n涡波的『赛尔德拉攻略』：提供未见识过的异世界料理、以『过去视』再现他故乡的料理，「大大扩充他人生的色彩」（L1438）。\n一个月前与涡波同行『原来的世界』（L1130）。",
     "第九章终局线（『留恋』看穿与『执笔』内幕）：后期线详见专属世界书手动条目（剧情推进后启用）。"),
    (F, "description", "G21a",
     "赛拉・雷迪安特——会向他送来情报报告的少女",
     "赛拉・雷迪安特——会向他送来情报报告"),
    (F, "description", "G21b",
     "他给的是「休息」「闭上眼」这类具体指令",
     "他给的是「闭上眼」这类具体指令"),
    (F, "personality", "G21c",
     "「古奈尔・历基亚。够了，快闭上眼。」",
     "「古奈尔・历基亚。……够了，快闭上眼。」"),
    (F, "description", "G21e",
     "库因非里翁为姓氏，「库因」为其名的一部分，勿当作另一角色",
     "「库因菲利翁／库因非里翁」异写皆为同一姓氏，勿当作另一角色"),
]

# load all files (memory)
docs = {}
tails = {}
for f in sorted(set(e[0] for e in EDITS)):
    p = os.path.join(BASE, f)
    raw = open(p, "rb").read()
    assert raw[:3] != b"\xef\xbb\xbf", f + ": unexpected BOM"
    text = raw.decode("utf-8-sig")
    tails[f] = raw.endswith(b"\n")
    docs[f] = json.loads(text)

FROZEN = {}
for f, d in docs.items():
    FROZEN[f] = (d["data"].get("name"), d["data"].get("creator_notes"), tuple(d["data"].get("tags", [])),
                 d["data"].get("first_mes"), tuple(d["data"].get("alternate_greetings", [])))

report, abort = [], False
for f, field, tag, old, new in EDITS:
    cur = docs[f]["data"][field]
    n = cur.count(old)
    if n == 1:
        docs[f]["data"][field] = cur.replace(old, new)
        report.append(f"[OK] {tag} {f}/{field}: replaced (1 hit)")
    elif n == 0:
        if new in cur:
            report.append(f"[IDEMPOTENT] {tag} {f}/{field}: new text already in place, skipped")
        else:
            report.append(f"[MISS] {tag} {f}/{field}: old not found and new not present -> NEEDS REVIEW")
            abort = True
    else:
        report.append(f"[MULTI={n}] {tag} {f}/{field}: old string hits {n} times -> ABORT")
        abort = True

if abort:
    print("\n".join(report))
    print("ABORTED — no write performed")
    sys.exit(1)

# write back
for f, d in docs.items():
    out = json.dumps(d, ensure_ascii=False, indent=2)
    if tails[f]:
        out += "\n"
    open(os.path.join(BASE, f), "wb").write(out.encode("utf-8"))
    report.append(f"[WRITE] {f}")

print("\n".join(report))
