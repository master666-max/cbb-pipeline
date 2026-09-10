# -*- coding: utf-8 -*-
"""naive_memory.py — 被审查基线：一个"看起来合理"的朴素自演化记忆库原型（约 95 行）

它复刻了一个未经治理的记忆库自演化引擎最自然的写法，【故意】保留与 bootstrap_v3
同构的机制缺口，供 baseline_review.py 探针逐条复现。后续 19 个实验即围绕这些缺口的
动态后果展开。缺陷标记 [Dx] 与探针一一对应。
"""
import time

class NaiveMemory:
    # [D7] 死参数：写进配置、对外宣称可调，运行时无任何消费方（公理 G 意义上的表演性配置）
    TUNABLES = {"broadcast_weights": [0.6, 0.3, 0.1], "index_hot_budget": 200,
                "review_intervals": [1, 7, 30], "emotion": {"valence": 0, "arousal": 0.5}}

    def __init__(self, w_kw=3.0, w_c=1.0, w_imp=1.0, w_age=0.1, spread=0.5):
        self.ents = {}; self.accum = 0; self.baseline = None
        self.w = (w_kw, w_c, w_imp, w_age, spread)

    def add(self, e):
        # [D1] 不校验 importance 范围/类型：条目自报多少就信多少（对照真实 validate_entry 只查字段存在）
        # [D0] 同 id 直接覆盖（朴素写法，违"永不覆盖"）
        self.ents[e["id"]] = e
        self.accum += e.get("importance", 0)          # [D5] 反思触发只累加【自报】importance

    def _hit(self, e, qw):
        kb = " ".join(e["keywords"]); cb = " ".join(e["content"])
        kw = sum(1 for w in qw if w in kb); c = sum(1 for w in qw if w in cb)
        if kw: c = max(c, 1)
        return kw, c

    def search(self, query, k=5, now=365, tokenize="space"):
        qw = query.split() if tokenize == "space" else [query.replace(" ", "")[i:i+2] for i in range(len(query.replace(" ", ""))-1)]  # [D4] 默认 split
        scored = {}
        for fid, e in self.ents.items():
            if e.get("t_invalid") is not None: continue
            kw, c = self._hit(e, qw)
            age = now - e["created_day"]
            scored[fid] = [self.w[0]*kw + self.w[1]*c + self.w[2]*e["importance"] - self.w[3]*age, e, kw+c]
        for fid, (s, e, wh) in list(scored.items()):     # [D3] links 扩散给零命中目标
            if s <= 0: continue
            for lid in e["links"]:
                if lid in scored and scored[lid][2] == 0:
                    scored[lid][0] += self.w[4] * s
        # [D2] 零词命中条目不过滤：单靠 importance-age 也能上榜
        return sorted(scored.items(), key=lambda kv: -kv[1][0])[:k]

    def maybe_reflect(self, thr=50, topn=6):
        if self.accum < thr: return None
        top = sorted(self.ents.values(), key=lambda e: -e["importance"])[:topn]  # [D5] 被自报值支配
        self.accum = 0
        return top

    def run_eval(self, golden, k=5, now=365):
        hits = 0
        for item in golden:
            top = [fid for fid, _ in self.search(item["query"], k, now)]
            if set(top) & set(item["expected"]): hits += 1
        score = hits / len(golden)
        self.baseline = score            # [D6] 无条件覆盖基线：劣化结果也写回 → 棘轮可被逐步拉低
        return score

    def retire(self, now, ttl=90):       # [D8] 固定 TTL，只看 t_invalid 标记，不看真实复用
        out = []
        for fid in list(self.ents):
            inv = self.ents[fid].get("t_invalid")
            if inv is not None and now - inv >= ttl: out.append(self.ents.pop(fid))
        return out
