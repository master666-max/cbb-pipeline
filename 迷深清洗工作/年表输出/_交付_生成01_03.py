# -*- coding: utf-8 -*-
"""交付① 最终年表.md + 交付③ 酒馆世界书.json
数据: final_output/full_event_list.json + 交付四件套/_agg.json
"""
import os, json, re
from collections import Counter

BASE = r"D:/DeepSeek Harness专用！危险！！！！！/迷深清洗工作2/年表输出"
DELIVER = os.path.join(BASE, "交付四件套")

fl = json.load(open(os.path.join(BASE, "final_output", "full_event_list.json"), encoding="utf-8"))
agg = json.load(open(os.path.join(DELIVER, "_agg.json"), encoding="utf-8"))
by_id = {e["event_id"]: e for e in fl}

LAYER_META = {
    "T0": ("段0 · 原世界(现代日本)", "涡波与阳滝的原生家庭、英才教育、妹妹病倒、病床前救赎。颗粒度=年。"),
    "T1": ("段1 · 千年前·战争期(T-1000~T-995)", "兄妹被召唤、圣人缇娅拉救世、阳滝病恶化、始祖涡波疯狂复仇。颗粒度=月~周。"),
    "T2": ("段2 · 千年前·建造期(T-995~T-990)", "十位理的盗窃者就位、诺斯菲诞生、形式婚姻、涡波休眠。颗粒度=月~周。"),
    "T4": ("段3 · 千年间(T-990~T-0)", "拉丝缇娅拉培育、守护者就位、探索者攻略至23层。颗粒度=百年粗略。"),
    "T3": ("段4 · 千年后主线(T-0~终章)", "涡波一层苏醒、攻略各层、守护者战、终局。颗粒度=日~时刻。"),
}
LAYER_ORDER = ["T0", "T1", "T2", "T4", "T3"]
KEY_TYPES = ("守护者战", "剧情高潮", "身份揭露", "穿越召唤", "境界战争战役", "迷宫建造", "角色入队", "世界事件", "咏唱节点")

def ev_line(e, with_desc=False, maxdesc=0):
    t = f"**{e['event_id']} · {e['title']}**"
    head = f"- {t} ｜ `{e.get('event_time','')}` ｜ {e.get('event_type','')} ｜ {e.get('confidence','')}\n  - 锚点: {e.get('story_anchor','')}"
    if with_desc:
        d = e.get("description", "") or ""
        if maxdesc and len(d) > maxdesc:
            d = d[:maxdesc] + "…"
        head += f"\n  - 描述: {d}"
    if e.get("characters"):
        chs = e.get("characters", "")
        if isinstance(chs, list): chs = "、".join(str(c) for c in chs)
        head += f"\n  - 人物: {chs}"
    if e.get("location"):
        head += f"\n  - 地点: {e.get('location','')}"
    return head

def seg_top_events(seg, n=8):
    ids = seg["event_ids"]
    # 优先: 原文明确 & 关键类型
    scored = []
    for i in ids:
        e = by_id[i]
        s = 0
        if e.get("confidence") == "原文明确": s += 10
        if e.get("event_type") in KEY_TYPES: s += 5
        if e.get("reversal"): s += 3
        scored.append((s, e))
    scored.sort(key=lambda x: (-x[0], x[1]["event_id"]))
    return [e for _, e in scored[:n]]

# ══════════════ ① 最终年表.md ══════════════
md = []
md.append("# 迷深web版 · 最终事件年表(全量 1568 条)")
md.append("")
md.append("> 数据源: final_output/full_event_list.json(千年序排序, event_time 主键) ｜ 生成: 2026-09-01")
md.append("> 分层: T0=58 ｜ T1=123 ｜ T2=119 ｜ T4=45 ｜ T3=1223 ｜ 置信度: 原文明确1437 / 合理推断124 / AI推算7")
md.append("> 字段: event_id / event_time / story_anchor / title / description / characters / location / event_type / confidence")
md.append("")
md.append("## 千年序总览(时间轴序 = time_seq)")
md.append("")
md.append("| time_seq | 层(工作号) | 时段 | 事件数 | 说明 |")
md.append("|---|---|---|---|---|")
for L in LAYER_ORDER:
    name, desc = LAYER_META[L]
    n = sum(1 for e in fl if e["timeline_layer"] == L)
    # 时段: 从段名括号中提取(T-1000~T-995 等)
    import re as _re
    m = _re.search(r"\((T[^)]*)\)", name)
    span = m.group(1) if m else name.split("·")[1].strip()
    seq = {"T0":0,"T1":1,"T2":2,"T4":3,"T3":4}[L]
    md.append(f"| {seq} | {L} | {span} | {n} | {desc} |")
