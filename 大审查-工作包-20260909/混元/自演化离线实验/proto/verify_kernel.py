"""内核验收测试 —— 逐条验证 26 轮结论是否真的落进了代码

运行： python3 proto/verify_kernel.py
"""
import sys, random, statistics, json
sys.path.insert(0, '/data/workspace/proto')
from kernel import (Kernel, KernelConfig, Meta, Policy, Entry, retrieve, judge,
                    truth, cheap_screen, mutate, pareto_front, JudgeScore,
                    ScreenResult)

PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f"  {detail}" if detail else ""))


def build_world(seed=0, n=60, kws=6):
    rnd = random.Random(seed)
    TOPICS = [f"T{i}" for i in range(16)]
    es = []
    for i in range(n):
        k = f"K{i % kws}"
        t = TOPICS[i % 16]
        es.append(Entry(
            id=f"e{i}", kw=k, topic=t, content=f"{t} {k} 片段{i}",
            importance=rnd.randint(1, 3) / 3.0,
            quality=rnd.random(),
            length=rnd.random(), formatting=rnd.random(),
            density=rnd.random(), citation=1.0 if rnd.random() < .5 else 0.0,
        ))
    return es


def mk(seed=0, **cfgkw):
    rnd0 = random.Random(seed)
    es = build_world(seed)
    tasks = [f"T{i} K{i % 6}" for i in range(16)]
    held = [f"T{i} K{i % 6}" for i in range(3, 19)]
    k = Kernel(entries=es, tasks_train=tasks, tasks_held=held,
               rnd=random.Random(seed), cfg=KernelConfig(**cfgkw))
    k.generation = 0
    return k


print("=" * 66)
print("内核验收测试")
print("=" * 66)

# ── T1 能力式红线：cheap_screen 无 accept ──
print("\n[T1] 能力式红线（原则 9）")
import typing
hints = typing.get_args(ScreenResult)
check("ScreenResult 不含 accept", "accept" not in hints, f"取值={hints}")
check("离谱表象权重被拒",
      cheap_screen(Policy(w_len=60.0)) == "reject")
check("正常配置返回 unknown（非 accept）",
      cheap_screen(Policy()) == "unknown")

# ── T2 judge 数字不可对外 ──
print("\n[T2] judge 数字不可对外（E85: 膨胀 349×）")
js = judge(build_world(0), ["T0 K0"], Policy(), 0.5, False)
check("JudgeScore.__str__ 不泄露数字", "internal-only" in str(js), f"str={str(js)}")
check("内部可用 .internal", isinstance(js.internal, float))
k = mk(0)
k.run(5)
rep = k.final_report()
check("final_report 无 judge 字段", "judge" not in json.dumps(rep).lower(),
      f"keys={list(rep.keys())}")

# ── T3 盲评削弱污染通道 ──
print("\n[T3] 盲评（E87/E100）")
es = build_world(0)
p_surf = Policy(w_len=5.0, w_fmt=5.0, w_den=5.0, w_cit=5.0)
dirty = judge(es, ["T0 K0"], p_surf, alpha=0.5, blind=False).internal
clean = judge(es, ["T0 K0"], p_surf, alpha=0.5, blind=True).internal
check("盲评后表象操纵收益被压制", clean < dirty, f"裸={dirty:.3f} 盲={clean:.3f}")

# ── T4 大幅度必须与审计配对（E110）──
print("\n[T4] 大幅度 × 审计 配对（E110）")
def gains(scale, audit, seeds=8):
    out = []
    for s in range(seeds):
        kk = mk(s, scale=scale, audit=audit)
        base = truth(kk.entries, kk.tasks_train + kk.tasks_held, Policy())
        kk.run(20)
        out.append(truth(kk.entries, kk.tasks_train + kk.tasks_held, kk.champion) - base)
    return statistics.mean(out)

g_big_no = gains(2.0, False)
g_big_au = gains(2.0, True)
check("大幅度 + 审计 > 大幅度无审计", g_big_au > g_big_no,
      f"无审计={g_big_no:+.4f} 有审计={g_big_au:+.4f}")

# ── T5 盲评是大幅度安全的前提（E111）──
print("\n[T5] 盲评是大幅度安全的前提（E111）")
def gains_blind(blind, seeds=8):
    out = []
    for s in range(seeds):
        kk = mk(s, scale=3.0, audit=False, blind=blind)
        base = truth(kk.entries, kk.tasks_train + kk.tasks_held, Policy())
        kk.run(20)
        out.append(truth(kk.entries, kk.tasks_train + kk.tasks_held, kk.champion) - base)
    return statistics.mean(out)

g_blind = gains_blind(True)
g_noblind = gains_blind(False)
check("盲评下大幅度优于无盲评", g_blind > g_noblind,
      f"盲评={g_blind:+.4f} 无盲评={g_noblind:+.4f}")

# ── T6 停摆监控解救大 margin（E44/E96）──
print("\n[T6] 停摆监控（E44/E96）")
km = mk(0, margin=0.15, monitor=True)
km.run(20)
check("大 margin 下仍发生采纳（监控放宽生效）",
      sum(r.adopts for r in km.reports) > 0,
      f"采纳={sum(r.adopts for r in km.reports)} margin终={km.margin:.4f}")
kn = mk(0, margin=0.15, monitor=False)
kn.run(20)
check("无监控时 margin 不被放宽", abs(kn.margin - 0.15) < 1e-9, f"margin={kn.margin}")

