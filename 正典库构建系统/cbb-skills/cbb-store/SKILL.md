---
name: cbb-store
description: CBB B1/B5 三态写入纪律与版本化存储。candidate 按门禁结果路由 confirmed/provisional（入正典库）或 quarantine（入隔离区）；supersedes 版本化修订链永不覆盖旧件；Part XI 置信度阈值路由。任何候选入库动作必须经此件。
---

# cbb-store（B1/B5 三态入库 · M1 骨架）

## 职责（P1 建设计划书 §三）

三态写入纪律（P1: candidate→confirmed/provisional/quarantine）+ 版本化 supersedes。
**B1 是全架构灵魂：错误可以产生，但 confirmed 的库里它进不来。**

## 三态路由纪律

```
admit(record, decision)：
  confirmed / provisional → libraries/<library>/<status>/<record_id>.json（正典库内）
  quarantine             → 隔离区（cbb-quarantine 登记条目，不进任何 library 目录）
route_by_confidence(conf)：
  ≥ τ_provisional(0.85) → provisional
  <  τ_provisional      → quarantine(low_confidence)
  （confirmed 永不因置信度单独达成——门2b/人工通道缺席时，confirmed 只走人工晋升）
```

阈值取 Part XI（τ_confirmed=0.97 / τ_provisional=0.85）；M1 无校准器，用名义值。

## 写入纪律（铁律对齐）

- **文件即记录，写后不改**：入库 = 新 JSON 文件（以 record_id 命名）；已存在即跳过（幂等）。
- **状态迁移走旁车日志** `transitions.jsonl`（append-only）——文件后端下
  Record.provenance.status_history 的等价物；P2 图后端由 Graphiti valid_at/invalid_at
  边原生承担（Part IV：库的审计日志内生于图谱）。
- **supersede 版本化（B5）**：新版本新文件（version+1, supersedes=旧 id），
  旧件字节不动；`supersede-index.jsonl` 登记链，`resolve_latest()` 沿链取最新。

## 后端

- `jsonl-file`（M1 实现）：上述布局，确定性可测。
- `neo4j`（P2 桩）：按 Step 0 Tier2 已验证配置接入（bolt://localhost:7687 +
  Graphiti），M1 显式 NotImplementedError 指路，不写未测运行时代码。

## 契约关联

入库前严格校验 Record（status 必须等于目标态，gate_trace 附加门1 判定条目）；
隔离路由的分组映射与 cbb-gate1 的 REASON_TO_QUARANTINE_GROUP 对齐。

## 用法

```python
store = ThreeStateStore(root_dir)
store.admit(candidate, "provisional", gate_trace_entry=chk["gate_trace_entry"])
store.supersede(old_id, new_canonical, evidence=…)
store.status_transition(record_id, "confirmed", by="human")  # 人工晋升通道
```

## M1 边界（P2 扩展点）

- 门2a/2b/门3 判定接入后的完整路由；校准器分桶阈值；
- Neo4j/Graphiti 后端（双向时序原生审计日志）；
- 检疫期（quarantined_precedent）与 VerdictKB 写入路径（P3）。
