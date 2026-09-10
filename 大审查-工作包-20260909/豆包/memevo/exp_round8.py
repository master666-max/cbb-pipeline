# -*- coding: utf-8 -*-
"""
第八轮 E44-E55：对抗动力学与系统韧性（adversarial dynamics & resilience）
前七轮问"某一刻能否被攻破/稳态可不可行"，本轮问四件更动态的事：
  L. 攻防双方都在线自适应（红皇后军备竞赛、先发锁定、去重被武器化、代理指标博弈）
  M. 错误如何沿结构/时间/群体传播（级联失效、事实变更、多数暴政）
  N. 系统随规模与污染的非单调/相变（规模不经济、污染不可逆临界点、OOD）
  O. 防御的自伤代价 + 对前七轮结论本身的种子稳健性审计（元实验）
全部局部 random.Random(seed)，并列排序加 id 字典序 tiebreak；8 种子均值（E50/E55 另注）。
文献锚点：Skalse NeurIPS2022(reward hacking)/Thomas&Uminsky(metrics)；Havlin/Buldyrev 级联、
Di Muro2015 临界恢复概率与三相位、Majdandzic 滞后；Lorenz PNAS2010、Banerjee1992、
Frey&van de Rijt(困难任务错误多数不自愈)。
"""
import random, statistics, time
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
# E44 红皇后攻防共演化：攻击者每代挑当前防御残余最大的攻击，防御每代补一个最有效的防御
# ==========================================================================
# 残余污染表：行=防御，列=攻击；0=该防御完全覆盖此攻击，1=完全无效（数值据前七轮结论标定）
ATTACKS = ["imp注水", "关键词堆砌", "互链农场", "伪造uses"]
DEFENSES = ["filter_zero", "uses门", "词表异常检测", "links度数上限"]
COVER = {
    "filter_zero":     {"imp注水": 0.05, "关键词堆砌": 0.90, "互链农场": 0.10, "伪造uses": 1.00},
    "uses门":          {"imp注水": 0.10, "关键词堆砌": 0.40, "互链农场": 0.40, "伪造uses": 1.00},
    "词表异常检测":    {"imp注水": 1.00, "关键词堆砌": 0.10, "互链农场": 1.00, "伪造uses": 1.00},
    "links度数上限":   {"imp注水": 1.00, "关键词堆砌": 1.00, "互链农场": 0.10, "伪造uses": 1.00},
}
def e44(seed):
    rnd = random.Random(seed)
    on = []
    normal_track, forge_track, attack_track, def_track = [], [], [], []
    for gen in range(12):
        # 高级攻击"伪造uses"第 6 代才解锁（需要先具备自证 uses 的能力）
        unlocked = ATTACKS if gen >= 6 else [a for a in ATTACKS if a != "伪造uses"]
        resid = {a: (min([COVER[d][a] for d in on]) if on else 1.0) for a in unlocked}
        if rnd.random() < 0.15:
            atk = rnd.choice(sorted(unlocked))
        else:
            atk = sorted(unlocked, key=lambda a: (-resid[a], a))[0]
        cur = resid[atk]
        added = "-"
        if cur > 0.5:  # 防御方补一个对当前攻击残余最低、尚未开启的防御
            cand = [d for d in DEFENSES if d not in on]
            if cand:
                pick = sorted(cand, key=lambda d: (COVER[d][atk], d))[0]
                on.append(pick); added = pick
        resid_all = {a: (min([COVER[d][a] for d in on]) if on else 1.0) for a in ATTACKS}
        normal = max(v for k, v in resid_all.items() if k != "伪造uses")
        forge_track.append(resid_all["伪造uses"])
        normal_track.append(normal); attack_track.append(atk); def_track.append(added)
    final = {a: (min([COVER[d][a] for d in on]) if on else 1.0) for a in ATTACKS}
    return normal_track, forge_track, attack_track, def_track, sorted(on), final

