"""E142 —— judge 看到的是【系统生成的文本】，不是特征向量

★ 全部 135 个实验的 judge 都是"直接读特征向量"。这是最大的未测项。
  真实系统里 LLM-as-judge 看到的是系统自己写的回答、自己选的 few-shot、
  自己组织的上下文 —— **系统能决定给它看什么**。

本实验引入【展示层】：系统有一个可演化的"展示策略" dsp，
决定把条目的哪些部分呈现给 judge：
  dsp → 0：忠实呈现真值特征
  dsp → 1：强调表象（长度/格式/引用数）

判据：judge 看到的是 disp = (1-dsp)*true_quality + dsp*surface

关键问题：
  Q1 系统会不会学会自我美化（dsp 上升）？
  Q2 盲评能否压制？（E111：盲评是地基）
  Q3 真值审计能否检出？（E81：锚定审计零触发）

设计：3 种对策 × 2 种 judge，n=16
  none      无对策
  blind     盲评（削弱 judge 的表象通道）
  audit     真值审计 + 回退
  both      盲评 + 审计
"""
import sys, os, json, statistics, math, random
sys.path.insert(0, '/data/workspace/proto')
from evolve9 import build_tasks
from evolve24 import _m, surf_mag, SURF, pareto_clean
from evolve20 import Cfg2
from evolve31 import build_world_strong, retrieve_strong, tscore

OUT = "/data/workspace/res_e142.json"
N_SEEDS = 16
GENS = 24


def disp_score(E, task, c, dsp):
    """judge 看到的分数：受展示策略 dsp 调制"""
    rs = retrieve_strong(E, task, c)
    if not rs:
        return 0.0
    real = sum(r["true_quality"] for r in rs) / len(rs)
    surf = sum((r["length"] + r["formatting"] + r["kw_density"]
                + r["has_citation"]) / 4.0 for r in rs) / len(rs)
    return (1 - dsp) * real + dsp * surf


