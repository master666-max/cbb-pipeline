# -*- coding: utf-8 -*-
"""exp_round6.py — 第六轮：12 个新方向实验（E20-E31）

六大方向，刻意扩展前五轮未覆盖的面，并反向挑战已有结论：
  A 反向压力测试  E20 uses 行为信号在稀疏/延迟/流行度噪声下何时失效
                  E21 自报+行为融合 α：纯 uses 真的最优吗（冷启动先验）
                  E24 攻击分类学，含"伪造 uses"——行为信号若可自导自演会怎样
  B 时间动态      E22 概念漂移：一次演化 vs 滚动演化 vs 灾难性遗忘
                  E23 冷启动库规模：极小库下 filter_zero 是否反伤
  C 攻击与检测    E25 纯结构信号在线检测注水/农场的 ROC
  D 反思二阶      E26 二阶反思的失真累积（传话游戏）
                  E27 反思取材宽度 topn 与重复合成膨胀
  E 优化本身      E28 可演化维度诅咒：固定评估预算下维度 vs 局部最优
                  E29 golden 标注污染：尺子脏了会把参数带向哪
  F 缓存与冗余    E30 Zipf 热点轮转下 LRU/LFU/自适应缓存
                  E31 近似重复去重的收益与误并代价
"""
import random, math, statistics
import mem_common as M

MEAN, SD = M.mean, M.sd
def line(c="-", n=78): print(c * n)


# 通用：按某键值取材，返回 (坏率, 平均真实质量)
def materials_by(ents, keyfn, topn=6):
    top = sorted(ents, key=lambda e: -keyfn(e))[:topn]
    bad = sum(1 for e in top if e["vanity"] or e.get("is_farm") or e["truly_invalid"])
    q = statistics.mean(e["true_quality"] for e in top)
    return round(bad / len(top), 3), round(q, 3)


def is_bad(e): return e["vanity"] or e.get("is_farm") or e["truly_invalid"]


# ═══════════════════ E20 · uses 在稀疏/延迟/流行度噪声下的可靠性 ═══════════════════
def degrade_uses(ents, cover, rng, pop=0.0, delay=0, now_day=365):
    """模拟真实反馈不完美：cover=能收到任何 uses 的条目比例；delay=创建后多少天才开始累积；
    pop=与质量无关的流行度噪声强度（0..1）。写入观测字段 uses_obs。"""
    for e in ents:
        fresh = (now_day - e["created_day"]) < delay
        if fresh or rng.random() > cover:
            e["uses_obs"] = 0
        else:
            e["uses_obs"] = e["uses"] + int(pop * rng.randint(0, 40))


def e20():
    line(); print("E20 · 行为信号 uses 的可靠性边界（20% 注水，取材 top6，8 种子均值）")
    print("    对比：自报 imp 取材 vs 观测 uses 取材（坏率↓/质量↑）")
    print(f"{'反馈覆盖cover':>12} | {'imp坏率/质量':>14} | {'uses坏率/质量':>14} | uses是否仍优")
    for cover in [1.0, 0.5, 0.25, 0.10]:
        imp_b, imp_q, us_b, us_q = [], [], [], []
        for s in range(8):
            ents = M.make_library(300, seed=s, vanity_frac=0.2, now_day=365)
            rng = random.Random(100 + s)
            degrade_uses(ents, cover, rng)
            b1, q1 = materials_by(ents, lambda e: e["importance"])
            b2, q2 = materials_by(ents, lambda e: e["uses_obs"])
            imp_b.append(b1); imp_q.append(q1); us_b.append(b2); us_q.append(q2)
        better = "是" if MEAN(us_b) < MEAN(imp_b) else "否（已被自报反超）"
        print(f"{cover:>12.2f} | {MEAN(imp_b):>6}/{MEAN(imp_q):<7} | {MEAN(us_b):>6}/{MEAN(us_q):<7} | {better}")
    # 流行度噪声：全覆盖但 uses 被无关热度污染
    print("  -- 全覆盖(cover=1)，叠加与质量无关的流行度噪声 pop：")
    print(f"{'pop强度':>10} | {'imp坏率/质量':>14} | {'uses坏率/质量':>14}")
    for pop in [0.0, 0.25, 0.5, 1.0]:
        imp_b, imp_q, us_b, us_q = [], [], [], []
        for s in range(8):
            ents = M.make_library(300, seed=s, vanity_frac=0.2)
            rng = random.Random(200 + s); degrade_uses(ents, 1.0, rng, pop=pop)
            b1, q1 = materials_by(ents, lambda e: e["importance"])
            b2, q2 = materials_by(ents, lambda e: e["uses_obs"])
            imp_b.append(b1); imp_q.append(q1); us_b.append(b2); us_q.append(q2)
        print(f"{pop:>10.2f} | {MEAN(imp_b):>6}/{MEAN(imp_q):<7} | {MEAN(us_b):>6}/{MEAN(us_q):<7}")


