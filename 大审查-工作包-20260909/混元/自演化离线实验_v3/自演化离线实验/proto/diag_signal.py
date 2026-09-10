"""诊断：排序空间里到底有没有真值信号？

E112 显示展示权重爆炸到 7-27 而真值仍为正。
可能的解释：(a) 展示权重确实无害；(b) 我的世界真值信号太弱，
任何排序都差不多，所以伤害看不出来。

本诊断直接测量：随机配置的真值分布有多宽。
"""
import sys, random, statistics
sys.path.insert(0, '/data/workspace/proto')
from evolve9 import build_tasks
from evolve20 import build_world_v2, Cfg2, truth_score
from evolve24 import _m

E = build_world_v2(0)
audit = build_tasks(E, random.Random(7777), 40, offset=5)
root = Cfg2()
base = _m(truth_score(E, t, root) for t in audit)
print('root 真值基线 = %.4f' % base)

rnd = random.Random(0)
zs, hi = [], []
for i in range(200):
    d = dict(w_kw=rnd.uniform(0, 6), w_content=rnd.uniform(0, 3),
             w_imp=rnd.uniform(-1, 3), w_age=rnd.uniform(-1, 1))
    if i % 2 == 0:
        c = Cfg2(**d)
        zs.append(_m(truth_score(E, t, c) for t in audit) - base)
    else:
        c = Cfg2(**dict(d, w_len=rnd.uniform(5, 20), w_fmt=rnd.uniform(5, 20),
                        w_den=rnd.uniform(5, 20), w_cit=rnd.uniform(5, 20)))
        hi.append(_m(truth_score(E, t, c) for t in audit) - base)

print('surf=0  : mean=%+.4f sd=%.4f max=%+.4f' %
      (statistics.mean(zs), statistics.pstdev(zs), max(zs)))
print('surf 高 : mean=%+.4f sd=%.4f max=%+.4f' %
      (statistics.mean(hi), statistics.pstdev(hi), max(hi)))
print('排序空间信号强度 sd = %.4f' % statistics.pstdev(zs))