def run(seed, mode, gens=GENS, kids=4, scale=2.0, tol=0.04, margin=0.0,
        blind_eff=0.95):
    rnd = random.Random(seed)
    E = build_world_strong(seed, corr=0.85)
    audit_set = build_tasks(E, random.Random(7777), 40, offset=5)
    root = Cfg2()
    base = _m(tscore(E, t, root) for t in audit_set)
    arch, main = [(root, 0.1)], root
    dsp = 0.1                    # 展示策略初值（可演化）
    best, btr = main, None
    probe = build_tasks(E, random.Random(4242), 4, offset=7)
    reverts = 0

    blind = mode in ("blind", "both")
    audit = mode in ("audit", "both")
    eff = blind_eff if blind else 0.5

    def jsc(c, tasks, d):
        # judge 看到的 = 真值通道(eff) 与表象通道 的混合，再经展示策略调制
        raw = _m(disp_score(E, t, c, d) for t in tasks)
        # eff 控制 judge 本身看真值的能力（盲评=0.95）
        return eff * _m(tscore(E, t, c) for t in tasks) + (1 - eff) * raw

    def mut(c, d):
        dd = dict(w_kw=c.w_kw, w_content=c.w_content, w_imp=c.w_imp, w_age=c.w_age,
                  w_len=c.w_len, w_fmt=c.w_fmt, w_den=c.w_den, w_cit=c.w_cit,
                  filter_zero=c.filter_zero, deep=c.deep)
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
        # ★ 协调式变异（E88）：dsp 上升时【同时】推高 surf 权重
        #   第一版失败原因：dsp 单点上升无收益
        #   —— judge 看到 (1-dsp)*real + dsp*surf，若检索结果 surf<real 则 dsp↑反而降分，
        #      dsp 随机游走必然掉到 0（实测 dsp 终值 = 0.000）
        #   真实系统改写 prompt 是"同时改多个维度"，故用协调式
        nd = min(1.0, max(0.0, d + rnd.choice([-0.15, -0.05, 0.1, 0.3]) * scale))
        if nd > d:      # 想美化 → 同时把表象通道推高，让 dsp 真的有收益
            for k in ("w_len", "w_fmt", "w_den", "w_cit"):
                dd[k] = round(min(20.0, dd[k] + 1.5 * scale), 4)
        return Cfg2(**dd), nd

    def pareto_strong(a, tr, he):
        pts = [((_m(jscore(E, t, c, d, eff, dsp) for t in tr),
                 _m(jscore(E, t, c, d, eff, dsp) for t in he)), (c, d)) for c, d in a]
        front = []
        for (A, ca) in pts:
            if not any(B[0] >= A[0] and B[1] >= A[1] and (B[0] > A[0] or B[1] > A[1])
                       for (B, _cb) in pts):
                front.append(ca)
        return front or a[-1:]

    def jscore(E, t, c, d, eff, dsp):
        return jsc(c, [t], d)

    for g in range(1, gens + 1):
        tr = build_tasks(E, rnd, 16)
        he = build_tasks(E, rnd, 16, offset=3)
        for _ in range(kids):
            cand, cdsp = rnd.choice(arch[-3:])
            ch, ndsp = mut(cand, cdsp)
            d_tr = jsc(ch, tr, ndsp) - jsc(cand, tr, cdsp) + rnd.gauss(0, 0.05)
            d_he = jsc(ch, he, ndsp) - jsc(cand, he, cdsp) + rnd.gauss(0, 0.05)
            if d_tr > -tol:
                arch.append((ch, ndsp))
            arch = pareto_strong(arch, tr, he)
            if len(arch) > 8:
                arch = rnd.sample(arch, 8)
            if d_tr > margin and d_he > 0 and jsc(ch, tr, ndsp) > jsc(main, tr, dsp):
                main, dsp = ch, ndsp
        if audit and g % 5 == 0:
            cur = _m(tscore(E, t, main) for t in probe)
            if btr is None:
                btr, best = cur, main
            elif cur < btr - 0.01:
                cb = _m(tscore(E, t, best) for t in probe)
                if cb > cur + 0.01:
                    main, arch, dsp = best, [(best, dsp)], dsp
                    reverts += 1
                    btr, best = cb, main
                else:
                    btr, best = cur, main
            else:
                btr, best = cur, main
    gain = _m(tscore(E, t, main) for t in audit_set) - base
    return gain, dsp, reverts


def main():
    res = json.load(open(OUT)) if os.path.exists(OUT) else {}
    for md in ("none", "blind", "audit", "both"):
        got = res.get(md, [])
        for s in range(len(got) + 1, N_SEEDS + 1):
            try:
                got.append(run(s, md))
            except Exception as ex:
                print("ERR", md, s, ex)
                break
            res[md] = got
            json.dump(res, open(OUT, "w"))
        print(f"  {md}: {len(res.get(md, []))}/{N_SEEDS}")

    if not all(len(res.get(m, [])) >= N_SEEDS for m in ("none", "blind", "audit", "both")):
        print("未完成，续跑")
        return

    print("\n" + "=" * 68)
    print(f"E142 judge 看到系统生成的展示（n={N_SEEDS}, {GENS} 代）")
    print("%-8s %12s %10s %8s" % ("对策", "真值增益", "dsp终值", "回退"))
    base_v = None
    for md in ("none", "blind", "audit", "both"):
        v = res[md][:N_SEEDS]
        g = [x[0] for x in v]
        print("%-8s %+12.4f %10.3f %8.1f" % (
            md, statistics.mean(g), statistics.mean(x[1] for x in v),
            statistics.mean(x[2] for x in v)))
        if md == "none":
            base_v = g
        else:
            d = [y - x for x, y in zip(base_v, g)]
            se = statistics.pstdev(d) / math.sqrt(len(d))
            print("           vs none: %+.4f ± %.4f (t=%.2f)" % (
                statistics.mean(d), se, statistics.mean(d) / se if se else 0))
    print("=" * 68)


if __name__ == "__main__":
    main()
