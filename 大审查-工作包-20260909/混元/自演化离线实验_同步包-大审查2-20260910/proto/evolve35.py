"""E135 —— 四态判别 + 状态依赖动作（打通 E12 → E133/E134）

E12 证明四态判别器 36/36 正确，但只做【离线分类】，没接进动作选择。
E133/E134 证明【动作的价值取决于退化原因】（corrupt +0.179 / drift −0.080）。
本实验打通：判别 → 动作。

四态：
  converged 收敛   —— 正常演化中，无需干预
  stuck     卡住   —— 适应度低谷，需要【放宽门槛】跨越
  drift     漂移   —— 世界变了，需要【重锚】
  failure   失败   —— 配置跑飞，需要【回退】

★ 关键设计：E12 的教训是"构造与判别器必须对齐"。
  本实验所有场景都用【同一套状态注入函数】保证语义一致。

状态注入（scene）：
  none     不注入 → converged
  drift    重洗条目质量 → drift
  corrupt  强制 champion 变差 → failure
  stuck    注入欺骗地形（局部最优 0.50，全局 0.90，中间隔低谷）→ stuck

判别器输入（系统可见，不含真值）：
  1. adopts     本代采纳次数（0 = 完全停摆）
  2. trend      近期真值审计读数的斜率
  3. recov      回退后是否恢复（回退是否有效）
  4. judge_gap  judge 自报改进 vs 审计读数改进的差（E14/E85 膨胀）

判据（与 E12 一致 + 动作化）：
  adopts==0 持续          → stuck     → 放宽 margin
  trend<0 且 recov 失败   → drift     → 重锚
  trend<0 且 recov 成功   → failure   → 回退
  否则                    → converged → 不动

对照：
  oracle      用真值直接告知状态（上界）
  diagnose    判别器驱动
  naive       无条件回退（当前基线）
  never       从不干预
"""
import sys, os, json, statistics, math, random
from typing import List, Optional, Dict, Tuple
sys.path.insert(0, '/data/workspace/proto')
from evolve9 import build_tasks
from evolve20 import Cfg2
from evolve24 import _m, SURF
from evolve31 import build_world_strong, retrieve_strong, tscore, jscore

OUT = "/data/workspace/res_e135.json"
N_PAIRS = 22   # 沙盒不稳，从 44 降到 22（本轮效应量大，足够）
GENS = 24
KIDS = 4
STATES = ("converged", "stuck", "drift", "failure")
STALL_K = 3          # 连续 N 代零采纳 → 判 stuck


# ────────────────────────── 世界 ──────────────────────────
def build_world_deceptive(seed, n=60, kws=6):
    """欺骗地形：0.50 局部最优，0.90 全局最优，中间隔低谷（E7 同款）"""
    rnd = random.Random(seed)
    E = build_world_strong(seed, n=n, kws=kws, corr=0.85)
    # 造低谷：让中间质量区间的条目质量压低
    for e in E:
        if 0.45 < e["true_quality"] < 0.75:
            e["true_quality"] = 0.30 + 0.1 * rnd.random()
    return E


def inject(E, seed, scene, rnd_state):
    if scene == "drift":
        r = random.Random(seed + 999)
        for e in E:
            if r.random() < 0.35:
                e["true_quality"] = r.random() * 0.3
    elif scene == "corrupt":
        pass   # 在 run 里替换 champion
    return E