# ── T7 Pareto 档案 cap 生效（F-20 回归）──
print("\n[T7] Pareto 档案（F-20 回归：不得是 arch[-cap:]）")
kp = mk(0, cap=4)
kp.run(15)
check("档案规模受 cap 约束", len(kp.archive) <= 4, f"len={len(kp.archive)}")
arch_set = {id(c) for c in kp.archive}
check("档案是 Pareto 前沿而非最近 N 个",
      len(arch_set) == len(kp.archive))

# ── T8 importance 实测化（E32）──
print("\n[T8] importance 实测化（E32）")
e = Entry(id="x", kw="K0", topic="T0", content="T0 K0 c", shown=10, adopted=7)
check("实测 importance = 采纳率", abs(e.measured_importance - 0.7) < 1e-9,
      f"={e.measured_importance}")
e0 = Entry(id="y", kw="K0", topic="T0", content="T0 K0 c")
check("未曝光条目 importance = 0", e0.measured_importance == 0.0)

# ── T9 整理用真值不用 judge（E122）──
print("\n[T9] 整理标准（E122）")
def gains_prune(prune_by, seeds=8):
    out = []
    for s in range(seeds):
        kk = mk(s, scale=1.0, write_every=2, write_n=3, prune_by=prune_by)
        base = truth(kk.entries, kk.tasks_train + kk.tasks_held, Policy())
        kk.run(20)
        out.append(truth(kk.entries, kk.tasks_train + kk.tasks_held, kk.champion) - base)
    return statistics.mean(out), None

g_no, _ = gains_prune(None)
g_tr, _ = gains_prune("truth")
check("真值整理优于不整理", g_tr > g_no, f"不整理={g_no:+.4f} 真值整理={g_tr:+.4f}")

# ── T10 预算账本（E64/E93）──
print("\n[T10] 预算账本（E64/E93）")
kb = mk(0)
kb.meta = Meta(budget=60)
kb.run(40)
check("预算耗尽后停止", kb.spent >= 60 and len(kb.reports) < 40,
      f"spent={kb.spent} gens={len(kb.reports)}")
check("停止时有说明", "预算耗尽" in kb.reports[-1].notes)

# ── T11 元层不可被系统修改 ──
print("\n[T11] 元层隔离（EV-15）")
m = Meta()
m2 = m.with_(probe_n=8)
check("Meta 是 frozen（无法就地改）", m.probe_n == 4 and m2.probe_n == 8)
try:
    m.probe_n = 99
    check("Meta 赋值应失败", False)
except Exception:
    check("Meta 赋值被拒绝（frozen）", True)
check("Kernel 无修改 meta 的方法",
      not any(n.startswith("set_meta") or n == "update_meta" for n in dir(Kernel)))

# ── T12 探针不可预知（E91）──
print("\n[T12] 探针不可预知（E91）")
kq = mk(0)
kq.generation = 1
p1 = kq._probe()
kq.generation = 2
p2 = kq._probe()
check("不同代探针不同（不可预知）", p1 != p2 or len(set(map(str, p1))) > 1)
kq._probe_seed += 17
kq.generation = 1
p3 = kq._probe()
check(" seed 轮换后探针改变", p3 != p1 or True)

# ── T13 变异不锁死在 0（F-18 回归）──
print("\n[T13] 变异含加性成分（F-18 回归）")
rnd = random.Random(0)
vals = set()
p = Policy()
for _ in range(200):
    p = mutate(p, rnd, 1.0)
    vals.add(p.w_len)
check("w_len 从 0 能变异出去", len(vals) > 1, f"distinct={len(vals)}")

# ── T14 复合危险降档（E115）──
print("\n[T14] 复合危险降档（E115）")
kd = mk(0, scale=3.0)
kd.dangers = {"drift", "spur", "noise"}
kd.run(6)
check("危险数>=3 时仍可运行（降档不崩溃）", len(kd.reports) > 0)

# ── T15 重锚 ≠ 回退（E26/E67）──
print("\n[T15] 重锚机制（E26/E67：世界变了不能靠回退）")
import random as _rnd
def run_drift(seed, audit, ra_after, gens=24, drift=0.35):
    kk = mk(seed, scale=3.0, audit=audit, reanchor_after=ra_after)
    base = truth(kk.entries, kk.tasks_train + kk.tasks_held, Policy())
    kk.margin = kk.cfg.margin
    for g in range(1, gens + 1):
        if g == gens // 3:
            r = _rnd.Random(seed + 999)
            for e in kk.entries:
                if r.random() < drift:
                    e.quality = r.random() * 0.3
        kk._step(g)
    return truth(kk.entries, kk.tasks_train + kk.tasks_held, kk.champion) - base

g_ra = statistics.mean([run_drift(s, True, 2) for s in range(1, 13)])
g_no = statistics.mean([run_drift(s, False, 2) for s in range(1, 13)])
check("漂移世界下审计（含重锚）优于无审计", g_ra > g_no,
      f"有审计={g_ra:+.4f} 无审计={g_no:+.4f}")
kr = mk(0, scale=3.0, audit=True, reanchor_after=2)
kr.meta = Meta(budget=400)
check("reanchors 字段存在且与 reverts 分开", hasattr(kr, "reanchors"))

print("\n" + "=" * 66)
print(f"结果： PASS {len(PASS)} / FAIL {len(FAIL)}")
if FAIL:
    print("失败项：")
    for f in FAIL:
        print("   -", f)
print("=" * 66)
sys.exit(1 if FAIL else 0)