md.append("")
md.append("> 层编号 T0~T3 为提取工作号, 不表示时间先后; 时间轴顺序以 time_seq 为准(0→原世界, 1→战争期, 2→建造期, 3→千年间, 4→千年后主线)。")
md.append("")
for L in LAYER_ORDER:
    name, _ = LAYER_META[L]
    md.append(f"## {name}")
    md.append("")
    for seg in agg["layers"][L]:
        if L == "T3":
            # 主线章标题: 章名+剧情名(便于小目录识别)
            md.append(f"### {seg['seg_name']} · {seg['seg_desc']}")
        else:
            md.append(f"### {seg['seg_name']}")
        md.append("")
        md.append(f"*{seg['seg_desc']} ｜ 含事件 {len(seg['event_ids'])} 条*")
        md.append("")
        if L == "T3":
            # 主线小目录: 章内按话组分为节(方案第5项)
            from _交付_节映射 import chapter_sec_plan
            for sec in chapter_sec_plan(seg["seg_name"], seg["event_ids"]):
                md.append(f"#### {sec['sec_name']}({len(sec['event_ids'])}条)")
                md.append("")
                for i in sec["event_ids"]:
                    md.append(ev_line(by_id[i], with_desc=True))
                    md.append("")
        else:
            for i in seg["event_ids"]:
                md.append(ev_line(by_id[i], with_desc=True))
                md.append("")
    md.append("")
md_text = "\n".join(md)
open(os.path.join(DELIVER, "01_最终年表_全量_v5.md"), "w", encoding="utf-8").write(md_text)
print("① written:", len(md_text), "chars")

# ══════════════ ③ 酒馆世界书 json ══════════════
# 仿 共通世界书.json schema;每层一个总entry + 每seg一个entry + T3每章一个entry
def make_entry(uid, keys, content, name, comment, insert):
    return {
        "uid": uid, "key": keys, "keys": keys,
        "content": content,
        "extensions": {"position": 0, "exclude_recursion": False, "display_index": uid,
                       "probability": 100, "useProbability": True, "depth": 0,
                       "selectiveLogic": 0, "group": "", "group_override": False,
                       "group_weight": 100, "prevent_recursion": False,
                       "delay_until_recursion": False, "scan_depth": 2,
                       "match_whole_words": False, "use_group_scoring": False,
                       "case_sensitive": False, "automation_id": "", "role": 0,
                       "sticky": 0, "cooldown": 0, "delay": 0},
        "enabled": True, "insertion_order": insert, "case_sensitive": False,
        "name": name, "priority": insert, "id": uid, "comment": comment,
        "selective": False, "selectiveLogic": 0, "add_conversation": False,
        "display_index": uid, "delay_until_recursion": False, "exclude_recursion": False,
        "group": "", "group_override": False, "group_weight": 100,
        "prevent_recursion": False, "probability": 100, "useProbability": True,
        "scan_depth": 0, "sticky": 0, "cooldown": 0, "delay": 0, "role": 0,
        "automation_id": ""
    }

def agg_content(seg, maxitems=8, with_descline=False):
    """组内聚合: 简介行 + 关键事件列表(标题+一句话 desc 摘取)"""
    top = seg_top_events(seg, maxitems)
    lines = [f"【{seg['seg_name']}】{seg['seg_desc']} 含事件{len(seg['event_ids'])}条。"]
    for e in top:
        d = (e.get("description", "") or "").replace("\n", " ")
        # 取首句(到第一个句号/感叹号,≤90字)
        m = re.split(r"[。！？!?]", d)
        s = m[0] if m else d
        s = (s + ("。" if len(m) > 1 else ""))[:100]
        lines.append(f"• {e['title']}({e['event_id']}): {s}")
    return "\n".join(lines)

def make_keys(seg):
    # keys = seg名核心词 + 组内标题高频人物词(简)
    kws = []
    kws.append(seg["seg_name"].split(":")[0][:8])
    for e in seg_top_events(seg, 5):
        chs = e.get("characters", "") or []
        if isinstance(chs, str):
            chs = [c.strip() for c in chs.replace("、", ",").split(",")]
        for ch in chs[:2]:
            ch = str(ch).split("(")[0].strip()[:6]
            if ch and ch not in kws and len(ch) >= 2:
                kws.append(ch)
    return kws[:8]

entries = []
insert = 100
uid = 0

