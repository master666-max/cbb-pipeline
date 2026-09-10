# -*- coding: utf-8 -*-
"""
第十轮 E61/E62/E63/E65/E66：周期、长尾、分歧、漂移、反身（5 个实验）
第九轮补完合谋/身份/时滞/预警/词面/元性质后，本轮问五个"非平稳与多样性"问题：
  E61 周期性概念漂移：主题热度去而复返时，LRU/LFU/慢性层两级存储的"回归失忆"与恢复代价
  E62 长尾公平：Zipf 查询频率下 LFU 让稀有主题窒息；配额救长尾的全局代价（Pareto 拐点）
  E63 合法多观点误合并：同情境、仅结论标记不同的记忆簇，去重阈值的两面夹击（E46 的对偶）
  E65 评测目标缓慢漂移：金尺合法换尺时，静态门控的参照点变幻觉锚（E15 棘轮的动态负债）
  E66 反身性闭环：考题从自己 top 记忆的词表里出——没有对手也足以 Goodhart（performative）
  E61/E62 的存储模型：热区（预算内、可被检索命中）+ 冷档案（不可命中、每查询可探测回读 1 条）。
文献锚点（本环境经 OpenAlex/Crossref 核验 DOI）：
  E61: Widmer & Kubat, Machine Learning 1996, concept drift & hidden contexts (10.1007/bf00116900)；
       Jiang & Zhang, SIGMETRICS 2002, LIRS (10.1145/511399.511340)；Gama et al., ACM CSUR 2014 (10.1145/2523813)
  E62: Klimashevskaia et al., UMUAI 2024, popularity bias survey (10.1007/s11257-024-09406-0)；
       Singh & Joachims, KDD 2018, fairness of exposure (10.1145/3219819.3220088)；Zipf 1949
  E63: Manku et al., WWW 2007, near-duplicate detection/simhash (10.1145/1242572.1242592)；
       Hong & Page, PNAS 2004, diverse problem solvers (10.1073/pnas.0403723101)；对偶 E46
  E65: Garivier & Moulines, ALT 2011, sliding-window UCB (10.1007/978-3-642-24412-4_16)；对偶 E15
  E66: Perdomo et al., ICML 2020, performative prediction（综述 Hardt, Statistical Science 2025, 10.1214/25-sts986）；
       Alemohammad et al. 2023, Self-Consuming Generative Models go MAD (arXiv:2307.01850，第七轮已锚)
全部局部 random.Random(seed)，并列排序加 id 字典序 tiebreak；8 种子均值；无计时实验、两次运行须逐行一致。
"""
import math, random, statistics
import mem_common as M

SEEDS = [11, 23, 37, 51, 67, 83, 101, 127]
def mean(x): return round(statistics.mean(x), 3) if x else 0.0
def sd(x):   return round(statistics.pstdev(x), 3) if len(x) > 1 else 0.0
def gini(vals):
    s = sorted(vals); n = len(s); cum = 0.0
    for i, v in enumerate(s, 1): cum += i * v
    tot = sum(s)
    return round((2 * cum) / (n * tot) - (n + 1) / n, 3) if tot > 0 else 0.0
def line(s=""): print(s)

# ==========================================================================
# E61 周期性概念漂移：正弦热度 + 热区/冷档案两级存储，LRU/LFU/慢性层
# ==========================================================================
def _hot_weight(g, topic_idx, P, n_ph=4):
    """主题热度：4 个相位组（组内同相），正弦 w∈[0,1]，周期 P 代，从 0 升起。"""
    ph = (topic_idx % n_ph) * (P / 4.0)
    return max(0.0, (1.0 + math.sin(2 * math.pi * (g + ph) / P - math.pi / 2)) / 2)

TH61 = dict(M.FACTORY, w_age=0.01)      # 缓存实验剥离老化项（age 伪影会让 golden 按年龄出局，见 F23）

