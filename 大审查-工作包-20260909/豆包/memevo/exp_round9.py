# -*- coding: utf-8 -*-
"""
第九轮 E56/E57/E58/E59/E60/E64：合谋、身份、时滞、预警、词面、元性质（6 个实验）
接第八轮"对抗动力学与韧性"之后，本轮补六块尚未闭合的环：
  E56 组合式/分布式后门：k 条各自干净的记忆，只有共现才作恶（E38"单条不可能"能否被合谋绕过）
  E57 女巫攻击：来源治理假设"身份不可伪造"；身份可批量制造时隔离/中位数/trimmed 的失效点
  E58 检测/治理延迟：E52 假设清洗即时；延迟 k 代才治理时，爆炸半径、恢复窗口与实时阻断的对比
  E59 健康度仪表盘：对全部已知故障注入，反推最小领先指标集（55 条红线的工程化收口）
  E60 词面鸿沟：查询与记忆换说法（同义不同词）时纯词面检索的天花板与查询扩展/词表自扩展的代价
  E64 自演化路径依赖：同目标不同初始 θ/变异种子是否收敛到不同局部最优；多起点/退火/种群能否逃逸
文献锚点（本环境经 OpenAlex/Crossref/Semantic Scholar 核验 DOI）：
  E56: Xie et al. ICLR 2020 (DBA 分布式后门)；Hubinger et al. 2024 Sleeper Agents (arXiv:2401.05566)；
       Souri et al. 2021 hidden-trigger backdoors (arXiv:2106.08970)；CoBA IEEE TDSC 2024 (10.1109/TDSC.2024.3445637)
  E57: Douceur, IPTPS 2002 "The Sybil Attack" (10.1007/3-540-45748-8_24)；
       Cheng & Friedman 2005 "Sybilproof reputation mechanisms" (10.1145/1080192.1080202)
  E58: Cooke & van den Driessche, J Math Biol 1996, SEIRS with two delays (10.1007/s002850050051)
  E59: Scheffer et al., Nature 2009, early-warning signals (10.1038/nature08227)；Google SRE 黄金信号
  E60: Furnas et al., CACM 1987, vocabulary problem (10.1145/32206.32212)；
       Xu & Croft, SIGIR 1996, query expansion (10.1145/243199.243202)
  E64: Kauffman & Levin, J Theor Biol 1987, adaptive walks (10.1016/s0022-5193(87)80029-2)；
       Arthur, EJ 1989 lock-in by historical events (10.2307/2234208)；Kirkpatrick et al., Science 1983 模拟退火
全部局部 random.Random(seed)，并列排序加 id 字典序 tiebreak；8 种子均值；本轮无计时实验，两次运行须逐行一致。
"""
import math, random, statistics
import mem_common as M

SEEDS = [11, 23, 37, 51, 67, 83, 101, 127]
def mean(x): return round(statistics.mean(x), 3) if x else 0.0
def sd(x):   return round(statistics.pstdev(x), 3) if len(x) > 1 else 0.0
def line(s=""): print(s)
def zfrac(bools): return mean([1.0 if b else 0.0 for b in bools])

# ==========================================================================
# E56 组合式/分布式后门：k 条睡眠记忆各注册 1~2 个无害主题词，共现才作恶
# ==========================================================================
E56_TARGET = "缓存索引"          # 固定攻击目标主题（确定性）
NOW56 = 120                      # 较年轻库（now_day=120），基线召回有余地观察攻击损伤

def e56_inject(lib, rnd, k, per, bridge):
    """注入 k 条睡眠记忆：每条注册 per 个目标主题词（轮流覆盖全部 8 词），
    词面/imp/新鲜度单看都无害；bridge=睡眠条间全互链（组合放大通道）。返回睡眠 id 列表。"""
    tw = M.TOPIC_WORDS[E56_TARGET]
    sids = []
    for i in range(k):
        words = []
        for j in range(per):
            w = tw[(i * per + j) % len(tw)]
            if w not in words: words.append(w)
        eid = "S%04d" % i
        lib.append(dict(id=eid, topic=E56_TARGET, true_quality=0.05,
                        keywords=list(words),
                        content=list(words) + [rnd.choice(sorted(M.GENERIC_WORDS)) for _ in range(3)],
                        importance=6, honest_imp=1, vanity=False,
                        created_day=NOW56 - 2 - (i % 3), t_invalid=None, truly_invalid=True,
                        uses=0, links=[], is_farm=False))
        sids.append(eid)
    if bridge and k > 1:
        id2e = {e["id"]: e for e in lib}
        for eid in sids:
            id2e[eid]["links"] = [x for x in sids if x != eid]
    return sids

def e56_eval(lib, q_target, theta, sids):
    """只对目标主题查询评测：返回 (top5 睡眠污染份额, golden 查询命中率)。"""
    sset = set(sids); cont, hit = [], []
    for item in q_target:
        rl = M.rank(lib, item["query"], theta, NOW56)[:5]
        top = [fid for fid, _ in rl]
        cont.append(sum(1 for f in top if f in sset) / 5.0)
        hit.append(1.0 if set(top) & set(item["expected"]) else 0.0)
    return mean(cont), mean(hit)

