"""E145a —— drift 检测：无真值时能否发现"世界变了"？

第 35 轮证明 drift 是唯一断崖（−0.2252, t=−5.78），
且现有全部防御（盲评/整理/审计/监控）都无效。

但前提是"能检测到 drift"。而 drift 的定义就是"真值定义变了"——
**如果有真值可测，就不叫 drift 检测问题了。**

所以核心问题：**用系统可见的信号能否检测 drift？**

候选信号（全部无需真值）：
  S1 adopt_rate   采纳率：drift 后旧配置不再有效 → 采纳率下降
  S2 judge_jump   judge 评分的跳变：世界变了 → 同一配置得分突变
  S3 ret_shift    检索结果分布偏移：条目分布变了 → top-K 集合变化
  S4 audit_degrade 真值审计连续下降（E134 判别式）——需探针，有成本
  S5 comb         组合信号

对照：
  oracle  用真值直接告知（上界）

设计：drift 在 g=8 注入（重洗 35% 条目质量），
      看各信号能否在 g=10/15/20 前检出。
      指标：检出率 / 误报率（在【无 drift】世界上的误报）
"""
import sys, os, json, statistics, math, random
sys.path.insert(0, '/data/workspace/proto')
from evolve9 import build_tasks
from evolve20 import Cfg2
from evolve24 import _m, SURF
from evolve31 import build_world_strong, retrieve_strong, tscore

OUT = "/data/workspace/res_e145a.json"
N_SEEDS = 24
GENS = 24


def run(seed, drift=True, gens=GENS, kids=4, scale=2.0, tol=0.04,
        margin=0.0, eff=0.95):
    rnd = random.Random(seed)
    E = build_world_strong(seed, corr=0.85)
    audit_set = build_tasks(E, random.Random(7777), 40, offset=5)
    root = Cfg2()
    base = _m(tscore(E, t, root) for t in audit_set)
    arch, main = [root], root
    cap = 8
    probe = build_tasks(E, random.Random(4242), 4, offset=7)

    hist_adopt = []
    hist_judge = []
    hist_retset = []
    hist_truth = []
    prev_ret = None
    drift_at = gens // 3
    truth_series = []

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
        if drift and g == drift_at:
            r = random.Random(seed + 999)
            for e in E:
                if r.random() < 0.35:
                    e["true_quality"] = r.random() * 0.3
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
            if d_tr > margin and d_he > 0 and jsc(ch, tr) > jsc(main, tr):
                main = ch
                adopts += 1

        hist_adopt.append(adopts)
        hist_judge.append(jsc(main, tr))
        cur_ret = frozenset(e["id"] for t in tr for e in retrieve_strong(E, t, main))
        if prev_ret is not None:
            inter = len(cur_ret & prev_ret)
            union = len(cur_ret | prev_ret) or 1
            hist_retset.append(1 - inter / union)     # Jaccard 距离
        else:
            hist_retset.append(0.0)
        prev_ret = cur_ret
        truth_series.append(_m(tscore(E, t, main) for t in probe))

    return {"adopt": hist_adopt, "judge": hist_judge,
            "ret": hist_retset, "truth": truth_series,
            "gain": _m(tscore(E, t, main) for t in audit_set) - base,
            "drift_at": drift_at}


def detect(hist, drift_at, kind, win=3, thr=None):
    """在 drift_at 之后 win 代内是否触发"""
    if kind == "adopt":
        # 采纳率骤降：drift 后 win 代平均 < drift 前平均 - 1
        pre = statistics.mean(hist["adopt"][max(0, drift_at - 6):drift_at])
        post = hist["adopt"][drift_at:drift_at + win]
        return (statistics.mean(post) < pre - 1) if post else False
    if kind == "judge":
        pre = statistics.mean(hist["judge"][max(0, drift_at - 6):drift_at])
        post = hist["judge"][drift_at:drift_at + win]
        return (statistics.mean(post) < pre - 0.02) if post else False
    if kind == "ret":
        pre = statistics.mean(hist["ret"][max(0, drift_at - 6):drift_at])
        post = hist["ret"][drift_at:drift_at + win]
        return (statistics.mean(post) > pre + 0.10) if post else False
    if kind == "truth":
        pre = statistics.mean(hist["truth"][max(0, drift_at - 6):drift_at])
        post = hist["truth"][drift_at:drift_at + win]
        return (statistics.mean(post) < pre - 0.02) if post else False
    if kind == "comb":
        return (detect(hist, drift_at, "adopt", win)
                or detect(hist, drift_at, "ret", win))
    return False


def main():
    res = json.load(open(OUT)) if os.path.exists(OUT) else {}
    for tag, dr in (("drift", True), ("clean", False)):
        got = res.get(tag, [])
        for s in range(len(got) + 1, N_SEEDS + 1):
            try:
                got.append(run(s, drift=dr))
            except Exception as ex:
                print("ERR", tag, s, ex)
                break
            res[tag] = got
            json.dump(res, open(OUT, "w"))
        print(f"  {tag}: {len(res.get(tag, []))}/{N_SEEDS}")

    if not all(len(res.get(t, [])) >= N_SEEDS for t in ("drift", "clean")):
        print("未完成，续跑")
        return

    print("\n" + "=" * 70)
    print(f"E145a drift 检测：无真值信号能否发现世界变化（n={N_SEEDS}）")
    print("%-10s %12s %12s %12s" % ("信号", "检出率(drift)", "误报率(clean)", "净判别力"))
    for kind in ("adopt", "judge", "ret", "truth", "comb"):
        hit = sum(1 for h in res["drift"][:N_SEEDS]
                  if detect(h, h["drift_at"], kind)) / N_SEEDS
        fp = sum(1 for h in res["clean"][:N_SEEDS]
                 if detect(h, h["drift_at"], kind)) / N_SEEDS
        print("%-10s %11.0f%% %11.0f%% %+12.2f"
              % (kind, hit * 100, fp * 100, hit - fp))
    print("=" * 70)
    print("注：truth 需探针（有成本，仅作上界参考）；其余为免费信号")


if __name__ == "__main__":
    main()
