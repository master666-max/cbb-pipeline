# 知识库索引（2026-09-03 建立）

> **每次任务开始必读本文件。** 常驻 AI 上下文，保持 200 行内。
> 维护规则：每次 wrap-up 的第 5 步同步更新；按验证次数/触发频率排序；断链当场修复。

## 使用方式
- 任务开始：配合 `skills/task-start/SKILL.md` 三步启动。
- 任务结束：配合 `skills/wrap-up/SKILL.md` 五步收尾。
- 条目格式与写入纪律见 `pitfalls.md` / `patterns.md` 文件头。

## 高频 Pitfalls（按触发次数排序）
- [P-001 大 PDF 提取路径（py 启动器 + pypdf）](pitfalls.md#p-001--2026-09-03--大-pdf-不能用-read-工具直接读windows-下用-py-启动器--pypdf-提取) — 1 次触发

## 验证过的 Patterns（按验证次数排序）
- [PT-001 docx 生成验收流水线](patterns.md#pt-001--2026-09-03--docx-生成验收流水线) — 已验证 1 次 · 适用：正式 Word 文档产出
- [PT-002 空工作区建库执行路径](patterns.md#pt-002--2026-09-03--空工作区建库执行路径) — 已验证 1 次 · 适用：新工作区首次搭建双库

## 可用 Skills
- `task-start` v1.0 — 触发词：新任务、开始、启动（已就绪）
- `wrap-up` v1.0 — 触发词：wrap-up、任务完成、收尾（已就绪）

## 架构决策（Decisions）
- [D-001](decisions.md) 双库从纯 Markdown + 索引起步，不引入向量库
- [D-002](decisions.md) 建库任务跳过历史挖掘阶段的依据
- [D-003](decisions.md) 体系文件「引用不搬移」归档方式

## 原始轨迹（Trajectories，平时不加载）
- `trajectories/2026-09-03/task-001-建库.md` — 双库体系建立过程记录