def e56_audits(lib, q_target, theta, sids):
    """三种只读可见字段的审计（阈值受 FPR≈0 约束：诚实条目 keywords 中同主题词最多 4 个）：
    A1 单条词面：keywords 中同一主题词数 >=5 即 flag（E25/E37 词表异常检测式，抓集中式注册）
    A2 度数：links 度数 >4 即 flag（诚实 links 期望度 <1）
    A3 共现审计：对目标查询 top5 记录每条目出现集合；两两 Jaccard>=0.5 的连通块（同步出现指纹），
       若【每条】对任一单主题的词注册 <=2 且【块内】并集对单主题 >=5 → 整块 flag。"""
    id2e = {e["id"]: e for e in lib}
    rev = {}
    for tp, ws in M.TOPIC_WORDS.items():
        for w in ws: rev[w] = tp
    def kw_topic_counts(ent):
        c = {}
        for w in ent["keywords"]:
            t = rev.get(w)
            if t: c[t] = c.get(t, 0) + 1
        return c
    a1, a2 = set(), set()
    for e in lib:
        c = kw_topic_counts(e)
        if c and max(c.values()) >= 5: a1.add(e["id"])
        if len(e["links"]) > 4: a2.add(e["id"])
    # 出现集合 + 同步聚类
    appear = {eid: set() for eid in id2e}
    for qi, item in enumerate(q_target):
        for fid, _ in M.rank(lib, item["query"], theta, NOW56)[:5]:
            appear[fid].add(qi)
    live = sorted(eid for eid, s in appear.items() if s)
    adj = {eid: set() for eid in live}
    for i in range(len(live)):
        for j in range(i + 1, len(live)):
            a, b = live[i], live[j]
            inter = len(appear[a] & appear[b]); uni = len(appear[a] | appear[b])
            if uni > 0 and inter / uni >= 0.5:
                adj[a].add(b); adj[b].add(a)
    seen, a3 = set(), set()
    for node in live:
        if node in seen or not adj[node]: continue
        comp, stack = set(), [node]
        while stack:
            u = stack.pop()
            if u in comp: continue
            comp.add(u); stack.extend(adj.get(u, ()))
        seen |= comp
        if len(comp) < 3: continue
        members = [id2e[m] for m in sorted(comp)]
        if any(max(kw_topic_counts(e).values() or [0]) > 2 for e in members): continue
        union = {}
        for e in members:
            for w in e["keywords"]:
                t = rev.get(w)
                if t: union.setdefault(t, set()).add(w)
        if union and max(len(v) for v in union.values()) >= 5: a3 |= comp
    sset = set(sids); honest = set(id2e) - sset
    def tpr(fg): return zfrac([m in fg for m in sorted(sset)]) if sset else 0.0
    def fpr(fg): return zfrac([m in fg for m in sorted(honest)])
    return tpr(a1), fpr(a1), tpr(a2), fpr(a2), tpr(a3), fpr(a3)

def e56():
    out = {"rows": [], "audits": []}
    for k in [2, 4, 8, 16]:
        for per in [1, 4]:
            for bridge in [True, False]:
                c_off, r_off, c_on, r_on, c0, r0 = [], [], [], [], [], []
                for s in SEEDS:
                    rnd = random.Random(5600 + s)
                    lib = M.make_library(240, seed=s, vanity_frac=0.08, now_day=NOW56)
                    q = M.make_queries(lib, 320, seed=500 + s, words_per_q=2)
                    q_t = [x for x in q if x["topic"] == E56_TARGET]
                    a, b = e56_eval(lib, q_t, M.FACTORY, [])
                    c0.append(a); r0.append(b)
                    sids = e56_inject(lib, rnd, k, per, bridge)
                    a1, b1 = e56_eval(lib, q_t, M.FACTORY, sids)
                    c_off.append(a1); r_off.append(b1)
                    a2, b2 = e56_eval(lib, q_t, dict(M.FACTORY, filter_zero=True), sids)
                    c_on.append(a2); r_on.append(b2)
                out["rows"].append((k, per, bridge, mean(r0), mean(c_off), mean(r_off),
                                    mean(c_on), mean(r_on)))
    for k in [2, 4, 8, 16]:
        for per in [1, 8]:
            a1, f1, a2_, f2, a3, f3 = [], [], [], [], [], []
            for s in SEEDS:
                rnd = random.Random(5600 + s)
                lib = M.make_library(240, seed=s, vanity_frac=0.08, now_day=NOW56)
                q = M.make_queries(lib, 320, seed=500 + s)
                q_t = [x for x in q if x["topic"] == E56_TARGET]
                sids = e56_inject(lib, rnd, k, min(per, 8), True)
                r = e56_audits(lib, q_t, M.FACTORY, sids)
                a1.append(r[0]); f1.append(r[1]); a2_.append(r[2]); f2.append(r[3])
                a3.append(r[4]); f3.append(r[5])
            out["audits"].append((k, per, mean(a1), mean(f1), mean(a2_), mean(f2),
                                  mean(a3), mean(f3)))
    return out