# ==========================================================================
# E45 冷启动先发投毒：恶意记忆独占早期采用窗口 W，之后正确记忆追赶，测翻盘/锁定
# ==========================================================================
def e45(seed, W, explore=0.0, q_bad=1.0):
    """早期 W 轮恶意独占(每轮10采用)；之后按 uses*质量 的优先连接瓜分采用。
    explore=探索份额(均匀分)，q_bad=恶意内容质量(被真实任务采用后发现差、降低再采用权重)。
    返回恶意最终是否仍占 top1、恶意uses/最好正确uses。"""
    rnd = random.Random(seed)
    n_good = 8
    uses_bad = 10.0 * W
    uses_good = [1.0] * n_good
    for t in range(60):
        wb = max(uses_bad, 1e-6) * q_bad; wg = [max(u, 1e-6) * 1.0 for u in uses_good]
        tot = wb + sum(wg)
        for _ in range(10):
            if rnd.random() < explore:
                pick = rnd.randrange(n_good + 1)          # 探索均匀
            else:
                r = rnd.random() * tot; pick = 0; acc = wb
                while r > acc and pick < n_good:
                    pick += 1; acc += wg[pick - 1]
            if pick == 0: uses_bad += 1
            else: uses_good[pick - 1] += 1
    best_good = max(uses_good)
    return (uses_bad >= best_good), round(uses_bad, 1), round(best_good, 1)

# ==========================================================================
# E46 去重/合并被武器化：近重复碰撞条目刷更高 uses，把正确记忆"合法合并"擦除
# ==========================================================================
def jaccard(a, b):
    ia, ib = set(a), set(b)
    return len(ia & ib) / len(ia | ib) if (ia | ib) else 0.0
def e46(seed, theta, uses_mult, safe_merge=False):
    """目标=8词正确记忆；攻击者保留 k 个、换 (8-k) 个无关词（同长度），Jaccard=k/(16-k)。
    攻击者取'刚好 J>=theta'的最小 k（最大化偷换）；k>=8 即逐字复制、无偷换空间=攻击失败。"""
    import math
    rnd = random.Random(seed)
    vocab = ["w%d" % i for i in range(60)]
    erased, need_k = 0, []
    trials = 200
    for _ in range(trials):
        target = rnd.sample(sorted(vocab), 8)
        k_min = math.ceil(theta * 16 / (1 + theta) - 1e-9)   # k/(16-k)>=theta
        need_k.append(k_min)
        if k_min >= 8:
            continue                                          # 必须逐字复制，无法夹带异质结论
        rest = rnd.sample(sorted(set(vocab) - set(target)), 8 - k_min)
        coll = target[:k_min] + rest
        j = jaccard(target, coll)
        same_conclusion = False                               # 换了词即偷换结论（异质碰撞）
        merged = j >= theta and (10.0 * uses_mult) >= 10.0
        if safe_merge:
            merged = merged and same_conclusion
        if merged:
            erased += 1
    return round(erased / trials, 3), round(mean(need_k), 2)

