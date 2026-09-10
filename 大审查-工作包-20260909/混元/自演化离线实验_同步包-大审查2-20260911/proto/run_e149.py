"""E149 —— 双故障组合：致命故障会被另一个故障引爆吗？

E148 测了 15 种【单一】故障：只有 judge_invert 让结果变负。
但 E80/E115/E144 反复证明**复合会放大**：
  E144: 2 种危险含 drift → 转负；不含 → 仍有 +0.155

本轮：4 个致命故障 × 其余 14 个 = 56 对（n=10，有防御）

致命故障（E148 判定）：
  judge_invert    judge 好坏颠倒
  mutate_dead     变异算子失效（静止）
  quality_corrupt 质量字段随机损坏
  pareto_degrade  Pareto 退化为取最近（F-20 回归）

判据（协同恶化 / synergy）：
  combo < min(single_A, single_B) − 0.03   → 超可加（1+1>2）
  combo < 0                                → 组合后变负（致命组合）
"""
import sys, os, json, statistics, math, random
sys.path.insert(0, '/data/workspace/proto')
from evolve9 import build_tasks
from evolve20 import Cfg2
from evolve24 import _m, SURF
from evolve31 import build_world_strong, retrieve_strong, tscore

OUT = "/data/workspace/res_e149.json"
N_SEEDS = 10
GENS = 20

FATAL = ("judge_invert", "mutate_dead", "quality_corrupt", "pareto_degrade")
OTHERS = ("baseline", "judge_noise", "judge_saturate", "probe_poison",
          "admit_always", "scale_spike", "entry_lose", "entry_dup",
          "write_explode", "audit_always", "audit_never", "budget_halve")


