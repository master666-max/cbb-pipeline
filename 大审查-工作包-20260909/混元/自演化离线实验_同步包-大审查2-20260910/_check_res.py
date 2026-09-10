"""静态核验同步包 E135/E136/E137 报告数字（对照 bootstrap_自演化推演_第二十九/三十轮.md）"""
import json, statistics, math, os

BASE = r"D:\临时工作区\大审查-工作包-20260909\混元\自演化离线实验_同步包-大审查2-20260910"

def load(f):
    return json.load(open(os.path.join(BASE, f), encoding="utf-8"))

def pdiff(a, b):
    n = min(len(a), len(b))
    d = [y - x for x, y in zip(a[:n], b[:n])]
    m = statistics.mean(d)
    se = statistics.pstdev(d) / math.sqrt(n)
    return m, se, (m / se if se else 0.0), n

def mean(v):
    n = min(len(v), 10**9)
    return statistics.mean(v[:n])

print("=" * 70)
print("E135 四态判别（报告口径：配对 n=22，diagnose/split − naive）")
print("报告: none +0.0003(t=.77)/+0.0006(t=1.16)  drift +0.1175±.0284(t=4.13)/+0.1174(t=4.12)")
print("      corrupt +0.0006(t=1.87)/+0.0033(t=2.06)  stuck +0.1428±.0179(t=7.97)/+0.1625±.0147(t=11.06)")
e135 = load("res_e135.json")
for sc in ("none", "drift", "corrupt", "stuck"):
    nv = [x for x in e135[f"{sc}_naive"]]
    dg = [x[0] for x in e135[f"{sc}_diagnose"]]
    sp = [x[0] for x in e135[f"{sc}_split"]]
    md = pdiff(nv, dg)
    ms = pdiff(nv, sp)
    print(f"  {sc:8s} diagnose−naive={md[0]:+.4f}±{md[1]:.4f} (t={md[2]:.2f}, n={md[3]})   "
          f"split−naive={ms[0]:+.4f}±{ms[1]:.4f} (t={ms[2]:.2f}, n={ms[3]})")

print("=" * 70)
print("E136 margin 扫描（报告: 0→+0.2122  0.02→+0.2072  0.05→+0.1797  0.10→+0.0580, n=40）")
e136 = load("res_e136.json")
for k in ("0.0", "0.02", "0.05", "0.1"):
    print(f"  margin {k:5s}: {mean(e136[k]):+.4f}  (n={len(e136[k])})")
d1 = pdiff(e136["0.02"], e136["0.0"])
d2 = pdiff(e136["0.05"], e136["0.0"])
print(f"  0 − 0.02 = {d1[0]:+.4f} (t={d1[2]:.2f})   0 − 0.05 = {d2[0]:+.4f} (t={d2[2]:.2f})  [报告 bootstrap: +0.0050 p=.0003 / +0.0325 p<.0001]")

print("=" * 70)
print("E137 clean vs trap（报告: clean 0→+0.1788 .02→+0.1730 .05→+0.1374; trap 0→+0.0238 .02→+0.0210 .05→+0.0065, n=24）")
e137 = load("res_e137.json")
for w in ("clean", "trap"):
    row = "  ".join(f"m{k}={mean(e137[f'{w}_{k}']):+.4f}" for k in ("0.0", "0.02", "0.05"))
    print(f"  {w:6s}: {row}")

print("=" * 70)
print("E137b（报告承认构造失败: clean sign−nogate=−0.0040 t=−1.17; trap +0.0023 t=1.21, n=16）")
e137b = load("res_e137b.json")
for w in ("clean", "trap"):
    m = pdiff(e137b[f"{w}_nogate"], e137b[f"{w}_sign"])
    print(f"  {w:6s}: sign−nogate={m[0]:+.4f} (t={m[2]:.2f}, n={m[3]})   "
          f"绝对水平 nogate={mean(e137b[f'{w}_nogate']):+.4f} sign={mean(e137b[f'{w}_sign']):+.4f}")
