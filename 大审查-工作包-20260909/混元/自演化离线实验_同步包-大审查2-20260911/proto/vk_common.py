"""verify_kernel 的公共构件（独立模块，import 不会执行测试）

★ 为什么要拆出来：
  verify_kernel.py 是【平铺脚本】，import 它会把全部测试跑一遍。
  沙盒不稳时无法"只预计算重活"，所以把 build_world / mk / cached 放这里。
"""
import sys, random, json, os
sys.path.insert(0, '/data/workspace/proto')
from kernel import (Kernel, KernelConfig, Meta, Policy, Entry, retrieve, judge,
                    truth, cheap_screen, mutate, pareto_front, JudgeScore,
                    ScreenResult)

_CACHE = "/data/workspace/res_verify_cache.json"


def cached(key, fn):
    """落盘缓存：沙盒中断后续跑只补缺失项"""
    c = {}
    if os.path.exists(_CACHE):
        try:
            c = json.load(open(_CACHE))
        except Exception:
            c = {}
    if key in c:
        return c[key]
    v = fn()
    c[key] = v
    json.dump(c, open(_CACHE, "w"))
    return v


def build_world(seed=0, n=60, kws=6):
    rnd = random.Random(seed)
    TOPICS = [f"T{i}" for i in range(16)]
    es = []
    for i in range(n):
        k = f"K{i % kws}"
        t = TOPICS[i % 16]
        es.append(Entry(
            id=f"e{i}", kw=k, topic=t, content=f"{t} {k} 片段{i}",
            importance=rnd.randint(1, 3) / 3.0,
            quality=rnd.random(),
            length=rnd.random(), formatting=rnd.random(),
            density=rnd.random(), citation=1.0 if rnd.random() < .5 else 0.0,
        ))
    return es


def mk(seed=0, **cfgkw):
    es = build_world(seed)
    tasks = [f"T{i} K{i % 6}" for i in range(16)]
    held = [f"T{i} K{i % 6}" for i in range(3, 19)]
    k = Kernel(entries=es, tasks_train=tasks, tasks_held=held,
               rnd=random.Random(seed), cfg=KernelConfig(**cfgkw))
    k.generation = 0
    return k