# ==========================================================================
# E47 Goodhart：把可被刷的内部代理 KPI 当优化目标，代理升而真实质量降
# ==========================================================================
def e47():
    # 基线
    base, basez = [], []
    for s in SEEDS:
        lib = M.make_library(240, seed=s, vanity_frac=0.10)
        q = M.make_queries(lib, 80, seed=500 + s)
        ev = M.evaluate(lib, q, M.FACTORY)
        base.append(ev["recall"]); basez.append(1 - ev["zero_share"])
    r0, z0 = mean(base), mean(basez)
    # 代理1 反思产出条数：全员自报 imp=10 -> 够格进反思取材的条数暴涨
    r1, p1 = [], []
    for s in SEEDS:
        lib = M.make_library(240, seed=s, vanity_frac=0.10)
        q = M.make_queries(lib, 80, seed=500 + s)
        for e in lib: e["importance"] = 10
        r1.append(M.evaluate(lib, q, M.FACTORY)["recall"])
        _top, _ = M.reflect_materials(lib, topn=len(lib))
        p1.append(len(_top) / len(lib))           # 全员刷满后，够格进反思取材的条数占比→1.0
    # 代理2 top平均自报imp：注水条目 imp=10，代理=top5平均imp（趋近10）
    r2, p2 = [], []
    for s in SEEDS:
        lib = M.make_library(240, seed=s, vanity_frac=0.35)
        for e in lib:
            if e.get("vanity"): e["importance"] = 10
        q = M.make_queries(lib, 80, seed=500 + s)
        ev = M.evaluate(lib, q, M.FACTORY, return_detail=True)
        r2.append(M.evaluate(lib, q, M.FACTORY)["recall"])
        rk = M.rank(lib, q[0]["query"], M.FACTORY)[:5]
        p2.append(statistics.mean([e["importance"] for _, (_, e, _) in rk]))
    # 代理3 词表覆盖度：注入注册全部主题词的条目，代理=top5平均词命中数(看起来匹配更满)
    r3, p3 = [], []
    for s in SEEDS:
        lib = M.make_library(240, seed=s, vanity_frac=0.10)
        q = M.make_queries(lib, 80, seed=500 + s)
        allwords = sorted({w for ws in M.TOPIC_WORDS.values() for w in ws})
        nid = 100000
        for _ in range(20):
            lib.append(dict(id=nid, topic=-1, true_quality=0.0,
                            keywords=allwords, content=list(M.GENERIC_WORDS),
                            importance=9, honest_imp=3, vanity=True, created_day=360,
                            t_invalid=None, truly_invalid=False, uses=0, links=[], is_farm=True)); nid += 1
        r3.append(M.evaluate(lib, q, M.FACTORY)["recall"])
        wh = []
        for qq in q:
            for _, (_, _, w) in M.rank(lib, qq["query"], M.FACTORY)[:5]: wh.append(w)
        p3.append(statistics.mean(wh))
    # 代理4 检索"满意度"：把 w_imp 调大(更信自报imp)，代理=top1平均检索分
    r4, p4 = [], []
    for s in SEEDS:
        lib = M.make_library(240, seed=s, vanity_frac=0.20)
        q = M.make_queries(lib, 80, seed=500 + s)
        t = dict(M.FACTORY); t["w_imp"] = 3.0
        r4.append(M.evaluate(lib, q, t)["recall"])
        sc = [M.rank(lib, qq["query"], t)[0][1][0] for qq in q[:30]]
        p4.append(statistics.mean(sc) / 10.0)
    # 对照：外部金尺真演化（hold 同分布）
    rg = []
    for s in SEEDS:
        lib = M.make_library(240, seed=s, vanity_frac=0.10)
        q = M.make_queries(lib, 80, seed=500 + s)
        traj = M.evolve(lib, q, q, dict(M.FACTORY), n_gen=20, seed=s)
        rg.append(traj[-1][1])
    rows = [
        ("基线(不优化)", 0.0, r0),
        ("反思产出条数代理", mean(p1), mean(r1)),
        ("top平均自报imp代理", mean(p2), mean(r2)),
        ("词表覆盖度代理(全注册)", mean(p3), mean(r3)),
        ("满意度代理(调大w_imp)", mean(p4), mean(r4)),
        ("外部金尺真演化(对照)", 1.0, mean(rg)),
    ]
    return r0, z0, rows

# ==========================================================================
# E48 级联失效：错误高层规律沿记忆依赖 DAG 逐层传播（对比扁平结构）
# ==========================================================================
def cascade_once(rnd, L, fan, tau, width=24, p0=0.15):
    """每层 width 节点、每节点 fan 个下层输入；输入污染占比>=tau 则合成节点被污染。"""
    layer = [rnd.random() < p0 for _ in range(width)]
    frac = [sum(layer) / width]
    for d in range(1, L):
        nxt = []
        for _ in range(width):
            inputs = [rnd.choice(layer) for _ in range(fan)]
            nxt.append((sum(inputs) / fan) >= tau - 1e-9)
        layer = nxt; frac.append(sum(layer) / width)
    return frac[-1]
def e48():
    out = {}
    # fan=3：OR 阈值=1/3（任一引用错即错）；多数=.5（需≥2）；AND=1（全错才错）
    for (L, tau, tag) in [(1, 1/3, "扁平 L=1(基线 p0=.15)"),
                          (6, 1/3, "深层 L=6 OR(任一错即错)"),
                          (6, 0.5, "深层 L=6 多数(≥2/3)"),
                          (6, 1.0, "深层 L=6 AND(全错才错)")]:
        vals = [cascade_once(random.Random(1000 + s), L, 3, tau) for s in range(60)]
        out[tag] = (mean(vals), sd(vals))
    return out

