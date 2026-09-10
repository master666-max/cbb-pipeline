# -*- coding: utf-8 -*-
"""engine_gate.py — V2 演化引擎: 参数化检索 + 两级门控 + Pareto 档案 + margin/停摆 + 真值抽样审计

检索计分为 _rank_entries(L899-914) 的显式参数化同构(见 lib_bridge.parity_check 等价门)。
"""
import random, time

from world_gen import K_GOLD

V3_DEFAULT = {"w_kw": 3.0, "w_content": 1.0, "w_imp": 1.0, "w_age": 0.1, "filter_zero": 0}
GENE_KEYS = ["w_kw", "w_content", "w_imp", "w_age"]
LINKS_GAIN = 0.5
MARGIN0 = 0.020
TOL_ARCH = 0.040
CAP_PARETO = 8
STALL_GEN = 5
AUDIT_EVERY = 3
REVERT_THR = 0.03
K_TOPK = 5


def age_days_of(created_at):
    try:
        return (time.time() - time.mktime(time.strptime(created_at[:10], "%Y-%m-%d"))) / 86400.0
    except Exception:
        return 0.0


def retrieve_top(entries, qtext, cfg, k=K_TOPK):
    """转写 b3._rank_entries: kw*3+c+imp-age + links 一跳扩散; 返回 [(score, entry)] 降序"""
    scored = {}
    for e in entries:
        if e.get("validity", {}).get("t_invalid"):
            continue
        c = e["content"]
        kw_join = " ".join(e.get("keywords", []))
        qwords = qtext.split()
        kw_hit = sum(1 for w in qwords if w in kw_join)
        c_hit = sum(1 for w in qwords if w in c)
        if kw_hit:
            c_hit = max(c_hit, 1)
        s = (kw_hit * cfg["w_kw"] + c_hit * cfg["w_content"]
             + e.get("importance", 0.0) * cfg["w_imp"]
             - age_days_of(e.get("created_at", "")) * cfg["w_age"])
        if cfg.get("filter_zero") and kw_hit == 0 and c_hit == 0:
            s = float("-inf")
        scored[e["id"]] = (s, e)
    for fid, (s, e) in list(scored.items()):
        if s <= 0 or s == float("-inf"):
            continue
        for link in e.get("links", []):
            lid = str(link).strip("[]")
            if lid in scored:
                le = scored[lid][1]
                qwords = qtext.split()
                hit_q = any(w and w in (le["content"] + " ".join(le.get("keywords", []))) for w in qwords)
                if not hit_q:
                    scored[lid] = (scored[lid][0] + s * LINKS_GAIN, le)
    ranked = sorted(scored.items(), key=lambda kv: (-kv[1][0], kv[0]))
    return [(fid, s, e) for fid, (s, e) in ranked[:k]]


def gold_ids_at(entries, q, gen, by):
    pool = []
    for e in entries:
        if e["topic"] != q["topic"]:
            continue
        if e["birth_gen"] > gen:
            continue
        if e.get("obsolete_gen") is not None and e["obsolete_gen"] <= gen:
            continue
        if e.get("role") in GOLD_EXCLUDE:
            continue
        pool.append(e)
    if by == "imp":
        pool.sort(key=lambda x: -x["importance"])
    else:
        pool.sort(key=lambda x: -x["rv"])
    return [e["id"] for e in pool[:K_GOLD]]


def measure(entries, qs, cfg, gen, by):
    if not qs:
        return 0.0
    tot = 0.0
    for q in qs:
        top = retrieve_top(entries, q["topic"], cfg)
        ids = [fid for fid, _s, _e in top]
        gold = set(gold_ids_at(entries, q, gen, by))
        hit = sum(1 for i in ids if i in gold)
        tot += hit / min(K_GOLD, K_TOPK)
    return tot / len(qs)


MUTATE_ZERO = 0.0   # >0 时: 变异有小概率把单个连续基因直接置 0(越过阶跃阈值, E7 谷测试用)
GOLD_EXCLUDE = set()  # 金标排除角色(如 dup): 世界声明组级真值时用; run_arm 每次运行按 world 重设


def _toks(e):
    return set(str(e["content"]).split())


def _jaccard(a, b):
    x, y = _toks(a), _toks(b)
    if not x or not y:
        return 0.0
    return len(x & y) / len(x | y)


