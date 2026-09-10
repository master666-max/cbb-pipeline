"""E147 —— 参数极端化报警 + 通道隔离（预注册 §二，勿反改）

世界 = E146 偏见世界。报警：任一 SC2 通道 |w|>=8 → 主配置该通道复位到 root 值（一次）。
臂：quarantine（偏见无盲评+隔离）/ quarantine_blind（偏见+盲评+隔离）；
对照复用 E146 存档 bias / bias_blind / base（同种子同节拍）。
"""
import sys, os, json, statistics, math, random

HERE = r"D:\临时工作区\大审查-工作包-20260909\混元\第35轮-极端化报警与一致性探针-20260910"
R34 = r"D:\临时工作区\大审查-工作包-20260909\混元\第34轮-正交组合与通道缠绕-20260910"
SYNC = r"D:\临时工作区\大审查-工作包-20260909\混元\自演化离线实验_同步包-大审查2-20260910\proto"
sys.path.insert(0, SYNC)
sys.path.insert(0, HERE)

from evolve9 import build_tasks          # noqa: E402
from evolve20 import Cfg2                # noqa: E402
from evolve24 import _m, SURF            # noqa: E402
from evolve31 import build_world_strong, tscore, jscore  # noqa: E402

OUT = os.path.join(HERE, "res_e147.json")
N = 44
ARMS = ("quarantine", "quarantine_blind")
ROOT_DEFAULTS = dict(w_kw=3.0, w_content=1.0, w_imp=1.0, w_age=0.1,
                     w_len=0.0, w_fmt=0.0, w_den=0.0, w_cit=0.0)
ALARM_THR = 8.0


def run(seed, arm):
    rnd = random.Random(seed)
    E = build_world_strong(seed, corr=0.85)
    audit_set = build_tasks(E, random.Random(7777), 40, offset=5)
    root = Cfg2()
    base = _m(tscore(E, t, root) for t in audit_set)
    blind = arm.endswith("blind")
    eff = 0.95 if blind else 0.5
    kr = random.Random(seed + 555)
    kappa = {e["id"]: max(0.0, kr.gauss(0.15, 0.03))
             for e in E if kr.random() < 0.40}

    def jsc(c, tasks):
        return _m(jscore(E, t, c, eff) + kappa.get(t["golden"], 0.0) * c.w_kw
                  for t in tasks)

    arch, main = [root], root
    m, tol, cap = 0.02, 0.04, 8
    alarms = 0
    quarantined = set()

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

    for g in range(1, 25):
        tr = build_tasks(E, rnd, 16)
        he = build_tasks(E, rnd, 16, offset=3)
        for _ in range(4):
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

        # 参数极端化报警 → 该通道复位到 root（一次，可重复触发不同通道）
        d = dict(w_kw=main.w_kw, w_content=main.w_content, w_imp=main.w_imp,
                 w_age=main.w_age, w_len=main.w_len, w_fmt=main.w_fmt,
                 w_den=main.w_den, w_cit=main.w_cit, filter_zero=main.filter_zero,
                 deep=main.deep)
        hit = False
        for c in ROOT_DEFAULTS:
            if abs(d[c]) >= ALARM_THR:
                d[c] = ROOT_DEFAULTS[c]
                alarms += 1
                hit = True
        if hit:
            main = Cfg2(**d)
            arch = [main]

    gain = _m(tscore(E, t, main) for t in audit_set) - base
    surf = sum(abs(getattr(main, w)) for w in SURF)
    return [round(gain, 6), round(surf, 4), main.w_kw, alarms]


def main():
    res = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
    for arm in ARMS:
        got = res.get(arm, [])
        for s in range(len(got) + 1, N + 1):
            try:
                got.append(run(s, arm))
            except Exception as ex:
                print("ERR", arm, s, ex)
                break
            res[arm] = got
            json.dump(res, open(OUT, "w"))
        print(f"  {arm}: {len(got)}/{N}")
    if not all(len(res.get(a, [])) >= N for a in ARMS):
        print("未完成，重跑续传")
        return

    e146 = json.load(open(os.path.join(
        R34, "res_e146.json"), encoding="utf-8"))
    print("\n" + "=" * 92)
    print(f"E147 · 参数极端化报警+通道隔离（配对 n={N}，阈值 |w|>={ALARM_THR}）")
    print("%-18s %12s %14s %10s %8s" % ("臂", "真值增益", "表象幅度", "终局w_kw", "报警"))
    rows = {}
    for arm, src in (("base", e146["base"]), ("bias", e146["bias"]),
                     ("bias_blind", e146["bias_blind"]),
                     ("quarantine", res["quarantine"]),
                     ("quarantine_blind", res["quarantine_blind"])):
        v = [x[0] for x in src]
        sf = statistics.mean(x[1] for x in src)
        kw = statistics.mean(x[2] for x in src)
        al = statistics.mean(x[3] for x in src) if arm.startswith("quar") else 0.0
        rows[arm] = v
        print("%-18s %+12.4f %14.3f %10.3f %8.1f" % (arm, statistics.mean(v), sf, kw, al))
    for a, b in (("bias", "quarantine"), ("bias_blind", "quarantine_blind")):
        diff = [y - x for x, y in zip(rows[a], rows[b])]
        m_ = statistics.mean(diff)
        se = statistics.pstdev(diff) / math.sqrt(len(diff))
        print("  %s − %s = %+0.4f ± %.4f (t=%+.2f)" % (b, a, m_, se, m_ / se if se else 0))
    print("=" * 92)


if __name__ == "__main__":
    main()
