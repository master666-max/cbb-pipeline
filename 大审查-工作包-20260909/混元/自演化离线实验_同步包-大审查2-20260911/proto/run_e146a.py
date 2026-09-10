"""E146a —— 渐进 drift 检测：跳变信号失效后怎么办？

E145a 证明 judge 跳变在【一次性 drift】下 88%/0%。
但真实 drift 很可能是【渐进】的（用户偏好缓慢迁移、数据分布渐变），
此时没有明显跳变点 → 跳变检测预计失效。

本轮检验：
  注入方式 A  abrupt  一次性（g=8 重洗 35%）      —— E145a 已测
  注入方式 B  gradual 每代重洗 RATE 比例          —— 本轮新增

候选信号（全部免费）：
  S1 jump         judge 评分跳变（E145a 赢家）—— 预计在渐进下失效
  S2 slope        judge 评分趋势（斜率）—— 会被"配置变好"混淆
  S3 anchor       ★锚定探针：固定参考配置(root) 在固定任务集上的得分漂移
                  —— 与演化解耦，理论上只反映世界变化
  S4 ret         检索集 Jaccard 距离趋势
  S5 truth       真值审计（付费，上界参考）

★ S3 的设计要点：用一个【不参与演化的固定配置】做"温度计"。
  世界不变 → 它的得分稳定；世界变了 → 它的得分漂移。
  这与 E14c 的"锚定集"思路不同：锚定的是【配置】，不是【样本】。

判据：检出率(drift) − 误报率(clean) = 净判别力
"""
import sys, os, json, statistics, math, random
sys.path.insert(0, '/data/workspace/proto')
from evolve9 import build_tasks
from evolve20 import Cfg2
from evolve24 import _m, SURF
from evolve31 import build_world_strong, retrieve_strong, tscore

OUT = "/data/workspace/res_e146a.json"
N_SEEDS = 20
GENS = 24


def run(seed, mode="gradual", rate=0.05, gens=GENS, kids=4, scale=2.0,
        tol=0.04, margin=0.0, eff=0.95):
    """mode: none(无drift) / abrupt(一次性) / gradual(渐进)"""
    rnd = random.Random(seed)
    E = build_world_strong(seed, corr=0.85)
    audit_set = build_tasks(E, random.Random(7777), 40, offset=5)
    root = Cfg2()
    base = _m(tscore(E, t, root) for t in audit_set)
    arch, main = [root], root
    cap = 8
    probe = build_tasks(E, random.Random(4242), 4, offset=7)
    anchor_tasks = build_tasks(E, random.Random(31337), 8, offset=11)  # 固定锚定集

    hist_judge = []
    hist_anchor = []
    hist_ret = []
    hist_truth = []
    prev_ret = None
    drift_at = gens // 3

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
        # ── drift 注入 ──
        if mode == "abrupt" and g == drift_at:
            r = random.Random(seed + 999)
            for e in E:
                if r.random() < 0.35:
                    e["true_quality"] = r.random() * 0.3
        elif mode == "gradual" and g >= drift_at:
            r = random.Random(seed * 1000 + g)
            for e in E:
                if r.random() < rate:
                    e["true_quality"] = r.random() * 0.3

        tr = build_tasks(E, rnd, 16)
        he = build_tasks(E, rnd, 16, offset=3)
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

        hist_judge.append(jsc(main, tr))
        # ★ 锚定探针：固定配置 root 在固定集上的得分
        hist_anchor.append(jsc(root, anchor_tasks))
        cur_ret = frozenset(e["id"] for t in tr for e in retrieve_strong(E, t, main))
        if prev_ret is not None:
            inter = len(cur_ret & prev_ret)
            union = len(cur_ret | prev_ret) or 1
            hist_ret.append(1 - inter / union)
        else:
            hist_ret.append(0.0)
        prev_ret = cur_ret
        hist_truth.append(_m(tscore(E, t, main) for t in probe))

    return {"judge": hist_judge, "anchor": hist_anchor, "ret": hist_ret,
            "truth": hist_truth, "drift_at": drift_at,
            "gain": _m(tscore(E, t, main) for t in audit_set) - base}


