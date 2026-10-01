# cbb-anchor（本体版 v2 · 双时间轴）

> 锚点树+双时间轴系统。前置：cbb-coordinate（摄入序=章阅读序）。消费契约 Record v2.0（record_type=anchor）。

## 双时间轴模型（v2 重构核心；第一对照项=neuro-book 双轴设计，转述自 `../全量构筑版-分析报告/neuro-book.md`，零其源码接触）

| 轴 | 含义 | 约束 |
|----|------|------|
| `tick` | 摄入序/叙事推进序（transaction time） | 宿主发放全序整数，**永远单调**（build_timeline 非递增即拒），知识边界权威，**必填** |
| `instant` | 故事时间（valid time，世界原点起的天偏移） | **可回退**——倒叙/插叙/回忆章 tick 递增而 instant 后退（这正是必须双轴的原因）；可空 |
| `time` | 人读原文 | verbatim 保留，**不可比较、不参与排序**（伪锚点禁令的正面表述） |

- **as-of 双查询语义**（`asof`）：`as_of_tick`=知识边界（叙事推进到这里时知道多少，tick≤）/`as_of_instant`=世界状态（故事时间这一刻世界什么样，instant≤）/双给=AND/双空=全知。
- **缺坐标判不可见**：instant 为 None 的条目对 as_of_instant 查询**不返回**——宁可漏召回不可泄漏。
- **故事序视图**（`story_order`）：按 instant 升序重组倒叙；缺坐标沉底保持 tick 序；只读永不改号。
- **章号轴回放**（`replay`，吸收 webnovel）：instant 缺失时的降级方案——按 tick 回放叙事，instant 有则作注记，无不影响次序。

## 保留面（v1.0 不动）
- 伪锚点 = 2000-01-01 + i 天（i=摄入序），保序不冒充真实日期；**禁墙钟**（源码静态检查+功能双检单测锁定）。
- 相对时间归一化 `normalize_relative` + **18 条精度抽检电池**（test_battery_count_18 锁条数）：挂不上锚显式标记 missing_anchor/ambiguous_reference/unresolved_time，绝不猜；月/年粒度不折天（保守）。
- 版本化落盘：修订=新版本新文件，同版本已存在即跳过（永不覆盖）。

## v2 新增
- `instant_from_relative`：人读时间串→instant 自研解析入口（16 仓无现成，Step 0 已判）；仅 day 精度产出 instant，粗精度不冒充。
- `countdowns_due`（吸收 chinese-webnovel）：倒计时到点兑现判定原语——未兑现且 due_tick≤当前 tick 即浮出（供 cbb-quarantine 🔴 超期态消费）。
- anchor Record canonical 增双轴字段（tick/instant），契约 v2.0 verified_against 三件套随构造落位（调用方传入管线快照；未传时占位 `1970-01-01`——值来自输入非时钟，禁墙钟不破）。

## 移出
三态写入桩 → cbb-store（U-B07）。

## 用法
```bash
py -X utf8 cbb/cbb-anchor/cbb_anchor.py --chapters 14,38,114 --tree-dir trees --vol 1
```
