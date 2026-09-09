# -*- coding: utf-8 -*-
"""P9 前置规范化：对 _merged/events_all.json 做机械性清洗。

1. event_type 非法值映射（P9 已知）：
   剧情 -> 剧情高潮；光环高潮 -> 剧情高潮
2. reversal 字段规范化：
   - "True"/"true" -> true
   - "False"/"false" -> false（移除）
   - 中文描述值（如「涡波=千年前…」）拆为 before_belief/after_truth 暂存字段
     （P7 反转节点阶段再正式收编），reversal 置 true。
3. confidence 规范化：AI推算（统一用 AI推算 三字）。
4. 输出规范后文件 _merged/events_all_norm.json，并打印统计。
"""
import os, json, re

BASE = r"D:/DeepSeek Harness专用！危险！！！！！/迷深清洗工作2/年表输出"
SRC = os.path.join(BASE, "_merged", "events_all.json")
DST = os.path.join(BASE, "_merged", "events_all_norm.json")

TYPE_MAP = {
    "剧情": "剧情高潮",
    "光环高潮": "剧情高潮",
    "剧情高潮": "剧情高潮",
}

def main():
    data = json.load(open(SRC, encoding="utf-8"))
    stats = {"type_fixed": [], "rev_fixed": 0, "rev_removed": 0, "conf_fixed": []}
    for e in data:
        # 1. event_type
        t = e.get("event_type", "")
        if t in TYPE_MAP and t != "剧情高潮":
            stats["type_fixed"].append((e["event_id"], t, TYPE_MAP[t]))
            e["event_type"] = TYPE_MAP[t]
        # 2. reversal
        rv = e.get("reversal")
        if isinstance(rv, str):
            s = rv.strip()
            if s.lower() == "true":
                e["reversal"] = True
                stats["rev_fixed"] += 1
            elif s.lower() == "false":
                e.pop("reversal", None)
                stats["rev_removed"] += 1
            else:
                # 中文描述：拆分 before_belief/after_truth
                parts = re.split(r"[=＝→➝]", s, maxsplit=1)
                if len(parts) == 2:
                    e["before_belief"] = parts[0].strip()
                    e["after_truth"] = parts[1].strip()
                else:
                    e["before_belief"] = s
                    e["after_truth"] = "待复核"
                e["reversal"] = True
                stats["rev_fixed"] += 1
        # 3. confidence
        c = e.get("confidence", "")
        if c == "AI 推算" or c == "AI推算" or "AI" in c:
            if c != "AI推算":
                stats["conf_fixed"].append((e["event_id"], c))
                e["confidence"] = "AI推算"
    with open(DST, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print("总事件:", len(data))
    print("event_type 修正:", stats["type_fixed"])
    print("reversal 规范化次数:", stats["rev_fixed"], "移除:", stats["rev_removed"])
    print("confidence 修正:", stats["conf_fixed"])
    print("->", DST)

if __name__ == "__main__":
    main()