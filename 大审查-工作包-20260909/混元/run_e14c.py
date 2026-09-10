import sys; sys.path.insert(0, '/data/workspace/proto')
import random, math, statistics
from evolve6 import *

# E14c 第三轮建议的『近因加权』在被污染环境下是否安全？
# 环境：人被系统输出锚定（α>0），判断样本持续累积（新样本用被污染的 w 生成）
# 策略：均匀加权 vs 近因加权
# 测：哪种策略让真实效用(W0)退化更快 —— 即第三轮建议在漂移下是药还是毒

def fit_w(entries, tasks, samples, weights=None, epochs=150, lr=0.1, dims=3):
    """加权配对 logistic 拟合"""
    w = [0.0] * dims
    if weights is None:
        weights = [1.0] * len(samples)
    F = [(feats(entries, tasks, a), feats(entries, tasks, b), y, wt)
         for (a, b, y), wt in zip(samples, weights)]
    for _ in range(epochs):
        for fa, fb, y, wt in F:
            d = [x - z for x, z in zip(fa, fb)]
            z = y * sum(wi * di for wi, di in zip(w, d))
            g = 1.0 / (1.0 + math.exp(max(-30, min(30, z))))
            for i in range(dims):
                w[i] += lr * wt * g * y * d[i]
    n = math.sqrt(sum(x * x for x in w)) or 1.0
    return [x / n * math.sqrt(sum(y * y for y in W0)) for x in w]


def run(seed, alpha, scheme, gens=20, per_gen=4, half_life=None):
    rnd = random.Random(seed)
    E = build_world(seed)
    tr, he = build_tasks(E, rnd, 20, 40)
    w_human = list(W0)                       # 人的真实（漂移中的）偏好
    samples = []                             # 判断样本库（只追加）
    # 初始样本：用 W0 生成（系统出现前采集的『锚定样本』）
    for _ in range(20):
        a, b = rand_cfg(rnd), rand_cfg(rnd)
        ua, ub = U_w(E, tr, a, W0), U_w(E, tr, b, W0)
        if abs(ua - ub) < 1e-9: continue
        samples.append((a, b, 1.0 if ua > ub else -1.0))

    root = Cfg(); arch = [root]; main = root
    for g in range(1, gens + 1):
        # 用当前拟合出的权重驱动演化
        w_fit = fit_w(E, tr, samples,
                      weights=None if scheme == "uniform" else
                      [0.5 ** ((len(samples) - 1 - i) / half_life) for i in range(len(samples))],
                      epochs=120)
        for _ in range(4):
            cand = rnd.choice(sorted(arch, key=lambda c: -U_w(E, tr, c, w_fit))[:3])
            ch = mutate(cand, rnd)
            if U_w(E, tr, ch, w_fit) - U_w(E, tr, cand, w_fit) > -0.06: arch.append(ch)
            if (U_w(E, tr, ch, w_fit) - U_w(E, tr, cand, w_fit) > 0.01 and
                    U_w(E, he, ch, w_fit) - U_w(E, he, cand, w_fit) > 0.01 and
                    U_w(E, tr, ch, w_fit) > U_w(E, tr, main, w_fit)): main = ch
        arch = arch[-30:]
        # 人看了系统输出后被锚定
        if alpha > 0:
            f = feats(E, tr, main)
            fn = math.sqrt(sum(x * x for x in f)) or 1.0
            tgt = [x / fn * math.sqrt(sum(y * y for y in W0)) for x in f]
            w_human = [(1 - alpha) * wi + alpha * ti for wi, ti in zip(w_human, tgt)]
        # 新判断样本：用【被锚定后】的 w_human 生成
        for _ in range(per_gen):
            a, b = rand_cfg(rnd), rand_cfg(rnd)
            ua, ub = U_w(E, tr, a, w_human), U_w(E, tr, b, w_human)
            if abs(ua - ub) < 1e-9: continue
            samples.append((a, b, 1.0 if ua > ub else -1.0))
    return U_w(E, he, main, W0), U_w(E, he, root, W0), math.dist(w_human, W0)


if __name__ == "__main__":
    print('E14c 近因加权 vs 均匀加权，在被锚定环境下（6 种子，20代）')
    print('W0 =', W0)
    print(f"{'锚定α':>7s} {'加权策略':>14s} {'真实效用':>9s} {'相对起点':>9s} {'人的权重漂移':>12s}")
    for alpha in (0.0, 0.05, 0.15):
        for scheme, hl, label in (("uniform", None, "均匀加权"),
                                  ("recency", 15, "近因加权(hl=15)"),
                                  ("recency", 5, "近因加权(hl=5)")):
            ts, r0s, drs = [], [], []
            for s in range(1, 7):
                t, r0, d = run(s, alpha, scheme, half_life=hl)
                ts.append(t); r0s.append(r0); drs.append(d)
            print(f'{alpha:>7.2f} {label:>14s} {statistics.mean(ts):>9.4f} '
                  f'{statistics.mean(ts)-statistics.mean(r0s):>+9.4f} {statistics.mean(drs):>12.3f}')