def e61_run(lib, rnd, policy, P, gens=80, n_q=20, budget=96, probe=1):
    """两级存储：热区可命中；每条查询额外探测冷档案 top1 回读。逐出按策略。
    返回 (总体recall, 回归初期recall, 恢复代数, 慢性占比, 峰谷差)"""
    hot = {e["id"]: e for e in lib}
    cold = {}
    uses = {e["id"]: 0 for e in lib}
    last_hit = {e["id"]: -1 for e in lib}
    chronic = set()
    topics = list(range(len(M.TOPICS)))
    golden = {}
    for t in topics:
        tp = M.TOPICS[t]
        golden[t] = {e["id"] for e in sorted([e for e in lib if e["topic"] == tp and not e.get("truly_invalid")],
                                             key=lambda e: (-e["true_quality"], e["id"]))[:3]}
    rec_all, rec_early = [], []
    topic_hist = {t: [] for t in topics}
    for g in range(gens):
        weights = {t: _hot_weight(g, t, P) for t in topics}
        tw = sum(weights.values())
        served = []
        for _ in range(n_q):
            if tw <= 0: break
            r = rnd.random() * tw; acc = 0.0; pick = topics[-1]
            for t in topics:
                acc += weights[t]
                if r <= acc: pick = t; break
            served.append(pick)
        for t in served:
            tp = M.TOPICS[t]
            qw = " ".join(rnd.sample(sorted(M.TOPIC_WORDS[tp]), 2))
            rl = M.rank(list(hot.values()), qw, TH61)[:5]
            top = [fid for fid, _ in rl]
            hit = 1.0 if set(top) & golden[t] else 0.0
            rec_all.append(hit); topic_hist[t].append((g, hit))
            for fid in top:
                uses[fid] += 1; last_hit[fid] = g
                if uses[fid] >= 6: chronic.add(fid)
            if cold and probe > 0:                              # 冷档案探测回读 probe 条
                cl = M.rank(list(cold.values()), qw, TH61)[:probe]
                for fid, _ in cl:
                    hot[fid] = cold.pop(fid)
        # 期末逐出热区到预算
        if policy == "慢性层":
            nonch = sorted([i for i in hot if i not in chronic], key=lambda i: (last_hit[i], i))
            for i in nonch:
                if len(hot) <= budget: break
                cold[i] = hot.pop(i)
            ch = sorted([i for i in hot if i in chronic], key=lambda i: (last_hit[i], i))
            for i in ch:
                if len(hot) <= budget or len(chronic & set(hot)) <= int(0.6 * budget): break
                cold[i] = hot.pop(i)
        else:
            if policy == "LRU":
                order = sorted(hot, key=lambda i: (last_hit[i], i))
            else:                                               # LFU
                order = sorted(hot, key=lambda i: (uses[i], last_hit[i], i))
            for i in order:
                if len(hot) <= budget: break
                cold[i] = hot.pop(i)
    for t in topics:
        rising = [g for g in range(1, gens) if _hot_weight(g, t, P) > 0.5 and _hot_weight(g - 1, t, P) <= 0.5]
        for g0 in rising:
            window = [h for (g, h) in topic_hist[t] if g0 <= g < g0 + 5]
            if window: rec_early.extend(window)
    recov = []
    for t in topics:
        g0 = next((g for g in range(1, gens) if _hot_weight(g, t, P) > 0.2 and _hot_weight(g - 1, t, P) <= 0.2), None)
        if g0 is None: continue
        run = 0; rr = -1
        for g, h in sorted(topic_hist[t]):
            if g < g0: continue
            run = run + 1 if h > 0 else 0
            if run >= 3: rr = g - g0; break
        if rr >= 0: recov.append(rr)
    ch_share = len([i for i in hot if i in chronic]) / max(1, len(hot))
    peak_trough = 0.0
    for t in topics:
        vals = [h for _, h in topic_hist[t]]
        if len(vals) >= 8:
            half = len(vals) // 2
            sv = sorted(vals)
            peak_trough = max(peak_trough, mean(sv[half:]) - mean(sv[:half]))
    return mean(rec_all), (mean(rec_early) if rec_early else -1), (mean(recov) if recov else -1), round(ch_share, 3), round(peak_trough, 3)

