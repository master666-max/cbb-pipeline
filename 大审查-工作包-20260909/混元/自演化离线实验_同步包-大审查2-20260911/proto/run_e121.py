"""E121-E124 分片运行器（断点续跑）"""
import sys, os, json, statistics
sys.path.insert(0, '/data/workspace/proto')
from evolve29 import e121, e122, e123, e124

OUT = "/data/workspace/res_e121.json"
res = json.load(open(OUT)) if os.path.exists(OUT) else {}
SAVE = lambda: json.dump(res, open(OUT, "w"))
SEEDS = list(range(1, 13))


FIELDS = ["gain", "writalloc", "self_frac", "avg_quality", "final_size"]


def flat(v):
    """v = (gain, st) → [gain, writalloc, self_frac, avg_quality, final_size]"""
    if isinstance(v, tuple):
        g, st = v
        return [g, st.get("writalloc", 0), st.get("self_frac", 0),
                st.get("avg_quality", 0), st.get("final_size", 0)]
    return [v, 0, 0, 0, 0]


def batch(name, fn, keys):
    d = res.setdefault(name, {})
    for k in keys:
        got = d.get(str(k), [])
        for s in SEEDS[len(got):]:
            try:
                got.append(flat(fn(s, k)))
            except Exception as ex:
                print("ERR", name, k, s, ex)
                break
            d[str(k)] = got
            SAVE()
    return d


def show(name, keys, cols):
    d = res.get(name, {})
    print(f"\n=== {name} ===")
    for k in keys:
        v = d.get(str(k), [])
        if len(v) < len(SEEDS):
            print(f"  {k}: 未完成 {len(v)}/{len(SEEDS)}")
            continue
        means = [statistics.mean(x[i] for x in v) for i in range(len(v[0]))]
        print(f"  {str(k):>10s}: " + "  ".join(f"{c}={m:+.4f}" if abs(m) < 10 else f"{c}={m:.2f}"
                                               for c, m in zip(cols, means)))


# E121 内生写入质量
batch("e121", lambda s, a: e121(s, a), [0.3, 0.5, 0.7, 0.95])
show("e121", [0.3, 0.5, 0.7, 0.95], ["增益", "writalloc", "自写占比", "平均质量", "世界大小"])

# E122 整理标准
batch("e122", lambda s, p: e122(s, p), ["none", "judge", "truth"])
show("e122", ["none", "judge", "truth"], ["增益", "writalloc", "自写占比", "平均质量", "世界大小"])

# E123 三元交互
for a in (True, False):
    for p in ("none", "truth"):
        batch(f"e123_{a}_{p}", lambda s, _k, a=a, p=p: e123(s, a, p), ["x"])
print("\n=== E123 审计 × 整理 ===")
for a in (True, False):
    for p in ("none", "truth"):
        v = res.get(f"e123_{a}_{p}", {}).get("x", [])
        if len(v) >= len(SEEDS):
            print(f"  审计={str(a):>5s} 整理={p:>6s}: {statistics.mean(x[0] for x in v):+.4f}")
        else:
            print(f"  审计={str(a):>5s} 整理={p:>6s}: 未完成 {len(v)}/{len(SEEDS)}")

# E124 冷启动
batch("e124", lambda s, i: e124(s, i), [True, False])
show("e124", [True, False], ["增益", "writalloc", "自写占比", "平均质量", "世界大小"])
