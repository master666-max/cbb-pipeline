# Round 10 预注册 · 三区定律：门控假采纳率的区域排序（NARRATIVE-DRIVEN）

> 状态：预注册。重放器（sandbox/analysis/replay_regions.txt）+ 判据（sandbox/judges/judge_r10_regions.txt）自测 PASS 后先锁后跑。
> source_type=NARRATIVE-DRIVEN：触发于 lab-notebook Round4/Round9 直觉（"护栏价值由三区域拼成：峰顶/缓坡/荒漠"）。**按规则解读自动降权一档。**
> 数据基础：r2_results.json（平坦 σ0.08/m0.05 格）与 r4_results.json（尖峰）锁定动力学的仪器化重放——同种子同 rng 调用序，仅加记采纳前主线效用 u_old；先验证 100 run 终值与锁定 JSON 全等（逐 run |diff|<1e-9），验证不过即中止。

## 区域定义（锁定）
- 以**采纳事件前**主线真值 u_old=U(x) 分区：峰顶 u_old>0.6；缓坡 0.2≤u_old≤0.6；荒漠 u_old<0.2。

## 假设清单

### H-R10-1 尖峰世界三区排序（direction=机制，source_type=NARRATIVE-DRIVEN，kind=confirm·降权）
- 陈述：尖峰世界假采纳率严格递增：rate(峰顶)<rate(缓坡)<rate(荒漠)。
- PRIOR: H-R10-1 0.65
- NOVELTY: H-R10-1 1
- KIND: H-R10-1 confirm
- 判据：三区各 n≥30 守卫；严格递增 → SUPPORTED；任一倒置 → REFUTED；其余 → INCONCLUSIVE。mechanical=rate(荒漠)−rate(峰顶)（clip 到 [0,1]，同向）。effect_size=同 mechanical。
- EVAL_UNITS: H-R10-1 3000

### H-R10-2 平坦世界三区排序（direction=机制，source_type=NARRATIVE-DRIVEN，kind=confirm·降权）
- 陈述：平坦世界同排序成立。
- PRIOR: H-R10-2 0.65
- NOVELTY: H-R10-2 1
- KIND: H-R10-2 confirm
- 判据：同 H-R10-1。
- EVAL_UNITS: H-R10-2 3000

## RED_TEAM: 10 0

## 自测用例（手算标准答案）
```
case1: 尖峰区域表 峰顶(n=40,rate=0.10) 缓坡(n=40,0.30) 荒漠(n=40,0.60) → 严格递增 → SUPPORTED，mechanical=0.5000
case2: 平坦区域表 峰顶(0.05) 缓坡(0.35) 荒漠(0.55)（各n≥30）→ SUPPORTED，mechanical=0.5000
case3: 倒置表 峰顶(0.40) 缓坡(0.30) 荒漠(0.50) → REFUTED（峰顶>缓坡倒置）
case4: 守卫表 各区 n=10 → INCONCLUSIVE（守卫）
```

## 三态结局定义
见各假设（含 n≥30 守卫）。

## 成本预估
重放器 ~90 行 + 判据 ~80 行；重放 2 格 × 100 run，秒级；验证失败即中止（成本上限）。

## 新颖性声明
- 区域分层（按主线效用分区）的门控有效性统计在本循环与档案均无先例（R2/R4 是整 run 粒度）。NOVELTY=1 ×2。
- NARRATIVE 风险登记：区域边界 0.6/0.2 是我自选的，若排序对边界敏感则结论脆弱——boundary_conditions 必须注明。
