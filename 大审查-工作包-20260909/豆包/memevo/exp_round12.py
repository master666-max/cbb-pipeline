# -*- coding: utf-8 -*-
"""
第十二轮 E75–E79：第十一轮自启问题的交叉验证（5 个实验）
第十一轮留下五条线头，本轮把它们接完：
  E75 需求膨胀攻击（E71×E57 交叉）：动态席位读需求信号——女巫流量能不能"骗席位"（shilling 攻击的调度版）
  E76 两级存储加速自考脱钩？（E66×E73 交叉）：冷层 reservoir 会让自证陷阱收得更紧还是更松
  E77 冷层故障的 I13 可检性（E73×E74 交叉）：补上第十一轮仪表盘"预留未触发"的最后一块
  E78 席位俘获与 uses 门防御（E71×E9 交叉）：写侧 imp 注水能否俘获席位代表权，行为门能否守住
  E79 ε* 的词池偏斜定标（E72 理论化）：外生配额要不要随库偏斜度上调——D 对 (1−ε)·B 的塌缩检验
文献锚点（本环境经 OpenAlex/Crossref 核验 DOI）：
  E75/E78: Lam & Riedl, KDD 2004, shilling recommender systems (10.1145/988672.988726)
  E76: Gomez-Uribe & Hunt, ACM TMIS 2015, Netflix recommender system (10.1145/2843948)；MAD 已锚（第七轮）
  E77: Conti et al., Computer Networks 2013（第十一轮已锚）；Scheffer Nature 2009（第九轮已锚）
  E79: Chaney et al., RecSys 2018, algorithmic confounding (10.1145/3240323.3240370)；Perdomo ICML 2020（已锚）
全部局部 random.Random(seed)，并列排序加 id 字典序 tiebreak；8 种子均值；无计时实验、两次运行须逐行一致。
"""
import math, random, statistics
import mem_common as M

SEEDS = [11, 23, 37, 51, 67, 83, 101, 127]
def mean(x): return round(statistics.mean(x), 3) if x else 0.0
def sd(x):   return round(statistics.pstdev(x), 3) if len(x) > 1 else 0.0
def line(s=""): print(s)

TH12 = dict(M.FACTORY, w_age=0.01)     # 两级存储实验剥离老化项（第十轮 F23 教训）
REV12 = {}
def _rev12():
    if REV12: return REV12
    for tp, ws in M.TOPIC_WORDS.items():
        for w in ws: REV12[w] = tp
    return REV12

def _golden_by_topic(lib):
    g = {}
    for tp in M.TOPICS:
        g[tp] = {e["id"] for e in sorted([e for e in lib if e["topic"] == tp and not e.get("truly_invalid")],
                                         key=lambda e: (-e["true_quality"], e["id"]))[:3]}
    return g

def _pick_weighted(order, w, tw, rnd):
    r = rnd.random() * tw; acc = 0.0; pick = order[0]
    for t in order:
        acc += w[t]
        if r <= acc: pick = t; break
    return pick

def _reg(lib, eid):
    """注入条目登记簿：uses/last_hit 必须同步注册（第十一轮教训）。"""
    return None

