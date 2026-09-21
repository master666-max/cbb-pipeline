# cbb-quarantine（本体版 v2 · 三子类+urgency）

> B6 隔离区管理器。前置：gate1（拦截原因码/子类）、anchor（countdowns_due 到点口径）。落盘 append-only。

## 三子类（用户裁决案 2026-09-15：quarantine 三子类，不增设第四态）

| 子类 | 中文 | 语义 |
|------|------|------|
| `contradiction_pending` | 矛盾待裁决 | 死人走路/时序倒置/同批矛盾/关系缺回链/实体不可归一 |
| `extrapolation_unverified` | 外推待证 | 无证据/证据悬空/结构不合规/无锚/指代不明/低置信 |
| `overdue_omission` | 超期遗漏 | 期限项（契诃夫枪/开环）到期未兑现 |

五分组（unresolved_time/missing_anchor/ambiguous_reference/entity_unalignable/low_confidence）保留为**细粒度入口**；三子类为**分流层**（统计+路由）。gate1 携带子类时显式优先；期限项（tier/planted/target）自动归超期遗漏。

## urgency 公式（webnovel-writer status_reporter.py:507-546 转译）
- `urgency = (已过章节/目标回收章节) × 层级权重`——核心 **3.0**（必须回收否则剧情崩塌）/支线 **2.0**（否则显得作者健忘）/装饰 **1.0**（可回收可不回收仅增加真实感）。
- 状态分档：🔴 已超期（current≥target，到点即超期——与 anchor.countdowns_due 同口径）／🟡 警告（进度比≥0.8，CBB 定约）／🟢 正常。
- `top_urgent(n=3)`：**只取前 3 条**（webnovel 写前注入 urgent_loops 前 3 条纪律）；🔴 超期项在报告置顶（遗漏告警）。

## 吸收项
- 🔴超期态（danghuangshang 遗漏告警）——超期持续浮出不沉底。
- `[?]` 内联标记+行号汇总（graphify-novel 字段级轻量隔离）：`scan_inline_unsure(text)` 扫描 `[?]` 按物理行号汇总，`inline_report` 出 markdown——与记录级隔离互补（标记不删不改，P-003）。

## 保留面（v1.0）
五分组请你确认报告；append-only 裁决通道（confirmed/rejected 终态留档不删，同条不可二裁）；登记幂等（item_id 内容哈希）；报告确定性（无时钟字段——current_chapter 由调用方显式传入）。

## 移出
三态写入桩 → cbb-store（U-B07）。

## 用法
```bash
py -X utf8 cbb/cbb-quarantine/cbb_quarantine.py --root qz --register unresolved_time "细节" rec-1 cbb-gate1
py -X utf8 cbb/cbb-quarantine/cbb_quarantine.py --root qz --report --current-chapter 20
```
