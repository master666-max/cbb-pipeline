# -*- coding: utf-8 -*-
"""S5 审计 + 重排: T0/T1/T2/T4 按真正时间轴排序
原则:
- 能数值化的(event_time 含新历X年/约T-X/西暦/年龄段) -> 数值键
- 模糊的(千年前/千年间/具体时点不详) -> 层内原序(event_id)兜底
- 输出: _审计_时间严谨性报告.md + 重排后 full_event_list.json
"""
import json, re, os
from collections import Counter

BASE = r"D:/DeepSeek Harness专用！危险！！！！！/迷深清洗工作2/年表输出"
FO = os.path.join(BASE, "final_output")
fl = json.load(open(os.path.join(FO,"full_event_list.json"), encoding="utf-8"))
byid = {e["event_id"]: e for e in fl}
report = []

ZH_NUM = {"零":0,"一":1,"二":2,"三":3,"四":4,"五":5,"六":6,"七":7,"八":8,"九":9,"十":10,"十一":11,"十二":12,"十三":13}

def newli_num(et):
    m = re.search(r"新历(零|一|二|三|四|五|六|七|八|九|十|十一|十二|十三|000?\d{1,3})年", et or "")
    if not m: return None
    s = m.group(1)
    if s in ZH_NUM: return ZH_NUM[s]
    try: return int(s)
    except: return None

def tminus_num(et):
    """约T-XXXX -> 数值; T-XXXX~YYYY 取中值? 不,取起点"""
    m = re.search(r"约?\s*T-(\d{3,4})", et or "")
    if m: return -int(m.group(1))
    return None

# ── T0 排序键: 年龄段/西暦 ──
T0_AGE = [
    ("幼年", 0), ("3岁", 0), ("童年", 1), ("小学", 2), ("中学", 3),
    ("少年", 4), ("学院", 5), ("青年", 6), ("病弱", 7), ("英才教育", 7),
    ("患病", 8), ("住院", 9), ("病床", 9), ("病房", 9), ("穿越前", 10), ("失踪前夕", 10),
    ("命运之日", 11), ("学院时代", 5),
]
def t0_key(e):
    et = e.get("event_time","") or ""
    if not et: return (99, 0, 0)
    m = re.search(r"西暦2012", et)
    if m: return (0, 0, 0)  # 2012 阳滝幼年, 最早
    for kw, v in T0_AGE:
        if kw in et: return (1, v, 0)
    return (2, 0, 0)  # 无法判定, 层内原序兜底

# ── T1/T2 排序键: 统一绝对轴(新历N ≈ T-1000+N; 约T-X = -X) ──
def t1_key(e):
    et = e.get("event_time","") or ""
    n = newli_num(et)
    if n is not None: return (0, -1000 + n, 0)  # 新历0年≈T-1000(异邦人被召唤年)
    tm = tminus_num(et)
    if tm is not None: return (0, tm, 0)
    if "召唤" in et or "穿越" in et: return (2, 0, 0)
    if "初期" in et: return (2, 1, 0)
    if "中期" in et or "战争期" in et: return (2, 2, 0)
    if "末期" in et or "终末" in et or "终局" in et: return (2, 3, 0)
    return (9, 0, 0)  # 兜底(层内原序)

def t2_key(e):
    et = e.get("event_time","") or ""
    m = re.search(r"第(\d+)日", et)
    if m: return (0, -1000 + int(m.group(1)), 0)
    n = newli_num(et)
    if n is not None: return (0, -1000 + n, 0)
    tm = tminus_num(et)
    if tm is not None: return (0, tm, 0)
    if "初期" in et or "第1日" in et or "数日后" in et: return (3, 0, 0)
    if "中期" in et: return (3, 1, 0)
    if "末期" in et or "完成前" in et or "前夕" in et: return (3, 2, 0)
    if "法尼亚" in et: return (4, 0, 0)
    return (9, 0, 0)

# ── T4 排序键: 相对千年位置 ──
def t4_key(e):
    et = e.get("event_time","") or ""
    tm = tminus_num(et)  # T-990 -> -990, T-0 -> 0; -990 < 0 正确(早->晚)
    if tm is not None: return (0, tm, 0)
    if "新历" in et:
        n = newli_num(et)
        return (1, n if n is not None else 1011, 0)
    if "末段" in et or "故事开始前" in et: return (2, 0, 0)
    if "早期" in et or "初期" in et: return (3, 0, 0)
    return (9, 0, 0)

KEYF = {"T0": t0_key, "T1": t1_key, "T2": t2_key, "T4": t4_key}

# 层内排序(同层内: 键 + 原 event_id 序兜底)
for L in ("T0","T1","T2","T4"):
    evs = [e for e in fl if e["timeline_layer"]==L]
    orig = {e["event_id"]: i for i, e in enumerate(evs)}
    keyed = sorted(evs, key=lambda e: (KEYF[L](e), orig[e["event_id"]]))
    # 统计键分布
    dist = Counter()
    for e in keyed:
        k = KEYF[L](e)
        dist[k[0]] += 1
    report.append(f"### {L}({len(evs)}条) 排序键分布: {dict(dist)}")
    # 检查重排后与原文序差异(有多少条位置变化)
    newpos = {e["event_id"]: i for i, e in enumerate(keyed)}
    moved = sum(1 for eid in orig if orig[eid] != newpos[eid])
    report.append(f"- 位置变动事件: {moved}/{len(evs)}")
    # 写回
    idx = {e["event_id"]: e for e in keyed}
    for e in fl:
        if e["timeline_layer"]==L:
            e.update(idx[e["event_id"]])

# 重排整个文件: 按 time_seq 层 + 层内已排顺序
layer_order = {"T0":0,"T1":1,"T2":2,"T4":3,"T3":4}
def full_key(e):
    return (layer_order.get(e["timeline_layer"],9), e.get("_s5seq", 0) if False else 0, e["event_id"])
# 由于 in-place update 打乱了层内顺序, 需重建: 按层分组, 每层用 keyed 顺序
newfl = []
for L in ("T0","T1","T2","T4","T3"):
    if L == "T3":
        # T3 已按 S4 排序, 保持 fl 中顺序
        newfl += [e for e in fl if e["timeline_layer"]=="T3"]
    else:
        evs = [e for e in fl if e["timeline_layer"]==L]
        newfl += sorted(evs, key=lambda e: (KEYF[L](e), {x["event_id"]: i for i,x in enumerate(evs)}[e["event_id"]]))

json.dump(newfl, open(os.path.join(FO,"full_event_list.json"),"w",encoding="utf-8"), ensure_ascii=False, indent=1)
for f in ("events_all.json","events_all_norm.json"):
    p = os.path.join(BASE,"_merged",f)
    if os.path.exists(p):
        json.dump(newfl, open(p,"w",encoding="utf-8"), ensure_ascii=False, indent=1)

# 审计报告
rep = ["# S5 时间轴审计与重排报告", "", "> T0/T1/T2/T4 层内重排(数值化排序键), 模糊事件按层内原序兜底", ""]
rep += report
rep.append("")
rep.append("## 重排后层序与计数")
from collections import Counter
cnt = Counter(e["timeline_layer"] for e in newfl)
rep.append(f"- 总数 {len(newfl)}: {dict(cnt)}")
rep.append("- 层序: T0→T1→T2→T4→T3(time_seq 0-4)")
open(os.path.join(BASE,"_审计_时间严谨性报告.md"),"w",encoding="utf-8").write("\n".join(rep))
print("S5 done:", len(newfl))
print("\n".join(report[:8]))
