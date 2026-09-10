"""R28-E131 · P0-1 重测：strict 审计模式在「审计真的会触发」的世界里是否有效？

背景（第二十七轮 6.2 行动项 P0-1）：
  E127 中 strict 与 danger 逐位相同，当时判"strict 完全无效"。
  但回退仅 0.5 次/10 种子——审计根本没机会触发，这可能是假阴性（测量工具局限≠对象性质）。

预注册设计（先锁判据再跑，PT-012 纪律）：
  载体：evolve31 强信号世界（corr=0.85）+ 非盲评（alpha=0.5，危险场景）+ scale=2.0
  漂移：世界层持续漂移——从 g=8 起，每 5 代以概率 p=0.4 独立重洗每条目 true_quality
        （tf 不变 → 演化学到的旧信号失效；漂移序列由 Random(seed*1000+7) 驱动，
         与策略随机流隔离，四组配置同种子共享同一漂移实现 → 配对公平）
  配置（4 组 × 24 种子 × 25 代，同种子配对）：
    rolling   audit=True,  audit_mode=rolling（现状默认）
    strict    audit=True,  audit_mode=strict
    noaudit   audit=False
    blind     blind=True（盲评对照，roll 配对基线）
  前提检查（场景成立判据，预注册）：
    rolling 组回退次数均值 >= 2.0 次/24 种子。若不成立，本次"strict 无效"复测无效，
    需加大漂移重跑（如实登记，不得悄悄换参数）。
  主判据：strict - rolling 的真值增益配对差，报 均值±se、t、n（第二十七轮新基线格式）
  副判据：rolling - noaudit（审计在漂移世界的收益，E110 配对效应的漂移场景版）

输出：res_r28_e131.json（逐 seed 落盘，可续跑）
"""
import sys, random, statistics, math, json, os
from dataclasses import asdict
sys.path.insert(0, '/data/workspace/proto')
from evolve9 import build_tasks
from evolve20 import Cfg2
from evolve24 import _m, surf_mag, pareto_clean, SURF
import evolve31
from evolve31 import (build_world_strong, retrieve_strong, tscore, jscore,
                      frac, strip, BASE)

RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'res_r28_e131.json')

DRIFT_EVERY = 5
DRIFT_P = 0.4
DRIFT_FROM = 8
GENS = 25
SEEDS = list(range(1, 25))   # 24 种子（>20，第二十七轮新基线）


def drift_world(E, rnd_drift):
    for e in E:
        if rnd_drift.random() < DRIFT_P:
            e["true_quality"] = rnd_drift.random()


def run_drift(seed, d, gens=GENS, kids=4, alpha=0.5):
    """与 evolve31.run 同构的主循环，仅插入世界层漂移钩子。"""
    rnd = random.Random(seed)
    rnd_drift = random.Random(seed * 1000 + 7)      # 策略无关的漂移流
    E = build_world_strong(seed)
    audit = build_tasks(E, random.Random(7777), 40, offset=5)
    root = Cfg2()
    base = _m(tscore(E, t, root) for t in audit)
    eff = 0.95 if d.get("blind", True) else alpha
    scale = d.get("scale", 2.0)
    cap, m, tol = d.get("cap", 8), d.get("margin", 0.02), d.get("tol", 0.04)
    thr = d.get("audit_thr", 0.01)
    mode = d.get("audit_mode", "rolling")
    probe = build_tasks(E, random.Random(4242), d.get("probe_n", 4), offset=7)

    arch, main, best, btr = [root], root, root, None
    st = {"reverts": 0, "audits": 0}

    def jsc(c, tasks):
        return _m(jscore(E, t, c, eff) for t in tasks)

    def pareto_strong(a):
        pts = [((_m(jscore(E, t, c, eff) for t in tr),
                 _m(jscore(E, t, c, eff) for t in he)), c) for c in a]
        front = []
        for (A, ca) in pts:
            if not any(B[0] >= A[0] and B[1] >= A[1] and (B[0] > A[0] or B[1] > A[1])
                       for (B, _cb) in pts):
                front.append(ca)
        return front or a[-1:]

    def mut(c):
        dd = asdict(c)
        r = rnd.random()
        if r < 0.08:
            dd["deep"] = 1 - dd["deep"]
        elif r < 0.16:
            dd["filter_zero"] = 1 - dd["filter_zero"]
        else:
            p = rnd.choice(["w_kw", "w_content", "w_imp", "w_age"] + list(SURF))
            dd[p] = round(max(-5.0, min(20.0,
                dd[p] * (1 + rnd.choice([-0.4, -0.15, 0.2, 0.6]) * scale)
                + rnd.choice([0, 0, 0.5, -0.5]) * scale)), 4)
        return Cfg2(**dd)

    for g in range(1, gens + 1):
        if g >= DRIFT_FROM and (g - DRIFT_FROM) % DRIFT_EVERY == 0:
            drift_world(E, rnd_drift)
        tr = build_tasks(E, rnd, 16)
        he = build_tasks(E, rnd, 16, offset=3)
        for _ in range(kids):
            cand = rnd.choice(arch[-3:])
            ch = mut(cand)
            d_tr = jsc(ch, tr) - jsc(cand, tr) + rnd.gauss(0, 0.05)
            d_he = jsc(ch, he) - jsc(cand, he) + rnd.gauss(0, 0.05)
            if d_tr > -tol:
                arch.append(ch)
            arch = pareto_strong(arch)
            if len(arch) > cap:
                arch = rnd.sample(arch, cap)
            if d_tr > m and d_he > m and jsc(ch, tr) > jsc(main, tr):
                main = ch
        if d.get("audit", True) and g % d.get("audit_every", 5) == 0:
            st["audits"] += 1
            cur = _m(tscore(E, t, main) for t in probe)
            if btr is None:
                btr, best = cur, main
            elif cur < btr - thr:
                main, arch = best, [best]
                st["reverts"] += 1
                if mode == "rolling":
                    btr, best = cur, main
            else:
                if mode == "strict":
                    if cur > btr:
                        btr, best = cur, main
                else:
                    btr, best = cur, main
    gain = _m(tscore(E, t, main) for t in audit) - base
    st["surf"] = surf_mag(main)
    st["frac"] = frac(main)
    return gain, st


