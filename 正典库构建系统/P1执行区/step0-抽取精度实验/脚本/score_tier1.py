# -*- coding: utf-8 -*-
"""score_tier1.py — Tier 1 抽取对账评分（对金标 v3）
用法: py -X utf8 score_tier1.py <extraction.json> [--adjudication adjud.json]
输出: 结果/score-<name>.json + stdout 摘要（含待人工裁决清单）
匹配规则（保守自动匹配，其余进人工裁决队列）:
  实体: 规范化(去『』「」空格·)后 相等/包含(短侧≥2字) 且一一对应；aliases 扩展
  关系: 端点对按实体匹配规则配对；方向=抽取 source 是否对应金标 source
  时间: 金标表达式关键词是否出现在任一 fact/summary 中
"""
import json, os, sys, re

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
GOLD = os.path.join(ROOT, "金标", "gold-excerpt1.json")

def norm(s):
    return re.sub(r"[\s『』「」·•]+", "", s or "")

def name_set(e):
    names = [norm(e.get("name"))]
    for a in e.get("aliases", []):
        na = norm(re.sub(r"\(.*?\)", "", a))
        if na:
            names.append(na)
    return [n for n in names if n]

def match_names(g, x):
    """gold 名称集合 vs 抽取名称：相等或包含(短侧>=2字)"""
    for gn in g:
        if not gn:
            continue
        for xn in x:
            if not xn:
                continue
            if gn == xn:
                return "exact"
            short = gn if len(gn) <= len(xn) else xn
            if len(short) >= 2 and (gn in xn or xn in gn):
                return "contain"
    return None

