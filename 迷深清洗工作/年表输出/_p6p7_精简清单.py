# -*- coding: utf-8 -*-
"""生成 P6/P7 专用精简清单（每条仅配对必需字段，控制文件体积）。"""
import os, json

BASE = r"D:/DeepSeek Harness专用！危险！！！！！/迷深清洗工作2/年表输出"
SRC = os.path.join(BASE, "_merged", "events_all_norm.json")
DIG = os.path.join(BASE, "_digest")

data = json.load(open(SRC, encoding="utf-8"))

# P6 精简：伏笔/回收配对只需 id/title/foreshadow/callback/story_anchor
fs = [{
    "event_id": e["event_id"], "title": e.get("title", ""),
    "foreshadow": e.get("foreshadow", ""), "story_anchor": e.get("story_anchor", ""),
    "event_type": e.get("event_type", ""),
} for e in data if e.get("foreshadow")]
cb = [{
    "event_id": e["event_id"], "title": e.get("title", ""),
    "callback": e.get("callback", ""), "story_anchor": e.get("story_anchor", ""),
    "event_type": e.get("event_type", ""),
} for e in data if e.get("callback")]

# P7 精简：反转节点
rv = [{
    "event_id": e["event_id"], "title": e.get("title", ""),
    "event_time": e.get("event_time", ""), "story_anchor": e.get("story_anchor", ""),
    "timeline_layer": e.get("timeline_layer", ""),
    "before_belief": e.get("before_belief", ""), "after_truth": e.get("after_truth", ""),
    "description": (e.get("description", "") or "")[:120],
} for e in data if e.get("reversal")]

json.dump({"foreshadow_events": fs, "callback_events": cb},
          open(os.path.join(DIG, "P6_配对精简.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
json.dump(rv, open(os.path.join(DIG, "P7_反转精简.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

print("P6 fs:", len(fs), "cb:", len(cb), "| P7 rv:", len(rv))
for name in ["P6_配对精简.json", "P7_反转精简.json"]:
    p = os.path.join(DIG, name)
    print(name, os.path.getsize(p), "bytes")