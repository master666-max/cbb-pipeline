"""自演化主循环（实验报告 §5.2 的可运行形态）。

配置（对照臂）：
  none             G1 无门控：每代取训练集最优直接晋升
  strict-admit     G2 单级严格准入：每步必须变好（E7 反例，预期卡在局部最优）
  two-tier         G3 宽松准入 + 双门晋升 + Pareto 档案
  two-tier+anchor  G4 = G3 + 锚定审计（漂移场景专用）
  random           G5 同等评估预算的随机搜索（判别"演化"是否优于"搜索"）
  static           G0 静态记忆库：不演化（基线）
"""
from __future__ import annotations

import random
import time

import metrics
from gate import (MARGIN, Archive, AnchorSet, StallMonitor,
                  admit, cheap_filter, promote)
from genome import DEFAULT, clamp, fingerprint, mutate, random_genome
from kernel import Library
from world import NOW

CONFIGS = ("static", "none", "strict-admit", "two-tier", "two-tier+anchor",
           "two-tier+reanchor", "random")

# 锚定集与锚定审计必须共用同一套口径：同一批查询、同一份**规范化**库状态、同样的地形项处理。
ANCHOR_N_PROBE = 20


def build_anchor_samples(world, rng, n=24, k=5, min_gap=0.02, n_probe=None):
    """锚定集：系统启用**之前**用初心权重 W0 标注，永不更新、永不衰减（E14c）。

    样本形态必须是**成对比较** (g_a, g_b, "W0 下谁更好")，不能是绝对阈值判定
    （如"效用是否 ≥ 0"）。实测后者在漂移前后几乎恒为 True → agreement 恒为 1.0
    → 永远检不出漂移，H7 直接测不出来。成对比较对权重旋转敏感得多。
    """
    n_probe = n_probe or ANCHOR_N_PROBE

    def score_W0(g):
        lib2 = Library(world.entries, NOW)
        lib2.apply(g)
        _, per_task = metrics.evaluate(world, lib2, world.queries["audit"][:n_probe], g,
                                       k=k, true=True, shape_bonus=0.0)
        return sum(per_task) / len(per_task)

    # 只保留 W0 下分差 > min_gap 的对：分差接近 0 的对，其标签本身就是噪声，
    # 会被后续任何微小状态变化翻转 —— 实测这是 α=0 下 11/12 误报的主因。
    samples, tries, gap = [], 0, min_gap
    while len(samples) < n and tries < n * 40:
        tries += 1
        ga, gb = random_genome(rng), random_genome(rng)
        ua, ub = score_W0(ga), score_W0(gb)
        if abs(ua - ub) >= gap:
            samples.append((ga, gb, 1 if ua > ub else 0))
        if tries == n * 20 and len(samples) < n:
            gap = gap / 2.0          # 实在凑不够就放宽，但记录实际间隔
    return samples


