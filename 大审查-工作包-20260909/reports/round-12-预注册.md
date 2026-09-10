# Round 12 预注册 · 收官红队：梯度律的带边界敏感性与跨世界池化（DATA-DRIVEN·证伪）

> 状态：预注册。判据 sandbox/judges/judge_r12_robust.txt 自测 PASS 后先锁后跑。数据复用锁定快照 sandbox/out/r11_gradient.json（hash 4f9e05d4…，零新模拟）。
> source_type=DATA-DRIVEN：触发行=第 11 轮 H-R11-1（SUPPORTED 0.7346，本循环目前最自信的新结论——正该被红队）。
> 红队对象：R11 结论对"带边界自选"的敏感性（R10 预注册已自认区域边界自选是脆弱点）与跨世界形式。

## 假设清单

### H-R12-1 带边界扰动鲁棒性（direction=证伪，source_type=DATA-DRIVEN·行11-H-R11-1，kind=disconfirm）
- 陈述：平坦世界梯度单调律在两套扰动边界下（A 套：低<0.05/中[0.05,0.30)/高≥0.30；B 套：低<0.15/中[0.15,0.70)/高≥0.70）**至少一套倒置或失守**（定律脆弱）。
- PRIOR: H-R12-1 0.35（我红队自己但真不觉得会翻——先验写低即红队诚意）
- NOVELTY: H-R12-1 1
- KIND: H-R12-1 disconfirm
- 判据：两套均严格单调（各带 n≥30）→ REFUTED（红队失败=定律鲁棒）；任一套任一段倒置 → SUPPORTED（红队成功=定律脆弱）；其余（含守卫触发）→ INCONCLUSIVE。mechanical=两套 (低−高) gap 的最小值（clip[0,1]，越高越支持红队成功）。
- EVAL_UNITS: H-R12-1 3000

### H-R12-2 跨世界池化单调律（direction=跨库，source_type=DATA-DRIVEN·行11-H-R11-2，kind=confirm）
- 陈述：默认带（0.1/0.5）下两世界事件池化后严格单调且各带 n≥30（mid 池化后 n=85+18=103 跨过守卫）。
- PRIOR: H-R12-2 0.7
- NOVELTY: H-R12-2 1
- KIND: H-R12-2 confirm
- 判据：严格单调且全带 n≥30 → SUPPORTED；任一段倒置 → REFUTED；其余 → INCONCLUSIVE。mechanical=池化 rate(低)−rate(高)。
- EVAL_UNITS: H-R12-2 6000

## RED_TEAM: 12 0（收官红队轮，非停摆闸触发；全程停摆闸未触发过）

## 自测用例（手算标准答案）
```
合成事件（grad 值组）：g=0.03 (n=30, rate=0.8) / g=0.2 (n=30, rate=0.3) / g=0.9 (n=30, rate=0.1)
case1（H1 规则）：A 套分带 0.03→低, 0.2→中, 0.9→高 → 0.8>0.3>0.1 严格单调；B 套同分带同单调
  → 两套均单调 → 红队失败 → H1 REFUTED；mechanical=min(0.7,0.7)=0.7000
case2（倒置）：g0.03 rate=0.3, g0.2 rate=0.6, g0.9 rate=0.1 → 两套低<中倒置 → H1 SUPPORTED；mechanical=min(0.3-0.1, 0.3-0.1)... 低−高=0.2 → 0.2000
case3（池化）：case1 数据 + 第二组 g0.9(n=30, rate=0.05) 池化 → 高带 false=3+2=5, n=60, rate=0.0833
  → SUPPORTED，mechanical=0.8−0.0833=0.7167（初稿手算 0.7000 漏算池化第二组——自测门 FAIL 抓出，锁定前修正，累计第 5 处手算错）
case4（守卫）：各带 n=10 → 两假设均 INCONCLUSIVE（守卫）
```

## 三态结局定义
见各假设（n≥30 守卫；H1 的三态按"红队成功/失败"语义映射）。

## 成本预估
判据 ~110 行；单遍扫描 r11_gradient.json 秒级。

## 新颖性声明
- 带边界敏感性分析与跨世界池化均为本循环首例；红队对象是 24 小时内自己刚立的定律。NOVELTY=1 ×2。