def slope(xs):
    n = len(xs)
    if n < 2:
        return 0.0
    mx = statistics.mean(xs)
    my = statistics.mean(range(n))
    num = sum((x - mx) * (i - my) for i, x in enumerate(xs))
    den = sum((i - my) ** 2 for i in range(n))
    return num / den if den else 0.0


def detect(h, kind, win=5):
    da = h["drift_at"]
    post_start = da + 2          # 给一点反应时间
    if kind == "jump":
        pre = statistics.mean(h["judge"][max(0, da - win):da])
        post = h["judge"][post_start:post_start + win]
        return bool(post) and statistics.mean(post) < pre - 0.02
    if kind == "slope":
        seg = h["judge"][post_start:]
        return len(seg) >= 4 and slope(seg) < -0.002
    if kind == "anchor":
        # ★ 锚定探针漂移：后期 vs 前期
        pre = statistics.mean(h["anchor"][max(0, da - win):da])
        post = h["anchor"][post_start:]
        return bool(post) and statistics.mean(post) < pre - 0.02
    if kind == "ret":
        pre = statistics.mean(h["ret"][max(0, da - win):da])
        post = h["ret"][post_start:]
        return bool(post) and statistics.mean(post) > pre + 0.05
    if kind == "truth":
        pre = statistics.mean(h["truth"][max(0, da - win):da])
        post = h["truth"][post_start:]
        return bool(post) and statistics.mean(post) < pre - 0.02
    return False


def main():
    res = json.load(open(OUT)) if os.path.exists(OUT) else {}
    scen = [("none", "none"), ("abrupt", "abrupt"), ("gradual03", "gradual")]
    rate_map = {"gradual03": 0.03}
    for tag, md in scen:
        got = res.get(tag, [])
        for s in range(len(got) + 1, N_SEEDS + 1):
            try:
                got.append(run(s, mode=md, rate=rate_map.get(tag, 0.05)))
            except Exception as ex:
                print("ERR", tag, s, ex)
                break
            res[tag] = got
            json.dump(res, open(OUT, "w"))
        print(f"  {tag}: {len(res.get(tag, []))}/{N_SEEDS}")

    # 无 drift 组复用 none 作为误报基准
    if not all(len(res.get(t, [])) >= N_SEEDS for t, _ in scen):
        print("未完成，续跑")
        return

    print("\n" + "=" * 76)
    print(f"E146a 渐进 drift 检测（n={N_SEEDS}, {GENS} 代）")
    print("%-10s %14s %14s %14s" % ("信号", "abrupt 检出", "gradual 检出", "误报(none)"))
    for kind in ("jump", "slope", "anchor", "ret", "truth"):
        ab = sum(1 for h in res["abrupt"][:N_SEEDS] if detect(h, kind)) / N_SEEDS
        gr = sum(1 for h in res["gradual03"][:N_SEEDS] if detect(h, kind)) / N_SEEDS
        fp = sum(1 for h in res["none"][:N_SEEDS] if detect(h, kind)) / N_SEEDS
        print("%-10s %13.0f%% %13.0f%% %13.0f%%" % (kind, ab * 100, gr * 100, fp * 100))
    print("-" * 76)
    print("净判别力（检出 − 误报）:")
    for kind in ("jump", "slope", "anchor", "ret", "truth"):
        gr = sum(1 for h in res["gradual03"][:N_SEEDS] if detect(h, kind)) / N_SEEDS
        fp = sum(1 for h in res["none"][:N_SEEDS] if detect(h, kind)) / N_SEEDS
        print("  %-8s gradual: %+.2f" % (kind, gr - fp))
    print("=" * 76)


if __name__ == "__main__":
    main()
