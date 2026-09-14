# CONSTELLATION-10 状态文件

- 启动时间: 2026-09-14
- 驱动方式: /goal 目标模式,agent 自主推进
- 参考常数: AGENTS.md 硬编码表(PDG 2024 / Planck 2018)

## Phase 状态

- P1 FLRW 宇宙学(宇宙年龄/距离积分) — DONE(年龄误差 0.0429%,双方法差 5.2e-13)
- P2 BBN 弱冻结 + 核网络(Y_p / D/H) — BLOCKED(Y_p=0.3068 误差+0.0598,判据<0.003未达;D/H=2.83e-5 偏+15.4%;重子守恒1.8e-15;瓶颈T=0.0660MeV/t=300.8s 与文献吻合)
- P3 再复合与 CMB 解耦(Saha/Peebles, r_s, z*) — PENDING
- P4 线性扰动与结构增长(D+ ODE vs Heath 积分, f0) — PENDING
- P5 N 体动力学(leapfrog 直接求和, Kepler/Plummer 验证) — PENDING
- P6 引力透镜(偏折角/爱因斯坦半径/像方程 vs 解析) — PENDING
- P7 黑洞几何(Schwarzschild 零测地线, 阴影 b_crit=3√3 M) — PENDING
- P8 引力波(四极领阶旋近 f(t)/t_c vs 解析) — PENDING
- P9 恒星结构(Lane-Emden n=1.5/3, TOV vs 内部 Schwarzschild) — PENDING
- P10 集成可视化桌面应用(实时物理, 60fps 基准) — PENDING

## 审查层

- AUDIT L1 自审(近似假设清单) — PENDING
- AUDIT L2 数值守恒总表 — PENDING
- AUDIT L3 反作弊审计 — PENDING
- AUDIT L4 压力测试 — PENDING

## 判据(全部达成才算完成)

- P1 宇宙年龄误差 < 0.5%
- P2 Y_p 误差 < 0.003
- P7 阴影半径误差 < 1%
- P10 桌面 60fps(实测帧时数字写入 PROGRESS.md)
