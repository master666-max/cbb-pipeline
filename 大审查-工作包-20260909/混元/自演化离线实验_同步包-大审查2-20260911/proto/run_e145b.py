"""E145b —— drift 应对：检出之后该做什么？

E145a 证明 judge_jump 能 88% 检出 drift 且零误报（免费）。
本轮问：**检出后做什么？**（E134 判别式重锚已被证明不够，第 35 轮 −0.070）

策略：
  never     不应对（基线）
  reanchor  E134 判别式重锚（重置审计基线，保留配置与档案）
  fresh     检出后【清空档案，从当前配置重新演化】
             —— E124 已证冷启动起点差不致命，故"重新起跑"可能优于"背着旧档案"
  shorten   检出后【只用近期任务训练】（滑动窗口，丢弃旧数据）
             —— 但 E14c 证明近因加权在"评判者被塑造"时是毒，需验证
  multi     检出后【并行保留新旧两个主线】，按近期表现择一
             —— E135 split 思路的延伸

检测：全部用 judge_jump（E145a 证实 88%/0%）

设计：n=20，drift 在 g=8 注入
"""
import sys, os, json, statistics, math, random
sys.path.insert(0, '/data/workspace/proto')
from evolve9 import build_tasks
from evolve20 import Cfg2
from evolve24 import _m, SURF
from evolve31 import build_world_strong, retrieve_strong, tscore

OUT = "/data/workspace/res_e145b.json"
N_SEEDS = 20
GENS = 24
DRIFT_AT = 8


def run(seed, mode, gens=GENS, kids=4, scale=2.0, tol=0.04, margin=0.0,
        eff=0.95, drift=0.35, write=False, wq=0.2):
    rnd = random.Random(seed)
    E = build_world_strong(seed, corr=0.85)
    audit_set = build_tasks(E, random.Random(7777), 40, offset=5)
    root = Cfg2()
    base = _m(tscore(E, t, root) for t in audit_set)
    arch, main = [root], root
    cap = 8
    probe = build_tasks(E, random.Random(4242), 4, offset=7)
    btr, best = None, root
    judge_hist = []
    detected_at = None
    recent_pool = []
    alt_main = None          # multi：平行主线
    alt_score = None

    def jsc(c, tasks):
        out = []
        for t in tasks:
            rs = retrieve_strong(E, t, c)
            if not rs:
                out.append(0.0); continue
            real = sum(x["true_quality"] for x in rs) / len(rs)
            surf = sum((x["length"] + x["formatting"] + x["kw_density"]
                        + x["has_citation"]) / 4.0 for x in rs) / len(rs)
            out.append(eff * real + (1 - eff) * surf)
        return _m(out)

    def jscore(E, t, c):
        return jsc(c, [t])

    def mut(c):
        d = dict(w_kw=c.w_kw, w_content=c.w_content, w_imp=c.w_imp, w_age=c.w_age,
                 w_len=c.w_len, w_fmt=c.w_fmt, w_den=c.w_den, w_cit=c.w_cit,
                 filter_zero=c.filter_zero, deep=c.deep)
        r = rnd.random()
        if r < 0.08:
            d["deep"] = 1 - d["deep"]
        elif r < 0.16:
            d["filter_zero"] = 1 - d["filter_zero"]
        else:
            p = rnd.choice(["w_kw", "w_content", "w_imp", "w_age"] + list(SURF))
            d[p] = round(max(-5.0, min(20.0,
                d[p] * (1 + rnd.choice([-0.4, -0.15, 0.2, 0.6]) * scale)
                + rnd.choice([0, 0, 0.5, -0.5]) * scale)), 4)
        return Cfg2(**d)

    def pareto_strong(a, tr, he):
        pts = [((_m(jscore(E, t, c) for t in tr),
                 _m(jscore(E, t, c) for t in he)), c) for c in a]
        front = []
        for (A, ca) in pts:
            if not any(B[0] >= A[0] and B[1] >= A[1] and (B[0] > A[0] or B[1] > A[1])
                       for (B, _cb) in pts):
                front.append(ca)
        return front or a[-1:]

    for g in range(1, gens + 1):
        if g == DRIFT_AT:
            r = random.Random(seed + 999)
            for e in E:
                if r.random() < drift:
                    e["true_quality"] = r.random() * 0.3

        tr = build_tasks(E, rnd, 16)
        he = build_tasks(E, rnd, 16, offset=3)
        if mode == "shorten" and detected_at is not None:
            recent_pool.append(tr)
            if len(recent_pool) > 4:
                recent_pool.pop(0)
            tr = [t for sub in recent_pool for t in sub] or tr

        for _ in range(kids):
            cand = rnd.choice(arch[-3:])
            ch = mut(cand)
            d_tr = jsc(ch, tr) - jsc(cand, tr) + rnd.gauss(0, 0.05)
            d_he = jsc(ch, he) - jsc(cand, he) + rnd.gauss(0, 0.05)
            if d_tr > -tol:
                arch.append(ch)
            arch = pareto_strong(arch, tr, he)
            if len(arch) > cap:
                arch = rnd.sample(arch, cap)
            if d_tr > margin and d_he > 0 and jsc(ch, tr) > jsc(main, tr):
                main = ch

        # ── 危险：低质量自写入 ──
        if write:
            for wi in range(3):
                kw_i = (g * 3 + wi) % 6
                q = wq * 0.9 + (1 - wq) * 0.1 + rnd.gauss(0, 0.12)
                E.append({"id": f"w{g}_{wi}", "kw": f"K{kw_i}", "topic": f"T{kw_i}",
                          "keywords": [f"K{kw_i}"], "content": f"w{g}_{wi}",
                          "importance": 2, "age_days": 0, "spur": 0,
                          "true_quality": max(0.0, min(1.0, q)),
                          "tf": max(0.0, min(1.0, q)),
                          "length": 0.95, "formatting": 0.95,
                          "kw_density": 0.95, "has_citation": 1.0})

        # ── 危险：低质量自写入 ──
        if write:
            for wi in range(3):
                kw_i = (g * 3 + wi) % 6
                q = wq * 0.9 + (1 - wq) * 0.1 + rnd.gauss(0, 0.12)
                E.append({"id": f"w{g}_{wi}", "kw": f"K{kw_i}", "topic": f"T{kw_i}",
                          "keywords": [f"K{kw_i}"], "content": f"w{g}_{wi}",
                          "importance": 2, "age_days": 0, "spur": 0,
                          "true_quality": max(0.0, min(1.0, q)),
                          "tf": max(0.0, min(1.0, q)),
                          "length": 0.95, "formatting": 0.95,
                          "kw_density": 0.95, "has_citation": 1.0})

        # ── 检测：judge 评分跳变（E145a：88%/0%）──
        cur_j = jsc(main, tr)
        judge_hist.append(cur_j)
        if detected_at is None and len(judge_hist) >= 7:
            pre = statistics.mean(judge_hist[-7:-1])
            if cur_j < pre - 0.02:
                detected_at = g
                if mode == "fresh":
                    arch = [main]           # 清空档案，从当前配置重新起跑
                elif mode == "multi":
                    alt_main, alt_score = main, cur_j

        # ── multi：平行主线按近期表现择一 ──
        if mode == "multi" and alt_main is not None and g % 3 == 0:
            s_cur = jsc(main, tr)
            s_alt = jsc(alt_main, tr)
            if s_alt > s_cur:
                main, alt_main = alt_main, main

        # ── reanchor：重置审计基线（E134 简化）──
        if mode == "reanchor" and g % 5 == 0:
            cur = _m(tscore(E, t, main) for t in probe)
            if btr is None:
                btr, best = cur, main
            elif cur < btr - 0.01:
                btr, best = cur, main      # 重锚：不回退
            else:
                btr, best = cur, main

    gain = _m(tscore(E, t, main) for t in audit_set) - base
    return gain, (detected_at or -1)