def e61():
    out = {"pol": {}, "bw": {}}
    for P in [20, 40, 80]:
        for policy in ["LRU", "LFU", "慢性层"]:
            agg = [[] for _ in range(5)]
            for s in SEEDS:
                rnd = random.Random(6600 + s)
                lib = M.make_library(240, seed=s, vanity_frac=0.08)
                r = e61_run(lib, rnd, policy, P)
                for i, v in enumerate(r): agg[i].append(v)
            out["pol"][(P, policy)] = tuple(mean(a) for a in agg)
    for pb in [0, 1, 3]:
        agg = [[] for _ in range(5)]
        for s in SEEDS:
            rnd = random.Random(6600 + s)
            lib = M.make_library(240, seed=s, vanity_frac=0.08)
            r = e61_run(lib, rnd, "LRU", 40, probe=pb)
            for i, v in enumerate(r): agg[i].append(v)
        out["bw"][pb] = tuple(mean(a) for a in agg)
    return out

# ==========================================================================
# E62 长尾公平：Zipf 查询流 + 热区/冷档案两级存储，LFU/LRU/折扣LFU/主题配额
# ==========================================================================
TH62 = dict(M.FACTORY, w_age=0.01)      # 同 E61：剥离老化项

def e62_run(lib, rnd, policy, quota, s_exp=1.5, gens=60, n_q=20, budget=80):
    hot = {}                                    # 冷启动：热区从空开始，只靠探测回读填充
    cold = {e["id"]: e for e in lib}
    uses = {e["id"]: 0 for e in lib}
    last_hit = {e["id"]: -1 for e in lib}
    order = list(range(len(M.TOPICS))); rnd.shuffle(order)
    w = {t: 1.0 / ((order.index(t) + 1) ** s_exp) for t in order}
    tw = sum(w.values())
    golden = {}
    for t in order:
        tp = M.TOPICS[t]
        golden[t] = {e["id"] for e in sorted([e for e in lib if e["topic"] == tp and not e.get("truly_invalid")],
                                             key=lambda e: (-e["true_quality"], e["id"]))[:3]}
    rec_by_topic = {t: [] for t in order}
    for g in range(gens):
        probes_left = 2                                  # 回读是稀缺资源：每代 2 条、先到先得
        for _ in range(n_q):
            r = rnd.random() * tw; acc = 0.0; pick = order[0]
            for t in order:
                acc += w[t]
                if r <= acc: pick = t; break
            tp = M.TOPICS[pick]
            qw = " ".join(rnd.sample(sorted(M.TOPIC_WORDS[tp]), 2))
            rl = M.rank(list(hot.values()), qw, TH62)[:5]
            top = [fid for fid, _ in rl]
            rec_by_topic[pick].append(1.0 if set(top) & golden[pick] else 0.0)
            for fid in top:
                uses[fid] += 1; last_hit[fid] = g
            if cold and probes_left > 0:
                probes_left -= 1
                cl = M.rank(list(cold.values()), qw, TH62)[:1]
                for fid, _ in cl:
                    hot[fid] = cold.pop(fid)
        if policy == "折扣LFU":
            for i in uses: uses[i] *= 0.97
        if quota > 0:
            # 预留席位制：每主题 visible 最优 quota 条（imp−0.1·age）常驻热区，其余按 LFU 竞争自由预算
            for t in order:
                tp = M.TOPICS[t]
                rep = sorted([e for e in lib if e["topic"] == tp],
                             key=lambda e: (-(e["importance"] - 0.1 * (365 - e["created_day"])), e["id"]))[:quota]
                for e in rep:
                    if e["id"] in cold:
                        hot[e["id"]] = cold.pop(e["id"])
            reserved = {e["id"] for t in order for e in
                        sorted([x for x in lib if x["topic"] == M.TOPICS[t]],
                               key=lambda x: (-(x["importance"] - 0.1 * (365 - x["created_day"])), x["id"]))[:quota]}
            victims = sorted((i for i in hot if i not in reserved), key=lambda i: (uses[i], last_hit[i], i))
            for i in victims:
                if len(hot) <= budget: break
                cold[i] = hot.pop(i)
        else:
            if policy == "LRU":
                orderk = sorted(hot, key=lambda i: (last_hit[i], i))
            else:                                                 # LFU / 折扣LFU
                orderk = sorted(hot, key=lambda i: (uses[i], last_hit[i], i))
            for i in orderk:
                if len(hot) <= budget: break
                cold[i] = hot.pop(i)
    recs = {t: mean(v) for t, v in rec_by_topic.items() if v}
    tail = [t for t in order if order.index(t) >= 14]
    head = [t for t in order if order.index(t) <= 6]
    return (mean(list(recs.values())),
            mean([recs[t] for t in head if t in recs]),
            mean([recs[t] for t in tail if t in recs]),
            gini(list(recs.values())))