def run(seed, faults, gens=GENS, kids=4, scale=2.0, tol=0.04, margin=0.0,
        wq=0.9, stress=False):
    """faults: 故障名集合/tuple。defend 恒为 True（测现有架构）"""
    F = set(faults) - {"baseline"}
    rnd = random.Random(seed)
    E = build_world_strong(seed, corr=0.85)
    audit_set = build_tasks(E, random.Random(7777), 40, offset=5)
    root = Cfg2()
    base = _m(tscore(E, t, root) for t in audit_set)
    arch, main, best, btr = [root], root, root, None
    cap = 8
    probe = build_tasks(E, random.Random(4242), 4, offset=7)
    anchor_tasks = build_tasks(E, random.Random(31337), 8, offset=11)
    anchor_hist = []
    drift_at = None
    k_cur = kids
    n_written = 0
    sc_eff = scale * 10 if "scale_spike" in F else scale
    eff = 0.95                      # 盲评
    use_anchor = use_prune = use_audit = True

    def jsc(c, tasks):
        out = []
        for t in tasks:
            rs = retrieve_strong(E, t, c)
            if not rs:
                out.append(0.0); continue
            real = sum(x["true_quality"] for x in rs) / len(rs)
            surf = sum((x["length"] + x["formatting"] + x["kw_density"]
                        + x["has_citation"]) / 4.0 for x in rs) / len(rs)
            v = eff * real + (1 - eff) * surf
            if "judge_noise" in F:
                v += rnd.gauss(0, 0.3)
            if "judge_invert" in F:
                v = 1.0 - v
            if "judge_saturate" in F:
                v = min(v, 0.8)
            out.append(max(0.0, min(1.0, v)))
        return _m(out)

    def jscore(E, t, c):
        return jsc(c, [t])

    def mut(c):
        if "mutate_dead" in F:
            return c
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
                d[p] * (1 + rnd.choice([-0.4, -0.15, 0.2, 0.6]) * sc_eff)
                + rnd.choice([0, 0, 0.5, -0.5]) * sc_eff)), 4)
        return Cfg2(**d)

    def pareto_strong(a, tr, he):
        if "pareto_degrade" in F:
            return a[-cap:]
        pts = [((_m(jscore(E, t, c) for t in tr),
                 _m(jscore(E, t, c) for t in he)), c) for c in a]
        front = []
        for (A, ca) in pts:
            if not any(B[0] >= A[0] and B[1] >= A[1] and (B[0] > A[0] or B[1] > A[1])
                       for (B, _cb) in pts):
                front.append(ca)
        return front or a[-1:]

    for g in range(1, gens + 1):
        if stress and g == gens // 3:
            r = random.Random(seed + 999)
            for e in E:
                if r.random() < 0.30:
                    e["true_quality"] = r.random() * 0.3

        if "entry_lose" in F and g % 3 == 0:
            k = max(1, len(E) // 20)
            E[:] = E[:-k]
        elif "entry_dup" in F and g % 3 == 0:
            k = max(1, len(E) // 20)
            E.extend(E[:k])
        elif "quality_corrupt" in F and g % 4 == 0:
            r = random.Random(seed * 7 + g)
            for e in E:
                if r.random() < 0.1:
                    e["true_quality"] = r.random()

        tr = build_tasks(E, rnd, 16)
        he = build_tasks(E, rnd, 16, offset=3)
        if "probe_poison" in F:
            tr = tr + [f"poison{rnd.randrange(1000)}" for _ in range(4)]

        if "budget_halve" in F and g == gens // 2:
            k_cur = max(1, k_cur // 2)

        for _ in range(k_cur):
            cand = rnd.choice(arch[-3:])
            ch = mut(cand)
            d_tr = jsc(ch, tr) - jsc(cand, tr) + rnd.gauss(0, 0.05)
            d_he = jsc(ch, he) - jsc(cand, he) + rnd.gauss(0, 0.05)
            tol_eff = 1e9 if "admit_always" in F else tol
            if d_tr > -tol_eff:
                arch.append(ch)
            arch = pareto_strong(arch, tr, he)
            if len(arch) > cap:
                arch = (arch[-cap:] if "pareto_degrade" in F
                        else rnd.sample(arch, cap))
            if d_tr > margin and d_he > 0 and jsc(ch, tr) > jsc(main, tr):
                main = ch

        wn = 30 if "write_explode" in F else 3
        for wi in range(wn):
            kw_i = (n_written + wi) % 6
            q = wq * 0.9 + 0.1 + rnd.gauss(0, 0.12)
            E.append({"id": f"w{n_written}", "kw": f"K{kw_i}", "topic": f"T{kw_i}",
                      "keywords": [f"K{kw_i}"], "content": f"w{n_written}",
                      "importance": 2, "age_days": 0, "spur": 0,
                      "true_quality": max(0.0, min(1.0, q)),
                      "tf": max(0.0, min(1.0, q)),
                      "length": 0.6, "formatting": 0.6,
                      "kw_density": 0.6, "has_citation": 0.5})
            n_written += 1

        if use_prune and g % 6 == 0:
            E[:] = [e for e in E if (not e["id"].startswith("w"))
                    or e["true_quality"] > 0.5]

        if use_anchor:
            anchor_hist.append(jsc(root, anchor_tasks))
            if (len(anchor_hist) >= 7
                    and anchor_hist[-1] < sum(anchor_hist[-7:-1]) / 6.0 - 0.02):
                if drift_at is None:
                    drift_at = g
                    k_cur = kids * 4

        if use_audit and g % 5 == 0:
            cur = _m(tscore(E, t, main) for t in probe)
            if "audit_always" in F:
                pass
            elif "audit_never" in F:
                btr, best = cur, main
            else:
                if btr is None:
                    btr, best = cur, main
                elif cur < btr - 0.01:
                    cb = _m(tscore(E, t, best) for t in probe)
                    if cb > cur + 0.01:
                        main, arch = best, [best]
                        btr, best = cb, main
                    else:
                        btr, best = cur, main
                else:
                    btr, best = cur, main

    return _m(tscore(E, t, main) for t in audit_set) - base


# 组合：4 致命 × 12 其他（含 baseline = 致命单独作用）
PAIRS = [(a, b) for a in FATAL for b in OTHERS if a != b]
# 单一故障基线（复用 E148 的 _def 结果，但 stress 一致性需重跑 baseline）
SINGLES = list(FATAL) + [o for o in OTHERS if o != "baseline"]
STRESS_SINGLE = {"baseline", "audit_always", "audit_never", "budget_halve"}


def key(faults, stress):
    return "|".join(sorted(faults)) + ("#S" if stress else "")


def main():
    res = json.load(open(OUT)) if os.path.exists(OUT) else {}

    todo = []
    for s in SINGLES:
        todo.append(((s,), s in STRESS_SINGLE))
    todo.append((("baseline",), True))     # baseline 在 stress 下的单独基准
    for a, b in PAIRS:
        todo.append(((a, b), (a in STRESS_SINGLE) or (b in STRESS_SINGLE)))

    for faults, st in todo:
        k = key(faults, st)
        got = res.get(k, [])
        for s in range(len(got) + 1, N_SEEDS + 1):
            try:
                got.append(run(s, faults, stress=st))
            except Exception as ex:
                print("ERR", k, s, ex)
                break
            res[k] = got
            json.dump(res, open(OUT, "w"))
        del got

    done = sum(1 for v in res.values() if len(v) >= N_SEEDS)
    print(f"进度 {done}/{len(todo)}", flush=True)
    if done < len(todo):
        print("未完成，续跑")
        return

    print("\n" + "=" * 80)
    print(f"E149 双故障组合（n={N_SEEDS}, {GENS} 代，有防御）")
    print("%-16s %-16s %9s %9s %9s %10s" %
          ("致命故障", "叠加故障", "单独", "叠加后", "变化", "判定"))
    rows = []
    for a, b in PAIRS:
        st = (a in STRESS_SINGLE) or (b in STRESS_SINGLE)
        def skey(f):
            if f == "baseline":
                return "baseline#S"
            return key((f,), f in STRESS_SINGLE)
        ka, kb = skey(a), skey(b)
        kc = key((a, b), st)
        sa = statistics.mean(res[ka][:N_SEEDS])
        sb = statistics.mean(res[kb][:N_SEEDS])
        sc = statistics.mean(res[kc][:N_SEEDS])
        mn = min(sa, sb)
        delta = sc - mn
        if sc < 0:
            tag = "⬅变负"
        elif delta < -0.03:
            tag = "⬅超可加"
        elif delta < -0.01:
            tag = "⚠"
        else:
            tag = ""
        rows.append((delta, a, b, sa, sb, sc, tag))
    rows.sort()
    for delta, a, b, sa, sb, sc, tag in rows:
        print("%-16s %-16s %+9.4f %+9.4f %+9.4f %10s"
              % (a, b, min(sa, sb), sc, delta, tag))
    print("=" * 80)
    neg = [r for r in rows if r[5] < 0]
    syn = [r for r in rows if r[0] < -0.03 and r[5] >= 0]
    print(f"变负组合 {len(neg)}/{len(PAIRS)}；超可加（未变负）{len(syn)}")
    for delta, a, b, sa, sb, sc, tag in neg:
        print("  变负： %s + %s = %+.4f（单独 %+.4f / %+.4f）" % (a, b, sc, sa, sb))


if __name__ == "__main__":
    main()
