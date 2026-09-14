"""P2 BBN 核心: 弱冻结 n/p 比率 + 氘瓶颈 + Y_p。

物理输入(全部第一性原理或标准常数):
  Q = m_n - m_p = 1.293332 MeV, m_e = 0.510999 MeV(PDG)
  τ_n = 880.2 s(AGENTS.md)
  η_b = 6.1e-10(Planck 2018 Ω_b h²=0.0224 换算, 见 L1 说明)
弱率 λ(T) 由 e±/ν 费米-狄拉克浴的精确相空间积分给出,
常数矩阵元, 归一化由零温 β 衰变率 λ(T=0)=1/τ_n 固定 —— 因此
G_F、g_A 从不出现, 无自由参数。
中微子温度 T_ν 由 e± 灭绝的熵守恒逐点确定。
"""
import numpy as np
from scipy.integrate import quad, solve_ivp
from scipy.optimize import brentq

# ---- 常数 ----
TAU_N = 880.2          # s
Q_NP = 1.293332        # MeV, 中子-质子质量差
M_E = 0.510999         # MeV
ETA_B = 6.1e-10        # 重子-光子比(辅助常数, Planck)
B_D = 2.224566         # MeV, 氘结合能
MEV_TO_S = 1.0 / (1.5192674e21)   # 1 MeV(自然单位) = 6.582e-22 s
S_TO_MEV = 1.5192674e21
G_NAT = 6.708e-45      # MeV^-2, 引力常数(G_F 体系不需要)
N_NU = 3.0


def _fd(E, T):
    """费米-狄拉克分布(零化学势), T<=0 时返回 0。"""
    if T <= 0:
        return np.zeros_like(E)
    x = np.asarray(E / T)
    out = np.empty_like(x)
    small = x < 700
    out[small] = 1.0 / (np.exp(x[small]) + 1.0)
    out[~small] = 0.0
    return out


# ============ 弱过程率 ============
# 归一化: I_beta = ∫_0^Q p_e E_e (Q-E_e)^2 dE_e,  K = 1/(τ_n · I_beta)

def _I_beta():
    f = lambda E: np.sqrt(max(E**2 - M_E**2, 0.0)) * E * (Q_NP - E)**2
    val, _ = quad(f, M_E, Q_NP, epsabs=1e-12, epsrel=1e-13, limit=200)
    return val

_I_BETA = _I_beta()
_K_RATE = 1.0 / (TAU_N * _I_BETA)   # s^-1 MeV^-5 (作用量单位换算含在积分内)


def lam_beta(T_gamma, T_nu):
    """n → p e⁻ ν̄(含两末态费米阻塞)。T→0 时精确 = 1/τ_n。"""
    f = lambda E: (np.sqrt(E**2 - M_E**2) * E * (Q_NP - E)**2
                   * (1.0 - _fd(E, T_gamma))
                   * (1.0 - _fd(Q_NP - E, T_nu)))
    val, _ = quad(f, M_E, Q_NP, epsabs=1e-14, epsrel=1e-10, limit=200)
    return _K_RATE * val


def lam_nu_abs(T_nu, T_gamma):
    """n + ν̄ → p + e⁻(阈值 E_ν > Q + m_e, 末态 e⁻ 阻塞)。"""
    if T_nu <= 0:
        return 0.0
    f = lambda Enu: (np.sqrt((Enu - Q_NP)**2 - M_E**2) * (Enu - Q_NP)
                     * Enu**2 * float(_fd(Enu, T_nu))
                     * (1.0 - _fd(Enu - Q_NP, T_gamma)))
    val, _ = quad(f, Q_NP + M_E, 60.0 * T_nu + Q_NP + M_E + 1.0,
                  epsabs=1e-16, epsrel=1e-9, limit=300)
    return _K_RATE * val


def lam_e_capture(T_gamma, T_nu):
    """n + e⁺ → p + ν̄(放能无阈值, 末态 ν̄ 阻塞)。"""
    if T_gamma <= 0:
        return 0.0
    f = lambda E: (np.sqrt(E**2 - M_E**2) * E * (Q_NP + E)**2
                   * float(_fd(E, T_gamma))
                   * (1.0 - _fd(Q_NP + E, T_nu)))
    val, _ = quad(f, M_E, 60.0 * T_gamma + M_E + 1.0,
                  epsabs=1e-16, epsrel=1e-9, limit=300)
    return _K_RATE * val


def lam_np_total(T_gamma, T_nu):
    """n→p 总转化率 s^-1(β衰变 + ν̄吸收 + e⁺捕获)。"""
    return lam_beta(T_gamma, T_nu) + lam_nu_abs(T_nu, T_gamma)         + lam_e_capture(T_gamma, T_nu)