# ==========================================================================
# E49 事实变更 vs 过时：旧记忆曾正确、现错误，凭 uses/长期层身份压过新事实
# ==========================================================================
def e49(seed, u_old, policy="naive"):
    """同主题：旧记忆 uses=u_old/imp8/龄120天，新事实 uses=2/imp7/龄2天；返回新事实进 top1 概率。"""
    rnd = random.Random(seed)
    win = 0; trials = 300
    for _ in range(trials):
        old = dict(uses=u_old, imp=8, age=120, created=1)
        new = dict(uses=2, imp=7, age=2, created=120)
        def sc(e):
            s = 0.5 * e["uses"] + e["imp"] - 0.02 * e["age"]   # uses 是长期背书主信号、弱时效
            if policy == "fresh_boost":
                s += (2.5 if e is new else 0.0)               # 近期新事件加权
            if policy == "version":
                if e is old: s -= 1e6                         # 版本链：旧记忆在更新时刻失效
            return s + rnd.random() * 0.4
        top = sorted([old, new], key=lambda e: -sc(e))[0]
        if top is new: win += 1
    return round(win / trials, 3)

# ==========================================================================
# E50 多数暴政/信息级联：序贯决策、能看到前人投票，社会影响 λ 从众
# ==========================================================================
def e50_once(rnd, n, p, lam):
    votes = []
    for i in range(n):
        private_right = rnd.random() < p
        if votes and rnd.random() < lam:           # 以 λ 概率跟前人多数
            right_majority = sum(votes) > len(votes) / 2
            decision = right_majority
        else:
            decision = private_right
        votes.append(1 if decision else 0)
    return 1 if sum(votes) > n / 2 else 0          # 集体最终多数是否正确
def e50():
    table = {}
    for p, tag in [(0.55, "易任务 p=.55"), (0.505, "难任务 p=.505")]:
        for lam in [0.0, 0.3, 0.6, 0.9]:
            acc, lock_wrong = [], []
            for s in range(120):
                rnd = random.Random(7000 + s)
                right = sum(e50_once(rnd, 21, p, lam) for _ in range(8)) / 8
                acc.append(right)
            table["%s λ=%.1f" % (tag, lam)] = mean(acc)
    return table

# ==========================================================================
# E51 规模不经济：库规模增大时 recall / 零命中份额 / 攻击面 / 单次耗时
# ==========================================================================
def e51():
    rows = []
    for n in [100, 300, 1000, 3000, 10000]:
        fac_rec, fac_zero, gov_rec, gov_zero, ms = [], [], [], [], []
        for s in SEEDS[:4]:
            lib = M.make_library(n, seed=s, vanity_frac=0.10)
            q = M.make_queries(lib, 60, seed=900 + s)
            t0 = time.perf_counter()
            e1 = M.evaluate(lib, q, M.FACTORY)
            ms.append((time.perf_counter() - t0) / len(q) * 1000)
            tg = dict(M.FACTORY); tg["filter_zero"] = True
            e2 = M.evaluate(lib, q, tg)
            fac_rec.append(e1["recall"]); fac_zero.append(e1["zero_share"])
            gov_rec.append(e2["recall"]); gov_zero.append(e2["zero_share"])
        rows.append((n, mean(fac_rec), mean(fac_zero), mean(gov_rec), mean(gov_zero),
                     round(mean(ms), 3)))
    return rows

# ==========================================================================
# E52 污染不可逆相变：每代清洗 γ 比例、污染以 β 速率二次扩散，扫 (初始p0, γ)
# ==========================================================================
def e52_sim(p0, gamma, beta=0.30, steps=400):
    x = p0
    for _ in range(steps):
        x = x + beta * x * (1 - x) - gamma * x
        x = min(1.0, max(0.0, x))
    return round(x, 3)
def e52():
    gamma_grid = [0.10, 0.20, 0.30, 0.35, 0.45]
    p0_grid = [0.05, 0.20, 0.40, 0.60]
    tab = {}
    for g in gamma_grid:
        tab[g] = [e52_sim(p, g) for p in p0_grid]
    return p0_grid, gamma_grid, tab

