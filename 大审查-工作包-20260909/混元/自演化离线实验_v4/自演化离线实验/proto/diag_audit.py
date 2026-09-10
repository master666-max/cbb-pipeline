"""诊断：为什么内核里审计是负收益，而 E110 是 +0.162？

假设：
  H1 审计在【干净静态世界】里无事可做，只有噪声成本 → 负收益合理
  H2 探针样本太少（4）导致误回退 → 回退次数异常高
  H3 审计本该抓【漂移/污染】，测试世界没开这些 → 没东西可抓

验证：分别在有/无漂移下测审计收益，并统计回退次数。
"""
import sys, statistics, random
sys.path.insert(0, '/data/workspace/proto')
from kernel import Kernel, KernelConfig, Policy, Entry, truth, judge
from check_pairing import build_world, mk

TOPICS = [f"T{i}" for i in range(16)]


def run_with_drift(seed, scale, audit, drift=0.0, gens=20):
    kk = mk(seed, scale=scale, audit=audit)
    base = truth(kk.entries, kk.tasks_train + kk.tasks_held, Policy())
    # 漂移：从第 gens//3 代起，条目的 quality 被重新洗牌（世界变了）
    drift_at = gens // 3 if drift > 0 else 10 ** 9
    orig = []
    for g in range(1, gens + 1):
        kk.generation = g
        if g == drift_at and drift > 0:
            r = random.Random(seed + 999)
            for e in kk.entries:
                orig.append((e, e.quality))
                if r.random() < drift:
                    e.quality = r.random()      # 世界变了
        kk._run_one(g)
    return (truth(kk.entries, kk.tasks_train + kk.tasks_held, kk.champion) - base,
            sum(x.reverts for x in kk.reports))


def _monkey():
    """给 Kernel 加一个单代执行方法（避免改动主循环结构）"""
    def _run_one(self, g):
        self.generation = g
        if self.spent >= self.meta.budget:
            return
        adopts = 0
        for _ in range(self.cfg.kids):
            from kernel import pick_parent, mutate, cheap_screen, pareto_front, judge
            parent = pick_parent(self.archive, self.entries, self.tasks_train,
                                 self.alpha, self.cfg.blind, self.cfg.temp, self.rnd)
            child = mutate(parent, self.rnd, self.cfg.scale)
            if cheap_screen(child) == "reject":
                continue
            d_tr = (judge(self.entries, self.tasks_train, child, self.alpha, self.cfg.blind).internal
                    - judge(self.entries, self.tasks_train, parent, self.alpha, self.cfg.blind).internal
                    + self.rnd.gauss(0, 0.05))
            d_he = (judge(self.entries, self.tasks_held, child, self.alpha, self.cfg.blind).internal
                    - judge(self.entries, self.tasks_held, parent, self.alpha, self.cfg.blind).internal
                    + self.rnd.gauss(0, 0.05))
            if d_tr > -self.cfg.tol:
                self.archive.append(child)
            self.archive = pareto_front(self.archive, self.entries, self.tasks_train,
                                        self.tasks_held, self.alpha, self.cfg.blind)
            if len(self.archive) > self.cfg.cap:
                self.archive = self.rnd.sample(self.archive, self.cfg.cap)
            if d_tr > self.margin and d_he > self.margin and \
               judge(self.entries, self.tasks_train, child, self.alpha, self.cfg.blind).internal > \
               judge(self.entries, self.tasks_train, self.champion, self.alpha, self.cfg.blind).internal:
                self.champion = child
                adopts += 1
        if self.cfg.monitor:
            if adopts == 0:
                self._stall += 1
                if self._stall >= 5:
                    self.margin = max(0.005, self.margin * 0.5)
                    self._stall = 0
            else:
                self._stall = 0
        reverted = False
        cur = truth(self.entries, self.tasks_train + self.tasks_held, self.champion)
        if self.cfg.audit and g % self.meta.audit_every == 0:
            reverted, _ = self._audit()
            cur = truth(self.entries, self.tasks_train + self.tasks_held, self.champion)
        if g % self.meta.rotate_every == 0:
            self._probe_seed += 17
            self._best_truth = None
            self._best_policy = self.champion
        self.reports.append(type(self.reports[0] if self.reports else None,
                                 (), {})() if False else __import__("kernel").Report(
            generation=g, truth_score=cur, policy=self.champion,
            reverts=1 if reverted else 0, adopts=adopts, budget_spent=self.spent))
    Kernel._run_one = _run_one


def simple(seed, scale, audit, gens=20):
    kk = mk(seed, scale=scale, audit=audit)
    base = truth(kk.entries, kk.tasks_train + kk.tasks_held, Policy())
    kk.run(gens)
    return (truth(kk.entries, kk.tasks_train + kk.tasks_held, kk.champion) - base,
            sum(r.reverts for r in kk.reports))


if __name__ == "__main__":
    print("诊断 1：干净静态世界里的审计收益 + 回退次数")
    for sc in (1.0, 2.0, 3.0):
        ga, ra = statistics.mean(x[0] for x in [simple(s, sc, True) for s in range(16)]), \
                 statistics.mean(x[1] for x in [simple(s, sc, True) for s in range(16)])
        gb, _ = statistics.mean(x[0] for x in [simple(s, sc, False) for s in range(16)]), 0
        print(f"  幅度{sc:.1f}: 有审计{ga:+.4f}(回退{ra:.1f})  无审计{gb:+.4f}  收益{ga-gb:+.4f}")

    print("\n诊断 2：回退是否误伤（审计触发时的真值变化）")
    kk = mk(0, scale=2.0, audit=True)
    kk.run(20)
    revs = [r for r in kk.reports if r.reverts]
    print(f"  总回退 {len(revs)} 次 / {len(kk.reports)} 代")
    print(f"  探针样本数 = {kk.meta.probe_n}，回退阈值 = 0.01")
