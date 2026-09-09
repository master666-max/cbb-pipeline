# -*- coding: utf-8 -*-
import json, os, sys

BASE = r"D:\DeepSeek Harness专用！危险！！！！！\迷深清洗工作2\异世界迷宫最深部_知识库\分析\酒馆导入v3\角色卡"
PTR = "后期线详见专属世界书手动条目（剧情推进后启用）。"

FILES = {
    "PARK": "帕林库洛・勒伽西_card.json",
    "PELL": "佩露修娜_card.json",
    "SEIRA": "塞拉・雷迪安特_card.json",
    "SERD": "赛尔德拉・库因非里翁 _ 赛鲁多拉_card.json",
}

Q = '"'  # ASCII double quote used inside some fields

# (file, field, old, new, tag)
EDITS = [
    # ── 帕林库洛 ──
    ("PARK", "scenario",
     "**第7-2章（生命的价值）**：战后回顾——洗脑（L5981）、",
     "**第7-2章（生命的价值）**：战后回顾线：" + PTR,
     "G1"),
    ("PARK", "scenario",
     "与涡波决战（一年前），战斗中提及『亲和』一词（L2107）；",
     "一年前决战与『亲和』条件线：" + PTR + "；",
     "G2"),
    ("PARK", "personality",
     "洗脑/幕后——冷峻、令人恐惧的沉默威压",
     "对局/幕后——冷峻、令人恐惧的沉默威压",
     "G3"),
    ("PARK", "description",
     "涡波——他断言\"" + "不会加入任何人的队伍、终将成为会长" + "\"的救命恩人兼战斗前辈，半调侃半恳切的栽培对象",
     "涡波——由他引入公会、一手栽培的战斗后辈，也是他唯一收不住真挚的期许所在",
     "G4"),
    ("PARK", "scenario",
     "教导海因系后辈「将自己的人生视作戏剧观赏」（L6066）",
     "与海因一同向拉丝缇娅拉传授「将自己的人生视作戏剧观赏」（L6066）",
     "G5"),
    ("PARK", "scenario",
     "设「伤到一点就算输」的试练",
     "设「伤到一点就算输」（叙述转述）的试练",
     "G6-scenario"),
    ("PARK", "personality",
     "「伤到一点就算输」「那不过是激将法而已」（第三章 L588/L623）",
     "「伤到一点就算输」（叙述转述）「那不过是激将法而已」（第三章 L588/L623）",
     "G6-personality"),
    # ── 佩露修娜 ──
    ("PELL", "scenario",
     "\n**对大灾厄的知情者**（第7-3章 比起爱与生命 L2613）：为拉古涅故乡西多雅村说明大灾厄毁灭真相——偏僻小村遭交易中断与绝收而废弃，村民完成避难转移。\n**半人马总长战**（第7-2章 生命的价值）：总长亲自出击，同队对抗涡波一行被擒（L13018-L13021）。",
     "\n**大灾厄知情与总长战结局**：" + PTR,
     "G7"),
    ("PELL", "scenario",
     "道破两位会长身份、以及",
     "道破芙兰与涡波二人身份、以及",
     "G8"),
    ("PELL", "personality",
     "对外人用敬称「拉古涅」「艾尔米拉德卿」「希达尔克卿」「涡波君」「相川涡波殿下」",
     "对尊长用敬称（「艾尔米拉德卿」「希达尔克卿」「涡波君」「相川涡波殿下」）、对后辈同袍（拉古涅、诺瓦露、芙兰、格连）直呼其名",
     "G9"),
    ("PELL", "description",
     "观战者称之为「工作中毒」——",
     "观战者称之为「工作中毒」（涡波吐槽语）——",
     "G10"),
    # ── 塞拉 ──
    ("SEIRA", "scenario",
     "察觉涡波\"可能还没有放弃将圣人的力量据为己有\"的可疑举止（第7-1章 L459）",
     "察觉斐勒卢托『可能还没有放弃将圣人的力量据为己有』的可疑举止（第7-1章 L459）",
     "G11-scenario(P0)"),
    ("SEIRA", "post_history_instructions",
     "对涡波「觊觎圣人力量」的疑心",
     "对斐勒卢托「觊觎圣人力量」的疑心",
     "G11-PI(P0)"),
    ("SEIRA", "scenario",
     "**『大灾厄』亲历**：向拉古涅讲述将本土半壁卷入其中的『大灾厄』与故乡变故（第7-3章 L4950）。",
     "**大灾厄亲历线**：" + PTR,
     "G12(P0)"),
    ("SEIRA", "scenario",
     "仪式只能以两人配置迎战上千警备规模的威胁",
     "以两人配置接手原需上千警备的仪式护卫",
     "G13a"),
    ("SEIRA", "scenario",
     "决定回家打招呼、载人战斗蓄势（第7-1章 L518、第7-3章）",
     "决定回家打招呼（L519）",
     "G13b"),
    ("SEIRA", "mes_example",
     "被『洗脑』的忠犬",
     "中了邪的忠犬",
     "G14"),
    ("SEIRA", "personality",
     "「我扬声许下骑士的誓言，以求摘除塞拉的不安。」（旁白描述其誓言分量）",
     "「我扬声许下骑士的誓言，以求摘除塞拉的不安。」（涡波视角旁白，仅作关系注脚）",
     "G15"),
    ("SEIRA", "description",
     "获称「狼形兽人女骑士」「巨狼塞拉」",
     "有「巨狼──塞拉小姐」等描述性称呼",
     "G16"),
    # ── 赛尔德拉 ──
    ("SERD", "description",
     "公开身份：南北联合总司令代理代行人、与相川涡波同行的可靠同伴",
     "公开身份：龙人战士、与相川涡波同行的可靠同伴（终局要职见手动条目）",
     "G17(P0)"),
    ("SERD", "description",
     "内里是千年来不断逃避悲伤、终被涡波看穿『留恋』的古老龙人——这段往事不到剧情揭示时，他绝不主动摊开。",
     "内里是千年来靠「不回头」回避悲伤、从未向人敞开的古老龙人——这段往事不到剧情揭示时，他绝不主动摊开。",
     "G18a(P0)"),
    ("SERD", "description",
     "【性格・深层】一只活了千年、靠「不回头」来回避悲伤的龙。真正的『留恋』被涡波看穿之后，漫长的旅程才被划下句点；如今他正学着在安稳的日常里品味「幸福的余味」，而不是再逃。",
     "【性格・深层】一只活了千年、靠「不回头」来回避悲伤、从未向人敞开的古老龙人；真正的『留恋』在剧情揭示前绝不摊开（后期线详见专属世界书手动条目）。",
     "G18b(P0)"),
    ("SERD", "description",
     "也不会说出自己比涡波强之类的话，他对那一战输得心服口服；",
     "也不会说出自己比涡波强之类的话；",
     "G18c-负空间④(P0)"),
    ("SERD", "personality",
     "- 语言指纹例句（原文）：「没有将自己可以能做到的事彻底完成就会催生出『留恋』，这正是我们『理的盗窃者』的难处啊。」",
     "- 语言指纹例句（原文）：「涡波，我可以正常地战斗。即使如此你还是要做吗？」（L5360）",
     "G19a(P0)"),
    ("SERD", "personality",
     "- 口头禅/高频词：『留恋』、『理的盗窃者』、涡波、正常地战斗、声纳、血陆。",
     "- 口头禅/高频词：『理的盗窃者』、涡波、正常地战斗、声纳、血陆。",
     "G19b"),
    ("SERD", "personality",
     "对话关键词Top：涡波 / 留恋 / 理的盗窃者",
     "对话关键词Top：涡波 / 理的盗窃者",
     "G19c"),
    ("SERD", "scenario",
     "在『原来的世界』与涡波的认真一战（L1616、L3181、L3188），败北感成为「已经输了的证据」。\n涡波看穿他真正的『留恋』，为「龙人赛尔德拉・库因非里翁漫长的旅程划下了句点」（L977）。\n至今未变魔石的秘密：涡波为他「『执笔』」后续（L978）。\n涡波的『赛尔德拉攻略』：提供未见识过的异世界料理、以『过去视』再现他故乡的料理，「大大扩充他人生的色彩」（L1438）。\n一个月前与涡波同行『原来的世界』（L1130）。",
     "第九章终局线（『留恋』看穿与『执笔』内幕）：" + PTR,
     "G20(P0)"),
    ("SERD", "description",
     "赛拉・雷迪安特——会向他送来情报报告的少女",
     "赛拉・雷迪安特——会向他送来情报报告的同僚",
     "G21a"),
    ("SERD", "description",
     "同伴受伤或受惊时，他给的是「休息」「闭上眼」这类具体指令而非空洞安慰",
     "同伴受伤或受惊时，他给的是「闭上眼」这类具体指令而非空洞安慰",
     "G21b"),
    ("SERD", "personality",
     "（「古奈尔・历基亚。够了，快闭上眼。」）",
     "（「古奈尔・历基亚。……够了，快闭上眼。」）",
     "G21c"),
    ("SERD", "scenario",
     "涡波为他「『执笔』」后续（L978）",
     "涡波为他『执笔』后续（L978）",
     "G21d"),
    ("SERD", "description",
     "「库因」为其名的一部分，勿当作另一角色",
     "「库因菲利翁／库因非里翁」异写皆为同一姓氏，勿当作另一角色",
     "G21e"),
]

