"""E126 —— P0 专项：在【真值信号强】的世界里重测 surf 爆炸

诊断发现（关键）：
  原世界真值信号 sd 仅 0.031 —— 排序几乎学不到东西，
  所以 surf 爆炸的危害被噪声淹没，无法评估任何对策。

本文件构造【强信号世界】：条目新增可观测特征 tf，quality 与 tf 强相关。
这样"把高 tf 条目排前面"是真本事，surf 权重扰乱排序 → 真值明显下降。
"""
import sys, random, statistics
from dataclasses import asdict
sys.path.insert(0, '/data/workspace/proto')
from evolve9 import build_tasks
from evolve20 import Cfg2
from evolve24 import _m, surf_mag, pareto_clean, SURF


def build_world_strong(seed, n=60, kws=6, corr=0.85):
    rnd = random.Random(seed)
    TOPICS = [f"T{i}" for i in range(16)]
    E = []
    for i in range(n):
        k = f"K{i % kws}"
        t = TOPICS[i % 16]
        tf = rnd.random()
        q = corr * tf + (1 - corr) * rnd.random()
        E.append({
            "id": f"e{i}", "kw": k, "topic": t, "keywords": [k],
            "content": f"{t} {k} 片段{i}",
            "importance": rnd.randint(1, 3),
            "age_days": rnd.randint(0, 400),
            "spur": 1 if rnd.random() < 0.5 else 0,
            "true_quality": q,
            "tf": tf,
            "length": rnd.random(),
            "formatting": rnd.random(),
            "kw_density": rnd.random(),
            "has_citation": 1.0 if rnd.random() < .5 else 0.0,
        })
    return E


def retrieve_strong(E, q, c, k=5):
    qw = (q["q"] if isinstance(q, dict) else q).split()
    out = []
    for e in E:
        kh = sum(1 for w in qw if w in e["kw"])
        ch = sum(1 for w in qw if w in e["content"])
        if c.filter_zero and kh == 0 and ch == 0:
            continue
        s = (c.w_kw * kh + c.w_content * ch
             + c.w_imp * e["tf"]
             - c.w_age * (e["age_days"] / 400.0))
        s += (c.w_len * e["length"] + c.w_fmt * e["formatting"]
              + c.w_den * e["kw_density"] + c.w_cit * e["has_citation"])
        out.append((s, e["id"], e))
    out.sort(key=lambda x: (-x[0], x[1]))
    return [x[2] for x in out[:k]]


def tscore(E, task, c):
    rs = retrieve_strong(E, task, c)
    return sum(r["true_quality"] for r in rs) / len(rs) if rs else 0.0


def jscore(E, task, c, eff):
    rs = retrieve_strong(E, task, c)
    if not rs:
        return 0.0
    real = sum(r["true_quality"] for r in rs) / len(rs)
    surf = sum((r["length"] + r["formatting"] + r["kw_density"]
                + r["has_citation"]) / 4.0 for r in rs) / len(rs)
    return eff * real + (1 - eff) * surf


def frac(c):
    tot = abs(c.w_kw) + abs(c.w_content) + abs(c.w_imp) + abs(c.w_age) + surf_mag(c)
    return surf_mag(c) / tot if tot > 0 else 0.0


def strip(c):
    return Cfg2(w_kw=c.w_kw, w_content=c.w_content, w_imp=c.w_imp,
                w_age=c.w_age, w_len=0.0, w_fmt=0.0, w_den=0.0, w_cit=0.0,
                filter_zero=c.filter_zero, deep=c.deep)


def run(seed, d, gens=30, kids=4, alpha=0.5, collect=False):
    rnd = random.Random(seed)
    E = build_world_strong(seed)
    audit = build_tasks(E, random.Random(7777), 40, offset=5)
    root = Cfg2()
    base = _m(tscore(E, t, root) for t in audit)
    eff = 0.95 if d.get("blind", True) else alpha
    scale = d.get("scale", 2.0)
    cap, m, tol = d.get("cap", 8), d.get("margin", 0.02), d.get("tol", 0.04)
    thr = d.get("audit_thr", 0.01)
    mode = d.get("audit_mode", "rolling")
    do_strip = d.get("strip", False)
    surf_cap = d.get("surf_cap", None)
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
        nc = Cfg2(**dd)
        if surf_cap is not None and surf_mag(nc) > surf_cap:
            return c
        return nc

    for g in range(1, gens + 1):
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
            cur = _m(tscore(E, t, strip(main) if do_strip else main) for t in probe)
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
    if collect:
        st["surf"] = surf_mag(main)
        st["frac"] = frac(main)
        st["gain_strip"] = _m(tscore(E, t, strip(main)) for t in audit) - base
        return gain, st
    return gain


BASE = dict(blind=True, audit=True, audit_every=5, scale=2.0,
            cap=8, margin=0.02, tol=0.04)

CFGS = {
    "baseline":     dict(BASE),
    "strict":       dict(BASE, audit_mode="strict"),
    "strip":        dict(BASE, strip=True),
    "strict+strip": dict(BASE, audit_mode="strict", strip=True),
    "cap5":         dict(BASE, surf_cap=5.0),
    "probe16":      dict(BASE, probe_n=16),
    "noaudit":      dict(BASE, audit=False),
}


def e126(seed, name, gens=30):
    return run(seed, CFGS[name], gens=gens, collect=True)


if __name__ == "__main__":
    E = build_world_strong(0)
    audit = build_tasks(E, random.Random(7777), 40, offset=5)
    root = Cfg2()
    base = _m(tscore(E, t, root) for t in audit)
    rnd = random.Random(0)
    zs, hs = [], []
    for i in range(200):
        d = dict(w_kw=rnd.uniform(0, 6), w_content=rnd.uniform(0, 3),
                 w_imp=rnd.uniform(-1, 3), w_age=rnd.uniform(-1, 1))
        if i % 2 == 0:
            zs.append(_m(tscore(E, t, Cfg2(**d)) for t in audit) - base)
        else:
            c = Cfg2(**dict(d, w_len=rnd.uniform(5, 20), w_fmt=rnd.uniform(5, 20),
                            w_den=rnd.uniform(5, 20), w_cit=rnd.uniform(5, 20)))
            hs.append(_m(tscore(E, t, c) for t in audit) - base)
    print("强信号世界 · 随机配置真值分布")
    print("  surf=0 : sd=%.4f  max=%+.4f" % (statistics.pstdev(zs), max(zs)))
    print("  surf高 : mean=%+.4f  sd=%.4f" % (statistics.mean(hs), statistics.pstdev(hs)))
    print("  → 信号强度 sd=%.4f（原世界仅 0.031）" % statistics.pstdev(zs))
