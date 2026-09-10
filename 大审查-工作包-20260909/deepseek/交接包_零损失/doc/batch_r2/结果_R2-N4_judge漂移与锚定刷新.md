# 批次 R2-N4 · judge 漂移 × 锚定刷新协议（E69/E14 检验）—— 构造性阴性

> 2026-09-09 ｜ probe_r2_n4_anchor_refresh.py ｜ out_r2_n4/
> 目标：E14 型 judge 偏好漂移（wJ 向系统输出靠拢）+ 锚定审计（固定 wJ0=1 排序）检出后 freeze/reanchor（E69 解药）应保护真值。

## 结果（spur-judge × 6 seeds × 40 代）

| arm | T_truth | P_judge | adopts | wJ_end | detections |
|---|---|---|---|---|---|
| static | 0.5463 | 0.6759 | 0 | 1.000 | 0 |
| noAudit / freeze / reanchor | 0.5648 | 0.7870 | 1.5 | 1.045 | **0** |

三臂完全同分：wJ 漂移量极小（α=0.05×40 代 → wJ 1.045），judge 金标（spur 名义×SHOW）在 wJ=1 时就已饱和（spur 感知分已高于真条目），一致性度量恒为 1 → 锚定审计 0 检出；引擎的小幅 w_show 剥削反而提升了 P 与 T（真值未伤）。

## 结论（构造性，诚实记录）

1. **在该检索-呈交空间里，"judge 数值偏好漂移"若无引擎可优化的新通道，就没有工程后果**：伤害不是"judge 数值变了"，而是"judge 变坏后 reward 形状改变并驱动引擎走向新目标"——后者的完整结构已由 R1-1 的 **reward-form 切换**（真值 recall→新鲜度 recall）实证（single 真遗忘、Pareto 保留）；人侧"刷新/重锚"= 修改奖励定义的那一步正是 R1-1 的 ga 切换点。因此 E14/E69 的刷新协议在本框架内的正确检验对象是 **reward-form 级漂移**，不是数值漂移。
2. **锚定一致性度量的陷阱（新记录）**：用"judge 金标 top3 排序重合率"做一致性饱和（top 集合早已全 spur），检不出任何漂移——正确做法是 E14 原文的**成对偏好（pair-wise verdict）锚定**（30 对配置 A/B 谁更好），或改为"belief 分布位移"度量（对候选池全排序的 τ）。这条写进方法学。
3. **处置**：N4 判"场景不可判别（数值漂移无工程后果）"，刷新协议验收并入 reward-form 级（R1-1 已给出判别与解药：Pareto 档案+人侧重锚）；pair-wise 锚定与 belief-τ 度量列为 D4/D 类后续。

## 产物
- out_r2_n4/rows_n4.json（证据：三臂同分、0 检出）
