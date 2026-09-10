# Round 6 预注册 · 多峰景观：局部最优陷阱与首峰锁定（REVIEW-DRIVEN）

> 状态：预注册。引擎（sandbox/eng/engine_r6.txt）+ 判据（sandbox/judges/judge_r6_multipeak.txt）自测 PASS 后**先锁后跑**。
> source_type=REVIEW-DRIVEN：引用 R5-REVIEW §R3——候选簇 B2世界景观（覆盖最少的非空簇），须与三条反例（H-R5-2 平台统计 / H-R3-2 档案缓解 / H-R3-3 塑性代价）差异最大。本轮取"多峰景观局部最优陷阱"（机械排除法三例之一）。
> 关联档案结论（非复现）：R1-H3 首采纳主导、R5-H1 早信号符号一致——多峰下"早锁定"的机制版本。

## 引擎世界定义（锁定对象）
- 5 峰：t_i ~ U[−1,1]²，h_i ~ U[0.5,1.0]，r_i ~ U[0.15,0.35]；峰间距 ≥0.5（拒绝采样，1000 次上限后整组重抽）。U(x)=max_i h_i·exp(−‖x−t_i‖²/(2r_i²))；global_max=max_i h_i。
- 演化：门控采纳骨架同 r2/r4——σ=0.08，margin=0.05，step=0.35，G=50，1 候选/代，100 run，seed=120000+run。
- 逐 run 记录：final_U（真值）、trap_ratio=final_U/global_max、首峰（U 首次 >0.4 时贡献最大的峰的 h）、终峰（final 处贡献最大的峰）、首峰==终峰（stay）、首峰发现代数、峰切换次数（描述性）。

## 假设清单

### H-R6-1 局部最优陷阱（direction=机制，source_type=REVIEW-DRIVEN·R5-REVIEW R3，kind=confirm）
- 陈述：median(trap_ratio) < 0.80——门控演化在多峰世界系统性困于次优峰。
- PRIOR: H-R6-1 0.6
- NOVELTY: H-R6-1 1
- KIND: H-R6-1 confirm
- 判据：<0.80 → SUPPORTED；≥0.95 → REFUTED（无陷阱，演化达到全局峰）；之间 INCONCLUSIVE。mechanical=1−median(trap_ratio)（同向：越高越陷阱）。effect_size=1−median(trap_ratio)。
- EVAL_UNITS: H-R6-1 5000

### H-R6-2 首峰锁定（direction=机制，source_type=REVIEW-DRIVEN·R5-REVIEW R3，kind=disconfirm·证伪"演化终会迁移到最高峰"）
- 陈述：stay_rate（终峰==首峰的 run 占比）≥ 0.70——发现首峰后基本不再迁移。
- PRIOR: H-R6-2 0.7
- NOVELTY: H-R6-2 1
- KIND: H-R6-2 disconfirm
- 判据：≥0.70 → SUPPORTED；≤0.40 → REFUTED（存在有效跳峰）；之间 INCONCLUSIVE。mechanical=stay_rate。effect_size=stay_rate−0.5。描述性附加：Spearman ρ(h_first, final_U)、峰切换次数分布。
- EVAL_UNITS: H-R6-2 5000

## RED_TEAM: 6 0

## 自测用例（手算标准答案）
```
case1: trap_ratios=[0.5,0.9] → median=0.7000 → H1 SUPPORTED，mechanical=0.3000
case2: trap_ratios=[0.9,0.97] → median=0.9350 → H1 INCONCLUSIVE，mechanical=0.0650
case3: 峰对=[(1,1),(2,3),(1,1)] → stay=2/3=0.6667 → H2 INCONCLUSIVE，mechanical=0.6667
case4: 峰对=[(1,2),(1,3)] → stay=0/2=0.0000 → H2 REFUTED，mechanical=0.0000
case5: 峰对=[(1,1),(1,1),(2,2)] → stay=1.0000 → H2 SUPPORTED，mechanical=1.0000
```

## 三态结局定义
见各假设判据。

## 成本预估
引擎 ~110 行 + 判据 ~90 行；100 run × 50 代 × 5 峰评估，秒级。

## 新颖性声明
- 档案与 E 系列均无多峰景观实验（E12 平台期三态是时间形态非空间形态；R2-R4 全单峰）。REVIEW-DRIVEN 首轮。NOVELTY=1 ×2。
