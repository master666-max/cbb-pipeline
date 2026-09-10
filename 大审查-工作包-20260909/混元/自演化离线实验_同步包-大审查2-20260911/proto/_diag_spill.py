import sys, random, statistics; sys.path.insert(0,'/data/workspace/proto')
from vk_common import build_world, mk
import kernel as K
from kernel import truth, Policy, replace, SURF

# 噪声底：两个随机配置的 truth 差（同任务集）
for n in (8, 20, 40, 80):
    diffs = []
    for s in range(12):
        k = mk(s)
        tasks = k.tasks_train + k.tasks_held
        tasks = tasks[:n] if len(tasks) >= n else tasks * (n // len(tasks) + 1)
        a = Policy(w_len=0.9, w_fmt=0.9, w_den=0.9, w_cit=0.9)
        b = replace(a, **{x: 0.0 for x in SURF})
        diffs.append(truth(k.entries, tasks, a) - truth(k.entries, tasks, b))
    print("任务数 %3d : justified 均值 %+.4f  sd %.4f  → 噪声底 ±%.4f"
          % (n, statistics.mean(diffs), statistics.pstdev(diffs),
             2*statistics.pstdev(diffs)))