def lam_pn_total(T_gamma, T_nu):
    """p→n 总转化率: 精细平衡闭合 λ_pn = e^{-Q/T_γ} λ_np。
    (显式 p→n 相空间积分的结构性困难见 AUDIT L1; 冻结期 T_ν/T_γ>0.99,
    浴温差的修正 <1%。与 Kawano/Mukhanov 标准处理一致。)"""
    return np.exp(-Q_NP / T_gamma) * lam_np_total(T_gamma, T_nu)


# ============ 辐射热力学(e± 灭绝精确处理) ============

def rho_gamma(T):
    return (np.pi**2 / 15.0) * T**4


def rho_e_pairs_exact(T):
    """e± 能量密度: g_total=4(2 自旋 × 正负电子), ρ = g/(2π²)∫ p² E f dE。"""
    f = lambda p: (p**2 * np.sqrt(p**2 + M_E**2)
                   / (np.exp(np.sqrt(p**2 + M_E**2) / T) + 1.0))
    val, _ = quad(f, 0.0, 60.0 * T, epsabs=1e-14, epsrel=1e-11, limit=400)
    return (4.0 / (2.0 * np.pi**2)) * val


def press_e_pairs(T):
    """e± 压强: P = g/(2π²)∫ p⁴/E f dp /3 → g/(6π²)∫ p⁴/E f dp。"""
    f = lambda p: (p**4 / np.sqrt(p**2 + M_E**2)
                   / (np.exp(np.sqrt(p**2 + M_E**2) / T) + 1.0))
    val, _ = quad(f, 0.0, 60.0 * T, epsabs=1e-14, epsrel=1e-11, limit=400)
    return (4.0 / (6.0 * np.pi**2)) * val


def T_nu_of_T(T):
    """熵守恒给出的中微子温度: T_ν = T (g_s,eγ(T)/5.5)^{1/3}。
    e± 灭绝前 g_s=5.5 → T_ν=T; 灭绝后 g_s→2 → T_ν/T→(2/5.5)^{1/3}=(4/11)^{1/3}。"""
    if T > 5.0 * M_E:
        return T
    rho = rho_e_pairs_exact(T)
    P = press_e_pairs(T)
    s_e_g = (rho + P) / T + rho_gamma(T) * (4.0 / 3.0) / T
    g_s = 45.0 * s_e_g / (2.0 * np.pi**2 * T**3)
    return T * (g_s / 5.5) ** (1.0 / 3.0)


def rho_total(T):
    """总辐射能量密度 MeV^4(γ + e± + 3 味中微子 at T_ν)。"""
    Tnu = T_nu_of_T(T)
    rho_nu = N_NU * (7.0 / 8.0) * (np.pi**2 / 15.0) * Tnu**4
    return rho_gamma(T) + rho_e_pairs_exact(T) + rho_nu


def g_star_rho(T):
    return 30.0 * rho_total(T) / (np.pi**2 * T**4)


def H_of_T(T):
    """哈勃率 s^-1(T 光子温度 MeV)。"""
    rho = rho_total(T)
    H_nat = np.sqrt(8.0 * np.pi * G_NAT * rho / 3.0)  # MeV
    return H_nat * S_TO_MEV


def g_star_s_total(T):
    """总熵系数(相对光子温度 T)。"""
    Tnu = T_nu_of_T(T)
    rho = rho_total(T)
    # 各分量熵: γ+e± 用 (ρ+P)/T; ν 用相对论式
    rho_e = rho_e_pairs_exact(T)
    P_e = press_e_pairs(T)
    s_eg = (rho_gamma(T) * 4.0 / 3.0 + rho_e + P_e) / T
    s_nu = N_NU * (7.0 / 8.0) * (4.0 / 3.0) * (np.pi**2 / 15.0) * Tnu**3
    s_tot = s_eg + s_nu
    return 45.0 * s_tot / (2.0 * np.pi**2 * T**3)


def dt_dT(T):
    """dt/dT < 0(熵守恒修正)。单位 s/MeV。"""
    Tn = T_nu_of_T(T)
    # d ln g_s/dT 数值微商(中心差分)
    h = 1e-3 * T
    gs1 = g_star_s_total(max(T - h, 1e-8))
    gs2 = g_star_s_total(T + h)
    dlngs = (np.log(gs2) - np.log(gs1)) / (2.0 * h)
    return -(1.0 + T / 3.0 * dlngs) / (H_of_T(T) * T)


# ============ n/p 冻结 ODE ============