# ═══════════════════ E21 · 自报+行为融合权重 α（冷启动是否需要自报先验） ═══════════════════
def e21():
    line(); print("E21 · 融合取材 key=α·归一化imp +(1-α)·归一化uses（稀疏反馈 cover=0.3，20%注水）")
    print("    同时看：取材坏率↓ 与 高质量条目(quality>=0.7)被选中率↑（防把没机会被用的好条目埋没）")
    print(f"{'α(自报占比)':>10} | {'坏率':>6} | {'素材质量':>8} | {'高质量覆盖率':>10}")
    for cover in [0.3, 1.0]:
        print(f"  [cover={cover}]")
        for alpha in [0.0, 0.25, 0.5, 0.75, 1.0]:
            bads, quals, covs = [], [], []
            for s in range(8):
                ents = M.make_library(300, seed=s, vanity_frac=0.2)
                rng = random.Random(300 + s); degrade_uses(ents, cover, rng)
                umax = max(1, max(e["uses_obs"] for e in ents))
                def key(e, a=alpha):
                    return a * (e["importance"] / 10.0) + (1 - a) * (e["uses_obs"] / umax)
                top = sorted(ents, key=lambda e: -key(e))[:6]
                bads.append(sum(1 for e in top if is_bad(e)) / 6)
                quals.append(statistics.mean(e["true_quality"] for e in top))
                hi = [e for e in ents if e["true_quality"] >= 0.7]
                covs.append(len(set(e["id"] for e in top) & set(e["id"] for e in hi)) / max(1, min(6, len(hi))))
            print(f"{alpha:>10.2f} | {MEAN(bads):>6.3f} | {MEAN(quals):>8.3f} | {MEAN(covs):>10.3f}")


# ═══════════════════ E22 · 概念漂移：演化一次 vs 滚动演化 vs 遗忘 ═══════════════════
def queries_on_topics(ents, topics, n_q=40, seed=0):
    rng = random.Random(seed); by = {}
    for e in ents: by.setdefault(e["topic"], []).append(e)
    qs = []
    for _ in range(n_q):
        tp = rng.choice(topics); pool = [e for e in by.get(tp, []) if not e.get("truly_invalid")]
        if len(pool) < 3: continue
        gold = sorted(pool, key=lambda e: -e["true_quality"])[:3]
        wl = rng.sample(M.TOPIC_WORDS[tp], 2)
        qs.append(dict(topic=tp, query=" ".join(wl), expected=[e["id"] for e in gold]))
    return qs


def e22():
    line(); print("E22 · 概念漂移（前半世界=主题A组，后半世界=主题B组；8 种子）")
    A, B = M.TOPICS[:10], M.TOPICS[10:]
    rows = {"fixed": [], "once": [], "rolling": []}; rowsA = {"fixed": [], "once": [], "rolling": []}
    for s in range(8):
        # 两批条目：A 批写于早期，B 批写于后期
        eA = M.make_library(200, seed=s, now_day=180)
        for i, e in enumerate(eA): e["topic"] = A[i % 10]; e["created_day"] = random.Random(s).randint(0, 170)
        eB = M.make_library(200, seed=s + 50, now_day=365)
        for i, e in enumerate(eB): e["topic"] = B[i % 10]; e["created_day"] = 185 + random.Random(s + 1).randint(0, 170)
        ents = eA + eB
        # 重建主题词与 keywords/content 以匹配新 topic（用确定性种子，禁用随机化 hash）
        for i, e in enumerate(ents):
            w = M.TOPIC_WORDS[e["topic"]]; r = random.Random(s * 1000 + i)
            e["keywords"] = r.sample(w, 3); e["content"] = [r.choice(w) for _ in range(7)]
        qA = queries_on_topics(ents, A, 40, s); qB = queries_on_topics(ents, B, 40, s + 1)
        # fixed：出厂参数贯穿（不演化）
        rows["fixed"].append(M.evaluate(ents, qB, M.FACTORY)["recall"])
        rowsA["fixed"].append(M.evaluate(ents, qA, M.FACTORY)["recall"])
        # once：只在 A 时代演化，之后冻结
        t0 = dict(M.FACTORY); t0["filter_zero"] = True
        traj = M.evolve(ents, qA, qA, t0, n_gen=25, seed=s, mutate_filter=False)
        theta_once = traj[-1][2]
        rows["once"].append(M.evaluate(ents, qB, theta_once)["recall"])
        rowsA["once"].append(M.evaluate(ents, qA, theta_once)["recall"])
        # rolling：A 时代演化后，世界切换到 B，训练流也换成新主题 qB（追逐新世界），回看 qA 测遗忘
        traj2 = M.evolve(ents, qB, qA, dict(theta_once), n_gen=25, seed=s + 2)
        rows["rolling"].append(M.evaluate(ents, qB, traj2[-1][2])["recall"]); rowsA["rolling"].append(traj2[-1][1])
    print(f"{'策略':>22} | {'旧主题A召回':>10} | {'新主题B召回':>10}")
    print(f"{'固定出厂(不演化)':>20} | {MEAN(rowsA['fixed']):>10.3f} | {MEAN(rows['fixed']):>10.3f}")
    print(f"{'旧世界演化一次后冻结':>20} | {MEAN(rowsA['once']):>10.3f} | {MEAN(rows['once']):>10.3f}")
    print(f"{'滚动追逐新世界演化':>20} | {MEAN(rowsA['rolling']):>10.3f} | {MEAN(rows['rolling']):>10.3f}")
    print("  看点：追新(B)与守旧(A)构成前沿；滚动演化追新的代价是旧主题召回塌缩=灾难性遗忘")