def main():
    ext_path = sys.argv[1]
    adj_path = None
    if "--adjudication" in sys.argv:
        adj_path = sys.argv[sys.argv.index("--adjudication") + 1]
    name = re.sub(r"\.json$", "", os.path.basename(ext_path))
    m = re.search(r"excerpt\d+", name)
    gold_name = m.group(0) if m else "excerpt1"
    GOLD = os.path.join(ROOT, "金标", f"gold-{gold_name}.json")

    gold = json.load(open(GOLD, encoding="utf-8"))
    ext = json.load(open(ext_path, encoding="utf-8"))
    g_ents, g_edges, g_times = gold["entities"], gold["edges"], gold["time_expressions"]
    x_ents = ext.get("entities", [])
    for x in x_ents:  # schema 归一化：graphiti 原生模板实体键为 entity
        if not x.get("name") and x.get("entity"):
            x["name"] = x["entity"]
    x_edges = ext.get("edges", [])

    adj = json.load(open(adj_path, encoding="utf-8")) if adj_path else {}
    ent_over = adj.get("entity_matches", [])   # [[gold_name, ext_name], ...]
    edge_over = adj.get("edge_matches", [])    # [[gold_idx, ext_idx, "forward"|"swapped"], ...]
    ent_rej = set(map(tuple, adj.get("entity_auto_reject", [])))
    edge_rej = set(map(tuple, adj.get("edge_auto_reject", [])))

    # ---------- 实体 ----------
    pairs = []
    for gi, g in enumerate(g_ents):
        gnames = name_set(g)
        for xi, x in enumerate(x_ents):
            if (gi, xi) in ent_rej:
                continue
            m = match_names(gnames, [norm(x.get("name"))])
            if m:
                pairs.append((gi, xi, m))
    # 一一对应：exact 优先，contain 次之
    pairs.sort(key=lambda p: 0 if p[2] == "exact" else 1)
    used_g, used_x, matched = set(), set(), []
    for gi, xi, m in pairs:
        if gi in used_g or xi in used_x:
            continue
        matched.append((gi, xi, m))
        used_g.add(gi); used_x.add(xi)
    # 人工裁决补充
    for gn, xn in ent_over:
        gi = next((i for i, e in enumerate(g_ents) if norm(e["name"]) == norm(gn)), None)
        xi2 = next((i for i, e in enumerate(x_ents) if norm(e.get("name")) == norm(xn)), None)
        if gi is not None and xi2 is not None and gi not in used_g:
            matched.append((gi, xi2, "manual"))
            used_g.add(gi); used_x.add(xi2)
    TP_e = len(matched)
    FN_e = [{"gold": g_ents[gi]["name"], "line": g_ents[gi].get("evidence")} for gi in range(len(g_ents)) if gi not in used_g]
    FP_e = [{"name": x_ents[xi].get("name"), "type": x_ents[xi].get("type"), "summary": (x_ents[xi].get("summary") or "")[:80]}
            for xi in range(len(x_ents)) if xi not in used_x]
    P_e = TP_e / (TP_e + len(FP_e)) if (TP_e + len(FP_e)) else 0
    R_e = TP_e / (TP_e + len(FN_e)) if (TP_e + len(FN_e)) else 0

    # ---------- 关系（索引对索引匹配） ----------
    g_name_to_idx = {}
    for i, e in enumerate(g_ents):
        for n in name_set(e):
            g_name_to_idx.setdefault(n, i)
    x_name_to_idx = {}
    for i, e in enumerate(x_ents):
        for n in name_set(e):
            x_name_to_idx.setdefault(n, i)
    def res(d, name):
        n = norm(name)
        if n in d:
            return d[n]
        for dn, di in d.items():
            short = min(n, dn, key=len)
            if len(short) >= 2 and (n in dn or dn in n):
                return di
        return None
    g2x = {gi: xi for gi, xi, m in matched}  # 金标实体→抽取实体 的既定配对
    e_pairs = []
    for gi, ge in enumerate(g_edges):
        gi_s = res(g_name_to_idx, ge["source"])
        gi_t = res(g_name_to_idx, ge["target"])
        xi_s = g2x.get(gi_s) if gi_s is not None else None
        xi_t = g2x.get(gi_t) if gi_t is not None else None
        if xi_s is None or xi_t is None:
            continue
        for xi, xe in enumerate(x_edges):
            if (gi, xi) in edge_rej:
                continue
            # 兼容两种边 schema：GLM 用 source/target，graphiti 原生模板用 source_entity_name/target_entity_name
            xs = xe.get("source") or xe.get("source_entity_name")
            xt = xe.get("target") or xe.get("target_entity_name")
            xi_s2 = res(x_name_to_idx, xs)
            xi_t2 = res(x_name_to_idx, xt)
            if xi_s2 is None or xi_t2 is None:
                continue
            if (xi_s2, xi_t2) == (xi_s, xi_t):
                e_pairs.append((gi, xi, "forward")); break
            if (xi_s2, xi_t2) == (xi_t, xi_s):
                e_pairs.append((gi, xi, "swapped")); break
    used_ge, used_xe, e_matched = set(), set(), []
    for gi, xi, d in sorted(e_pairs, key=lambda p: 0 if p[2] == "forward" else 1):
        if gi in used_ge or xi in used_xe:
            continue
        e_matched.append((gi, xi, d)); used_ge.add(gi); used_xe.add(xi)
    for gj, xj, d in edge_over:
        if gj not in used_ge:
            e_matched.append((gj, xj, d)); used_ge.add(gj); used_xe.add(xj)
    fwd = sum(1 for _, _, d in e_matched if d in ("forward", "manual"))
    swap = sum(1 for _, _, d in e_matched if d == "swapped")
    TP_r = len(e_matched)
    FN_r = [{"gold": f'{g_edges[gi]["source"]} -{g_edges[gi]["relation"]}-> {g_edges[gi]["target"]}',
             "claim": g_edges[gi].get("claim"), "evidence": g_edges[gi].get("evidence")}
            for gi in range(len(g_edges)) if gi not in used_ge]
    FP_r = [{"fact": (xe.get("fact") or "")[:100]} for xi, xe in enumerate(x_edges) if xi not in used_xe]
    dir_acc = fwd / TP_r if TP_r else 0
    P_r = TP_r / (TP_r + len(FP_r)) if (TP_r + len(FP_r)) else 0
    R_r = TP_r / (TP_r + len(FN_r)) if (TP_r + len(FN_r)) else 0

    # ---------- 时间表述可用率 ----------
    facts_blob = " ".join([(xe.get("fact") or "") for xe in x_edges] + [(x.get("summary") or "") for x in x_ents])
    time_keys = {"隔了一次休息": "休息", "第一天结识克劳": "第一天", "到休息时间为止": "休息时间",
                 "休息时同席": "休息", "这几天忙碌": "这几天", "第一天见的少女": "第一天",
                 "每天每日念叨": "每天", "之前接触帕林库洛": "帕林库洛", "带玛利亚升级": "升级",
                 "这几天没见过她": "这几天"}
    t_detail = []
    for te in g_times:
        key = time_keys.get(te["text"], te["text"][:4])
        t_detail.append({"text": te["text"], "key": key, "preserved": key in facts_blob})
    T_used = sum(1 for t in t_detail if t["preserved"])
    T_rate = T_used / len(g_times) if g_times else 0

    out = {"name": name,
           "metrics": {"entity_P": round(P_e, 3), "entity_R": round(R_e, 3), "entity_TP": TP_e,
                       "entity_FP": len(FP_e), "entity_FN": len(FN_e),
                       "relation_matched": TP_r, "relation_dir_acc": round(dir_acc, 3),
                       "relation_swapped": swap, "relation_P": round(P_r, 3), "relation_R": round(R_r, 3),
                       "relation_FP": len(FP_r), "relation_FN": len(FN_r),
                       "time_usability": round(T_rate, 3), "time_used": T_used, "time_total": len(g_times)},
           "entity_FN": FN_e, "entity_FP": FP_e,
           "relation_matched_detail": [{"gold": f'{g_edges[gi]["source"]} -{g_edges[gi]["relation"]}-> {g_edges[gi]["target"]}',
                                        "ext_fact": (x_edges[xi].get("fact") or "")[:80], "dir": d}
                                       for gi, xi, d in e_matched],
           "relation_FN": FN_r, "relation_FP": FP_r,
           "time_detail": t_detail}
    op = os.path.join(ROOT, "结果", f"score-{name}.json")
    with open(op, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(json.dumps(out["metrics"], ensure_ascii=False, indent=1))
    print(f"entity_FN: {[f['gold'] for f in out['entity_FN']]}")
    print(f"relation_FN count={len(FN_r)}; relation_FP count={len(FP_r)} -> 见 {op}")

if __name__ == "__main__":
    main()
