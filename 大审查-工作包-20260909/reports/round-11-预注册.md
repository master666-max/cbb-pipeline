# Round 11 预注册 · 梯度定律：假采纳率随局部梯度带单调下降（REVIEW-DRIVEN）

> 状态：预注册。重放器（sandbox/analysis/replay_gradient.txt）+ 判据（sandbox/judges/judge_r11_gradient.txt）自测 PASS 后先锁后跑。
> source_type=REVIEW-DRIVEN：引用 R10-REVIEW §R3——候选簇 B6梯度信噪（最薄簇，2 假设），反例约束（避开平台统计/族分层/采纳粒度）满足。
> 理论对齐（OBL-003）：门控有效性由"候选-主线真值差 vs 噪声"的信噪比决定；|ΔU_true|≈|∇U|·step，故梯度带低→门控看噪声→假采纳率高。平坦世界低梯度区=峰顶∪荒漠（g≈0 两处），此定律应把 R10 的 U 形统一为单调律。

## 引擎/重放定义（锁定对象）
- 重放 r2 平坦格（seed=400000+run）与 r4 尖峰格（seed=90000+run）锁定动力学（与 replay_regions v2 同 rng 序），加记采纳前主线局部梯度 |∇U(x)|：
  - 平坦：U=max(0,1−d²) → |∇U| = 2d（d<1），d≥1（荒漠平台）取 0。
  - 尖峰：U=exp(−d²/(2·0.15²)) → |∇U| = U·d/r²。
- 验证门：与锁定 JSON 终值 0/100 全等，否则中止。
- 梯度带（锁定）：低 <0.1；中 [0.1,0.5)；高 ≥0.5。

## 假设清单

### H-R11-1 平坦世界梯度单调律（direction=机制，source_type=REVIEW-DRIVEN·R10-REVIEW R3，kind=confirm）
- 陈述：rate(低带)>rate(中带)>rate(高带) 严格下降。
- PRIOR: H-R11-1 0.7
- NOVELTY: H-R11-1 1
- KIND: H-R11-1 confirm
- 判据：三带 n≥30 守卫；严格下降 → SUPPORTED；任一上升 → REFUTED；其余 INCONCLUSIVE。mechanical=rate(低)−rate(高)（clip[0,1]）。effect_size=同。
- EVAL_UNITS: H-R11-1 3000

### H-R11-2 尖峰世界梯度单调律（direction=机制，source_type=REVIEW-DRIVEN·R10-REVIEW R3，kind=confirm）
- 陈述：同 H-R11-1，尖峰世界。
- PRIOR: H-R11-2 0.6
- NOVELTY: H-R11-2 1
- KIND: H-R11-2 confirm
- 判据：同。
- EVAL_UNITS: H-R11-2 3000

## RED_TEAM: 11 0

## 自测用例（手算标准答案）
```
case1: 带表 低(n=40,0.70) 中(n=40,0.40) 高(n=40,0.10) → 严格下降 → SUPPORTED，mechanical=0.6000
case2: 倒置表 低(0.3) 中(0.5) 高(0.1)（各n≥30）→ REFUTED（低<中上升）
case3: 平局表 低(0.5) 中(0.5) 高(0.1) → INCONCLUSIVE（带间隙为 0 非严格）
case4: 守卫表 各带 n=10 → INCONCLUSIVE（守卫）
```

## 三态结局定义
见各假设（n≥30 守卫 + 严格单调）。

## 成本预估
重放 v3 ~100 行 + 判据 ~80 行；秒级；验证门失败即中止。

## 新颖性声明
- 梯度（非效用高度）作为门控有效性调节变量的直接单调检验；统一 R10 U 形 + R4 双因素 + R9 荒漠功能件三个发现的单一变量假设。NOVELTY=1 ×2。