def e22b():
    line(); print("E22b · 真冲突漂移：A世界靠正文匹配(w_c)、B世界靠关键词(w_kw)，最优参数相反（锁 filter_zero=False，8 种子）")
    A, B = M.TOPICS[:10], M.TOPICS[10:]
    C = {"facA": [], "facB": [], "tA_A": [], "tA_B": [], "tAB_A": [], "tAB_B": []}
    wcA, wkA, wcAB, wkAB = [], [], [], []
    for s in range(8):
        rng = random.Random(s)
        ents = []
        for grp, topics, nkw, ncnt in [("A", A, 1, 9), ("B", B, 4, 2)]:
            for i in range(200):
                tp = topics[i % 10]; w = M.TOPIC_WORDS[tp]
                q = round(rng.betavariate(2, 2), 3)
                ents.append(dict(id=f"{grp}{i:04d}", topic=tp, true_quality=q,
                    keywords=rng.sample(w, nkw), content=[rng.choice(w) for _ in range(ncnt)],
                    importance=min(10, 1 + int(9 * q)), honest_imp=min(10, 1 + int(9 * q)),
                    vanity=False, created_day=(rng.randint(0, 170) if grp == "A" else rng.randint(185, 360)),
                    t_invalid=None, truly_invalid=False, uses=int(q ** 1.5 * rng.randint(0, 40)),
                    links=[], is_farm=False))
        qA = queries_on_topics(ents, A, 40, s); qB = queries_on_topics(ents, B, 40, s + 1)
        tf = dict(M.FACTORY)
        C["facA"].append(M.evaluate(ents, qA, tf)["recall"]); C["facB"].append(M.evaluate(ents, qB, tf)["recall"])
        thA = M.evolve(ents, qA, qA, dict(tf), 25, s)[-1][2]
        C["tA_A"].append(M.evaluate(ents, qA, thA)["recall"]); C["tA_B"].append(M.evaluate(ents, qB, thA)["recall"])
        wcA.append(thA["w_c"]); wkA.append(thA["w_kw"])
        thAB = M.evolve(ents, qB, qA, dict(thA), 25, s + 3)[-1][2]
        C["tAB_A"].append(M.evaluate(ents, qA, thAB)["recall"]); C["tAB_B"].append(M.evaluate(ents, qB, thAB)["recall"])
        wcAB.append(thAB["w_c"]); wkAB.append(thAB["w_kw"])
    print(f"{'参数来自':>16} | {'旧世界A召回':>10} | {'新世界B召回':>10}")
    print(f"{'出厂(未演化)':>14} | {MEAN(C['facA']):>10.3f} | {MEAN(C['facB']):>10.3f}")
    print(f"{'只在A世界演化':>14} | {MEAN(C['tA_A']):>10.3f} | {MEAN(C['tA_B']):>10.3f}")
    print(f"{'再追B世界演化':>14} | {MEAN(C['tAB_A']):>10.3f} | {MEAN(C['tAB_B']):>10.3f}")
    print(f"  参数移动：w_c {MEAN(wcA):.2f}→{MEAN(wcAB):.2f}，w_kw {MEAN(wkA):.2f}→{MEAN(wkAB):.2f}（追逐B时牺牲了A所需的 w_c）")


def beta_recall(ents, qs, beta, K=5):
    """零和旋钮：score=β·关键词命中+(1-β)·正文命中（注意力预算在两者间分配，此消彼长）。"""
    hit = 0
    for item in qs:
        qw = item["query"].split(); scored = []
        for e in ents:
            kb, cb = " ".join(e["keywords"]), " ".join(e["content"])
            kw = sum(1 for w in qw if w in kb); c = sum(1 for w in qw if w in cb)
            scored.append((beta * kw + (1 - beta) * c + e["importance"] / 20.0, e["id"]))
        top = [i for _, i in sorted(scored, reverse=True)[:K]]
        if set(top) & set(item["expected"]): hit += 1
    return round(hit / len(qs), 3)


def e22c():
    line(); print("E22c · 遗忘的条件：零和旋钮 β（关键词vs正文注意力预算，β∈[0,1]此消彼长；8 种子）")
    A, B = M.TOPICS[:10], M.TOPICS[10:]
    grid = [0.0, 0.25, 0.5, 0.75, 1.0]
    table = {b: {"A": [], "B": []} for b in grid}
    for s in range(8):
        rng = random.Random(s); ents = []
        for grp, topics in [("A", A), ("B", B)]:
            for i in range(200):
                tp = topics[i % 10]; w = M.TOPIC_WORDS[tp]; q = round(rng.betavariate(2, 2), 3)
                if grp == "A":   # 靠正文：keywords 全是泛词(查询词命中不了)，content 全是主题词
                    kws = rng.sample(M.GENERIC_WORDS, 2); cont = [rng.choice(w) for _ in range(9)]
                else:            # 靠关键词：keywords 全是主题词，content 全是泛词
                    kws = rng.sample(w, 4); cont = rng.sample(M.GENERIC_WORDS, 3)
                ents.append(dict(id=f"{grp}{i:04d}", topic=tp, true_quality=q,
                    keywords=kws, content=cont,
                    importance=min(10, 1 + int(9 * q)), honest_imp=5, vanity=False, created_day=200,
                    t_invalid=None, truly_invalid=False, uses=0, links=[], is_farm=False))
        qA = queries_on_topics(ents, A, 40, s); qB = queries_on_topics(ents, B, 40, s + 1)
        for b in grid: table[b]["A"].append(beta_recall(ents, qA, b)); table[b]["B"].append(beta_recall(ents, qB, b))
    print(f"{'β(关键词预算)':>12} | {'旧世界A召回':>10} | {'新世界B召回':>10}")
    for b in grid:
        print(f"{b:>12.2f} | {MEAN(table[b]['A']):>10.3f} | {MEAN(table[b]['B']):>10.3f}")
    print("  → 加性独立权重(E22b)下新旧正和、不遗忘；只有零和/竞争型旋钮才此消彼长——灾难性遗忘需要参数层真实冲突")


