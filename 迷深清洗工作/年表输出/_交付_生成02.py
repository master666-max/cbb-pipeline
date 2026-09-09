# -*- coding: utf-8 -*-
"""交付② AI知识库(父子分段): 迷深web版·事件时间线知识库
父段=时间层/章; 子段=聚合组(带 parent+source),每条含代表事件摘要。
数据源: full_event_list + _agg.json + reversal_nodes + foreshadow_chains
"""
import os, json, re

BASE = r"D:/DeepSeek Harness专用！危险！！！！！/迷深清洗工作2/年表输出"
DELIVER = os.path.join(BASE, "交付四件套")
fl = json.load(open(os.path.join(BASE, "final_output", "full_event_list.json"), encoding="utf-8"))
agg = json.load(open(os.path.join(DELIVER, "_agg.json"), encoding="utf-8"))
rev = json.load(open(os.path.join(BASE, "final_output", "reversal_nodes.json"), encoding="utf-8"))
by_id = {e["event_id"]: e for e in fl}
rev_by_ev = {}
for n in rev:
    rev_by_ev.setdefault(n.get("event_id"), []).append(n)

KEY_TYPES = ("守护者战", "剧情高潮", "身份揭露", "穿越召唤", "境界战争战役", "迷宫建造", "角色入队", "世界事件", "咏唱节点")
LAYER_META = {
    "T0": ("P01", "原世界(现代日本)", "涡波与阳滝的原生家庭、英才教育、妹妹病倒、病床前救赎。颗粒度=年。58 事件。"),
    "T1": ("P02", "千年前·战争期(T-1000~T-995)", "兄妹被召唤、圣人缇娅拉救世、阳滝病恶化、始祖涡波疯狂复仇。颗粒度=月~周。123 事件。"),
    "T2": ("P03", "千年前·建造期(T-995~T-990)", "十位理的盗窃者就位、诺斯菲诞生、形式婚姻、涡波休眠。颗粒度=月~周。123 事件。"),
    "T4": ("P04", "千年间(T-990~T-0)", "拉丝缇娅拉培育、守护者就位、探索者攻略至23层。颗粒度=百年粗略。45 事件。"),
    "T3": ("P05", "千年后主线(T-0~终章)", "涡波一层苏醒、攻略各层、守护者战、终局。颗粒度=日~时刻。1223 事件。"),
}
# T3 章节父段映射
T3_CHAP_PARENT = {  # 章节 -> (父段号, 父段名)
    "第一章": ("P05", "第1~3章 攻略初期(10/20/30层)"),
    "第二章": ("P05", "第1~3章 攻略初期(10/20/30层)"),
    "第三章": ("P05", "第1~3章 攻略初期(10/20/30层)"),
    "第四章": ("P06", "第4~6章 中盘(40/50/60层)"),
    "第五章": ("P06", "第4~6章 中盘(40/50/60层)"),
    "第六章": ("P06", "第4~6章 中盘(40/50/60层)"),
    "第7-1章": ("P07", "第七章 爱的告白/生命的价值/比起爱与生命(70层)"),
    "第7-2章": ("P07", "第七章 爱的告白/生命的价值/比起爱与生命(70层)"),
    "第7-3章": ("P07", "第七章 爱的告白/生命的价值/比起爱与生命(70层)"),
    "第八章": ("P08", "第八章 最终章·始祖揭露(80层)"),
    "第九章": ("P09", "第九章 无尽的梦之延续(90层)"),
    "第十章": ("P10", "第十章 致以久远的天空(100层阳滝·终局)"),
    "未映射": ("P10", "第十章"),
}
T3_CHAP_DESC = {
    "第一章": "迷宫一层苏醒至迁移瓦尔德,基督·欧亚化名,拉丝缇娅拉入队", "第二章": "弗茨亚茨·圣诞祭,20层缇达暗之理战,缇娅拉再诞阴谋",
    "第三章": "舞斗大会,30层诺文地之理战,莉帕线", "第四章": "海上迷宫船与40层艾德木之理『面试』,西娅小队",
    "第五章": "庭师与无名者物语,50层风之理罗德线", "第六章": "仅此二人的家庭,60层诺斯菲光之理",
    "第7-1章": "爱的告白:佩艾希亚/支配之王线", "第7-2章": "生命的价值:缇亚/使徒西斯复活线", "第7-3章": "比起爱与生命:次元之冬封印西斯,缇亚独立个体确认",
    "第八章": "最终章·始祖真相:涡波=始祖,迷宫本质揭露", "第九章": "无尽的梦之延续:90层诺伊,世界奉还阵/终谭祭前奏",
    "第十章": "终谭祭·100层阳滝水之理决战,第120之试炼,终局与后日谭", "未映射": "其他",
}

