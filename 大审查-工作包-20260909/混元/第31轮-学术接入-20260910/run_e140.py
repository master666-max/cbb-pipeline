"""E140 —— 动作层接线：split vs split_cd（预注册判据 §三，勿反改）

两臂逐字复刻 evolve35.split（停摆监控每代 + 审计二态判别），唯一差异：
split_cd 在审计时喂 CD（中选检测器，从 res_e139_eval.json 冻结读取），
CD 报警且当期【未判退化】→ 提前重锚（btr/best=cur/main）。
CD 不得覆盖 cur_best 二态判别的回退决定（corrupt 安全检查点）。

与 E135 的实现差异（两臂同受影响，配对内公平）：审计为逐代（E97b：频率>>样本量）。

中选规则（E139 出数前锁定）：文献检测器中 driftg 测试 TPR 最高者；
平手取测试 FPR 更低；再平手取延迟更短；若全部不发（预期 adwin 如此）→ 用 cusum。

审计逐代 → best 每代随 main 刷新（E135 语义保留：非退化审计一律 btr,best=cur,main）。
"""
import sys, os, json, random, statistics, math

HERE = r"D:\临时工作区\大审查-工作包-20260909\混元\第31轮-学术接入-20260910"
SYNC = r"D:\临时工作区\大审查-工作包-20260909\混元\自演化离线实验_同步包-大审查2-20260910\proto"
sys.path.insert(0, SYNC)
sys.path.insert(0, HERE)

from evolve9 import build_tasks          # noqa: E402
from evolve20 import Cfg2                # noqa: E402
from evolve24 import _m, SURF            # noqa: E402
from evolve31 import build_world_strong, tscore, jscore  # noqa: E402
import cdetectors                        # noqa: E402

OUT = os.path.join(HERE, "res_e140.json")
GENS = 24
KIDS = 4
SCENES = ("none", "drift", "driftg", "corrupt")
EVENT_AT = {"none": 8, "drift": 8, "driftg": 10, "corrupt": 8}
N = 44
STALL_K = 3


def pick_detector():
    ev = json.load(open(os.path.join(HERE, "res_e139_eval.json"), encoding="utf-8"))
    streams = json.load(open(os.path.join(HERE, "res_e139_streams.json"), encoding="utf-8"))
    chosen = ev["chosen"]

    def perf(name):
        tpr = fpr = 0
        lat = []
        for s in range(1, N + 1):
            d = cdetectors.make(name, **chosen[name]["params"])
            fire = None
            for g, x in streams[f"driftg_{s}"]["stream"]:
                if d.update(x):
                    fire = g
                    break
            if fire is not None and fire >= EVENT_AT["driftg"]:
                tpr += 1
                lat.append(fire - EVENT_AT["driftg"])
            elif fire is not None:
                fpr += 1
        return (tpr / N, -fpr / N, -(statistics.mean(lat) if lat else 99))

    cands = ["cusum", "ph", "adwin"]
    cands.sort(key=perf, reverse=True)
    winner = cands[0]
    if perf(winner)[0] == 0:
        winner = "cusum"   # 全不响 → 兜底规范检测器（预期 adwin 沉默的情形）
    return winner, chosen[winner]["params"]


