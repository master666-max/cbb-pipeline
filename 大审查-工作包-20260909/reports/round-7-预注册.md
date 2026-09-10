# Round 7 预注册 · 红队挑战 R5 双 SUPPORTED：分层复测（增益分层 / 族分层）

> 状态：预注册。判据 sandbox/judges/judge_r7_stratify.txt 自测 PASS 后先锁后跑。
> source_type=DATA-DRIVEN：H-R7-1 触发于 data-archive 行 5轮H-R5-1（mechanical=0.9268）；H-R7-2 触发于行 5轮H-R5-2（0.8750，boundary 已注明"几乎全为 x2_clean"）。
> 判据遵 OBL-003：双侧区间 + 理论对齐 + 样本量守卫。

## 假设清单

### H-R7-1 天花板效应挑战（direction=证伪，source_type=DATA-DRIVEN·行5-H-R5-1，kind=disconfirm）
- 陈述：R5-H1 的 0.9268 一致率由大增益 run 驱动——小增益层（|total_gain|<0.1）一致率 <0.70（早信号结论降格为"大增益世界的平凡推论"）。
- PRIOR: H-R7-1 0.55
- NOVELTY: H-R7-1 1
- KIND: H-R7-1 disconfirm
- 判据（双侧区间+守卫）：小增益层 n≥10 为前提；一致率 <0.70 → SUPPORTED（证伪成立）；≥0.85 → REFUTED（早信号在小增益层仍稳健，证伪失败）；[0.70,0.85) → INCONCLUSIVE（带内不确定，by design）。mechanical=小增益层一致率（同向：越低越支持证伪）。effect_size=全体一致率−小增益层一致率。
- EVAL_UNITS: H-R7-1 1256

### H-R7-2 族特异性挑战（direction=证伪，source_type=DATA-DRIVEN·行5-H-R5-2，kind=disconfirm）
- 陈述：R5-H2 的 0.875 平台化是 x2_clean 设计产物——非 x2_clean 且非 x1_static（静态基线，平台是构造性的）的其他源 run 平台占比 <0.50。
- PRIOR: H-R7-2 0.45
- NOVELTY: H-R7-2 1
- KIND: H-R7-2 disconfirm
- 判据：其他源层 n≥10 为前提（不足→INCONCLUSIVE·数据不足）；占比 <0.50 → SUPPORTED（普遍性降格）；≥0.75 → REFUTED（跨源平台稳健）；[0.50,0.75) → INCONCLUSIVE。mechanical=其他源层占比。effect_size=x2_clean 层占比−其他源层占比。
- EVAL_UNITS: H-R7-2 1256

## RED_TEAM: 7 0（主动证伪轮，非停摆闸触发）

## 自测用例（手算标准答案）
> 修正记录（锁定前）：初稿手算两处错（A 早斜率 0.019→**0.0150**；B 0.13→**0.1400**——分子求和错误），自测门 FAIL 抓出。另：合成层 n=2<10 守卫触发时 H1 期望=INCONCLUSIVE（初稿误写 REFUTED——守卫分支先于阈值分支）。

```
SYN-A(x2_clean族) rounds1-8 [0.5,0.52,0.54,0.55,0.56,0.56,0.56,0.56]:
  gain=+0.06(小增益); 前5点斜率=+0.0150(num=0.15/den=10) 符号✓; 末5点斜率=+0.0020<0.005 平台✓
SYN-B(x2_clean族) rounds1-8 [0.2,0.4,0.6,0.7,0.75,0.75,0.75,0.75]:
  gain=+0.55(大增益); 前5点斜率=+0.1400(num=1.40/den=10) 符号✓; 末5点斜率=+0.0100≥0.005 非平台
SYN-C(豆包族) rounds1-8 [0.8,0.78,0.76,0.75,0.75,0.75,0.75,0.75]:
  gain=−0.05(小增益); 前5点斜率=−0.0130 符号✓; 末5点斜率=0 平台✓
→ 全体一致率=3/3=1.0000；小增益层(A,C)=2/2=1.0000 但 n=2<10 → H1 INCONCLUSIVE（守卫）
→ x2_clean层平台=1/2=0.5000；其他源层n=1<10 → H2 INCONCLUSIVE（数据不足守卫触发）
```

## 三态结局定义
见各假设判据（含 n 守卫分支）。

## 成本预估
判据 ~120 行（OLS 复用自 r5 判据函数，新文件追加）；无引擎。

## 新颖性声明
- 分层复测（增益×族）在任何源与 R5 均未做过；这是对自有 SUPPORTED 结论的首次受控证伪尝试。NOVELTY=1 ×2。
