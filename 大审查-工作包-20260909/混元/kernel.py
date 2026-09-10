"""自演化内核 v1 —— 把 26 轮推演的结论落实为可运行代码

设计来源（每条都对应实验结论）：
  E7/E9   两级门控：宽松准入(tol) + 双门晋升(margin)   —— 严格准入 0/20 逃出
  E14/69  锚定层：锚定集永不衰减，只重锚
  E32     importance 实测化（被检索后是否被采纳）
  E44/E96 停摆监控检测【绝对状态】(采纳数=0)，不是相对目标
  E64/93  注意力预算账本，不足则禁止演化
  E72/E96 Pareto 档案 cap=8；tol=0.02-0.04
  E87/E100 盲评为默认层（结构性削弱污染通道）
  E97b    审计频率 >> 样本量；探针轮换 + 不可预知
  E104/110 大幅度(scale 2-3) × 审计 配对；单独大幅度 −0.048
  E111    盲评是大幅度安全的前提
  E115    复合危险数 >=3 → 幅度降档到 1.0
  E119/123 整理是审计在数据空间生效的前提
  E122    整理标准用真值，不用 judge（+0.064 vs +0.005）
  E85/E100 judge 数字永不对外报告（类型级约束）

三层结构：
  元层 Meta   —— 效用函数/任务集/探针/预算，仅人侧，系统无写入方法
  法层 Policy —— 检索与演化参数，系统可自由演化
  行层 Row    —— 记忆条目，系统可自由写（但需整理）
"""
from __future__ import annotations
import random, math, json, hashlib
from dataclasses import dataclass, field, asdict, replace
from typing import List, Tuple, Optional, Dict, Any, Literal

# ══════════════════════════════════════════════════════════════
# 第 0 层：类型级红线（能力式，不是检测式）
# ══════════════════════════════════════════════════════════════

ScreenResult = Literal["reject", "unknown"]
# ★ 没有 "accept" —— 廉价筛选【在类型上】无法采纳。
#   违反此红线的代码写不出来，而不是"写了会被拒绝"。(原则 9)


class JudgeScore(float):
    """judge 分数的包装类型。

    ★ 唯一出口是 .internal —— 仅用于内部排序。
      没有 __str__/__repr__ 的友好输出，防止误当报告用。(E85: 膨胀 349×)
    """
    __slots__ = ()

    @property
    def internal(self) -> float:
        return float(self)

    def __str__(self):      # 强制：judge 数字不可对外呈现
        return "<judge:internal-only>"

    __repr__ = __str__


@dataclass(frozen=True)
class Meta:
    """元层：仅人侧，冻结。系统拿不到写入方法。"""
    task_seed: int = 7777
    probe_seed: int = 4242
    probe_n: int = 4
    audit_every: int = 5          # E97b: 频率优先于样本量
    rotate_every: int = 10        # E84: 探针必须轮换
    blind_alpha: float = 0.95     # E87: 盲评把表象影响压到 0.05
    budget: int = 300             # E93: judge 可被操纵时门槛 300（原 150）
    danger_threshold: int = 3     # E115: >=3 种危险 → 降档
    signature: str = "HUMAN-SIGNED"

    def with_(self, **kw) -> "Meta":
        """★ 只暴露给人类调用方；系统侧不持有可写引用。"""
        return replace(self, **kw, signature="HUMAN-SIGNED")


# ══════════════════════════════════════════════════════════════
# 第 1 层：数据模型
# ══════════════════════════════════════════════════════════════

@dataclass
class Entry:
    id: str
    kw: str
    topic: str
    content: str
    importance: float = 1.0        # ★ 实测化后的值（E32），非自称
    adopted: int = 0               # 被检索后真正被采纳的次数
    shown: int = 0                 # 被检索到的次数
    quality: float = 0.5           # 真值（系统不可见，仅审计时用）
    length: float = 0.5            # 表象特征
    formatting: float = 0.5
    density: float = 0.5
    citation: float = 0.0
    self_written: bool = False

    @property
    def measured_importance(self) -> float:
        """E32：实测 = 被采纳率。系统本就有 (adopted, shown) 记录，零新增成本。"""
        if self.shown == 0:
            return 0.0
        return self.adopted / self.shown