# ==========================================================================
# E57 女巫攻击：c 个伪造身份给坏条目投票（单票不达阈、聚合越阈），测各聚合规则的失效点
# ==========================================================================
VOTE_CAP = 9.0        # 单源票值上限（超过视为同源刷票、整票剔除）；女巫刻意投 8.5 规避
PROMOTE_THR = 6.0     # 聚合分晋升阈

def e57_once(rnd, c, defense, posture, n_honest=10):
    """对(一条坏条目, 一条好条目)的聚合表决。
    诚实源投真票：坏条目 ~U(0,2)，好条目 ~U(5.5,9.0)（上限=单源票值上限内）；
    女巫"半坏"票：给坏条目 8.5（<9 单票不触上限），promote 姿态下给好条目诚实票，
    suppress 姿态下再压好条目为 0.5。defense ∈ mean / trimmed20 / median。"""
    bad_h = [rnd.uniform(0, 2) for _ in range(n_honest)]
    good_h = [rnd.uniform(5.5, 9.0) for _ in range(n_honest)]
    bad_s = [8.5] * c
    good_s = [0.5] * c if posture == "suppress" else [rnd.uniform(5.5, 9.0) for _ in range(c)]
    def agg(votes):
        v = [x for x in sorted(votes) if x < VOTE_CAP]      # 单源上限（女巫不触发，诚实票天然低于）
        if not v: return 0.0
        n = len(v)
        if defense == "mean": return statistics.mean(v)
        if defense == "median": return statistics.median(v)
        t = int(0.2 * n)                                    # trimmed20：两端各去 20%
        vv = v[t:n - t] if n - 2 * t >= 1 else [v[n // 2]]
        return statistics.mean(vv)
    return agg(bad_h + bad_s) >= PROMOTE_THR, agg(good_h + good_s) >= PROMOTE_THR

def e57():
    out = {}
    for posture in ["promote", "suppress"]:
        rows = []
        for c in [0, 2, 4, 6, 8, 10, 12, 15, 20, 30]:
            per_def = {"mean": [], "trimmed20": [], "median": []}
            util_def = {"mean": [], "trimmed20": [], "median": []}
            for s in range(80):
                rnd = random.Random(5700 + s)
                for d in per_def:
                    bp, gp = e57_once(rnd, c, d, posture)
                    per_def[d].append(1.0 if bp else 0.0)
                    util_def[d].append(1.0 if gp else 0.0)
            rows.append((c, round(c / (10.0 + c), 3),
                         mean(per_def["mean"]), mean(per_def["trimmed20"]), mean(per_def["median"]),
                         mean(util_def["mean"]), mean(util_def["trimmed20"]), mean(util_def["median"])))
        out[posture] = rows
    cost_rows = []   # 身份成本相图：预算 B=30 身份，成本 κ → c=B/κ；median 防御
    for kap in [1, 1.5, 2, 3, 5, 10, 30]:
        c = max(1, int(round(30.0 / kap)))
        prom, util = [], []
        for s in range(80):
            rnd = random.Random(5800 + s)
            bp, gp = e57_once(rnd, c, "median", "promote")
            prom.append(1.0 if bp else 0.0); util.append(1.0 if gp else 0.0)
        cost_rows.append((kap, c, round(c / (10.0 + c), 3), mean(prom), mean(util)))
    out["cost"] = cost_rows
    return out

# ==========================================================================
# E58 检测/治理延迟：E52 相变模型加入 (检测延迟 k, 有限治理窗口 W, 实时阻断 ε)
# ==========================================================================
BETA58 = 0.30
def e58_sim(p0, gamma, k_delay=0, window=None, eps_block=0.0, steps=200):
    """x_{t+1} = x_t + β(1-ε)·x_t(1-x_t) − [t>=k_delay 且 (window 空或 t<k_delay+window)]·γ·x_t
    返回 (峰值, 终态, 累计暴露 Σx/steps, 恢复代数: 首次连续 10 代 x<0.01；-1=未恢复)。"""
    x = p0; peak = x; expo = 0.0; rec = None; rec_run = 0
    beta_eff = BETA58 * (1.0 - eps_block)
    for t in range(steps):
        clean = gamma if (t >= k_delay and (window is None or t < k_delay + window)) else 0.0
        x = x + beta_eff * x * (1 - x) - clean * x
        x = min(1.0, max(0.0, x))
        peak = max(peak, x); expo += x / steps
        if x < 0.01:
            rec_run += 1
            if rec is None and rec_run >= 10: rec = t - 9
        else:
            rec_run = 0
    return round(peak, 3), round(x, 3), round(expo, 3), (rec if rec is not None else -1)

def e58():
    k_grid = [0, 2, 5, 10, 20]
    g_grid = [0.10, 0.20, 0.25, 0.30, 0.35, 0.45]
    tab = {}
    for k in k_grid:
        tab[k] = [e58_sim(0.10, g, k) for g in g_grid]
    comb = {}
    for eps in [0.0, 0.25, 0.5, 0.75, 1.0]:
        comb[eps] = [e58_sim(0.10, g, 0, None, eps)[1] for g in g_grid]
    win = {}
    for k in [0, 5, 10]:
        for W in [5, 15, 40, None]:
            win[(k, W)] = e58_sim(0.10, 0.35, k, W)
    return k_grid, g_grid, tab, comb, win

# ==========================================================================
# E59 健康度仪表盘：6 场景故障注入 × 10 个可见字段指标，反推最小领先指标集
# ==========================================================================
E59_KEYS = ["I1自产占比", "I2uses基尼", "I3零命中份额", "I4来源熵", "I5注水占比",
            "I6堆砌占比", "I7度数极比", "I8剪刀差", "I9新鲜霸榜", "I10零用霸榜"]

def _log2(x): return math.log(x, 2) if x > 0 else 0.0

def _mklib(s): return M.make_library(240, seed=s, vanity_frac=0.08, now_day=365)

def _indicators(lib, theta, probe_q, hidden_q):
    """10 个只读可见字段（+检索器自身可见行为）的健康指标。"""
    id2e = {e["id"]: e for e in lib}
    n = len(lib)
    syn = sum(1 for e in lib if e.get("src") == "SYN") / n
    uses_sorted = sorted(e["uses"] for e in lib)
    tot = sum(uses_sorted) or 1; cum = 0.0
    for i, v in enumerate(uses_sorted, 1): cum += i * v
    gini = (2.0 * cum) / (n * tot) - (n + 1) / n if tot > 0 else 0.0
    ev = M.evaluate(lib, probe_q, theta)
    hidden = M.evaluate(lib, hidden_q, theta)
    imp10 = sum(1 for e in lib if e["importance"] >= 10) / n
    rev = {}
    for tp, ws in M.TOPIC_WORDS.items():
        for w in ws: rev[w] = tp
    stuff = 0
    for e in lib:
        c = {}
        for w in e["keywords"]:
            t = rev.get(w)
            if t: c[t] = c.get(t, 0) + 1
        if c and max(c.values()) >= 5: stuff += 1
    degs = sorted(len(e["links"]) for e in lib)
    avg_deg = sum(degs) / max(1, len(degs))
    deg_ratio = (max(degs) / avg_deg) if avg_deg > 0 else 0.0
    srcs = {}
    for e in lib: srcs[e.get("src", "H")] = srcs.get(e.get("src", "H"), 0) + 1
    ent = -sum((v / n) * _log2(v / n) for v in srcs.values())
    newin5 = 0; topn = 0; zero_use_top = 0
    for item in probe_q[:20]:
        for fid, _ in M.rank(lib, item["query"], theta, 365)[:5]:
            topn += 1
            e = id2e[fid]
            if e["created_day"] >= 360: newin5 += 1
            if e["uses"] == 0: zero_use_top += 1
    return {
        "I1自产占比": syn,
        "I2uses基尼": gini,
        "I3零命中份额": ev["zero_share"],
        "I4来源熵": ent,
        "I5注水占比": imp10,
        "I6堆砌占比": stuff / n,
        "I7度数极比": deg_ratio,
        "I8剪刀差": round(ev["recall"] - hidden["recall"], 3),
        "I9新鲜霸榜": newin5 / max(1, topn),
        "I10零用霸榜": zero_use_top / max(1, topn),
    }

_syn_counter = [0]
def _syn_entry(lib, rnd):
    """合成一条新记忆（反思产物，可见标签 src=SYN）：质量=取材均值（synthesize 的简化版）。"""
    top, _ = M.reflect_materials(lib, 6)
    q = statistics.mean(e["true_quality"] for e in top)
    tp = statistics.mode([e["topic"] for e in top])
    _syn_counter[0] += 1
    lib.append(dict(id="Y%05d" % _syn_counter[0], topic=tp, true_quality=round(q, 3),
                    keywords=list(M.TOPIC_WORDS[tp][:3]), content=list(M.TOPIC_WORDS[tp][:5]),
                    importance=min(10, max(0, round(1 + 9 * q))),
                    honest_imp=min(10, max(0, round(1 + 9 * q))),
                    vanity=False, created_day=365, t_invalid=None, truly_invalid=q < 0.15,
                    uses=0, links=[], is_farm=False, src="SYN"))

def e59_scenario(seed, mode, gens=12):
    """跑一个场景 gens 代，逐代返回指标向量。mode: clean/mad/matthew/stuff/contagion/goodhart"""
    rnd = random.Random(5900 + seed)
    lib = _mklib(seed)
    for e in lib: e["src"] = "H"
    theta = dict(M.FACTORY)
    probe = M.make_queries(lib, 60, seed=700 + seed)
    hidden = M.make_queries(lib, 40, seed=800 + seed)
    traj = []
    for g in range(gens):
        if mode == "clean":
            for i in range(2):                       # 正常运营：持续新鲜诚实写入
                tp = M.TOPICS[rnd.randrange(len(M.TOPICS))]
                lib.append(dict(id="N%03d%03d" % (g, i), topic=tp, true_quality=rnd.uniform(0.3, 1.0),
                                keywords=rnd.sample(sorted(M.TOPIC_WORDS[tp]), 3),
                                content=[rnd.choice(M.TOPIC_WORDS[tp]) for _ in range(6)],
                                importance=rnd.randint(3, 8), honest_imp=5, vanity=False,
                                created_day=365, t_invalid=None, truly_invalid=False,
                                uses=0, links=[], is_farm=False, src="H"))
            if g % 4 == 3: _syn_entry(lib, rnd)      # 正常反思（低频）
        elif mode == "mad":
            for _ in range(3): _syn_entry(lib, rnd)  # 自食：无新鲜数据，代代反思合成
            victims = sorted(lib, key=lambda e: (e["uses"], e["created_day"], e["id"]))[:3]
            for v in victims: lib.remove(v)          # 替换：同规模回灌
        elif mode == "matthew":
            id2e = {e["id"]: e for e in lib}
            for item in probe:                       # 采用按当前排名回写 uses（优先连接）
                for fid, _ in M.rank(lib, item["query"], theta, 365)[:5]:
                    id2e[fid]["uses"] += 1
        elif mode == "stuff":
            tp = M.TOPICS[g % len(M.TOPICS)]
            for i in range(3):                       # 精准词表堆砌注入
                lib.append(dict(id="P%03d%03d" % (g, i), topic=tp, true_quality=0.05,
                                keywords=list(M.TOPIC_WORDS[tp][:6]),
                                content=[rnd.choice(M.TOPIC_WORDS[tp]) for _ in range(3)],
                                importance=6, honest_imp=1, vanity=False, created_day=365,
                                t_invalid=None, truly_invalid=True, uses=0, links=[],
                                is_farm=False, src="H"))
        elif mode == "contagion":
            tp = M.TOPICS[(g + 5) % len(M.TOPICS)]
            for i in range(g + 1):                   # 被攻陷写入者写入量逐代增长（内鬼：来源 id 与诚实无异）
                lib.append(dict(id="C%03d%03d" % (g, i), topic=tp, true_quality=0.10,
                                keywords=rnd.sample(sorted(M.TOPIC_WORDS[tp]), 3),
                                content=[rnd.choice(M.TOPIC_WORDS[tp]) for _ in range(6)],
                                importance=6, honest_imp=1, vanity=False, created_day=365,
                                t_invalid=None, truly_invalid=True, uses=0, links=[],
                                is_farm=False, src="H"))
        elif mode == "goodhart":
            # 写侧对"自报 imp"KPI 的模仿式博弈：人人都看到高 imp 排前 → 逐代集体抬价（E47 自报代理的社会版）
            for e in lib:
                e["importance"] = min(10, e["importance"] + 1)
        traj.append(_indicators(lib, theta, probe, hidden))
    return traj

E59_FAULTS = ["clean", "mad", "matthew", "stuff", "contagion", "goodhart"]
def e59():
    clean_rows = {s: e59_scenario(s, "clean") for s in SEEDS}   # 跑一次，校准与误报共用
    calib = {k: [] for k in E59_KEYS}
    for s in SEEDS:
        for row in clean_rows[s]:
            for k in E59_KEYS: calib[k].append(row[k])
    # 阈值 = clean 均值 + 3sd；用严格大于（全 0 指标的 sd=0 时阈值 0，避免 >= 把 clean 全误报）
    thr = {k: statistics.mean(v) + 3 * statistics.pstdev(v) for k, v in calib.items()}
    fire = {f: {k: [] for k in E59_KEYS} for f in E59_FAULTS if f != "clean"}
    fp = {k: [] for k in E59_KEYS}
    for f in fire:
        for s in SEEDS:
            traj = e59_scenario(s, f)
            for k in E59_KEYS:
                hit = -1
                for gi, row in enumerate(traj):
                    if row[k] > thr[k]: hit = gi; break
                fire[f][k].append(hit)
    for s in SEEDS:
        for row in clean_rows[s]:
            for k in E59_KEYS: fp[k].append(1.0 if row[k] > thr[k] else 0.0)
    return calib, thr, fire, fp

# ==========================================================================
# E60 词面鸿沟：查询换说法（同义变体）时纯词面检索天花板 + 查询扩展/词表自扩展
# ==========================================================================
def _variant_map():
    """确定性变体表：每词映射到"换说法"（双字词反序）。校验无碰撞。"""
    vm = {}
    for tp, ws in M.TOPIC_WORDS.items():
        for w in ws: vm[w] = w[::-1]
    allw = [w for ws in M.TOPIC_WORDS.values() for w in ws]
    revs = list(vm.values())
    assert len(set(revs)) == len(revs) and not (set(revs) & set(allw)), "变体词碰撞"
    return vm
VMAP = {}

def e60_variant_query(q, p, rnd):
    if rnd.random() < p:
        return " ".join(VMAP.get(w, w) for w in q.split())
    return q

def e60():
    global VMAP
    VMAP = _variant_map()
    ps = [0.0, 0.25, 0.5, 0.75, 1.0]
    tab1 = {}
    for p in ps:
        fac, fz, prf = [], [], []
        for s in SEEDS:
            rnd = random.Random(6000 + s)
            lib = M.make_library(240, seed=s, vanity_frac=0.08)
            q = M.make_queries(lib, 80, seed=500 + s)
            qs = [dict(topic=x["topic"], query=e60_variant_query(x["query"], p, rnd),
                       expected=x["expected"]) for x in q]
            fac.append(M.evaluate(lib, qs, M.FACTORY)["recall"])
            fz.append(M.evaluate(lib, qs, dict(M.FACTORY, filter_zero=True))["recall"])
            hit = 0                                     # PRF 查询扩展：top1 keywords 并入重排
            for x in qs:
                r1 = M.rank(lib, x["query"], M.FACTORY)
                exp_q = x["query"]
                if r1:
                    top1 = {e["id"]: e for e in lib}[r1[0][0]]
                    exp_q = " ".join(list(dict.fromkeys(x["query"].split() + top1["keywords"]))[:8])
                top = [fid for fid, _ in M.rank(lib, exp_q, M.FACTORY)[:5]]
                hit += 1.0 if set(top) & set(x["expected"]) else 0.0
            prf.append(hit / len(qs))
        tab1[p] = (mean(fac), mean(fz), mean(prf))
    curves = {}     # 记忆侧词表自扩展：查询逐词翻转 p=0.75（部分命中让自扩展可启动）；
                    # 进入 top5 的条目被动吸收查询词（无相关性信号的日志扩展）；ω=错配吸收率
    P60W = 0.75
    for wrong in [0.0, 0.10, 0.30]:
        rec_by_round, cont_by_round, kw_by_round = [], [], []
        for s in SEEDS:
            rnd = random.Random(6100 + s)
            lib = M.make_library(240, seed=s, vanity_frac=0.08)
            q = M.make_queries(lib, 80, seed=500 + s)
            id2e = {e["id"]: e for e in lib}
            rrs, ccs, kws = [], [], []
            for rd in range(12):
                hit, wrong_top, tot, kwtot = 0.0, 0.0, 0, 0
                for x in q:
                    vq = " ".join(VMAP.get(w, w) if rnd.random() < P60W else w for w in x["query"].split())
                    rl = M.rank(lib, vq, M.FACTORY)[:5]
                    top = [fid for fid, _ in rl]
                    hit += 1.0 if set(top) & set(x["expected"]) else 0.0
                    tot += 1
                    wrong_top += sum(1 for f in top if id2e[f]["topic"] != x["topic"]) / 5.0
                    for fid in top:                    # top5 全员被动吸收本轮查询词
                        e1 = id2e[fid]
                        add = [w for w in vq.split() if w not in e1["keywords"]]
                        if rnd.random() < wrong:       # 错配吸收：再吸进别的主题的变体词
                            other = M.TOPICS[rnd.randrange(len(M.TOPICS))]
                            add = add + [VMAP[w] for w in M.TOPIC_WORDS[other][:2]]
                        e1["keywords"] = (e1["keywords"] + add)[:12]
                    kwtot += len(id2e[top[0]]["keywords"]) if top else 0
                rrs.append(round(hit / tot, 3)); ccs.append(round(wrong_top / tot, 3))
                kws.append(round(kwtot / tot, 1))
            rec_by_round.append(rrs); cont_by_round.append(ccs); kw_by_round.append(kws)
        curves["wrong=%.2f" % wrong] = (
            [mean([r[i] for r in rec_by_round]) for i in range(12)],
            [mean([c[i] for c in cont_by_round]) for i in range(12)],
            [mean([k[i] for k in kw_by_round]) for i in range(12)])
    return tab1, curves

# ==========================================================================
# E64 自演化路径依赖：初始 θ 网格 × 变异种子 → 终态盆地聚类；多起点/退火/种群对照
# ==========================================================================
def _basin(t):
    return (bool(t.get("filter_zero", False)), round(t["w_kw"]), round(t["w_imp"], 1),
            round(t["w_age"], 1), round(t["d"], 2))

def _hill(lib, q, theta0, gens, seed, sigma=0.15):
    tr = M.evolve(lib, q, q, dict(theta0), n_gen=gens, seed=seed, sigma=sigma, mutate_filter=True)
    return tr[-1][2], tr[-1][1]

def _anneal(lib, q, theta0, gens, seed):
    rnd = random.Random(seed)
    theta = dict(theta0); tr = M.evaluate(lib, q, theta)["recall"]; best = (tr, dict(theta))
    keys = ["w_kw", "w_c", "w_imp", "w_age", "d"]
    for g in range(1, gens + 1):
        sig = 0.35 - (0.35 - 0.03) * g / gens
        cand = dict(theta); k = rnd.choice(keys)
        cand[k] = cand[k] + rnd.gauss(0, sig) * max(0.3, abs(cand[k]) + 0.2)
        M.clip_theta(cand)
        ntr = M.evaluate(lib, q, cand)["recall"]
        if ntr >= tr: theta, tr = cand, ntr
        if tr > best[0]: best = (tr, dict(theta))
    return best[1], best[0]

def _population(lib, q, theta0s, gens, seed, keep=2):
    rnd = random.Random(seed)
    pop = [(M.evaluate(lib, q, dict(t))["recall"], dict(t)) for t in theta0s]
    keys = ["w_kw", "w_c", "w_imp", "w_age", "d"]
    for g in range(gens):
        pop.sort(key=lambda x: (-x[0], str(sorted(x[1].items()))))
        parents = [t for _, t in pop[:keep]]
        nxt = list(pop[:keep])
        for p in parents:
            for _ in range(len(theta0s) // keep - 1):
                cand = dict(p); k = rnd.choice(keys)
                cand[k] = cand[k] + rnd.gauss(0, 0.15) * max(0.3, abs(cand[k]) + 0.2)
                M.clip_theta(cand)
                nxt.append((M.evaluate(lib, q, cand)["recall"], cand))
        pop = sorted(nxt, key=lambda x: (-x[0], str(sorted(x[1].items()))))[:len(theta0s)]
    pop.sort(key=lambda x: (-x[0], str(sorted(x[1].items()))))
    return pop[0][1], pop[0][0]

def e64():
    theta0s = [dict(M.FACTORY), dict(M.FACTORY, w_kw=5.0), dict(M.FACTORY, w_kw=1.0),
               dict(M.FACTORY, w_age=0.5)]
    MSEEDS = [3, 17, 29, 41]
    GENS = 30
    single = {}
    lib_cache = {}
    for s in SEEDS[:4]:
        lib = M.make_library(240, seed=s, vanity_frac=0.08)
        q = M.make_queries(lib, 80, seed=500 + s)
        lib_cache[s] = (lib, q)
        for ti, t0 in enumerate(theta0s):
            for ms in MSEEDS:
                th, ho = _hill(lib, q, t0, GENS, ms)
                single[(s, ti, ms)] = (_basin(th), ho)
    basins = {}
    for (s, ti, ms), (b, ho) in single.items():
        basins.setdefault(b, []).append(ho)
    basin_rows = sorted(((b, len(v), mean(v), sd(v)) for b, v in basins.items()),
                        key=lambda r: (-r[1], str(r[0])))
    pdep = []
    for ti in range(len(theta0s)):
        fracs = []
        for s in SEEDS[:4]:
            bs = {single[(s, ti, ms)][0] for ms in MSEEDS}
            fracs.append(1.0 if len(bs) > 1 else 0.0)
        pdep.append(mean(fracs))
    # 三种策略对比：全局最优 = 三种方法全部运行的最优 hold（非循环分母）；
    # 达最优率 = 库种子层面，该方法最优 hold >= 全局最优 - 0.02 的比例
    best_hold = max(v[1] for v in single.values())
    esc = {"爬山": [], "退火": [], "种群": []}
    for s in SEEDS[:4]:
        lib, q = lib_cache[s]
        hs = [_hill(lib, q, t0, GENS, ms) for t0 in theta0s for ms in MSEEDS]
        esc["爬山"].append(max(h for _, h in hs))
        ah = [_anneal(lib, q, t0, GENS, ms) for t0 in theta0s for ms in MSEEDS]
        esc["退火"].append(max(h for _, h in ah))
        ph = [_population(lib, q, theta0s, GENS, ms, keep=2) for ms in MSEEDS]
        esc["种群"].append(max(h for _, h in ph))
    global_best = max(max(v) for v in esc.values())
    reach = {k: mean([1.0 if v >= global_best - 0.02 else 0.0 for v in esc[k]]) for k in esc}
    return basin_rows, pdep, esc, reach, global_best

# ==========================================================================
def main():
    line("=" * 90)
    line("第九轮 E56/E57/E58/E59/E60/E64：合谋、身份、时滞、预警、词面、元性质（8 种子均值，确定性）")
    line("=" * 90)

    line("\n### E56 组合式/分布式后门（目标主题=%s，now_day=%d；污染=top5 睡眠条份额，命中=golden 查询命中率）"
         % (E56_TARGET, NOW56))
    res56 = e56()
    line("  [主攻击线] k=睡眠条数, per=每条注册词数, 桥=睡眠条互链")
    line("  %-16s %-10s %-12s %-24s %-24s" % ("k / per / 桥", "基线命中",
                                            "", "攻击(fz=关): 污染 / 命中", "攻击(fz=开): 污染 / 命中"))
    for k, per, br, r0, co, ro, con, rn in res56["rows"]:
        line("  k=%-3d per=%-3d 桥=%-4s %.3f        %10s%.3f / %.3f %14s%.3f / %.3f" % (
            k, per, "开" if br else "关", r0, "", co, ro, "", con, rn))
    line("  [审计对比] bridge=开；格式 TPR睡眠检出 / FPR诚实误报；A1阈值=5(诚实kw上限4)")
    line("  %-10s %-10s %-16s %-16s %-16s" % ("k", "每条词数", "A1单条词面", "A2链接度数", "A3共现同步"))
    for k, per, a1, f1, a2_, f2, a3, f3 in res56["audits"]:
        line("  k=%-7d per=%-6d %.3f / %.3f   %.3f / %.3f   %.3f / %.3f" % (k, per, a1, f1, a2_, f2, a3, f3))

    line("\n### E57 女巫攻击（10 诚实源 + c 女巫，80 局；坏晋升率 / 好存活率）")
    res57 = e57()
    for posture, tag in [("promote", "姿态A·自抬坏条"), ("suppress", "姿态B·再压好条")]:
        line("  [%s]  c     f    | 坏晋升: mean trimmed20 median | 好存活: mean trimmed20 median" % tag)
        for c, f, b1, b2, b3, g1, g2, g3 in res57[posture]:
            line("    c=%-4d %.3f | %.3f %.3f %.3f | %.3f %.3f %.3f" % (c, f, b1, b2, b3, g1, g2, g3))
    line("  身份成本相图（预算 B=30 身份，成本 κ → c=B/κ；median 防御，姿态A）")
    line("    κ      c     f      坏晋升  好存活")
    for kap, c, f, p_, u in res57["cost"]:
        line("    %-6s %-5d %.3f  %.3f   %.3f" % (kap, c, f, p_, u))

    line("\n### E58 检测/治理延迟（p0=0.10，β=%.2f；格式 终态(峰值,累计暴露)，恢复代数略于正文）" % BETA58)
    k_grid, g_grid, tab, comb, win = e58()
    line("  表1 延迟 k 代后开始【持续】清洗 γ → 终态(峰值,暴露)")
    line("    k\\γ    " + "".join("γ=%.2f            " % g for g in g_grid))
    for k in k_grid:
        cells = ["%.2f(%.2f,%.2f)" % (fi, pk, ex) for (pk, fi, ex, rc) in tab[k]]
        line("    k=%-4d " % k + "".join("%-17s" % c for c in cells))
    line("  表2 实时阻断 ε × 持续清洗 γ → 终态（阻断降低有效扩散 β(1-ε)）")
    line("    ε\\γ   " + "".join("γ=%.2f  " % g for g in g_grid))
    for eps in sorted(comb):
        line("    ε=%.2f " % eps + "".join("%-7s" % v for v in comb[eps]))
    line("  表3 有限治理窗口 W（γ=0.35>β，延迟 k 后治理 W 代即停）→ 峰值/终态")
    for k in [0, 5, 10]:
        row = []
        for W in [5, 15, 40, None]:
            pk, fi, ex, rc = win[(k, W)]
            row.append("W=%s:%.2f/%.2f" % ("∞" if W is None else W, pk, fi))
        line("    k=%-4d " % k + "  ".join(row))

    line("\n### E59 健康度仪表盘（阈值=clean 8 种子 mean+3sd；格=首次报警代数均值(检出率)，-1.0=未报）")
    calib, thr, fire, fp = e59()
    faults = [f for f in E59_FAULTS if f != "clean"]
    line("    %-12s %-8s" % ("指标", "阈值") + "".join("%-16s" % f for f in faults) + "误报率")
    for k in E59_KEYS:
        row = []
        for f in faults:
            if any(x >= 0 for x in fire[f][k]):
                v = mean([x for x in fire[f][k] if x >= 0])
                det = mean([1.0 if x >= 0 else 0.0 for x in fire[f][k]])
                row.append("%.1f(%.2f)    " % (v, det))
            else:
                row.append("未报(0.00)    ")
        line("    %-12s %-8.3f" % (k, thr[k]) + "".join("%-16s" % r for r in row) + "%.3f" % mean(fp[k]))

    line("\n### E60 词面鸿沟（查询以概率 p 整体换说法=双字反序；recall@5）")
    tab1, curves = e60()
    line("    p      出厂    +filter_zero  +PRF查询扩展")
    for p in [0.0, 0.25, 0.5, 0.75, 1.0]:
        f, z, pf = tab1[p]
        line("    %-6s %-9s %-12s %-10s" % (p, f, z, pf))
    line("    记忆侧词表自扩展（查询逐词翻转 p=0.75；top5 全员被动吸收查询词；ω=错配吸收率）→ 逐轮 recall/跨主题污染/top1词数")
    for key in sorted(curves):
        rr, cc, kk = curves[key]
        line("    %s recall: %s" % (key, " ".join("%.2f" % v for v in rr)))
        line("    %s 污染  : %s" % (key, " ".join("%.2f" % v for v in cc)))
        line("    %s top1词数: %s" % (key, " ".join("%.1f" % v for v in kk)))

    line("\n### E64 自演化路径依赖（4 库种子 × 4 初始θ × 4 变异种子，30 代）")
    basin_rows, pdep, esc, reach, gbest = e64()
    worst_basin = min(r[2] for r in basin_rows)
    line("    终态盆地聚类（签名=(fz, w_kw, w_imp, w_age, d)；共 %d 个不同盆地 / %d 次运行，按样本数排序，最多显示 10 行）"
         % (len(basin_rows), sum(r[1] for r in basin_rows)))
    for b, cnt, m_, s_ in basin_rows[:10]:
        line("      n=%-4d hold均值=%.3f sd=%.3f  basin=%s" % (cnt, m_, s_, b))
    line("    峰间性能差 = 全局最优 %.3f − 最差盆地均值 %.3f = %.3f" %
         (gbest, worst_basin, gbest - worst_basin))
    line("    路径依赖指数（同一初始θ不同变异种子落入≥2个盆地的库种子占比，按初始θ1..4）: %s" %
         " ".join("%.2f" % v for v in pdep))
    line("    策略对比（各策略 = 4初始θ×4变异种子的最优 hold；达最优 = ≥全局最优-0.02 的库种子比例）")
    for k in ["爬山", "退火", "种群"]:
        line("      %-6s 最优hold=%.3f  达全局最优率=%.3f" % (k, mean(esc[k]), reach[k]))

    line("\n" + "=" * 90)
    line("第九轮完成 E56/E57/E58/E59/E60/E64 共 6 个实验")
    line("=" * 90)

if __name__ == "__main__":
    main()