# ═══════════════════ E23 · 冷启动：极小库 + filter_zero 是否反伤 ═══════════════════
def cold_queries(ents, n_q, seed=0):
    """冷启动：只从库里实际存在、且有非失效条目的主题出题，expected=该主题质量最高的 1 条。"""
    rng = random.Random(seed); by = {}
    for e in ents: by.setdefault(e["topic"], []).append(e)
    ok = [tp for tp in by if [e for e in by[tp] if not e.get("truly_invalid")]]
    qs = []
    for _ in range(n_q):
        if not ok: break
        tp = rng.choice(ok); pool = [e for e in by[tp] if not e.get("truly_invalid")]
        gold = sorted(pool, key=lambda e: -e["true_quality"])[:1]
        wl = rng.sample(M.TOPIC_WORDS[tp], min(2, len(M.TOPIC_WORDS[tp])))
        qs.append(dict(topic=tp, query=" ".join(wl), expected=[e["id"] for e in gold]))
    return qs


def e23():
    line(); print("E23 · 冷启动库规模（6 种子，演化 20 代；空结果率=top5 被零命中过滤滤光的查询占比）")
    print(f"{'库规模n':>8} | {'出厂holdout':>10} | {'演化后holdout':>12} | {'零命中过滤空结果率':>14}")
    for n in [10, 20, 50, 100, 200]:
        fac, evo, empty = [], [], []
        for s in range(6):
            ents = M.make_library(n, seed=s, now_day=120)
            nq = max(8, n // 2)
            qtr = cold_queries(ents, nq, s); qho = cold_queries(ents, nq, s + 999)
            if not qtr or not qho: continue
            fac.append(M.evaluate(ents, qho, M.FACTORY)["recall"])
            t0 = dict(M.FACTORY); t0["filter_zero"] = True
            traj = M.evolve(ents, qtr, qho, t0, n_gen=20, seed=s, mutate_filter=True)
            evo.append(traj[-1][1])
            # 空结果率
            tz = dict(M.FACTORY); tz["filter_zero"] = True
            e_cnt = 0
            for item in qho:
                if not M.rank(ents, item["query"], tz, now_day=120): e_cnt += 1
            empty.append(e_cnt / len(qho))
        print(f"{n:>8} | {MEAN(fac):>10.3f} | {MEAN(evo):>12.3f} | {MEAN(empty):>14.3f}")


# ═══════════════════ E24 · 攻击分类学（含伪造 uses） ═══════════════════
def make_attack_world(kind, seed=0, n=300):
    """统一 20% 攻击预算，五种攻击形态。攻击条目一律打 attack=True 以便统计恶意占比。"""
    ents = M.make_library(n, seed=seed, now_day=365,
                          vanity_frac=0.2 if kind == "vanity" else 0.0,
                          farm_clusters=(12 if kind in ("farm", "combo") else 0), farm_size=5)
    for e in ents: e["attack"] = bool(e["vanity"] or e.get("is_farm"))
    rng = random.Random(seed + 7)
    n_attack = int(0.2 * n)
    if kind == "stuff":                       # 关键词堆砌：不刷 imp，塞满全部主题词骗词命中
        allw = list({w for tp in M.TOPICS for w in M.TOPIC_WORDS[tp][:2]})
        for e in rng.sample(ents, n_attack):
            e["keywords"] = allw; e["importance"] = e["honest_imp"]; e["attack"] = True
    if kind == "fakeuses":                    # 伪造 uses：垃圾条目自导自演高"采用次数"
        cands = [e for e in ents if e["true_quality"] < 0.35 and not e["attack"]]
        for e in rng.sample(cands, min(n_attack, len(cands))): e["uses"] = 40; e["attack"] = True
    if kind == "combo":
        for e in ents:
            if e.get("is_farm"): e["uses"] = 40
        for e in rng.sample([x for x in ents if not x["attack"]], n_attack // 2):
            e["importance"] = 10; e["uses"] = 40; e["attack"] = True
    return ents


def e24():
    line(); print("E24 · 五种攻击形态 × 三治理水平（8 种子；recall / 恶意条目占top5）")
    print(f"{'攻击形态':>10} | {'L0出厂 r/恶意占比':>16} | {'L1 filter_zero':>16} | {'L2 +uses取材/排序':>18}")
    names = [("vanity", "刷imp注水"), ("stuff", "关键词堆砌"), ("farm", "互链农场"),
             ("fakeuses", "伪造uses"), ("combo", "全武行合谋")]
    for kind, zh in names:
        c0r, c0m, c1r, c1m, c2r, c2m = [], [], [], [], [], []
        for s in range(8):
            ents = make_attack_world(kind, s)
            q = M.make_queries(ents, 60, s + 5)
            id2 = {e["id"]: e for e in ents}
            def mal_share(theta, use_uses=False):
                tot = 0.0
                for item in q:
                    rl = M.rank(ents, item["query"], theta)[:5]
                    ids = [fid for fid, _ in rl]
                    if use_uses:  # L2：在 filter_zero 基础上，候选按 uses 重排（行为背书）
                        ids = sorted(ids, key=lambda fid: -id2[fid]["uses"])[:5]
                    tot += sum(1 for fid in ids if id2[fid].get("attack")) / 5
                return tot / len(q)
            t1 = dict(M.FACTORY); t1["filter_zero"] = True
            t2 = dict(t1)
            c0r.append(M.evaluate(ents, q, M.FACTORY)["recall"]); c0m.append(mal_share(M.FACTORY))
            c1r.append(M.evaluate(ents, q, t1)["recall"]);           c1m.append(mal_share(t1))
            c2r.append(M.evaluate(ents, q, t2)["recall"]);           c2m.append(mal_share(t2, True))
        print(f"{zh:>10} | {MEAN(c0r):>7.3f}/{MEAN(c0m):<7.3f} | {MEAN(c1r):>7.3f}/{MEAN(c1m):<7.3f} | {MEAN(c2r):>8.3f}/{MEAN(c2m):<8.3f}")
    print("  注：fakeuses 直接攻击行为信号本身——若 uses 可被写入方自导自演，L2 是否还成立是关键看点")


def e24b():
    line(); print("E24b · 行为信号的信任根（20% 注水，取材 top6，8 种子）")
    print("    对比：自报 imp 取材 / 诚实 uses 取材 / 攻击者把自身 uses 刷满后的 uses 取材")
    imp_b, use_b, forge_b = [], [], []
    imp_q, use_q, forge_q = [], [], []
    for s in range(8):
        ents = M.make_library(300, seed=s, vanity_frac=0.2)
        b1, q1 = materials_by(ents, lambda e: e["importance"]); imp_b.append(b1); imp_q.append(q1)
        b2, q2 = materials_by(ents, lambda e: e["uses"]); use_b.append(b2); use_q.append(q2)
        for e in ents:
            if e["vanity"]: e["uses"] = 40          # 攻击者自导自演"假采用"，把 uses 刷满
        b3, q3 = materials_by(ents, lambda e: e["uses"]); forge_b.append(b3); forge_q.append(q3)
    print(f"{'自报 imp 取材':>16}：坏率 {MEAN(imp_b):.3f} / 质量 {MEAN(imp_q):.3f}")
    print(f"{'诚实 uses 取材':>16}：坏率 {MEAN(use_b):.3f} / 质量 {MEAN(use_q):.3f}")
    print(f"{'伪造 uses 后取材':>16}：坏率 {MEAN(forge_b):.3f} / 质量 {MEAN(forge_q):.3f}")
    print("  → uses 的抗操纵性来自'写入瞬间无法伪造'；采用记录必须由下游真实事件背书（铁律2），否则退化为第二个 imp")


# ═══════════════════ E25 · 纯结构信号的在线检测 ROC ═══════════════════
def e25():
    line(); print("E25 · 不依赖上帝视角的结构检测器（条目级 TPR/FPR，combo 攻击世界，8 种子）")
    # 特征：①imp=10 且 uses=0（自报与行为背离）②所属互链连通块大小 ③关键词数异常多（堆砌）
    feats = {"imp=10且零uses": lambda e, comp: (e["importance"] >= 10 and e["uses"] == 0),
             "互链连通块>=4": lambda e, comp: comp.get(e["id"], 1) >= 4,
             "关键词数异常>=10": lambda e, comp: len(e["keywords"]) >= 10}
    def components(ents):
        adj = {e["id"]: set(e["links"]) for e in ents}; comp = {}
        for e in ents:
            if e["id"] in comp: continue
            stack, seen = [e["id"]], set()
            while stack:
                x = stack.pop()
                if x in seen: continue
                seen.add(x); stack.extend(adj.get(x, set()) - seen)
            for x in seen: comp[x] = len(seen)
        return comp
    agg = {k: [[], []] for k in feats}
    tprs, fprs = [], []
    for s in range(8):
        ents = make_attack_world("combo", s)
        rng = random.Random(s)
        for e in rng.sample([x for x in ents if not x.get("attack")], 30):  # 再补关键词堆砌攻击
            e["keywords"] = e["keywords"] + M.TOPIC_WORDS[e["topic"]] * 2; e["attack"] = True
        comp = components(ents)
        npos = max(1, sum(1 for e in ents if e.get("attack"))); nneg = max(1, sum(1 for e in ents if not e.get("attack")))
        for name, fn in feats.items():
            tp = sum(1 for e in ents if e.get("attack") and fn(e, comp))
            fp = sum(1 for e in ents if not e.get("attack") and fn(e, comp))
            agg[name][0].append(tp / npos); agg[name][1].append(fp / nneg)
        pred = lambda e: (e["importance"] >= 10 and e["uses"] == 0) or comp.get(e["id"], 1) >= 4 or len(e["keywords"]) >= 10
        tprs.append(sum(1 for e in ents if e.get("attack") and pred(e)) / npos)
        fprs.append(sum(1 for e in ents if not e.get("attack") and pred(e)) / nneg)
    print(f"{'结构特征':>16} | {'恶意检出TPR':>10} | {'误伤FPR':>8}")
    for name in feats:
        print(f"{name:>16} | {MEAN(agg[name][0]):>10.3f} | {MEAN(agg[name][1]):>8.3f}")
    print(f"{'三特征任一(组合)':>16} | {MEAN(tprs):>10.3f} | {MEAN(fprs):>8.3f}")


# ═══════════════════ E26 · 二阶反思的失真累积 ═══════════════════
def syn_to_entry(syn, gen, rng, mode):
    """把合成规律转成下一轮可被优先取材的条目（高层规律入长期层：imp 高；
    uses 模式下其 uses 取高位以公平地进入下一轮递归——两种模式都让"上一层结论"主导下一层）。"""
    w = M.TOPIC_WORDS[syn["topic"]]
    return dict(id=f"S{gen}_{rng.randint(0,9999)}", topic=syn["topic"], true_quality=syn["syn_quality"],
                keywords=list(w[:4]), content=list(w[:6]),
                importance=10 if mode == "imp" else 5, honest_imp=8,
                vanity=False, created_day=365, t_invalid=None, truly_invalid=syn["pollution"] > 0.5,
                uses=(999 if mode == "uses" else 2), links=[], is_farm=False)


def e26():
    line(); print("E26 · 二阶反思：上一层合成结论主导下一层取材，递归 5 代（传话游戏，8 种子）")
    print("    每代素材=上一代合成规律(优先回流)+原始库补位；看质量/污染随抽象代数的轨迹")
    print(f"{'取材方式':>8} | {'代1 质量/污染':>13} | {'代3':>11} | {'代5':>11} | 5代内主题漂移")
    q_track, p_track, drift = {m: [] for m in ["imp", "uses"]}, {m: [] for m in ["imp", "uses"]}, {m: [] for m in ["imp", "uses"]}
    for s in range(8):
        base = M.make_library(300, seed=s, vanity_frac=0.15)
        for mode in ["imp", "uses"]:
            rng = random.Random(s); carried = []; base_topic = None; d = 0; qs, ps = [], []
            for g in range(1, 6):
                keyfn = (lambda e: e["importance"]) if mode == "imp" else (lambda e: e["uses"])
                rest_n = max(1, 6 - len(carried))           # 历史合成物逐层累积、优先回流
                rest = sorted(base, key=lambda e: -keyfn(e))[:rest_n]
                top = carried + rest
                syn = M.synthesize(top)
                if base_topic is None: base_topic = syn["topic"]
                elif syn["topic"] != base_topic: d += 1
                qs.append(syn["syn_quality"]); ps.append(syn["pollution"])
                carried.append(syn_to_entry(syn, g, rng, mode)); carried = carried[-5:]
            q_track[mode].append(qs); p_track[mode].append(ps); drift[mode].append(d)
    for mode in ["imp", "uses"]:
        qt, pt = q_track[mode], p_track[mode]
        qg = lambda i: MEAN([x[i] for x in qt]); pg = lambda i: MEAN([x[i] for x in pt])
        print(f"{mode:>8} | {qg(0):>6.3f}/{pg(0):<6.3f} | {qg(2):>5.3f}/{pg(2):<5.3f} | {qg(4):>5.3f}/{pg(4):<5.3f} | {MEAN(drift[mode]):.2f}")


# ═══════════════════ E27 · 反思取材宽度与重复合成膨胀 ═══════════════════
def e27():
    line(); print("E27a · 取材宽度 topn（15% 注水，8 种子；坏率↓/质量↑/主题集中度）")
    print(f"{'topn':>6} | {'坏率':>6} | {'质量':>6} | {'主题集中度(最大主题占比)':>20}")
    for topn in [3, 6, 12, 20]:
        bads, quals, conc = [], [], []
        for s in range(8):
            ents = M.make_library(300, seed=s, vanity_frac=0.15)
            top = sorted(ents, key=lambda e: -e["importance"])[:topn]
            bads.append(sum(1 for e in top if is_bad(e)) / topn)
            quals.append(statistics.mean(e["true_quality"] for e in top))
            tps = [e["topic"] for e in top]
            conc.append(max(tps.count(t) for t in set(tps)) / topn)
        print(f"{topn:>6} | {MEAN(bads):>6.3f} | {MEAN(quals):>6.3f} | {MEAN(conc):>20.3f}")
    print("E27b · 重复合成膨胀：连续 20 次反思同一批库，高层规律去重后唯一率（按主题+质量桶）")
    for mode in ["imp", "uses"]:
        uniq = []
        for s in range(8):
            ents = M.make_library(300, seed=s, vanity_frac=0.15); seen = set(); n_total = 0
            for _ in range(20):
                keyfn = (lambda e: e["importance"]) if mode == "imp" else (lambda e: e["uses"])
                top = sorted(ents, key=lambda e: -keyfn(e))[:6]
                syn = M.synthesize(top)
                sig = (syn["topic"], round(syn["syn_quality"], 1))  # 同主题同质量桶视为重复规律
                n_total += 1; seen.add(sig)
            uniq.append(len(seen) / n_total)
        print(f"  {mode:>5} 取材：20 次合成的唯一规律率 = {MEAN(uniq):.3f}（越低=越在反复提炼同一件事）")


# ═══════════════════ E28 · 可演化维度诅咒（固定评估预算） ═══════════════════
def evolve_budget(ents, qtr, qho, keys, budget=40, seed=0, sigma=0.15):
    """固定评估次数预算（而非代数），看不同维度数能找到多好的参数。"""
    rng = random.Random(seed); theta = dict(M.FACTORY); theta["filter_zero"] = False
    def sc(t, q): return M.evaluate(ents, q, t)["recall"]
    tr, ho = sc(theta, qtr), sc(theta, qho); used = 0
    while used < budget:
        cand = dict(theta); k = rng.choice(keys)
        if k == "filter_zero": cand["filter_zero"] = not cand.get("filter_zero", False)
        else: cand[k] += rng.gauss(0, sigma) * max(0.3, abs(cand[k]) + 0.2)
        M.clip_theta(cand); used += 1
        ntr = sc(cand, qtr)
        if ntr >= tr: theta, tr = cand, ntr; ho = sc(theta, qho)
    return tr, ho


def e28():
    line(); print("E28 · 可演化维度诅咒（固定 40 次评估预算，10 种子；train/holdout 与种子间sd）")
    dims = {"2维(w_kw,w_age)": ["w_kw", "w_age"],
            "4维(+w_c,w_imp)": ["w_kw", "w_age", "w_c", "w_imp"],
            "6维(+d,filter)": ["w_kw", "w_age", "w_c", "w_imp", "d", "filter_zero"]}
    print(f"{'维度':>18} | {'train':>7} | {'holdout':>7} | {'holdout种子sd':>12}")
    for name, keys in dims.items():
        trs, hos = [], []
        for s in range(10):
            ents = M.make_library(300, seed=s, vanity_frac=0.1, now_day=365)
            qtr = M.make_queries(ents, 40, s); qho = M.make_queries(ents, 40, s + 999)
            tr, ho = evolve_budget(ents, qtr, qho, keys, 40, s)
            trs.append(tr); hos.append(ho)
        print(f"{name:>18} | {MEAN(trs):>7.3f} | {MEAN(hos):>7.3f} | {SD(hos):>12.3f}")


# ═══════════════════ E29 · golden 标注污染 ═══════════════════
def poison_queries(qs, ents, p, seed=0):
    """训练 golden 中 p 比例的 expected 被换成低质量条目（脏标注），隐藏集保持干净。"""
    rng = random.Random(seed); id2 = {e["id"]: e for e in ents}
    low = [e["id"] for e in ents if e["true_quality"] < 0.3]
    out = []
    for item in qs:
        it = dict(item); 
        if rng.random() < p and low:
            it["expected"] = [rng.choice(low) for _ in item["expected"]]
        out.append(it)
    return out


def e29():
    line(); print("E29 · golden 标注污染（训练尺子脏 p，隐藏集干净；演化 25 代，8 种子）")
    print(f"{'训练标注污染p':>12} | {'训练分(虚高?)':>12} | {'干净隐藏分':>10} | 训练-隐藏缺口")
    for p in [0.0, 0.1, 0.2, 0.3, 0.5]:
        trs, hos = [], []
        for s in range(8):
            ents = M.make_library(300, seed=s, vanity_frac=0.1)
            qtr0 = M.make_queries(ents, 40, s); qho = M.make_queries(ents, 60, s + 999)
            qtr = poison_queries(qtr0, ents, p, s)
            t0 = dict(M.FACTORY); t0["filter_zero"] = True
            traj = M.evolve(ents, qtr, qho, t0, n_gen=25, seed=s)
            trs.append(traj[-1][0]); hos.append(traj[-1][1])
        print(f"{p:>12.2f} | {MEAN(trs):>12.3f} | {MEAN(hos):>10.3f} | {round(MEAN(trs)-MEAN(hos),3):.3f}")


# ═══════════════════ E30 · Zipf 热点轮转下的缓存策略 ═══════════════════
class Cache:
    def __init__(self, cap, policy, tau=120.0):
        self.cap=cap; self.policy=policy; self.s=set(); self.lru=[]
        self.freq={}; self.last={}; self.t=0; self.tau=tau; self.rng=random.Random(12345)
    def access(self, x):
        self.t += 1
        hit = x in self.s
        self.freq[x] = self.freq.get(x, 0) + 1; self.last[x] = self.t
        if x in self.lru: self.lru.remove(x)
        self.lru.append(x)
        if hit: return True
        if len(self.s) >= self.cap: self._evict()
        self.s.add(x); return False
    def _evict(self):
        if self.policy == "random":
            v = self.rng.choice(sorted(self.s))
        elif self.policy == "lfu":
            v = min(self.s, key=lambda k: (self.freq.get(k, 0), k))
        elif self.policy == "hybrid":   # 近因×频率：score=freq·exp(-距上次访问/τ)，逐出最低分
            v = min(self.s, key=lambda k: (self.freq.get(k,0)*math.exp(-(self.t-self.last.get(k,0))/self.tau), k))
        else:                          # lru
            v = next(k for k in self.lru if k in self.s)
        self.s.discard(v)


def access_stream(names, T, n=2000, seed=0, W=60):
    """分时代：每个时代长度 T，活跃工作集是一个大小 W 的窗口，时代间窗口不重叠（整体换工作集）。
    窗口内按 Zipf 访问，窗口外不访问。T=inf 时工作集恒定（静态）。"""
    rng = random.Random(seed); m = len(names); seq = []
    zw = [1.0 / (j + 1) ** 0.9 for j in range(W)]
    for i in range(n):
        epoch = 0 if T == float("inf") else i // T
        start = (epoch * W) % max(1, m - W)
        j = rng.choices(range(W), weights=zw)[0]
        seq.append(names[start + j])
    return seq


def e30():
    line(); print("E30 · 工作集时代切换 × 缓存策略（容量=50/工作集60/候选200，8 种子均值命中率）")
    names = [f"X{i}" for i in range(200)]
    print(f"{'时代长度T':>10} | {'random':>7} | {'LRU近因':>7} | {'LFU频率':>7} | {'hybrid近因×频率':>12}")
    for T, zh in [(float("inf"), "工作集恒定"), (500, "慢换工作集"), (120, "快换工作集")]:
        res = {p: [] for p in ["random", "lru", "lfu", "hybrid"]}
        for s in range(8):
            seq = access_stream(names, T, 1500, s)
            for p in res:
                c = Cache(50, p, tau=80.0); hits = sum(1 for x in seq if c.access(x))
                res[p].append(hits / len(seq))
        print(f"{zh:>10} | {MEAN(res['random']):>7.3f} | {MEAN(res['lru']):>7.3f} | {MEAN(res['lfu']):>7.3f} | {MEAN(res['hybrid']):>12.3f}")
    print("  看点：工作集恒定时频率最优；工作集整体快换时 LFU 抱住上一时代高频死重，近因/混合反超")


# ═══════════════════ E31 · 近似重复去重：收益与误并 ═══════════════════
def jaccard(a, b):
    sa, sb = set(a), set(b)
    return len(sa & sb) / max(1, len(sa | sb))


def dedup(ents, thr=0.8):
    """关键词 Jaccard>=thr 视为重复，保留 uses 最高者。返回 (去重后库, 合并组数, 误并数)。"""
    keep, removed, merges, wrong = [], set(), 0, 0
    for i, e in enumerate(ents):
        if e["id"] in removed: continue
        group = [e]
        for e2 in ents[i + 1:]:
            if e2["id"] in removed: continue
            if jaccard(e["keywords"], e2["keywords"]) >= thr:
                group.append(e2); removed.add(e2["id"])
        if len(group) > 1:
            merges += 1
            topics = {g["topic"] for g in group}
            if len(topics) > 1: wrong += 1            # 把不同主题的独立条目错并
            best = max(group, key=lambda g: g["uses"]); keep.append(best)
        else:
            keep.append(e)
    return keep, merges, wrong


def e31():
    line(); print("E31 · 近似重复去重（注入近重复条目；看有效容量、top5证据多样性、误并）")
    print(f"{'近重复比例':>10} | {'去重前n':>7} | {'去重后n':>7} | {'合并组':>6} | {'误并组':>6} | top5不同证据数(前→后)")
    for dup in [0.0, 0.15, 0.3, 0.5]:
        bs, as_, mg, wg, divb, diva = [], [], [], [], [], []
        for s in range(8):
            ents = M.make_library(300, seed=s, now_day=300)
            rng = random.Random(s)
            srcs = rng.sample(ents, int(dup * len(ents)))
            for src in srcs:                        # 制造近重复：拷贝并微调 1 个词
                clone = dict(src); clone["id"] = src["id"] + "d"
                clone["keywords"] = list(src["keywords"])
                clone["true_quality"] = max(0, src["true_quality"] - 0.02)
                ents.append(clone)
            q = M.make_queries(ents, 40, s + 3)
            def diversity(lib):
                d = []
                for item in q[:20]:
                    top = [fid for fid, _ in M.rank(lib, item["query"], M.FACTORY, now_day=300)[:5]]
                    d.append(len({fid.rstrip("d") for fid in top}))
                return statistics.mean(d)
            divb.append(diversity(ents))
            kept, merges, wrong = dedup(ents, 0.8)
            diva.append(diversity(kept))
            bs.append(300 + int(dup * 300)); as_.append(len(kept)); mg.append(merges); wg.append(wrong)
        print(f"{dup:>10.2f} | {MEAN(bs):>7.0f} | {MEAN(as_):>7.1f} | {MEAN(mg):>6.1f} | {MEAN(wg):>6.2f} | {MEAN(divb):.2f} → {MEAN(diva):.2f}")


if __name__ == "__main__":
    e20(); e21(); e22(); e22b(); e22c(); e23(); e24(); e24b(); e25(); e26(); e27(); e28(); e29(); e30(); e31()
    line(); print("第六轮 E20-E31（含 E22b/E22c/E24b）完成")
