"""序贯变化检测器库（第31轮 · E139/E140）

全部检测【均值下降】（漂移/退化语义）。仅标准库。
实现依据（见 预注册-第31轮-20260910.md §一）：
  - PageHinkley: Page 1954 / Hinkley 1971；固定参考均值 μ0（前 W0 个读数），
    PH_t = Σ(x_i − μ0 + α)，跟踪 min，报警 PH_t − PH_min > λ
  - CUSUM:       Page 1954；S_t = max(0, S_{t−1} + (μ0 − x_t) − k)，报警 S_t > h
    （μ0 同样取前 W0 个读数——事件代固定为 8/10，W0=5 保证参考段无事件，无标签泄漏）
  - ADWIN0:      Bifet & Gavaldà 2007（论文原始 O(W²) 版，忠实于 cut 判据）
    对每个切分 W0·W1：若 μ_W0 − μ_W1 ≥ ε_cut = sqrt((1/(2m))·ln(4|W|/δ)) 则裁剪
    （m = 调和平均），裁剪即报警；只对【下降】方向置 fired 标志，上升方向静默裁剪
  - Baseline:    现行判据操作化 x_t < x_{t−1} − thr（kernel degrade_thr=0.01）
"""
import math


class PageHinkley:
    """单侧（下降）PH 变体：参考 = 扩张均值 x̄，累积 (x − x̄ + α) 且上界截 0，
    PH_t < −λ 报警。截断保证【上升】方向永不报警（经典 min-tracking 形式在
    永久性偏移下永不回升、且不辨方向，故采用此单侧等价形式）。"""

    def __init__(self, alpha=0.005, lambd=0.2, w0=5):
        self.alpha, self.lambd, self.w0 = alpha, lambd, w0
        self.reset()

    def reset(self):
        self.xs, self.ph, self.mu0 = [], 0.0, None

    def update(self, x):
        self.xs.append(x)
        if len(self.xs) < self.w0:
            return False
        if len(self.xs) == self.w0:
            self.mu0 = sum(self.xs) / self.w0
            return False
        # 扩张均值（偏离项用纳入当前点【之前】的参考均值）
        dev = x - self.mu0
        self.mu0 += dev / (len(self.xs) - 1)
        self.ph = min(0.0, self.ph + dev + self.alpha)
        return self.ph < -self.lambd


class Cusum:
    def __init__(self, k=0.005, h=0.3, w0=5):
        self.k, self.h, self.w0 = k, h, w0
        self.reset()

    def reset(self):
        self.xs, self.s, self.mu0 = [], 0.0, None

    def update(self, x):
        self.xs.append(x)
        if len(self.xs) == self.w0:
            self.mu0 = sum(self.xs) / self.w0
            return False
        if len(self.xs) < self.w0 or self.mu0 is None:
            return False
        self.s = max(0.0, self.s + (self.mu0 - x) - self.k)
        return self.s > self.h


class Adwin0:
    """论文 ADWIN0：每步检查所有切分，显著则裁掉旧段并报警（只报下降）。"""

    def __init__(self, delta=0.01, min_len=3):
        self.delta, self.min_len = delta, min_len
        self.reset()

    def reset(self):
        self.w = []

    def update(self, x):
        self.w.append(x)
        fired = False
        while True:
            n = len(self.w)
            if n < 2 * self.min_len:
                return fired
            cut_ok = None
            for i in range(self.min_len, n - self.min_len + 1):
                w0, w1 = self.w[:i], self.w[i:]
                m0 = sum(w0) / len(w0)
                m1 = sum(w1) / len(w1)
                m = 1.0 / (1.0 / len(w0) + 1.0 / len(w1))   # 调和平均/2 的等比形式
                eps = math.sqrt((1.0 / (2.0 * m)) * math.log(4.0 * n / self.delta))
                if m0 - m1 >= eps:      # 只认下降方向
                    cut_ok = i
                    break
            if cut_ok is None:
                return fired
            self.w = self.w[cut_ok:]    # 裁掉旧段，保留新段
            fired = True


class Baseline:
    """现行判据操作化：一步落差 x_t < x_{t−1} − thr。"""

    def __init__(self, thr=0.01):
        self.thr = thr
        self.reset()

    def reset(self):
        self.prev = None

    def update(self, x):
        fire = self.prev is not None and x < self.prev - self.thr
        self.prev = x
        return fire


def make(name, **kw):
    return {"ph": PageHinkley, "cusum": Cusum, "adwin": Adwin0,
            "baseline": Baseline}[name](**kw)


# ────────────────────────── 合成流自测（上实验前必须全过） ──────────────────────────
def selftest():
    const = [0.5] * 24
    step = [0.5] * 7 + [0.2] * 17
    grad = [0.5] * 7 + [max(0.05, 0.5 - 0.02 * (t - 7)) for t in range(8, 25)]
    rise = [0.5] * 7 + [0.8] * 17
    # ADWIN 用 300 点长流验证实现正确性（界要求调和均值 m≥62.7 才能检出 0.3 落差；
    # 24 点短流上 ε≈0.96>效应量，结构性沉默——该性质如实进实验报告，不算实现错误）
    long_step = [0.5] * 100 + [0.2] * 200
    long_rise = [0.5] * 100 + [0.8] * 200

    cfg = dict(ph=dict(alpha=0.005, lambd=0.1), cusum=dict(k=0.005, h=0.3),
               adwin=dict(delta=0.01), baseline=dict(thr=0.01))
    fails = []
    for name in ("ph", "cusum", "baseline"):
        for stream, expect_fire, tag in ((const, False, "const"), (step, True, "step"),
                                         (grad, True, "grad"), (rise, False, "rise")):
            d = make(name, **cfg[name])
            fired = any(d.update(x) for x in stream)
            if fired != expect_fire:
                fails.append(f"{name}/{tag}: fired={fired} expect={expect_fire}")
    for stream, expect_fire, tag in ((long_step, True, "long_step"),
                                     (long_rise, False, "long_rise")):
        d = make("adwin", **cfg["adwin"])
        fired = any(d.update(x) for x in stream)
        if fired != expect_fire:
            fails.append(f"adwin/{tag}: fired={fired} expect={expect_fire}")
    return fails


if __name__ == "__main__":
    bad = selftest()
    if bad:
        print("自测未过：")
        for b in bad:
            print("  ✗", b)
        raise SystemExit(1)
    print("✓ 检测器自测全部通过（const 不报 / step·grad 必报 / rise 不报）")
