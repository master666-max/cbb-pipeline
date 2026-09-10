"""自演化内核原型 v2 —— 修正 E2 的实验设计（上一版世界太干净，过拟合不可能发生）

世界 B 故意埋入【伪相关】：
  entries 有一个与查询无关的特征 spur(0/1)
  训练集里 金标条目 80% 恰好 spur=1（历史偶然 / 采样偏差）
  留出集里 spur 与金标无关
→ 任何"重视 spur"的配置都会在训练集上大放异彩、在留出集上崩盘
这正是 reward hacking 的微观形态：系统找到了一个能刷高指标的捷径，而非真正变好。
"""
import random, statistics
from dataclasses import dataclass, asdict, replace

K = 5
LAMBDA = 0.15

@dataclass(frozen=True)
class Cfg:
    w_kw: float = 3.0
    w_content: float = 1.0
    w_imp: float = 1.0
    w_age: float = 0.1
    w_spur: float = 0.0        # 伪相关特征权重（起点为 0，演化可自行发现它）
    filter_zero: int = 0

PARAMS = ["w_kw", "w_content", "w_imp", "w_age", "w_spur"]

def build_world(seed, spurious=True, n_entries=80, n_topics=16, n_kws=20, n_train=40, spur_bias=0.8):
    rnd = random.Random(seed)
    entries = []
    for i in range(n_entries):
        t, k = i % n_topics, i % n_kws
        entries.append({"id": f"e{i}", "topic": f"T{t}", "kw": f"K{k}",
                        "keywords": [f"K{k}"],
                        "content": f"T{t} K{k} 内容片段 {i}",
                        "importance": rnd.randint(1, 10),
                        "age_days": rnd.randint(0, 400),
                        "spur": 1 if rnd.random() < 0.25 else 0})
    spur1 = [e for e in entries if e["spur"] == 1]
    allidx = list(range(n_entries)); rnd.shuffle(allidx)
    train, held = [], []
    for i in allidx[:n_train]:
        g = rnd.choice(spur1) if (spurious and rnd.random() < spur_bias) else entries[i]
        train.append({"q": f"{g['topic']} {g['kw']}", "kw": g["kw"], "golden": g["id"]})
    for i in allidx[n_train:80]:
        g = entries[i]                      # 留出集：spur 与金标无关
        held.append({"q": f"{g['topic']} {g['kw']}", "kw": g["kw"], "golden": g["id"]})
    return entries, train, held

def retrieve(entries, task, cfg):
    qw = task["q"].split(); out = []
    for e in entries:
        kw_hit = sum(1 for w in qw if w in " ".join(e["keywords"]))
        c_hit = sum(1 for w in qw if w in e["content"])
        if cfg.filter_zero and kw_hit == 0 and c_hit == 0:
            continue
        s = (cfg.w_kw * kw_hit + cfg.w_content * c_hit + cfg.w_imp * e["importance"]
             - cfg.w_age * (e["age_days"] / 100.0) + cfg.w_spur * e["spur"])
        out.append((s, e))
    out.sort(key=lambda x: -x[0])
    return [e for _, e in out[:K]]

def utility(entries, task, cfg):
    top = retrieve(entries, task, cfg)
    hit = 1.0 if task["golden"] in [e["id"] for e in top] else 0.0
    n_irrel = sum(1 for e in top if e["kw"] != task["kw"])
    return hit - LAMBDA * n_irrel

def score(entries, tasks, cfg):
    return sum(utility(entries, t, cfg) for t in tasks) / len(tasks)

def paired(entries, tasks, a, b):
    return sum(utility(entries, t, a) - utility(entries, t, b) for t in tasks) / len(tasks)

