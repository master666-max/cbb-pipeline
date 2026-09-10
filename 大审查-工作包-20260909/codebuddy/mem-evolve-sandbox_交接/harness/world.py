"""合成记忆世界：条目生成、查询负载、地形、留出集轮换、评判者漂移。

为什么用合成世界而不是真实记忆库（实验报告第四部分「实验设计失败」教训 #1/#3）：
  - 真实库里"过拟合是否发生"取决于伪特征是否存在，不可控 → 无法复现；
  - 真实库没有金标 → 无法计算 recall@5 / MRR；
  - 地形的"低谷"必须是**已知**的，否则测不出门控的跨越能力。
所以：合成世界负责**可控地形的构造**，被测的检索/存储/遗忘/重组逻辑全部来自真实源码语义。
"""
from __future__ import annotations

import json
import random
import time
from pathlib import Path

TERRAINS = ("clean", "pseudo", "deceptive", "switch", "drift")

NOW = time.mktime(time.strptime("2026-09-08", "%Y-%m-%d"))  # 时钟注入（红线 27）


def _tok(prefix, i):
    return f"{prefix}{i:03d}"


class World:
    """一个可控地形 + 可复现的记忆世界。"""

    def __init__(self, seed=1, terrain="clean", n_groups=10, per_group=30,
                 n_train=40, n_holdout=40, n_audit=40, pool=3,
                 noise_p=0.0, noise_kind="none"):
        if terrain not in TERRAINS:
            raise ValueError(f"未知地形 {terrain}，可选 {TERRAINS}")
        self.seed = seed
        self.terrain = terrain
        # 注意：不能用 hash(terrain)——Python 字符串哈希默认带进程级随机盐，会破坏可复现性
        self.rng = random.Random(seed * 1000 + (sum(ord(c) for c in terrain) % 997))
        self.switch_gen = None
        # 权重取**带符号**：cost 为负（成本是惩罚项）。这样"漂移"可以表现为权重变号——
        # 评判者从"嫌贵"变成"喜欢臃肿"，这才是 E14 里"系统输出塑造评判它的人"的破坏形态。
        self.rater_w = {"recall": 0.50, "mrr": 0.30, "cost": -0.20}
        self.W0 = dict(self.rater_w)          # 冻结初心权重（衡量真实效用）
        self._W0_scale = sum(abs(v) for v in self.W0.values()) or 1.0
        self.drift_alpha = 0.15
        # 漂移从第几代开始注入。必须晚于"检索 headroom 被消耗完"的时点：
        # 否则系统一边被带偏一边仍在吃 headroom，真实效用仍在上升，E14 的伤害测不出来。
        self.drift_start = 15

        self.entries = self._gen_entries(n_groups, per_group)
        self.queries = self._gen_queries(n_train, n_holdout, n_audit, pool)
        self.noise_p, self.noise_kind = noise_p, noise_kind
        self._apply_label_noise(noise_p, noise_kind)
        self.holdout_pool = list(range(n_train))  # 留出集轮换池（示意：下挂于查询索引）

    # ── 条目 ────────────────────────────────────────────────
    def _gen_entries(self, n_groups, per_group):
        rng, out = self.rng, []
        gid = 0
        for g in range(n_groups):
            gtoks = [_tok("g", g), _tok("g", g) + "b"]
            for j in range(per_group):
                eid = f"e{gid:04d}"
                true_q = rng.random()
                kws = list(gtoks) + ([_tok("n", rng.randrange(50))] if rng.random() < 0.4 else [])
                # 伪特征必须**独占一个打分通道**才可被独立利用（否则与真实信号耦合，
                # 基因组无论怎么调都是同向的，实验测不出"过拟合"）：
                #   pseudo 地形：正文只放填充词 + xpf，关键词只放组标记
                #   → 关键词通道=真实信号，正文通道=伪特征，两者可分离
                has_xpf = self.terrain == "pseudo" and rng.random() < 0.5
                if self.terrain == "pseudo":
                    content = " ".join([_tok("f", rng.randrange(200)) for _ in range(6)]
                                       + (["xpf"] if has_xpf else []))
                elif self.terrain == "deceptive":
                    # 关键词通道做成**检索中立**（关键词只放噪声），使 w_kw 只能通过地形塑形项
                    # 影响效用 —— 否则"提权重带来的检索增益"会掩盖低谷，E7 测不出分离。
                    kws = [_tok("n", rng.randrange(50))]
                    content = " ".join(gtoks + [_tok("f", rng.randrange(200)) for _ in range(6)])
                else:
                    content = " ".join(gtoks + [_tok("f", rng.randrange(200)) for _ in range(6)])
                age = rng.randrange(0, 90)
                created = time.strftime("%Y-%m-%d", time.localtime(NOW - age * 86400))
                # 自称 importance：与真实质量**弱**相关 + 大噪声（E32 的剥削对象；
                # 若强相关，则 v3 默认打分已接近最优，演化没有改进空间，实验测不出东西）
                self_imp = max(1, min(10, int(round(true_q * 3 + rng.gauss(0, 3)))))
                out.append({
                    "id": eid, "created_at": created, "updated_at": "",
                    "content": content, "keywords": kws,
                    "links": [], "source_event_id": f"EV-{gid:05d}",
                    "importance": self_imp, "confidence": "中", "validity": {},
                    "_true_quality": round(true_q, 4), "_group": g, "_xpf": int(has_xpf),
                })
                gid += 1
        # 失效标注（遗忘维度的载体）：12% 条目被打上 t_invalid，日期分布在 30–300 天前。
        # 它们仍可能是某些查询的金标 → ttl 过小会误伤召回，过大则保留噪声并增加扫描成本，
        # 由此构成"遗忘"这一维度的真实权衡（否则 ttl 单调最优，实验测不出东西）。
        for e in out:
            if rng.random() < 0.12:
                back = rng.randrange(10, 95)
                e["validity"] = {"t_invalid": time.strftime(
                    "%Y-%m-%d", time.localtime(NOW - back * 86400))}
        # 组内互链（重组能力的载体：[[links]] 一跳扩散）
        by_group = {}
        for e in out:
            by_group.setdefault(e["_group"], []).append(e["id"])
        for g, ids in by_group.items():
            n = len(ids)
            for idx, eid in enumerate(ids):
                e = next(x for x in out if x["id"] == eid)
                a1, a2 = ids[(idx + 1) % n], ids[(idx + 2) % n]
                e["links"] = ["[[" + a1 + "]]", "[[" + a2 + "]]"]
        return out

    # ── 查询负载 ─────────────────────────────────────────────
    def _gen_queries(self, n_train, n_holdout, n_audit, pool):
        rng = self.rng
        by_group = {}
        for e in self.entries:
            by_group.setdefault(e["_group"], []).append(e)
        groups = sorted(by_group)

        def make(split, n):
            qs = []
            for _ in range(n):
                g = rng.choice(groups)
                members = by_group[g]
                toks = [_tok("g", g), _tok("g", g) + "b"]
                text = " ".join(toks)
                if self.terrain == "pseudo":
                    text += " xpf"          # 伪特征出现在查询里，但金标方向在留出集上反转
                elif rng.random() < 0.3:
                    text += " " + _tok("f", rng.randrange(200))
                if split == "train" and self.terrain == "pseudo":
                    key = lambda e: e["_true_quality"] + 2.0 * e["_xpf"]   # 训练集：XPF 指向金标
                elif self.terrain == "pseudo":
                    key = lambda e: e["_true_quality"] - 2.0 * e["_xpf"]   # 留出集：方向反转
                else:
                    key = lambda e: e["_true_quality"]
                gold = [e["id"] for e in sorted(members, key=key, reverse=True)[:3]]
                qs.append({"query": text, "expected": gold, "_group": g, "_split": split})
            return qs

        return {"train": make("train", n_train),
                "holdout": make("holdout", n_holdout),
                "audit": make("audit", n_audit)}

    # ── 金标噪声（E52 独立 / E57 相关）────────────────────────
    def _apply_label_noise(self, p, kind):
        """只污染 train/holdout 的金标；**审计集保持干净**——真实效用必须用干净标尺衡量。

        independent：每条查询独立地以概率 p 把金标换成随机条目 → 双门天然过滤（E52）。
        correlated ：所有查询用**同一个方向**的偏移——标注者偏爱"自称 importance 高"的条目，
                     而这正是 v3 默认打分本来就偏好的东西 → 标注者与系统犯同一个错误，
                     双门挡不住（E57）。区分二者的不是噪声量，是噪声的**方向是否一致**。
        """
        if p <= 0 or kind == "none":
            return
        all_ids = [e["id"] for e in self.entries]
        biased = [e["id"] for e in sorted(self.entries,
                                          key=lambda e: -e.get("importance", 0))[:30]]
        for split in ("train", "holdout"):
            for q in self.queries[split]:
                if self.rng.random() < p:
                    src = biased if kind == "correlated" else all_ids
                    q["expected"] = self.rng.sample(src, 3)

    # ── 留出集轮换（红线 11：留出集是燃料，不是尺子）────────────
    def rotate_holdout(self, gen, every=15):
        if self.terrain == "pseudo":
            return  # 伪特征地形下轮换会破坏构造，显式禁用并说明
        if gen and gen % every == 0:
            rng = random.Random(self.seed * 7919 + gen)
            self.queries["holdout"] = [
                {"query": q["query"], "expected": q["expected"], "_group": q["_group"],
                 "_split": "holdout"}
                for q in rng.sample(self.queries["audit"] + self.queries["holdout"],
                                    k=len(self.queries["holdout"]))
            ]

    # ── 地形与效用 ───────────────────────────────────────────
    def shape(self, g) -> float:
        """欺骗地形的显式塑形项（元层效用的一部分，人侧定义、系统不可见）。

        U_shape = -0.01*max(w_kw-3, 0) + 0.15*1[filter_zero==1 且 w_kw>=4] - 0.005*1[fz==1 且 w_kw<4]

        单点地形（deceptive 下 w_kw 检索中立，故下表只差地形项；gain_fz 为过滤零命中带来的检索增益）：
          (3,0)  = base                      ← 起点
          (3,1)  = base+gain_fz-0.005        ← 局部最优，严格准入会走到这里后卡死
          (3.5,1)= base+gain_fz-0.010        ← 比冠军差，严格准入必拒
          (4,1)  = base+gain_fz-0.010+0.150  ← 全局最优，必须先经过低谷
        低谷深度 0.005–0.010 < 档案准入容忍度 0.05 → 中性/小幅退化的中间态能在档案里存活，
        从而保留跨越低谷的可能（E7）。
        """
        if self.terrain != "deceptive":
            return 0.0
        wk, fz = float(g["w_kw"]), int(g["filter_zero"])
        return (-0.01 * max(wk - 3.0, 0.0)
                + (0.15 if (fz == 1 and wk >= 4.0) else 0.0)
                - (0.005 if (fz == 1 and wk < 4.0) else 0.0))

    def objective(self, gen=0, true=True):
        if self.terrain == "switch" and self.switch_gen is not None and gen >= self.switch_gen:
            # 目标切换必须**真的冲突**，否则测不出灾难性遗忘（上一轮 H3 未获证实的根因）：
            # 切换前"快速响应"→ 成本是惩罚；切换后"深度研究"→ 需要**扩大**扫描面，
            # 成本项权重由 −0.20 变号成 +0.30。两个目标的最优点位于相反方向。
            w = {"recall": 0.20, "mrr": 0.50, "cost": 0.30}
        else:
            w = dict(self.rater_w)
        if true and self.terrain == "drift":
            w = dict(self.W0)                                  # 真实效用一律用初心权重衡量
        return w

    def utility(self, perf: dict, gen=0, genome=None, true=True) -> float:
        w = self.objective(gen, true=true)
        u = (w["recall"] * perf["recall@5"] + w["mrr"] * perf["MRR"]
             + w["cost"] * perf["cost_norm"])                  # cost 权重带符号
        if genome is not None:
            u += self.shape(genome)
        return u

    def drift_step(self, feats_mainline: dict, alpha=None, gen=None):
        """评判者漂移（E14）：人的权重被系统**当前产出**锚定 —— 人逐渐喜欢上系统正在做的事。

        目标权重 = 当前产出特征量归一到与 W0 相同的 L1 尺度。因为 cost_norm 是正的，
        成本项权重会从 −0.20 一路漂到正值：系统越臃肿，人越觉得"详实"。
        于是系统会为了讨好这把坏尺子而膨胀扫描面，真实效用（W0）随之下降。
        """
        if self.terrain != "drift":
            return
        if gen is not None and gen < self.drift_start:
            return
        a = self.drift_alpha if alpha is None else alpha
        tot = sum(abs(float(feats_mainline.get(k, 0.0))) for k in self.W0) or 1.0
        for k in self.W0:
            target = float(feats_mainline.get(k, 0.0)) / tot * self._W0_scale
            self.rater_w[k] = (1.0 - a) * self.rater_w[k] + a * target

    def to_lib_entries(self):
        """导出为 SCHEMA_V3 合法条目（去掉内部 `_` 前缀字段）。"""
        return [{k: v for k, v in e.items() if not k.startswith("_")} for e in self.entries]

    def dump(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps({
            "seed": self.seed, "terrain": self.terrain,
            "n_entries": len(self.entries),
            "queries": {k: len(v) for k, v in self.queries.items()},
        }, ensure_ascii=False, indent=1), encoding="utf-8")