CFGS = {
    "rolling": dict(BASE, blind=False),
    "strict":  dict(BASE, blind=False, audit_mode="strict"),
    "noaudit": dict(BASE, blind=False, audit=False),
    "blind":   dict(BASE, blind=True),
}


def load():
    if os.path.exists(RES):
        with open(RES, encoding='utf-8') as f:
            return json.load(f)
    return {}


def main():
    res = load()
    for nm, cfg in CFGS.items():
        res.setdefault(nm, {})
        for s in SEEDS:
            if str(s) in res[nm]:
                continue
            g, st = run_drift(s, cfg)
            res[nm][str(s)] = {"gain": g, **st}
            with open(RES, 'w', encoding='utf-8') as f:
                json.dump(res, f, ensure_ascii=False, indent=1)
    # ---- 统计（配对，第二十七轮新格式）----
    def arr(nm, key="gain"):
        return [res[nm][str(s)][key] for s in SEEDS]

    def paired(a, b, la, lb):
        da = arr(a); db = arr(b)
        diff = [x - y for x, y in zip(da, db)]
        n = len(diff)
        m_ = statistics.mean(diff); sd_ = statistics.pstdev(diff)
        se_ = sd_ / math.sqrt(n) if n else float('nan')
        t_ = m_ / se_ if se_ else float('nan')
        print("  %s - %s: %+0.4f ± %.4f (sd %.4f, t=%.2f, n=%d)"
              % (la, lb, m_, se_, sd_, t_, n))

    print("R28-E131 · strict 重测（强信号+非盲评+持续漂移, %d 种子, %d 代）" % (len(SEEDS), GENS))
    print("前提检查（场景成立）：")
    for nm in CFGS:
        rv = arr(nm, "reverts"); ad = arr(nm, "audits")
        print("  %-8s 回退均值 %.2f  审计执行 %.2f  回退>0的种子 %d/%d"
              % (nm, statistics.mean(rv), statistics.mean(ad),
                 sum(1 for x in rv if x > 0), len(rv)))
    print("主判据：")
    paired("strict", "rolling", "strict", "rolling")
    print("副判据：")
    paired("rolling", "noaudit", "rolling", "noaudit")
    print("参考配对：")
    paired("blind", "rolling", "blind", "rolling")
    for nm in CFGS:
        print("  %-8s gain %+0.4f (sd %.4f)  frac %.1f%%"
              % (nm, statistics.mean(arr(nm)), statistics.pstdev(arr(nm)),
                 statistics.mean(arr(nm, "frac")) * 100))


if __name__ == "__main__":
    main()
