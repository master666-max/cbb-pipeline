---
name: cbb-gate1
description: CBB P4 门1 确定性规则硬校验。对候选记录做 schema 必填/证据四元组完整性/悬空引用/时间倒置四类确定性检查，拦截附原因码转隔离区。不需要 LLM，纯规则，任何候选入库前必过此门。
---

# cbb-gate1（P4 门1 规则硬校验 · M1 骨架）

## 职责（P1 建设计划书 §三）

确定性规则硬校验：schema 必填 / 证据四元组完整性 / 悬空引用 / 时间倒置。
**拦截 → quarantine，附原因码**。无 LLM、无网络、无时钟——同输入必同判定（可重放）。

## 四校验与原因码

| 原因码 | 检查 | 说明 |
|---|---|---|
| `G1-SCHEMA` | 契约必填 | `contracts/record.schema.json` 全字段校验（经 cbb_contracts；candidate 态放行） |
| `G1-EVIDENCE` | 证据四元组 | 证据非空、四元组类型合规、**quote 可回落到 cbb-coordinate 坐标块**（证据悬空即拦） |
| `G1-REF` | 悬空引用 | canonical.causal_predecessors / entity_refs / supersedes 引用的 ID 必须在已知记录宇宙内 |
| `G1-TIME_INVERSION` | 时间倒置 | 事件 day 精度故事时间早于其 causal_predecessors 的最大 day → 倒置。粗精度（月/年/季）**不判**（借 cbb_anchor.compare_story_time 的保守语义：宁缺毋滥） |

## 拦截 → 隔离区分组（M1 暂定映射，【待确认】）

- `G1-TIME_INVERSION` → unresolved_time
- `G1-REF` → ambiguous_reference
- `G1-SCHEMA` / `G1-EVIDENCE` → low_confidence（结构/证据缺陷=不可信件；细节保留在原因码）

映射为 M1 保守决策，留给审核线/后续设计轮裁决（issues/ 在案）。

## 契约关联

产出 Verdict 形态的判定记录：每 record 一条
`{record_id, verdict: pass|intercept, violations: [{code, detail}], gate_trace_entry}`；
`gate_trace_entry = {gate:"1", verdict_id}` 与 Record.provenance.gate_trace 对齐
（verdict_id 内容哈希→确定性可重放）。

## 用法

```python
from cbb_gate1 import check_batch
result = check_batch(candidates, ctx={"blocks": blocks, "known_ids": {...}, "records_by_id": {...}})
# result["passed"] / result["intercepted"] / result["summary"]
```

## M1 边界（P2 扩展点）

- 门2a 本地 judge + 先例注入、门2b 云端三票、门3 增量触发（P2+）；
- 图约束求解形态升级（组件卡：Gate 1 Rule Checker = 图约束求解，确定性拦截）；
- 与 Skill Registry 联动的记录类型专属规则（S1-S5 校验面）。
