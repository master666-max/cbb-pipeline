---
name: library-bootstrap
description: 在任何 agent harness 的工作区一键建立双库自进化体系时调用。触发词：建库、一键建库、library-bootstrap、建 L{n} 库、建{角色扮演/写作/语料/代码/研究/多agent}库、迁移双库。支持 8 档预设（L0 裸奔 → L7 实验）、10 个功能模块自由组合、6 个特色包，模板复制式安装保证跨 harness 可复现。
---

# library-bootstrap · 通用建库 Skill（v1.2）

把本 skill 目录整个拷到目标 harness 工作区，对 agent 说「按 library-bootstrap 建库」即可运行。无需本仓库其他文件。
**用户提示词速查见 `references/PROMPTS-建库提示词速查.md`（或发布包根目录「提示词速查.md」）——不知道发什么指令先翻它。**

## 主流程（严格按序）

1. **选型**：读 `references/decision-tree.md`，解析用户指令 → 预设档位 + 特色包 + 自由组合。解析不了且 harness 支持交互 → 逐项问（预设/特色包/实验模块）；不支持交互 → 默认 L2。
2. **环境探测**：按 `adapters/harness-detect.md` 跑探测（解释器 → .py 拦截 → cron 能力 → 入口文件），结果写目标工作区 env/ENVIRONMENT.md。
3. **依赖校验**：跑 `scripts/bootstrap_verify.txt --deps {模块清单}`，不满足即停，向用户报告缺项。
4. **逐模块安装**：按依赖表拓扑序，逐个读 `modules/{m-*}/install.md` 照单执行。特色包读 `packs/{x-*}/install.md`。铁律：**已存在的文件一律跳过并记录，永不覆盖**。
5. **实验模块**（仅 L7）：逐个读 `experimental/{*}/install.md`，先向用户明示风险清单，确认后才装。
6. **收尾**：跑 `scripts/bootstrap_verify.txt --init {preset} {modules} [--packs ...] [--exp ...]` 生成 manifest；再跑 m-tools 的 lint_library.txt，0 问题才算完成。
7. **报告**：输出安装清单（装了什么/跳过了什么/待确认项）+ 两个触发词说明（task-start / wrap-up）。

## 关键纪律

- **模板复制 > 自由生成**：结构文件全部来自本 skill 的模板（{{SLOT:*}} 填槽），agent 不得即兴改结构。槽位定义见 decision-tree.md 第六节。
- **幂等**：重复安装 = 跳过已存在文件 + 增量补齐；重跑 bootstrap_verify.txt 应全部「一致」。
- **升级**：读目标 .library-manifest.json → diff → 只装新增；哈希漂移的报告差异等用户裁决，不自动覆盖。
- **E-manual 降级**：无 Python 时全部走 install.md 清单式手工安装，脚本只留文档说明。

## 快速参考

- 预设：L0 裸奔 / L1 基础闭环 / L2 标准校验 / L3 演化 / L4 灵魂 / L5 反思 / L6 前沿全家桶 / L7 实验 / L8 超绝激进（自指演化，add-on） / L9 内省仿生（BCA 认知架构，add-on，消融可验）/ CUSTOM 自由组合
- 特色包：x-rp 角色扮演 / x-writer 写作 / x-corpus 语料 / x-code 代码 / x-research 研究 / x-multiagent 多 Agent
- 实验 L7：vector-search / auto-critic / dream-fusion；L8 层：constitution/lifelog/mutation-engine/tournament/council/twin/worldsim（宪章至上）；L9 层：constitution-bca/instrumentation/emotion/goalstack/dual-memory/gwt/sleep-pipeline/dmn（BCA v0.1 仿生架构，消融/干预/谄媚三验收）
- L8/L9 均为独立 add-on 分包，主发布包纯净；详情见 presets/L8.md、presets/L9.md 与各 addon README

## 溯源

本 skill 由 PT-004（建库路径，3 次验证）+ 21 信源 SOTA 雷达 + 本工作区 v2→v4 三轮实装蒸馏而成；源工作区 D:\zcode专用！！！！危险！！！！！！！（knowledge/trajectories/ 全记录）。
