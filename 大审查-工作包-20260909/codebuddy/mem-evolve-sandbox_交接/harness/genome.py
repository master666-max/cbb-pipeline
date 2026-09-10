"""法层基因与变异算子。

三层边界（与实验报告 §5.1 同构）：
  元层（人侧签名，冻结，系统不可达）：K、评测协议、任务集、效用权重 W0
  法层（可自主演化）：本文件的 GENE_SPACE
  行层（自由写入）：记忆条目、采纳日志、attic

能力式约束（报告 §2.5）：违反铁律的变异**不可表达**，而不是"表达了再检测"。
"""
from __future__ import annotations

import copy
import random

# 默认值 = bootstrap_v3.py 中的硬编码常量（_rank_entries / TUNABLES / cmd_engine）
DEFAULT = {
    "w_kw": 3.0,            # _rank_entries: kw_hit * 3
    "w_content": 1.0,       # _rank_entries: c_hit * 1
    "w_imp": 1.0,           # _rank_entries: + importance
    "w_age": 0.1,           # _rank_entries: - 0.1 * age_days
    "filter_zero": 0,       # BUG-006：零命中过滤开关（v3 默认关）
    "link_spread": 0.5,     # _rank_entries: [[links]] 一跳扩散 ×0.5
    "importance_source": "self",   # self=自称 / measured=实测采纳率（E32）
    "hot_budget": 200,      # TUNABLES["index_hot_budget"]
    "ttl_days": 90,         # TUNABLES["invalid_ttl_days"]：失效条目出仓（存储卫生）
    "max_age_days": 3650,   # 【新增·可演化】遗忘闸门：条目生存期上限（3650 ≈ 关闭）
    "merge_mode": "flat",   # flat=平铺 / hier=层次化归并（E28）
    "longterm_cut": 7,      # cmd_engine: importance>=7 → longterm
}

# kind, lo/choices, hi, step
GENE_SPACE = {
    "w_kw":              ("float", 0.0, 8.0, 0.5),
    "w_content":         ("float", 0.0, 4.0, 0.25),
    "w_imp":             ("float", 0.0, 3.0, 0.25),
    "w_age":             ("float", 0.0, 1.0, 0.05),
    "filter_zero":       ("int",   0,   1,   1),
    "link_spread":       ("float", 0.0, 1.0, 0.1),
    "importance_source": ("enum", ("self", "measured"), None, None),
    "hot_budget":        ("int",   20,  400, 20),
    "ttl_days":          ("int",   7,   365, 7),
    "max_age_days":      ("int",   30,  3650, 30),
    "merge_mode":        ("enum", ("flat", "hier"), None, None),
    "longterm_cut":      ("int",   1,   10,  1),
}

# 元层：绝不可被变异触碰（红线 1/13）
META = {"K": 5, "protocol": "recall@5+MRR+cost", "taskset": "world.seeded", "W0": "frozen"}


class LawViolation(Exception):
    """能力式边界抛出的异常：违反铁律的基因组根本构造不出来。"""


def clamp(g: dict) -> dict:
    out = {}
    for k, v in g.items():
        if k not in GENE_SPACE:
            raise LawViolation(f"未知基因 {k}（元层/法层边界越界）")
        kind, lo, hi, step = GENE_SPACE[k]
        if kind == "enum":
            if v not in lo:
                raise LawViolation(f"{k}={v} 不在允许取值 {lo}")
            out[k] = v
        elif kind == "int":
            iv = int(round(float(v)))
            out[k] = max(int(lo), min(int(hi), iv))
        else:
            fv = float(v)
            out[k] = max(float(lo), min(float(hi), fv))
    # 铁律 1 投影：遗忘必须是"移 attic 留痕"，不允许 0 天即时清空（等价删除语义）
    if out["ttl_days"] < 7:
        raise LawViolation("ttl_days<7：等价销毁式遗忘，违反铁律1（回退=移attic）")
    if out["hot_budget"] < 20:
        raise LawViolation("hot_budget<20：热度逐出过激，等价不可控遗忘")
    return out


def mutate(g: dict, rng: random.Random, n_genes: int = 1, genes=None) -> dict:
    """在能力式边界内变异；非法结果在构造期即被拒绝（不是事后检测）。

    genes 用于**隔离实验**：把变异限制在少数基因上，排除其他维度的收益把目标效应淹没
    （报告实验设计失败 #4 的同构教训：不隔离就看不出分离度）。
    """
    space = [k for k in (genes or GENE_SPACE) if k in GENE_SPACE] or list(GENE_SPACE)
    for _ in range(8):
        cand = copy.deepcopy(g)
        keys = rng.sample(space, k=min(n_genes, len(space)))
        for k in keys:
            kind, lo, hi, step = GENE_SPACE[k]
            if kind == "enum":
                cand[k] = rng.choice([c for c in lo if c != cand[k]] or list(lo))
            elif kind == "int":
                cand[k] = int(cand[k]) + rng.choice([-step, step])
            else:
                cand[k] = float(cand[k]) + rng.choice([-step, step])
        try:
            return clamp(cand)
        except LawViolation:
            continue
    return clamp(copy.deepcopy(g))


def random_genome(rng: random.Random) -> dict:
    """对照组 G5（随机搜索）用：在基因空间内均匀采样。"""
    g = {}
    for k, (kind, lo, hi, step) in GENE_SPACE.items():
        if kind == "enum":
            g[k] = rng.choice(list(lo))
        elif kind == "int":
            g[k] = rng.randrange(int(lo), int(hi) + 1, int(step))
        else:
            g[k] = round(rng.uniform(float(lo), float(hi)), 3)
    return clamp(g)


def diff(a: dict, b: dict) -> list:
    return sorted(k for k in DEFAULT if a.get(k) != b.get(k))


def fingerprint(g: dict) -> str:
    return "|".join(f"{k}={g[k]}" for k in sorted(GENE_SPACE))
