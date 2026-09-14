"""P2 约化 BBN 核网络: n, p, D, t, He3, He4。

率来源: 带电反应用 S 因子 Gamow 积分(数值精确),
  ⟨σv⟩ = √(8/(πμ)) (kT)^{-3/2} ∫ S(E) exp(-E/kT - √(E_G/E)) dE
S(0) 值[UNCERTAIN, 记忆来源, 见 AUDIT L1]:
  d(p,γ)³He   2.16e-4 keV·b   (著名值 2.1-2.5e-4)
  d(d,n)³He   55.4  keV·b
  d(d,p)t     55.6  keV·b
  t(d,n)⁴He   1.20e4 keV·b   (交叉验证: 由此得 σ_DT(126keV)≈2.5b, 文献~3-5b)
  ³He(d,p)⁴He 6.0e3 keV·b
中子反应:
  p(n,γ)d     热截面 0.332 b × 1/v 放能律 → ⟨σv⟩=7.3e-20 cm³/s
  ³He(n,p)t   热截面 5330 b × 1/v → ⟨σv⟩=1.17e-15 cm³/s
D 光致分解: 细致平衡 λ_γD = λ_pnγ / Saha_R(T)。
略去: t+t, He3+He3, Li7/Be7 链(对 Y_p/D/H 影响 <1e-3, L1 说明)。
"""
import numpy as np
from scipy.integrate import quad, solve_ivp
import bbn

# ---- 单位 ----
KEV_ERG = 1.602176634e-9      # 1 keV = erg
MEV_ERG = 1.602176634e-6
BARN = 1.0e-24                # cm^2
U_G = 1.66053906660e-24       # 1 u = g
C_CGS = 2.99792458e10         # cm/s
ALPHA = 1.0 / 137.035999
MEV_TO_INVCM = 5.0677307e10  # 1 MeV = cm^-1 (ħc)

# ---- S 因子 (keV·b) ----
S_DPG = 2.16e-4
S_DDN = 55.4
S_DDP = 55.6
S_TDN = 1.20e4
S_HE3DP = 6.0e3
SIGMAV_PNG = 0.332e-24 * 2.2e5      # cm^3/s (0.332b × 热速度)
SIGMAV_HE3NP = 5330e-24 * 2.2e5    # cm^3/s

# 核质量 (MeV)
M_P, M_N, M_D, M_T, M_HE3, M_HE4 = 938.272, 939.565, 1875.613, 2808.921, 2808.391, 3727.379


def _egamow_mu(Z1Z2, m1_mev, m2_mev):
    """Gamow 能量 (erg) 与约化质量 (g)。"""
    mu_mev = m1_mev * m2_mev / (m1_mev + m2_mev)
    mu_g = mu_mev * 1.78266192e-27      # 1 MeV/c² = g
    E_G = 2.0 * mu_mev * MEV_ERG * (np.pi * ALPHA * Z1Z2) ** 2
    return E_G, mu_g


def sigmav_charged(T_mev, S_kevb, Z1Z2, m1, m2):
    """S 因子 Gamow 积分, 返回 cm^3/s。"""
    kT = T_mev * MEV_ERG
    E_G, mu = _egamow_mu(Z1Z2, m1, m2)
    S = S_kevb * KEV_ERG * BARN       # erg·cm²
    # 积分上限: E_G(足够远); 数值替换 √(E_G/E) 在 E→0 奇异 → 换元 E = E_G/t²
    f = lambda t: (S * (2.0 * E_G / t**3) *
                   np.exp(-E_G / (t * t * kT) - t))
    val, _ = quad(f, 1.0, 60.0, epsabs=1e-30, epsrel=1e-9, limit=300)
    pref = np.sqrt(8.0 / (np.pi * mu)) * kT ** -1.5
    return pref * val


class Rates:
    """给定 T(MeV) 的网络速率(每秒, 相对数密度 n[cm^-3])。"""

    def __init__(self):
        self._cache = {}

    def get(self, T):
        key = round(T, 12)
        if key in self._cache:
            return self._cache[key]
        kT = T * MEV_ERG
        n_gamma_cm3 = bbn._n_gamma(T) * MEV_TO_INVCM ** 3
        n_b = bbn.ETA_B * n_gamma_cm3
        r = {}
        r['dpg'] = sigmav_charged(T, S_DPG, 1, M_P, M_D)
        r['ddn'] = sigmav_charged(T, S_DDN, 1, M_D, M_D)
        r['ddp'] = sigmav_charged(T, S_DDP, 1, M_D, M_D)
        r['tdn'] = sigmav_charged(T, S_TDN, 1, M_T, M_D)
        r['he3dp'] = sigmav_charged(T, S_HE3DP, 1, M_HE3, M_D)
        r['png'] = SIGMAV_PNG
        r['he3np'] = SIGMAV_HE3NP
        r['n_gamma_cm3'] = n_gamma_cm3
        r['n_b'] = n_b
        # D 光致分解率: λ_γD = λ_pnγ·n_p n_n/n_D|eq → 用 Saha:
        # n_D/(n_p n_n) = R(T) → λ_γD = σv_png / R(T)(MeV^-3 → cm^3 换算)
        R_mev3 = bbn._saha_R_D(T)                     # MeV^-3
        R_cm3 = R_mev3 * MEV_TO_INVCM ** -3            # cm^3
        r['lam_gD'] = r['png'] / R_cm3
        self._cache[round(T, 12)] = r
        return r


