# RELEASE NOTES · CBB v3.0.0（2026-09-27）

> 分支：`refactor/phase-a`（Phase A→E 四连快进）；tag：`v3.0.0`。
> 构建产物：`cbb-pipeline-skill/cbb-pipeline/`（HASHES.json manifest，`--verify` 可复算；**手改即 FAIL**）。

## 本版新东西

1. **契约 v3**：canonical 断言位/陈述位二分（profiles 六库）+ `t_valid/t_invalid/at` 时间位——**失效记账制**取代"状态变化=矛盾"：死亡行走、时序精化（人物→人物(迷宫生物)→人物(迷宫守护者)实证三代并存）走 invalidations.jsonl，旧件字节不动、历史全保留，不再进隔离区。
2. **store 写入决策树五分支**：新建/一致重复（闸2 NLI 复核）/互补陈述（内容哈希 event，**incoming 不再丢失**——qoder D-23 整库作废事故的根治）/失效记账/真矛盾（闸1 三分+无闸保守回落）。`admit_or_merge` 冻结为 v1 等价锚（PROVEN 指纹 aafe3804 不回退），新流水线一律走 `write_decision`（at 必填）。
3. **gate 候选态输入档**：畸形 canonical→G1-SCHEMA 码不崩；null record_id→哈希占位。
4. **NLI 双通道矛盾预筛**：LLM 通道（env）+ 本地 RoBERTa-NLI 通道（缺依赖自动降级）；两通道一致采纳、不一致人审；上岗小考分离度 ≥0.70+分桶校准。
5. **运行契约闸**：端点在位/消费件存在/已接线/本批回执——四缺一 BLOCKED，治"凭证在位≠接线"。
6. **投影派生层**：归属单键 `group_id` 写读同源（D-13 根治）；节点/边双时序列（valid_at/invalid_at）；投影检查点（崩溃重放代替 mtime 猜测）；**导出债务 repay 语义**（"债务=0∧终审可用"可达）。
7. **runner 编排**：门控动态切分（θ 三条件，旗标 CBB_DYNAMIC_SPLIT 默认 off=整章等价）+场景软标签+承接摘要 ≤200 字+三层上下文包（实体卡/滚动摘要/近窗+sticky/cooldown）。
8. **治理层**：对样双轨（发现轨/估计轨分离，Wilson 95% 区间——"30 全过=95%"的点宣称从此禁用）+植物捕获金标+缺口队列+ER 归一三段（合并可撤销，0.85 绝对带废弃）+**票数晋升 G5**（三考官 env 编制 LOCAL/DEEPSEEK/QWEN，隔离评审+答案对调，against>0 即 human）。
9. **安全拔除**：发布件不再写死任何实例/容器名（CBB_NEO4J_CONTAINER env 化）；**docker inspect 抠凭据通道删除**；Graphiti 五件退役（上游三雷未修+add_triplet 不绕失效/去重）。

## 修复的缺陷（外来消费者实测 29 条中的 13 条开放项）

D-1 ✅ D-2 ✅ D-6 ✅ D-13 ✅ D-14 ✅ D-15 ✅ D-21 ✅ D-23 ✅ D-24 ✅ D-25 ✅ D-28（机制）✅ D-29（判据面）✅；移交：D-18/19/20/27（Phase C runner/CLI 卫生批后续）、D-5/D-12 上游版本面。全程修前反例先红（PT-020）。

## 破坏性变更

- 状态变化不再进矛盾轨（失效记账）；隔离区只收"不可同真断言位冲突"。
- 通过率宣称必须带 Wilson 区间；LQAS 判定按失败数。
- `write_decision` 缺 at 直接 ValueError。
- 合并必须留合并日志；split 回滚一等公民。

## env 契约（全部 env 注入，零硬编码）

```
CBB_NAMESPACE / CBB_STORE / NEO4J_HTTP / NEO4J_PASSWORD / CBB_NEO4J_CONTAINER
EXAMINER_LOCAL_BASE / EXAMINER_LOCAL_MODEL
EXAMINER_DEEPSEEK_BASE / EXAMINER_DEEPSEEK_MODEL / EXAMINER_DEEPSEEK_API_KEY
EXAMINER_QWEN_BASE / EXAMINER_QWEN_MODEL / EXAMINER_QWEN_API_KEY（回落 DASHSCOPE_API_KEY）
CBB_DYNAMIC_SPLIT（默认 off）/ CBB_SPLIT_THETA_*
```

## 外部消费者验收指引（V6）

重放 R000/R001 五单元（判据：假矛盾=0、互补陈述入 event、失效记账非隔离、不触发整库作废）；本版 BUILD-STATE：`正典库构建系统/全量重构-PhaseA-BUILD-STATE.md`（A→D 四相收口记录）。
