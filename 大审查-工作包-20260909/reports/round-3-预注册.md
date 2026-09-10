# Round 3 预注册 · 世界切换 × 档案结构（E16 遗忘 / E11 Pareto 恢复力）

> 状态：预注册。引擎（sandbox/eng/engine_r3.txt）+ 判据（sandbox/judges/judge_r3_switch.txt）自测 PASS 后连同本文件**先**锁 registry **再**执行（吸取 R2 时序教训）。
> LIT-REPLICATE 声明：H-R3-1 复现 E16（灾难性遗忘，单一档案）；H-R3-2 复现 E11（Pareto 档案恢复力）；H-R3-3 证伪"多目标档案损害新世界可塑性"（关联 E18 跨库负面结论的民间引申）。

## 引擎世界定义（锁定对象）
- 双世界：目标 t_A、t_B ∈ U[−1,1]²，拒绝采样保证 ‖t_A−t_B‖≥1.2（真实遗忘压力）；效用 U_W(x)=max(0,1−‖x−t_W‖²)。
- 演化：G=30 代，第 15 代末世界 A→B 切换。候选=x_parent+N(0,0.35²)。评估噪声 σ=0.03（低噪，隔离遗忘机制）。margin=0.05。
- 两臂（同种子配对，seed=7000+run，同 x₀/同目标）：
  - **single**（档案容量 K=1）：parent=唯一成员；采纳条件 obs_当前(候选)>obs_当前(成员)+margin → 替换。
  - **pareto**（K=5）：parent=档案中 obs_当前最高者；候选加入档案后，若超容：优先淘汰**被支配**成员（对已见世界效用向量 (U_A,U_B) 的含噪支配判断：≥两维且>一维），无被支配者才淘汰 obs_当前最低者。A 专家（高 U_A 低 U_B）与 B 攀升者互不支配 → 结构性存活，非手工豁免。
- 度量（真值无噪）：
  - retention_A = bestA(末代档案) − bestA(第15代档案)，bestA = 档案成员 U_A 最大值。
  - B_gain = bestB(末代档案) − bestB(第15代档案)。
  - single 臂档案=单点，公式同构。
- 每臂 100 run。事件流全量落盘 sandbox/out/r3_results.json。

## 假设清单

### H-R3-1 切换致遗忘（single 臂）（direction=机制，source_type=LIT-REPLICATE·E16，kind=confirm）
- 陈述：single 臂 retention_A 均值 < −0.10（切换后 A 能力显著掉落）。
- PRIOR: H-R3-1 0.75
- NOVELTY: H-R3-1 1
- KIND: H-R3-1 confirm
- 判据：mean_retA(single) < −0.10 → SUPPORTED；> −0.03 → REFUTED（无实质遗忘）；之间 INCONCLUSIVE。mechanical=forgetting=max(0,−mean_retA(single))（0-1 同向）。effect_size=−mean_retA(single)。
- EVAL_UNITS: H-R3-1 3000

### H-R3-2 Pareto 缓解且不牺牲 B（direction=机制，source_type=LIT-REPLICATE·E11，kind=confirm）
- 陈述：retention_A(pareto) − retention_A(single) > 0.10 且 B_gain(pareto) ≥ B_gain(single) − 0.05。
- PRIOR: H-R3-2 0.65
- NOVELTY: H-R3-2 1
- KIND: H-R3-2 confirm
- 判据：两条件全满足 → SUPPORTED；retention 差 ≤ 0 → REFUTED；其余 INCONCLUSIVE。mechanical=配对 run 中 retention_A(pareto)>retention_A(single) 的占比（0-1 同向）。effect_size=retention 差（均值）。
- EVAL_UNITS: H-R3-2 6000

### H-R3-3 档案无塑性代价（direction=机制，source_type=LIT-REPLICATE·E18引申，kind=disconfirm）
- 陈述：B_gain(pareto) − B_gain(single) ≥ −0.03（多目标档案不显著拖慢新世界学习）。
- PRIOR: H-R3-3 0.6
- NOVELTY: H-R3-3 1
- KIND: H-R3-3 disconfirm
- 判据：差 ≥ −0.03 → SUPPORTED；< −0.10 → REFUTED；之间 INCONCLUSIVE。mechanical=配对 run 中 Bg(pareto)≥Bg(single) 占比。effect_size=B_gain 差。
- EVAL_UNITS: H-R3-3 6000

## RED_TEAM: 3 0

## 自测用例（手算标准答案）

```
引擎单测（--check，手算）：
  U((0,0); t=(0,0)) = 1.0000；U((2,0); t=(0,0)) = 0.0000；U((0.5,0); t=(0,0)) = 0.7500
  dominates((0.8,0.3),(0.5,0.2)) = True（两维≥且首维>）
  dominates((0.8,0.3),(0.9,0.1)) = False（互不支配）
判据单测（--selftest，手算）：
  single run 库：retA={−0.30,−0.10}, Bg={+0.40,+0.20} → mean_retA=−0.20, mean_Bg=+0.30 → H1: −0.20<−0.10 → SUPPORTED
  pareto run 库：retA={−0.05,+0.05}, Bg={+0.30,+0.50} → H2: 差=0.20>0.10 ∧ 0.40≥0.25 → SUPPORTED；H3: 0.40≥0.27 → SUPPORTED
  配对占比：pareto>single 的 run 对 = {(-0.05>-0.30)✓, (0.05>-0.10)✓} → H2 mechanical=1.0000；Bg≥: {0.30<0.40✗,0.50>0.20✓} → H3 mechanical=0.5000
```

## 三态结局定义
见各假设判据。三假设独立判定。

## 成本预估
引擎 ~130 行 + 判据 ~90 行；2 臂 × 100 run × 30 代，秒级。超预算则砍 run 数（100→50）。

## 新颖性声明
- 档案中 E16/E11 均为真实系统宏观对照；最小引擎中"同种子配对 + 非支配淘汰的显式机制 + 目标间距 ≥1.2 的受控遗忘压力"为新（尤其 H-R3-3 的塑性代价量化在档案中无对应物）。NOVELTY=1 ×3。
- 风险登记：pareto 臂的"恢复力"若只是因为 A 专家碰巧不被淘汰（噪声运气），配对占比会接近 0.5——判据可区分。