# ────────────────────────── 演化 ──────────────────────────
def run(seed: int, scene: str, mode: str, gens: int = GENS, kids: int = KIDS,
        blind: bool = True, scale: float = 2.0, collect: bool = False):
    rnd = random.Random(seed)
    # ★ stuck 必须用正常世界：deceptive 世界下系统连 root 都无法改进
    #   （实测 adopts 全 0，main 恒为 root → 所有策略 gain 逐位相同）
    E = build_world_strong(seed, corr=0.85)
    audit_set = build_tasks(E, random.Random(7777), 40, offset=5)
    root = Cfg2()
    base = _m(tscore(E, t, root) for t in audit_set)
    eff = 0.95 if blind else 0.5
    arch, main, best, btr = [root], root, root, None
    m, tol, cap = 0.02, 0.04, 8
    probe = build_tasks(E, random.Random(4242), 4, offset=7)
    reverts = reanchors = relaxes = 0
    stall = 0
    hist: List[float] = []
    event_at = gens // 3
    guessed: List[str] = []

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
                d[p] * (1 + rnd.choice([-0.4, -0.15, 0.2, 0.6]) * scale)
                + rnd.choice([0, 0, 0.5, -0.5]) * scale)), 4)
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

    for g in range(1, gens + 1):
        if g == event_at:
            if scene == "drift":
                inject(E, seed, "drift", None)
            elif scene == "corrupt":
                main = Cfg2(w_kw=-2.0, w_content=-1.0, w_imp=-1.0, w_age=1.0,
                            w_len=6.0, w_fmt=6.0, w_den=6.0, w_cit=6.0)
                arch = [main]
            elif scene == "stuck":
                # ★ 卡住 = 想动但门槛太高动不了（E44/E96 停摆语义）
                #   此前用"欺骗地形"构造无效：系统几乎不采纳，main 恒为 root，
                #   所有策略结果逐位相同（"过于整齐"= 构造失败的信号）
                m = 0.25

        tr = build_tasks(E, rnd, 16)
        he = build_tasks(E, rnd, 16, offset=3)
        adopts = 0
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
            if d_tr > m and d_he > m and jsc(ch, tr) > jsc(main, tr):
                main = ch
                adopts += 1

        # ── 停摆计数（判别器输入 1）──
        if adopts == 0:
            stall += 1
        else:
            stall = 0
        # ★ 分离式（mode=split）：停摆监控独立于审计，每代都可触发
        #   这是内核的实现方式（E44/E96），而非四态分类器的一部分
        if mode == "split" and stall >= STALL_K:
            m = max(0.005, m * 0.5)
            relaxes += 1
            stall = 0
            guessed.append((g, "stuck"))

        if g % 5 == 0:
            cur = _m(tscore(E, t, main) for t in probe)
            hist.append(cur)
            if btr is None:
                btr, best = cur, main
                guessed.append((g, "converged"))
                continue

            degraded = cur < btr - 0.01

            # ── 判别（mode == "diagnose"）──
            state = None
            if mode == "oracle":
                state = {"none": "converged", "drift": "drift",
                         "corrupt": "failure", "stuck": "stuck"}[scene] \
                    if g >= event_at else "converged"
            elif mode == "split":
                # 只做二态判别（E134），stuck 已由上面的独立监控处理
                if degraded:
                    cur_best = _m(tscore(E, t, best) for t in probe)
                    state = "failure" if cur_best > cur + 0.01 else "drift"
                else:
                    state = "converged"
            elif mode == "diagnose":
                # ★ 优先级修正：先判"是否退化"，再分 drift/failure；
                #   只有【没退化但停摆】才是 stuck。
                #   原实现把 stall 放最前，导致 drift/corrupt 被误判为 stuck
                #   （实测 drift 准确率仅 19/132，corrupt 31/132）
                if degraded:
                    cur_best = _m(tscore(E, t, best) for t in probe)
                    state = "failure" if cur_best > cur + 0.01 else "drift"
                elif stall >= STALL_K:
                    state = "stuck"
                else:
                    state = "converged"
            if state:
                guessed.append((g, state))

            # ── 动作 ──
            if mode == "never":
                btr, best = cur, main
            elif mode == "naive":
                if degraded:
                    main, arch = best, [best]
                    reverts += 1
                    btr, best = cur, main
                else:
                    btr, best = cur, main
            else:   # oracle / diagnose：状态决定动作
                if state == "stuck":
                    m = max(0.005, m * 0.5)      # 放宽门槛跨越低谷
                    relaxes += 1
                    stall = 0
                    btr, best = cur, main
                elif state == "failure":
                    main, arch = best, [best]    # 回退
                    reverts += 1
                    btr, best = cur, main
                elif state == "drift":
                    btr, best = cur, main        # 重锚：不回退
                    reanchors += 1
                else:
                    btr, best = cur, main
                if mode == "split" and state in ("failure", "drift", "converged"):
                    pass

    gain = _m(tscore(E, t, main) for t in audit_set) - base
    if collect:
        return gain, {"reverts": reverts, "reanchors": reanchors,
                      "relaxes": relaxes, "guessed": guessed}
    return gain


