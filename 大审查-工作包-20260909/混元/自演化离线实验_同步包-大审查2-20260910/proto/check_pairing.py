"""T4b 独立验证：大幅度 × 审计 的配对效应（E110）

独立脚本，不导入 verify_kernel（否则会执行全部测试）。
"""
import sys, statistics, random
sys.path.insert(0, '/data/workspace/proto')
from kernel import Kernel, KernelConfig, Policy, Entry, truth

TOPICS = [f"T{i}" for i in range(16)]


def build_world(seed=0, n=60, kws=6):
    rnd = random.Random(seed)
    es = []
    for i in range(n):
        k = f"K{i % kws}"
        t = TOPICS[i % 16]
        es.append(Entry(id=f"e{i}", kw=k, topic=t, content=f"{t} {k} 片段{i}",
                        importance=rnd.randint(1, 3) / 3.0, quality=rnd.random(),
                        length=rnd.random(), formatting=rnd.random(),
                        density=rnd.random(),
                        citation=1.0 if rnd.random() < .5 else 0.0))
    return es


def mk(seed=0, **kw):
    es = build_world(seed)
    tr = [f"T{i} K{i % 6}" for i in range(16)]
    he = [f"T{i} K{i % 6}" for i in range(3, 19)]
    k = Kernel(entries=es, tasks_train=tr, tasks_held=he,
               rnd=random.Random(seed), cfg=KernelConfig(**kw))
    k.generation = 0
    return k


def gains(scale, audit, blind=True, gens=20, seeds=16):
    out = []
    for s in range(seeds):
        kk = mk(s, scale=scale, audit=audit, blind=blind)
        base = truth(kk.entries, kk.tasks_train + kk.tasks_held, Policy())
        kk.run(gens)
        out.append(truth(kk.entries, kk.tasks_train + kk.tasks_held, kk.champion) - base)
    return statistics.mean(out)


if __name__ == "__main__":
    print("T4b 配对效应：审计收益应随幅度上升（E110）")
    prev = None
    for sc in (1.0, 2.0, 3.0):
        a = gains(sc, True)
        b = gains(sc, False)
        print(f"  幅度{sc:.1f}: 有审计{a:+.4f}  无审计{b:+.4f}  审计收益{a - b:+.4f}")
        prev = a - b