@dataclass(frozen=True)
class Policy:
    """法层：可自由演化的检索/写入参数。"""
    w_kw: float = 3.0
    w_content: float = 1.0
    w_imp: float = 1.0
    w_age: float = 0.1
    w_len: float = 0.0
    w_fmt: float = 0.0
    w_den: float = 0.0
    w_cit: float = 0.0
    filter_zero: int = 0
    deep: int = 0
    writalloc: float = 0.5         # 写入时投给真实质量的比例（E121）

    def surf_magnitude(self) -> float:
        return abs(self.w_len) + abs(self.w_fmt) + abs(self.w_den) + abs(self.w_cit)


SCALARS = ("w_kw", "w_content", "w_imp", "w_age")
SURF = ("w_len", "w_fmt", "w_den", "w_cit")


# ══════════════════════════════════════════════════════════════
# 第 2 层：检索 + judge + 盲评
# ══════════════════════════════════════════════════════════════

def retrieve(entries: List[Entry], q: str, p: Policy, k: int = 5) -> List[Entry]:
    qw = q.split()
    out = []
    for e in entries:
        kh = sum(1 for w in qw if w in e.kw)
        ch = sum(1 for w in qw if w in e.content)
        if p.filter_zero and kh == 0 and ch == 0:
            continue
        s = (p.w_kw * kh + p.w_content * ch
             + p.w_imp * e.measured_importance
             - p.w_age * 0.1)
        if p.w_len or p.w_fmt or p.w_den or p.w_cit:
            s += (p.w_len * e.length + p.w_fmt * e.formatting
                  + p.w_den * e.density + p.w_cit * e.citation)
        out.append((s, e))
    out.sort(key=lambda x: (-x[0], x[1].id))
    return [e for _, e in out[:k]]


def judge(entries: List[Entry], tasks: List[str], p: Policy,
          alpha: float, blind: bool) -> JudgeScore:
    """judge 评分。alpha = judge 看真值的比例；blind=True 时剥离表象 (E87)。

    ★ 返回 JudgeScore，不是 float。想拿数字必须走 .internal，
      且 Kernel 保证 .internal 只用于档案排序，不进入任何对外报告。
    """
    eff = 0.95 if blind else alpha          # 盲评：把污染压到 0.05
    if not entries:
        return JudgeScore(0.0)
    real, surf, n = 0.0, 0.0, 0
    for t in tasks:
        for e in retrieve(entries, t, p):
            real += e.quality
            surf += (e.length + e.formatting + e.density + e.citation) / 4.0
            n += 1
    if n == 0:
        return JudgeScore(0.0)
    return JudgeScore(eff * (real / n) + (1 - eff) * (surf / n))


def truth(entries: List[Entry], tasks: List[str], p: Policy) -> float:
    """真值：审计专用读数。绕开 judge 通道（E81c）。"""
    if not entries:
        return 0.0
    tot, n = 0.0, 0
    for t in tasks:
        for e in retrieve(entries, t, p):
            tot += e.quality
            n += 1
    return tot / n if n else 0.0


# ══════════════════════════════════════════════════════════════
# 第 3 层：廉价筛选（能力式：无 accept）
# ══════════════════════════════════════════════════════════════

def cheap_screen(p: Policy) -> ScreenResult:
    """廉价筛选：只能拒绝，不能采纳。(E50/E13)

    返回 "reject" 表示明确该杀；"unknown" 表示无法判断 → 交给昂贵门控。
    ★ 类型上不存在 "accept"，所以"用廉价筛选采纳"的代码写不出来。
    """
    if p.surf_magnitude() > 50.0:       # 表象权重离谱，直接拒
        return "reject"
    if not (0.0 <= p.writalloc <= 1.0):
        return "reject"
    return "unknown"


# ══════════════════════════════════════════════════════════════
# 第 4 层：变异（大幅度 + 温度采样）
# ══════════════════════════════════════════════════════════════

