"""指标采集：检索准确率 / 演化效率 / 资源开销 / 记忆一致性 / 遗忘与重组。

指标分三类，采集时严格分离（避免"用被测系统的自报值衡量被测系统"，报告 E8/E32）：
  - 实测类：recall@5 / MRR / cost_norm / 存储字节 / 耗时
  - 自报类：训练集效用、感知效用（留作对照，不单独作为结论）
  - 审计类：冻结审计集效用（对外报告以此为准）
"""
from __future__ import annotations

import time

from kernel import Library, topk


def evaluate(world, lib: Library, queries, g, k=5, feedback=False, gen=0, true=True,
             shape_bonus=None):
    """在一个查询集上评估一个基因组；返回 (perf, per_task_scores)。

    shape_bonus：地形塑形项是**基因组级**的（如欺骗地形的低谷/奖励），必须摊到每个任务分上，
    否则留出集配对比较看不见它 —— 实测会导致"全局最优候选因逐任务差≈0 而永远过不了
    bootstrap 门"（E7 直接复现失败）。
    """
    n = max(1, len(queries))
    hits = rr = cost = 0.0
    per_task = []
    w = world.objective(gen, true=true)
    sb = world.shape(g) if shape_bonus is None else shape_bonus
    # 扫描面在一次 evaluate 内不变（apply 在外层做），没必要每个查询重算一次
    scan_frac = len(lib.scannable()) / max(1, len(lib.by_id))
    for q in queries:
        ranked = topk(lib, q["query"], g, k)
        exp = set(q["expected"])
        found = [i + 1 for i, fid in enumerate(ranked) if fid in exp]
        hit = 1.0 if found else 0.0
        rrv = 1.0 / found[0] if found else 0.0
        c = scan_frac
        if feedback:
            lib.record_feedback(ranked, exp)
        hits += hit
        rr += rrv
        cost += c
        per_task.append(w["recall"] * hit + w["mrr"] * rrv + w["cost"] * c + sb)  # cost 权重带符号
    return {"recall@5": hits / n, "MRR": rr / n, "cost_norm": cost / n}, per_task


def top_quality(lib: Library, g, k=10):
    """E32 复现：按 importance 取 top-k，看这些条目的**真实质量**均值。"""
    ids = list(lib.scannable())
    ids.sort(key=lambda i: -lib.importance_of(i, g))
    top = ids[:k]
    if not top:
        return 0.0, []
    return sum(lib.true_quality.get(i, 0.0) for i in top) / len(top), top


def retention(lib: Library, g_old, g_new, queries_old, world, k=5):
    """E16 复现：目标/策略切换后，旧目标能力在档案中的保留度。用旧目标查询集测新基因组。"""
    perf, _ = evaluate(world, lib, queries_old, g_new, k=k)
    perf_old, _ = evaluate(world, lib, queries_old, g_old, k=k)
    return {"old_capability_after": perf["recall@5"], "old_capability_before": perf_old["recall@5"]}


def resource(lib: Library, fn):
    t0 = time.perf_counter()
    out = fn()
    return out, time.perf_counter() - t0


def storage_bytes(lib: Library):
    return lib.bytes()


def summarize(values):
    n = len(values)
    if not n:
        return {"n": 0, "mean": 0.0, "std": 0.0}
    m = sum(values) / n
    var = sum((v - m) ** 2 for v in values) / n
    return {"n": n, "mean": round(m, 6), "std": round(var ** 0.5, 6)}


def paired_delta(a, b):
    """同种子配对差：a - b。"""
    return [x - y for x, y in zip(a, b)]


def max_gens(budget, init_cost=40, per_gen=1, audit_every=10, audit_cost=5):
    """注意力预算 → 可跑代数（报告 E64：预算决定自主性上限）。"""
    if budget <= init_cost:
        return 0
    per = per_gen + audit_cost / audit_every
    return int((budget - init_cost) / per)