# ==========================================================================
# E53 分布外泛化：演化只见过训练查询分布，测同分布 vs 三类 OOD
# ==========================================================================
def build_queries(lib, seed, mode, topics=None):
    """产出与 make_queries 同构的 dict(topic,query,expected)；mode 控制查询风格。"""
    rnd = random.Random(seed)
    by = {}
    for e in lib: by.setdefault(e["topic"], []).append(e)
    qs = []
    topics = topics or sorted(by.keys())
    for t in topics:
        pool = sorted([e for e in by.get(t, []) if not e.get("truly_invalid")],
                      key=lambda e: -e["true_quality"])
        if len(pool) < 3: continue
        words = M.TOPIC_WORDS[t]
        if mode == "id":
            wl = rnd.sample(sorted(words), 2)
        else:  # ood_combo：三主题词 + 一个泛词（演化时没见过的长度/噪声风格）
            wl = rnd.sample(sorted(words), min(3, len(words))) + [rnd.choice(sorted(M.GENERIC_WORDS))]
        qs.append(dict(topic=t, query=" ".join(wl), expected=[e["id"] for e in pool[:3]]))
    return qs
def e53(seed):
    lib = M.make_library(300, seed=seed, vanity_frac=0.08)
    topics = sorted(M.TOPIC_WORDS.keys())
    held = set(topics[-2:])                                   # 留出 2 个演化时整体不见的主题
    train_topics = [t for t in topics if t not in held]
    q_train = build_queries(lib, 300 + seed, "id", train_topics)
    traj = M.evolve(lib, q_train, q_train, dict(M.FACTORY), n_gen=25, seed=seed)
    theta_ev = traj[-1][2]
    q_id = build_queries(lib, 401 + seed, "id", topics)
    q_cb = build_queries(lib, 402 + seed, "ood_combo", train_topics)
    q_nt = build_queries(lib, 403 + seed, "id", sorted(held))
    # 内容缺口 OOD：库里只建前18主题，却查询后2主题（根本没有相关记忆）
    lib18 = [e for e in lib if e["topic"] not in held]
    q_gap = build_queries(lib, 404 + seed, "id", sorted(held))
    gap0 = M.evaluate(lib18, q_gap, M.FACTORY)["recall"]
    gap1 = M.evaluate(lib18, q_gap, theta_ev)["recall"]
    return (M.evaluate(lib, q_id, M.FACTORY)["recall"], M.evaluate(lib, q_id, theta_ev)["recall"],
            M.evaluate(lib, q_cb, M.FACTORY)["recall"], M.evaluate(lib, q_cb, theta_ev)["recall"],
            M.evaluate(lib, q_nt, M.FACTORY)["recall"], M.evaluate(lib, q_nt, theta_ev)["recall"],
            gap0, gap1)

# ==========================================================================
# E54 全治理叠加的自伤代价：逐级开治理，安全↑ vs 洁净召回/冷启动覆盖↓
# ==========================================================================
def attack_inject(lib, seed, frac=0.12):
    rnd = random.Random(seed)
    for e in lib:
        if rnd.random() < frac:
            e["vanity"] = True; e["importance"] = 10; e["is_farm"] = True
    return lib
