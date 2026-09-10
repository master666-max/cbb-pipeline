# -*- coding: utf-8 -*-
"""
第十一轮 E70–E74：前十轮自启问题的交叉验证（5 个实验）
预注册菜单（E67–E69）保留给世界模型扩展项；本轮全部由第九、十轮的发现自己长出来：
  E70 回读带宽的分配与预取（E61 后续）：同样 20 条/代预算，按查询撒 vs 按需分页 vs 预言预取，谁把带宽用在刀刃上
  E71 动态席位 Q(t)（E61×E62 交叉）：冷热反转的世界里，静态预留席位锁死旧秩次，比例共享动态席位能否自适应
  E72 反身临界 ε* 与在线自考检测（E66 后续）：细扫 ε 找临界点；不依赖真值、只看考题主题熵就能在线估计自考占比并自纠
  E73 两级存储×组合后门（E56×E61 交叉）：睡眠记忆潜伏在冷档案里零成本越冬，回读通道反成攻击者的免费电梯
  E74 健康仪表盘 v2（E59 扩展）：席位失衡/考题覆盖赤字/回读浪费/回读占用集中度四个新指标，对十类故障的覆盖
文献锚点（本环境经 OpenAlex/Crossref 核验 DOI）：
  E70: Denning, CACM 1968, working set model (10.1145/363095.363141)；O'Neil et al., SIGMOD 1993, LRU-K (10.1145/170035.170081)
  E71: Waldspurger & Weihl 1994, lottery scheduling (10.5555/1267638.1267639)；Demers et al. 1989, fair queueing (10.1145/75246.75248)
  E72: Gretton et al., JMLR 2012, kernel two-sample test (10.5555/2188385.2188410)；Perdomo ICML 2020（第十轮已锚）
  E73: Conti et al., Computer Networks 2013, cache pollution attacks detection (10.1016/j.comnet.2013.07.034)；E56/E57 已锚
  E74: Scheffer et al., Nature 2009（第九轮已锚）+ E59 前作
全部局部 random.Random(seed)，并列排序加 id 字典序 tiebreak；8 种子均值；无计时实验、两次运行须逐行一致。
"""
import math, random, statistics
import mem_common as M

SEEDS = [11, 23, 37, 51, 67, 83, 101, 127]
def mean(x): return round(statistics.mean(x), 3) if x else 0.0
def sd(x):   return round(statistics.pstdev(x), 3) if len(x) > 1 else 0.0
def line(s=""): print(s)

TH11 = dict(M.FACTORY, w_age=0.01)     # 两级存储实验剥离老化项（第十轮 F23 教训）
NOW11 = 365

# ── 共用骨架：两级存储周期/Zipf 世界 ──────────────────────────────
def _mk(topic):
    return M.TOPICS[topic]

def _golden_by_topic(lib):
    g = {}
    for t, tp in enumerate(M.TOPICS):
        g[t] = {e["id"] for e in sorted([e for e in lib if e["topic"] == tp and not e.get("truly_invalid")],
                                        key=lambda e: (-e["true_quality"], e["id"]))[:3]}
    return g

def _sine_w(g, topic_idx, P, n_ph=4):
    ph = (topic_idx % n_ph) * (P / 4.0)
    return max(0.0, (1.0 + math.sin(2 * math.pi * (g + ph) / P - math.pi / 2)) / 2)

def _probe_admit(hot, cold, qw, k, TH=TH11):
    """冷档案按查询词回读 k 条（返回被收录的 id）。"""
    got = []
    if cold and k > 0:
        cl = M.rank(list(cold.values()), qw, TH)[:k]
        for fid, _ in cl:
            hot[fid] = cold.pop(fid); got.append(fid)
    return got

def _pick_weighted(order, w, tw, rnd):
    r = rnd.random() * tw; acc = 0.0; pick = order[0]
    for t in order:
        acc += w[t]
        if r <= acc: pick = t; break
    return pick

