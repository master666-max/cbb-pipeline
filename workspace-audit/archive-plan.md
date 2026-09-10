# archive-plan.md — 归档方案（2026-09-10，只出方案不执行）

> 铁律：永不删除；回退一律移 attic。本方案为建议，执行需人工批准（R1/R3）。
> 状态定义：CANONICAL=权威现行；SUPERSEDED=已被修订取代（原地保留+标注）；DRAFT=草稿；可安全移入 attic=已嵌入上位产物的中间件。

## 一、账本类（全部 CANONICAL，永不移动永不改写）

claim_ledger.csv、alias_map.csv、tree_edges.csv、lit-ledger.csv、ordering-claims.csv、ghost-papers.csv、incident-log.csv、mechanism-registry.csv、lm-matrix.csv、supersede_log.csv、audit-log.csv、delta-baseline.csv、ghost_list.csv、participants.csv、supersede_log.csv

## 二、报告与治理类（CANONICAL）

- 00-PROMPT.md（v1 规格）、PROMPT-SPEC-v2.md（v2 规格）、gate-revision.md（裁决本体）、HALT.md（中止与解除史）、progress.md（任务账本）
- 00-盘点.md、00-文献清单.md、0.5-试金石.md、1-实体总表.md、1-版本谱系.md、3-分支树.md、04-diff.md、30-景观五区.md、06-新旧文献交叉.md、07-L轴.md、08-LM矩阵.md、09-M-STATUS.md、10-branch-proposals.md、99-MAP.md、archive-plan.md、red-team-input-manifest.csv
- 20-分支树.mmd（渲染图）、00-重复表.csv（6,759 行机械产物，大文件但为盘点权威产物）

## 三、SUPERSEDED（原地保留，已带内部标注）

| 位置 | 内容 | 被谁取代 |
|---|---|---|
| 00-PROMPT.md 阶段4 条款 | 原单阈值质量门 | gate-revision.md §一（2026-09-10 标注） |
| 04-diff.md §五 | 按 >25% 阈值的 HALT 判决叙述 | gate-revision.md（HALT §六 解除） |
| HALT.md §一–§五 | 中止理由与出路清单 | HALT.md §六（用户裁决，原地保留） |
| tools/phase5-guide.md §五 v1 关键词表 | 死因表初版（覆盖 50%） | 同文件 §九 v2 块（86.5%） |
| tools/phase6-guide.md §三.3 | S4 自注计数 8 | 同文件 §十 v2 块（实测 10） |
| incident-log.csv 第 2/3 行重复行 | 双写冗余 | 无（保留原样，计数按唯一行，见 progress 开工登记） |

## 四、可安全移入 attic（候选清单——需人工批准后才移动）

| 文件 | 理由 |
|---|---|
| data/phase5-frag-tier1.md、phase5-frag-frontier.md、phase5-frag-graveyard.md、phase5-frag-contradicts.md | 四张表片段已逐字嵌入 30-景观五区.md，为防手抄中间件 |
| data/phase4-diff-detail.csv、phase4-content-uncovered.csv | 阶段4 明细档案（1,582+226 行）——若终报审定后空间紧张可移，**建议保留**（04-diff 引用） |

## 五、DRAFT

无（全部产物经阶段收尾三件套+commit）。

## 六、tools/ 与 data/ 其余文件

全部 CANONICAL（各阶段 guide/脚本/数据为报告的可复现入口，progress.md 逐阶段登记哈希）。
