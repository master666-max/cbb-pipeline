"""参数化检索内核 + 记忆库行层状态（存储/更新/遗忘/重组）。

与 bootstrap_v3.py 的关系（本实验的 correctness 门禁）：
  - rank() 是 _rank_entries 的**参数化重实现**；默认基因组下必须与真实函数逐条同分。
  - 该等价性由 `equivalence_gate()` 强制校验，不通过则整个实验不得开跑（见 run.py selftest）。
  - 之所以不直接调 _rank_entries：演化循环需要上万次评估，真实函数每次都全盘 rglob + 读盘，
    IO 会主导测量，测不出演化本身。等价性门禁负责堵住"重实现跑偏"的风险。
"""
from __future__ import annotations

import functools
import json
import time

from genome import DEFAULT


@functools.lru_cache(maxsize=None)
def _ts(date10: str) -> float:
    """日期 → 时间戳。**必须缓存**：time.strptime 极慢（约 10µs），
    未缓存时每个条目每个查询都要重新解析一次日期，实测占 60% 墙钟
    （cProfile：246 万次调用 / 25s）。
    """
    return time.mktime(time.strptime(date10, "%Y-%m-%d"))


def age_days(entry, now: float) -> float:
    try:
        return (now - _ts(entry["created_at"][:10])) / 86400.0
    except Exception:
        return 0.0


class Library:
    """行层记忆库：热/冷分层、attic（遗忘）、采纳日志（更新）、链接（重组）。"""

    def __init__(self, entries, now: float, base_importance=1):
        self.now = now
        # 预计算检索用的文本块：每个条目每个查询都重新 join 一次关键词是纯浪费
        self.by_id = {}
        for e in entries:
            d = dict(e)
            d["_kw_blob"] = " ".join(d.get("keywords") or [])
            d["_content"] = d.get("content") or ""
            self.by_id[d["id"]] = d
        self.tier = {}
        self.cold = set()
        self.attic = set()
        self.shown = {}
        self.adopt = {}
        self.append_count = 0
        self.max_age = DEFAULT["max_age_days"]   # 遗忘闸门的当前设定（3650 ≈ 关闭）
        self.imp_src = DEFAULT["importance_source"]
        self.true_quality = {e["id"]: e.get("_true_quality", 0.0) for e in entries}
        for e in entries:
            self.tier[e["id"]] = "longterm" if e.get("importance", 0) >= 7 else "intermediate"
        self._rescore_hot(DEFAULT["hot_budget"])

    # ── 存储 ──────────────────────────────────────────────
    def append(self, entry, longterm_cut=7):
        eid = entry["id"]
        if eid in self.by_id:                    # 铁律 1：永不覆盖
            return False
        self.by_id[eid] = dict(entry)
        self.tier[eid] = "longterm" if entry.get("importance", 0) >= longterm_cut else "intermediate"
        self.true_quality.setdefault(eid, entry.get("_true_quality", 0.5))
        self.append_count += 1
        return True

    def _hot_key(self, eid):
        # 热度分层必须只依赖**基因组**，不能依赖"采纳日志是否为空"这类 incidental 状态，
        # 否则同一基因组在不同代数上会选出不同的热层 → 演化效果与"用了多少代"混淆。
        imp = self.importance_of(eid, {"importance_source": self.imp_src})
        recency = 1.0 / (1.0 + age_days(self.by_id[eid], self.now) / 30.0)
        return imp * recency

    def _rescore_hot(self, hot_budget):
        live = [i for i in self.by_id if i not in self.attic]
        live.sort(key=self._hot_key, reverse=True)
        self.cold = set(live[int(hot_budget):])

    def evict(self, hot_budget):
        """热度分层逐出（A14 口径）：超预算条目转冷，不参与扫描 → 省成本、可能损召回。"""
        self._rescore_hot(hot_budget)

    def apply(self, g: dict):
        """按基因组施加行层策略：热度分层 + 遗忘闸门 + 出仓。演化循环的唯一切换点。"""
        self.max_age = g.get("max_age_days", self.max_age)
        self.imp_src = g.get("importance_source", self.imp_src)
        self._rescore_hot(g["hot_budget"])
        return self.retire(g["ttl_days"])

    # ── 遗忘（铁律 1：只移 attic，不删除）─────────────────────
    def retire(self, ttl_days):
        moved = []
        for eid, e in self.by_id.items():
            if eid in self.attic:
                continue
            inv = (e.get("validity") or {}).get("t_invalid")
            if not inv:
                continue
            try:
                ts = _ts(str(inv)[:10])
            except Exception:
                continue
            if (self.now - ts) / 86400.0 >= ttl_days:
                self.attic.add(eid)
                moved.append(eid)
        return moved

    # ── 更新（E32：importance 从"自称"改为"实测采纳率"）──────────
    def record_feedback(self, ranked, expected: set):
        for i, fid in enumerate(ranked):
            self.shown[fid] = self.shown.get(fid, 0) + 1
            if fid in expected:
                self.adopt[fid] = self.adopt.get(fid, 0) + 1

    def importance_measured(self, eid):
        # 贝叶斯平滑：采纳率映射到 0–10，与自称 importance 同量纲
        s, a = self.shown.get(eid, 0), self.adopt.get(eid, 0)
        return round((a + 1.0) / (s + 2.0) * 10.0, 4)

    def importance_of(self, eid, g):
        if g["importance_source"] == "measured":
            return self.importance_measured(eid)
        return float(self.by_id[eid].get("importance", 0))

    def snapshot(self):
        """行层状态快照：保证冠军与候选在同一状态上做**配对**比较。"""
        return (dict(self.shown), dict(self.adopt), set(self.attic), set(self.cold))

    def restore(self, s):
        self.shown, self.adopt = s[0].copy(), s[1].copy()
        self.attic, self.cold = set(s[2]), set(s[3])

    # ── 扫描面 ────────────────────────────────────────────
    def scannable(self):
        """与 _rank_entries 同构：attic / 冷层 / t_invalid 一律不参与检索；
        另加遗忘闸门 max_age_days（对 v3 invalid_ttl_days 的推广，可演化）。"""
        out = []
        for i, e in self.by_id.items():
            if i in self.attic or i in self.cold:
                continue
            if (e.get("validity") or {}).get("t_invalid"):
                continue
            if self.max_age is not None and age_days(e, self.now) > self.max_age:
                continue
            out.append(i)
        return out

    def bytes(self):
        return sum(len(json.dumps(e, ensure_ascii=False)) for e in self.by_id.values())