def detect_redundant(entries):
    """可发现的近似重复簇: e.links 指向同 topic 的存活条目且内容 Jaccard>=0.5 -> 副本(可 retire, 首领保留)"""
    alive = {e["id"]: e for e in entries}
    by_target = {}
    for e in entries:
        for link in e.get("links", []):
            lid = str(link).strip("[]")
            if lid in alive and alive[lid]["topic"] == e["topic"] and _jaccard(e, alive[lid]) >= 0.5:
                by_target.setdefault(lid, []).append(e["id"])
    return by_target


def redundancy(entries, qs, cfg, gen, k=K_TOPK):
    """top-k 内容冗余度: 各查询返回集内两两 token Jaccard 的均值(重组质量轴)"""
    if not qs:
        return 0.0
    tot = 0.0
    cnt = 0
    for q in qs:
        top = retrieve_top(entries, q["topic"], cfg, k)
        ids = [fid for fid, _s, _e in top]
        byid = {e["id"]: e for e in entries}
        toks = [_toks(byid[i]) for i in ids if i in byid]
        if len(toks) < 2:
            continue
        s = 0.0
        n = 0
        for i in range(len(toks)):
            for j in range(i + 1, len(toks)):
                x, y = toks[i], toks[j]
                if not x or not y:
                    continue
                s += len(x & y) / len(x | y)
                n += 1
        if n:
            tot += s / n
            cnt += 1
    return tot / cnt if cnt else 0.0


def _gene_keys(cfg):
    keys = [k for k in GENE_KEYS if k in cfg]
    if "w_show" in cfg:
        keys.append("w_show")
    return keys


def mutate(rng, cfg, step_scale=0.3):
    c = dict(cfg)
    keys = _gene_keys(cfg)
    coin = rng.random()
    if coin < 0.10:
        c["filter_zero"] = 1 - c.get("filter_zero", 0)
    elif MUTATE_ZERO > 0 and coin < 0.10 + MUTATE_ZERO:
        k = rng.choice(keys)
        c[k] = 0.0
    elif coin < 0.90:
        k = rng.choice(keys)
        c[k] = max(0.0, c[k] * (1 + rng.uniform(-step_scale, step_scale)))
    else:
        for k in keys:
            c[k] = max(0.0, c[k] * (1 + rng.uniform(-0.1, 0.1)))
    return c


def _pareto(cfgs, entries, train_q, hold_q, gen):
    pts = [(c, measure(entries, train_q, c, gen, "imp"),
            measure(entries, hold_q, c, gen, "rv")) for c in cfgs]
    keep = []
    for i in range(len(pts)):
        dominated = False
        for j in range(len(pts)):
            if i == j:
                continue
            if pts[j][1] > pts[i][1] and pts[j][2] > pts[i][2]:
                dominated = True
                break
        if not dominated:
            keep.append(cfgs[i])
    return keep or [cfgs[0]]


def _pareto_cap(cfgs, entries, capA, capB, gen):
    """档案按双能力轴(A/B 两阶段真值)保留 Pareto 前沿 —— E16 防灾难性遗忘机制"""
    pts = []
    for c in cfgs:
        ua = measure(entries, capA, c, gen, "rv") if capA else 0.0
        ub = measure(entries, capB, c, gen, "rv") if capB else 0.0
        pts.append((c, ua, ub))
    keep = []
    for i in range(len(pts)):
        dominated = False
        for j in range(len(pts)):
            if i == j:
                continue
            if pts[j][1] > pts[i][1] and pts[j][2] > pts[i][2]:
                dominated = True
                break
        if not dominated:
            keep.append(cfgs[i])
    return keep or [cfgs[0]]


def _best_cap(cfgs, entries, cap_q, gen):
    if not cap_q or not cfgs:
        return None
    return max(measure(entries, cap_q, c, gen, "rv") for c in cfgs)


