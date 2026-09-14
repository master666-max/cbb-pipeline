---
name: cbb-anchor
description: CBB P1 锚点树建立与版本化、相对时间归一化辅助。锚点人工前置（技能只辅助不改判，B2 锚点先于偏移）。需要为故事时间建立伪锚点、把"三天后/次年"类相对表述挂靠锚点树、或做时间精度抽检时使用。
---

# cbb-anchor（P1 锚点树 · M1 骨架）

## 职责（P1 建设计划书 §三）

锚点树建立/版本化——**人工前置，技能只辅助不改判**（B2：全局时间锚人工先定，
相对时间挂靠锚点树；没有这步，后续所有时间归一化都在盲猜）。

## Step 0 三条件之二、之三的落地（下发单①输入依据）

1. **伪锚点纪律**：故事时间原点 = `2000-01-01 + i 天`（i = 章序，0-based）。
   这是叙事保序伪锚点，**不冒充真实日期**；`reference_time` 一律来自锚点树，
   **禁止墙钟**（Step 0 Tier1 实证：墙钟会把无日期事实盖成假日期）。
   本模块源代码级禁墙钟（无 `datetime.now/today` 调用，单测静态+功能双检）。
2. 时间归一化自研（Tier1 双模型时间线 0.18-0.67 判定线不过 → 本件兜底，计划内分支）。

## 功能

- `pseudo_anchor(i)` / `story_date(day_offset)`：章序 ↔ 伪日期（纯函数）。
- `build_pseudo_tree(chapters)`：按阅读序为每章生成伪锚点候选（status=provisional，
  **等人工确认后才升 confirmed**——改判权在人）。
- `normalize_relative(expr, context_anchor)`：相对时间表述 →
  `{precision, day_offset/月年增量, flags}`；挂不上显式标记，绝不猜：
  - 无锚可挂 → `missing_anchor`
  - 指代不明（"那天/当时"）→ `ambiguous_reference`
  - 模糊量词（"数日后"）/不可解析 → `unresolved_time`
  （对应隔离区三入口，cbb-quarantine 分组消费。）
- `compare_story_time(a, b)`：精度允许才比，粗精度返回 None（保守不判倒置，供门1 用）。
- 版本化：树存 `anchor-tree.v{N}.json`，修订=新版本新文件，永不覆盖（铁律2）。

## 契约关联

锚点节点 = Record（`record_type="anchor"`, `library="timeline"`，canonical 含
`label/kind/day_offset/pseudo_date/precision/chapter_ref/parent_anchor`）。
伪锚点的 evidence = 章序标记本身（伪锚点不自充故事内证据）。
校验走 `../contracts/cbb_contracts.validate_record`。

## 三态写入桩（M1）

`three_state_write_stub` 与 cbb-coordinate 同纪律：三池分目录、ID 命名、
已存在即跳过；P2 由 cbb-store 接管。

## 用法

```bash
py -X utf8 cbb_anchor.py --chapters 14,38,114 --tree-dir trees
py -X utf8 test_cbb_anchor.py   # 含时间精度抽检电池
```

## M1 边界（P2 扩展点）

- 人工真锚点（纪元原点/主角出生锚/卷首锚）的录入界面与确认流；
- 跨卷锚点重排、时间悖论聚集反查（FMEA「锚点树本身错」防线）；
- 更全的中文时间表述语法（当前覆盖：次日/当天/当晚/N天后/N月后/N年后/半年后/次年/那年冬天类）。