def main():
    res = json.load(open(OUT)) if os.path.exists(OUT) else {}
    import sys as _s
    scen = _s.argv[1] if len(_s.argv) > 1 else "solo"
    DO_WRITE = (scen == "multi_danger")
    DO_SURF = (scen == "multi_danger")
    modes = ("never", "reanchor", "fresh", "shorten", "multi")
    for md in modes:
        k = f"{scen}_{md}"
        got = res.get(k, [])
        for s in range(len(got) + 1, N_SEEDS + 1):
            try:
                got.append(run(s, md, write=DO_WRITE,
                               eff=(0.5 if DO_SURF else 0.95)))
            except Exception as ex:
                print("ERR", md, s, ex)
                break
            res[k] = got
            json.dump(res, open(OUT, "w"))
        print(f"  {k}: {len(res.get(k, []))}/{N_SEEDS}")

    if not all(len(res.get(f"{scen}_{m}", [])) >= N_SEEDS for m in modes):
        print("未完成，续跑")
        return

    print("\n" + "=" * 70)
    print(f"E145b drift 应对策略（场景={scen}, n={N_SEEDS}）")
    print("%-10s %10s %10s %14s" % ("策略", "真值增益", "检出代", "vs never"))
    nv = [x[0] for x in res[f"{scen}_never"][:N_SEEDS]]
    for md in modes:
        v = [x[0] for x in res[f"{scen}_{md}"][:N_SEEDS]]
        det = [x[1] for x in res[f"{scen}_{md}"][:N_SEEDS]]
        line = "%-10s %+10.4f %10.1f" % (md, statistics.mean(v),
                                         statistics.mean(d for d in det if d > 0) if any(d > 0 for d in det) else -1)
        if md != "never":
            d = [y - x for x, y in zip(nv, v)]
            se = statistics.pstdev(d) / math.sqrt(len(d))
            line += "  %+.4f ± %.4f (t=%.2f)" % (
                statistics.mean(d), se, statistics.mean(d) / se if se else 0)
        print(line)
    print("=" * 70)


if __name__ == "__main__":
    main()
