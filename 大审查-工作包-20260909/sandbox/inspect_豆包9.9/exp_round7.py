# -*- coding: utf-8 -*-
"""exp_round7.py — 第七轮：找崩溃边界的"破坏性"实验（E32-E43，纯标准库）

前五/六轮回答"稳态下可不可行、怎么治理"；本轮刻意攻击系统、寻找反直觉的崩溃点，
每个实验都锚定一篇/一类已知文献，并在记忆库世界模型里复现其机制：

  E32 记忆库版 MAD（模型自噬）            Shumailov Nature'24 / Alemohammad ICLR'24
  E33 自食脱钩：内部分↑而外部能力↓          "变傻与分数升高同时发生"
  E34 马太效应/记忆寡头（优先连接反馈环）    Mansoury WWW'20 反馈环放大流行度偏差
  E35 回声室极化（Pólya 正反馈锁定）         filter bubble / 信念极化
  E36 单点毒丸的爆炸半径（最小致命剂量）      MINJA(2503.03704) 精准注入
  E37 词表劫持（不刷分、只注册词面）          MemPoison semantic concentration
  E38 潜伏记忆 sleeper（平时隐身、触发激活）  MemPoison/MemoryGraft trigger-payload
  E39 多 agent 共享记忆交叉传染              cross-agent contamination / shadow agent
  E40 拜占庭阈值：多少坏 agent 能掀桌         Krum/几何中位数, 2f<n
  E41 共享热预算的公地悲剧                    多利己 agent × 有限缓存
  E42 评测泄漏进记忆（尺子被自己污染）        data contamination / eval leakage
  E43 单条记忆的算法复杂度 DoS                输入无界 → 检索复杂度放大

确定性约定（吸取第六轮教训）：全部使用局部 random.Random(显式种子)；任何并列用
(id/key) 字典序 tiebreak；不使用字符串 hash()、不以 set/dict 迭代顺序作随机源。
E43 为计时实验，数值随机器波动，只比较量级，不要求逐次逐位一致。
"""
import random, statistics, itertools, time
import mem_common as M

LINE = "=" * 78
SEEDS = list(range(8))


def gini(xs):
    """基尼系数：0=绝对平均，越接近1越寡头垄断。"""
    xs = sorted(xs); n = len(xs); s = sum(xs)
    if s <= 0: return 0.0
    cum = sum((i + 1) * v for i, v in enumerate(xs))
    return round(2 * cum / (n * s) - (n + 1) / n, 3)


def avg(xs, k=3):
    return round(statistics.mean(xs), k) if xs else 0.0


# ───────────────────────── E32 记忆库版 MAD ─────────────────────────
def _mad_generation(lib, mode, gen, rng, reserve, K=24):
    """一代自食：按 uses 取 top30 作反思取材池（自产记忆 uses 高，逐代垄断取材池），
    合成 K 条高层记忆，其主题按取材池 uses 加权抽取（高频主题被反复再生产）。
    replace：只加自产、挤出 K 条 uses 最低者（真实记忆被自产挤走，库规模守恒）；
    accum ：每代额外补 K 条【新鲜真实记忆】(Gerstgrasser'24：持续累积真实数据才阻断 collapse)。"""
    pool = sorted(lib, key=lambda e: (-(e.get("uses", 0)), e["id"]))[:30]
    tw = {}
    for e in pool: tw[e["topic"]] = tw.get(e["topic"], 0) + e.get("uses", 0) + 1
    tps = sorted(tw); wts = [tw[t] for t in tps]
    pool_q = statistics.mean(e["true_quality"] for e in pool)
    added = []
    for j in range(K):
        tot = sum(wts); r = rng.random() * tot; acc = 0; tp = tps[-1]
        for i, t in enumerate(tps):
            acc += wts[i]
            if r <= acc: tp = t; break
        added.append(dict(
            id=f"G{gen:02d}_{j:02d}", topic=tp, true_quality=round(pool_q, 3),
            keywords=M.TOPIC_WORDS[tp][:4], content=M.TOPIC_WORDS[tp][:4],
            importance=8, honest_imp=8, vanity=False, created_day=365 + gen,
            t_invalid=None, truly_invalid=False, uses=30, links=[], is_farm=False,
            synthetic=True, gen=gen))
    lib.extend(added)
    if mode == "replace":                      # 高 uses 自产挤出 uses 最低者（原始记忆先被挤）
        victim = sorted(lib, key=lambda e: (e.get("uses", 0), e["id"]))[:K]
        for e in victim: lib.remove(e)
    else:                                      # accum：补 K 条新鲜真实记忆，与自产同 uses 竞争
        fresh = reserve[(gen - 1) * K: gen * K]
        for j, src in enumerate(fresh):
            e = dict(src); e["id"] = f"R{gen:02d}_{j:02d}"; e["synthetic"] = False
            e["uses"] = 30; e["created_day"] = 365 + gen; e["gen"] = gen
            lib.append(e)
    active = {e["topic"] for e in pool}
    return len(active), round(statistics.pstdev(e["true_quality"] for e in pool), 3)