def mutate(cfg, rnd):
    d = asdict(cfg)
    if rnd.random() < 0.12:
        d["filter_zero"] = 1 - d["filter_zero"]
    else:
        p = rnd.choice(PARAMS)
        d[p] = round(max(-5.0, min(20.0, d[p] * rnd.choice([0.5, 0.7, 0.85, 1.2, 1.5, 2.0])
                                   + rnd.choice([0, 0, 0, 0.3, -0.3]))), 4)
    return Cfg(**d)

def evolve(seed, gens=25, kids=3, gated=True, margin=0.01, spurious=True, n_train=40):
    rnd = random.Random(seed)
    entries, train, held = build_world(seed, spurious=spurious, n_train=n_train, spur_bias=0.95)
    root = Cfg()
    root_tr, root_he = score(entries, train, root), score(entries, held, root)
    archive = [{"cfg": root, "tr": root_tr, "he": root_he, "gen": 0}]
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
                ok = ctr > cand["tr"]
            if ok:
                archive.append({"cfg": child, "tr": ctr, "he": score(entries, held, child), "gen": g})
    sysbest = max(archive, key=lambda x: x["tr"])
    return {"root_tr": root_tr, "root_he": root_he, "best_tr": sysbest["tr"],
            "best_he": sysbest["he"], "cfg": asdict(sysbest["cfg"]),
            "spur": sysbest["cfg"].w_spur, "n": len(archive),
            "recoverable": any(x["he"] >= root_he for x in archive)}

if __name__ == "__main__":
    SEEDS = list(range(1, 11))
    print("=" * 80)
    print("世界 B（含伪相关 spur）：门控 vs 无门控 —— 10 个种子")
    print("=" * 80)
    res = {}
    for label, gated in (("有门控", True), ("无门控", False)):
        rows = [evolve(s, gated=gated, spurious=True) for s in SEEDS]
        res[label] = rows
        d_he = [r["best_he"] - r["root_he"] for r in rows]
        d_tr = [r["best_tr"] - r["root_tr"] for r in rows]
        print(f"\n【{label}】")
        print(f"  系统自认为的进步(训练集) : {statistics.mean(d_tr):+.4f}")
        print(f"  真实进步(留出集)         : {statistics.mean(d_he):+.4f}"
              f"   为正的种子 {sum(1 for x in d_he if x>0)}/{len(SEEDS)}")
        print(f"  留出集绝对分             : {statistics.mean([r['root_he'] for r in rows]):.4f}"
              f" → {statistics.mean([r['best_he'] for r in rows]):.4f}")
        print(f"  选出的伪相关权重 w_spur  : 均值 {statistics.mean([r['spur'] for r in rows]):+.3f}"
              f"  最大 {max(r['spur'] for r in rows):+.3f}")

    gt = statistics.mean([r["best_he"] for r in res["有门控"]])
    ut = statistics.mean([r["best_he"] for r in res["无门控"]])
    print(f"\n  → 门控带来的留出集收益差: {gt-ut:+.4f}"
          f"（无门控系统被伪相关带偏的程度）")

    print("\n" + "=" * 80)
    print("对照：干净世界（无伪相关）下门控是否拖累演化速度")
    print("=" * 80)
    for label, gated in (("有门控", True), ("无门控", False)):
        rows = [evolve(s, gated=gated, spurious=False) for s in SEEDS]
        d = [r["best_he"] - r["root_he"] for r in rows]
        print(f"  {label}: 留出集提升 {statistics.mean(d):+.4f}  为正的种子 {sum(1 for x in d if x>0)}/{len(SEEDS)}")

    print("\n" + "=" * 80)
    print("回滚安全性 + 单种子细看（世界 B，有门控，seed=1）")
    print("=" * 80)
    r = evolve(1, gated=True, spurious=True)
    print(f"  起点 v3 默认: {asdict(Cfg())}")
    print(f"  演化后      : {r['cfg']}")
    print(f"  留出集 {r['root_he']:.4f} → {r['best_he']:.4f} ({r['best_he']-r['root_he']:+.4f})"
          f" | 档案 {r['n']} 项 | 可回滚 {r['recoverable']}")