# ─────────────────────────────────────────────────────────────
# 参数化检索（= _rank_entries 的可演化形态）
# ─────────────────────────────────────────────────────────────

def score_all(lib: Library, q: str, g: dict, now: float = None):
    now = lib.now if now is None else now
    words = q.split()
    scored = {}
    for eid in lib.scannable():
        e = lib.by_id[eid]
        kws = e.get("_kw_blob") or " ".join(e.get("keywords") or [])
        c = e.get("_content", e.get("content") or "")
        kw_hit = sum(1 for w in words if w in kws)
        c_hit = sum(1 for w in words if w in c)
        if kw_hit:
            c_hit = max(c_hit, 1)
        if g["filter_zero"] and kw_hit == 0 and c_hit == 0:
            continue
        s = (g["w_kw"] * kw_hit + g["w_content"] * c_hit
             + g["w_imp"] * lib.importance_of(eid, g)
             - g["w_age"] * age_days(e, now))
        scored[eid] = [s, e]

    if g["merge_mode"] == "hier":
        scored = _hier_merge(scored, lib)

    if g["link_spread"] > 0:
        # 必须与 _rank_entries 同构：传播量取**传播发生前**的快照分数，
        # 而不是被前面几轮扩散抬升后的当前值（否则等价性门禁过不去）。
        orig = {eid: scored[eid][0] for eid in scored}
        for eid in list(scored):
            s = orig[eid]
            if s <= 0:
                continue
            for link in scored[eid][1].get("links", []) or []:
                lid = str(link).strip("[]")
                if lid in scored:
                    t = scored[lid][1]
                    blob = t.get("_content", "") + " " + t.get("_kw_blob", "")
                    if not any(w and w in blob for w in words):
                        scored[lid][0] += s * g["link_spread"]
    return scored


def _hier_merge(scored, lib):
    """层次化归并（E28 候选）：同组条目取组均值，用组内等权换维度成本。"""
    groups = {}
    for eid, (s, e) in scored.items():
        kws = e.get("keywords", []) or []
        key = kws[0] if kws else "_"
        groups.setdefault(key, []).append((eid, s, e))
    out = {}
    for key, items in groups.items():
        mean = sum(s for _, s, _ in items) / len(items)
        for eid, _, e in items:
            out[eid] = [mean, e]
    return out


def topk(lib: Library, q: str, g: dict, k: int = 5):
    scored = score_all(lib, q, g)
    ranked = sorted(scored.items(), key=lambda kv: kv[1][0], reverse=True)
    return [fid for fid, _ in ranked[:k]]


# ─────────────────────────────────────────────────────────────
# 等价性门禁：证明 rank() 在默认基因下 == 真实 _rank_entries
# ─────────────────────────────────────────────────────────────

def equivalence_gate(bs3, world, tol=1e-4):
    """把世界条目落到真实库，跑真实 _rank_entries，与 rank() 逐条对比。

    时钟注入口径：真实函数内部用 time.time() 计算 age_days，故每次对比前现取 now
    并显式传入 score_all，消除时钟漂移（红线 27）。
    """
    import tempfile
    from pathlib import Path

    lib_dir = Path(tempfile.mkdtemp(prefix="eqgate_"))
    for d in ("memory/intermediate", "memory/longterm", "audit", "ledger", "evals"):
        (lib_dir / d).mkdir(parents=True, exist_ok=True)
    sub = world.entries[:120]
    for e in world.to_lib_entries()[:120]:
        (lib_dir / "memory" / "intermediate" / f"{e['id']}.json").write_text(
            json.dumps(e, ensure_ascii=False), encoding="utf-8")

    lib = Library(sub, time.time())
    lib._rescore_hot(10 ** 6)  # 门禁阶段不测逐出：全部可扫

    probes = [q["query"] for q in world.queries["train"][:5] + world.queries["audit"][:5]]
    mismatch, checked = [], 0
    for q in probes:
        now = time.time()
        real, _ = bs3._rank_entries(lib_dir, q)
        mine = {k: v[0] for k, v in score_all(lib, q, DEFAULT, now=now).items()}
        for eid, (s, _e, _c) in real.items():
            checked += 1
            if eid not in mine or abs(mine[eid] - s) > tol:
                mismatch.append({"q": q, "id": eid, "real": round(s, 6),
                                 "mine": round(mine.get(eid, float("nan")), 6)})
    return {"checked_pairs": checked, "mismatch": mismatch[:10],
            "passed": not mismatch, "n_entries": len(sub), "n_queries": len(probes)}