def first_sents(text, n=2, cap=140):
    text = (text or "").replace("\n", " ")
    parts = re.split(r"(?<=[。！？!?])", text)
    out = ""
    for p in parts:
        if not p.strip(): continue
        out += p.strip()
        if len(out) >= cap: break
    return (out[:cap] + "…") if len(out) > cap else out

def seg_reps(seg, n=6):
    ids = seg["event_ids"]
    scored = []
    for i in ids:
        e = by_id[i]
        s = 0
        if e.get("confidence") == "原文明确": s += 10
        if e.get("event_type") in KEY_TYPES: s += 5
        if e.get("event_id") in rev_by_ev: s += 4
        scored.append((s, e))
    scored.sort(key=lambda x: (-x[0], x[1]["event_id"]))
    return [e for _, e in scored[:n]]

def fmt_ev(e):
    rv = rev_by_ev.get(e["event_id"], [])
    extra = ""
    if rv:
        b = rv[0].get("before_belief", ""); a = rv[0].get("after_truth", "")
        extra = f"  ｜ [反转] {b}→{a}" if b and a else " ｜ [反转节点]"
    return (f"- {e['event_id']}《{e['title']}》({e.get('event_time','')}; {e.get('confidence','')})——"
            f"{first_sents(e.get('description',''), cap=120)}{extra}")

L = []
L.append("# 迷深web版 · 事件时间线 AI 知识库(父子分段)")
L.append("")
L.append("> 父子分段: 父段=时间层/大章语境块; 子段=细粒度检索块(带 parent + source),source 指向 01_最终年表_全量_v5.md 或 full_event_list.json 的 event_id。")
L.append("> 检索口径: 子段内容为事件真实摘录(不虚构),按 confidence 分级;事件粒度全量见 01 年表,本库为时间线导航与要点检索。")
L.append("> 版本: v1.0 ｜ 生成: 2026-09-01 ｜ 事件总数 1568(T0=58/T1=123/T2=119/T4=45/T3=1223)")
L.append("")

# P00 总览
L.append("## 父段 P00 · 千年双时间线总览")
L.append("")
L.append("本作时间结构为『表层攻略进度+深层历史真相』双轨。千年前真相(涡波是迷宫始祖、阳滝是水之理、迷宫为完成守护者千年未竟愿望而建)与表层攻略线(涡波是一层苏醒的失忆少年)混成一体,检索时务必区分两个时间字段: story_time=叙事中被讲述的章节, event_time=实际发生的时代(T0/T1/T2/T4/T3)。")
L.append("")
L.append("| 层 | 名称 | 事件数 | 一句话 |")
L.append("|---|---|---|---|")
for Lk in ("T0", "T1", "T2", "T4", "T3"):
    pid, name, d = LAYER_META[Lk]
    n = sum(1 for e in fl if e["timeline_layer"] == Lk)
    L.append(f"| {pid} | {name} | {n} | {d} |")
L.append("")
L.append("### 子段 P00-1 · 核心反转轴速查 ｜ parent: P00 ｜ source: reversal_nodes.json")
L.append("")
axis_map = {}
for n in rev:
    ax = n.get("axis", 0)
    if ax:
        axis_map.setdefault(ax, []).append(n)