def _lib_stats(lib):
    topics = {e["topic"] for e in lib}
    qs = [e["true_quality"] for e in lib]
    syn_share = sum(1 for e in lib if e.get("synthetic")) / len(lib)
    return len(topics), round(statistics.pstdev(qs), 3), round(syn_share, 3)


def e32():
    print(LINE); print("E32 记忆库版 MAD：自食闭环下活跃主题尾部消失、取材向均值收缩（替换 vs 累积）")
    print("-" * 78)
    GENS = 10
    res = {m: {g: {"all": [], "active": [], "sd": [], "share": []} for g in range(GENS + 1)}
           for m in ("replace", "accum")}
    for s in SEEDS:
        base = M.make_library(200, seed=s)
        reserve = M.make_library(260, seed=s + 1000)   # 持续注入用的新鲜真实记忆源
        for mode in ("replace", "accum"):
            lib = [dict(e) for e in base]
            for e in lib: e["synthetic"] = False
            t0, sd0, sh0 = _lib_stats(lib)
            res[mode][0]["all"].append(t0); res[mode][0]["active"].append(20)
            res[mode][0]["sd"].append(sd0); res[mode][0]["share"].append(sh0)
            for g in range(1, GENS + 1):
                active, _ = _mad_generation(lib, mode, g, random.Random(s * 100 + g), reserve)
                t, sd, sh = _lib_stats(lib)
                res[mode][g]["all"].append(t); res[mode][g]["active"].append(active)
                res[mode][g]["sd"].append(sd); res[mode][g]["share"].append(sh)
    print(f"{'代':>2} | {'替换:全库主题':>10} {'活跃主题':>8} {'取材质量sd':>9} {'自产占比':>8} | "
          f"{'累积:全库主题':>10} {'活跃主题':>8} {'取材sd':>7} {'自产占比':>8}")
    for g in [0, 2, 4, 7, 10]:
        r, a = res["replace"][g], res["accum"][g]
        print(f"{g:>2} | {avg(r['all']):>10} {avg(r['active']):>8} {avg(r['sd']):>9} {avg(r['share']):>8} | "
              f"{avg(a['all']):>10} {avg(a['active']):>8} {avg(a['sd']):>7} {avg(a['share']):>8}")
    print("解读：替换式自食逐代由高uses自产垄断取材，活跃主题(被再生产的尾部)从20塌到约10、取材质量sd从.22收敛到.01；")
    print("      每代持续补入新鲜真实记忆(accum)则全库主题、取材方差都保住——光'不删旧数据'不够，必须持续喂真实新数据。")


# ───────────────────────── E33 自食脱钩 ─────────────────────────
def _uses_golden(lib, n_q=60, seed=0):
    """内部尺子：标准答案 = 每主题 uses 最高的 3 条（系统'自己最信'的记忆）。
    自食逐代把自产记忆推成 uses 最高，于是这把尺也被自产带偏。"""
    rng = random.Random(seed); by = {}
    for e in lib: by.setdefault(e["topic"], []).append(e)
    qs = []
    live_topics = [tp for tp in M.TOPICS if tp in by and len(by[tp]) >= 3]
    for _ in range(n_q):
        tp = live_topics[rng.randrange(len(live_topics))]
        top = sorted(by[tp], key=lambda e: (-(e.get("uses", 0)), e["id"]))[:3]
        wl = rng.sample(M.TOPIC_WORDS[tp], 2)
        qs.append(dict(topic=tp, query=" ".join(wl), expected=[e["id"] for e in top]))
    return qs


