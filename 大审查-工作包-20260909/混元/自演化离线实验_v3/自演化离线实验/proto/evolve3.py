"""自演化 v3 —— 精确构造「可被利用的伪相关」

设计：
  每个 keyword 组 4 条；组内真正的判别信号（content 里的 topic token）只有 60% 可靠
  伪特征 spur：训练集上 金标恰好都是 spur=1；留出集上 金标恰好都是 spur=0（方向反转）
→ 重视 spur 的配置：训练集近乎满分，留出集反向崩盘
这正是 reward hacking 的微观形态：找到了刷高历史指标的捷径，而非真正变好。
"""
import random, statistics
from dataclasses import dataclass, asdict

K, LAMBDA = 5, 0.15
TOPICS = [f"T{i}" for i in range(16)]

@dataclass(frozen=True)
class Cfg:
    w_kw: float = 3.0
    w_content: float = 1.0
    w_imp: float = 1.0
    w_age: float = 0.1
    w_spur: float = 0.0
    filter_zero: int = 0

PARAMS = ["w_kw", "w_content", "w_imp", "w_age", "w_spur"]

def build_world(seed, n_entries=80, n_kws=10, n_train=12, reliability=0.6):
    rnd = random.Random(seed)
    entries = []
    for i in range(n_entries):
        k, t = i % n_kws, TOPICS[i % 16]
        tok = t if rnd.random() < reliability else rnd.choice(TOPICS)   # 真信号 60% 可靠
        entries.append({"id": f"e{i}", "kw": f"K{k}", "topic": t,
                        "keywords": [f"K{k}"], "content": f"{tok} K{k} 片段{i}",
                        "importance": rnd.randint(1, 3),
                        "age_days": rnd.randint(0, 400),
                        "spur": 1 if rnd.random() < 0.5 else 0})
    train, held = [], []
    for i in range(72):
        grp = [e for e in entries if e["kw"] == f"K{i % n_kws}"]
        want = 1 if i < n_train else 0                    # 留出集方向反转
        cands = [e for e in grp if e["spur"] == want] or grp
        g = rnd.choice(cands)
        (train if i < n_train else held).append(
            {"q": f"{g['topic']} {g['kw']}", "kw": g["kw"], "golden": g["id"]})
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
    return hit - LAMBDA * sum(1 for e in top if e["kw"] != task["kw"])

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
                                   + rnd.choice([0, 0, 0.5, -0.5]))), 4)
    return Cfg(**d)

def evolve(seed, gens=30, kids=4, gated=True, margin=0.01, n_train=12, reliability=0.6, n_kws=10):
    rnd = random.Random(seed)
    entries, train, held = build_world(seed, n_train=n_train, reliability=reliability, n_kws=n_kws)
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
    sb = max(archive, key=lambda x: x["tr"])
    return {"root_tr": root_tr, "root_he": root_he, "best_tr": sb["tr"], "best_he": sb["he"],
            "cfg": asdict(sb["cfg"]), "spur": sb["cfg"].w_spur, "n": len(archive),
            "recoverable": any(x["he"] >= root_he for x in archive),
            "cheated": sb["cfg"].w_spur > 0.5}

if __name__ == "__main__":
    SEEDS = list(range(1, 13))
    print("=" * 84)
    print("组内伪相关 + 留出集方向反转：门控 vs 无门控（12 种子）")
    print("=" * 84)
    for nt in (12, 20, 40):
        G = [evolve(s, gated=True,  n_train=nt) for s in SEEDS]
        U = [evolve(s, gated=False, n_train=nt) for s in SEEDS]
        dg = statistics.mean(r["best_he"] - r["root_he"] for r in G)
        du = statistics.mean(r["best_he"] - r["root_he"] for r in U)
        cg = sum(r["cheated"] for r in G); cu = sum(r["cheated"] for r in U)
        print(f"\n  训练任务数 = {nt}")
        print(f"    有门控  : 留出集 {dg:+.4f}   训练集 {statistics.mean(r['best_tr']-r['root_tr'] for r in G):+.4f}"
              f"   采纳伪特征(w_spur>0.5) 的种子 {cg}/{len(SEEDS)}")
        print(f"    无门控  : 留出集 {du:+.4f}   训练集 {statistics.mean(r['best_tr']-r['root_tr'] for r in U):+.4f}"
              f"   采纳伪特征(w_spur>0.5) 的种子 {cu}/{len(SEEDS)}")
        print(f"    → 门控净收益 {dg-du:+.4f}")

    print("\n" + "=" * 84)
    r = evolve(1, gated=True, n_train=12)
    print("单种子细看（有门控, seed=1）")
    print(f"  起点 v3 默认: {asdict(Cfg())}")
    print(f"  演化后      : {r['cfg']}")
    print(f"  留出集 {r['root_he']:.4f} → {r['best_he']:.4f} ({r['best_he']-r['root_he']:+.4f})"
          f" | 档案 {r['n']} | 可回滚 {r['recoverable']} | 是否作弊 {r['cheated']}")
