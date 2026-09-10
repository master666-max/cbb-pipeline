import sys; sys.path.insert(0, '/data/workspace/proto')
import random, math, statistics
from evolve5 import *

# E9 修正设计：不去测"演化终值"(增益小、噪声大)，而测"选择一致性"
#   给一批候选配置，用【拟合权重】排序 vs 用【真值权重】排序，看 top-k 重合度
#   这直接回答：多少条人类判断，才够让系统选出人真正想要的配置

def rand_cfg(rnd):
    return Cfg(w_kw=round(rnd.uniform(0, 8), 2), w_content=round(rnd.uniform(0, 4), 2),
               w_imp=round(rnd.uniform(-1, 3), 2), w_age=round(rnd.uniform(0, 0.5), 3),
               filter_zero=rnd.randint(0, 1), expand_links=rnd.randint(0, 1),
               retriever=rnd.choice(["kw", "content", "hybrid"]))

print('E9  判断样本 → 拟合效用 → 与真人偏好的选择一致性（10 种子）')
print('W_TRUE =', W_TRUE, '(命中, 噪声, 成本)')
print(f"{'样本数':>6s} {'权重误差':>9s} {'排序相关τ':>10s} {'top1命中':>9s} {'top3重合':>9s}")

for n in (5, 10, 20, 40, 80, 160):
    errs, taus, hits, tops = [], [], [], []
    for s in range(1, 11):
        rnd = random.Random(s * 17)
        E = build_world(s)
        tr, _ = build_tasks(E, rnd, 20, 40)
        js = gen_judgments(E, tr, n, rnd)
        w = fit_from_judgments(E, tr, js, rnd, epochs=400)
        errs.append(math.sqrt(sum((a - b) ** 2 for a, b in zip(w, W_TRUE))))

        cands = [rand_cfg(rnd) for _ in range(60)]
        key_t = lambda c: U_true(E, tr, c)
        key_f = lambda c: U_lin(E, tr, c, w)
        ord_t = sorted(cands, key=lambda c: -key_t(c))
        ord_f = sorted(cands, key=lambda c: -key_f(c))
        hits.append(1.0 if str(asdict(ord_f[0])) == str(asdict(ord_t[0])) else 0.0)
        tops.append(len({str(asdict(c)) for c in ord_f[:3]} & {str(asdict(c)) for c in ord_t[:3]}) / 3)

        # Kendall tau（60 个候选，O(n^2) 可接受）
        agree = dis = 0
        for i in range(len(cands)):
            for j in range(i + 1, len(cands)):
                a = key_t(cands[i]) - key_t(cands[j])
                b = key_f(cands[i]) - key_f(cands[j])
                if a * b > 0: agree += 1
                elif a * b < 0: dis += 1
        taus.append((agree - dis) / (agree + dis) if (agree + dis) else 0.0)
    print(f'{n:>6d} {statistics.mean(errs):>9.3f} {statistics.mean(taus):>10.3f} '
          f'{statistics.mean(hits):>9.0%} {statistics.mean(tops):>9.0%}')
