# CBB 本体版（全量构筑版 · 阶段二产物根）

> 依据：《本体构筑-工单.md》v1.0（唯一指令源）§0——本目录为正典库构建系统本体落盘根。
> 前身：`../cbb-skills/`（实验版，FROZEN 只读，交接基线 73 单测）。本目录是**全量构筑版**（吸收 16 仓分析成果的重构产物），两者并存不覆盖。
> 状态缓存：`../本体构筑-BUILD-STATE.md`（磁盘+git 为事实）。

## 目录

- `contracts/` — 四契约 schema v2 + 校验器（U-B01）
- `cbb-coordinate/` — 幂等坐标+追加序纪律（U-B02）
- `cbb-anchor/` — 双时间轴 tick/instant/time（U-B03）
- `cbb-extract/` — 四面防御抽取（U-B04）
- `cbb-gate1/` — 三域校验 validate/links/continuity（U-B05）
- `cbb-quarantine/` — 三子类隔离区+urgency（U-B06）
- `cbb-store/` — 双轨合并+UNIQUE 约束族（cbb-merge 并入，U-B07）
- `smoke/` — 集成冒烟（U-B08）
- `自审日志/` — §3 十轮自审逐轮留痕（每单位一个文件）
- `issues/` — 工单与事实冲突登记处（§0 前言约定）
