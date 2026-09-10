# Round 9 预注册 · 两阶段门控的景观边界（尖峰世界复测）

> 状态：预注册。引擎（sandbox/eng/engine_r9.txt）+ 判据（sandbox/judges/judge_r9_sharp2s.txt）自测 PASS 后先锁后跑。
> source_type=DATA-DRIVEN：触发行= data-archive 第 8 轮 H-R8-1/H-R8-2（两阶段双轴占优于平坦世界）+ 第 4 轮 H-R4-1（尖峰世界单阶段 0.3508/双峰）。边界主张：R8 优势不跨景观。

## 引擎世界定义（锁定对象）
- 与 engine_r4 完全同构（窄高斯峰 r=0.15、σ=0.08、margin=0.05、step=0.35、G=30、100 run、seed=180000+run），门控改两阶段（同 engine_r8：两次独立含噪评估都过门）。
- 对照（锁定数据）：R4 尖峰单阶段（rate=0.7628，final=0.3508，收敛 30%）。

## 假设清单

### H-R9-1 尖峰世界两阶段不占优（direction=边界，source_type=DATA-DRIVEN·行8，kind=confirm）
- 陈述：尖峰世界两阶段终值 <0.40（=单阶段 0.3508+0.05 占优带下限之外）——发现依赖荒漠随机游走，压假采纳压发现。
- PRIOR: H-R9-1 0.55
- NOVELTY: H-R9-1 1
- KIND: H-R9-1 confirm
- 判据：<0.40 → SUPPORTED（边界成立）；≥0.45 → REFUTED（两阶段跨景观占优）；[0.40,0.45) → INCONCLUSIVE。mechanical=1−final（同向：越低越支持边界主张）。effect_size=final_两阶段−0.3508。描述性：收敛率（final>0.8 占比）对比 30%。
- EVAL_UNITS: H-R9-1 3000

### H-R9-2 假采纳抑制跨景观保真（direction=边界，source_type=DATA-DRIVEN·行8，kind=confirm）
- 陈述：尖峰世界两阶段假采纳率 <0.60（单阶段 0.7628 显著下降）。
- PRIOR: H-R9-2 0.7
- NOVELTY: H-R9-2 1
- KIND: H-R9-2 confirm
- 判据：<0.60 → SUPPORTED；≥0.70 → REFUTED；[0.60,0.70) → INCONCLUSIVE。mechanical=1−rate。effect_size=0.7628−rate。
- EVAL_UNITS: H-R9-2 3000

## RED_TEAM: 9 0

## 自测用例（手算标准答案）
```
case1: H1 规则——final=0.35→SUPPORTED(0.35<0.40)；final=0.47→REFUTED；final=0.42→INCONCLUSIVE
case2: H2 规则——rate=0.55→SUPPORTED；rate=0.75→REFUTED；rate=0.65→INCONCLUSIVE
case3: 事件 dtrue={+0.1,−0.05} → 假采纳率=0.5000
```

## 三态结局定义
见各假设（双侧区间）。

## 成本预估
引擎 ~60 行（r4 骨架改门控）；判据 ~70 行；3000 评估秒级。

## 新颖性声明
- 门控机制的景观调节效应（同一门控在平坦占优、尖峰可能反噬）在档案与本循环均未测过。NOVELTY=1 ×2。