def e62():
    policies = [("LFU", 0), ("LRU", 0), ("折扣LFU", 0), ("预留Q2", 2), ("预留Q3", 3), ("预留Q4", 4)]
    out = {}
    for policy, quota in policies:
        agg = [[] for _ in range(4)]
        for s in SEEDS:
            rnd = random.Random(6700 + s)
            lib = M.make_library(240, seed=s, vanity_frac=0.08)
            r = e62_run(lib, rnd, policy, quota)
            for i, v in enumerate(r): agg[i].append(v)
        out[policy] = tuple(mean(a) for a in agg)
    return out

# ==========================================================================
# E63 合法多观点误合并：同情境、仅结论标记不同，去重阈值的两面夹击
# ==========================================================================
E63_MARKS = ["甲案", "乙案"]                              # 结论标记词（不在任何主题词表内）
E63_TOPIC = "多智能体"
NOW63 = 205
E63_GEN = ["方法", "机制", "方案"]                          # 变体用泛词（确定性轮换）

def e63_cluster(seed):
    """两视角簇，每簇：2 条主条（词集 {协作,分工,方法,mark}）+ 3 条变体（主条词集 + 1 个互不相同的泛词）。
    词面结构：同视角 主-变 J=4/5=0.8、变-变 J=5/6≈0.83、主-主 J=1.0；
    跨视角 主-主 J=3/5=0.6、主-变 4/6≈0.67、变-变 5/7≈0.71。"""
    rnd = random.Random(6800 + seed)
    lib = []
    for mk in E63_MARKS:
        for j in range(5):
            if j < 2:
                kws = ["协作", "分工", "方法", mk]; content = ["协作", "分工", "方法", mk]
            else:
                kws = ["协作", "分工", "方法", mk]; content = ["协作", "分工", mk, E63_GEN[j % 3]]
            lib.append(dict(id="V%s%d" % (mk, j), topic=E63_TOPIC,
                            true_quality=round(rnd.uniform(0.75, 0.95), 3),
                            keywords=kws, content=content,
                            importance=6, honest_imp=6, vanity=False, created_day=195 + j,
                            t_invalid=None, truly_invalid=False, uses=rnd.randint(0, 20),
                            links=[], is_farm=False, mark=mk))
    return lib

def _jset(e):
    return set(e["keywords"]) | set(e["content"])

def _jac(a, b):
    ia, ib = _jset(a), _jset(b)
    return len(ia & ib) / len(ia | ib) if (ia | ib) else 0.0