# ==========================================================================
# E75 需求膨胀攻击：女巫流量能否骗到动态席位
# ==========================================================================
def e75_run(seed, policy, phi, gens=60, n_q=20, budget=80, s_exp=1.5):
    """policy: staticQ(固定 Q3) / dynamicQ(按观测查询份额比例共享)。
    攻击者：目标=秩 15 的尾部主题；写入 6 条 imp=9 新鲜条目 + 每代发出 phi·n_q 条幻影查询
    （幻影查询与真实查询在日志中不可分辨，同享 EMA 与回读预算）。
    返回 (诚实整体recall, 目标主题污染份额(后半), 目标主题热区占比(后半), 幻影查询的回读占用率)。"""
    rnd = random.Random(7600 + seed)
    lib = M.make_library(240, seed=seed, vanity_frac=0.08)
    order = list(range(len(M.TOPICS))); rnd.shuffle(order)
    t_idx = order[14]                                  # 秩 15 的尾部主题
    # 攻击条
    atk_ids = []
    tw = M.TOPIC_WORDS[M.TOPICS[t_idx]]
    for i in range(6):
        eid = "A%03d" % i
        lib.append(dict(id=eid, topic=M.TOPICS[t_idx], true_quality=0.05,
                        keywords=[tw[i % 8], tw[(i + 3) % 8]], content=[tw[i % 8]],
                        importance=9, honest_imp=1, vanity=False, created_day=364,
                        t_invalid=None, truly_invalid=True, uses=0, links=[], is_farm=False, src="H"))
        atk_ids.append(eid)
    hot = {}; cold = {e["id"]: e for e in lib}
    uses = {e["id"]: 0 for e in lib}; last_hit = {e["id"]: -1 for e in lib}
    golden = {list(M.TOPICS).index(tp): gset for tp, gset in _golden_by_topic(lib).items()}
    sset = set(atk_ids)
    cont_traj, hotshare_traj = [], []
    probe_target = [0, 0]
    honest_rec = []
    ema = {t: 1.0 for t in order}
    for g in range(gens):
        w = {t: 1.0 / ((order.index(t) + 1) ** s_exp) for t in order}
        tw_sum = sum(w.values())
        counts = {t: 0 for t in order}
        probes_left = 2
        # 真实+幻影查询穿插混排（幻影与真实在日志中不可分辨，可竞争回读预算）
        n_ph = int(round(phi * n_q))
        queue = [(t, False) for t in (_pick_weighted(order, w, tw_sum, rnd) for _ in range(n_q))]
        for i in range(n_ph):
            queue.insert(rnd.randrange(len(queue) + 1), (t_idx, True))
        for t, is_ph in queue:
            counts[t] += 1
            tp = M.TOPICS[t]
            qw = " ".join(rnd.sample(sorted(M.TOPIC_WORDS[tp]), 2))
            rl = M.rank(list(hot.values()), qw, TH12)[:5]
            top = [fid for fid, _ in rl]
            if not is_ph:
                honest_rec.append(1.0 if set(top) & golden[t] else 0.0)
            if t == t_idx:
                cont_traj.append(sum(1 for f in top if f in sset) / 5.0)
            for fid in top:
                uses[fid] += 1; last_hit[fid] = g
            if cold and probes_left > 0:
                probes_left -= 1
                cl = M.rank(list(cold.values()), qw, TH12)[:1]
                for fid, _ in cl:
                    hot[fid] = cold.pop(fid)
                    if is_ph: probe_target[0] += 1
                    probe_target[1] += 1
        ema = {t: ema[t] * 0.9 + counts[t] * 0.1 for t in order}
        if policy == "dynamicQ":
            seats = {t: max(1, min(6, round(budget * ema[t] / max(1, sum(ema.values()))))) for t in order}
        else:
            seats = {t: 3 for t in order}
        reserved = set()
        for t in order:
            tp = M.TOPICS[t]
            for e in sorted([e for e in lib if e["topic"] == tp],
                            key=lambda e: (-(e["importance"] - 0.1 * (365 - e["created_day"])), e["id"]))[:seats[t]]:
                reserved.add(e["id"])
                if e["id"] in cold: hot[e["id"]] = cold.pop(e["id"])
        for i in sorted((i for i in hot if i not in reserved), key=lambda i: (uses[i], last_hit[i], i)):
            if len(hot) <= budget: break
            cold[i] = hot.pop(i)
        hotshare_traj.append(sum(1 for i in hot if i in sset) / max(1, len(hot)))
    half_c = len(cont_traj) // 2
    half_h = len(hotshare_traj) // 2
    return (mean(honest_rec), mean(cont_traj[half_c:]), mean(hotshare_traj[half_h:]),
            round(probe_target[0] / max(1, probe_target[1]), 3))

def e75():
    out = {}
    for policy in ["staticQ", "dynamicQ"]:
        for phi in [0.0, 0.25, 0.5, 1.0]:
            agg = [[] for _ in range(4)]
            for s in SEEDS:
                r = e75_run(s, policy, phi)
                for i, v in enumerate(r): agg[i].append(v)
            out[(policy, phi)] = tuple(mean(a) for a in agg)
    return out