# 总览 entry
total_cnt = Counter(e["event_type"] for e in fl)
ov = ("《以异世界迷宫最深处为目标》web版事件年表(千年双时间线)。时间线分层: T0原世界·现代日本(58事件)→T1千年前境界战争期约T-1000~T-995(121)→T2千年前迷宫建造期约T-995~T-990(121)→T4迷宫间千年约T-990~T-0(49)→T3千年后故事主线(1219)。"
      "核心真相: 主角相川涡波(化名基督·欧亚)即是千年前迷宫始祖;迷宫是魔力污水处理厂/实现守护者千年愿望的遗迹;诺斯菲=第一个魔石人类=涡波千年前之妻;缇亚=使徒西斯转世;阳滝=100层水之理盗窃者。"
      f"事件类型分布: 剧情高潮{total_cnt.get('剧情高潮',0)}/身份揭露{total_cnt.get('身份揭露',0)}/守护者战{total_cnt.get('守护者战',0)}/咏唱节点{total_cnt.get('咏唱节点',0)}。"
      "检索用关键词: 迷宫层数、守护者名、使徒体系(西斯/勒伽西/迪普拉库拉)、各角色名、『第X之试炼』。")
entries.append(make_entry(uid, ["迷深", "异世界迷宫最深部", "时间线", "年表", "千年", "迷宫", "涡波", "阳滝", "始祖"], ov, "总览/千年双时间线", "总览", insert))
uid += 1; insert += 100

for L in LAYER_ORDER:
    name, desc = LAYER_META[L]
    segs = agg["layers"][L]
    # 层总 entry
    ids = [i for seg in segs for i in seg["event_ids"]]
    top_all = []
    for seg in segs:
        top_all += seg_top_events(seg, 3)
    top_all = sorted(top_all, key=lambda e: e["event_id"])[:10]
    lines = [f"【{name}】{desc} 事件{len(ids)}条。"]
    for e in top_all:
        d = (e.get("description", "") or "").replace("\n", " ")
        m = re.split(r"[。！？!?]", d); s = (m[0] if m else d)
        s = (s + ("。" if len(m) > 1 else ""))[:90]
        lines.append(f"• {e['title']}({e['event_id']}): {s}")
    lk = [name.split("·")[0]] + [seg["seg_name"].split(":")[0][:6] for seg in segs[:3]]
    entries.append(make_entry(uid, lk[:8], "\n".join(lines), f"{L} 层总览", f"{L}层", insert))
    uid += 1; insert += 100
    # seg entry
    for seg in segs:
        content = agg_content(seg)
        # T3 章 entry: 追加话级节导航(方案第5项)
        if L == "T3":
            from _交付_节映射 import get_secs_by_chapter
            secs = get_secs_by_chapter(seg["seg_name"])
            if secs:
                nav = ["", "【本章话组分节】"] + [f"· {s['sec_name'].split('·',1)[1] if '·' in s['sec_name'] else s['sec_name']} ({len(s['event_ids'])}条)" for s in secs]
                content += "\n" + "\n".join(nav)
        entries.append(make_entry(uid, make_keys(seg), content, f"{L}-{seg['seg_name'][:18]}", f"{L} {seg['seg_name'][:30]}", insert))
        uid += 1; insert += 100

# 反转节点 entry(六轴)
rev = json.load(open(os.path.join(BASE, "final_output", "reversal_nodes.json"), encoding="utf-8"))
axes = {}
for n in rev:
    ax = n.get("axis", 0)
    axes.setdefault(ax, []).append(n)
AXIS_NAME = {1: "涡波=千年前迷宫/莱文教始祖", 2: "迷宫本质=魔力污水处理厂", 3: "诺斯菲=涡波之女/妻·首个魔石人类",
             4: "缇亚=使徒西斯转世(独立个体)", 5: "技能???=使徒植入木马", 6: "阳滝=100层水之理盗窃者"}
for ax in sorted(axes):
    if ax == 0: continue
    ns = axes[ax][:6]
    lines = [f"【反转轴{ax}】{AXIS_NAME.get(ax,'')} 节点{len(axes[ax])}个。"]
    for n in ns:
        lines.append(f"• {n.get('title','')}({n.get('event_id')}): {n.get('before_belief','')}→{n.get('after_truth','')}")
    kws = ["反转"] + [n.get("title", "")[:4] for n in ns[:3]]
    entries.append(make_entry(uid, kws[:8], "\n".join(lines), f"反转轴{ax}", f"反转轴{ax}", insert))
    uid += 1; insert += 100

wb = {"name": "迷深时间线世界书(千年双线)", "description": "web版《以异世界迷宫最深处为目标》事件年表世界书: 千年前真相(T1/T2/T4)与千年后攻略主线(T3)双线, 覆盖反转轴与守护者战。",
      "metadata": {}, "entries": entries}
json.dump(wb, open(os.path.join(DELIVER, "03_酒馆世界书_时间线_v5.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("③ written entries:", len(entries))
