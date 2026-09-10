# Task-002 双库 v3 升级轨迹 · 2026-09-03

> 原始轨迹层：只追加，只写不改。平时不加载，仅在复盘时引用。

## 任务
按用户要求「还有什么优化的，比如灵魂系统」+「要目前最先进的库架构」，对 v2 双库做 SOTA 对齐升级。

## 过程
1. 用户批评只看本地文件 → 用 webReader MCP 调研五篇 SOTA 论文：A-MEM(2502.12110)、Mem0(2504.19413)、MemGPT(2310.08560)、Generative Agents(2304.03442)、Voyager(2305.16291)。Context7 MCP 因 API key 失效不可用。
2. 写计划书 workspace/双库v3优化计划书.md，AskUserQuestion 三项裁决：SOUL 写入双模式 / lint 纯手动+每月自动 / USER.md 工作区为准。
3. P0：soul/SOUL.md + soul/USER.md + AGENTS.md v3（三级加载）。
4. P1：pitfalls/patterns 全部 7 条加 关键词/关联([[]]双链)/版本 字段（A-MEM 结构化属性）。
5. P2：task-start v3（第 0 步加载灵魂）、wrap-up v3（第 6 步演化回扫 + 反思计数）、reflect 新技能。
6. P3：tools/lint_knowledge_base.txt 体检工具；CronCreate 每月 1 号 9 点自动体检（automation-bb8b3e66）。
7. P4：knowledge/skills/docx-pipeline/（SKILL.md + scripts 5 件自 comfyui-docx-scratch 复制 + references），PT-002 升 v2 版本号并回链。
8. 收尾：_index v3（反思计数行）、trajectory、归档 dual-library-v3、_INDEX 新行、lint 验收。

## 关键决策
- v3 不引向量库，维持 D-001 纯 Markdown（A-MEM 的演化用"修订+版本号"在 Markdown 上即可实现）。
- 灵魂层限定 2 文件（SOUL/USER）且控制篇幅，避免常驻上下文膨胀。

## 本任务验证的模式
- PT-004 双库建库/升级路径验证 +1（schema 迁移与技能固化是其扩展步骤）。