SCENE_STATE = {"none": "converged", "drift": "drift",
               "corrupt": "failure", "stuck": "stuck"}


def main():
    import sys as _s
    only = _s.argv[1] if len(_s.argv) > 1 else None
    res = json.load(open(OUT)) if os.path.exists(OUT) else {}
    keys = [f"{sc}_{md}" for sc in SCENE_STATE
            for md in ("never", "naive", "diagnose", "split", "oracle")]
    if only:
        keys = [k for k in keys if k.startswith(only + "_")]
    for k in keys:
        sc, md = k.split("_")
        got = res.get(k, [])
        for s in range(len(got) + 1, N_PAIRS + 1):
            try:
                got.append(run(s, sc, md, collect=(md in ("diagnose", "split"))))
            except Exception as ex:
                print("ERR", k, s, ex)
                break
            res[k] = got
            json.dump(res, open(OUT, "w"))
        print(f"  {k}: {len(res.get(k, []))}/{N_PAIRS}")

    if not all(len(res.get(k, [])) >= N_PAIRS for k in keys):
        print("未完成，再跑一次续跑")
        print("未完成，再跑一次续跑")
        return

    print("\n" + "=" * 74)
    print(f"E135 四态判别 + 状态依赖动作（配对 n={N_PAIRS}, {GENS} 代）")
    print("%-10s %-10s %10s %8s %8s %8s" %
          ("场景(真值态)", "策略", "真值增益", "回退", "重锚", "放宽"))

    acc = {}
    for sc, true_state in SCENE_STATE.items():
        for md in ("never", "naive", "diagnose", "split", "oracle"):
            v = res[f"{sc}_{md}"][:N_PAIRS]
            if md in ("diagnose", "split"):
                st = [x[1] for x in v]
                g = [x[0] for x in v]
                rv = statistics.mean(s["reverts"] for s in st)
                ra = statistics.mean(s["reanchors"] for s in st)
                rl = statistics.mean(s["relaxes"] for s in st)
            else:
                g = v
                rv = ra = rl = 0.0
            print("%-10s %-10s %+10.4f %8.1f %8.1f %8.1f" %
                  (f"{sc}({true_state})", md, statistics.mean(g), rv, ra, rl))
        # 判别准确率（只统计事件后的猜测）
        st_list = [x[1] for x in res[f"{sc}_diagnose"][:N_PAIRS]]
        tot = cor = 0
        for s in st_list:
            for g, x in s["guessed"][1:]:   # 跳过首次（基线初始化）
                label = true_state if g >= GENS // 3 else "converged"
                tot += 1
                if x == label:
                    cor += 1
        acc[sc] = (cor, tot)
        print("           判别准确率（按事件前后正确标注）%d/%d\n" % (cor, tot))

    # 汇总：diagnose vs naive
    print("-" * 74)
    print("%-12s %14s" % ("场景", "diagnose − naive"))
    for sc in SCENE_STATE:
        nv = [x[0] if isinstance(x, (list, tuple)) else x
              for x in res[f"{sc}_naive"][:N_PAIRS]]
        dv = [x[0] if isinstance(x, (list, tuple)) else x
              for x in res[f"{sc}_diagnose"][:N_PAIRS]]
        sv = [x[0] if isinstance(x, (list, tuple)) else x
              for x in res[f"{sc}_split"][:N_PAIRS]]
        diff = [b - a for a, b in zip(nv, dv)]
        m_ = statistics.mean(diff)
        se = statistics.pstdev(diff) / math.sqrt(len(diff))
        sd_ = [b - a for a, b in zip(nv, sv)]
        m2 = statistics.mean(sd_)
        se2 = statistics.pstdev(sd_) / math.sqrt(len(sd_))
        print("%-12s %+10.4f ± %.4f (t=%.2f)   | split %+0.4f ± %.4f (t=%.2f)"
              % (sc, m_, se, m_ / se if se else 0, m2, se2, m2 / se2 if se2 else 0))
    print("=" * 74)


if __name__ == "__main__":
    main()