def run_arm(world, arm, seed, gens, audit_on=True, pareto_on=True,
            margin_override=None, quick=False, pareto_mode="trainhold"):
    global GOLD_EXCLUDE
    GOLD_EXCLUDE = set(world.get("gold_exclude_roles") or [])
    entries = list(world["entries"])   # 本地可变工作集: gated-row 的 retire 提案直接移除冗余副本
    rng = random.Random(seed * 7919 + 17)
    train_phaseA = world.get("trainA") or world.get("train")
    train_phaseB = world.get("trainB")
    hold_q = world["hold"]
    audit_q = world["audit"]
    gens_eff = gens
    if quick:
        gens_eff = max(6, int(gens * 0.6))
    if world.get("phaseA") is not None and gens_eff <= 6:
        ga = max(2, gens_eff // 2)
    else:
        ga = world.get("switch_ga") or max(2, int(gens_eff * 2 / 3))

    def train_now(g):
        if train_phaseB is not None:
            return train_phaseA if g < ga else train_phaseB
        return train_phaseA

    def final_metrics(cfg):
        g = gens_eff - 1
        u = {"u_trainA": measure(entries, train_phaseA, cfg, g, "imp")}
        if train_phaseB is not None:
            u["u_trainB"] = measure(entries, train_phaseB, cfg, g, "imp")
        u["u_hold"] = measure(entries, hold_q, cfg, g, "rv")
        u["u_audit"] = measure(entries, audit_q, cfg, g, "rv")
        u["uA_true"] = measure(entries, train_phaseA, cfg, g, "rv") if world.get("phaseA") else None
        return u

    if arm == "static":
        cfg = dict(V3_DEFAULT)
        u = final_metrics(cfg)
        capA = world.get("trainA")
        capB = world.get("trainB")
        u["bestA_true"] = _best_cap([cfg], entries, capA, gens_eff - 1)
        u["bestB_true"] = _best_cap([cfg], entries, capB, gens_eff - 1)
        u["redun_hold"] = redundancy(entries, hold_q, cfg, gens_eff - 1)
        return {"mode": arm, "final_cfg": dict(cfg), "adopts": 0, "audit_dips": 0,
                "rollbacks": 0, "stall_events": 0, "arch_final": 1, "eval_units": 1,
                "ops_applied": 0, "ops_rejected": 0, "n_removed": 0,
                "gens_eff": gens_eff, "traj": [{"gen": 0, "cfg": dict(cfg)}], **u}

    mainline = dict(V3_DEFAULT)
    margin = MARGIN0 if margin_override is None else margin_override
    archive = [dict(mainline)]
    adopts = stall = audit_dips = rollbacks = stall_events = 0
    ops_applied = 0
    ops_rejected = 0
    removed_ids = []
    last_check = None
    traj = []

    for g in range(gens_eff):
        tn = train_now(g)
        if arm in ("bare", "single"):
            # bare: 单主线只看训练集(judge), Δ>0 即采纳; single: 单主线但要 hold(真值)也过 margin
            gate_hold = (arm == "single")
            u_mn_train = measure(entries, tn, mainline, g, "imp")
            u_mn_hold = measure(entries, hold_q, mainline, g, "rv")
            best, best_du = None, 0.0
            for _ in range(3):
                c = mutate(rng, mainline)
                du = measure(entries, tn, c, g, "imp") - u_mn_train
                du_ho = measure(entries, hold_q, c, g, "rv") - u_mn_hold
                ok = du > 0 if not gate_hold else (du > margin and du_ho > margin)
                if ok and du_ho > best_du:
                    best, best_du = c, du_ho
            if best is not None:
                mainline = dict(best)
                adopts += 1
                stall = 0
            else:
                stall += 1
                if stall >= STALL_GEN and gate_hold:
                    margin = max(0.005, margin * 0.5)
                    stall = 0
                    stall_events += 1
            events = []
            if audit_on and (g % AUDIT_EVERY == 0 or g == gens_eff - 1):
                u_aud = measure(entries, audit_q, mainline, g, "rv")
                if last_check is not None and u_aud < last_check[1] - REVERT_THR:
                    audit_dips += 1
                    if last_check[0] is not None:
                        mainline = dict(last_check[0])
                        rollbacks += 1
                        events.append("rollback")
                    margin = max(0.005, margin * 0.7)
                last_check = (dict(mainline), u_aud)
            traj.append({"gen": g, "cfg": dict(mainline),
                         "u_train": round(u_mn_train, 4),
                         "u_hold": round(u_mn_hold, 4),
                         "u_audit": round(measure(entries, audit_q, mainline, g, "rv"), 4),
                         "margin": round(margin, 4), "arch_size": 1, "adopts": adopts,
                         "events": ",".join(events)})
            continue

        if arm == "gated-row":
            clus = detect_redundant(entries)
            if clus:
                retire_ids = sorted({m for ms in clus.values() for m in ms})
                if retire_ids:
                    cand = [e for e in entries if e["id"] not in retire_ids]
                    u0 = measure(entries, tn, mainline, g, "imp")
                    u1 = measure(cand, tn, mainline, g, "imp")
                    h0 = measure(entries, hold_q, mainline, g, "rv")
                    h1 = measure(cand, hold_q, mainline, g, "rv")
                    if u1 >= u0 - TOL_ARCH and h1 >= h0 - TOL_ARCH:
                        entries = cand
                        ops_applied += len(retire_ids)
                        removed_ids.extend(retire_ids)
                    else:
                        ops_rejected += 1
        u_mn_hold = measure(entries, hold_q, mainline, g, "rv")
        u_mn_train = measure(entries, tn, mainline, g, "imp")
        cands = [mutate(rng, mainline) for _ in range(3)]
        for c in cands:
            u_tr = measure(entries, tn, c, g, "imp")
            if u_tr >= u_mn_train - TOL_ARCH:
                archive.append(dict(c))
        if pareto_on:
            if (pareto_mode == "cap" and world.get("trainA") is not None
                    and world.get("trainB") is not None):
                archive = _pareto_cap(archive, entries, world["trainA"], world["trainB"], g)
            else:
                archive = _pareto(archive, entries, tn, hold_q, g)
        if len(archive) > CAP_PARETO:
            rng.shuffle(archive)
            archive = archive[:CAP_PARETO]
        best, best_du = None, 0.0
        for c in archive:
            du_tr = measure(entries, tn, c, g, "imp") - u_mn_train
            du_ho = measure(entries, hold_q, c, g, "rv") - u_mn_hold
            if du_tr > margin and du_ho > margin and du_ho > best_du:
                best, best_du = c, du_ho
        if best is not None:
            mainline = dict(best)
            adopts += 1
            stall = 0
        else:
            stall += 1
            if stall >= STALL_GEN:
                margin = max(0.005, margin * 0.5)
                stall = 0
                stall_events += 1
        events = []
        if audit_on and (g % AUDIT_EVERY == 0 or g == gens_eff - 1):
            u_aud = measure(entries, audit_q, mainline, g, "rv")
            if last_check is not None and u_aud < last_check[1] - REVERT_THR:
                audit_dips += 1
                if last_check[0] is not None:
                    mainline = dict(last_check[0])
                    rollbacks += 1
                    events.append("rollback")
                margin = max(0.005, margin * 0.7)
            last_check = (dict(mainline), u_aud)
        traj.append({"gen": g, "cfg": dict(mainline),
                     "u_train": round(u_mn_train, 4),
                     "u_hold": round(measure(entries, hold_q, mainline, g, "rv"), 4),
                     "u_audit": round(measure(entries, audit_q, mainline, g, "rv"), 4),
                     "margin": round(margin, 4), "arch_size": len(archive),
                     "adopts": adopts, "events": ",".join(events)})

    u = final_metrics(mainline)
    g_f = gens_eff - 1
    pool = [mainline] + [c for c in (archive or []) if not all(c.get(k) == mainline.get(k) for k in V3_DEFAULT)]
    capA = world.get("trainA")
    capB = world.get("trainB")
    u["bestA_true"] = _best_cap(pool, entries, capA, g_f)
    u["bestB_true"] = _best_cap(pool, entries, capB, g_f)
    u["redun_hold"] = redundancy(entries, hold_q, mainline, g_f)
    return {"mode": arm, "final_cfg": dict(mainline), "adopts": adopts,
            "audit_dips": audit_dips, "rollbacks": rollbacks,
            "stall_events": stall_events, "arch_final": len(archive),
            "ops_applied": ops_applied, "ops_rejected": ops_rejected,
            "n_removed": len(removed_ids),
            "removed_ids": removed_ids[:20],
            "eval_units": 3 * gens_eff, "gens_eff": gens_eff, "traj": traj, **u}


# ====================================================================
# 预算受限 gated（探针 4 / H8 E64 注意力门槛复现）
# 语义: 每代只有 budget 次 measure(train/hold/audit 各计 1)。变异不费注意力;
#       候选逐个计 train, 若过 margin 再计 hold, 预算耗尽即停止(无法验证的不采纳)。
# ====================================================================
def run_arm_budget(world, seed, gens, budget, audit_on=True):
    global GOLD_EXCLUDE
    GOLD_EXCLUDE = set(world.get("gold_exclude_roles") or [])
    entries = list(world["entries"])
    rng = random.Random(seed * 613 + 31)
    train_q = world.get("train") or world.get("trainA")
    hold_q = world["hold"]
    audit_q = world["audit"]
    mainline = dict(V3_DEFAULT)
    margin = MARGIN0
    archive = [dict(mainline)]
    adopts = stall = audit_dips = rollbacks = 0
    used = 0
    last_check = None
    for g in range(gens):
        left = budget
        tn = train_q
        # 审计(每 3 代, 1 单位, 真值)
        if audit_on and (g % AUDIT_EVERY == 0) and left >= 1:
            left -= 1
            used += 1
            u_aud = measure(entries, audit_q, mainline, g, "rv")
            if last_check is not None and u_aud < last_check[1] - REVERT_THR:
                audit_dips += 1
                if last_check[0] is not None:
                    mainline = dict(last_check[0])
                    rollbacks += 1
                margin = max(0.005, margin * 0.7)
            last_check = (dict(mainline), u_aud)
        u_tr0 = measure(entries, tn, mainline, g, "imp")
        u_ho0 = measure(entries, hold_q, mainline, g, "rv")
        adopted = False
        while left >= 1:
            c = mutate(rng, mainline)
            left -= 1
            used += 1
            du_tr = measure(entries, tn, c, g, "imp") - u_tr0
            if du_tr <= margin:
                continue
            if left >= 1:
                left -= 1
                used += 1
                du_ho = measure(entries, hold_q, c, g, "rv") - u_ho0
                if du_ho > margin:
                    mainline = dict(c)
                    adopts += 1
                    stall = 0
                    adopted = True
                    break
            else:
                break
        if not adopted:
            stall += 1
            if stall >= STALL_GEN:
                margin = max(0.005, margin * 0.5)
                stall = 0
    g_f = gens - 1
    u = {"u_audit": round(measure(entries, audit_q, mainline, g_f, "rv"), 4),
         "u_hold": round(measure(entries, hold_q, mainline, g_f, "rv"), 4),
         "u_trainA": round(measure(entries, train_q, mainline, g_f, "imp"), 4)}
    return {"mode": "gated-budget", "budget": budget, "gens": gens,
            "used": used, "adopts": adopts, "audit_dips": audit_dips,
            "rollbacks": rollbacks, "final_cfg": dict(mainline), **u}


# ====================================================================
# E81 型 judge 通道污染引擎（探针 3）
# 语义: 引擎呈交给 judge 的 top-K 可用 w_show 放大 SHOW(表象)条目;
#       judge(名义 importance 金标)=自洽但被表象误导; 真值(rv 金标)独立。
# 臂: e81-static / e81-bare(纯judge, 无审计) / e81-anchor(仅judge自洽审计, 预期0触发)
#     / e81-truth(周期性真值抽样审计, 预期检出回退)
# ====================================================================
E81_CFG0 = {"w_kw": 3.0, "w_content": 1.0, "w_imp": 1.0, "w_age": 0.1,
            "filter_zero": 0, "w_show": 1.0}


def _presented_top(entries, qtext, cfg, k=K_TOPK):
    """检索排序 + 展示权重: SHOW 条目得分加 w_show(表象通道, judge 可见)"""
    scored = {}
    for e in entries:
        if e.get("validity", {}).get("t_invalid"):
            continue
        qwords = qtext.split()
        kw_join = " ".join(e.get("keywords", []))
        kw_hit = sum(1 for w in qwords if w in kw_join)
        c_hit = sum(1 for w in qwords if w in e["content"])
        if kw_hit:
            c_hit = max(c_hit, 1)
        s = (kw_hit * cfg["w_kw"] + c_hit * cfg["w_content"]
             + e.get("importance", 0.0) * cfg["w_imp"]
             - age_days_of(e.get("created_at", "")) * cfg["w_age"])
        if cfg.get("filter_zero") and kw_hit == 0 and c_hit == 0:
            s = float("-inf")
        if " SHOW" in e["content"] or e["content"].endswith("SHOW"):
            s = s + cfg.get("w_show", 1.0) * 1.0   # 表象条目呈交加成(不影响检索真值排序之外的事实: 这里即最终呈交序)
        scored[e["id"]] = (s, e)
    ranked = sorted(scored.items(), key=lambda kv: (-kv[1][0], kv[0]))
    return [fid for fid, (s, e) in ranked[:k]]


def _judge_score(cfg, e):
    """judge 感知分: 名义 importance 被表面(SHOW)乘性放大 —— E81 展示权重通道"""
    imp = e.get("importance", 0.0)
    show = 1 if (" SHOW" in e.get("content", "") or e["content"].endswith("SHOW")) else 0
    return imp * (1.0 + cfg.get("w_show", 1.0) * show)


def _gold_top(entries, q, gen, by, k=K_GOLD, cfg=None):
    pool = []
    for e in entries:
        if e["topic"] != q["topic"]:
            continue
        if e["birth_gen"] > gen:
            continue
        if e.get("obsolete_gen") is not None and e["obsolete_gen"] <= gen:
            continue
        if e.get("role") in GOLD_EXCLUDE:
            continue
        pool.append(e)
    if by == "imp":
        pool.sort(key=lambda x: -_judge_score(cfg, x))
    else:
        pool.sort(key=lambda x: -x["rv"])
    return [e["id"] for e in pool[:k]]


def measure_presented(entries, qs, cfg, gen, by):
    """judge 通道(by=imp: 感知分=名义*(1+w_show*show))或真值通道(by=rv)在【呈交 top-K】上的 util"""
    if not qs:
        return 0.0
    tot = 0.0
    for q in qs:
        ids = _presented_top(entries, q["topic"], cfg)
        gold = set(_gold_top(entries, q, gen, by, cfg=cfg))
        hit = sum(1 for i in ids if i in gold)
        tot += hit / min(K_GOLD, K_TOPK)
    return tot / len(qs)


def run_arm_e81(world, arm, seed, gens, audit_every=AUDIT_EVERY):
    entries = list(world["entries"])
    rng = random.Random(seed * 131 + 7)
    train_q = world.get("train") or world.get("trainA")
    hold_q = world["hold"]
    audit_q = world["audit"]
    g_f = gens - 1

    if arm == "e81-static":
        cfg = dict(E81_CFG0)
        return {"mode": arm, "final_cfg": dict(cfg), "adopts": 0,
                "P_final": round(measure_presented(entries, audit_q, cfg, g_f, "imp"), 4),
                "T_final": round(measure_presented(entries, audit_q, cfg, g_f, "rv"), 4),
                "audit_dips": 0, "rollbacks": 0, "w_show_end": cfg["w_show"],
                "sec": 0.0}

    mainline = dict(E81_CFG0)
    margin = MARGIN0
    adopts = audit_dips = rollbacks = 0
    last_check = None
    traj = []

    for g in range(gens):
        p_tr0 = measure_presented(entries, train_q, mainline, g, "imp")  # judge 训练
        h_tr0 = measure_presented(entries, hold_q, mainline, g, "imp")   # judge 晋升(污染通道)
        best, best_du = None, 0.0
        for _ in range(3):
            c = mutate(rng, mainline)
            du_p = measure_presented(entries, train_q, c, g, "imp") - p_tr0
            du_h = measure_presented(entries, hold_q, c, g, "imp") - h_tr0
            if arm == "e81-bare":
                ok = du_p > 0
            else:
                ok = du_p > margin and du_h > margin
            if ok and du_p > best_du:
                best, best_du = c, du_p
        if best is not None:
            mainline = dict(best)
            adopts += 1
        if arm in ("e81-anchor", "e81-truth") and (g % audit_every == 0 or g == gens - 1):
            by = "imp" if arm == "e81-anchor" else "rv"   # 锚定审计=judge 自洽; 真值抽样=rv
            u_aud = measure_presented(entries, audit_q, mainline, g, by)
            if last_check is not None and u_aud < last_check[1] - REVERT_THR:
                audit_dips += 1
                if last_check[0] is not None:
                    mainline = dict(last_check[0])
                    rollbacks += 1
                margin = max(0.005, margin * 0.7)
            last_check = (dict(mainline), u_aud)
        traj.append({"gen": g,
                     "P": round(measure_presented(entries, audit_q, mainline, g, "imp"), 4),
                     "T": round(measure_presented(entries, audit_q, mainline, g, "rv"), 4),
                     "w_show": round(mainline.get("w_show", 1.0), 4)})

    return {"mode": arm, "final_cfg": dict(mainline), "adopts": adopts,
            "P_final": round(measure_presented(entries, audit_q, mainline, g_f, "imp"), 4),
            "T_final": round(measure_presented(entries, audit_q, mainline, g_f, "rv"), 4),
            "audit_dips": audit_dips, "rollbacks": rollbacks,
            "w_show_end": round(mainline.get("w_show", 1.0), 4), "traj": traj}

