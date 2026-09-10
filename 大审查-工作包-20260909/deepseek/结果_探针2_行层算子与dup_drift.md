# 探针 2 · 行层算子 × dup-drift（H7）— 结果

> 时间 2026-09-08 ｜ 场景 dup-drift(有结构: 组首领+近似重复副本, 副本 links 指向首领) vs clean(无结构)
> 新增臂 gated-row: 每代先用**可见证据**(links + 内容 Jaccard>=0.5 同 topic)检测近似重复簇 → 提案"冗余副本 retire(首领保留)" → 宽松容差验收(tol=0.04, 不损害即采纳, E7 哲学) → 之后再演参数
> 世界改动: dup-drift 金标改为仅组首领(gold_exclude_roles=["dup"]) — 副本是可观测噪声, 去重价值可测
> 20 代 × 6 seeds, 独立分析脚本读盘

## 1) 主结果(真值集 u_audit, recall@5)

| 场景 | static | gated(仅参数) | gated-row(+行层) | row-ops 边际 | 正种子 |
|---|---|---|---|---|---|
| **dup-drift** | 0.2037 | 0.3519 | **0.4352** | **+0.0834** | 6/6 |
| clean | 0.2037 | 0.4815 | 0.4815 | 0.0000(零操作) | 6/6 |

- dup-drift: 移除 22/24 个副本(平均; seed1=19), ops_rejected=0(宽松验收, 从不损害);
  gated-row 相比纯参数 gated 的 Δ vs static 从 +0.148 升到 +0.232 → **行层算子提供 +0.083 检索增益**(去重降低同组副本对 top-5 的拥挤, 让组首领/其他高价值条目可及; 金标=首领, 故 recall 可观测提升)。
- clean(无 links/无重复结构): 检测零簇 → 零操作 → 与 gated **逐位一致**(u_audit/gap/redun 全同) → **无结构时重组零收益零代价**(E6 否定性结论的精确复现带)。

## 2) 冗余度(设计为重组质量轴) — 诚实的指标教训

| 场景 | static | gated | gated-row |
|---|---|---|---|
| dup-drift redun_hold | 0.4289 | 0.6419 | 0.6532 |
| clean redun_hold | 0.1327 | 0.6547 | 0.6547 |

top-5 两两 Jaccard **未随去重下降**(反而略升): 同主题 top-5 天然共享主题词/语义 token → 该指标被主题内词汇重叠主导, 无法分辨"真重复"与"同主题多样性"。**结论: 冗余度需按"语义组"计数(组内成员重复)而非 token 重叠**; 本轮不以它作判据, 以 recall 增益为准。

## 3) 真实路径验证(引擎驱动的重组 = 真实 b3 retire)

seed1 gated-row 终局: 活动条目 77, 19 条被引擎 retire 的副本以失效标记注入真实库 → 真实 b3 retire **移动 19 条 → attic**;
- doctor: 前后均「memory 96 / audit 96 / ledger 96 / 审计链 连续 / state 根一致 / 五态 全一致」
- integrity: chain_bad=0, mem/audit mismatch=0, merkle_ok=true, attic_files 0→19
- 泄漏: 被 retire 的条目在真实 retrieve top-5 中出现次数 = 0

→ **行层重组(append-only 语义下: 副本 retire 留痕入 attic)与记忆一致性(H6)不冲突**, 且走的是真实代码路径。

## 4) 结论(H7)

**支持(场景依赖)**: 行层算子收益**严格依赖可发现结构** —
- dup-drift(links+近似重复存在): +0.083 检索增益, 6/6 种子为正;
- clean(无结构): 零操作、零收益、零代价, 与 gated 逐位一致;
- 引擎的"重组"完全走 append-only/retire 语义(铁律 1: 移 attic 而非删除), 一致性由真实 b3 保证。
与报告 E6(无结构则结构演化无收益)/E28(盲目归并有害)自洽; 与 E32/E73 家族一致: 有效方案=利用已有可观测量(links+重复度), 而非发明启发式。

## 产物
- out_v2_rowops2/ (rows_clean/dup-drift, manifest, p5_real_spot, analysis_summary)
- out_v2_rowops2/integrity_real/dup-drift_seed1_gatedrow.json (真实 retire 验证)
