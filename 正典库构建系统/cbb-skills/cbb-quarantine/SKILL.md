---
name: cbb-quarantine
description: CBB B6 隔离区管理。五类分组（unresolved_time/missing_anchor/ambiguous_reference/entity_unalignable/low_confidence）、阻塞下游计数排序、"请你确认"清单报告生成、人工裁决通道（confirmed|rejected 终态留档不删）。任何"处理不了"的记录显式入区时使用。
---

# cbb-quarantine（B6 隔离区 · M1 骨架）

## 职责（P1 建设计划书 §三 / CBB Part VI）

五类分组 + 阻塞下游计数排序 + 报告生成。**隔离区是一等公民**（B6）：
处理不了的显式隔离并出报告，绝不静默丢弃或猜测。
**隔离区报告即高价值产出**——"这 137 处请你确认"清单好过埋雷的完整年表。

## 五类分组（照抄 Part VI）

`unresolved_time / missing_anchor / ambiguous_reference / entity_unalignable / low_confidence`

## 数据形态

- 落盘：`<root>/items.jsonl`（登记，append-only）+ `<root>/adjudications.jsonl`（裁决日志）。
- 条目：`{item_id, group, source, record_id, detail, blocks_downstream[], status}`；
  `item_id` = 内容哈希 → 重复登记幂等跳过。
- 状态机（Part V）：`quarantine ──人工裁决──→ confirmed | rejected（终态，留档不删）`。
  裁决只能由人发起（`by="human"`，M1 无自动晋升通道——晋级走 cbb-store 的状态迁移）。

## 报告（第一产出）

`report_markdown()`：分组统计 + 待裁决清单（**阻塞下游计数降序**——优先裁决高阻塞项，
FMEA「隔离区积压」对策）+ 每项「请你确认」标注 + 已裁决终态留档节。
报告确定性（无时钟字段），同状态必同文。

## 接口

```python
zone = QuarantineZone(root_dir)
zone.register("unresolved_time", detail="三天后无法挂锚", record_id="cand-x",
              source="cbb-anchor", blocks=["cand-y", "cand-z"])
zone.adjudicate(item_id, "rejected", note="金标复核为误报")
md = zone.report_markdown()
```

## 三态写入桩（M1）

`three_state_write_stub` 与其他 cbb-* 同纪律（quarantine 池即本区对接点）。

## M1 边界（P2 扩展点）

- 晋升通道与 cbb-store 状态迁移的线上对接（当前裁决结论落日志，store 侧入库由 P2 联动）；
- 仪表盘对接（可观测性 #1 隔离区积压率按类型分桶）；
- 报告导出多格式（md → docx 走 docx-pipeline 技能）。
