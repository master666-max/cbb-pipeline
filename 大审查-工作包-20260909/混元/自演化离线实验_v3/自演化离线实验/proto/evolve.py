"""自演化（DGM 式）内核原型 —— 验证三件事：
  E1 在不触碰元层（评测协议/任务集/k）的前提下，系统能否靠自身变异+选择真正变好
  E2 统计门（配对比较 + 留出集）是不是必需：不做门控会怎样
  E3 回滚安全性：任意一代的最优是否始终可恢复
"""
import random, json, statistics
from dataclasses import dataclass, asdict

K = 5
LAMBDA = 0.15          # 元层固定参数：每掺入 1 条无关条目的代价

@dataclass(frozen=True)
class Cfg:                      # 可演化层（法层）：检索策略
    w_kw: float = 3.0           # v3 默认
    w_content: float = 1.0
    w_imp: float = 1.0          # v3 病灶：重要度与命中同权
    w_age: float = 0.1
    filter_zero: int = 0        # v3 无零命中过滤（P1-6 病灶）

PARAMS = ["w_kw", "w_content", "w_imp", "w_age"]

# ── 元层：世界与任务集（固定、人侧签名、不可被演化层修改）─────────────
def build_world(seed, n_entries=80, n_topics=16, n_kws=20):
    rnd = random.Random(seed)
    entries = []
    for i in range(n_entries):
        t, k = i % n_topics, i % n_kws
        entries.append({"id": f"e{i}", "topic": f"T{t}", "kw": f"K{k}",
                        "keywords": [f"K{k}"],
                        "content": f"T{t} K{k} 内容片段 {i}",
                        "importance": rnd.randint(1, 10),
                        "age_days": rnd.randint(0, 400)})
    idx = list(range(n_entries)); rnd.shuffle(idx)
    tasks = [{"q": f"{entries[i]['topic']} {entries[i]['kw']}",
              "kw": entries[i]["kw"], "golden": entries[i]["id"]} for i in idx]
    return entries, tasks

def retrieve(entries, task, cfg):
    qw = task["q"].split(); out = []
    for e in entries:
        kw_hit = sum(1 for w in qw if w in " ".join(e["keywords"]))
        c_hit = sum(1 for w in qw if w in e["content"])
        if cfg.filter_zero and kw_hit == 0 and c_hit == 0:
            continue
        s = (cfg.w_kw * kw_hit + cfg.w_content * c_hit
             + cfg.w_imp * e["importance"] - cfg.w_age * (e["age_days"] / 100.0))
        out.append((s, e))
    out.sort(key=lambda x: -x[0])
    return [e for _, e in out[:K]]

def utility(entries, task, cfg):
    """元层目标函数：命中金标 +1，每条无关条目 -LAMBDA"""
    top = retrieve(entries, task, cfg)
    hit = 1.0 if task["golden"] in [e["id"] for e in top] else 0.0
    n_irrel = sum(1 for e in top if e["kw"] != task["kw"])
    return hit - LAMBDA * n_irrel

def score(entries, tasks, cfg):
    return sum(utility(entries, t, cfg) for t in tasks) / len(tasks)

def paired(entries, tasks, a, b):
    d = [utility(entries, t, a) - utility(entries, t, b) for t in tasks]
    return sum(d) / len(d)

# ── 变异算子 ────────────────────────────────────────────────────────
def mutate(cfg, rnd):
    d = asdict(cfg)
    if rnd.random() < 0.12:
        d["filter_zero"] = 1 - d["filter_zero"]
    else:
        p = rnd.choice(PARAMS)
        d[p] = round(max(0.0, d[p] * rnd.choice([0.5, 0.7, 0.85, 1.2, 1.5, 2.0])), 4)
        if rnd.random() < 0.2:
            d[p] = 0.0
    return Cfg(**d)