def run_once(world, cfg="two-tier", seed=1, gens=60, k=5, fanout=3, n_genes=1,
             use_cheap=True, rotate=False, archive_mode="pareto", genes=None,
             use_holdout_gate=True, use_stall=True, reanchor_delay=5, gate_tasks=None):
    rng = random.Random(seed * 7919 + 13)
    lib = Library(world.entries, NOW)
    champ = clamp(DEFAULT)
    archive = Archive(mode=("single" if cfg == "strict-admit" else archive_mode), cap=40)
    stall = StallMonitor()
    anchor = None
    if cfg in ("two-tier+anchor", "two-tier+reanchor"):
        anchor = AnchorSet(build_anchor_samples(world, random.Random(seed)))

    frozen = False
    reanchor_at = None      # 冻结后第几代执行重锚
    reanchors = 0
    log = []
    peak_audit_u = float("-inf")
    t_start = time.perf_counter()

    def deploy(g, queries):
        """部署冠军：唯一会写入采纳日志的动作（行层"更新"的数据来源）。"""
        lib.apply(g)
        perf, _ = metrics.evaluate(world, lib, queries, g, k=k, feedback=True)
        return perf

    def uW1(g):
        """旧目标(W1)下的效用：用于度量"系统保有什么"，而非"系统当前输出什么"（E16）。"""
        lib2 = Library(world.entries, NOW)
        lib2.apply(g)
        p, _ = metrics.evaluate(world, lib2, world.queries["audit"][:20], g, k=k, true=True)
        return world.utility(p, 0, g, true=True)

    W1_default = uW1(clamp(DEFAULT))
    W1_at_switch = None

    # 系统内部看到的是**当前（可能被漂移污染）的尺子**；真实效用只在报告时用初心权重 W0 计算。
    # 二者不分离的话，漂移地形下系统压根不会走偏，E14 永远测不出来。
    champ_train = deploy(champ, world.queries["train"])
    champ_train_u = world.utility(champ_train, 0, champ, true=False)
    snap0 = lib.snapshot()
    champ_hold, champ_hold_scores = metrics.evaluate(
        world, lib, world.queries["holdout"], champ, k=k, true=False)
    lib.restore(snap0)
    start_audit, _ = metrics.evaluate(world, lib, world.queries["audit"], champ, k=k)
    start_u = world.utility(start_audit, 0, champ)
    evals = 2

    for gen in range(1, gens + 1):
        if (world.terrain == "switch" and world.switch_gen is not None
                and gen == world.switch_gen):
            W1_at_switch = uW1(champ)     # 切换时刻的旧目标能力：E16 的参照点
        if rotate:
            world.rotate_holdout(gen)
        gen_t0 = time.perf_counter()
        adopted = False
        rejected = 0
        proposed = None
        snap = lib.snapshot()

        if cfg == "static":
            log.append({"gen": gen, "adopted": False, "u_train": round(champ_train_u, 6),
                        "u_hold": round(world.utility(champ_hold, gen, champ), 6),
                        "front": 0, "genome": fingerprint(champ)})
            continue

        if cfg == "random":
            cands = [random_genome(rng) for _ in range(fanout)]
        elif cfg.startswith("two-tier"):
            # 开放式档案的关键：变异可以**从档案中任意成员**出发，而不只从冠军出发。
            # 否则"先变差后变好"的中间态永远无法被扩展，E7 的跨越低谷不会发生。
            cands = []
            for _ in range(fanout):
                parent = archive.sample_parent(rng) or champ
                if rng.random() < 0.5:
                    parent = champ          # 一半从冠军局部搜索，一半从档案开放式探索
                cands.append(mutate(parent, rng, n_genes=n_genes, genes=genes))
        else:
            cands = [mutate(champ, rng, n_genes=n_genes, genes=genes) for _ in range(fanout)]

        best_train = None
        for c in cands:
            if use_cheap and cheap_filter(c) == "reject":
                rejected += 1
                continue
            lib.restore(snap)
            lib.apply(c)
            tr, _ = metrics.evaluate(world, lib, world.queries["train"], c, k=k, true=False)
            evals += 1
            u_tr = world.utility(tr, gen, c, true=False)
            if cfg == "none":
                if best_train is None or u_tr > best_train[1]:
                    best_train = (c, u_tr, tr)
            elif cfg == "strict-admit":
                mg = stall.margin if use_stall else MARGIN
                if u_tr > champ_train_u + max(0.0, mg):
                    if best_train is None or u_tr > best_train[1]:
                        best_train = (c, u_tr, tr)
            else:  # two-tier 家族：宽松准入
                if admit(u_tr - champ_train_u):
                    archive.add(c, u_tr, tr["cost_norm"], gen, rng)

        if cfg in ("none", "strict-admit"):
            proposed = best_train[0] if best_train else None
            if proposed is not None:
                adopted = True
                champ = proposed
                champ_train_u = best_train[1]
        elif cfg.startswith("two-tier"):
            pick = archive.best(rng)
            if pick is not None and not frozen:
                lib.restore(snap)
                lib.apply(pick["genome"])
                ho, ho_scores = metrics.evaluate(
                    world, lib, world.queries["holdout"], pick["genome"], k=k, true=False)
                evals += 1
                gate_train = pick["u"] > champ_train_u            # 门 1：训练集
                if use_holdout_gate:
                    # 注意力预算决定**门控判决能看多少个任务**（E17：n=10 时假阳 0.42）。
                    # 预算不足 → 判决不可靠 → 采纳噪声 → 低预算下演化反而有害（E64）。
                    n_t = gate_tasks or len(ho_scores)
                    gate_hold = promote(ho_scores[:n_t], champ_hold_scores[:n_t], rng,
                                        margin=(stall.margin if use_stall else MARGIN))
                    passed = gate_hold["passed"]
                else:
                    passed = True                                  # 消融臂：去掉留出集门
                if gate_train and passed:
                    champ = pick["genome"]
                    champ_train_u = pick["u"]
                    champ_hold_scores = ho_scores
                    champ_hold = ho
                    adopted = True
            if use_stall:
                stall.step(adopted)

        # 锚定审计（每 5 代：检出延迟本身就是指标，太疏会错过冻结窗口）
        anchor_flag = None
        if anchor is not None and gen % 5 == 0:
            def scorer(g):
                """用**当前（可能被漂移污染的）尺子**给基因组打分——这正是被审计的对象。

                必须在与标注时**完全相同的规范化库状态**上打分。若改用演化中的活库，
                热层/attic/采纳日志的差异会让成对序翻转，检测器测到的是"状态漂移"
                而非"权重漂移"：实测 α=0 与 α=0.10 的分布完全重叠，分离度为零。
                """
                lib2 = Library(world.entries, NOW)
                lib2.apply(g)
                _, per_task = metrics.evaluate(
                    world, lib2, world.queries["audit"][:ANCHOR_N_PROBE], g,
                    k=k, true=False, shape_bonus=0.0)
                return sum(per_task) / len(per_task)
            drifted, agree = anchor.drifted(scorer)
            evals += 2 * len(anchor.samples)
            anchor_flag = {"agreement": round(agree, 4), "drifted": drifted}
            if drifted:
                frozen = True      # 检出漂移 → 冻结自动演化（红线 18）
                if cfg == "two-tier+reanchor" and reanchor_at is None:
                    reanchor_at = gen + reanchor_delay

        # 重锚（E26/E27：真正有效的是重锚，不是简单恢复或回滚）
        # 人重新校准自己的尺子：权重拉回 W0 + 残差噪声，并**重新采集**判断样本，然后解冻。
        if reanchor_at is not None and gen >= reanchor_at:
            world.rater_w = {kk: world.W0[kk] * (1.0 + rng.gauss(0.0, 0.05))
                             for kk in world.W0}
            anchor = AnchorSet(build_anchor_samples(world, random.Random(seed * 31 + gen)))
            evals += 2 * len(anchor.samples)      # 重新采集人类判断 = 注意力成本
            reanchors += 1
            reanchor_at = None
            frozen = False
            anchor_flag = {"agreement": 1.0, "drifted": False, "reanchored": True}

        # 部署冠军，累积采纳日志（行层"更新"）
        lib.restore(snap)
        champ_train = deploy(champ, world.queries["train"])
        snap0 = lib.snapshot()

        if world.terrain == "drift":
            world.drift_step({"recall": champ_train["recall@5"],
                              "mrr": champ_train["MRR"],
                              "cost": champ_train["cost_norm"]}, gen=gen)

        audit_perf = None
        if gen % 5 == 0 or gen == gens:      # 审计集每 5 代测一次，才能描出"先变好再被带偏"的回撤
            snap2 = lib.snapshot()
            audit_perf, _ = metrics.evaluate(world, lib, world.queries["audit"], champ, k=k,
                                             true=True)
            lib.restore(snap2)
            audit_u = world.utility(audit_perf, gen, champ, true=True)
            peak_audit_u = max(peak_audit_u, audit_u)

        log.append({
            "gen": gen,
            "adopted": adopted,
            "rejected_by_cheap": rejected,
            "u_train": round(champ_train_u, 6),
            "u_hold": round(world.utility(champ_hold, gen, champ), 6),
            "u_audit": round(world.utility(audit_perf, gen, champ), 6) if audit_perf else None,
            "u_perceived": round(world.utility(champ_hold, gen, champ, true=False), 6),
            "front": archive.front_size(),
            "pool": archive.pool_size(),
            "frozen": frozen,
            "anchor": anchor_flag,
            "stall_margin": round(stall.margin, 5),
            "genome": fingerprint(champ),
            "bytes": metrics.storage_bytes(lib),
            "sec": round(time.perf_counter() - gen_t0, 5),
        })

    # 终局：冻结审计集上的真实效用（对外报告以此为准，红线 11）
    snapf = lib.snapshot()
    final_audit, _ = metrics.evaluate(world, lib, world.queries["audit"], champ, k=k)
    lib.restore(snapf)
    q_top, _ = metrics.top_quality(lib, champ, k=10)
    q_top_base, _ = metrics.top_quality(lib, clamp(DEFAULT), k=10)

    # E16 判据：切换后**旧目标(W1)**的能力保留度。
    #   champion_W1   = 当前冠军在旧目标上的效用（单一最优：适应了新目标 → 应显著下降）
    #   archive_best_W1 = 档案中任一成员在旧目标上的最好值（Pareto：应保留住）
    champion_W1 = archive_best_W1 = None
    if world.terrain == "switch":
        champion_W1 = uW1(champ)
        # 必须扫**全部**档案成员（front + pool），只取前 20 个会漏掉早期保留的旧目标专家
        members = {fingerprint(r["genome"]): r["genome"]
                   for r in (list(archive.pool) + list(archive.front))}
        archive_best_W1 = max([champion_W1] + [uW1(g) for g in members.values()])

    return {
        "cfg": cfg, "seed": seed, "terrain": world.terrain, "gens": gens,
        "start_audit_u": round(start_u, 6),
        "final_audit_u": round(world.utility(final_audit, gens, champ), 6),
        "delta": round(world.utility(final_audit, gens, champ) - start_u, 6),
        "final_recall@5": round(final_audit["recall@5"], 4),
        "final_MRR": round(final_audit["MRR"], 4),
        "final_cost_norm": round(final_audit["cost_norm"], 4),
        "top10_quality_evolved": round(q_top, 4),
        "top10_quality_selfreported": round(q_top_base, 4),
        # E7 判据：是否逃出局部最优（到达 (w_kw>=4 且 filter_zero==1) 的全局最优点）
        "escaped_local_optimum": bool(champ["filter_zero"] == 1 and champ["w_kw"] >= 4.0),
        "final_w_kw": champ["w_kw"], "final_filter_zero": champ["filter_zero"],
        "final_importance_source": champ["importance_source"],
        "final_hot_budget": champ["hot_budget"],
        "final_max_age_days": champ["max_age_days"],
        "final_merge_mode": champ["merge_mode"],
        "champion_W1": None if champion_W1 is None else round(champion_W1, 6),
        "archive_best_W1": None if archive_best_W1 is None else round(archive_best_W1, 6),
        "W1_default": round(W1_default, 6),
        "W1_at_switch": None if W1_at_switch is None else round(W1_at_switch, 6),
        # switch 地形下主指标 delta 是**跨目标口径**（终点 W2 / 起点 W1），不可直接读。
        # delta_W1 是同口径版本：终点与起点都在旧目标 W1 下衡量。
        "delta_W1": (round(champion_W1 - W1_default, 6)
                     if champion_W1 is not None else None),
        # E14 主观测量：自报 − 真实（自报 +1.50 而真实 −0.83 的那一类缺口）
        "final_self_report_gap": round(
            world.utility(final_audit, gens, champ, true=False)
            - world.utility(final_audit, gens, champ, true=True), 6),
        "final_perceived_u": round(world.utility(final_audit, gens, champ, true=False), 6),
        # 漂移的核心观测量：先变好、再被带偏 → 用"峰值后回撤"而非绝对符号来判定
        "peak_audit_u": round(peak_audit_u, 6),
        "drift_drawdown": round(peak_audit_u - world.utility(final_audit, gens, champ), 6),
        "drift_start": getattr(world, "drift_start", None),
        "frozen_by_anchor": bool(frozen),
        "reanchors": reanchors,
        "anchor_agreement_min": round(min(
            (r["anchor"]["agreement"] for r in log if r.get("anchor")), default=1.0), 4),
        "evals": evals,
        "wall_seconds": round(time.perf_counter() - t_start, 4),
        "final_genome": fingerprint(champ),
        "adoptions": sum(1 for r in log if r.get("adopted")),
        "stall_gens": sum(1 for r in log if not r.get("adopted")),
        "log": log,
    }