def e54(seed):
    # 洁净效用：固定洁净库 recall；冷启动：小库（30条）零结果率
    lib = M.make_library(240, seed=seed, vanity_frac=0.0)
    q = M.make_queries(lib, 80, seed=600 + seed)
    small = M.make_library(30, seed=seed + 777, vanity_frac=0.0)
    qs = M.make_queries(small, 40, seed=800 + seed, expected_per_q=1)
    # 受攻击库
    libA = attack_inject(M.make_library(240, seed=seed + 1, vanity_frac=0.0), seed)
    qA = M.make_queries(libA, 80, seed=600 + seed)
    def clean_recall(t):       return M.evaluate(lib, q, t)["recall"]
    def cold_zero(t):         return M.evaluate(small, qs, t)["zero_share"]
    def attack_farm(t):       return M.evaluate(libA, qA, t)["farm_share"]
    levels = {
        "G0 出厂": dict(M.FACTORY),
        "G1 +filter_zero": (lambda: dict(M.FACTORY, filter_zero=True))(),
        "G2 +uses门(过滤uses=0注水)": None,
        "G3 +来源隔离/配额": None,
        "G4 +links限长/词表": None,
    }
    out = {}
    t0 = dict(M.FACTORY)
    out["G0 出厂"] = (round(attack_farm(t0), 3), clean_recall(t0), round(cold_zero(t0), 3))
    t1 = dict(M.FACTORY, filter_zero=True)
    out["G1 +filter_zero"] = (round(attack_farm(t1), 3), clean_recall(t1), round(cold_zero(t1), 3))
    # G2：在 G1 基础上把 uses=0 的注水条目从候选剔除（模拟 uses 门）
    def eval_gate(libx, qx, t, require_uses):
        keep = [e for e in libx if (not require_uses) or e["uses"] > 0]
        return M.evaluate(keep, qx, t)
    a2 = eval_gate(libA, qA, t1, True); c2 = eval_gate(lib, q, t1, True); s2 = eval_gate(small, qs, t1, True)
    out["G2 +uses门"] = (round(a2["farm_share"], 3), c2["recall"], round(s2["zero_share"], 3))
    # G3：来源隔离——直接按 is_farm 源剔除（攻击者可被源识别），配额使每源最多贡献 K 条进候选
    def eval_source(libx, qx, t, quota):
        seen = {}; keep = []
        for e in sorted(libx, key=lambda e: (-(e["uses"]), e["id"])):
            src = "farm" if e.get("is_farm") else "ok"
            seen[src] = seen.get(src, 0) + 1
            if seen[src] <= quota or src == "ok":
                keep.append(e)
        return M.evaluate(keep, qx, t)
    a3 = eval_source(libA, qA, t1, 6); c3 = eval_source(lib, q, t1, 6); s3 = eval_source(small, qs, t1, 6)
    out["G3 +来源配额"] = (round(a3["farm_share"], 3), c3["recall"], round(s3["zero_share"], 3))
    # G4：在 G3 来源配额上再叠加 uses门 + links限（最严，测过度防御对冷启动新记忆的自伤）
    def hard(libx):
        return [e for e in libx if e["uses"] > 0 and len(e.get("links", [])) <= 32]
    a4 = eval_source(hard(libA), qA, t1, 6); c4 = eval_source(hard(lib), q, t1, 6)
    s4 = eval_source(hard(small), qs, t1, 6)
    out["G4 全叠加"] = (round(a4["farm_share"], 3), c4["recall"], round(s4["zero_share"], 3))
    return out

# ==========================================================================
# E55 种子彩票元审计：32 种子重跑三个关键结论，看方向是否对运气稳健
# ==========================================================================
def e55():
    # 结论A（E32 MAD）：replace 自食 10 代后取材 sd 应显著小于持续注入 accum
    def mad_gap(seed):
        rnd = random.Random(seed)
        def run(replace):
            qualities = [rnd.uniform(0.2, 1.0) for _ in range(60)]
            pool = list(qualities)
            for gen in range(10):
                # 反思取 top6 合成、质量取均值（收缩），replace 时回灌替换；accum 时补 24 条新鲜
                top = sorted(pool, reverse=True)[:6]
                syn = statistics.mean(top)
                if replace:
                    pool = pool[len(pool) - 54:] + [syn] * 6
                else:
                    pool += [rnd.uniform(0.2, 1.0) for _ in range(24)]
            return statistics.pstdev(pool)
        return run(True) - run(False)   # 期望 <0（replace 收缩更厉害）
    # 结论B（E34 马太）：α=1 基尼应 > α=0 基尼
    def matthew_gap(seed):
        def run(alpha):
            rnd = random.Random(seed); u = [1.0] * 40
            for _ in range(1500):
                w = [x ** alpha for x in u]
                i = rnd.choices(range(40), weights=w, k=1)[0]; u[i] += 1
            return gini(u)
        return run(1) - run(0)          # 期望 >0
    # 结论C（E40 拜占庭）：f=4/10 时 mean 漏毒、median 守住 -> 漏毒条数差应 >0
    def byz_gap(seed):
        rnd = random.Random(seed)
        def agg(f, mode):
            leak = 0
            for _ in range(50):
                honest = [rnd.uniform(0, 0.2) for _ in range(10 - f)]
                mal = [rnd.uniform(0.8, 1.0) for _ in range(f)]
                vals = sorted(honest + mal)
                m = statistics.mean(vals) if mode == "mean" else statistics.median(vals)
                if m > 0.4: leak += 1
            return leak
        return agg(4, "mean") - agg(4, "median")   # 期望 >0
    res = {}
    for name, fn, expect in [("A MAD收缩差(repl-accum)", mad_gap, "<0"),
                             ("B 马太基尼差(a1-a0)", matthew_gap, ">0"),
                             ("C 拜占庭漏毒差(mean-median)", byz_gap, ">0")]:
        vals = [fn(s) for s in range(32)]
        if expect == "<0": agree = sum(1 for v in vals if v < 0) / 32
        else:             agree = sum(1 for v in vals if v > 0) / 32
        res[name] = (mean(vals), sd(vals), round(min(vals), 3), round(max(vals), 3),
                     round(agree, 3), expect)
    return res