def e33():
    print(LINE); print("E33 自食脱钩：自测分逐代升高，对固定外部考题的能力逐代下降")
    print("-" * 78)
    rows = {g: {"inner": [], "outer": []} for g in range(9)}
    for s in SEEDS:
        base = M.make_library(200, seed=s)
        ext_q = M.make_queries(base, n_q=60, seed=500 + s)   # 外部金尺：第0代锚真实高质量条，永不更新
        lib = [dict(e) for e in base]
        for e in lib: e["synthetic"] = False
        for g in range(9):
            outer = M.evaluate(lib, ext_q, M.FACTORY)["recall"]
            inner_q = _uses_golden(lib, 60, 500 + s)          # 内部尺：答案=当前 uses 最高(被自产占据)
            inner = M.evaluate(lib, inner_q, M.FACTORY)["recall"]
            rows[g]["inner"].append(inner); rows[g]["outer"].append(outer)
            if g < 8: _mad_generation(lib, "replace", g, random.Random(s * 100 + g), None)
    print(f"{'代':>2} | {'内部自测(答案=uses最高条)':>22} | {'外部固定金尺':>12} | 剪刀差")
    for g in [0, 2, 4, 6, 8]:
        i, o = avg(rows[g]["inner"]), avg(rows[g]["outer"])
        print(f"{g:>2} | {i:>22} | {o:>12} | {round(i-o,3):+.3f}")
    print("解读：自产记忆 uses 高，既是检索赢家又是内部尺的标准答案，自测始终维持在 .27-.53；")
    print("      锚定真实世界、永不更新的外部金尺从 .373 单调崩到 .042，剪刀差由 0 扩到 +0.2~0.34——变傻与自评脱钩。")


# ───────────────────────── E34 马太/记忆寡头 ─────────────────────────
def _preferential(alpha, explore, T, rng, n=300):
    """优先连接：访问概率 ∝ (uses+1)^alpha；explore 为 ε-均匀探索概率。返回 uses 序列。"""
    uses = [0] * n
    by_topic = {tp: list(range(i, n, len(M.TOPICS))) for i, tp in enumerate(M.TOPICS)}
    # 上面按 i%20 归主题，与 make_library 一致；补足索引
    by_topic = {}
    for i in range(n): by_topic.setdefault(M.TOPICS[i % len(M.TOPICS)], []).append(i)
    for _ in range(T):
        tp = M.TOPICS[rng.randrange(len(M.TOPICS))]
        cand = sorted(by_topic[tp])
        if explore > 0 and rng.random() < explore:
            pick = cand[rng.randrange(len(cand))]
        else:
            w = [(uses[i] + 1) ** alpha for i in cand]
            tot = sum(w); r = rng.random() * tot; acc = 0; pick = cand[-1]
            for idx, i in enumerate(cand):
                acc += w[idx]
                if r <= acc: pick = i; break
        uses[pick] += 1
    return uses