AXIS_NAME = {1: "涡波=千年前迷宫/莱文教始祖", 2: "迷宫本质=魔力污水处理厂", 3: "诺斯菲=涡波之女/妻·首个魔石人类",
             4: "缇亚=使徒西斯转世(独立个体)", 5: "技能???=使徒植入木马", 6: "阳滝=100层水之理盗窃者"}
for ax in sorted(axis_map):
    ns = axis_map[ax]
    ex = ns[0]
    L.append(f"- 轴{ax} {AXIS_NAME.get(ax,'')}: {len(ns)} 节点。例:{ex.get('event_id')}《{ex.get('title')}》{ex.get('before_belief','')}→{ex.get('after_truth','')}")
L.append("")

# 层父段
sid = 0
for Lk in ("T0", "T1", "T2", "T4"):
    pid, name, meta = LAYER_META[Lk]
    L.append(f"## 父段 {pid} · {name}")
    L.append("")
    L.append(meta)
    L.append("")
    for seg in agg["layers"][Lk]:
        sid += 1
        reps = seg_reps(seg, 6)
        n_rev = sum(1 for i in seg["event_ids"] if i in rev_by_ev)
        L.append(f"### 子段 {Lk}-{sid:03d} · {seg['seg_name']} ｜ parent: {pid} ｜ source: 01年表·{Lk}层 {len(seg['event_ids'])}事件")
        L.append("")
        L.append(f"概述: {seg['seg_desc']} ｜ 含事件 {len(seg['event_ids'])} 条,反转节点 {n_rev} 个。")
        L.append("")
        for e in reps:
            L.append(fmt_ev(e))
        L.append("")

# T3 章父段(合并到 P05~P10)
T3_segs = agg["layers"]["T3"]
chap_group = {}
for seg in T3_segs:
    pid, pname = T3_CHAP_PARENT.get(seg["seg_name"], ("P05", "其他"))
    chap_group.setdefault((pid, pname), []).append(seg)

# 生成 P05..P10 父段(按 pid 排序)
pid_order = ["P05", "P06", "P07", "P08", "P09", "P10"]
for pid in pid_order:
    items = [(pn, ss) for (p, pn), ss in chap_group.items() if p == pid]
    if not items: continue
    pname = items[0][0]
    chaps = [s["seg_name"] for _, ss in items for s in ss]
    n_ev = sum(len(s["event_ids"]) for _, ss in items for s in ss)
    L.append(f"## 父段 {pid} · {pname}")
    L.append("")
    L.append(f"覆盖章节: {'/'.join(chaps)} ｜ 共 {n_ev} 事件。")
    L.append("")
    for _, ss in items:
        for seg in ss:
            sid += 1
            reps = seg_reps(seg, 5)
            n_rev = sum(1 for i in seg["event_ids"] if i in rev_by_ev)
            L.append(f"### 子段 {seg['seg_name']} · {T3_CHAP_DESC.get(seg['seg_name'], seg['seg_desc'])} ｜ parent: {pid} ｜ source: 01年表·{seg['seg_name']} {len(seg['event_ids'])}事件")
            L.append("")
            L.append(f"概述: {T3_CHAP_DESC.get(seg['seg_name'], seg['seg_desc'])} ｜ 含事件 {len(seg['event_ids'])} 条,反转节点 {n_rev} 个。")
            L.append("")
            # 主线小目录: 章内话级节速览(方案第5项)
            from _交付_节映射 import chapter_sec_plan
            secs = chapter_sec_plan(seg["seg_name"], seg["event_ids"])
            if len(secs) > 1:
                L.append(f"章内分节({len(secs)}):")
                for sc in secs:
                    ev0 = sc["event_ids"][0] if sc["event_ids"] else ""
                    L.append(f"- {sc['sec_name']}({len(sc['event_ids'])}条, 起于 {ev0})")
                L.append("")
            for e in reps:
                L.append(fmt_ev(e))
            L.append("")

txt = "\n".join(L)
outp = os.path.join(DELIVER, "02_AI知识库_事件时间线_父子分段_v5.md")
open(outp, "w", encoding="utf-8").write(txt)
print("② written:", len(txt), "chars, lines:", txt.count("\n"))