# ==========================================================================
def main():
    line("=" * 90)
    line("第八轮 E44-E55：对抗动力学与系统韧性（8 种子均值，确定性可复现）")
    line("=" * 90)

    line("\n### E44 红皇后攻防共演化（攻击者/防御者每代互相适应，12 代；伪造uses第6代解锁）")
    agg_n = [[] for _ in range(12)]; agg_f = [[] for _ in range(12)]
    final_on = None; final_acc = None; sample_traj = None
    for s in SEEDS:
        nt, ft, at, dt, on, fr = e44(s)
        for i in range(12): agg_n[i].append(nt[i]); agg_f[i].append(ft[i])
        final_on = on
        final_acc = fr if final_acc is None else final_acc
        if s == SEEDS[0]: sample_traj = (at, dt)
    line("代次  " + " ".join("g%-2d" % i for i in range(12)))
    line("常规攻击最大残余 " + " ".join("%.2f" % mean(v) for v in agg_n))
    line("伪造uses残余     " + " ".join("%.2f" % mean(v) for v in agg_f))
    line("首种子攻击轨迹: " + " > ".join(sample_traj[0]))
    line("首种子补防轨迹: " + " > ".join(x if x != "-" else "·" for x in sample_traj[1]))
    line("12代后已集齐防御: " + "/".join(final_on))
    line("12代后各攻击残余: " + "  ".join("%s=%.2f" % (k, v) for k, v in sorted(final_acc.items())))
    line("=> 三种常规攻击被逐个补防压到<=.10；但'伪造uses'解锁后任何静态组合残余恒1.00（红皇后无终点，需下游背书）")

    line("\n### E45 冷启动先发投毒：早期独占窗口 W + 优先连接，测后期能否翻盘（锁定率）")
    line("%-7s %-16s %-16s %-18s %-18s" % (
        "W窗口", "纯优先连接", "+15%探索", "+质量降权.5", "探索+质量降权"))
    for W in [1, 2, 4, 8, 16]:
        c0, c1, c2, c3 = [], [], [], []
        for s in SEEDS:
            c0.append(e45(s, W, 0.0, 1.0)[0]); c1.append(e45(s, W, 0.15, 1.0)[0])
            c2.append(e45(s, W, 0.0, 0.5)[0]); c3.append(e45(s, W, 0.15, 0.5)[0])
        z = lambda xs: mean([1.0 if x else 0.0 for x in xs])
        line("%-7s %-16s %-16s %-18s %-18s" % ("W=%d" % W, z(c0), z(c1), z(c2), z(c3)))

    line("\n### E46 去重被武器化：近重复碰撞擦除正确记忆（普通合并 vs 要求结论一致的安全合并）")
    line("%-10s %-10s %-20s %-18s %-16s" % (
        "合并阈值", "uses倍率", "普通合并:擦除成功率", "安全合并:擦除", "达标需保留词数k"))
    for theta in [0.5, 0.6, 0.7, 0.8, 0.9]:
        for mult in [1.5, 3.0]:
            o1, k1, o2 = [], [], []
            for s in SEEDS:
                a, k = e46(s, theta, mult, False); o1.append(a); k1.append(k)
                c, _ = e46(s, theta, mult, True);  o2.append(c)
            line("%-10s %-10s %-20s %-18s %-16s" % (
                "theta=%.1f" % theta, "x%.1f" % mult, mean(o1), mean(o2), mean(k1)))

    line("\n### E47 Goodhart：优化可被刷的代理 KPI，代理↑而真实 recall↓")
    r0, z0, rows = e47()
    line("基线真实 recall=%.3f、非空率=%.3f" % (r0, z0))
    line("%-26s %-16s %-14s" % ("被优化的目标", "代理分", "真实recall"))
    for name, proxy, real in rows:
        line("%-26s %-16s %-14s" % (name, proxy, real))

    line("\n### E48 级联失效：错误沿记忆依赖 DAG 逐层传播（污染节点占比）")
    for tag, (m, sd_) in sorted(e48().items()):
        line("  %-26s 污染占比=%.3f sd=%.3f" % (tag, m, sd_))

    line("\n### E49 事实变更：旧记忆曾正确现错误，新事实进 top1 的概率（越高=更新越及时）")
    line("%-12s %-14s %-16s %-16s" % ("旧记忆uses", "朴素", "新事件加权", "版本链失效"))
    for u in [1, 3, 6, 12, 24]:
        a, b, c = [], [], []
        for s in SEEDS:
            a.append(e49(s, u, "naive")); b.append(e49(s, u, "fresh_boost")); c.append(e49(s, u, "version"))
        line("%-12s %-14s %-16s %-16s" % (u, mean(a), mean(b), mean(c)))

    line("\n### E50 多数暴政/信息级联（21人序贯、120局×8重复，集体正确率）")
    for k, v in sorted(e50().items()):
        line("  %-26s 集体正确率=%.3f" % (k, v))

    line("\n### E51 规模不经济（库规模 vs 出厂/治理 召回与零命中份额、单次耗时ms）")
    line("%-8s %-14s %-14s %-14s %-14s %-10s" % (
        "N", "出厂recall", "出厂零命中", "治理recall", "治理零命中", "单次ms"))
    for n, fr, fz, gr, gz, ms in e51():
        line("%-8s %-14s %-14s %-14s %-14s %-10s" % (n, fr, fz, gr, gz, ms))

    line("\n### E52 污染不可逆相变（β=.30，列=初始污染p0，值=400代后稳态污染）")
    p0g, gg, tab = e52()
    line("临界恢复率 γc=β=0.30；γ>γc 应回到0，γ<γc 锁定在 1-γ/β")
    line("γ\\p0   " + "".join("p0=%-6s" % p for p in p0g))
    for g in gg:
        line("γ=%.2f  " % g + "".join("%-9s" % v for v in tab[g]))

    line("\n### E53 分布外泛化（演化只见前18主题；测同分布/新风格/全新主题/内容缺口）")
    agg = [[] for _ in range(8)]
    for s in SEEDS:
        for i, v in enumerate(e53(s)): agg[i].append(v)
    lab = ["同分布-出厂", "同分布-演化后", "OOD新风格-出厂", "OOD新风格-演化后",
           "OOD新主题-出厂", "OOD新主题-演化后", "内容缺口-出厂", "内容缺口-演化后"]
    for l, v in zip(lab, agg):
        line("  %-20s recall=%.3f" % (l, mean(v)))
    line("  => 调全局排序权重对词面/主题OOD同幅泛化(无OOD惩罚)；但库里没有的内容，权重再优也=0")

    line("\n### E54 全治理叠加的自伤代价（攻击污染份额↓ vs 洁净recall/冷启动零结果）")
    agg54 = {}
    for s in SEEDS:
        for k, v in e54(s).items():
            agg54.setdefault(k, []).append(v)
    line("%-18s %-16s %-14s %-16s" % ("治理级别", "攻击后污染份额", "洁净recall", "冷启动零结果率"))
    for k in ["G0 出厂", "G1 +filter_zero", "G2 +uses门", "G3 +来源配额", "G4 全叠加"]:
        vals = agg54[k]
        line("%-18s %-16s %-14s %-16s" % (
            k, mean([v[0] for v in vals]), mean([v[1] for v in vals]), mean([v[2] for v in vals])))

    line("\n### E55 种子彩票元审计（32 种子，审计三个关键结论的方向稳健性）")
    for name, (m, sd_, mn, mx, agree, expect) in sorted(e55().items()):
        line("  %-30s 均值=%.3f sd=%.3f [%s,%s] 方向(%s)一致种子占比=%.3f" % (
            name, m, sd_, mn, mx, expect, agree))

    line("\n" + "=" * 90)
    line("第八轮完成 E44-E55 共 12 个实验")
    line("=" * 90)

if __name__ == "__main__":
    main()