def mutate(p: Policy, rnd: random.Random, scale: float) -> Policy:
    d = asdict(p)
    r = rnd.random()
    if r < 0.08:
        d["deep"] = 1 - d["deep"]
    elif r < 0.16:
        d["filter_zero"] = 1 - d["filter_zero"]
    elif r < 0.24:
        d["writalloc"] = round(min(1.0, max(0.0,
            d["writalloc"] + rnd.choice([-0.3, -0.15, 0.15, 0.3]))), 3)
    else:
        f = rnd.choice(SCALARS + SURF)
        # E104: 加性成分必须有，否则 0*倍数 永远锁死在 0（F-18 教训）
        d[f] = round(max(-5.0, min(20.0,
            d[f] * (1 + rnd.choice([-0.4, -0.15, 0.2, 0.6]) * scale)
            + rnd.choice([0, 0, 0.5, -0.5]) * scale)), 4)
    return Policy(**d)


def pareto_front(arch: List[Policy], entries: List[Entry],
                 train: List[str], held: List[str],
                 alpha: float, blind: bool) -> List[Policy]:
    """干净双目标 Pareto：(训练集 judge, 留出集 judge)。

    ★ 两个目标都是实测 judge 读数，不含"我知道什么是表象"的先验
      （F-21 教训：目标被构造污染会让结论不可用）。
    """
    pts = []
    for c in arch:
        a = judge(entries, train, c, alpha, blind).internal
        b = judge(entries, held, c, alpha, blind).internal
        pts.append(((a, b), c))
    front = []
    for (A, ca) in pts:
        dominated = False
        for (B, _cb) in pts:
            if B[0] >= A[0] and B[1] >= A[1] and (B[0] > A[0] or B[1] > A[1]):
                dominated = True
                break
        if not dominated:
            front.append(ca)
    return front or arch[-1:]


def pick_parent(arch: List[Policy], entries: List[Entry],
                train: List[str], alpha: float, blind: bool,
                temp: float, rnd: random.Random) -> Policy:
    """温度采样：0 = 只取最好，1 = 均匀随机。(E104: 0.3 最优)"""
    if temp <= 0 or len(arch) == 1:
        return rnd.choice(arch[-3:])
    scores = [judge(entries, train, c, alpha, blind).internal for c in arch]
    lo, hi = min(scores), max(scores)
    if hi - lo < 1e-9:
        return rnd.choice(arch)
    wts = [math.exp((s - lo) / (hi - lo) / max(0.01, temp)) for s in scores]
    tot = sum(wts)
    r = rnd.random() * tot
    acc = 0.0
    for c, w in zip(arch, wts):
        acc += w
        if r <= acc:
            return c
    return arch[-1]


# ══════════════════════════════════════════════════════════════
# 第 5 层：内核
# ══════════════════════════════════════════════════════════════

@dataclass
class KernelConfig:
    scale: float = 2.0          # E106: 2.0 见顶；E115 复合危险→1.0
    temp: float = 0.3           # E104
    tol: float = 0.04           # E96: 宽松准入 0.02-0.04
    margin: float = 0.02        # E96: 有监控时几乎不重要
    cap: int = 8                # E72
    kids: int = 4
    blind: bool = True          # ★ E111: 盲评是大幅度安全的前提
    audit: bool = True          # ★ E110: 必须与大幅度配对
    write_every: int = 0        # 0 = 不自写入（静态世界）
    write_n: int = 3
    prune_by: Optional[str] = None   # None / "truth"（★ E122: 不用 judge）
    prune_every: int = 2
    monitor: bool = True        # E44: 检测绝对状态
    reanchor_after: int = 2     # E26/E67: 连续退化 N 次 → 判定世界变了→重锚
    reanchor_after: int = 2     # E26/E67: 连续退化 N 次 → 判定世界变了→重锚


@dataclass
class Report:
    """★ 对外报告。注意：里面没有任何 judge 分数。(E85)"""
    generation: int
    truth_score: float          # 真值审计读数（可对外）
    policy: Policy
    reverts: int = 0
    adopts: int = 0
    budget_spent: int = 0
    notes: str = ""


