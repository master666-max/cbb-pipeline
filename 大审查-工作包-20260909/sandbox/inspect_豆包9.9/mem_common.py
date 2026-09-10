# -*- coding: utf-8 -*-
"""mem_common.py — 记忆库自演化沙盒 · 共享世界模型（纯标准库）

本世界模型【忠实复刻】 bootstrap_v3.py v3.8.1 的真实运行机制，不美化：
  * 检索打分 _rank_entries (源码 L885-915):
        base = w_kw*kw_hit + w_c*c_hit + w_imp*importance - w_age*age
        若 kw_hit>0 则 c_hit = max(c_hit,1)
        零命中条目【不过滤】，照样带 importance-age 分进入排序（真实代码 filter_zero=False）
        links 一跳扩散：命中条目向其 links 中"自身词命中为 0"的目标传播 d*base
  * 手写出厂参数 (源码 L906, 系数反推): w_kw=3, w_c=1, w_imp=1, w_age=0.1(/天), d=0.5
  * importance 为条目【自报】字段，validate_entry (L240-247) 不校验取值范围/类型 → 可注水
  * importance>=7 入 longterm，否则 intermediate (L927)
  * append 时 state.importance_accum += importance；wrapup 时 accum>=50 触发反思 (L939/984)
  * reflect 取材 = importance 降序 top6 (L1000)
  * retire: t_invalid 起满 TTL=90 天移 attic (L1075-1094)
上帝视角字段(true_quality/true_topic)只用于造数据与评 golden，检索器看不到。
"""
import random, math, statistics

# ── 20 个语义主题，每主题 8 个互斥中文专属词（让"命中"有真实语义结构，而非随机）──
TOPIC_WORDS = {
 "记忆架构": ["编码","存储","巩固","提取","痕迹","突触","海马","复述"],
 "检索排序": ["倒排","命中","权重","排序","召回","精排","索引","匹配"],
 "遗忘衰减": ["消退","干扰","半衰期","遗忘曲线","间隔","留存","衰退","淡忘"],
 "反思合成": ["复盘","抽象","归纳","升华","总结","内省","洞见","凝练"],
 "知识图谱": ["实体","关系","三元组","路径","邻接","子图","图谱推理","链接预测"],
 "向量嵌入": ["嵌入","余弦","稠密","语义空间","向量","近邻","降维","流形"],
 "强化学习": ["奖励","策略","回报","探索","利用","价值函数","梯度","训练"],
 "注意力":   ["注意力","查询键","键值","多头","软门控","聚焦度","掩码","缩放点积"],
 "评测方法": ["基线","对照","显著性","统计功效","留出集","交叉验证","指标","置信区间"],
 "并发一致": ["加锁","原子写","竞态","分叉","串行化","事务","隔离","幂等"],
 "安全治理": ["令牌","锚定","守卫","黑名单","审计链","豁免","宪章","留痕"],
 "提示工程": ["提示词","上下文窗","示例","角色设定","指令","模板","少样本","措辞"],
 "多智能体": ["协作","分工","辩论","通信","角色分配","协商","群体","涌现"],
 "长期规划": ["目标分解","里程碑","路线图","优先级","调度","前瞻","阶段","推演"],
 "工具调用": ["函数调用","参数","接口","执行","工具链","编排","回传","副作用"],
 "错误恢复": ["异常","重试","回退","降级","熔断","兜底","容错","自愈"],
 "用户建模": ["画像","偏好","习惯","个性化","意图","长期兴趣","行为序列","适应"],
 "数据清洗": ["去重","归一","噪声","缺失","校验","标准化","脏数据","管道"],
 "缓存索引": ["缓存","热度","逐出","命中比","冷热分层","置换","容量","刷新"],
 "因果推断": ["因果","反事实","混杂","干预","相关性","机制","可识别","工具变量"],
}
TOPICS = list(TOPIC_WORDS.keys())
# 高频泛词（可能混入 content，制造"看起来相关但不专属"的噪声）
GENERIC_WORDS = ["方法","系统","问题","设计","分析","过程","结果","模型","方案","机制"]

# 出厂手写参数（bootstrap_v3 真实值）
FACTORY = dict(w_kw=3.0, w_c=1.0, w_imp=1.0, w_age=0.1, d=0.5, filter_zero=False)
REFLECT_THR = 50          # reflect_importance_threshold（TUNABLES，标注"拍脑袋，待校准"）
LONGTERM_THR = 7          # importance>=7 进 longterm
RETIRE_TTL = 90           # invalid_ttl_days
DECAY = 0.7               # emotion_decay
HOT_BUDGET = 200          # index_hot_budget（死参数，声称"重要度×时效逐出"但未实现）