def e63(seed, theta_m, marker_aware):
    """作用域=两簇 + 1 条高 uses 武器化仿主条（乙标记、词集=乙主条+噪声 → J=4/5=0.8）。
    返回 (跨视角直接合并率, 簇内重复去除率, 乙主条存活率(受攻击), top5 非golden占用)"""
    lib = e63_cluster(seed)
    atk = dict(id="W001", topic=E63_TOPIC, true_quality=0.02,
               keywords=["协作", "分工", "方法", "乙案"], content=["协作", "分工", "方法", "乙案", "噪声"],
               importance=6, honest_imp=1, vanity=False, created_day=197, t_invalid=None,
               truly_invalid=True, uses=99, links=[], is_farm=False, mark="乙案")
    world = lib + [atk]
    del_ids = set(); cross_merged = 0
    for a in world:
        for b in world:
            if a["id"] >= b["id"]: continue
            j = _jac(a, b)
            if j < theta_m: continue
            if marker_aware and a.get("mark") != b.get("mark"): continue
            ka = (a["uses"], a["id"]); kb = (b["uses"], b["id"])
            drop = b if ka >= kb else a
            del_ids.add(drop["id"])
    ka_ = [e for e in lib if e.get("mark") == "甲案"]
    kb_ = [e for e in lib if e.get("mark") == "乙案"]
    n_cross = len(ka_) * len(kb_)
    for a in ka_:                                   # 跨视角直接合并只数簇内对（攻击条另计）
        for b in kb_:
            if _jac(a, b) < theta_m: continue
            if marker_aware: continue               # 视角感知下跨视角合并被禁止
            cross_merged += 1
    alive = [e for e in world if e["id"] not in del_ids]
    # 簇内重复去除率（同视角非逐字对：主-变、变-变）
    dup_pairs = []
    for mk in E63_MARKS:
        mem = [e for e in lib if e.get("mark") == mk]
        for i in range(len(mem)):
            for j2 in range(i + 1, len(mem)):
                if _jac(mem[i], mem[j2]) < 1.0:
                    dup_pairs.append((mem[i], mem[j2]))
    dup_removed = sum(1 for a, b in dup_pairs if a["id"] in del_ids or b["id"] in del_ids)
    # 攻击条是否清空乙主条（j=0,1 双双被并、高 uses 攻击条成为乙视角唯一代表）
    mains = [e for e in kb_ if e["id"].endswith(("0", "1"))]
    main_alive = sum(1 for e in mains if e["id"] not in del_ids) / max(1, len(mains))
    atk_dominate = 1.0 if ("W001" not in del_ids and main_alive == 0) else 0.0
    # 检索槽位
    wasted = 0
    for mk in ["甲案", "乙案"]:
        q = "协作 分工 " + mk
        exp = {e["id"] for e in sorted([e for e in lib if e.get("mark") == mk and e["id"] not in del_ids],
                                       key=lambda e: (-e["true_quality"], e["id"]))[:2]}
        top = [fid for fid, _ in M.rank(alive, q, M.FACTORY, NOW63)[:5]]
        wasted += sum(1 for f in top if f not in exp) / 5.0
    return (round(cross_merged / n_cross, 3), round(dup_removed / max(1, len(dup_pairs)), 3),
            round(atk_dominate, 3), round(wasted / 2, 3))

def e63_wrapper():
    out = {}
    for marker_aware in [False, True]:
        for th in [0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9]:
            agg = [[] for _ in range(4)]
            for s in SEEDS:
                r = e63(s, th, marker_aware)
                for i, v in enumerate(r): agg[i].append(v)
            out[(marker_aware, th)] = tuple(mean(a) for a in agg)
    return out

# ==========================================================================
# E65 评测目标缓慢漂移：偏好质量→新鲜，硬景观（600 条、单词查询、K=3）
# ==========================================================================
def e65_golden(lib, lam, queries):
    """golden 随 λ 漂移：score = quality − λ·age_norm；expected=主题内 top3。"""
    by = {}
    for e in lib: by.setdefault(e["topic"], []).append(e)
    qs = []
    for item in queries:
        pool = [e for e in by.get(item["topic"], []) if not e.get("truly_invalid")]
        if len(pool) < 3: continue
        scored = sorted(pool, key=lambda e: (-(e["true_quality"] - lam * (365 - e["created_day"]) / 365.0), e["id"]))
        qs.append(dict(topic=item["topic"], query=item["query"], expected=[e["id"] for e in scored[:3]]))
    return qs

def e65_eval(lib, qs, theta):
    hit = 0
    for x in qs:
        top = [fid for fid, _ in M.rank(lib, x["query"], theta)[:3]]
        hit += 1.0 if set(top) & set(x["expected"]) else 0.0
    return hit / max(1, len(qs))

