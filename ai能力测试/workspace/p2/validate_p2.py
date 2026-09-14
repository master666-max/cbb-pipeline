"""P2 独立数值验证器。

判据: |Y_p - 0.247| < 0.003。
实测(2026-09-14): Y_p = 0.3068(网络) → 误差 +0.0598 → 判据 FAIL → BLOCKED。
已执行 3 轮实质修复: ①末态费米阻塞补全 ②p→n 用精细平衡闭合
③Gamow 积分 E_G 双重计数 + dd 反应重子记账。每轮均改善物理正确性,
Y_p 仍高的根因: 有效冻结温度偏高(T_eff≈0.85 vs 全网络码 ~0.74),
半解析率的弛豫在 T≈1 MeV 处不足, 平衡追踪提前失守。
D/H = 2.83e-5 vs 参考 2.45e-5(+15%), S 因子为记忆值 → UNCERTAIN。
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import bbn, network as nw

YP_REF = 0.247
DH_REF = 2.45e-5


def main():
    ok_all = True
    results = {}

    # --- 1) 弱率归一化: T→0 精确回到自由中子衰变 ---
    lam0 = bbn.lam_np_total(1e-6, 1e-6)
    rel = abs(lam0 - 1.0 / bbn.TAU_N) * bbn.TAU_N
    print(f"[1] λ_np(T→0) = {lam0:.12e} s^-1 vs 1/τ_n = {1.0/bbn.TAU_N:.12e}, "
          f"相对差 {rel:.2e}  (要求 < 1e-12)")
    ok = rel < 1e-12
    print(f"    -> {'PASS' if ok else 'FAIL'}"); ok_all &= ok

    # --- 2) 精细平衡(等温浴, β 道贡献可忽略区) ---
    T = 2.0
    ratio = bbn.lam_pn_total(T, T) / bbn.lam_np_total(T, T)
    expect = np.exp(-bbn.Q_NP / T)
    dev = abs(ratio - expect) / expect
    print(f"[2] λ_pn/λ_np(T=2, 等温) = {ratio:.8f} vs e^(-Q/T) = {expect:.8f}, "
          f"偏差 {dev:.2e}  (构造上恒等, 要求 < 1e-12)")
    ok = dev < 1e-12
    print(f"    -> {'PASS' if ok else 'FAIL'}"); ok_all &= ok

    # --- 3) t-T 关系锚点 ---
    Ts, rs, ts = bbn.integrate_np(T_start=20.0, T_end=0.03)
    t1 = float(np.interp(1.0, Ts[::-1], ts[::-1]))
    t01 = float(np.interp(0.1, Ts[::-1], ts[::-1]))
    print(f"[3] t(T=1 MeV) = {t1:.3f} s (标准 0.738 s, 偏 "
          f"{abs(t1-0.738)/0.738*100:.1f}%); t(T=0.1 MeV) = {t01:.1f} s "
          f"(标准 ~130 s, 偏 {abs(t01-130)/130*100:.1f}%)")

    # --- 4) 冻结温度(Γ = H) ---
    from scipy.optimize import brentq
    f_ratio = lambda T: (bbn.lam_np_total(T, bbn.T_nu_of_T(T))
                         + bbn.lam_pn_total(T, bbn.T_nu_of_T(T))) / bbn.H_of_T(T) - 1.0
    T_f = brentq(f_ratio, 0.5, 1.2, xtol=1e-8)
    print(f"[4] Γ_wn = H 处 T_f = {T_f:.3f} MeV (文献 0.7-0.8)")

    # --- 5) 氘瓶颈 ---
    r_at = lambda Tq: float(np.interp(Tq, Ts[::-1], rs[::-1]))
    T_d, r_d = bbn.deuterium_bottleneck_T(r_at)
    t_d = float(np.interp(T_d, Ts[::-1], ts[::-1]))
    print(f"[5] 氘瓶颈 T_d = {T_d:.4f} MeV (文献 0.066-0.07), "
          f"t(T_d) = {t_d:.1f} s (文献 ~200-300)")

    # --- 6) 主判据: 网络 Y_p ---
    sol = nw.run_network(T_start=0.10, T_end=0.02)
    s = nw.summarize(sol)
    err = abs(s['Yp_mass'] - YP_REF)
    print(f"[6] Y_p(网络, 4Y_He4) = {s['Yp_mass']:.4f} vs 参考 {YP_REF}, "
          f"误差 {s['Yp_mass']-YP_REF:+.4f}  (判据 |err|<0.003)")
    ok = err < 0.003
    print(f"    -> {'PASS' if ok else 'FAIL'}")
    ok_all &= ok
    results['Yp'] = s['Yp_mass']

    # --- 7) D/H ---
    dh_err = (s['DH'] - DH_REF) / DH_REF * 100
    print(f"[7] D/H = {s['DH']:.3e} vs 参考 {DH_REF}, 偏差 {dh_err:+.1f}% "
          f"(S 因子记忆值, UNCERTAIN)")

    # --- 8) 重子守恒 ---
    tot = (s['Yn'] + s['Yp'] + 2 * s['Yd'] + 3 * (s['Yt'] + s['Y3'])
           + 4 * s['Y4'])
    print(f"[8] ΣA·Y = {tot:.10f} (应=1, 偏差 {abs(tot-1):.2e})")
    ok = abs(tot - 1) < 1e-6
    print(f"    -> {'PASS' if ok else 'FAIL'}"); ok_all &= ok

    print("\n=== P2 总判定:", "PASS" if ok_all else "FAIL(BLOCKED: Y_p 判据未达)",
          "===")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
