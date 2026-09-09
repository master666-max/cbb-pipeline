# -*- coding: utf-8 -*-
"""生成 P6/P7/P8 子代理消费的摘要清单（小而精，避免子代理读大 JSON）。

输出到 _digest/ ：
- 伏笔清单.json     ：所有 foreshadow 事件 + 所有 callback 事件（含旧id引用/语义文本）
- 反转清单.json     ：所有 reversal=true 事件（含 before_belief/after_truth 若有）
- 咏唱清单.json     ：所有 incantation_refs 事件（含魔法名文本）
- 分层清单.json     ：每层全事件标题速览（供 P10 timeline_index 用）
"""
import os, json, re

BASE = r"D:/DeepSeek Harness专用！危险！！！！！/迷深清洗工作2/年表输出"
SRC = os.path.join(BASE, "_merged", "events_all_norm.json")
DIG = os.path.join(BASE, "_digest")
os.makedirs(DIG, exist_ok=True)

data = json.load(open(SRC, encoding="utf-8"))

def brief(e):
    return {
        "event_id": e["event_id"],
        "title": e.get("title", ""),
        "event_time": e.get("event_time", ""),
        "story_anchor": e.get("story_anchor", ""),
        "timeline_layer": e.get("timeline_layer", ""),
        "event_type": e.get("event_type", ""),
        "foreshadow": e.get("foreshadow", ""),
        "callback": e.get("callback", ""),
        "reversal": e.get("reversal", False),
        "before_belief": e.get("before_belief", ""),
        "after_truth": e.get("after_truth", ""),
        "incantation_refs": e.get("incantation_refs", []),
        "characters": e.get("characters", []),
    }

fs = [brief(e) for e in data if e.get("foreshadow")]
cb = [brief(e) for e in data if e.get("callback")]
rv = [brief(e) for e in data if e.get("reversal")]
ic = [brief(e) for e in data if e.get("incantation_refs")]

json.dump({"foreshadow_events": fs, "callback_events": cb},
          open(os.path.join(DIG, "伏笔清单.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
json.dump(rv, open(os.path.join(DIG, "反转清单.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
json.dump(ic, open(os.path.join(DIG, "咏唱清单.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

# 分层速览
by_layer = {}
for e in data:
    l = e.get("timeline_layer", "T3")
    by_layer.setdefault(l, []).append({"event_id": e["event_id"], "title": e.get("title", "")})
json.dump(by_layer, open(os.path.join(DIG, "分层清单.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

print("foreshadow:", len(fs), "callback:", len(cb), "reversal:", len(rv), "incantation:", len(ic))
print("分层:", {k: len(v) for k, v in by_layer.items()})
print("->", DIG)