def e65_run(lib, seed, variant, margin, gens=50, W=10):
    """variant: freeze(门控参照点=上次接受时分) / fresh(每代重评参照) / slide(金尺取近 W 代期望频率)"""
    rnd = random.Random(7000 + seed)
    base_q = M.make_queries(lib, 60, seed=500 + seed, words_per_q=1)
    theta = dict(M.FACTORY); keys = ["w_kw", "w_c", "w_imp", "w_age", "d"]
    tr = None; stalls = 0; traj = []; window = []
    for g in range(gens):
        lam = g / (gens - 1.0)
        qs = e65_golden(lib, lam, base_q)
        if variant == "slide":
            window.append({i: x["expected"] for i, x in enumerate(qs)})
            if len(window) > W: window.pop(0)
            qs_train = []
            for i in range(len(qs)):
                freq = {}
                for win in window:
                    for eid in win.get(i, []): freq[eid] = freq.get(eid, 0) + 1
                if not freq: continue
                top3 = sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))[:3]
                x = dict(qs[i]); x["expected"] = [eid for eid, _ in top3]
                qs_train.append(x)
        else:
            qs_train = qs
        cur = e65_eval(lib, qs_train, theta)
        if tr is None or variant != "freeze":
            tr = cur
        cand = dict(theta); k = rnd.choice(keys)
        cand[k] = cand[k] + rnd.gauss(0, 0.15) * max(0.3, abs(cand[k]) + 0.2)
        M.clip_theta(cand)
        ntr = e65_eval(lib, qs_train, cand)
        if ntr >= tr + margin:
            theta = cand; tr = ntr
        else:
            stalls += 1
        traj.append(e65_eval(lib, qs, theta))
    return mean(traj[len(traj) // 2:]), traj[-1], stalls / gens

def e65():
    out = {}
    for variant in ["freeze", "fresh", "slide"]:
        for margin in [0.0, 0.02, 0.05]:
            agg = [[] for _ in range(2)]; st = []
            for s in SEEDS:
                lib = M.make_library(600, seed=s, vanity_frac=0.08)
                m, fin, sr = e65_run(lib, s, variant, margin)
                agg[0].append(m); agg[1].append(fin); st.append(sr)
            out[(variant, margin)] = (mean(agg[0]), mean(agg[1]), mean(st))
    return out

# ==========================================================================
# E66 反身性闭环：考题从自己 top 记忆的词表里出，内部分与外部金尺背离
# ==========================================================================
def e66_gen_exam(lib, rnd, pool_words, n_q=40, eps=0.0):
    """1−ε 比例自考题：词采自 pool_words（上代 top 记忆词表），
    expected=含查询词条目中 true_quality top3（考官上帝视角允许）；ε 外生考题。"""
    qs = []
    ext = M.make_queries(lib, n_q, seed=rnd.randrange(1 << 30))
    for i in range(n_q):
        if rnd.random() < eps:
            qs.append(ext[i % len(ext)]); continue
        if len(pool_words) < 2: continue
        wl = rnd.sample(sorted(pool_words), 2)
        q = " ".join(wl)
        blob = lambda e: " ".join(e["keywords"]) + " " + " ".join(e["content"])
        cand = [e for e in lib if not e.get("truly_invalid") and any(w in blob(e) for w in wl)]
        if len(cand) < 3: continue
        exp = sorted(cand, key=lambda e: (-e["true_quality"], e["id"]))[:3]
        qs.append(dict(topic=-1, query=q, expected=[e["id"] for e in exp]))
    return qs

def e66_run(lib, seed, eps, gens=40):
    """返回 (内部自考终值, 外部金尺终值, 外部后半均值, 背离差)。"""
    rnd = random.Random(7100 + seed)
    ext = M.make_queries(lib, 80, seed=500 + seed)
    theta = dict(M.FACTORY); keys = ["w_kw", "w_c", "w_imp", "w_age", "d"]
    id2e = {e["id"]: e for e in lib}
    pool_words = []
    for x in ext[:10]:
        for fid, _ in M.rank(lib, x["query"], M.FACTORY)[:10]:
            pool_words.extend(id2e[fid]["keywords"])
    ext_traj = []; int_traj = []
    for g in range(gens):
        exam = e66_gen_exam(lib, rnd, pool_words, eps=eps)
        if not exam: break
        cur = M.evaluate(lib, exam, theta)["recall"]
        cand = dict(theta); k = rnd.choice(keys)
        cand[k] = cand[k] + rnd.gauss(0, 0.15) * max(0.3, abs(cand[k]) + 0.2)
        M.clip_theta(cand)
        ntr = M.evaluate(lib, exam, cand)["recall"]
        if ntr >= cur:
            theta = cand
        ext_traj.append(M.evaluate(lib, ext, theta)["recall"])
        int_traj.append(cur)
        words = []
        for x in exam[:10]:
            for fid, _ in M.rank(lib, x["query"], theta)[:10]:
                words.extend(id2e[fid]["keywords"])
        if words: pool_words = words
    half = len(ext_traj) // 2
    div = mean(int_traj[half:]) - mean(ext_traj[half:])
    return int_traj[-1], ext_traj[-1], mean(ext_traj[half:]), round(div, 3)

def e66():
    out = {}
    for eps in [0.0, 0.2, 0.4, 0.6, 1.0]:
        agg = [[] for _ in range(4)]
        for s in SEEDS:
            lib = M.make_library(240, seed=s, vanity_frac=0.08)
            r = e66_run(lib, s, eps)
            for i, v in enumerate(r): agg[i].append(v)
        out[eps] = tuple(mean(a) for a in agg)
    return out

# ==========================================================================
def main():
    line("=" * 90)
    line("第十轮 E61/E62/E63/E65/E66：周期、长尾、分歧、漂移、反身（8 种子均值，确定性可复现）")
    line("=" * 90)

    line("\n### E61 周期性概念漂移（4 相位组正弦、热区预算 96/240+冷档案回读；总体/回归初期/恢复代数/慢性占比/峰谷差）")
    res61 = e61()
    line("  [表A 策略对比（回读=1）] %-8s %-10s %-12s %-10s %-10s %-8s" % ("策略", "总体", "回归初期", "恢复代数", "慢性占比", "峰谷差"))
    for (P, pol), r in sorted(res61["pol"].items()):
        line("  P=%-4d %-6s %-10s %-12s %-10s %-10s %-8s" % (P, pol, r[0], r[1], r[2], r[3], r[4]))
    line("  [表B 回读带宽消融（P=40, LRU）]")
    line("  %-14s %-10s %-12s %-10s %-10s" % ("回读条数/查询", "总体", "回归初期", "恢复代数", "慢性占比"))
    for pb, r in sorted(res61["bw"].items()):
        line("  probe=%-10d %-10s %-12s %-10s %-10s" % (pb, r[0], r[1], r[2], r[3]))

    line("\n### E62 长尾公平（Zipf s=1.5、热区预算 80/240 冷启动+探测回读；整体/head(前6秩)/tail(后7秩)/主题recall基尼）")
    res62 = e62()
    line("  %-10s %-12s %-12s %-12s %-10s" % ("策略", "整体recall", "头部recall", "尾部recall", "主题基尼"))
    for pol in ["LFU", "LRU", "折扣LFU", "预留Q2", "预留Q3", "预留Q4"]:
        r = res62[pol]
        line("  %-10s %-12s %-12s %-12s %-10s" % (pol, r[0], r[1], r[2], r[3]))

    line("\n### E63 合法多观点误合并（跨视角J=0.60-0.71/簇内重复J=0.8-1.0/仿主攻击条J=0.8；阈值θ扫）")
    res63 = e63_wrapper()
    line("  %-14s %-6s %-14s %-14s %-16s %-14s" % ("合并策略", "θ", "跨视角合并率", "簇内重复去除", "攻击条清空乙主条", "top5非golden占用"))
    for (ma, th), r in sorted(res63.items()):
        line("  %-14s %-6s %-14s %-14s %-16s %-14s" % (
            "视角感知" if ma else "朴素Jaccard", th, r[0], r[1], r[2], r[3]))

    line("\n### E65 评测目标缓慢漂移（600条库、单词查询、K=3；λ:0→1 质量转向新鲜，50 代）")
    res65 = e65()
    line("  %-8s %-8s %-16s %-12s %-12s" % ("参照点", "margin", "追踪recall后半", "末代recall", "冻结代占比"))
    for (var, mg), r in sorted(res65.items()):
        line("  %-8s %-8s %-16s %-12s %-12s" % (var, mg, r[0], r[1], r[2]))

    line("\n### E66 反身性闭环（自考题占比 1−ε，40 代；内部终值/外部终值/外部后半/背离差）")
    res66 = e66()
    line("  %-8s %-10s %-10s %-14s %-10s" % ("ε外考", "内部终值", "外部终值", "外部recall后半", "背离差"))
    for eps, r in sorted(res66.items()):
        line("  ε=%-6s %-10s %-10s %-14s %-10s" % (eps, r[0], r[1], r[2], r[3]))

    line("\n" + "=" * 90)
    line("第十轮完成 E61/E62/E63/E65/E66 共 5 个实验")
    line("=" * 90)

if __name__ == "__main__":
    main()