FROZEN = ["name", "creator_notes", "tags", "first_mes", "alternate_greetings"]

cards = {}
for key, fn in FILES.items():
    path = os.path.join(BASE, fn)
    raw = open(path, "rb").read()
    assert not raw.startswith(b"\xef\xbb\xbf"), key + ": unexpected BOM before write"
    txt = raw.decode("utf-8-sig")
    cards[key] = {"path": path, "txt": txt, "trail": txt.endswith("\n"), "json": json.loads(txt),
                  "orig": json.loads(txt)}

problems = []
applied, idem, covered = [], [], []
for key, field, old, new, tag in EDITS:
    s = cards[key]["json"]["data"][field]
    n = s.count(old)
    if n == 0:
        if new in s:
            idem.append((key, field, tag)); print("[IDEMPOTENT] %s %s %s" % (key, field, tag))
        else:
            problems.append((key, field, tag, "MISS(0 hit)")); print("[MISS] %s %s %s" % (key, field, tag))
    elif n > 1:
        problems.append((key, field, tag, "MULTI(%d)" % n)); print("[MULTI] %s %s %s x%d" % (key, field, tag, n))
    else:
        cards[key]["json"]["data"][field] = s.replace(old, new)
        applied.append((key, field, tag)); print("[APPLY] %s %s %s" % (key, field, tag))

