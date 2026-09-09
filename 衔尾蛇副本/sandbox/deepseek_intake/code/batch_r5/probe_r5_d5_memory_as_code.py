# -*- coding: utf-8 -*-
"""probe_r5_d5_memory_as_code.py — D5: 记忆即程序(受控规则条目)
记忆条目可携带受限规则(白名单词表, 能力面限制), 检索时执行:
  vocab = {drop_obsolete, fresh_only, boost_kw}。世界 stale(纠错后旧条目是噪声)。
臂: facts-only(纯事实检索) vs facts+rules(引擎可提案规则条目, 只增不减, 深度<=1, 能力面=引擎不能写词表外 token)。
度量: 真值 recall、规则采纳数、安全不变量(无循环/深度越界=0)。
"""
import sys, os, json, time, pathlib, statistics, random
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE.parent))
import world_gen as wg
import engine_gate as eg

OUT = HERE / "out_r5_d5"
OUT.mkdir(parents=True, exist_ok=True)
VOCAB = {"drop_obsolete", "fresh_only", "boost_kw"}


def apply_rules(entries, rules):
    """返回排序后列表(规则作用于检索集合): 每规则 {kind: ...} 白名单"""
    out = list(entries)
    for rule in rules:
        kind = rule.get("kind")
        if kind not in VOCAB:
            continue   # 能力面: 词表外忽略
        if kind == "drop_obsolete":
            out = [e for e in out if not (e.get("obsolete_gen") is not None and e["obsolete_gen"] <= 99)]
        elif kind == "fresh_only":
            out = [e for e in out if e.get("age_days", 999) < 120]
    return out


def util_with(entries, rules, qs, cfg, gen):
    act = apply_rules(entries, rules)
    return eg.measure(act, qs, cfg, gen, "rv")


def run(w, arm, seed, gens):
    entries = w["entries"]
    rng = random.Random(seed * 7 + 11)
    trq = w.get("train") or w.get("trainA")
    holdq = w["hold"]
    audq = w["audit"]
    rules = []
    cfg = dict(eg.V3_DEFAULT)
    margin = eg.MARGIN0
    adopts = rule_adopts = 0
    depth_viol = 0
    for g in range(gens):
        # 规则提案(仅当世界有可发现结构特征: 过期比例高)
        if arm == "facts-rules" and g % 4 == 0 and len(rules) < 2:
            cand_kind = rng.choice(sorted(VOCAB))
            trial = rules + [{"kind": cand_kind}]
            u0 = util_with(entries, rules, trq, cfg, g)
            u1 = util_with(entries, trial, trq, cfg, g)
            if u1 >= u0 + eg.MARGIN0 * 2:   # 显著才采纳(宽松)
                rules = trial
                rule_adopts += 1
        tr0 = eg.measure(entries, trq, cfg, g, "imp")
        ho0 = eg.measure(entries, holdq, cfg, g, "rv")
        best, bd = None, 0.0
        for _ in range(4):
            c = eg.mutate(rng, cfg)
            dt = eg.measure(entries, trq, c, g, "imp") - tr0
            dh = eg.measure(entries, holdq, c, g, "rv") - ho0
            if dt > margin and dh > margin and dt > bd:
                best, bd = c, dt
        if best is not None:
            cfg = dict(best)
            adopts += 1
    gf = gens - 1
    T_r = util_with(entries, rules, audq, cfg, gf)
    T0 = eg.measure(entries, audq, cfg, gf, "rv")
    # 安全不变量: 规则数/词表合法/无递归(实现无递归)
    safe = all(rule["kind"] in VOCAB for rule in rules)
    return {"mode": arm, "T_final": round(T_r if arm == "facts-rules" else T0, 4),
            "T_wo_rules": round(T0, 4), "rules": [x["kind"] for x in rules],
            "rule_adopts": rule_adopts, "adopts": adopts, "safe": safe, "depth_viol": depth_viol}


rows = []
for seed in range(1, 7):
    w = wg.build_world("stale", seed)
    for arm in ["facts-only", "facts-rules"]:
        r = run(w, arm, seed, 20)
        r.update({"seed": seed})
        rows.append(r)
(OUT / "rows_d5.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
print("%-11s %9s %9s %8s %7s %8s" % ("arm", "T_final", "T_wo_rules", "ruleAdopt", "adopt", "safe"))
for arm in ["facts-only", "facts-rules"]:
    rs = [r for r in rows if r["mode"] == arm]
    print("%-11s %9.4f %9.4f %8.1f %7.1f %8s" % (
        arm, statistics.mean(r["T_final"] for r in rs),
        statistics.mean(r["T_wo_rules"] for r in rs),
        statistics.mean(r["rule_adopts"] for r in rs),
        statistics.mean(r["adopts"] for r in rs),
        all(r["safe"] for r in rs)))
print("采纳的规则样本:", sorted(set(x for r in rows if r["mode"] == "facts-rules" for x in r["rules"])))
print("[D5] out_r5_d5 done");