def run(seed, scene, arm, cd_params=None):
    rnd = random.Random(seed)
    E = build_world_strong(seed, corr=0.85)
    audit_set = build_tasks(E, random.Random(7777), 40, offset=5)
    root = Cfg2()
    base = _m(tscore(E, t, root) for t in audit_set)
    eff = 0.95
    arch, main, best, btr = [root], root, root, None
    m, tol, cap = 0.02, 0.04, 8
    probe = build_tasks(E, random.Random(4242), 4, offset=7)
    reverts = reanchors = relaxes = cd_early = 0
    stall = 0
    event_at = GENS // 3
    cd = cdetectors.make(cd_params[0], **cd_params[1]) if arm == "split_cd" else None

    def jsc(c, tasks):
        return _m(jscore(E, t, c, eff) for t in tasks)

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
                d[p] * (1 + rnd.choice([-0.4, -0.15, 0.2, 0.6]) * 2.0)
                + rnd.choice([0, 0, 0.5, -0.5]) * 2.0)), 4)
        return Cfg2(**d)

    def pareto_strong(a, tr, he):
        pts = [((_m(jscore(E, t, c, eff) for t in tr),
                 _m(jscore(E, t, c, eff) for t in he)), c) for c in a]
        front = []
        for (A, ca) in pts:
            if not any(B[0] >= A[0] and B[1] >= A[1] and (B[0] > A[0] or B[1] > A[1])
                       for (B, _cb) in pts):
                front.append(ca)
        return front or a[-1:]

    for g in range(1, GENS + 1):
        if g == event_at:
            if scene == "drift":
                r = random.Random(seed + 999)
                for e in E:
                    if r.random() < 0.35:
                        e["true_quality"] = r.random() * 0.3
            elif scene == "corrupt":
                main = Cfg2(w_kw=-2.0, w_content=-1.0, w_imp=-1.0, w_age=1.0,
                            w_len=6.0, w_fmt=6.0, w_den=6.0, w_cit=6.0)
                arch = [main]
        elif scene == "driftg" and g in (10, 15, 20):
            r = random.Random(seed + 1000 + g)
            for e in E:
                if r.random() < 0.10:
                    e["true_quality"] = r.random() * 0.3

        tr = build_tasks(E, rnd, 16)
        he = build_tasks(E, rnd, 16, offset=3)
        adopts = 0
        for _ in range(KIDS):
            cand = rnd.choice(arch[-3:])
            ch = mut(cand)
            d_tr = jsc(ch, tr) - jsc(cand, tr) + rnd.gauss(0, 0.05)
            d_he = jsc(ch, he) - jsc(cand, he) + rnd.gauss(0, 0.05)
            if d_tr > -tol:
                arch.append(ch)
            arch = pareto_strong(arch, tr, he)
            if len(arch) > cap:
                arch = rnd.sample(arch, cap)
            if d_tr > m and d_he > m and jsc(ch, tr) > jsc(main, tr):
                main = ch
                adopts += 1

        # 停摆监控（每代，split 两臂同）
        if adopts == 0:
            stall += 1
        else:
            stall = 0
        if stall >= STALL_K:
            m = max(0.005, m * 0.5)
            relaxes += 1
            stall = 0

        # 审计（逐代；CD 每次审计恰好喂一次读数，但其报警只在未退化时生效）
        cur = _m(tscore(E, t, main) for t in probe)
        if btr is None:
            btr, best = cur, main
            continue
        fired = cd.update(cur) if cd is not None else False
        degraded = cur < btr - 0.01
        if degraded:
            cur_best = _m(tscore(E, t, best) for t in probe)
            if cur_best > cur + 0.01:          # failure → 回退（CD 不得覆盖）
                main, arch = best, [best]
                reverts += 1
            else:                               # drift → 重锚
                reanchors += 1
        else:
            if fired:                           # CD 报警且未退化 → 提前重锚
                cd_early += 1
        btr, best = cur, main

    gain = _m(tscore(E, t, main) for t in audit_set) - base
    return [round(gain, 6), {"reverts": reverts, "reanchors": reanchors,
                             "relaxes": relaxes, "cd_early": cd_early}]


def main():
    name, params = pick_detector()
    print(f"中选检测器（预注册规则冻结）：{name} {params}")
    res = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
    keys = [f"{sc}_{arm}" for sc in SCENES for arm in ("split", "split_cd")]
    for k in keys:
        sc, arm = k.split("_", 1)
        got = res.get(k, [])
        for s in range(len(got) + 1, N + 1):
            try:
                got.append(run(s, sc, arm, cd_params=(name, params)))
            except Exception as ex:
                print("ERR", k, s, ex)
                break
            res[k] = got
            json.dump(res, open(OUT, "w"))
        print(f"  {k}: {len(res.get(k, []))}/{N}")

    if not all(len(res.get(k, [])) >= N for k in keys):
        print("未完成，重跑续传")
        return

    print("\n" + "=" * 84)
    print(f"E140 动作层（配对 n={N}，检测器={name} {params}）")
    print("%-8s %10s %10s %22s %8s %8s %8s %8s" %
          ("场景", "split", "split_cd", "Δ (cd−split) 均值±se (t)", "回退s", "重锚s", "早锚cd", "放宽s"))
    for sc in SCENES:
        a = [x[0] for x in res[f"{sc}_split"][:N]]
        b = [x[0] for x in res[f"{sc}_split_cd"][:N]]
        diff = [y - x for x, y in zip(a, b)]
        m_ = statistics.mean(diff)
        se = statistics.pstdev(diff) / math.sqrt(len(diff))
        ca = res[f"{sc}_split"][:N]
        cb = res[f"{sc}_split_cd"][:N]
        rv = statistics.mean(x[1]["reverts"] for x in cb)
        ra = statistics.mean(x[1]["reanchors"] for x in cb)
        ce = statistics.mean(x[1]["cd_early"] for x in cb)
        rl = statistics.mean(x[1]["relaxes"] for x in cb)
        print("%-8s %+10.4f %+10.4f   %+10.4f±%.4f (t=%+.2f)  %8.1f %8.1f %8.1f %8.1f" %
              (sc, statistics.mean(a), statistics.mean(b), m_, se,
               m_ / se if se else 0, rv, ra, ce, rl))
    print("=" * 84)


if __name__ == "__main__":
    main()
