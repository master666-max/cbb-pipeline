# Round 8 预注册 · 两阶段门控（E13/E7 复现于最小噪声引擎）

> 状态：预注册。引擎（sandbox/eng/engine_r8.txt）+ 判据（sandbox/judges/judge_r8_twostage.txt）自测 PASS 后先锁后跑。
> LIT-REPLICATE 声明：H-R8-1/H-R8-2 复现 E13（两阶段门控）与 E7（两级门控）的核心主张——廉价门+昂贵门优于单门/margin 加码；对话 R2 锁定数据（单阶段 σ0.08/m0.05：rate=0.5243 final=0.7567；m0.15：rate=0.3102 final=0.7648）。
> 判据遵 OBL-003：双侧区间 + 理论对齐（理论预测：纯噪声过两独立门为乘法概率，粗算 ≈0.27 一带）。

## 引擎世界定义（锁定对象）
- 与 engine_r2 完全同构（平坦二次景观 U=max(0,1−‖x−t‖²)、σ=0.08、step=0.35、G=30、100 run、seed=150000+run）。
- 唯一改动（两阶段门控）：每代抽两次独立含噪评估——采纳条件 = [obs1(候选)>obs1(主线)+0.05] **且** [obs2(候选)>obs2(主线)+0.05]（4 个独立噪声抽签/代）。
- 对照（锁定数据，不重跑）：R2 单阶段 m0.05 与 m0.15 两格。

## 假设清单

### H-R8-1 两阶段压假采纳（direction=机制，source_type=LIT-REPLICATE·E13/E7，kind=confirm）
- 陈述：两阶段门控的假采纳率 <0.30（低于单阶段 0.5243 与 margin 加码的 0.3102）。
- PRIOR: H-R8-1 0.75
- NOVELTY: H-R8-1 1
- KIND: H-R8-1 confirm
- 判据：<0.30 → SUPPORTED；≥0.45 → REFUTED；[0.30,0.45) → INCONCLUSIVE。mechanical=假采纳率（反向量，为同向取 1−rate）。effect_size=0.5243−rate_两阶段。
- EVAL_UNITS: H-R8-1 3000

### H-R8-2 两阶段非劣终值（direction=机制，source_type=LIT-REPLICATE·E13/E7，kind=confirm）
- 陈述：两阶段终值 ≥0.735（单阶段 0.7567−0.02 非劣带内），即压假采纳不以终值为代价。
- PRIOR: H-R8-2 0.55
- NOVELTY: H-R8-2 1
- KIND: H-R8-2 confirm
- 判据：≥0.735 → SUPPORTED；<0.70 → REFUTED；[0.70,0.735) → INCONCLUSIVE。mechanical=终值。effect_size=终值−0.7567。
- EVAL_UNITS: H-R8-2 3000

## RED_TEAM: 8 0

## 自测用例（手算标准答案）
```
case1: 事件 dtrue={+0.1,−0.05,−0.2} → 假采纳率=2/3=0.6667
case2: H1 规则——rate=0.25 → SUPPORTED（1−rate=0.7500）；rate=0.47 → REFUTED；rate=0.35 → INCONCLUSIVE
case3: H2 规则——final=0.75 → SUPPORTED；final=0.69 → REFUTED；final=0.72 → INCONCLUSIVE
```

## 三态结局定义
见各假设判据（双侧区间，OBL-003）。

## 成本预估
引擎 ~70 行（r2 骨架改门控）；判据 ~80 行；1 格 3000 评估秒级。

## 新颖性声明
- E13/E7 在真实系统验证过，但从未与"margin 加码"在同一受控世界对齐比较（R2 锁定格提供 margin 臂）；两阶段 vs margin 的头对头是新的。NOVELTY=1 ×2。