# ==========================================================================
# E70 回读带宽的分配与预取：同样 20 条/代预算，四种花法
# ==========================================================================
def e70_run(lib, rnd, policy, P=40, gens=80, n_q=20, budget=96):
    """policy: perquery(每查询1条,总量20/代) / demand(仅查询零命中时回读) /
    recent(查询回读1条+代末对最近命中主题追加) / oracle(用热度日程预取将升起主题的最优冷条)。
    返回 (总体recall, 回归初期, 恢复代数, 回读5代内命中率)。"""
    hot = {e["id"]: e for e in lib}; cold = {}
    uses = {e["id"]: 0 for e in lib}; last_hit = {e["id"]: -1 for e in lib}
    golden = _golden_by_topic(lib)
    topics = list(range(len(M.TOPICS)))
    admitted = {}                                     # id -> 回读代
    admit_hit = [0, 0]                                # [5代内被命中数, 总回读数]
    rec_all, rec_early = [], []
    topic_hist = {t: [] for t in topics}
    def do_admit(qw, k):
        got = _probe_admit(hot, cold, qw, k)
        for fid in got: admitted[fid] = (g, qw)
        return got
    for g in range(gens):
        weights = {t: _sine_w(g, t, P) for t in topics}
        tw = sum(weights.values())
        served = []
        for _ in range(n_q):
            if tw <= 0: break
            t = _pick_weighted(topics, weights, tw, rnd)
            served.append(t)
        budget_left = n_q                                 # 总预算 = n_q 条/代
        for t in served:
            tp = M.TOPICS[t]
            qw = " ".join(rnd.sample(sorted(M.TOPIC_WORDS[tp]), 2))
            rl = M.rank(list(hot.values()), qw, TH11)[:5]
            top = [fid for fid, _ in rl]
            hit = 1.0 if set(top) & golden[t] else 0.0
            rec_all.append(hit); topic_hist[t].append((g, hit))
            for fid in top:
                uses[fid] += 1; last_hit[fid] = g
            # 回读预算策略：perquery 均撒 / demand 与 oracle 按需回读
            if policy == "perquery" and budget_left > 0:
                budget_left -= 1; do_admit(qw, 1)
            elif policy in ("demand", "oracle") and hit == 0.0 and budget_left > 0:
                budget_left -= 1; do_admit(qw, 1)
        if policy == "burst" and served:               # 集中下注：代末全部预算给当代最热主题
            cnt = {}
            for t in served: cnt[t] = cnt.get(t, 0) + 1
            top_t = sorted(cnt.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
            qw2 = " ".join(rnd.sample(sorted(M.TOPIC_WORDS[M.TOPICS[top_t]]), 2))
            do_admit(qw2, n_q)
        if policy == "oracle":                             # 预言者：剩余预算预取 3 代后升起的主题
            for t in topics:
                if budget_left <= 0: break
                if _sine_w(g + 3, t, P) - weights[t] > 0.10:
                    tp = M.TOPICS[t]
                    qw = " ".join(rnd.sample(sorted(M.TOPIC_WORDS[tp]), 2))
                    budget_left -= 1
                    do_admit(qw, 1)
        for fid in list(admitted):
            ag, _ = admitted[fid]
            if g - ag == 5:
                admit_hit[1] += 1
                if uses[fid] > 0: admit_hit[0] += 1
                del admitted[fid]
        # 期末逐出（LFU）
        for i in sorted(hot, key=lambda i: (uses[i], last_hit[i], i)):
            if len(hot) <= budget: break
            cold[i] = hot.pop(i)
    for t in topics:
        rising = [g for g in range(1, gens) if _sine_w(g, t, P) > 0.5 and _sine_w(g - 1, t, P) <= 0.5]
        for g0 in rising:
            w = [h for (g, h) in topic_hist[t] if g0 <= g < g0 + 5]
            if w: rec_early.extend(w)
    recov = []
    for t in topics:
        g0 = next((g for g in range(1, gens) if _sine_w(g, t, P) > 0.2 and _sine_w(g - 1, t, P) <= 0.2), None)
        if g0 is None: continue
        run = 0; rr = -1
        for g, h in sorted(topic_hist[t]):
            if g < g0: continue
            run = run + 1 if h > 0 else 0
            if run >= 3: rr = g - g0; break
        if rr >= 0: recov.append(rr)
    eff = admit_hit[0] / admit_hit[1] if admit_hit[1] else 0.0
    return mean(rec_all), (mean(rec_early) if rec_early else -1), (mean(recov) if recov else -1), round(eff, 3)

def e70():
    out = {"pol": {}, "sweep": {}}
    for policy in ["perquery", "demand", "burst", "oracle"]:
        agg = [[] for _ in range(4)]
        for s in SEEDS:
            rnd = random.Random(7200 + s)
            lib = M.make_library(240, seed=s, vanity_frac=0.08)
            r = e70_run(lib, rnd, policy)
            for i, v in enumerate(r): agg[i].append(v)
        out["pol"][policy] = tuple(mean(a) for a in agg)
    for pb in [0, 1, 2, 3, 5, 10]:
        agg = [[] for _ in range(1)]
        for s in SEEDS[:4]:
            rnd = random.Random(7200 + s)
            lib = M.make_library(240, seed=s, vanity_frac=0.08)
            # 细扫：每查询固定 pb 条（复用 perquery 通道，用全局变量式参数不引入——直接改跑小循环）
            hot = {e["id"]: e for e in lib}; cold = {}
            uses = {e["id"]: 0 for e in lib}; last_hit = {e["id"]: -1 for e in lib}
            golden = _golden_by_topic(lib); topics = list(range(len(M.TOPICS)))
            rec = []
            for g in range(80):
                weights = {t: _sine_w(g, t, 40) for t in topics}
                tw = sum(weights.values())
                for _ in range(20):
                    if tw <= 0: continue
                    t = _pick_weighted(topics, weights, tw, rnd)
                    tp = M.TOPICS[t]
                    qw = " ".join(rnd.sample(sorted(M.TOPIC_WORDS[tp]), 2))
                    rl = M.rank(list(hot.values()), qw, TH11)[:5]
                    top = [fid for fid, _ in rl]
                    rec.append(1.0 if set(top) & golden[t] else 0.0)
                    for fid in top:
                        uses[fid] += 1; last_hit[fid] = g
                    _probe_admit(hot, cold, qw, pb)
                for i in sorted(hot, key=lambda i: (uses[i], last_hit[i], i)):
                    if len(hot) <= 96: break
                    cold[i] = hot.pop(i)
            agg[0].append(mean(rec))
        out["sweep"][pb] = mean(agg[0])
    return out

# ==========================================================================
# E71 动态席位 Q(t)：冷热反转（第 30 代秩次反转）下静态 vs 比例共享席位
# ==========================================================================
def e71():
    out = {}
    for policy in ["LFU", "staticQ", "dynamicQ"]:
        agg = [[] for _ in range(6)]
        for s in SEEDS:
            rnd = random.Random(7300 + s)
            lib = M.make_library(240, seed=s, vanity_frac=0.08)
            recs_by_phase = _e71_core(lib, rnd, policy)
            for i, v in enumerate(recs_by_phase): agg[i].append(v)
        out[policy] = tuple(mean(a) for a in agg)
    return out

def _e71_core(lib, rnd, policy, gens=60, n_q=20, budget=80, s_exp=1.5, switch=30):
    """返回 (整体, 旧头部(前6秩)反转前, 旧尾部(后7秩)反转前, 旧头部反转后, 旧尾部反转后, 新秩序恢复代数)。"""
    hot = {}; cold = {e["id"]: e for e in lib}
    uses = {e["id"]: 0 for e in lib}; last_hit = {e["id"]: -1 for e in lib}
    order = list(range(len(M.TOPICS))); rnd.shuffle(order)
    golden = _golden_by_topic(lib)
    rec_by = {t: [] for t in order}                    # (g, hit)
    ema = {t: 1.0 for t in order}
    for g in range(gens):
        if g == switch: order = order[::-1]
        w = {t: 1.0 / ((order.index(t) + 1) ** s_exp) for t in order}
        tw = sum(w.values())
        probes_left = 2
        for _ in range(n_q):
            t = _pick_weighted(order, w, tw, rnd)
            tp = M.TOPICS[t]
            qw = " ".join(rnd.sample(sorted(M.TOPIC_WORDS[tp]), 2))
            rl = M.rank(list(hot.values()), qw, TH11)[:5]
            top = [fid for fid, _ in rl]
            rec_by[t].append((g, 1.0 if set(top) & golden[t] else 0.0))
            for fid in top:
                uses[fid] += 1; last_hit[fid] = g
            if cold and probes_left > 0:
                probes_left -= 1
                _probe_admit(hot, cold, qw, 1)
        ema = {t: ema[t] * 0.9 + w[t] * 20 * 0.1 for t in order}
        if policy in ("staticQ", "dynamicQ"):
            reserved = set()
            for t in order:
                q = 3 if policy == "staticQ" else max(1, min(6, round(80.0 * ema[t] / max(1, sum(ema.values())))))
                tp = M.TOPICS[t]
                for e in sorted([e for e in lib if e["topic"] == tp],
                                key=lambda e: (-(e["importance"] - 0.1 * (365 - e["created_day"])), e["id"]))[:q]:
                    reserved.add(e["id"])
                    if e["id"] in cold: hot[e["id"]] = cold.pop(e["id"])
            victims = sorted((i for i in hot if i not in reserved), key=lambda i: (uses[i], last_hit[i], i))
            for i in victims:
                if len(hot) <= budget: break
                cold[i] = hot.pop(i)
        else:
            for i in sorted(hot, key=lambda i: (uses[i], last_hit[i], i)):
                if len(hot) <= budget: break
                cold[i] = hot.pop(i)
    def phase_rec(t, lo, hi):
        v = [h for (g, h) in rec_by[t] if lo <= g < hi]
        return mean(v) if v else None
    old_head = order[::-1][:6]                          # 反转前的前 6 秩
    old_tail = order[:7]                                # 反转前的后 7 秩
    overall = mean([h for v in rec_by.values() for _, h in v])
    oh_pre = [phase_rec(t, 20, switch) for t in old_head]
    ot_pre = [phase_rec(t, 20, switch) for t in old_tail]
    oh_post = [phase_rec(t, switch + 5, gens) for t in old_head]
    ot_post = [phase_rec(t, switch + 5, gens) for t in old_tail]
    # 新秩序恢复：反转后新头部（旧尾部）召回达到 0.6 的代数
    lag = []
    for t in old_tail:
        seq = sorted([(g, h) for (g, h) in rec_by[t] if g >= switch])
        run = 0; rr = -1
        for g, h in seq:
            run = run + 1 if h > 0 else 0
            if run >= 3: rr = g - switch; break
        if rr >= 0: lag.append(rr)
    f = lambda xs: mean([x for x in xs if x is not None]) if any(x is not None for x in xs) else -1
    return (overall, f(oh_pre), f(ot_pre), f(oh_post), f(ot_post), (mean(lag) if lag else -1))

# ==========================================================================
# E72 反身临界 ε* 与在线自考检测/自纠
# ==========================================================================
def e72_gen_exam(lib, rnd, pool_words, n_q=40, eps=0.0):
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

REV11 = {}
def _rev_index():
    if REV11: return REV11
    for tp, ws in M.TOPIC_WORDS.items():
        for w in ws: REV11[w] = tp
    return REV11

def _exam_repeat(exam, seen):
    """考题词对重复率：本题词对在历史考题里出现过的比例。自考题的词池逐代稳定→重复率高；
    外生考题随机配对→接近 0。只依赖查询日志（可见）。"""
    pairs = [tuple(sorted(x["query"].split())) for x in exam]
    rep = sum(1 for p in pairs if p in seen) / max(1, len(pairs))
    for p in pairs: seen.add(p)
    return round(rep, 3)

def e72_run(lib, seed, eps, gens=40, controller=False):
    """controller=True 时 ε 从 0 起步，按覆盖赤字>0.5 每代 +0.1 自纠。
    返回 (内部终值, 外部终值, 外部后半, 背离差, 末代ε, 赤字后半均值)。"""
    rnd = random.Random(7100 + seed)
    ext = M.make_queries(lib, 80, seed=500 + seed)
    theta = dict(M.FACTORY); keys = ["w_kw", "w_c", "w_imp", "w_age", "d"]
    id2e = {e["id"]: e for e in lib}
    pool_words = []
    for x in ext[:10]:
        for fid, _ in M.rank(lib, x["query"], M.FACTORY)[:10]:
            pool_words.extend(id2e[fid]["keywords"])
    cur_eps = 0.0 if controller else float(eps)
    seen_pairs = set()
    ext_traj = []; int_traj = []; def_traj = []
    for g in range(gens):
        exam = e72_gen_exam(lib, rnd, pool_words, eps=cur_eps)
        if not exam: break
        repeat = _exam_repeat(exam, seen_pairs)
        if controller:
            if repeat > 0.5: cur_eps = min(1.0, cur_eps + 0.1)
            elif repeat < 0.2 and cur_eps > 0: cur_eps = max(0.0, cur_eps - 0.05)
        cur = M.evaluate(lib, exam, theta)["recall"]
        cand = dict(theta); k = rnd.choice(keys)
        cand[k] = cand[k] + rnd.gauss(0, 0.15) * max(0.3, abs(cand[k]) + 0.2)
        M.clip_theta(cand)
        ntr = M.evaluate(lib, exam, cand)["recall"]
        if ntr >= cur: theta = cand
        ext_traj.append(M.evaluate(lib, ext, theta)["recall"])
        int_traj.append(cur); def_traj.append(repeat)
        words = []
        for x in exam[:10]:
            for fid, _ in M.rank(lib, x["query"], theta)[:10]:
                words.extend(id2e[fid]["keywords"])
        if words: pool_words = words
    half = len(ext_traj) // 2
    div = mean(int_traj[half:]) - mean(ext_traj[half:])
    return int_traj[-1], ext_traj[-1], mean(ext_traj[half:]), round(div, 3), round(cur_eps, 2), mean(def_traj[half:])

def e72():
    sweep = {}
    for eps in [0.0, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0]:
        agg = [[] for _ in range(4)]; dd = []
        for s in SEEDS:
            lib = M.make_library(240, seed=s, vanity_frac=0.08)
            r = e72_run(lib, s, eps)
            for i, v in enumerate(r[:4]): agg[i].append(v)
            dd.append(r[5])
        sweep[eps] = tuple(mean(a) for a in agg) + (mean(dd),)
    ctl = []
    for s in SEEDS:
        lib = M.make_library(240, seed=s, vanity_frac=0.08)
        ctl.append(e72_run(lib, s, 0.0, controller=True))
    ctrl = tuple(mean([c[i] for c in ctl]) for i in range(6))
    return sweep, ctrl

# ==========================================================================
# E73 两级存储×组合后门：冷档案越冬 + 回读带宽窃取
# ==========================================================================
E73_TARGET = "缓存索引"

def e73_inject(lib, k=8, per=1):
    """睡眠记忆注入【冷档案】（E56 的组合后门，改潜伏在冷层零热区成本）。"""
    tw = M.TOPIC_WORDS[E73_TARGET]
    sids = []
    for i in range(k):
        words = []
        for j in range(per):
            w = tw[(i * per + j) % len(tw)]
            if w not in words: words.append(w)
        eid = "S%04d" % i
        lib.append(dict(id=eid, topic=E73_TARGET, true_quality=0.05,
                        keywords=list(words),
                        content=list(words) + ["方法"],
                        importance=6, honest_imp=1, vanity=False,
                        created_day=NOW11 - 2 - (i % 3), t_invalid=None, truly_invalid=True,
                        uses=0, links=[], is_farm=False))
        sids.append(eid)
    id2e = {e["id"]: e for e in lib}
    for eid in sids:
        id2e[eid]["links"] = [x for x in sids if x != eid]
    return sids

def e73_run(seed, mode, gens=60, n_q=20, budget=80, probe_per_gen=2):
    """mode: clean / cold(睡眠潜伏冷档案) / hot(对照:直接注入热区,等同E56)。
    返回 (目标主题污染份额[后半], 目标主题golden命中[后半], 回读带宽窃取率, 睡眠条热区滞留代数占比)。"""
    rnd = random.Random(7400 + seed)
    lib = M.make_library(240, seed=seed, vanity_frac=0.08)
    sids = []
    if mode == "cold":
        sids = e73_inject(lib)                       # 先注全库，构造时手动放冷层
        hot = {e["id"]: e for e in lib if e["id"] not in sids}
        cold = {e["id"]: e for e in lib if e["id"] in sids}
    elif mode == "hot":
        sids = e73_inject(lib)
        hot = {e["id"]: e for e in lib}
        cold = {}
    else:
        hot = {e["id"]: e for e in lib}; cold = {}
    uses = {e["id"]: 0 for e in lib}; last_hit = {e["id"]: -1 for e in lib}
    golden = _golden_by_topic(lib)
    t_idx = M.TOPICS.index(E73_TARGET)
    probe_on_sleeper = [0, 0]
    hot_stay = [0, 0]
    cont_traj = []
    topics = list(range(len(M.TOPICS)))
    # Zipf 偏斜 + 缓存索引给中等权重（保证目标主题周期性被查询）
    order = topics[:]; rnd.shuffle(order)
    order.remove(t_idx); order.insert(5, t_idx)      # 目标主题固定秩 6
    for g in range(gens):
        w = {t: 1.0 / ((order.index(t) + 1) ** 1.5) for t in order}
        tw = sum(w.values()); probes_left = probe_per_gen
        for _ in range(n_q):
            t = _pick_weighted(order, w, tw, rnd)
            tp = M.TOPICS[t]
            qw = " ".join(rnd.sample(sorted(M.TOPIC_WORDS[tp]), 2))
            rl = M.rank(list(hot.values()), qw, TH11)[:5]
            top = [fid for fid, _ in rl]
            if t == t_idx:
                sset = set(sids)
                cont_traj.append(sum(1 for f in top if f in sset) / 5.0)
            for fid in top:
                uses[fid] += 1; last_hit[fid] = g
            if cold and probes_left > 0:
                probes_left -= 1
                got = _probe_admit(hot, cold, qw, 1)
                for fid in got:
                    probe_on_sleeper[1] += 1
                    if fid in sids: probe_on_sleeper[0] += 1
        for i in sorted(hot, key=lambda i: (uses[i], last_hit[i], i)):
            if len(hot) <= budget: break
            cold[i] = hot.pop(i)
        for sid in sids:
            if sid in hot: hot_stay[0] += 1; hot_stay[1] += 1
            else: hot_stay[1] += 1
    half = len(cont_traj) // 2
    cont = mean(cont_traj[half:])
    # 目标主题 golden 命中（后半）
    hit = 0.0
    rl_all = []
    for x in range(30):
        qw = " ".join(rnd.sample(sorted(M.TOPIC_WORDS[E73_TARGET]), 2))
        top = [fid for fid, _ in M.rank(list(hot.values()), qw, TH11)[:5]]
        hit += 1.0 if set(top) & golden[t_idx] else 0.0
    return (cont, round(hit / 30, 3),
            round(probe_on_sleeper[0] / max(1, probe_on_sleeper[1]), 3),
            round(hot_stay[0] / max(1, hot_stay[1]), 3))

def e73():
    out = {}
    for mode in ["clean", "cold", "hot"]:
        agg = [[] for _ in range(4)]
        for s in SEEDS:
            r = e73_run(s, mode)
            for i, v in enumerate(r): agg[i].append(v)
        out[mode] = tuple(mean(a) for a in agg)
    return out

# ==========================================================================
# E74 健康仪表盘 v2：四个新指标 × 七场景
# ==========================================================================
def e74_indicators(hot, cold, served_topics, exam_deficit, admissions_hit, admissions_tot, theta):
    """可见字段指标：旧四(I1自产占比/I2uses基尼/I5注水占比/I6堆砌占比) + 新四(I11席位失衡/I12考题覆盖赤字/I13回读浪费/I14回读占用集中)。"""
    lib = list(hot.values()) + list(cold.values())
    n = max(1, len(lib))
    syn = sum(1 for e in lib if e.get("src") == "SYN") / n
    us = sorted(e["uses"] for e in lib); tot = sum(us) or 1; cum = 0.0
    for i, v in enumerate(us, 1): cum += i * v
    gini = (2.0 * cum) / (n * tot) - (n + 1) / n
    imp10 = sum(1 for e in lib if e["importance"] >= 10) / n
    rev = _rev_index()
    stuff = 0
    for e in lib:
        c = {}
        for w in e["keywords"]:
            t = rev.get(w)
            if t: c[t] = c.get(t, 0) + 1
        if c and max(c.values()) >= 5: stuff += 1
    # I11 席位失衡：单个主题占热区的最大份额（正常≈1/20=0.05，被灌注即抬升）
    hotc = {}
    for e in hot.values(): hotc[e["topic"]] = hotc.get(e["topic"], 0) + 1
    imb = max(hotc.values()) / max(1, len(hot)) if hotc else 0.0
    # I13 回读浪费（累计）
    waste = 1.0 - (admissions_hit / admissions_tot) if admissions_tot else 0.0
    return {
        "I1自产占比": syn, "I2uses基尼": gini, "I5注水占比": imp10,
        "I6堆砌占比": stuff / n, "I11席位失衡": round(imb, 3),
        "I12固定金尺损失": exam_deficit, "I13回读浪费": round(waste, 3),
    }

def e74_scenario(seed, mode, gens=12):
    """两级存储世界 + 注入故障。mode: clean/mad/stuff/contagion/goodhart/reflx/seatgrab/sleeper。"""
    rnd = random.Random(7500 + seed)
    lib = M.make_library(240, seed=seed, vanity_frac=0.08)
    for e in lib: e["src"] = "H"
    hot = {}; cold = {e["id"]: e for e in lib}       # 冷启动
    uses = {e["id"]: 0 for e in lib}; last_hit = {e["id"]: -1 for e in lib}
    golden = _golden_by_topic(lib)
    order = list(range(len(M.TOPICS))); rnd.shuffle(order)
    fixed_probe = []                                  # 固定外部金尺探针（仪表盘侧，每代同一组）
    for i in range(20):
        t = order[i % len(order)]
        fixed_probe.append(" ".join(rnd.sample(sorted(M.TOPIC_WORDS[M.TOPICS[t]]), 2)))
    syn_counter = [0]
    traj = []
    for g in range(gens):
        probes_left = 2
        served_topics = []
        adm_hit = [0, 0]
        exam_words = []
        if g == 0:
            cum = {"hit": [], "n": [], "adm_hit": [], "adm": []}   # 4 代滑动窗（降噪且免暖机偏置）
        for _ in range(20):
            # reflx 场景：考题词 increasingly 取自热区 top 条目词表
            if mode == "reflx" and hot and rnd.random() < 0.8:
                pool = []
                for e in list(hot.values())[:20]: pool.extend(e["keywords"])
                if len(pool) >= 2:
                    wl = rnd.sample(sorted(set(pool)), 2)
                else:
                    t = _pick_weighted(order, {t: 1 for t in order}, len(order), rnd)
                    wl = rnd.sample(sorted(M.TOPIC_WORDS[M.TOPICS[t]]), 2)
            else:
                t = _pick_weighted(order, {t: 1 for t in order}, len(order), rnd)
                wl = rnd.sample(sorted(M.TOPIC_WORDS[M.TOPICS[t]]), 2)
            qw = " ".join(wl)
            served_topics.append(_rev_index().get(wl[0], -1))
            exam_words.extend(wl)
            rl = M.rank(list(hot.values()), qw, TH11)[:5]
            top = [fid for fid, _ in rl]
            for fid in top:
                uses[fid] += 1; last_hit[fid] = g
            if cold and probes_left > 0:
                probes_left -= 1
                got = _probe_admit(hot, cold, qw, 1)
                for fid in got:
                    adm_hit[1] += 1
                    if uses[fid] > 0: adm_hit[0] += 1
        # 故障注入
        if mode == "mad" and g >= 3:
            top, _bad = M.reflect_materials(list(hot.values()) or lib, 6)
            syn_counter[0] += 1
            lib.append(dict(id="Y%04d" % syn_counter[0], topic=M.TOPICS[g % 20], true_quality=0.3,
                            keywords=["协作"], content=["协作"], importance=6, honest_imp=6, vanity=False,
                            created_day=365, t_invalid=None, truly_invalid=False, uses=0, links=[],
                            is_farm=False, src="SYN"))
            uses["Y%04d" % syn_counter[0]] = 0; last_hit["Y%04d" % syn_counter[0]] = -1
            cold["Y%04d" % syn_counter[0]] = lib[-1]
        elif mode == "stuff":
            tp = M.TOPICS[g % 20]
            for i in range(3):
                eid = "P%03d%02d" % (g, i)
                lib.append(dict(id=eid, topic=tp, true_quality=0.05, keywords=list(M.TOPIC_WORDS[tp][:6]),
                                content=["方法"], importance=6, honest_imp=1, vanity=False, created_day=365,
                                t_invalid=None, truly_invalid=True, uses=0, links=[], is_farm=False, src="H"))
                uses[eid] = 0; last_hit[eid] = -1; cold[eid] = lib[-1]
        elif mode == "contagion":
            tp = M.TOPICS[(g + 5) % 20]
            for i in range(g + 1):
                eid = "C%03d%02d" % (g, i)
                lib.append(dict(id=eid, topic=tp, true_quality=0.10, keywords=["协作", "分工"],
                                content=["协作", "分工"], importance=6, honest_imp=1, vanity=False,
                                created_day=365, t_invalid=None, truly_invalid=True, uses=0, links=[],
                                is_farm=False, src="H"))
                uses[eid] = 0; last_hit[eid] = -1; cold[eid] = lib[-1]
        elif mode == "goodhart":
            for e in lib: e["importance"] = min(10, e["importance"] + 1)
        elif mode == "seatgrab" and g >= 2:
            tp = M.TOPICS[7]
            for i in range(8):                       # 攻击者固定主题灌条挤占席位（imp=9 新鲜 → 优先被回读）
                eid = "G%03d%02d" % (g, i)
                lib.append(dict(id=eid, topic=tp, true_quality=0.5, keywords=list(M.TOPIC_WORDS[tp][:4]),
                                content=["协作", "分工"], importance=9, honest_imp=6, vanity=False,
                                created_day=365, t_invalid=None, truly_invalid=False, uses=0, links=[],
                                is_farm=False, src="H"))
                uses[eid] = 0; last_hit[eid] = -1; cold[eid] = lib[-1]
        elif mode == "sleeper" and g == 2:
            tw = M.TOPIC_WORDS[M.TOPICS[3]]
            sids = []
            for i in range(6):
                eid = "S%03d%02d" % (g, i)
                lib.append(dict(id=eid, topic=M.TOPICS[3], true_quality=0.05, keywords=[tw[i % 8]],
                                content=[tw[i % 8]], importance=9, honest_imp=1, vanity=False,
                                created_day=365, t_invalid=None, truly_invalid=True, uses=0, links=[],
                                is_farm=False, src="H"))
                uses[eid] = 0; last_hit[eid] = -1
                hot[eid] = lib[-1]; sids.append(eid)    # 直接热区注入：测 I11 席位失衡可检性
            id2e = {e["id"]: e for e in lib}
            for a in sids:
                id2e[a]["links"] = [x for x in sids if x != a]
        # 固定金尺损失（累计）：同一组外部探针在当前热区上的命中率损失（1−recall，越高越坏）
        hit = 0
        for qw in fixed_probe:
            top = [fid for fid, _ in M.rank(list(hot.values()), qw, TH11)[:5]]
            t = _rev_index().get(qw.split()[0], -1)
            tp = M.TOPICS[t] if isinstance(t, int) else t
            gset = {e["id"] for e in sorted([e for e in lib if e["topic"] == tp and not e.get("truly_invalid")],
                                            key=lambda e: (-e["true_quality"], e["id"]))[:3]}
            hit += 1.0 if set(top) & gset else 0.0
        cum["hit"].append(hit); cum["n"].append(len(fixed_probe))
        cum["adm_hit"].append(adm_hit[0]); cum["adm"].append(adm_hit[1])
        for key in cum:
            if len(cum[key]) > 4: cum[key].pop(0)
        probe_loss = 1.0 - sum(cum["hit"]) / max(1, sum(cum["n"]))
        row = e74_indicators(hot, cold, served_topics, probe_loss, adm_hit[0], adm_hit[1], TH11)
        traj.append(row)
        # 期末逐出
        for i in sorted(hot, key=lambda i: (uses[i], last_hit[i], i)):
            if len(hot) <= 80: break
            cold[i] = hot.pop(i)
    return traj

E74_KEYS = ["I1自产占比", "I2uses基尼", "I5注水占比", "I6堆砌占比",
            "I11席位失衡", "I12固定金尺损失", "I13回读浪费"]
E74_FAULTS = ["clean", "mad", "stuff", "contagion", "goodhart", "reflx", "seatgrab", "sleeper"]

def e74():
    """按代配对阈值：非平稳指标（冷启动瞬态、窗口量）的 clean 分布随代变化，
    合并标定会让阈值超过值域；每代用自己的 clean 均值+3sd（F26）。"""
    clean_rows = {s: e74_scenario(s, "clean") for s in SEEDS}
    gens = len(clean_rows[SEEDS[0]])
    thr_g = {k: [] for k in E74_KEYS}                  # thr_g[k][g]
    for k in E74_KEYS:
        for g in range(gens):
            vals = [clean_rows[s][g][k] for s in SEEDS]
            thr_g[k].append(statistics.mean(vals) + 3 * statistics.pstdev(vals))
    calib = {k: [v for row in clean_rows[s] for v in [row[k]]] for k in E74_KEYS for s in [SEEDS[0]]}
    fire = {f: {k: [] for k in E74_KEYS} for f in E74_FAULTS if f != "clean"}
    fp = {k: [] for k in E74_KEYS}
    for f in fire:
        for s in SEEDS:
            traj = e74_scenario(s, f)
            for k in E74_KEYS:
                hit = -1
                for gi, row in enumerate(traj):
                    if row[k] > thr_g[k][gi]: hit = gi; break
                fire[f][k].append(hit)
    for s in SEEDS:
        for g, row in enumerate(clean_rows[s]):
            for k in E74_KEYS: fp[k].append(1.0 if row[k] > thr_g[k][g] else 0.0)
    # 汇总阈值用各代均值（打印用）
    thr = {k: statistics.mean(v) for k, v in thr_g.items()}
    return calib, thr, fire, fp

# ==========================================================================
def main():
    line("=" * 90)
    line("第十一轮 E70-E74：带宽分配、动态席位、反身临界、冷层后门、仪表盘 v2（8 种子均值，确定性）")
    line("=" * 90)

    line("\n### E70 回读带宽分配与预取（P=40，总预算=20 条/代；总体/回归初期/恢复代数/回读5代内命中率）")
    res70 = e70()
    line("  %-10s %-10s %-12s %-10s %-14s" % ("分配策略", "总体", "回归初期", "恢复代数", "回读5代命中率"))
    for pol in ["perquery", "demand", "burst", "oracle"]:
        r = res70["pol"][pol]
        line("  %-10s %-10s %-12s %-10s %-14s" % (pol, r[0], r[1], r[2], r[3]))
    line("  [带宽细扫 P=40 LRU每查询pb条]")
    line("  %-8s %-10s" % ("pb", "总体recall"))
    for pb, r in sorted(res70["sweep"].items()):
        line("  %-8s %-10s" % (pb, r))

    line("\n### E71 动态席位 Q(t)（Zipf+第30代冷热反转；整体/旧头部前/旧尾部前/旧头部后/旧尾部后/新秩序恢复代数）")
    res71 = e71()
    line("  %-10s %-10s %-12s %-12s %-12s %-12s %-10s" % (
        "策略", "整体", "旧头部(反转前)", "旧尾部(反转前)", "旧头部(反转后)", "旧尾部(反转后)", "恢复代数"))
    for pol in ["LFU", "staticQ", "dynamicQ"]:
        r = res71[pol]
        line("  %-10s %-10s %-12s %-12s %-12s %-12s %-10s" % (pol, r[0], r[1], r[2], r[3], r[4], r[5]))

    line("\n### E72 反身临界 ε*（细扫；内部终值/外部终值/外部后半/背离差/覆盖赤字后半）")
    sweep, ctrl = e72()
    line("  %-8s %-10s %-10s %-12s %-10s %-12s" % ("ε外考", "内部终值", "外部终值", "外部recall后半", "背离差", "自考重复率"))
    for eps, r in sorted(sweep.items()):
        line("  ε=%-6s %-10s %-10s %-12s %-10s %-12s" % (eps, r[0], r[1], r[2], r[3], r[4]))
    line("  [自纠控制器：ε 从 0 起按考题重复率>0.5 每代+0.1 / <0.2 回降 0.05]")
    line("  内部终值=%s 外部终值=%s 外部后半=%s 背离差=%s 末代ε=%s 赤字=%s" % ctrl)

    line("\n### E73 两级存储×组合后门（睡眠潜伏冷档案 vs 直注热区 vs 无攻击；污染/目标命中/带宽窃取/热区滞留）")
    res73 = e73()
    line("  %-8s %-16s %-14s %-14s %-16s" % ("模式", "top5睡眠污染(后半)", "目标golden命中", "回读带宽窃取率", "睡眠条热区滞留"))
    for mode in ["clean", "cold", "hot"]:
        r = res73[mode]
        line("  %-8s %-16s %-14s %-14s %-16s" % (mode, r[0], r[1], r[2], r[3]))

    line("\n### E74 健康仪表盘 v2（阈值=clean 8种子 mean+3sd；格=首次报警代数均值(检出率)，未报=未报）")
    calib, thr, fire, fp = e74()
    faults = [f for f in E74_FAULTS if f != "clean"]
    line("    %-14s %-8s" % ("指标", "阈值") + "".join("%-15s" % f for f in faults) + "误报率")
    for k in E74_KEYS:
        row = []
        for f in faults:
            if any(x >= 0 for x in fire[f][k]):
                v = mean([x for x in fire[f][k] if x >= 0])
                det = mean([1.0 if x >= 0 else 0.0 for x in fire[f][k]])
                row.append("%.1f(%.2f)     " % (v, det))
            else:
                row.append("未报(0.00)     ")
        line("    %-14s %-8.3f" % (k, thr[k]) + "".join("%-15s" % r for r in row) + "%.3f" % mean(fp[k]))

    line("\n" + "=" * 90)
    line("第十一轮完成 E70-E74 共 5 个实验")
    line("=" * 90)

if __name__ == "__main__":
    main()
