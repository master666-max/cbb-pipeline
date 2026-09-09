# -*- coding: utf-8 -*-
"""S2 数据变更: full_event_list.json
1) 删除 5 条同 block 双标(T1-0126/0129/0131/0136/0137)
2) 合并 T1-0132+T1-0133 -> 保留 T1-0132 吸收 0133(改 T3)
3) 迁移 6 条(T1-0125/0127/0128/0130/0134/0135) -> T3 + event_time 改写
4) 每条新增 time_seq + display_layer(命名解耦)
输出: 变更后 full_event_list.json + 变更 diff 记录
"""
import json, os, copy, re

BASE = r"D:/DeepSeek Harness专用！危险！！！！！/迷深清洗工作2/年表输出"
SRC = os.path.join(BASE, "final_output", "full_event_list.json")
DST = os.path.join(BASE, "_merged", "events_all.json")

DISPLAY = {
    "T0": ("原世界(现代日本)", 0),
    "T1": ("千年前·战争期", 1),
    "T2": ("千年前·建造期", 2),
    "T4": ("千年间", 3),
    "T3": ("千年后主线", 4),
}

fl = json.load(open(SRC, encoding="utf-8"))
byid = {e["event_id"]: e for e in fl}
diff = {"deleted": [], "merged": [], "migrated": [], "layer_count": {}}

# ── 1) 删除 5 条 ──
DEL = ["T1-0126", "T1-0129", "T1-0131", "T1-0136", "T1-0137"]
for eid in DEL:
    if eid in byid:
        diff["deleted"].append({"event_id": eid, "title": byid[eid]["title"], "block": re.findall(r"7373md-\d+", byid[eid].get("story_anchor",""))})
        del byid[eid]

# ── 2) 合并 T1-0132 + T1-0133 ──
a, b = byid["T1-0132"], byid["T1-0133"]
a["title"] = "帕林库洛×涡波『大灾厄』·拉古涅听闻与重拾初心"
a["event_time"] = "T3-主线中期·本土大灾厄(帕林库洛发动世界奉还阵·与涡波同归于尽)"
a["timeline_layer"] = "T3"
a["description"] = a["description"] + " 另据原文:拉古涅内心深知帕林库洛其实真心喜欢并保护涡波的,不禁疑惑他为何认真与涡波死战——是为畏惧涡波的『元老院』下达了暗杀命令,还是另有私人原因。"
a["characters"] = ["拉古涅·卡伊库欧拉", "塞拉·雷迪安特(天上之七骑士/魔人化骑士)", "帕林库洛·勒伽西(亡于同归于尽)", "相川涡波(始祖/千年前化身)"]
a["location"] = "联合国·大圣堂 / 本土与西多雅村"
a["event_type"] = "剧情高潮"
a["merged_from"] = ["T1-0132", "T1-0133"]
a["foreshadow"] = a.get("foreshadow") or "大灾厄(帕林库洛x涡波同归)是揭示帕林库洛真实立场的前史,指向弗茨亚茨大战(命运之日)"
a["quotes"] = list(dict.fromkeys(a.get("quotes", []) + b.get("quotes", [])))
diff["merged"].append({"keep": "T1-0132", "absorbed": "T1-0133", "title": a["title"]})
del byid["T1-0133"]

# ── 3) 迁移 6 条 -> T3 + event_time 改写 ──
MIG = {
    "T1-0125": ("T3-主线后期·第7-3章追忆(拉古涅幼年·西多雅村)", "拉古涅贫寒童年(第7-3章拉古涅追忆·现世幼年史)"),
    "T1-0127": ("T3-主线后期·第7-3章追忆(少女期·卡伊库欧拉家)", "拉古涅接近里埃尔(第7-3章追忆·少女期)"),
    "T1-0128": ("T3-主线后期·第7-3章追忆(候补骑士期·七骑士之邀)", "里埃尔·天上七骑士之邀(第7-3章追忆·候补骑士期)"),
    "T1-0130": ("T3-主线后期·第7-3章追忆(里埃尔死当日·帕林库洛荐入)", "帕林库洛荐拉古涅入七骑士(第7-3章追忆·里埃尔死当日)"),
    "T1-0134": ("T3-主线后期·弗茨亚茨行(大灾厄后·与涡波同行Living Legend号)", "拉古涅咏唱两节魔法启程夺顶(大灾厄后·弗茨亚茨行)"),
    "T1-0135": ("T3-主线后期·第7-3章追忆(大灾厄后五年·故乡寻母)", "拉古涅故乡寻母落空(第7-3章追忆·大灾厄后五年)"),
}
for eid, (newtime, newtitle) in MIG.items():
    e = byid[eid]
    diff["migrated"].append({"event_id": eid, "title": e["title"], "new_event_time": newtime})
    e["event_time"] = newtime
    e["title"] = newtitle
    e["timeline_layer"] = "T3"

# ── 4) 命名解耦: time_seq + display_layer(全库) ──
for e in byid.values():
    lay = e["timeline_layer"]
    dname, seq = DISPLAY.get(lay, (lay, 9))
    e["time_seq"] = seq
    e["display_layer"] = dname

# 层计数
from collections import Counter
cnt = Counter(e["timeline_layer"] for e in byid.values())
diff["layer_count"] = dict(cnt)

# 写回
fl_new = sorted(byid.values(), key=lambda e: (e.get("time_seq", 9), e["event_id"]))
json.dump(fl_new, open(SRC, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
# 同步 events_all.json(合并仓库)
if os.path.exists(DST):
    json.dump(fl_new, open(DST, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

json.dump(diff, open(os.path.join(BASE, "_S2_diff.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("S2 done. total:", len(fl_new), "| layers:", diff["layer_count"])
print("deleted:", [d["event_id"] for d in diff["deleted"]])
print("merged:", diff["merged"])
print("migrated:", [m["event_id"] for m in diff["migrated"]])
