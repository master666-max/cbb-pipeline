# -*- coding: utf-8 -*-
"""P10 final_output 七件套落盘：JSON + YAML 双格式 + Markdown 汇总。

七件套：
1. timeline_index    双线对照表（T1/T2 千年前 vs T3 现世,按 story_anchor 章节并排）
2. full_event_list   完整事件列表（P5 排序后,含全部字段）
3. foreshadow_chains 伏笔链（P6 产物）
4. reversal_nodes    反转节点（P7 产物）
5. incantation_links 咏唱-事件关联（P8 产物）
6. conflict_report   冲突消解报告（P9 产物）
7. confidence_stats  置信度统计
"""
import os, json, re, yaml
from collections import Counter

BASE = r"D:/DeepSeek Harness专用！危险！！！！！/迷深清洗工作2/年表输出"
MERGED = os.path.join(BASE, "_merged")
TMP = os.path.join(BASE, "_tmp_全")
OUT = os.path.join(BASE, "final_output")
os.makedirs(OUT, exist_ok=True)

def load(p):
    return json.load(open(p, encoding="utf-8"))

def save_json(name, obj):
    with open(os.path.join(OUT, name + ".json"), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)

def save_yaml(name, obj):
    with open(os.path.join(OUT, name + ".yaml"), "w", encoding="utf-8") as f:
        yaml.safe_dump(obj, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

# ── 基础数据
events = load(os.path.join(MERGED, "events_all_norm.json"))
print("events:", len(events))

# ── 1. timeline_index: 双线对照
# 章节来源: _merged/event_chapter_map.json（P5 从源文件名提取）优先,
# 兜底从 story_anchor 正则提取（早期章节「话:第X章-」格式）。
CHAP_RE = re.compile(r"(第十章|第九章|第八章|第7-[123]章|第六章|第五章|第四章|第三章|第二章|第一章)")
try:
    chap_map = load(os.path.join(MERGED, "event_chapter_map.json"))
except Exception:
    chap_map = {}
def chap_of(e):
    c = chap_map.get(e.get("event_id"))
    if c and c != "未知":
        return c
    m = CHAP_RE.search(e.get("story_anchor", "") or "")
    return m.group(1) if m else "未知"
chap_order = ["第一章","第二章","第三章","第四章","第五章","第六章","第7-1章","第7-2章","第7-3章","第八章","第九章","第十章"]
timeline_index = []
for ch in chap_order:
    ch_events = [e for e in events if chap_of(e) == ch]
    if not ch_events:
        continue
    ancient = [e for e in ch_events if e.get("timeline_layer") in ("T1","T2")]
    modern = [e for e in ch_events if e.get("timeline_layer") == "T3"]
    tl0 = [e for e in ch_events if e.get("timeline_layer") == "T0"]
    tl4 = [e for e in ch_events if e.get("timeline_layer") == "T4"]
    timeline_index.append({
        "chapter": ch,
        "story_anchor_range": f"{ch_events[0].get('story_anchor','')} ~ {ch_events[-1].get('story_anchor','')}",
        "T1_T2_千年前线": [{"event_id": e["event_id"], "title": e.get("title","")} for e in ancient],
        "T3_现世线": [{"event_id": e["event_id"], "title": e.get("title","")} for e in modern],
        "T0_原世界": [{"event_id": e["event_id"], "title": e.get("title","")} for e in tl0],
        "T4_千年间": [{"event_id": e["event_id"], "title": e.get("title","")} for e in tl4],
    })

# ── 2. full_event_list
full_event_list = events

# ── 3. foreshadow_chains (P6)
raw6 = load(os.path.join(TMP, "_p6_chains.json"))
chains_summary = None
foreshadow_chains = []
for item in raw6:
    if isinstance(item, dict) and "summary" in item:
        chains_summary = item["summary"]
    elif isinstance(item, dict) and "chain_id" in item:
        foreshadow_chains.append(item)
    elif isinstance(item, list):
        foreshadow_chains.extend(item)
# 保险: 若数组元素直接是链对象
if not foreshadow_chains:
    for item in raw6:
        if isinstance(item, dict) and item.get("chain_id"):
            foreshadow_chains.append(item)

# ── 4. reversal_nodes (P7)
raw7 = load(os.path.join(TMP, "_p7_nodes.json"))
rev_summary = None
reversal_nodes = []
for item in raw7:
    if isinstance(item, dict) and "summary" in item:
        rev_summary = item["summary"]
    elif isinstance(item, dict) and "node_id" in item:
        reversal_nodes.append(item)
    elif isinstance(item, list):
        reversal_nodes.extend(item)
if not reversal_nodes:
    for item in raw7:
        if isinstance(item, dict) and item.get("node_id"):
            reversal_nodes.append(item)

# ── 5. incantation_links (P8)
raw8 = load(os.path.join(TMP, "_p8_links.json"))
inc_summary = None
incantation_links = []
for item in raw8:
    if isinstance(item, dict) and "summary" in item:
        inc_summary = item["summary"]
    elif isinstance(item, dict) and "link_id" in item:
        incantation_links.append(item)
    elif isinstance(item, list):
        incantation_links.extend(item)
if not incantation_links:
    for item in raw8:
        if isinstance(item, dict) and item.get("link_id"):
            incantation_links.append(item)

# ── 6. conflict_report (P9)
conflict_report = load(os.path.join(OUT, "conflict_report.json"))

# ── 7. confidence_stats
conf_stats = Counter(e.get("confidence", "未知") for e in events)
layer_stats = Counter(e.get("timeline_layer") for e in events)
type_stats = Counter(e.get("event_type") for e in events)
confidence_stats = {
    "total_events": len(events),
    "by_confidence": dict(conf_stats.most_common()),
    "by_timeline_layer": {k: layer_stats.get(k, 0) for k in ["T0","T1","T2","T4","T3"]},
    "by_event_type": dict(type_stats.most_common()),
    "foreshadow_chains_closed": sum(1 for c in foreshadow_chains if c.get("status") == "closed"),
    "foreshadow_chains_open": sum(1 for c in foreshadow_chains if c.get("status") == "open"),
    "reversal_nodes_total": len(reversal_nodes),
    "incantation_links_total": len(incantation_links),
    "incantation_matched": sum(1 for l in incantation_links if l.get("status") == "matched"),
    "incantation_unmatched": sum(1 for l in incantation_links if l.get("status") == "unmatched"),
}

# ── 落盘: JSON + YAML
pieces = {
    "timeline_index": timeline_index,
    "full_event_list": full_event_list,
    "foreshadow_chains": foreshadow_chains,
    "reversal_nodes": reversal_nodes,
    "incantation_links": incantation_links,
    "conflict_report": conflict_report,
    "confidence_stats": confidence_stats,
}
for name, obj in pieces.items():
    save_json(name, obj)
    save_yaml(name, obj)
    print(f"{name}: json+yaml written")

# ── Markdown 汇总
md = []
md.append("# 迷深事件年表 final_output 汇总\n")
md.append(f"> 生成日期:2026-09-01 ｜ 事件总数:**{len(events)}** ｜ 时间线五层:T0={layer_stats.get('T0',0)} T1={layer_stats.get('T1',0)} T2={layer_stats.get('T2',0)} T4={layer_stats.get('T4',0)} T3={layer_stats.get('T3',0)}\n")
md.append("## 七件套清单\n")
md.append("| 件 | 文件 | 内容 | 规模 |")
md.append("|---|---|---|---|")
md.append(f"| 1 | timeline_index.json/yaml | 双线对照表(T1/T2 千年前 vs T3 现世,按章节并排) | {len(timeline_index)} 章 |")
md.append(f"| 2 | full_event_list.json/yaml | 完整事件列表(千年序排序) | {len(full_event_list)} 条 |")
md.append(f"| 3 | foreshadow_chains.json/yaml | 伏笔链 | {len(foreshadow_chains)} 链 |")
md.append(f"| 4 | reversal_nodes.json/yaml | 反转节点 | {len(reversal_nodes)} 节点 |")
md.append(f"| 5 | incantation_links.json/yaml | 咏唱-事件关联 | {len(incantation_links)} 关联 |")
md.append(f"| 6 | conflict_report.json/yaml | 冲突消解报告 | {len(conflict_report.get('items',[]))} 条 + {len(conflict_report.get('residual_review',[]))} 复核 |")
md.append(f"| 7 | confidence_stats.json/yaml | 置信度统计 | — |\n")
md.append("## confidence_stats 摘要\n")
md.append(f"- 原文明确:{conf_stats.get('原文明确',0)} ｜ 合理推断:{conf_stats.get('合理推断',0)} ｜ AI推算:{conf_stats.get('AI推算',0)}\n")
md.append("## event_type 分布\n")
for t, n in type_stats.most_common():
    md.append(f"- {t}: {n}")
md.append("\n## 伏笔链状态\n")
md.append(f"- closed:{sum(1 for c in foreshadow_chains if c.get('status')=='closed')} ｜ open:{sum(1 for c in foreshadow_chains if c.get('status')=='open')}")
md.append("\n## 反转节点 axis 分布\n")
axis_cnt = Counter(n.get("axis") for n in reversal_nodes)
for a in sorted(axis_cnt, key=lambda x: (x is not None, str(x))):
    md.append(f"- axis{a}: {axis_cnt[a]}")
md.append("\n## 咏唱关联状态\n")
md.append(f"- matched:{sum(1 for l in incantation_links if l.get('status')=='matched')} ｜ unmatched:{sum(1 for l in incantation_links if l.get('status')=='unmatched')}")
md.append("\n## P9 未决项(待人工复核)\n")
for r in conflict_report.get("residual_review", []):
    md.append(f"- {r.get('event_id')}: {r.get('note','')}")
for it in conflict_report.get("items", []):
    if not it.get("resolved"):
        md.append(f"- [P9-{it.get('issue_id')}] {it.get('topic')}: {it.get('decision','')} (confidence={it.get('confidence')})")
md.append("\n---\n*由 P1–P10 全流程自动生成,事件可经 story_anchor 回溯原文。*")
with open(os.path.join(OUT, "README_汇总.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(md))
print("README_汇总.md written")

# 打印确认
print("\n=== 确认 ===")
print("timeline_index 章节数:", len(timeline_index))
print("foreshadow_chains:", len(foreshadow_chains), "closed:", sum(1 for c in foreshadow_chains if c.get('status')=='closed'))
print("reversal_nodes:", len(reversal_nodes))
print("incantation_links:", len(incantation_links))
print("conflict_report items:", len(conflict_report.get('items', [])))