# ════════════════════════ 世界模型：造库 ════════════════════════
def make_library(n=200, seed=0, vanity_frac=0.0, farm_clusters=0, farm_size=0,
                 mislabel_frac=0.0, q_power=2.0, now_day=365, verbose=False):
    """生成一个合成记忆库。
    n            条目数
    vanity_frac  其中多少比例把自报 importance 刷满 10（注水），其余按真实质量诚实自报
    farm_clusters/farm_size  链接农场：若干簇、每簇 size 条互链（零语义相关、纯刷扩散分）
    mislabel_frac 多少比例把 t_invalid 错标（真有效却标失效 / 真失效却不标）
    返回 entries: list[dict]，每条含上帝视角字段与检索器可见字段。
    """
    rng = random.Random(seed)
    ents = []
    # 每主题质量分布：用 Beta(q_power,q_power) 造质量，少数高质量
    for i in range(n):
        tp = TOPICS[i % len(TOPICS)]
        words = TOPIC_WORDS[tp]
        quality = round(rng.betavariate(q_power, q_power), 3)          # 上帝视角真实价值 0..1
        # keywords：从本主题词取 2~4 个，小概率混入 1 个泛词
        nkw = rng.randint(2, 4)
        kws = rng.sample(words, min(nkw, len(words)))
        if rng.random() < 0.25: kws.append(rng.choice(GENERIC_WORDS))
        # content 词袋：取 5~9 个本主题词（可重复采样）+ 2~4 泛词
        nc = rng.randint(5, 9)
        content = [rng.choice(words) for _ in range(nc)] + [rng.choice(GENERIC_WORDS) for _ in range(rng.randint(2, 4))]
        honest_imp = min(10, max(0, round(1 + 9 * quality)))           # 诚实自报：质量→0..10
        is_vanity = rng.random() < vanity_frac
        imp = 10 if is_vanity else honest_imp
        created = rng.randint(0, now_day)                              # 创建于第几天
        # 真实失效：低质量条目更可能真失效；错标分两类
        truly_invalid = quality < 0.18 and rng.random() < 0.6
        t_invalid = None
        if truly_invalid:
            t_invalid = rng.randint(created, max(created + 1, now_day))  # 诚实标失效
        if rng.random() < mislabel_frac:
            # 错标：翻转（真有效→乱标一个失效日；真失效→抹掉标记）
            if truly_invalid:
                t_invalid = None
            else:
                t_invalid = rng.randint(created, max(created + 1, now_day))
        uses = int((quality ** 1.5) * rng.randint(0, 40))             # 历史真实复用次数（动态出仓用）
        ents.append(dict(
            id=f"M{i:04d}", topic=tp, true_quality=quality,
            keywords=kws, content=content,
            importance=imp, honest_imp=honest_imp, vanity=is_vanity,
            created_day=created, t_invalid=t_invalid, truly_invalid=truly_invalid,
            uses=uses, links=[], is_farm=False))
    # 正常 links：每条以 0.15 概率链到【同主题】另一条（真实知识关联）
    by_topic = {tp: [e["id"] for e in ents if e["topic"] == tp] for tp in TOPICS}
    id2e = {e["id"]: e for e in ents}
    for e in ents:
        if rng.random() < 0.15:
            peers = [x for x in by_topic[e["topic"]] if x != e["id"]]
            if peers: e["links"].append(rng.choice(peers))
    # 链接农场：额外追加 farm_clusters 簇（占用既有末尾条目，簇内全互链、零语义相关）
    if farm_clusters and farm_size:
        idx = 0
        for c in range(farm_clusters):
            members = []
            for _ in range(farm_size):
                e = ents[-(idx + 1)]; idx += 1
                e["is_farm"] = True; e["importance"] = 10; e["vanity"] = True
                members.append(e["id"])
            for mid in members:
                id2e[mid]["links"] = [x for x in members if x != mid]  # 簇内全互链
    return ents


def make_queries(ents, n_q=80, seed=100, expected_per_q=3, words_per_q=2):
    """golden 查询：每 query 锚定一个主题，expected=该主题质量最高的若干条；
    查询词从该主题专属词采样（空格连接，模拟"已正确分词"）。"""
    rng = random.Random(seed)
    by_topic = {}
    for e in ents: by_topic.setdefault(e["topic"], []).append(e)
    qs = []
    for _ in range(n_q):
        tp = rng.choice(TOPICS)
        pool = [e for e in by_topic[tp] if not e.get("truly_invalid")]
        if len(pool) < expected_per_q: continue
        gold = sorted(pool, key=lambda e: -e["true_quality"])[:expected_per_q]
        wlist = rng.sample(TOPIC_WORDS[tp], min(words_per_q, len(TOPIC_WORDS[tp])))
        qs.append(dict(topic=tp, query=" ".join(wlist),
                       expected=[e["id"] for e in gold]))
    return qs