def integrate_np(T_start=20.0, T_end=0.02, rtol=1e-10):
    """从 T_start(平衡初始条件)积到 T_end。
    返回 (T 数组, r=n_n/n_b 数组, t 数组)。"""
    def rhs(T, y):
        r, t = y          # r = n_n/n_b, t = 时间 s
        Tnu = T_nu_of_T(T)
        lnp = lam_np_total(T, Tnu)
        lpn = lam_pn_total(T, Tnu)
        drdt = -lnp * r + lpn * (1.0 - r)
        return [drdt * dt_dT(T), dt_dT(T)]

    r0 = 1.0 / (1.0 + np.exp(Q_NP / T_start))  # 平衡 n/n_b
    sol = solve_ivp(rhs, (T_start, T_end), [r0, 0.0],
                    method="Radau", rtol=rtol, atol=1e-14,
                    dense_output=True, max_step=0.05)
    return sol.t, sol.y[0], sol.y[1]


def _saha_R_D(T):
    """Saha 系数 n_D/(n_p n_n), 单位 MeV^-3。"""
    m_p, m_n, m_d = 938.272, 939.565, 1875.613  # MeV
    # n_D/(n_p n_n) = (3/4)(2π m_D/(m_p m_n T))^{3/2} e^{B_D/T}
    # 注意是 m_D 本身(非约化质量), T 幂次为 -3/2
    return 0.75 * (2.0 * np.pi * m_d / (m_p * m_n) / T) ** 1.5 * np.exp(B_D / T)


def _n_gamma(T):
    return (2.0 * 1.2020569) / np.pi**2 * T**3


def deuterium_xD(T, r_n):
    """给定自由中子占比 r_n=n_n/n_b, Saha 二次方程小根求 n_D/n_b。
    n_D = R(n_p0-n_D)(n_n0-n_D) 的有界小根(数值稳定式)。"""
    R = _saha_R_D(T)
    n_b = ETA_B * _n_gamma(T)
    n_p0, n_n0 = (1.0 - r_n) * n_b, r_n * n_b
    s = 1.0 + R * (n_p0 + n_n0)
    disc = np.sqrt(max(s * s - 4.0 * R * R * n_p0 * n_n0, 0.0))
    n_D = 2.0 * R * n_p0 * n_n0 / (s + disc)
    return n_D / n_b


def deuterium_bottleneck_T(r_of_T):
    """氘瓶颈开启温度: 一半中子进入 D(n_D = 0.5·r_n(T)·n_b), 与 n/p 解自洽。"""
    T_guess = 0.08
    for _ in range(50):
        r_n = float(r_of_T(T_guess))
        f = lambda T: deuterium_xD(T, r_n) - 0.5 * r_n
        T_new = brentq(f, 0.02, 0.2, xtol=1e-12)
        if abs(T_new - T_guess) < 1e-10:
            T_guess = T_new
            break
        T_guess = T_new
    r_n = float(r_of_T(T_guess))
    return T_guess, r_n


def compute_Yp():
    """主计算: 积分 n/p 至氘瓶颈温度, Y_p = 2r/(1+r)。"""
    Ts, rs, ts = integrate_np(T_start=20.0, T_end=0.02)
    sol_r = lambda Tq: np.interp(Tq, Ts[::-1], rs[::-1])
    sol_t = lambda Tq: np.interp(Tq, Ts[::-1], ts[::-1])
    T_d, r_d = deuterium_bottleneck_T(sol_r)
    t_d = float(sol_t(T_d))
    Yp = 2.0 * r_d / (1.0 + r_d)
    return Yp, r_d, T_d, t_d


if __name__ == "__main__":
    # 自检: 归一化(零温=自由衰变), 高温平衡, 冻结温度量级
    print("I_beta =", _I_BETA, "MeV^5")
    print("λ(T=1e-6 MeV) =", lam_np_total(1e-6, 1e-6), "s^-1 (应=1/880.2=",
          1.0 / TAU_N, ")")
    for Tg in [5.0, 2.0, 1.0, 0.8, 0.6, 0.4, 0.2, 0.1]:
        Tnu = T_nu_of_T(Tg)
        lnp = lam_np_total(Tg, Tnu)
        lpn = lam_pn_total(Tg, Tnu)
        H = H_of_T(Tg)
        print(f"T={Tg:5.2f} Tν={Tnu:5.3f} λ_np={lnp:10.4g} λ_pn={lpn:10.4g} "
              f"λ/H={lnp/H:8.3f} g*={g_star_rho(Tg):6.3f}")
    Yp, r, Td, tB = compute_Yp()
    print(f"\n氘瓶颈 T = {Td:.4f} MeV, t(T_d) = {tB:.1f} s")
    print(f"n/p at T_d = {r/(1-r):.4f}")
    print(f"Y_p = {Yp:.4f}")
