# Round 2 预注册 · 噪声评估世界的采纳边界（最小引擎）

> 状态：预注册。引擎（sandbox/eng/engine_r2.txt）+ 判据（sandbox/judges/judge_r2_noise.txt）自测 PASS 后连同本文件 sha256 锁入 registry。
> 知识来源：Round 1 边界发现（确定性世界假采纳率=0/176，结论不可外推到噪声世界）+ E5（Goodhart：代理可被操纵）/ E14（内生评判者漂移）——LIT-REPLICATE 声明：H-R2-1 复现 E5/E14 的微观参数化形态；H-R2-2 关联 E41（margin=0.15 违 E29b 饿死采纳）与 E17（margin 的统计基础）。

## 引擎世界定义（锁定对象）
- 效用景观：U(x)=max(0, 1−‖x−t‖²)，x∈R²，目标 t ~ U[−1,1]²，初始 x₀ ~ U[−1,1]²（每 run 独立抽）。
- 评估噪声：obs(x)=U(x)+N(0,σ)；候选与主线**各自独立**抽噪（每代重评，评判者噪声不衰减）。
- 候选生成：每代 1 个，x+N(0,step²)，step=0.35。
- 门控：obs(候选) > obs(主线当前) + margin 则采纳（写入 mainline）。
- 代数 G=30；每格 100 run；seed=格序号×100000+run序号（确定性可复现）。
- 格设计：H-R2-1 用 (σ∈{0.02,0.06,0.10}, margin=0.05)；H-R2-2 用 (σ=0.08, margin∈{0.0,0.05,0.15,0.30})。共 7 格。
- 事件记录：每次采纳记 dtrue=U(新)−U(旧)（无噪声真值）。

## 假设清单

### H-R2-1 噪声敏感性（direction=边界，source_type=LIT-REPLICATE·E5/E14，kind=confirm）
- 陈述：margin=0.05 固定时，假采纳率（dtrue≤0 的采纳占比）随 σ 单调上升，且 rate(σ=0.02)<0.05、rate(σ=0.10)>0.20。
- PRIOR: H-R2-1 0.7
- NOVELTY: H-R2-1 1
- KIND: H-R2-1 confirm
- 判据：三条件全满足 → SUPPORTED；（rate(0.10)≤0.10 或 rate(0.02)≥0.05 或非单调）→ REFUTED；其余 → INCONCLUSIVE。mechanical=rate(σ=0.10)（0-1 同向：越高越支持）。effect_size=rate(0.10)−rate(0.02)。
- EVAL_UNITS: H-R2-1 9000

### H-R2-2 margin 内点最优（direction=边界，source_type=LIT-REPLICATE·E41/E17，kind=disconfirm·证伪"margin 越大越安全"）
- 陈述：σ=0.08 下，最终真效用对 margin 呈倒 U——内部点（margin∈{0.05,0.15}）优于两端（0.0 与 0.30）。
- PRIOR: H-R2-2 0.6
- NOVELTY: H-R2-2 1
- KIND: H-R2-2 disconfirm
- 判据：min(内部均值) > max(边缘值)+0.02 → SUPPORTED；max(内部) ≤ max(边缘) → REFUTED（存在边缘占优=单调 folk 结论成立）；其余 → INCONCLUSIVE。mechanical=内部对边缘两两胜率（4 对，0-1 同向）。effect_size=mean(内部)−mean(边缘)。
- EVAL_UNITS: H-R2-2 12000

## RED_TEAM: 2 0

## 判据脚本
sandbox/judges/judge_r2_noise.txt：--selftest 嵌入手算用例；--real 读 sandbox/out/r2_results.json。

## 自测用例（手算标准答案）

```
用例1（事件级）：A run 事件 dtrue={+0.1, −0.05}，B run dtrue={+0.2, 0.0}；finals A=0.8 B=0.6
  → false_rate=2/4=0.5000；mean_final=0.7000
用例2（H1 规则）：σ→rate 字典 {0.02:0.03, 0.06:0.15, 0.10:0.35}
  → 单调=True；0.02<0.05 ✓；0.10>0.20 ✓ → verdict=SUPPORTED；mechanical=0.3500
用例3（H2 规则）：margin→final 字典 {0.0:0.45, 0.05:0.80, 0.15:0.70, 0.30:0.40}
  → 内部{0.80,0.70} 边缘{0.45,0.40}；两两胜率 4/4=1.0000；min内部0.70 > max边缘0.45+0.02 → verdict=SUPPORTED
```

## 三态结局定义
见各假设判据。两假设独立判定。

## 成本预估
引擎 ~90 行 + 判据 ~110 行；7 格 × 100 run × 30 代 ≈ 4.2 万次评估，秒级。超预算则砍 σ 档位（3→2）。

## 新颖性声明
- 档案中 E5/E14 为真实系统宏观结论（自报膨胀、评判者漂移），从未在受控最小引擎中做过 σ×假采纳率的定量边界；E41 只测了 margin=0.15 一点，无相图。NOVELTY=1 ×2。
- 风险登记：最小引擎世界过简（1 候选/代、二次景观、无检索结构），若两假设全 SUPPORTED 且方向"理所当然"，boundary_conditions 必须写明外推限制。