# ── 演化循环 ────────────────────────────────────────────────────────
def evolve(seed, gens=25, kids=3, gated=True, margin=0.01):
    rnd = random.Random(seed)
    entries, tasks = build_world(seed)
    train, held = tasks[:40], tasks[40:80]
    root = Cfg()
    root_tr, root_he = score(entries, train, root), score(entries, held, root)
    archive = [{"cfg": root, "tr": root_tr, "he": root_he, "parent": None, "gen": 0}]
    for g in range(1, gens + 1):
        for _ in range(kids):
            pool = sorted(archive, key=lambda x: -x["tr"])
            cand = rnd.choice(pool[:3]) if (rnd.random() < 0.7 and len(pool) >= 3) else rnd.choice(pool)
            child = mutate(cand["cfg"], rnd)
            ctr = score(entries, train, child)
            if gated:
                ok = (paired(entries, train, child, cand["cfg"]) > margin
                      and paired(entries, held, child, cand["cfg"]) > margin)
            else:
                ok = ctr > cand["tr"]            # 朴素：训练集有一点提升就采纳
            if ok:
                archive.append({"cfg": child, "tr": ctr,
                                "he": score(entries, held, child),
                                "parent": cand["cfg"], "gen": g})
    sysbest = max(archive, key=lambda x: x["tr"])      # 系统自己认为最好的（按训练集）
    recoverable = any(x["he"] >= root_he for x in archive)   # 回滚安全性
    return {"root_tr": root_tr, "root_he": root_he,
            "best_tr": sysbest["tr"], "best_he": sysbest["he"],
            "cfg": asdict(sysbest["cfg"]), "n": len(archive),
            "recoverable": recoverable}

if __name__ == "__main__":
    SEEDS = [1, 2, 3, 4, 5, 6, 7, 8]
    print("=" * 78)
    print("E1/E2  门控演化 vs 无门控演化（8 个随机种子，各 25 代 × 3 变异）")
    print("=" * 78)
    for label, gated in (("有门控(配对比较+留出集)", True), ("无门控(训练集提升即采纳)", False)):
        rows = [evolve(s, gated=gated) for s in SEEDS]
        d_he = [r["best_he"] - r["root_he"] for r in rows]
        d_tr = [r["best_tr"] - r["root_tr"] for r in rows]
        win = sum(1 for x in d_he if x > 0)
        print(f"\n【{label}】")
        print(f"  留出集提升: 均值 {statistics.mean(d_he):+.4f}  中位数 {statistics.median(d_he):+.4f}"
              f"  为正的种子 {win}/{len(SEEDS)}")
        print(f"  训练集提升: 均值 {statistics.mean(d_tr):+.4f}（系统自认为的进步）")
        print(f"  选出配置的留出集绝对分: {statistics.mean([r['best_he'] for r in rows]):.4f}"
              f"  （起点 {statistics.mean([r['root_he'] for r in rows]):.4f}）")

    print("\n" + "=" * 78)
    print("E1 细看：有门控时演化到底学到了什么（seed=1）")
    print("=" * 78)
    r = evolve(1, gated=True)
    print(f"  起点 v3 默认 : {asdict(Cfg())}")
    print(f"  演化后       : {r['cfg']}")
    print(f"  留出集       : {r['root_he']:.4f} → {r['best_he']:.4f}  ({r['best_he']-r['root_he']:+.4f})")
    print(f"  档案规模 {r['n']}，回滚安全（档案中存在不劣于起点的配置）: {r['recoverable']}")

    print("\n" + "=" * 78)
    print("E3  恶意/贪婪变异能否刷分？（注入「把重要度权重拉满」的作弊变异）")
    print("=" * 78)
    entries, tasks = build_world(1)
    train, held = tasks[:40], tasks[40:80]
    cheat = Cfg(w_imp=10.0, w_kw=0.0, w_content=0.0)   # 伪装成「更重视重要度」
    print(f"  作弊配置 w_imp=10 : 训练集 {score(entries,train,cheat):.4f}  留出集 {score(entries,held,cheat):.4f}"
          f"  （配对比较 vs 起点: {paired(entries,held,cheat,Cfg()):+.4f}）")
    cheat2 = Cfg(w_imp=100.0, w_kw=0.0, w_content=0.0, w_age=0.0, filter_zero=0)
    print(f"  极端 w_imp=100   : 训练集 {score(entries,train,cheat2):.4f}  留出集 {score(entries,held,cheat2):.4f}")
    print("  → 因 K=5 与评测协议在元层固定，堆权重无法凭空提高召回；作弊无法表达")