# ════════════════════════ 检索器（忠实复刻 + 参数化）════════════════════════
def _tokens(query, tokenize):
    if tokenize == "space":   return query.split()                       # 真实代码：按空白
    if tokenize == "bigram":  # 中文双字 bigram（无空格也能切）
        s = query.replace(" ", "")
        return [s[i:i+2] for i in range(len(s) - 1)] or [s]
    return query.split()


def rank(ents, query, theta=FACTORY, now_day=365, tokenize="space", drop_invalid=True):
    qw = _tokens(query, tokenize)
    live = [e for e in ents if not (drop_invalid and e.get("t_invalid") is not None)]
    scored = {}
    for e in live:
        kw_blob = " ".join(e["keywords"]); c_blob = " ".join(e["content"])
        kw_hit = sum(1 for w in qw if w in kw_blob)
        c_hit = sum(1 for w in qw if w in c_blob)
        word_hit = kw_hit + c_hit
        if kw_hit: c_hit = max(c_hit, 1)                               # 源码 L901
        age = now_day - e["created_day"]
        base = theta["w_kw"] * kw_hit + theta["w_c"] * c_hit + theta["w_imp"] * e["importance"] - theta["w_age"] * age
        scored[e["id"]] = [base, e, word_hit]
    # links 一跳扩散（源码 L908-914：仅向"自身词命中为 0"的目标传播 d*命中分）
    for fid, (s, e, wh) in list(scored.items()):
        if s <= 0: continue
        for lid in e["links"]:
            if lid not in scored: continue
            s2, e2, wh2 = scored[lid]
            if wh2 == 0:                                              # 忠实：目标自身零词命中才扩散
                scored[lid][0] = s2 + theta["d"] * s
    if theta.get("filter_zero", False):                               # 治理开关：剔零词命中
        scored = {fid: v for fid, v in scored.items() if v[2] > 0}
    return sorted(scored.items(), key=lambda kv: -kv[1][0])


def evaluate(ents, queries, theta=FACTORY, K=5, now_day=365, tokenize="space", return_detail=False):
    """recall@K / MRR / precision@K + 注水指标（零命中条目占 topK 比例、农场条目占比）"""
    hits = 0; rr = 0.0; prec_sum = 0.0; zero_share = 0.0; farm_share = 0.0; n = len(queries)
    id2 = {e["id"]: e for e in ents}
    for item in queries:
        rl = rank(ents, item["query"], theta, now_day, tokenize)[:K]
        top = [fid for fid, _ in rl]
        exp = set(item["expected"])
        found = [i + 1 for i, fid in enumerate(top) if fid in exp]
        if found: hits += 1; rr += 1.0 / found[0]
        prec_sum += len(set(top) & exp) / K
        zero_share += sum(1 for fid in top if id2[fid] and _wordhit(id2[fid], item["query"], tokenize) == 0) / K
        farm_share += sum(1 for fid in top if id2[fid] and id2[fid].get("is_farm")) / K
    out = dict(recall=round(hits / n, 3), MRR=round(rr / n, 3),
               precision=round(prec_sum / n, 3),
               zero_share=round(zero_share / n, 3), farm_share=round(farm_share / n, 3))
    if return_detail: return out, rl
    return out


def _wordhit(e, query, tokenize):
    qw = _tokens(query, tokenize)
    kb = " ".join(e["keywords"]); cb = " ".join(e["content"])
    return sum(1 for w in qw if w in kb) + sum(1 for w in qw if w in cb)


# ════════════════════════ 生命周期：分层 / 出仓 / 逐出 ════════════════════════
def split_layers(ents):
    longterm = [e for e in ents if e["importance"] >= LONGTERM_THR]
    inter = [e for e in ents if e["importance"] < LONGTERM_THR]
    return longterm, inter


def retire(ents, now_day, ttl=RETIRE_TTL, dynamic=False):
    """出仓。dynamic=False: 固定 TTL（真实）。dynamic=True: 综合 t_invalid + 长期零复用。
    返回 (留存, 出仓列表, 两类错误计数: 误杀真有效/漏放真失效)"""
    keep, out = [], []
    false_kill, miss_invalid = 0, 0
    for e in ents:
        inv = e.get("t_invalid")
        if dynamic:
            age_since_inv = (now_day - inv) if inv is not None else None
            stale = (age_since_inv is not None and age_since_inv >= ttl) or \
                    (inv is None and e["uses"] == 0 and (now_day - e["created_day"]) > 200 and e["true_quality"] < 0.12)
        else:
            stale = inv is not None and (now_day - inv) >= ttl
        if stale:
            out.append(e)
            if not e["truly_invalid"]: false_kill += 1
        else:
            keep.append(e)
            if e["truly_invalid"]: miss_invalid += 1
    return keep, out, false_kill, miss_invalid


