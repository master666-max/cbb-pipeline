# -*- coding: utf-8 -*-
"""共享模块: 话级节映射加载与查询(供交付生成脚本使用)
用法:
    from _交付_节映射 import get_secs_by_chapter, load_sec_map
    secmap = load_sec_map()          # {章名: {sec_name, ep_range, event_ids[]}}
    secs = get_secs_by_chapter("第一章")
返回: [{sec_name, ep_range, event_ids, event_set}]
event_set 用于 O(1) 判断事件归属节。
"""
import json, os

_BASE = os.path.dirname(os.path.abspath(__file__))
_CACHE = None

def load_sec_map():
    global _CACHE
    if _CACHE is None:
        p = os.path.join(_BASE, "_索引_话级节映射.json")
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        _CACHE = {}
        for ch, info in data.get("chapters", {}).items():
            secs = []
            for s in info.get("secs", []):
                secs.append({
                    "sec_name": s.get("sec_name", ""),
                    "ep_range": s.get("ep_range"),
                    "event_ids": s.get("event_ids", []),
                    "event_set": set(s.get("event_ids", [])),
                })
            _CACHE[ch] = secs
    return _CACHE

def get_secs_by_chapter(ch):
    return load_sec_map().get(ch, [])

def sec_of_event(ch, event_id):
    """返回事件所在节的 sec_name(不含章前缀), 找不到返回 None"""
    for s in load_sec_map().get(ch, []):
        if event_id in s["event_set"]:
            name = s["sec_name"]
            # 去掉 "章名·" 前缀, 保留节名
            if "·" in name:
                name = name.split("·", 1)[1]
            return name
    return None

def chapter_sec_plan(ch, event_ids):
    """给定章名与该章全部 event_ids(按序), 返回节插入计划:
    [{sec_name, event_ids:[...]}] —— 保证覆盖全部事件(节映射缺失的事件归入尾节)
    """
    secs = get_secs_by_chapter(ch)
    if not secs:
        return [{"sec_name": ch, "event_ids": event_ids}]
    plan = []
    covered = set()
    for s in secs:
        ids = [eid for eid in s["event_ids"] if eid in event_ids]
        if ids:
            plan.append({"sec_name": s["sec_name"].split("·", 1)[1] if "·" in s["sec_name"] else s["sec_name"],
                         "event_ids": ids})
            covered.update(ids)
    rest = [eid for eid in event_ids if eid not in covered]
    if rest:
        if plan:
            plan[-1]["event_ids"].extend(rest)
        else:
            plan.append({"sec_name": ch, "event_ids": rest})
    return plan
