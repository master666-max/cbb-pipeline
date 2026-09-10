"""E112-E115 分片运行器"""
import sys, os, json, statistics
sys.path.insert(0, '/data/workspace/proto')
from evolve27 import e112, e113, e114, e115
from evolve27 import run, V3, V4A, V4B

OUT = "/data/workspace/res_e112.json"
res = json.load(open(OUT)) if os.path.exists(OUT) else {}
SAVE = lambda: json.dump(res, open(OUT, "w"))


def batch(name, fn, keys, seeds=range(1, 13)):
    d = res.setdefault(name, {})
    for k in keys:
        got = d.get(str(k), [])
        for s in list(seeds)[len(got):]:
            try:
                got.append(fn(s, k))
            except Exception as ex:
                print("ERR", name, k, s, ex)
                break
            d[str(k)] = got
            SAVE()
    return d


# E112 大幅度的破坏性代价
def f112(seed, sc):
    g, st = e112(seed, sc, gens=25)
    return [g, st["reverts"], st["surf"], st.get("mutations", 0)]


d112 = batch("e112", f112, [0.5, 1.0, 2.0, 3.0, 5.0])
print("=== E112 大幅度的破坏性代价（12种子，25代）===")
print(f"{'幅度':>5s} {'真值增益':>9s} {'回退次数':>9s} {'展示权重':>9s}")
for sc in [0.5, 1.0, 2.0, 3.0, 5.0]:
    if str(sc) not in d112 or len(d112[str(sc)]) < 12:
        print(f"{sc:>5.1f}  (未完成 {len(d112.get(str(sc),[]))}/12)")
        continue
    v = d112[str(sc)]
    print(f"{sc:>5.1f} {statistics.mean(x[0] for x in v):>+9.4f} "
          f"{statistics.mean(x[1] for x in v):>9.1f} {statistics.mean(x[2] for x in v):>9.3f}")

# E113 幅度自适应
def f113(seed, mode):
    g, sc, rv = e113(seed, mode, gens=30)
    return [g, sc, rv]


d113 = batch("e113", f113, ["fixed2.0", "adaptive"])
print("\n=== E113 幅度自适应（12种子，30代）===")
for m in ["fixed2.0", "adaptive"]:
    if str(m) not in d113 or len(d113[str(m)]) < 12:
        print(f"  {m}: 未完成 {len(d113.get(str(m),[]))}/12")
        continue
    v = d113[str(m)]
    print(f"  {m:>10s}: {statistics.mean(x[0] for x in v):+.4f}  "
          f"终局幅度{statistics.mean(x[1] for x in v):.2f}  回退{statistics.mean(x[2] for x in v):.1f}")

# E114 幅度 × 温度
def f114(seed, combo):
    sc, tp = combo
    return e114(seed, sc, tp, gens=25)


combos = [(1.0, 0.0), (1.0, 0.3), (2.0, 0.0), (2.0, 0.3), (2.0, 0.6), (3.0, 0.3)]
d114 = batch("e114", f114, combos)
print("\n=== E114 幅度 × 温度（12种子，25代）===")
for c in combos:
    if str(c) not in d114 or len(d114[str(c)]) < 12:
        print(f"  {c}: 未完成 {len(d114.get(str(c),[]))}/12")
        continue
    print(f"  幅度{c[0]:.1f} 温度{c[1]:.1f}: {statistics.mean(d114[str(c)]):+.4f}")

# E115 复合危险世界
def f115(seed, tier):
    return e115(seed, tier, gens=25)


d115 = batch("e115", f115, ["v3", "v4-A", "v4-B"])
print("\n=== E115 复合危险世界（漂移+伪特征+噪声20%+污染50%；12种子，25代）===")
for t in ["v3", "v4-A", "v4-B"]:
    if str(t) not in d115 or len(d115[str(t)]) < 12:
        print(f"  {t}: 未完成 {len(d115.get(str(t),[]))}/12")
        continue
    print(f"  {t:>6s}: {statistics.mean(d115[str(t)]):+.4f}")
