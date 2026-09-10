# Full 统计协议（12 seeds × 40 代 + bootstrap 95% CI / Wilcoxon）

> 时间 2026-09-09 ｜ 场景: clean / spur-surface / stale / switch / dup-drift(首领金标) ｜ 臂: static,bare,gated(+dup-drift 加 gated-row)
> 数据: out_v2_full_a / out_v2_full_switch / out_v2_full_dup ｜ 分析器: analysis/full_stats.py（读盘独立运行; Wilcoxon 配对精确(并列平均秩, 双侧最小尾×2); bootstrap 10^4 重采样种子级配对差）
> 方法：同 seed 配对 Δ；判据（F1）= gated vs static 正种子 ≥70% 且 bootstrap 95% CI 下界 > 0。

## 1) 主判据：gated vs static（真值集 u_audit）

| 场景 | static | gated | 配对 Δ | 正种子 | Wilcoxon p | 95% CI | F1 |
|---|---|---|---|---|---|---|---|
| clean | 0.2176 | 0.5046 | +0.2870 | 12/12 | 0.0005 | [+0.245, +0.329] | **PASS** |
| spur-surface | 0.1944 | 0.4444 | +0.2500 | 12/12 | 0.0005 | [+0.199, +0.296] | **PASS** |
| stale | 0.3287 | 0.6389 | +0.3102 | 12/12 | 0.0005 | [+0.259, +0.361] | **PASS** |
| switch | 0.2014 | 0.4236 | +0.2222 | 11/12 | 0.0010 | [+0.160, +0.278] | **PASS** |
| dup-drift | 0.1620 | gated 0.3056 | +0.1435 | 12/12 | 0.0005 | [+0.116, +0.171] | **PASS** |
| dup-drift | 0.1620 | **gated-row 0.4074** | **+0.2454** | 12/12 | 0.0005 | [+0.204, +0.287] | **PASS** |

→ **F1 在 5/5 场景 PASS**；行层算子边际在 12×40 下 = +0.245−0.144 = **+0.102**（quick 20 代时为 +0.083，量级稳健）。

## 2) bare 对照（无门控）在 full 协议下的读数

| 场景 | bare Δ vs static | 正种子 | 备注 |
|---|---|---|---|
| clean | +0.2870 | 12/12 | == gated（无危险场景两通道对齐, 门控无分离, E41 镜像） |
| spur-surface | +0.2546 | 12/12 | ≈ gated(+0.250)（见 3) 的窗口性说明） |
| stale | +0.3102 | 12/12 | == gated |
| switch | +0.2222 | 11/12 | == gated |

## 3) 诚实读数：H2 的窗口性

- spur-surface 12×40：bare 自报−真值 gap = **+0.148** ≈ gated(+0.144)，两者真值几乎相等（bare 0.449 vs gated 0.444）。
- 早前 spur30（8 seeds × 30 代）曾测到 bare gap +0.354 vs gated +0.160（2.2× 分离）：**该分离是 30 代窗口内的动态现象**——40 代后两条轨迹在"降 age 噪声"这一主导改进上汇合，表象污染的单参数路径被该改进淹没，judge/真值分歧消失。
- 结论：**检索权重单参数空间里"裸演化自报膨胀"是窗口性的**；能在任意水平稳定复现自报-真值分歧的机制需要"可演化的展示通道"（=探针 3 的 E81：judge 感知分 = 名义×(1+w_show×SHOW)，bare/anchor 稳定 gap +0.354 而真值抽样审计把真值钉回 static）。full 协议与探针 3 互补：前者证明长水平收益稳健（F1 全 PASS），后者证明诚实性机制的可检测性。

## 4) 方法学说明

- Wilcoxon 为配对精确双侧（并列平均秩），n=12 无近似误差；bootstrap 为种子级配对差重采样 10^4。
- 配对设计消除了同种子世界差异；效应量 +0.14~+0.31，噪声 std 0.05~0.12，统计功效充分。
- dup-drift 用首领金标世界（探针2 口径，与 quick 旧口径不横向比）；spur-surface 为当前文件世界（spur 名义高/年龄 100-300）。

## 5) 汇总：全部判据（探针 1-6 + FULL）

| 判据 | 状态 |
|---|---|
| F1 H1（gated>static 且 ≥70% 正、CI 下界>0） | **5/5 PASS（FULL 12×40）** |
| H2（裸演化自报膨胀） | 部分支持：30 代 spur 窗口 gap 2.2×；40 代收敛 → 稳定机制见探针3(E81) |
| H3（Pareto 抗遗忘） | 场景未达判别条件（无切换压力/阶跃死区；需污染晋升门复合） |
| H4（importance 实测化） | spur 场景 ratio 3.29×（自称不可信域）；clean 中性 |
| H5（真值抽样审计） | E81 场景检出回退、真值无损；锚定 0 触发 |
| H6/H6b | 真实路径一致性全绿；能力式边界 5/5 + merkle 检出 5/5 |
| H7（行层重组） | dup-drift +0.10（FULL）；clean 零操作零代价 |
| H8（预算门槛） | S 形门槛实证（b=1 无效 / b≈6 饱和）；B* 场景依赖 |
| H9（复合危险） | 增益有限、无额外伤害；E80 负交互未复现（需更强构造） |

## 产物
- analysis/full_stats.py、out_v2_full_a(含 full_stats_FULL.md)/out_v2_full_switch/out_v2_full_dup
- 复现：py -3 analysis/full_stats.py --dirs ../out_v2_full_a ../out_v2_full_switch ../out_v2_full_dup --label FULL