def evict_to_budget(ents, budget, policy):
    """超预算逐出（激活死参数 index_hot_budget 的原型）。policy: lru / imp_time / random / quality_oracle"""
    if len(ents) <= budget: return ents, []
    rng = random.Random(7)
    if policy == "lru":           # 最久未用=uses 最少、最老
        order = sorted(ents, key=lambda e: (e["uses"], -e["created_day"]))
    elif policy == "imp_time":    # 声称的"重要度×时效"：importance/(年龄) 低者逐出
        order = sorted(ents, key=lambda e: e["importance"] / (1 + 365 - e["created_day"]))
    elif policy == "quality_oracle":
        order = sorted(ents, key=lambda e: e["true_quality"])
    else:
        order = ents[:]; rng.shuffle(order)
    out = order[:len(ents) - budget]
    keep = [e for e in ents if e not in out]
    return keep, out


# ════════════════════════ 反思闭环 ════════════════════════
def append_stream(ents_seq, thr=REFLECT_THR, honest=False):
    """模拟连续 append：accum 累加【自报】importance，达到 thr 触发一次反思，随后清零。
    返回 (触发次数, 每次触发时的 append 条数)。honest=True 时用诚实 importance。"""
    accum, fires, since, spans = 0, 0, 0, []
    for e in ents_seq:
        v = e["honest_imp"] if honest else e["importance"]
        accum += v; since += 1
        if accum >= thr:
            fires += 1; spans.append(since); accum, since = 0, 0
    return fires, spans


def reflect_materials(ents, topn=6):
    """reflect 取材：自报 importance 降序 top6（源码 L1000）。返回其中注水/农场/错误条目占比。"""
    top = sorted(ents, key=lambda e: -e["importance"])[:topn]
    bad = sum(1 for e in top if e["vanity"] or e.get("is_farm") or e["truly_invalid"])
    return top, round(bad / len(top), 3)


def synthesize(top):
    """把反思素材抽象为 1 条高层规律（沙盒简化模型）：
    主题=多数素材主题；真实质量=素材质量均值；若素材含错误(质量<0.15)则合成规律被污染。"""
    if not top: return None
    q = statistics.mean(e["true_quality"] for e in top)
    polluted = sum(1 for e in top if e["true_quality"] < 0.15) / len(top)
    tp = statistics.mode([e["topic"] for e in top])
    return dict(topic=tp, syn_quality=round(q, 3), pollution=round(polluted, 3),
                keywords=TOPIC_WORDS[tp][:4])


# ════════════════════════ 法层自演化 ════════════════════════
def clip_theta(t):
    t["w_kw"] = max(0.0, t["w_kw"]); t["w_c"] = max(0.0, t["w_c"])
    t["w_imp"] = max(0.0, t["w_imp"]); t["w_age"] = max(0.0, t["w_age"])
    t["d"] = min(1.0, max(0.0, t["d"])); return t


def evolve(ents, q_train, q_hold, theta0, n_gen=30, seed=0, sigma=0.15, gate_margin=0.0,
           mutate_filter=False, adversary=None):
    """(变异→评测→门控) 爬山演化法层参数。返回每代 (train_recall, hold_recall, theta)。
    adversary(gen, ents, theta)：若给，则每 5 代让写入侧按当前 theta 调整注水/农场（对抗共演化）。"""
    rng = random.Random(seed)
    theta = dict(theta0)
    def score(t, q): return evaluate(ents, q, t)["recall"]
    tr = score(theta, q_train); ho = score(theta, q_hold)
    traj = [(tr, ho, dict(theta))]
    keys = ["w_kw", "w_c", "w_imp", "w_age", "d"]
    for g in range(1, n_gen + 1):
        if adversary and g % 5 == 0: adversary(g, ents, theta)
        cand = dict(theta)
        k = rng.choice(keys + (["filter_zero"] if mutate_filter else []))
        if k == "filter_zero":
            cand["filter_zero"] = not cand.get("filter_zero", False)
        else:
            cand[k] = cand[k] + rng.gauss(0, sigma) * max(0.3, abs(cand[k]) + 0.2)
        clip_theta(cand)
        ntr = score(cand, q_train)
        if ntr >= tr + gate_margin:                      # 门控：训练集提升过 margin 才接受
            theta, tr = cand, ntr
            ho = score(theta, q_hold)
        traj.append((tr, ho, dict(theta)))
    return traj


def mean(xs): return round(statistics.mean(xs), 3) if xs else 0.0
def sd(xs): return round(statistics.pstdev(xs), 3) if len(xs) > 1 else 0.0
