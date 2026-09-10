# Round 1 预注册 · 采纳微观机制（衔尾蛇 x2_clean 逐代数据）

> 状态：预注册（判据锁定前）。执行真实数据前，本文件与判据脚本 sha256 锁入 sandbox/meta/registry.md。
> 数据源：unified/衔尾蛇.jsonl 的 x2_clean-* run（40 run × 26 代，逐代 train_U / promoted / mainline 参数，锚例：x2_clean-G2-s1 L26-L62，Δ 在采纳代发生、不采纳代持平——见阶段1归一化与 03-flags STALLED 族）。

## 假设清单

### H-R1-1 假采纳率（direction=机制，source_type=DATA-DRIVEN，kind=disconfirm·对"门控微观完美"的怀疑）
- 陈述：x2_clean 全部采纳事件（promoted=1 且前代分数存在的代）中，假采纳（Δ=train_U(t)−train_U(t−1) ≤ 0）占比 ≤ 0.10。
- 灵感锚点：lab-notebook Round0 直觉（怀疑 E14 内生评判者漂移存在微观版：候选评估与下一代重评估的口径差）。
- PRIOR: H-R1-1 0.45
- NOVELTY: H-R1-1 1
- KIND: H-R1-1 disconfirm
- 判据（mechanical=假采纳率，0-1）：rate ≤ 0.10 → SUPPORTED；rate ≥ 0.25 → REFUTED；之间 → INCONCLUSIVE。
- EVAL_UNITS: H-R1-1 1000（预估可用 (t-1,t) 对数）

### H-R1-2 复合变更效应（direction=参数，source_type=DATA-DRIVEN，kind=confirm）
- 陈述：采纳事件的 mainline 变更参数个数 k≥2（复合变更）的平均 Δ 高于 k=1（单参数变更）。
- PRIOR: H-R1-2 0.55
- NOVELTY: H-R1-2 1
- KIND: H-R1-2 confirm
- 判据：diff = mean(Δ|k≥2) − mean(Δ|k=1)。diff>0 且置换检验 p<0.05（10000 次，seed=42）→ SUPPORTED；diff≤0 → REFUTED；diff>0 但 p≥0.05 → INCONCLUSIVE。mechanical=配对优势概率 P(随机 k≥2 的 Δ > 随机 k=1 的 Δ)（平局记 0.5，0-1）。
- 边界：k=0 的采纳（无参数变更也采纳）不入两组，但计入 H-R1-1 分母。
- EVAL_UNITS: H-R1-2 1000

### H-R1-3 先发采纳主导（direction=机制，source_type=DATA-DRIVEN，kind=confirm）
- 陈述：各 run 总收益（末代−首代 train_U）中，第一次采纳的 Δ 贡献占比中位数 > 0.5。
- PRIOR: H-R1-3 0.5
- NOVELTY: H-R1-3 1
- KIND: H-R1-3 confirm
- 判据：跨 run 的首采纳占比中位数 > 0.5 → SUPPORTED；< 0.3 → REFUTED；之间 → INCONCLUSIVE。mechanical=该中位数（0-1）。总收益 ≤ 0 的 run 剔除并计数。
- EVAL_UNITS: H-R1-3 40

## RED_TEAM: 1 0

## 判据脚本
sandbox/judges/judge_r1_adoption.txt，--selftest 模式跑合成数据，--real 模式跑 unified/衔尾蛇.jsonl。

## 自测用例（手算标准答案，2026-09-09 手工推导）

合成数据（两 run，x2_clean-SYNTH-A/B，字段与真实 schema 同构）：

```
SYNTH-A: gen1 0.0 p0 m{w_kw:3.0,fz:0} | gen2 0.5 p1 m{w_kw:2.5,fz:0}(k=1,Δ+0.5)
         gen3 0.5 p0 m{w_kw:2.5,fz:0}(k=0,Δ0) | gen4 0.4 p1 m{w_kw:2.5,fz:1}(k=1,Δ−0.1假采纳)
         gen5 0.9 p1 m{w_kw:1.0,fz:1,w_imp:2.0}(k=2,Δ+0.5)
SYNTH-B: gen1 0.2 p0 m{w_kw:3.0,fz:0} | gen2 0.7 p1 m{w_kw:3.0,fz:0,w_imp:1.0}(k=1新增,Δ+0.5)
         gen3 0.7 p1 m{w_kw:3.0,fz:0,w_imp:1.0}(k=0,Δ0假采纳)
```

手算答案（脚本输出必须逐项相等，4 位小数）：
| 量 | 手算值 | 推导 |
|---|---|---|
| 采纳事件数 | 5 | A:gen2/4/5 + B:gen2/3 |
| 假采纳率 | 0.4000 | A gen4(−0.1)、B gen3(0.0) → 2/5 |
| mean(Δ\|k≥2) | 0.5000 | A gen5 {+0.5} |
| mean(Δ\|k=1) | 0.3000 | {+0.5,−0.1,+0.5}/3 |
| diff | 0.2000 | 0.5−0.3 |
| 配对优势P | 0.6667 | 3 对：(0.5,0.5)平、(0.5,−0.1)胜、(0.5,0.5)平 → (0.5+1+0.5)/3 |
| SYNTH-A 首采纳占比 | 0.5556 | 0.5/(0.9−0.0) |
| SYNTH-B 首采纳占比 | 1.0000 | 0.5/(0.7−0.2) |
| 占比中位数 | 0.7778 | median{0.5556,1.0} |
| 不采纳代 \|Δ\| 中位数 | 0.0000 | 仅 A gen3 |

## 三态结局定义
每假设独立判定：SUPPORTED / REFUTED / INCONCLUSIVE（阈值见上）。本轮无跨假设联合判定。

## 成本预估
判据脚本 1 份（~160 行）+ 自测 1 次 + 真实数据 1 次。无模拟成本。预计全轮 ≤1 小时等价工作量。

## 新颖性声明
- H-R1-1：八源档案与 E 系列均无"逐代假采纳率"统计（E5 Goodhart 是宏观自报通道结论；deepseek bare/gated 是总分差）。NOVELTY=1。
- H-R1-2：变更粒度（单参数 vs 复合）× 收益，档案未触及（E15 选择策略不涉及粒度；E6 结构演化是否定性总论）。NOVELTY=1。
- H-R1-3：收益集中度（首采纳贡献占比）未量化过（E12 平台期三态是形态分类非集中度）。NOVELTY=1。
- 若真实数据中三者的可变异性为零（如 Δ 全部>0 且 k 恒定），按"世界过简无区分度"记 INCONCLUSIVE 并在 boundary_conditions 标注。
