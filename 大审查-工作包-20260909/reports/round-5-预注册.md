# Round 5 预注册 · 跨库元分析：早信号与平台期（unified 全量）

> 状态：预注册。判据（sandbox/judges/judge_r5_meta.txt）自测 PASS 后**先锁后跑**。
> source_type=DATA-DRIVEN：H-R5-1 触发行为 data-archive.csv 第 1 轮 H-R1-3（首采纳主导 0.5127，边界字段注明仅 x2_clean）；H-R5-2 触发于 03-flags STALLED 族（5 run，x2_clean）+ 关联 E12 平台期三态（非复现，仅同域）。
> 跨库意图：R1 结论的族外推广检验——unified/*.jsonl 全部 5 文件、任何有代际序列的 run。

## 假设清单

### H-R5-1 早斜率符号预测总收益符号（direction=跨库，source_type=DATA-DRIVEN·行3，kind=confirm）
- 陈述：所有合格 run（≥5 个 (round, gen_score) 点）中，前 5 代 OLS 斜率符号与总收益（末−首）符号的一致率 ≥ 0.80。
- PRIOR: H-R5-1 0.65
- NOVELTY: H-R5-1 1
- KIND: H-R5-1 confirm
- 判据：一致率 ≥0.80 → SUPPORTED；<0.50 → REFUTED；之间 → INCONCLUSIVE。mechanical=一致率（0-1 同向）。effect_size=一致率−0.5。描述性附加：Pearson r(early_slope, total_gain)。
- EVAL_UNITS: H-R5-1 1256

### H-R5-2 平台期普遍性（direction=跨库，source_type=DATA-DRIVEN·03-flags，kind=confirm）
- 陈述：合格 run（≥8 点）中，末 5 代 |OLS 斜率|<0.005 的"平台化"占比 ≥ 0.50（演化收敛到平台是跨族普遍终态，非 x2_clean 特有）。
- PRIOR: H-R5-2 0.6
- NOVELTY: H-R5-2 1
- KIND: H-R5-2 confirm
- 判据：占比 ≥0.50 → SUPPORTED；<0.30 → REFUTED；之间 → INCONCLUSIVE。mechanical=占比。effect_size=占比−0.5。
- EVAL_UNITS: H-R5-2 1256

## RED_TEAM: 5 0

## 判据脚本
sandbox/judges/judge_r5_meta.txt --selftest / --real（读 unified/*.jsonl 全部 5 文件）。

## 自测用例（手算标准答案）
> 修正记录：初稿手算有误（A 早斜率算成 0.0600，正确 0.0650——分子应为 0.32+0.06+0.09+0.18=0.65；且 B/C 原用例点数不足 H1 的 ≥5 门槛）。自测门首轮 FAIL 抓出，锁定前修正。

```
runA rounds1-8 scores [0.0,0.1,0.2,0.25,0.25,0.25,0.25,0.25]:
  前5点OLS斜率=0.0650（num=0.65/den=10）；总收益=+0.25 符号✓；末5点斜率=0.0000 → 平台✓
runB rounds1-8 scores [0.5,0.45,0.35,0.2,0.15,0.14,0.13,0.12]:
  前5点OLS斜率=−0.0950（num=−0.95/den=10）；总收益=−0.38 符号✓；末5点[0.2,0.15,0.14,0.13,0.12]斜率=−0.0180 → 非平台
runC rounds1-5 scores [0.1,0.3,0.2,0.25,0.25]:
  前5点OLS斜率=+0.0250（num=0.25/den=10）；总收益=+0.15 符号✓；点数<8不入H2
→ H1 一致率=3/3=1.0000（合格3 run）；H2 平台占比=1/2=0.5000（合格2 run）
```

## 三态结局定义
见各假设判据。

## 成本预估
判据 ~100 行；单遍扫描 unified（~2600 行），秒级。

## 新颖性声明
- 任何源都没做过跨族/跨源的"早信号→总收益"或"平台期占比"统计（各源只看自家 run；02-统计 只算了斜率本身）。NOVELTY=1 ×2。
- 边界预期：unified 中有代际序列的 run 集中在衔尾蛇 x2/x3/x3c/x6b 族（混元/豆包多为终态行）——"跨库"实际跨度=衔尾蛇内跨族+跨实验代（x2_clean/x3/x3c/x6b 是四套实验设计）。如实标注。
