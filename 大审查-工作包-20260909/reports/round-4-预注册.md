# Round 4 预注册 · 尖峰景观挑战"吸收论"（红队预演·证伪轮）

> 状态：预注册。引擎（sandbox/eng/engine_r4.txt）+ 判据（sandbox/judges/judge_r4_sharp.txt）自测 PASS 后**先锁后跑**。
> source_type=DATA-DRIVEN：触发行为 data-archive.csv 第 2 轮 H-R2-1/H-R2-2 行（boundary_conditions 记载"平坦景观吸收假采纳代价，假采纳率 0.61~0.03 区间终值仅波动 0.06"）+ 锁定数据快照 sandbox/out/r2_results.json（σ=0.08/margin=0.05 格：rate=0.5243，final=0.7567）。
> 证伪对象：R2 意外发现的外推——"假采纳代价被景观吸收"若为普遍规律，则换尖峰景观终值不应塌缩。

## 先验的形成过程（如实记录）
- 直觉先验 0.70（"尖峰=吸收态，假采纳掉出峰外回不来"——lab-notebook R3 语）。
- 预注册形式化时推演出**门控不对称性**：陡梯度下，"掉出峰"的候选其 obs 远低于主线，门控以 ~12σ 差距拒绝——假采纳在尖峰世界反而更难发生；平坦世界的吸收恰恰因为梯度小于噪声。据此注册先验降为 **0.45**。
- 此修正发生在任何数据产生之前，属合法的拟题期更新。

## 引擎世界定义（锁定对象）
- 与 engine_r2 同构，仅景观替换：U_sharp(x)=exp(−‖x−t‖²/(2·0.15²))（窄高斯峰，r=0.15；远场梯度趋零=超平坦荒漠）。
- 格：σ=0.08，margin=0.05，step=0.35，G=30，1 候选/代，100 run，seed=格序号×100000+run。
- 对照：R2 平坦格（σ=0.08，margin=0.05）锁定数据。

## 假设清单

### H-R4-1 尖峰塌缩（direction=证伪，source_type=DATA-DRIVEN·行2，kind=disconfirm）
- 陈述：尖峰世界终值塌缩——mean_final_sharp < 0.45（吸收论被证伪：景观尖锐度是假采纳代价的调节变量）。
- PRIOR: H-R4-1 0.45
- NOVELTY: H-R4-1 1
- KIND: H-R4-1 disconfirm
- 判据：<0.45 → SUPPORTED；>0.65 → REFUTED（吸收在尖峰下依然成立=直觉错误）；之间 → INCONCLUSIVE。mechanical=1−mean_final_sharp（0-1 同向）。effect_size=0.7567−mean_final_sharp。
- 描述性附加（不入判定）：median_final、收敛率（final>0.8 占比）——预期分布双峰。
- EVAL_UNITS: H-R4-1 3000

### H-R4-2 塌缩归因（代价非概率）（direction=证伪，source_type=DATA-DRIVEN·行2，kind=confirm）
- 陈述：若终值下降，其机制是"单步代价重尾"而非"假采纳概率上升"——即 |rate_sharp−0.5243|≤0.10 且终值差>0.20。
- PRIOR: H-R4-2 0.5
- NOVELTY: H-R4-2 1
- KIND: H-R4-2 confirm
- 判据：两条款全满足 → SUPPORTED；rate 差>0.10 且终值差≤0.20 → REFUTED（塌缩源于概率上升，非代价）；其余 → INCONCLUSIVE。mechanical=满足条款占比（0/0.5/1）。effect_size=终值差。
- EVAL_UNITS: H-R4-2 3000

## RED_TEAM: 4 1

## 自测用例（手算标准答案）
```
case1: final=0.30 → H1 SUPPORTED，mechanical=1−0.30=0.7000
case2: final=0.70 → H1 REFUTED，mechanical=0.3000
case3: rate=0.52, final=0.30 → 终值差=0.4567>0.20 ✓，|0.52−0.5243|=0.0043≤0.10 ✓ → H2 SUPPORTED，mechanical=1.0000
case4: rate=0.75, final=0.70 → rate 差=0.2257>0.10 且终值差=0.0567≤0.20 → H2 REFUTED，mechanical=0.0000
```

## 三态结局定义
见各假设判据。

## 成本预估
引擎 ~70 行（复用 r2 骨架）+ 判据 ~80 行；1 格 3000 评估，秒级。

## 新颖性声明
- 档案无任何"景观尖锐度 × 护栏/假采纳代价"的调节变量实验（R2 意外发现本身是首次）。对自有结论的受控证伪测试=红队预演。NOVELTY=1 ×2。
