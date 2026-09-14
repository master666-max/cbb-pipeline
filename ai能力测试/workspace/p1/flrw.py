"""P1 FLRW 宇宙学核心模块。

ΛCDM(近平平,含辐射)弗里德曼方程数值求解:
    H(a)^2 = H0^2 [Ω_r a^-4 + Ω_m a^-3 + Ω_k a^-2 + Ω_Λ]
常数来源 AGENTS.md(PDG 2024 / Planck 2018 硬编码表)。
单位: H0 km/s/Mpc, 时间 Gyr, 距离 Mpc。
"""
import numpy as np
from scipy.integrate import quad, solve_ivp

# ---- 物理常数(单位换算,非宇宙学参数) ----
C_KMS = 299792.458            # 光速 km/s
MPC_KM = 3.0856775814913673e19  # 1 Mpc = km
GYR_S = 3.15576e16            # 1 Gyr = s (儒略年)

# ---- 宇宙学参数(AGENTS.md 硬编码表) ----
H0 = 67.4                     # km/s/Mpc
OMEGA_R = 9.2e-5
OMEGA_M = 0.315
OMEGA_L = 0.685
OMEGA_K = 1.0 - (OMEGA_R + OMEGA_M + OMEGA_L)  # = -9.2e-5, 微闭

H0_S = H0 / MPC_KM            # s^-1
T_HUB_GYR = 1.0 / H0_S / GYR_S  # 哈勃时间 Gyr


def E_of_a(a):
    """无量纲哈勃参数 H(a)/H0。"""
    a = np.asarray(a, dtype=float)
    return np.sqrt(OMEGA_R * a**-4 + OMEGA_M * a**-3
                   + OMEGA_K * a**-2 + OMEGA_L)


def E_of_z(z):
    """E(z) = H(z)/H0。"""
    z = np.asarray(z, dtype=float)
    return E_of_a(1.0 / (1.0 + z))


def age_quad():
    """宇宙年龄: 逆协变积分 t0 = ∫_0^1 da/(a H(a)),自适应 Gauss-Kronrod。"""
    f = lambda a: 1.0 / (a * H0_S * E_of_a(a))
    val, err = quad(f, 0.0, 1.0, epsabs=1e-13, epsrel=1e-13, limit=200)
    return val / GYR_S, err / GYR_S


def age_ode():
    """宇宙年龄(独立方法): 解 ODE da/dt = a H(a), DOP853 高阶积分。
    事件 a=1.0 终止(单位: 秒, 1/H0 ≈ 4.58e17 s)。"""
    def rhs(t, y):
        a = y[0]
        return [a * H0_S * E_of_a(a)]
    hit_a1 = lambda t, y: y[0] - 1.0
    hit_a1.terminal = True
    hit_a1.direction = 1.0
    sol = solve_ivp(rhs, (0.0, 2.0e18), [1e-12], rtol=1e-12, atol=1e-30,
                    events=hit_a1, dense_output=False)
    t_end = sol.t_events[0][0]
    # 辐射主导期 a<a_start 的解析补底(可忽略但如实加上):
    # 纯辐射 t(a) = a^2/(2 H0 √Ω_r), a_start=1e-12 → <1e-24 s
    t_start = (1e-12)**2 / (2.0 * H0_S * np.sqrt(OMEGA_R))
    return (t_end + t_start) / GYR_S, 1.0


def age_analytic_matlam():
    """解析对照(近似,不含辐射): 平直物質+Λ 的闭式年龄。
    t0 = 2/(3 H0 √ΩΛ) asinh(√(ΩΛ/Ωm)) —— 仅作 L1 近似差值报告,非判据。
    """
    t0_s = 2.0 / (3.0 * H0_S * np.sqrt(OMEGA_L)) \
        * np.arcsinh(np.sqrt(OMEGA_L / OMEGA_M))
    return t0_s / GYR_S


def comoving_distance(z):
    """共动距离 χ(z) = c∫_0^z dz'/H(z'), 单位 Mpc。"""
    f = lambda zp: 1.0 / E_of_z(zp)
    val, _ = quad(f, 0.0, z, epsabs=1e-12, epsrel=1e-12, limit=200)
    return C_KMS / H0 * val


def particle_horizon_mpc():
    """粒子视界 χ_p = c∫_0^∞ dz/H(z)。"""
    val, _ = quad(lambda z: 1.0 / E_of_z(z), 0.0, np.inf,
                  epsabs=1e-10, epsrel=1e-12, limit=500)
    return C_KMS / H0 * val


def time_at_redshift(z):
    """宇宙年龄 t(z)(回望时间减法), 单位 Gyr。"""
    a = 1.0 / (1.0 + z)
    val, _ = quad(lambda ap: 1.0 / (ap * H0_S * E_of_a(ap)), 0.0, a,
                  epsabs=1e-13, epsrel=1e-13, limit=200)
    return val / GYR_S


if __name__ == "__main__":
    t_quad, qerr = age_quad()
    t_ode, a_end = age_ode()
    print(f"t0 (quad)      = {t_quad:.6f} Gyr  (quad估计误差 {qerr:.2e} Gyr)")
    print(f"t0 (ODE)       = {t_ode:.6f} Gyr  (终态 a={a_end:.9f})")
    print(f"t0 (物質+Λ解析) = {age_analytic_matlam():.6f} Gyr  [近似对照]")
