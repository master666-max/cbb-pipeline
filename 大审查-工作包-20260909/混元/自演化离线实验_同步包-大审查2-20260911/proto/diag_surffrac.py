"""诊断2：surf 爆炸是绝对增长还是相对占比上升？"""
import sys, random, statistics
sys.path.insert(0, '/data/workspace/proto')
from evolve9 import build_tasks
from evolve20 import build_world_v2, Cfg2, truth_score
from evolve24 import _m, surf_mag

E = build_world_v2(0)
audit = build_tasks(E, random.Random(7777), 40, offset=5)
root = Cfg2()
base = _m(truth_score(E, t, root) for t in audit)


def frac(c):
    tot = abs(c.w_kw) + abs(c.w_content) + abs(c.w_imp) + abs(c.w_age) + surf_mag(c)
    return surf_mag(c) / tot if tot > 0 else 0.0


print('root: surf=%.2f 占比=%.1f%% w_kw=%.1f' %
      (surf_mag(root), frac(root) * 100, root.w_kw))

rnd = random.Random(1)
rows = []
for i in range(300):
    big = 1.0 if i % 2 else 0.0
    sc = 8.0 if big else 1.0
    c = Cfg2(w_kw=rnd.uniform(0, 6) * sc, w_content=rnd.uniform(0, 3) * sc,
             w_imp=rnd.uniform(-1, 3) * sc, w_age=rnd.uniform(-1, 1) * sc,
             w_len=rnd.uniform(0, 5) * sc, w_fmt=rnd.uniform(0, 5) * sc,
             w_den=rnd.uniform(0, 5) * sc, w_cit=rnd.uniform(0, 5) * sc)
    g = _m(truth_score(E, t, c) for t in audit) - base
    rows.append((surf_mag(c), frac(c), g, big))

for lab, sel in (("小幅度", 0.0), ("大幅度", 1.0)):
    sub = [r for r in rows if r[3] == sel]
    print('%s: surf均值=%.2f 占比均值=%.1f%% 真值=%+.4f (sd=%.4f)'
          % (lab, statistics.mean(r[0] for r in sub),
             statistics.mean(r[1] for r in sub) * 100,
             statistics.mean(r[2] for r in sub),
             statistics.pstdev([r[2] for r in sub])))


def corr(xs, ys):
    mx, my = statistics.mean(xs), statistics.mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = sum((x - mx) ** 2 for x in xs) ** .5
    dy = sum((y - my) ** 2 for y in ys) ** .5
    return num / (dx * dy) if dx and dy else 0.0


print()
print('corr(surf绝对值, 真值) = %+.3f' % corr([r[0] for r in rows], [r[2] for r in rows]))
print('corr(surf占比,   真值) = %+.3f' % corr([r[1] for r in rows], [r[2] for r in rows]))