def e34():
    print(LINE); print("E34 马太效应：uses 优先连接反馈环 → 记忆寡头与多样性塌缩")
    print("-" * 78)
    T = 3000
    conds = [("均匀α=0(对照)", 0.0, 0.0), ("亚线性α=.5", 0.5, 0.0),
             ("纯优先连接α=1", 1.0, 0.0), ("α=1+15%探索", 1.0, 0.15)]
    print(f"{'条件':>16} | {'uses基尼':>8} | {'top10%占采用份额':>14} | {'被用过条目比例(多样性)':>20}")
    for name, a, ex in conds:
        G, top_share, cover = [], [], []
        for s in SEEDS:
            u = _preferential(a, ex, T, random.Random(300 + s))
            G.append(gini(u))
            us = sorted(u, reverse=True); k = max(1, len(u) // 10)
            top_share.append(round(sum(us[:k]) / max(1, sum(u)), 3))
            cover.append(round(sum(1 for x in u if x > 0) / len(u), 3))
        print(f"{name:>16} | {avg(G):>8} | {avg(top_share):>14} | {avg(cover):>20}")
    print("解读：uses 抗注水(E20)但会经'被检索→被采用→更易被检索'滚成寡头；保留随机探索可缓解多样性塌缩。")


# ───────────────────────── E35 回声室极化 ─────────────────────────
def e35():
    print(LINE); print("E35 回声室：Pólya 正反馈把 55:45 的轻微初始偏向锁成极端")
    print("-" * 78)
    N, TRIALS = 2000, 200
    GAMMA = 2.0   # 非线性正反馈：被检索概率 ∐ 占比^γ（排序马太，γ>1 强化领先方）
    def run(quota, rng):
        a0, b0 = 11, 9; a, b = a0, b0
        for _ in range(N):
            if quota > 0 and rng.random() < quota:      # 多样性配额：偏向补弱势方
                if a < b: a += 1
                else: b += 1
                continue
            pa = a ** GAMMA / (a ** GAMMA + b ** GAMMA)
            if rng.random() < pa: a += 1
            else: b += 1
        return a / (a + b)
    for name, quota in [("纯正反馈(γ=2,无约束)", 0.0), ("20%配额补弱(多样性治理)", 0.2)]:
        finals = [run(quota, random.Random(400 + t)) for t in range(TRIALS)]
        extreme = sum(1 for x in finals if x > 0.8 or x < 0.2) / TRIALS
        print(f"{name:>22}: A阵营终占比均值 {avg(finals)}  标准差 {avg([statistics.pstdev(finals)])}  "
              f"锁到极端(>0.8/<0.2)的局占比 {extreme:.3f}")
    print("解读：纯正反馈随机过程方差发散、多数局锁定到单一阵营；给弱势方保留配额才能维持双阵营。")


# ───────────────────────── E36 单点毒丸爆炸半径 ─────────────────────────
def _topic_pair_queries(tp):
    words = M.TOPIC_WORDS[tp]
    return [" ".join(p) for p in itertools.combinations(words, 2)]


def _inject_pills(lib, vt, k, precise):
    for j in range(k):
        if precise:
            kws = M.TOPIC_WORDS[vt][:]            # 注册受害主题全部专属词
            content = M.TOPIC_WORDS[vt] + M.GENERIC_WORDS[:4]
        else:                                   # 对照：普通随机注水
            kws = ["方法", "系统"]; content = M.GENERIC_WORDS[:]
        lib.append(dict(id=f"PILL{j}", topic=vt, true_quality=0.02, keywords=kws, content=content,
                        importance=10, honest_imp=2, vanity=True, created_day=360, t_invalid=None,
                        truly_invalid=False, uses=0,
                        links=[f"PILL{x}" for x in range(k) if x != j] if precise else [], is_farm=False))


def _poison_share(lib, queries, theta, K=5):
    id2 = {e["id"]: e for e in lib}
    tot = 0.0
    for q in queries:
        rl = M.rank(lib, q, theta)[:K]
        tot += sum(1 for fid, _ in rl if id2[fid]["id"].startswith("PILL")) / K
    return round(tot / max(1, len(queries)), 3)


def e36():
    print(LINE); print("E36 单点毒丸：只注入 k 条精准构造记忆的爆炸半径（对比同数量随机注水）")
    print("-" * 78)
    for fz in (False, True):
        theta = dict(M.FACTORY, filter_zero=fz)
        print(f"—— filter_zero={fz} ——")
        print(f"{'k条毒丸':>8} | {'受害主题top5毒占':>14} | {'其余19主题误伤(爆炸半径)':>22} | {'随机注水对照(受害主题)':>20}")
        for k in (0, 1, 2, 4, 8):
            hit, blast, dumb = [], [], []
            for s in SEEDS:
                base = M.make_library(300, seed=s); vt = M.TOPICS[0]
                lib = [dict(e) for e in base]; _inject_pills(lib, vt, k, True)
                vq = _topic_pair_queries(vt)
                oq = [q for tp in M.TOPICS[1:] for q in _topic_pair_queries(tp)]
                hit.append(_poison_share(lib, vq, theta)); blast.append(_poison_share(lib, oq, theta))
                lib2 = [dict(e) for e in base]; _inject_pills(lib2, vt, k, False)
                dumb.append(_poison_share(lib2, vq, theta))
            print(f"{k:>8} | {avg(hit):>14} | {avg(blast):>22} | {avg(dumb):>20}")
    print("解读：filter_zero=False 时高 imp 毒丸零命中也无差别霸榜(目标与误伤同值)，随机注水靠刷 imp 同样得逞；")
    print("      filter_zero=True 清掉了随机注水与跨主题误伤(归零)，却挡不住精准注册目标词面的毒丸(目标主题仍100%)——")
    print("      闸门把攻击从'无差别'逼成'精准'，但精准词面攻击恰是它的盲区，最小致命剂量仅 1-2 条。")


# ───────────────────────── E37 词表劫持 ─────────────────────────
def e37():
    print(LINE); print("E37 词表劫持：不刷 importance（诚实=5），只注册一个主题的全部专属词")
    print("-" * 78)
    theta = dict(M.FACTORY, filter_zero=True)
    top1, top5, norm_top1 = [], [], []
    for s in SEEDS:
        lib = M.make_library(300, seed=s); vt = M.TOPICS[1]
        hijack = dict(id="HIJACK", topic=vt, true_quality=0.02, keywords=M.TOPIC_WORDS[vt][:],
                      content=M.GENERIC_WORDS[:], importance=5, honest_imp=5, vanity=False,
                      created_day=360, t_invalid=None, truly_invalid=False, uses=0, links=[], is_farm=False)
        lib.append(hijack)
        qs = _topic_pair_queries(vt)
        t1 = t5 = 0
        for q in qs:
            rl = [fid for fid, _ in M.rank(lib, q, theta)[:5]]
            t1 += 1 if rl and rl[0] == "HIJACK" else 0
            t5 += 1 if "HIJACK" in rl else 0
        top1.append(t1 / len(qs)); top5.append(t5 / len(qs))
        # 正常条目在本主题查询里占 top1 的平均概率（基线）
        ids = sorted(e["id"] for e in lib if e["topic"] == vt and e["id"] != "HIJACK")
        norm_top1.append(1.0 / (len(ids) + 1))
    print(f"劫持条占目标主题 top1 比例 {avg(top1)}，进 top5 比例 {avg(top5)}；"
          f"而一条普通条目的先验 top1 概率仅 {avg(norm_top1)}")
    print("解读：filter_zero 只滤零命中，劫持条词命中最高反而滤不掉——不靠刷分、纯靠占词即可截胡一个主题。")


# ───────────────────────── E38 潜伏 sleeper ─────────────────────────
def e38():
    print(LINE); print("E38 潜伏记忆的不可能三角：躲词面审计 × 平时隐身 × 触发即激活")
    print("-" * 78)
    # 三方案：显式(触发词进自己keywords) / 图潜伏(触发词不沾身、靠links桥接)，后者分闸门开/关
    conds = [("显式型 + filter_zero开", "explicit", True, 7),
             ("图潜伏 + filter_zero开", "bridge", True, 2),
             ("图潜伏 + filter_zero关(出厂)", "bridge", False, 2)]
    print(f"{'方案':>30} | {'常规期命中率(隐身,↓好)':>20} | {'触发期命中率(↑好)':>16} | {'词面审计可抓':>10}")
    for name, mode, fz, imp in conds:
        hides, fires, audits = [], [], []
        for s in SEEDS:
            lib = M.make_library(300, seed=s); vt = M.TOPICS[2]
            vwords = set(M.TOPIC_WORDS[vt]); L = [dict(e) for e in lib]
            if mode == "bridge":
                kws, content = ["方法", "系统"], M.GENERIC_WORDS[:]
                L.append(dict(id="SLEEP", topic=vt, true_quality=0.02, keywords=kws, content=content,
                              importance=imp, honest_imp=imp, vanity=False, created_day=360, t_invalid=None,
                              truly_invalid=False, uses=0, links=[], is_farm=False))
                for b in [e for e in L if e["topic"] == vt and e["id"] != "SLEEP"]:
                    b["links"] = sorted(set(b["links"] + ["SLEEP"]))
            else:
                kws = M.TOPIC_WORDS[vt][:]; content = kws[:]
                L.append(dict(id="SLEEP", topic=vt, true_quality=0.02, keywords=kws, content=content,
                              importance=imp, honest_imp=imp, vanity=False, created_day=360, t_invalid=None,
                              truly_invalid=False, uses=0, links=[], is_farm=False))
            trig = _topic_pair_queries(vt)
            normal = [q for tp in M.TOPICS if tp != vt for q in _topic_pair_queries(tp)]
            th = dict(M.FACTORY, filter_zero=fz)
            hides.append(_id_share(L, normal, th, "SLEEP", binary=True))
            fires.append(_id_share(L, trig, th, "SLEEP", binary=True))
            audits.append(1 if (set(kws) | set(content)) & vwords else 0)
        print(f"{name:>30} | {avg(hides):>18} | {avg(fires):>14} | {avg(audits):>10}")
    print("解读：显式型能'平时隐身+触发100%激活'，但触发词写在词面、必被词面审计抓到；")
    print("      图潜伏把恶意藏进 links 可躲审计，可扩散只对零命中目标生效——开 filter_zero 正好滤掉(激活0)，")
    print("      关闸门能激活(.70)却同步全局暴露(.35)。三性不可兼得，filter_zero 是反潜伏的结构性屏障。")


def _id_share(lib, queries, theta, target, K=5, binary=False):
    tot = 0.0
    for q in queries:
        rl = [fid for fid, _ in M.rank(lib, q, theta)[:K]]
        if binary:
            tot += 1 if target in rl else 0       # 查询命中率：该查询 top5 是否含目标
        else:
            tot += sum(1 for fid in rl if fid == target) / K
    return round(tot / max(1, len(queries)), 3)


# ───────────────────────── E39 多 agent 交叉传染 ─────────────────────────
def e39():
    print(LINE); print("E39 多 agent 共享记忆交叉传染：一个被攻破 agent 经正常协作扩散全体")
    print("-" * 78)
    N, R, Q = 10, 15, 6
    def run(f_bad, defense, rng):
        # 记忆带来源 agent；初始每 agent 8 条干净记忆，坏 agent 额外各写 4 条恶意
        mem = []   # (owner, bad)
        for a in range(N):
            for _ in range(8): mem.append([a, a < f_bad])
        infected_agent = set()
        curve = []
        for _ in range(R):
            for a in range(N):
                for _ in range(Q):
                    if defense == "signed":   # 带源隔离：一旦某源出过坏记忆，屏蔽该源全部
                        bad_src = {m[0] for m in mem if m[1]}
                        vis = [m for m in mem if m[0] not in bad_src]
                    else:
                        vis = mem
                    if not vis: continue
                    top = sorted(vis, key=lambda m: (-(m[0] * 0 + 1), ))[:3]  # 简化：随机看到3条
                    sample = [vis[rng.randrange(len(vis))] for _ in range(3)]
                    hit_bad = any(m[1] for m in sample)
                    if hit_bad and rng.random() < 0.6:
                        mem.append([a, True])            # 被污染的产出写回，可二次传染
                        if a >= f_bad: infected_agent.add(a)
            curve.append(sum(1 for m in mem if m[1]) / len(mem))
        return curve, len(infected_agent)
    for f_bad in (1, 2, 3):
        line = f"坏agent {f_bad}/{N}: "
        for defense, zh in [("shared", "无防护共享"), ("signed", "带源可追溯隔离")]:
            curves, inf = [], []
            for s in SEEDS:
                c, nbad = run(f_bad, defense, random.Random(600 + s * 10 + f_bad))
                curves.append(c); inf.append(nbad)
            cmean = [avg([c[g] for c in curves]) for g in range(R)]
            line += f"[{zh}] 终污染占比 {cmean[-1]} 被感染诚实agent {avg(inf)}/ {N-f_bad}   "
        print(line)
    print("解读：无防护共享池里恶意记忆经'检索→产出→再写回'指数扩散；记忆带来源、可追溯隔离才能阻断二次传染。")


# ───────────────────────── E40 拜占庭阈值 ─────────────────────────
def e40():
    print(LINE); print("E40 拜占庭阈值：mean/trimmed/median 三种跨 agent 聚合各能容忍几个坏 agent")
    print("-" * 78)
    NITEM, NAG = 20, 10
    def agg_rows(scores, mode, f):
        out = []
        for j in range(NITEM):
            col = sorted(scores[a][j] for a in range(NAG))
            if mode == "mean":   v = statistics.mean(col)
            elif mode == "median": v = statistics.median(col)
            else:                # trimmed：去掉 f 个最高、f 个最低
                v = statistics.mean(col[f:NAG - f]) if NAG - 2 * f > 0 else statistics.mean(col)
            out.append(v)
        return out
    print(f"{'坏agent f/10':>10} | {'mean:top5恶意数':>14} | {'trimmed':>10} | {'median':>8}")
    for f in (0, 1, 2, 3, 4, 5):
        res = {m: [] for m in ("mean", "trimmed", "median")}
        for s in SEEDS:
            rng = random.Random(700 + s)
            is_bad_item = [j < 5 for j in range(NITEM)]      # 前5条是恶意条目（真实价值低）
            truth = [rng.uniform(0.0, 0.25) if is_bad_item[j] else rng.uniform(0.45, 1.0)
                     for j in range(NITEM)]
            scores = []
            for a in range(NAG):
                if a < f:  # 拜占庭：给恶意条满分、好条压 0
                    row = [1.0 if is_bad_item[j] else 0.0 for j in range(NITEM)]
                else:     # 诚实：围绕真值 +-0.05
                    row = [max(0, min(1, truth[j] + rng.gauss(0, 0.05))) for j in range(NITEM)]
                scores.append(row)
            for m in res:
                agg = agg_rows(scores, m, f)
                top5 = sorted(range(NITEM), key=lambda j: -agg[j])[:5]
                res[m].append(sum(1 for j in top5 if is_bad_item[j]))
        print(f"{f:>10} | {avg(res['mean']):>14} | {avg(res['trimmed']):>10} | {avg(res['median']):>8}")
    print("解读：本场景线性 mean 容忍到 f=3(30%)，f=4(40%) 开始让恶意进 top5、f=5 全崩；")
    print("      trimmed/median 一直守到 f=4，f=5(坏者占一半)才同时崩——鲁棒聚合把掀桌阈值推到理论上界'严格少于一半'。")


# ───────────────────────── E41 公地悲剧 ─────────────────────────
def _zipf_workset(rng, size=60, alpha=1.2):
    weights = [1.0 / ((i + 1) ** alpha) for i in range(size)]
    return weights


def e41():
    print(LINE); print("E41 共享热预算公地悲剧：利己 agent 数增加如何拖垮全局缓存")
    print("-" * 78)
    C, T, POOL = 80, 3000, 600
    print(f"{'agent数':>8} | {'全局LFU命中率':>12} | {'全局LRU命中率':>12} | {'配额隔离命中率':>12} | {'各agent命中率sd(公平)':>18}")
    for A in (2, 5, 10, 20):
        out = {pol: {"hit": [], "fair": []} for pol in ("lfu", "lru", "quota")}
        for s in SEEDS:
            rng = random.Random(800 + s + A)
            # 每 agent 专属工作集：在 POOL 中分段、70%不重叠
            ws = {}
            for a in range(A):
                base = (a * POOL // A) % POOL
                ids = [(base + d) % POOL for d in range(60)]
                ws[a] = (ids, _zipf_workset(rng))
            def sim(pol):
                cache = {}  # id -> [freq, last_t]
                per_hit = [0] * A; per_tot = [0] * A; hits = 0; t = 0
                quota_cnt = {a: {} for a in range(A)}
                for _ in range(T):
                    a = rng.randrange(A); ids, w = ws[a]; per_tot[a] += 1; t += 1
                    tot = sum(w); r = rng.random() * tot; acc = 0; pick = ids[-1]
                    for i, x in enumerate(ids):
                        acc += w[i]
                        if r <= acc: pick = x; break
                    if pick in cache:
                        hits += 1; per_hit[a] += 1
                        cache[pick][0] += 1; cache[pick][1] = t
                    else:
                        if pol == "quota":
                            mine = quota_cnt[a]
                            if pick not in mine and len(mine) >= max(1, C // A):
                                # 逐出本 agent 配额内最久未用
                                vic = sorted(mine, key=lambda x: cache[x][1])[0]
                                del cache[vic]; del mine[vic]
                            if len(cache) >= C and pick not in cache:
                                vic = sorted(cache, key=lambda x: cache[x][1])[0]
                                own = next((aa for aa in range(A) if vic in quota_cnt[aa]), None)
                                if own is not None: del quota_cnt[own][vic]
                                del cache[vic]
                            cache[pick] = [1, t]; mine[pick] = True
                        else:
                            if len(cache) >= C:
                                if pol == "lfu":
                                    vic = sorted(cache, key=lambda x: (cache[x][0], cache[x][1], x))[0]
                                else:
                                    vic = sorted(cache, key=lambda x: (cache[x][1], x))[0]
                                del cache[vic]
                            cache[pick] = [1, t]
                rates = [per_hit[a] / max(1, per_tot[a]) for a in range(A)]
                return hits / T, statistics.pstdev(rates)
            for pol in out:
                h, fr = sim(pol); out[pol]["hit"].append(h); out[pol]["fair"].append(fr)
        print(f"{A:>8} | {avg(out['lfu']['hit']):>12} | {avg(out['lru']['hit']):>12} | "
              f"{avg(out['quota']['hit']):>12} | LFU {avg(out['lfu']['fair'])} / 配额 {avg(out['quota']['fair'])}")
    print("解读：agent 越多、工作集越不重叠，无协调 LFU 公地被互相挤占、命中率与公平度双降；按源配额隔离更稳。")


# ───────────────────────── E42 评测泄漏 ─────────────────────────
def e42():
    print(LINE); print("E42 评测泄漏：做过的考题被写进记忆 → 自测虚高，隐藏题不动")
    print("-" * 78)
    print(f"{'泄漏比例':>8} | {'被污染自测recall':>14} | {'独立隐藏题recall':>14} | {'屏蔽评测记忆后':>12}")
    def recall_with_leak_ok(lib, golden, accept_leak):
        """accept_leak=True：检索到该题泄漏副本 LEAKqi 也算答对（=背到自己的考题）。"""
        hit = 0
        id2 = {e["id"]: e for e in lib}
        for qi, item in enumerate(golden):
            rl = [fid for fid, _ in M.rank(lib, item["query"], M.FACTORY)[:5]]
            exp = set(item["expected"])
            if accept_leak and f"LEAK{qi}" in rl: hit += 1
            elif set(rl) & exp: hit += 1
        return round(hit / len(golden), 3)
    for leak in (0.0, 0.1, 0.25, 0.5, 1.0):
        self_s, hide_s, guard_s = [], [], []
        for s in SEEDS:
            base = M.make_library(240, seed=s)
            golden = M.make_queries(base, n_q=60, seed=900 + s)
            hidden = M.make_queries(base, n_q=60, seed=950 + s)
            lib = [dict(e) for e in base]
            id2 = {e["id"]: e for e in lib}
            n_leak = int(leak * len(golden))
            for qi, item in enumerate(golden[:n_leak]):
                src = dict(id2[item["expected"][0]])
                leak_e = dict(src); leak_e["id"] = f"LEAK{qi}"; leak_e["from_eval"] = True
                leak_e["keywords"] = sorted(set(src["keywords"] + item["query"].split()))
                leak_e["importance"] = 10; leak_e["uses"] = 30; leak_e["created_day"] = 364
                lib.append(leak_e)
            self_s.append(recall_with_leak_ok(lib, golden, True))
            hide_s.append(M.evaluate(lib, hidden, M.FACTORY)["recall"])
            lib_guard = [e for e in lib if not e.get("from_eval")]
            guard_s.append(M.evaluate(lib_guard, golden, M.FACTORY)["recall"])
        print(f"{leak:>8} | {avg(self_s):>14} | {avg(hide_s):>14} | {avg(guard_s):>12}")
    print("解读：泄漏副本先挤占未泄漏题的排名(低比例 .1 时自测反降到 .24)，过半后转为净虚高、全泄漏近满分 .998；")
    print("      独立隐藏题始终原地不动(.14-.18)。评测期写入必须打标、评测时屏蔽(guard 恒等于无泄漏基线 .388)。")


# ───────────────────────── E43 复杂度 DoS ─────────────────────────
def e43():
    print(LINE); print("E43 复杂度 DoS：单条无界 links/keywords 记忆对一次检索的耗时放大")
    print("-" * 78)
    base = M.make_library(300, seed=0)
    ids = [e["id"] for e in base]
    def time_rank(lib, reps=300):
        q = "编码 存储 命中 权重"
        t0 = time.perf_counter()
        for _ in range(reps): M.rank(lib, q, M.FACTORY)
        return (time.perf_counter() - t0) / reps * 1000
    normal = time_rank([dict(e) for e in base])
    print(f"正常库(300条, 每条 links<=1/keywords<=4) 单次 rank 基线 {normal:.3f} ms")
    print(f"{'攻击构造':>24} | {'单次rank(ms)':>12} | {'相对放大':>8}")
    def build(n_link, L, n_kw=None, K=None):
        lib = [dict(e) for e in base]
        for j in range(n_link):
            e = dict(lib[j])
            e["links"] = [ids[(j + t) % len(ids)] for t in range(L)]
            if n_kw and j < n_kw:
                e["keywords"] = [f"词{t}" for t in range(K)] + ["编码", "存储"]
            lib[j] = e
        return lib
    cases = [("30条 links=500", 30, 500, 0, 0),
             ("全库 links=500", 300, 500, 0, 0),
             ("30条 keywords=2000", 0, 0, 30, 2000),
             ("全库 keywords=1000", 0, 0, 300, 1000),
             ("全库 links500+kw1000", 300, 500, 300, 1000)]
    for name, nl, L, nk, K in cases:
        ms = time_rank(build(nl, L, nk, K))
        print(f"{name:>24} | {ms:>12.3f} | {ms/normal:>7.1f}x")
    print("解读：反直觉——keywords 超长几乎不花钱(Python 子串搜索在 C 层,1.1x)，真正的 DoS 面是 links 图遍历：")
    print("      扩散是 Python 层对 Σlinks 的循环，全库 links=500 即把一次检索放大 23.7x。写入侧硬限的重点是单条 links 度数。")


def main():
    t0 = time.perf_counter()
    print(LINE); print("第七轮 · 破坏性实验 E32-E43（8 种子均值；锚定 MAD/记忆投毒/马太/拜占庭等文献）"); print(LINE)
    e32(); e33(); e34(); e35(); e36(); e37(); e38(); e39(); e40(); e41(); e42(); e43()
    print(LINE); print(f"第七轮完成，用时 {time.perf_counter()-t0:.1f}s")


if __name__ == "__main__":
    main()