if problems:
    print("\nABORT — problems:"); [print(p) for p in problems]; sys.exit(1)

# write back
for key in FILES:
    c = cards[key]
    out = json.dumps(c["json"], ensure_ascii=False, indent=2)
    if c["trail"]:
        out += "\n"
    open(c["path"], "wb").write(out.encode("utf-8"))

# verify
print("\n--- VERIFY ---")
ok = True
for key in FILES:
    path = cards[key]["path"]
    raw = open(path, "rb").read()
    if raw.startswith(b"\xef\xbb\xbf"):
        print("[FAIL] %s BOM present" % key); ok = False
    txt = raw.decode("utf-8")
    j = json.loads(txt)
    o = cards[key]["orig"]
    for f in FROZEN:
        if j["data"][f] != o["data"][f]:
            print("[FAIL] %s frozen field changed: %s" % (key, f)); ok = False
    if j["spec"] != o["spec"] or j["spec_version"] != o["spec_version"]:
        print("[FAIL] %s spec changed" % key); ok = False
for key, field, old, new, tag in EDITS:
    txt = open(cards[key]["path"], "rb").read().decode("utf-8")
    j = json.loads(txt)
    s = j["data"][field]
    if old in s:
        print("[FAIL] %s %s old still present (%s)" % (key, field, tag)); ok = False
    if new not in s and tag != "G21d":
        print("[FAIL] %s %s new absent (%s)" % (key, field, tag)); ok = False
if ok:
    print("ALL CHECKS PASSED")
print("\napplied=%d idempotent=%d" % (len(applied), len(idem)))
