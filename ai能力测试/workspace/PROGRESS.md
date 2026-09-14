# CONSTELLATION-10 进度日志(append-only)

约定: 每条记录含具体数字;验证失败重试≤3次后标 BLOCKED。
参考常数(AGENTS.md): H0=67.4, Ω_r=9.2e-5, Ω_m=0.315, Ω_Λ=0.685,
T_CMB0=2.7255K, τ_n=880.2s, Y_p_ref=0.247, D/H_ref=2.45e-5, b_crit=3√3 M≈5.196M。

## 轮次 1(2026-09-14)

- 环境探测: Python 3.14.7(py 启动器), numpy 2.5.2, scipy 1.18.1,
  pygame-ce 2.5.8(pip 装 pygame 失败无 3.14 轮子,改装 pygame-ce 成功),
  tkinter 在位作兜底。P10 方案定为 pygame-ce + SDL dummy driver 无头基准。
- 骨架建立: workspace/p1..p10 目录, STATE.md, PROGRESS.md。
- P1 完成(一次修复后全绿): 修复记录=ODE 时间上限单位错(1e12→1e12 s 应为 1e18 s)+D_A 锚点口径错(改用 χ(z*) 锚点)。
  数值: t0(quad)=13.791083 Gyr, t0(ODE)=13.791083 Gyr, 双方法相对差 5.173e-13;
  t0 vs Planck 2018 参考 13.797 Gyr 误差 0.0429% [判据<0.5% PASS];
  近似公式(物質+Λ无辐射) 13.7962 Gyr, 辐射项使年龄 -0.037%(L1 素材);
  a_eq=2.920635e-4, z_eq=3422.9, T_eq=9332 K; 粒子视界 14144.8 Mpc(锚点 14260, 偏 0.81%);
  χ(z*=1089.92)=13864.7 Mpc(锚点 13870, 偏 0.04%); E(0)=1 精确到 1e-15。