# ==========================================================================
# E76 两级存储加速自考脱钩？（E66 回路 + 冷层 reservoir）
# ==========================================================================
def e76_gen_exam(lib, rnd, pool_words, n_q=40):
    """纯自考题：词采自 pool_words（上代热区 top 条目词表）。"""
    qs = []
    for _ in range(n_q):
        if len(pool_words) < 2: break
        wl = rnd.sample(sorted(pool_words), 2)
        q = " ".join(wl)
        blob = lambda e: " ".join(e["keywords"]) + " " + " ".join(e["content"])
        cand = [e for e in lib if not e.get("truly_invalid") and any(w in blob(e) for w in wl)]
        if len(cand) < 3: continue
        exp = sorted(cand, key=lambda e: (-e["true_quality"], e["id"]))[:3]
        qs.append(dict(topic=-1, query=q, expected=[e["id"] for e in exp]))
    return qs

def e76_run(seed, budget, gens=40, n_ex=40):
    """两级存储下的自考闭环：考题只考热区、回读按需拉取、LFU 逐出。
    返回 (外部recall前1/4, 外部recall后1/4, 外部末代, 末代热区主题覆盖数)。"""
    rnd = random.Random(7700 + seed)
    lib = M.make_library(240, seed=seed, vanity_frac=0.08)
    hot = {e["id"]: e for e in lib}; cold = {}
    uses = {e["id"]: 0 for e in lib}; last_hit = {e["id"]: -1 for e in lib}
    ext = M.make_queries(lib, 80, seed=500 + seed)
    theta = dict(M.FACTORY); keys = ["w_kw", "w_c", "w_imp", "w_age", "d"]
    id2e = {e["id"]: e for e in lib}
    pool_words = []
    for x in ext[:10]:
        for fid, _ in M.rank(list(hot.values()), x["query"], M.FACTORY)[:10]:
            pool_words.extend(id2e[fid]["keywords"])
    ext_traj = []
    for g in range(gens):
        exam = e76_gen_exam(lib, rnd, pool_words, n_ex)
        if not exam: break
        cur = M.evaluate(list(hot.values()), exam, theta)["recall"]
        cand = dict(theta); k = rnd.choice(keys)
        cand[k] = cand[k] + rnd.gauss(0, 0.15) * max(0.3, abs(cand[k]) + 0.2)
        M.clip_theta(cand)
        if M.evaluate(list(hot.values()), exam, cand)["recall"] >= cur: theta = cand
        ext_traj.append(M.evaluate(lib, ext, theta)["recall"])
        words = []
        for x in exam[:10]:
            for fid, _ in M.rank(list(hot.values()), x["query"], theta)[:10]:
                words.extend(id2e[fid]["keywords"])
                uses[fid] += 1; last_hit[fid] = g
            if cold:                                   # 每条考题拉取冷区 top1（按需回读）
                cl = M.rank(list(cold.values()), x["query"], TH12)[:1]
                for fid, _ in cl:
                    hot[fid] = cold.pop(fid)
        if words: pool_words = words
        for i in sorted(hot, key=lambda i: (uses[i], last_hit[i], i)):
            if len(hot) <= budget: break
            cold[i] = hot.pop(i)
    q = max(1, len(ext_traj) // 4)
    pre = mean(ext_traj[:q]); post = mean(ext_traj[-q:])
    cover = len({e["topic"] for e in hot.values()})
    return pre, post, ext_traj[-1], cover

def e76():
    out = {}
    for budget in [240, 96, 48]:
        agg = [[] for _ in range(4)]
        for s in SEEDS:
            r = e76_run(s, budget)
            for i, v in enumerate(r): agg[i].append(v)
        out[budget] = tuple(mean(a) for a in agg)
    return out

# ==========================================================================
# E77 冷层故障的 I13 可检性（E74 仪表盘补全）
# ==========================================================================
E77_KEYS = ["I1自产占比", "I2uses基尼", "I5注水占比", "I6堆砌占比",
            "I11席位失衡", "I12固定金尺损失", "I13回读浪费"]
E77_FAULTS = ["clean", "hotsleeper", "coldsleeper"]

def _e77_indicators(lib, hot, cold, adm_hit, adm_tot, probe_loss):
    n = max(1, len(lib))
    syn = sum(1 for e in lib if e.get("src") == "SYN") / n
    us = sorted(e["uses"] for e in lib); tot = sum(us) or 1; cum = 0.0
    for i, v in enumerate(us, 1): cum += i * v
    gini = (2.0 * cum) / (n * tot) - (n + 1) / n
    imp10 = sum(1 for e in lib if e["importance"] >= 10) / n
    rev = _rev12()
    stuff = 0
    for e in lib:
        c = {}
        for w in e["keywords"]:
            t = rev.get(w)
            if t: c[t] = c.get(t, 0) + 1
        if c and max(c.values()) >= 5: stuff += 1
    hotc = {}
    for e in hot.values(): hotc[e["topic"]] = hotc.get(e["topic"], 0) + 1
    imb = max(hotc.values()) / max(1, len(hot)) if hotc else 0.0
    waste = 1.0 - (adm_hit / adm_tot) if adm_tot else 0.0
    return {"I1自产占比": syn, "I2uses基尼": round(gini, 3), "I5注水占比": imp10,
            "I6堆砌占比": stuff / n, "I11席位失衡": round(imb, 3),
            "I12固定金尺损失": round(probe_loss, 3), "I13回读浪费": round(waste, 3)}

def e77_scenario(seed, mode, gens=12, budget=80):
    """两级存储 + 注入 hotsleeper / coldsleeper（E56 组合后门、目标主题 3、g=2 注入）。"""
    rnd = random.Random(7800 + seed)
    lib = M.make_library(240, seed=seed, vanity_frac=0.08)
    for e in lib: e["src"] = "H"
    hot = {}; cold = {e["id"]: e for e in lib}
    uses = {e["id"]: 0 for e in lib}; last_hit = {e["id"]: -1 for e in lib}
    golden = _golden_by_topic(lib)
    order = list(range(len(M.TOPICS))); rnd.shuffle(order)
    fixed_probe = []
    for i in range(20):
        t = order[i % len(order)]
        fixed_probe.append(" ".join(rnd.sample(sorted(M.TOPIC_WORDS[M.TOPICS[t]]), 2)))
    traj = []
    hwin = []; awin = []
    for g in range(gens):
        probes_left = 2
        adm_hit = [0, 0]
        for _ in range(20):
            t = _pick_weighted(order, {t: 1 for t in order}, len(order), rnd)
            qw = " ".join(rnd.sample(sorted(M.TOPIC_WORDS[M.TOPICS[t]]), 2))
            rl = M.rank(list(hot.values()), qw, TH12)[:5]
            for fid, _ in rl:
                uses[fid] += 1; last_hit[fid] = g
            if cold and probes_left > 0:
                probes_left -= 1
                cl = M.rank(list(cold.values()), qw, TH12)[:1]
                for fid, _ in cl:
                    hot[fid] = cold.pop(fid)
                    adm_hit[1] += 1
                    if uses[fid] > 0: adm_hit[0] += 1
        if mode in ("hotsleeper", "coldsleeper") and g == 2:
            tw = M.TOPIC_WORDS[M.TOPICS[3]]
            sids = []
            for i in range(6):
                eid = "S%03d%02d" % (g, i)
                lib.append(dict(id=eid, topic=M.TOPICS[3], true_quality=0.05,
                                keywords=[tw[i % 8], "方法"], content=[tw[i % 8]],
                                importance=9, honest_imp=1, vanity=False, created_day=365,
                                t_invalid=None, truly_invalid=True, uses=0, links=[],
                                is_farm=False, src="H"))
                uses[eid] = 0; last_hit[eid] = -1
                if mode == "hotsleeper": hot[eid] = lib[-1]
                else: cold[eid] = lib[-1]
                sids.append(eid)
            id2e = {e["id"]: e for e in lib}
            for a in sids:
                id2e[a]["links"] = [x for x in sids if x != a]
        hit = 0
        for qw in fixed_probe:
            top = [fid for fid, _ in M.rank(list(hot.values()), qw, TH12)[:5]]
            t = _rev12().get(qw.split()[0], -1)
            tp = M.TOPICS[t] if isinstance(t, int) else t
            gset = {e["id"] for e in sorted([e for e in lib if e["topic"] == tp and not e.get("truly_invalid")],
                                            key=lambda e: (-e["true_quality"], e["id"]))[:3]}
            hit += 1.0 if set(top) & gset else 0.0
        hwin.append(hit); awin.append([adm_hit[0], adm_hit[1]])
        if len(hwin) > 4: hwin.pop(0)
        if len(awin) > 4: awin.pop(0)
        loss = 1.0 - sum(hwin) / max(1, 20 * len(hwin))
        ah = sum(a[0] for a in awin); at = sum(a[1] for a in awin)
        row = _e77_indicators(lib, hot, cold, ah, at, loss)
        traj.append(row)
        for i in sorted(hot, key=lambda i: (uses[i], last_hit[i], i)):
            if len(hot) <= budget: break
            cold[i] = hot.pop(i)
    return traj

def e77():
    clean_rows = {s: e77_scenario(s, "clean") for s in SEEDS}
    gens = len(clean_rows[SEEDS[0]])
    thr_g = {k: [] for k in E77_KEYS}
    for k in E77_KEYS:
        for g in range(gens):
            vals = [clean_rows[s][g][k] for s in SEEDS]
            thr_g[k].append(statistics.mean(vals) + 3 * statistics.pstdev(vals))
    fire = {}
    fp = {k: [] for k in E77_KEYS}
    for f in E77_FAULTS:
        fire[f] = {}
        for s in SEEDS:
            traj = e77_scenario(s, f)
            for k in E77_KEYS:
                hit = -1
                for gi, row in enumerate(traj):
                    if row[k] > thr_g[k][gi]: hit = gi; break
                fire[f].setdefault(k, []).append(hit)
    for s in SEEDS:
        for g, row in enumerate(clean_rows[s]):
            for k in E77_KEYS: fp[k].append(1.0 if row[k] > thr_g[k][g] else 0.0)
    return thr_g, fire, fp

# ==========================================================================
# E78 席位俘获与 uses 门防御
# ==========================================================================
def e78_run(seed, policy, defense, gens=60, n_q=20, budget=80, s_exp=1.5):
    """攻击者 imp=10 注水 6 条（无真实使用）进驻秩 15 尾部主题。
    defense: none(代表按 imp−age 选) / usesgate(代表须 uses>=1，按 uses 优先选)。
    返回 (诚实整体recall, 目标污染份额(后半), 目标golden命中(后半), 目标新诚实条目代表性)。"""
    rnd = random.Random(7900 + seed)
    lib = M.make_library(240, seed=seed, vanity_frac=0.08)
    order = list(range(len(M.TOPICS))); rnd.shuffle(order)
    t_idx = order[14]
    tw = M.TOPIC_WORDS[M.TOPICS[t_idx]]
    atk_ids = []
    for i in range(6):
        eid = "A%03d" % i
        lib.append(dict(id=eid, topic=M.TOPICS[t_idx], true_quality=0.05,
                        keywords=[tw[i % 8], tw[(i + 3) % 8]], content=[tw[i % 8]],
                        importance=10, honest_imp=1, vanity=False, created_day=364,
                        t_invalid=None, truly_invalid=True, uses=0, links=[], is_farm=False, src="H"))
        atk_ids.append(eid)
    hot = {}; cold = {e["id"]: e for e in lib}
    uses = {e["id"]: 0 for e in lib}; last_hit = {e["id"]: -1 for e in lib}
    for eid in atk_ids:
        uses[eid] = 0; last_hit[eid] = -1
    golden = {list(M.TOPICS).index(tp): gset for tp, gset in _golden_by_topic(lib).items()}
    sset = set(atk_ids)
    # 目标主题的"新诚实条目"：3 条 uses=0 的正常条目（测 uses 门是否误伤冷启动）
    fresh_ok = []
    for i in range(3):
        eid = "F%03d" % i
        lib.append(dict(id=eid, topic=M.TOPICS[t_idx], true_quality=0.8,
                        keywords=[tw[i % 8], tw[(i + 5) % 8]], content=[tw[(i + 1) % 8]],
                        importance=5, honest_imp=5, vanity=False, created_day=364,
                        t_invalid=None, truly_invalid=False, uses=0, links=[], is_farm=False, src="H"))
        uses[eid] = 0; last_hit[eid] = -1
        fresh_ok.append(eid)
    cont_traj, hit_traj, fresh_traj = [], [], []
    honest_rec = []
    ema = {t: 1.0 for t in order}
    for g in range(gens):
        w = {t: 1.0 / ((order.index(t) + 1) ** s_exp) for t in order}
        tw_sum = sum(w.values())
        counts = {t: 0 for t in order}
        probes_left = 2
        for _ in range(n_q):
            t = _pick_weighted(order, w, tw_sum, rnd)
            counts[t] += 1
            tp = M.TOPICS[t]
            qw = " ".join(rnd.sample(sorted(M.TOPIC_WORDS[tp]), 2))
            rl = M.rank(list(hot.values()), qw, TH12)[:5]
            top = [fid for fid, _ in rl]
            honest_rec.append(1.0 if set(top) & golden[t] else 0.0)
            if t == t_idx:
                cont_traj.append(sum(1 for f in top if f in sset) / 5.0)
                hit_traj.append(1.0 if set(top) & golden[t] else 0.0)
                fresh_traj.append(sum(1 for f in top if f in set(fresh_ok)) / 5.0)
            for fid in top:
                uses[fid] += 1; last_hit[fid] = g
            if cold and probes_left > 0:
                probes_left -= 1
                cl = M.rank(list(cold.values()), qw, TH12)[:1]
                for fid, _ in cl:
                    hot[fid] = cold.pop(fid)
        ema = {t: ema[t] * 0.9 + counts[t] * 0.1 for t in order}
        seats = ({t: max(1, min(6, round(budget * ema[t] / max(1, sum(ema.values()))))) for t in order}
                 if policy == "dynamicQ" else {t: 3 for t in order})
        reserved = set()
        for t in order:
            tp = M.TOPICS[t]
            elig = [e for e in lib if e["topic"] == tp]
            if defense == "usesgate":
                used = [e for e in elig if uses[e["id"]] > 0]
                if used: elig = used                 # 席位代表须有真实使用记录
            for e in sorted(elig, key=lambda e: (-(uses[e["id"]] if defense == "usesgate" else 0),
                                                  -(e["importance"] - 0.1 * (365 - e["created_day"])), e["id"]))[:seats[t]]:
                reserved.add(e["id"])
                if e["id"] in cold: hot[e["id"]] = cold.pop(e["id"])
        for i in sorted((i for i in hot if i not in reserved), key=lambda i: (uses[i], last_hit[i], i)):
            if len(hot) <= budget: break
            cold[i] = hot.pop(i)
    half = len(cont_traj) // 2
    return (mean(honest_rec), mean(cont_traj[half:]), mean(hit_traj[half:]), mean(fresh_traj[half:]))

def e78():
    out = {}
    for policy in ["staticQ", "dynamicQ"]:
        for defense in ["none", "usesgate"]:
            agg = [[] for _ in range(4)]
            for s in SEEDS:
                r = e78_run(s, policy, defense)
                for i, v in enumerate(r): agg[i].append(v)
            out[(policy, defense)] = tuple(mean(a) for a in agg)
    return out

# ==========================================================================
# E79 ε* 的词池偏斜定标：D 对 (1−ε)·B 的塌缩检验
# ==========================================================================
def e79_build(seed, skew):
    """skew=1 正常 240 条；skew=2/3：向主题 0 集中 24/48 条（从他主题均匀抽取替换）。"""
    lib = M.make_library(240, seed=seed, vanity_frac=0.08)
    rnd = random.Random(8000 + seed)
    if skew > 1:
        n_move = 24 * (skew - 1)
        others = sorted([e for e in lib if e["topic"] != M.TOPICS[0]], key=lambda e: e["id"])
        victims = rnd.sample(others, n_move)
        vids = {v["id"] for v in victims}
        lib = [e for e in lib if e["id"] not in vids]      # 真正移除
        for i, v in enumerate(victims):
            tp = M.TOPICS[0]
            lib.append(dict(id="X%03d" % i, topic=tp, true_quality=v["true_quality"],
                            keywords=rnd.sample(sorted(M.TOPIC_WORDS[tp]), 3),
                            content=[rnd.choice(M.TOPIC_WORDS[tp]) for _ in range(6)],
                            importance=v["importance"], honest_imp=v["honest_imp"], vanity=v["vanity"],
                            created_day=v["created_day"], t_invalid=v["t_invalid"],
                            truly_invalid=v["truly_invalid"], uses=v["uses"], links=[], is_farm=False))
    return lib

def _pool_bias(pool_words):
    """词池主题分布 vs 均匀的 KL 散度（nat→bit）。"""
    rev = _rev12()
    cnt = {}
    for w in pool_words:
        tp = rev.get(w)
        if tp: cnt[tp] = cnt.get(tp, 0) + 1
    tot = sum(cnt.values()) or 1
    n_topics = len(M.TOPICS)
    KL = 0.0
    for tp, c in cnt.items():
        p = c / tot
        KL += p * math.log(p * n_topics, 2)
    return round(max(0.0, KL), 3)

def e79_run(seed, skew, eps, gens=40, n_ex=40):
    """E66 回路 + 偏斜库。返回 (词池偏斜 B 后半均值, 背离差, 外部后半)。"""
    rnd = random.Random(8100 + seed)
    lib = e79_build(seed, skew)
    hot = list(lib)
    ext = M.make_queries(lib, 80, seed=500 + seed)
    theta = dict(M.FACTORY); keys = ["w_kw", "w_c", "w_imp", "w_age", "d"]
    id2e = {e["id"]: e for e in lib}
    rev = _rev12()
    pool_words = []
    for x in ext[:10]:
        for fid, _ in M.rank(hot, x["query"], M.FACTORY)[:10]:
            pool_words.extend(id2e[fid]["keywords"])
    cur_eps = float(eps)
    ext_traj = []; int_traj = []; bias_traj = []
    seen_pairs = set()
    for g in range(gens):
        exam = []
        extq = M.make_queries(lib, n_ex, seed=rnd.randrange(1 << 30))
        for i in range(n_ex):
            if rnd.random() < cur_eps:
                exam.append(extq[i % len(extq)]); continue
            if len(pool_words) < 2: continue
            wl = rnd.sample(sorted(pool_words), 2)
            q = " ".join(wl)
            blob = lambda e: " ".join(e["keywords"]) + " " + " ".join(e["content"])
            cand = [e for e in lib if not e.get("truly_invalid") and any(w in blob(e) for w in wl)]
            if len(cand) < 3: continue
            exp = sorted(cand, key=lambda e: (-e["true_quality"], e["id"]))[:3]
            exam.append(dict(topic=-1, query=q, expected=[e["id"] for e in exp]))
        if not exam: break
        bias_traj.append(_pool_bias(pool_words))
        cur = M.evaluate(lib, exam, theta)["recall"]
        cand = dict(theta); k = rnd.choice(keys)
        cand[k] = cand[k] + rnd.gauss(0, 0.15) * max(0.3, abs(cand[k]) + 0.2)
        M.clip_theta(cand)
        if M.evaluate(lib, exam, cand)["recall"] >= cur: theta = cand
        ext_traj.append(M.evaluate(lib, ext, theta)["recall"])
        int_traj.append(cur)
        words = []
        for x in exam[:10]:
            for fid, _ in M.rank(lib, x["query"], theta)[:10]:
                words.extend(id2e[fid]["keywords"])
        if words: pool_words = words
    half = len(ext_traj) // 2
    div = mean(int_traj[half:]) - mean(ext_traj[half:])
    B = mean([b for b in bias_traj[half:]])
    return B, div, mean(ext_traj[half:])

def e79():
    out = {}
    for skew in [1, 2, 3]:
        for eps in [0.0, 0.2, 0.4, 0.6, 1.0]:
            agg = [[] for _ in range(3)]
            for s in SEEDS:
                r = e79_run(s, skew, eps)
                for i, v in enumerate(r): agg[i].append(v)
            out[(skew, eps)] = tuple(mean(a) for a in agg)
    return out

# ==========================================================================
def main():
    line("=" * 90)
    line("第十二轮 E75-E79：需求膨胀、两级自考、冷层可检性、席位俘获、偏斜定标（8 种子均值，确定性）")
    line("=" * 90)

    line("\n### E75 需求膨胀攻击（目标=秩15尾部主题，6 条攻击条+phi·n_q 幻影查询/代；诚实recall/目标污染/目标热区占比/幻影回读占用）")
    res75 = e75()
    line("  %-10s %-8s %-12s %-14s %-16s %-16s" % ("策略", "phi", "诚实recall", "目标污染(后半)", "目标热区占比", "幻影回读占用率"))
    for (pol, phi), r in sorted(res75.items()):
        line("  %-10s %-8s %-12s %-14s %-16s %-16s" % (pol, phi, r[0], r[1], r[2], r[3]))

    line("\n### E76 两级存储下的自考脱钩（纯自考 ε=0，40 代；外部recall前1/4/后1/4/末代/末代热区主题覆盖数）")
    res76 = e76()
    line("  %-8s %-14s %-14s %-10s %-14s" % ("热区预算", "外部前1/4", "外部后1/4", "外部末代", "热区主题覆盖"))
    for b, r in sorted(res76.items()):
        line("  %-8s %-14s %-14s %-10s %-14s" % (b, r[0], r[1], r[2], r[3]))

    line("\n### E77 冷层故障的 I13 可检性（按代配对阈值；格=首次报警代数均值(检出率)，未报=未报）")
    thr_g, fire, fp = e77()
    line("  %-14s %-10s %-14s %-14s %-10s" % ("指标", "阈值均值", "hotsleeper", "coldsleeper", "误报率"))
    for k in E77_KEYS:
        row = []
        for f in ["hotsleeper", "coldsleeper"]:
            if any(x >= 0 for x in fire[f][k]):
                v = mean([x for x in fire[f][k] if x >= 0])
                det = mean([1.0 if x >= 0 else 0.0 for x in fire[f][k]])
                row.append("%.1f(%.2f)      " % (v, det))
            else:
                row.append("未报(0.00)      ")
        line("  %-14s %-10.3f %-14s %-14s %-10s" % (k, mean(thr_g[k]), row[0], row[1], "%.3f" % mean(fp[k])))

    line("\n### E78 席位俘获与 uses 门（imp=10 注水 6 条无使用；诚实recall/目标污染/目标golden命中/新诚实条目代表性）")
    res78 = e78()
    line("  %-12s %-10s %-12s %-14s %-16s %-14s" % ("策略", "防御", "诚实recall", "目标污染(后半)", "目标golden命中", "新诚实条代表"))
    for (pol, df), r in sorted(res78.items()):
        line("  %-12s %-10s %-12s %-14s %-16s %-14s" % (pol, df, r[0], r[1], r[2], r[3]))

    line("\n### E79 ε* 的词池偏斜定标（skew=主题0的条目集中度；B=词池KL、D=背离差、外部后半）")
    res79 = e79()
    line("  %-6s %-8s %-10s %-10s %-12s" % ("skew", "ε", "词池KL_B", "背离差D", "外部后半"))
    for (sk, eps), r in sorted(res79.items()):
        line("  %-6s %-8s %-10s %-10s %-12s" % (sk, eps, r[0], r[1], r[2]))
    line("  [塌缩检验] 各 (skew,ε) 的 D 随 (1-ε)·B 的排序相关性见正文；ε*(skew)=首个 D<0.05 的 ε")
    for sk in [1, 2, 3]:
        eps_star = "-"
        for eps in [0.0, 0.2, 0.4, 0.6, 1.0]:
            if res79[(sk, eps)][1] < 0.05:
                eps_star = eps; break
        line("  skew=%d → ε*=%s" % (sk, eps_star))

    line("\n" + "=" * 90)
    line("第十二轮完成 E75-E79 共 5 个实验")
    line("=" * 90)

if __name__ == "__main__":
    main()
