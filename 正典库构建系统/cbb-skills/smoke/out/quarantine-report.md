# 隔离区报告（请你确认清单）

> cbb-quarantine M1 ｜ 待裁决 3 项 ｜ 已裁决 0 项
> 纪律：显式隔离，绝不静默丢弃（B6）；以下条目按**阻塞下游计数降序**排列。

## 分组统计
- **missing_anchor**: 1 项
- **ambiguous_reference**: 1 项
- **low_confidence**: 1 项

## 待裁决清单（按阻塞下游计数降序）

### 1. [missing_anchor] `q-2ff9f018c7b5`（阻塞下游 6 项）
- 详情：「次日」无锚可挂（mini 冒烟）
- 来源：cbb-anchor ｜ 关联记录：（无）
- 阻塞：cand-entity-04c1eba1881d, cand-entity-52c6e72bbb59, cand-entity-77a70bfd4406, cand-entity-a455d7574064, cand-event-7e5f4f7ec342, cand-event-edd91773acf8
- **请你确认**：该条应判 confirmed 入库，还是 rejected 作废？

### 2. [low_confidence] `q-73b92e89cf51`（阻塞下游 2 项）
- 详情：证据[0] quote 悬空（坐标块内不可回落）: v1c14 根本不存在的引文…
- 来源：cbb-gate1 ｜ 关联记录：cand-entity-785833b16993
- 阻塞：cand-entity-77a70bfd4406, cand-entity-a455d7574064
- **请你确认**：该条应判 confirmed 入库，还是 rejected 作废？

### 3. [ambiguous_reference] `q-b2818f450b37`（阻塞下游 1 项）
- 详情：「那天」指代不明（mini 冒烟）
- 来源：cbb-anchor ｜ 关联记录：（无）
- 阻塞：cand-entity-77a70bfd4406
- **请你确认**：该条应判 confirmed 入库，还是 rejected 作废？

## 已裁决（终态留档，不删）
- （无）