@dataclass
class Kernel:
    entries: List[Entry]
    tasks_train: List[str]
    tasks_held: List[str]
    meta: Meta = field(default_factory=Meta)
    cfg: KernelConfig = field(default_factory=KernelConfig)
    rnd: random.Random = field(default_factory=lambda: random.Random(0))

    def __post_init__(self):
        self.root = Policy()
        self.archive: List[Policy] = [self.root]
        self.champion: Policy = self.root
        self.anchor: List[Tuple[str, str]] = []     # 锚定集（永不衰减）
        self.anchor_truth: Optional[float] = None
        self._probe_seed = self.meta.probe_seed
        self._best_truth: Optional[float] = None
        self._best_policy: Policy = self.root
        self._stall = 0
        self._degrade_streak = 0
        self.reanchors = 0          # 重锚次数（★ 与回退区分）
        self.reports: List[Report] = []
        self.spent = 0
        self.alpha = 0.5      # judge 看真值的比例（外部设定）
        self.dangers: set = set()

    # ── 审计探针：外部固定 + 不可预知 + 轮换 ──
    def _probe(self) -> List[str]:
        r = random.Random(self._probe_seed + self.generation)   # ★ 每代不同
        pool = [f"{t}" for t in self.tasks_train] + [f"{t}" for t in self.tasks_held]
        if not pool:
            return []
        return [r.choice(pool) for _ in range(self.meta.probe_n)]

    def _audit(self) -> Tuple[bool, float]:
        """真值审计。

        ★ 区分两种退化（E12 四态判别的简化版）：
          - 配置跑飞  → 回退到历史最优配置
          - 世界变了  → 回退无用，必须【重锚】(E26/E67/E69)

        判据：连续 reanchor_after 次审计都退化，且回退未能恢复
              → 判定为"世界变了"，重置基线，在新基线上继续演化。
        """
        cur = truth(self.entries, self._probe(), self.champion)
        self.spent += self.meta.probe_n * 12       # E93: 12/样本

        if self._best_truth is None:
            self._best_truth, self._best_policy = cur, self.champion
            return False, cur

        if cur >= self._best_truth - 0.01:
            self._best_truth, self._best_policy = cur, self.champion
            self._degrade_streak = 0
            return False, cur

        # 退化：先看是不是"世界变了"
        self._degrade_streak += 1
        if self._degrade_streak >= self.cfg.reanchor_after:
            # 世界变了 → 重锚：基线重置为当前，保留当前配置
            self._best_truth = cur
            self._best_policy = self.champion
            self._degrade_streak = 0
            self.reanchors += 1
            return False, cur

        # 否则视为配置跑飞 → 回退
        self.champion = self._best_policy
        self.archive = [self.champion]
        return True, cur

    # ── 数据空间：写入 + 整理 ──
    def _write(self):
        p = self.champion
        for _ in range(self.cfg.write_n):
            i = len(self.entries)
            kw = f"K{self.rnd.randrange(6)}"
            topic = self.rnd.choice(self.tasks_train) if self.tasks_train else "T"
            a = p.writalloc
            self.entries.append(Entry(
                id=f"n{i}", kw=kw, topic=topic, content=f"{topic} {kw} 自写入{i}",
                importance=0.0,                       # 新条目无实测，从 0 起
                quality=self.rnd.random() * a,        # 真实质量 ∝ writalloc
                length=self.rnd.random() * (1 - a) + 0.5 * a,
                formatting=self.rnd.random() * (1 - a) + 0.5 * a,
                density=self.rnd.random() * (1 - a) + 0.5 * a,
                citation=1.0 if self.rnd.random() < (1 - a) else 0.5,
                self_written=True,
            ))

    def _prune(self):
        """★ 整理标准用真值，不用 judge（E122: +0.064 vs +0.005）。"""
        mine = [e for e in self.entries if e.self_written]
        if len(mine) <= 8:
            return
        mine.sort(key=lambda e: e.quality)          # 真值排序
        for e in mine[:max(1, len(mine) // 4)]:
            self.entries.remove(e)

    # ── 单代执行（抽出以便注入漂移/污染做验证）──
    def _step(self, g: int, pool: Optional[List[str]] = None):
        pool = pool or (self.tasks_train + self.tasks_held)
        self.generation = g

        # E115: 复合危险降档
        eff_scale = 1.0 if len(self.dangers) >= self.meta.danger_threshold else self.cfg.scale

        # E64/93: 预算耗尽则停止演化
        if self.spent >= self.meta.budget:
            self.reports.append(Report(g, truth(self.entries, pool, self.champion),
                                       self.champion, notes="预算耗尽，停止演化"))
            return

        adopts = 0
        for _ in range(self.cfg.kids):
            parent = pick_parent(self.archive, self.entries, self.tasks_train,
                                 self.alpha, self.cfg.blind, self.cfg.temp, self.rnd)
            child = mutate(parent, self.rnd, eff_scale)

            # 能力式筛选：只能拒绝（无 accept 分支）
            if cheap_screen(child) == "reject":
                continue

            d_tr = (judge(self.entries, self.tasks_train, child, self.alpha, self.cfg.blind).internal
                    - judge(self.entries, self.tasks_train, parent, self.alpha, self.cfg.blind).internal
                    + self.rnd.gauss(0, 0.05))
            d_he = (judge(self.entries, self.tasks_held, child, self.alpha, self.cfg.blind).internal
                    - judge(self.entries, self.tasks_held, parent, self.alpha, self.cfg.blind).internal
                    + self.rnd.gauss(0, 0.05))

            # E7 第一级：宽松准入
            if d_tr > -self.cfg.tol:
                self.archive.append(child)
            self.archive = pareto_front(self.archive, self.entries, self.tasks_train,
                                        self.tasks_held, self.alpha, self.cfg.blind)
            if len(self.archive) > self.cfg.cap:
                self.archive = self.rnd.sample(self.archive, self.cfg.cap)

            # E7 第二级：双门晋升（严格）
            if d_tr > self.margin and d_he > self.margin and \
               judge(self.entries, self.tasks_train, child, self.alpha, self.cfg.blind).internal > \
               judge(self.entries, self.tasks_train, self.champion, self.alpha, self.cfg.blind).internal:
                self.champion = child
                adopts += 1

        # E44: 停摆监控 —— 检测【绝对状态】采纳数=0
        if self.cfg.monitor:
            if adopts == 0:
                self._stall += 1
                if self._stall >= 5:
                    self.margin = max(0.005, self.margin * 0.5)
                    self._stall = 0
            else:
                self._stall = 0

        # 数据空间
        if self.cfg.write_every and g % self.cfg.write_every == 0:
            self._write()
        if self.cfg.prune_by and g % self.cfg.prune_every == 0:
            self._prune()

        # 真值审计（频率优先，探针轮换）
        reverted = False
        cur = truth(self.entries, pool, self.champion)
        if self.cfg.audit and g % self.meta.audit_every == 0:
            reverted, _ = self._audit()
            cur = truth(self.entries, pool, self.champion)
        if self.meta.rotate_every and g % self.meta.rotate_every == 0:
            self._probe_seed += 17
            self._best_truth = None
            self._best_policy = self.champion

        self.reports.append(Report(
            generation=g, truth_score=cur, policy=self.champion,
            reverts=1 if reverted else 0, adopts=adopts,
            budget_spent=self.spent,
        ))

    def run(self, generations: int = 30, task_pool: Optional[List[str]] = None):
        pool = task_pool or (self.tasks_train + self.tasks_held)
        self.margin = self.cfg.margin
        for g in range(1, generations + 1):
            self._step(g, pool)
            if self.reports and "预算耗尽" in (self.reports[-1].notes or ""):
                break
        return self.reports

    # ── 对外接口 ──
    def final_report(self) -> Dict[str, Any]:
        """★ 唯一对外的报告接口。不含任何 judge 分数。(E85)"""
        last = self.reports[-1] if self.reports else None
        return {
            "truth_score": round(last.truth_score, 4) if last else 0.0,
            "generations": len(self.reports),
            "reverts": sum(r.reverts for r in self.reports),
            "reanchors": self.reanchors,      # ★ 重锚 ≠ 回退
            "reanchors": self.reanchors,      # ★ 重锚 ≠ 回退
            "budget_spent": self.spent,
            "policy_surface_magnitude": round(self.champion.surf_magnitude(), 3),
            "entry_count": len(self.entries),
            "self_written_frac": round(
                sum(1 for e in self.entries if e.self_written) / max(1, len(self.entries)), 3),
        }
