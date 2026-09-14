"""P1 独立数值验证器。

判据: 宇宙年龄相对 Planck 2018 参考值 13.797 Gyr 误差 < 0.5%。
交叉验证: quad vs ODE 双方法一致性;近似公式差值(进 AUDIT L1)。
外部锚点(非判据,文献记忆值,容差宽松): 粒子视界 ~14.2 Gpc,
z* 角度直径距离 ~12.7 Gpc, z_eq ~ 3400。
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from flrw import (H0, OMEGA_R, OMEGA_M, OMEGA_L, T_HUB_GYR,
                  age_quad, age_ode, age_analytic_matlam,
                  comoving_distance, particle_horizon_mpc,
                  time_at_redshift, E_of_z, C_KMS)

T0_REF = 13.797  # Gyr, Planck 2018 TT,TE,EE+lowE+lensing 发表值(外部参考)
HORIZON_REF = 14260.0   # Mpc ≈ 46.5 Gly,文献记忆值(宽松锚点)
CHI_ZS_REF = 13870.0    # Mpc, Planck 参数下到 z*≈1090 的共动距离(宽松锚点)

def main():
    ok_all = True

    # --- 1) 两方法一致性 ---
    t_quad, qerr = age_quad()
    t_ode, a_end = age_ode()
    d_rel = abs(t_quad - t_ode) / t_quad
    print(f"[1] quad t0 = {t_quad:.6f} Gyr | ODE t0 = {t_ode:.6f} Gyr "
          f"(ODE终态 a={a_end:.9f})")
    print(f"    双方法相对差 = {d_rel:.3e}  (要求 < 1e-6)")
    ok = d_rel < 1e-6
    print(f"    -> {'PASS' if ok else 'FAIL'}")
    ok_all &= ok

    # --- 2) 主判据: vs Planck 13.797 Gyr ---
    err_pct = abs(t_quad - T0_REF) / T0_REF * 100.0
    print(f"[2] t0(计算) = {t_quad:.4f} Gyr vs 参考 {T0_REF} Gyr")
    print(f"    误差 = {err_pct:.4f}%  (判据 < 0.5%)")
    ok = err_pct < 0.5
    print(f"    -> {'PASS' if ok else 'FAIL'}")
    ok_all &= ok

    # --- 3) 近似公式差(辐射项影响, L1 素材) ---
    t_ap = age_analytic_matlam()
    print(f"[3] 物質+Λ解析(无辐射) t0 = {t_ap:.4f} Gyr, "
          f"与全模型差 {t_quad - t_ap:+.4f} Gyr ({(t_quad-t_ap)/t_quad*100:+.3f}%)")

    # --- 4) 辐射-物质平等期 ---
    a_eq = OMEGA_R / OMEGA_M
    z_eq = 1.0 / a_eq - 1.0
    T_eq = 2.7255 * (1.0 + z_eq)
    print(f"[4] a_eq = {a_eq:.6e}, z_eq = {z_eq:.1f} (文献~3400), "
          f"T_eq = {T_eq:.0f} K")

    # --- 5) 距离锚点 ---
    chi_h = particle_horizon_mpc()
    print(f"[5] 粒子视界 = {chi_h:.1f} Mpc vs 锚点 {HORIZON_REF} Mpc, "
          f"偏差 {abs(chi_h-HORIZON_REF)/HORIZON_REF*100:.2f}%")
    z_s = 1089.92
    chi_s = comoving_distance(z_s)
    dA_s = chi_s / (1.0 + z_s)
    print(f"    χ(z*=1089.92) = {chi_s:.1f} Mpc vs 锚点 {CHI_ZS_REF} Mpc, "
          f"偏差 {abs(chi_s-CHI_ZS_REF)/CHI_ZS_REF*100:.2f}% "
          f"(物理 D_A = {dA_s:.2f} Mpc)")

    # --- 6) 回望时间单调性/边界 sanity ---
    t_z0 = time_at_redshift(0.0)
    t_z1 = time_at_redshift(1.0)
    t_z10 = time_at_redshift(10.0)
    print(f"[6] t(z=0)={t_z0:.4f}, t(z=1)={t_z1:.4f}, t(z=10)={t_z10:.4f} Gyr "
          f"(单调递减 {'PASS' if t_z0>t_z1>t_z10 else 'FAIL'})")
    ok_all &= (t_z0 > t_z1 > t_z10)

    # --- 7) E(0) 恒等 ---
    e0 = float(E_of_z(0.0))
    print(f"[7] E(0) = {e0:.15f} (应=1)")
    ok_all &= abs(e0 - 1.0) < 1e-14

    print("\n=== P1 总判定:", "PASS" if ok_all else "FAIL", "===")
    return 0 if ok_all else 1

if __name__ == "__main__":
    sys.exit(main())