def run_network(T_start=0.10, T_end=0.02, Y_init=None, rates=None):
    """积分 6 分量网络。Y = [n, p, D, t, He3, He4](数密度比)。"""
    rates = rates or Rates()
    Ts_np, rs_np, ts_np = bbn.integrate_np(T_start=20.0, T_end=T_end)
    r_at = lambda Tq: float(np.interp(Tq, Ts_np[::-1], rs_np[::-1]))

    if Y_init is None:
        r_n = r_at(T_start)
        # D 初值取 Saha(远低于瓶颈时被光致分解钳制)
        xD = bbn.deuterium_xD(T_start, r_n)
        Y = np.array([max(r_n - xD, 1e-30), 1.0 - r_n - xD, xD, 0.0, 0.0, 0.0])
    else:
        Y = np.array(Y_init, dtype=float)

    def rhs(T, y):
        Yn, Yp, Yd, Yt, Y3, Y4 = y
        y = np.abs(y)
        Yn, Yp, Yd, Yt, Y3, Y4 = y
        r = rates.get(T)
        nb = r['n_b']
        dYdt = np.zeros(6)
        # n 衰变(弱率: 低温只剩 β衰变 1/τ)
        lam_decay = 1.0 / bbn.TAU_N
        # 1) p(n,γ)d 及逆(光致分解)
        dYdt[0] += -r['png'] * Yn * Yp * nb - lam_decay * Yn + r['lam_gD'] * Yd
        dYdt[1] += -r['png'] * Yn * Yp * nb + r['lam_gD'] * Yd + r['he3np'] * Y3 * Yn * nb
        dYdt[2] += r['png'] * Yn * Yp * nb - r['lam_gD'] * Yd
        # 2) d(p,γ)He3
        dYdt[2] += -r['dpg'] * Yd * Yp * nb
        dYdt[1] += -r['dpg'] * Yd * Yp * nb
        dYdt[4] += r['dpg'] * Yd * Yp * nb
        # 3) d(d,n)He3(消耗 2 个 D)
        dYdt[2] += -2.0 * r['ddn'] * Yd * Yd * nb
        dYdt[0] += r['ddn'] * Yd * Yd * nb
        dYdt[4] += r['ddn'] * Yd * Yd * nb
        # 4) d(d,p)t(消耗 2 个 D)
        dYdt[2] += -2.0 * r['ddp'] * Yd * Yd * nb
        dYdt[1] += r['ddp'] * Yd * Yd * nb
        dYdt[3] += r['ddp'] * Yd * Yd * nb
        # 5) t(d,n)He4
        dYdt[3] += -r['tdn'] * Yt * Yd * nb
        dYdt[2] += -r['tdn'] * Yt * Yd * nb
        dYdt[0] += r['tdn'] * Yt * Yd * nb
        dYdt[5] += r['tdn'] * Yt * Yd * nb
        # 6) He3(d,p)He4
        dYdt[4] += -r['he3dp'] * Y3 * Yd * nb
        dYdt[2] += -r['he3dp'] * Y3 * Yd * nb
        dYdt[1] += r['he3dp'] * Y3 * Yd * nb
        dYdt[5] += r['he3dp'] * Y3 * Yd * nb
        # 7) He3(n,p)t
        dYdt[4] += -r['he3np'] * Y3 * Yn * nb
        dYdt[0] += -r['he3np'] * Y3 * Yn * nb
        dYdt[3] += r['he3np'] * Y3 * Yn * nb
        # n 衰变产物进 p
        dYdt[1] += lam_decay * Yn
        return dYdt * bbn.dt_dT(T)

    sol = solve_ivp(rhs, (T_start, T_end), Y, method='Radau',
                    rtol=1e-8, atol=1e-14, dense_output=True)
    return sol


def summarize(sol):
    Y = np.abs(sol.y[:, -1])
    Yn, Yp, Yd, Yt, Y3, Y4 = Y
    Yp_mass = 4.0 * Y4  # Σ A·Y = 1 守恒
    DH = Yd / max(Yp, 1e-30)
    return dict(Yn=Yn, Yp=Yp, Yd=Yd, Yt=Yt, Y3=Y3, Y4=Y4,
                Yp_mass=Yp_mass, DH=DH)


if __name__ == "__main__":
    sol = run_network()
    s = summarize(sol)
    print("终态丰度(T=0.02 MeV):")
    for k in ['Yn', 'Yp', 'Yd', 'Yt', 'Y3', 'Y4']:
        print(f"  {k} = {s[k]:.6e}")
    print(f"Y_p(质量分数) = {s['Yp_mass']:.4f}  (参考 0.247)")
    print(f"D/H = {s['DH']:.4e}  (参考 2.45e-5)")
    # 守恒检查: Σ A_i Y_i = 1
    tot = 1 * (s['Yn'] + s['Yp']) + 2 * s['Yd'] + 3 * (s['Yt'] + s['Y3']) + 4 * s['Y4']
    print(f"重子数守恒 ΣA·Y = {tot:.10f} (应=1)")
