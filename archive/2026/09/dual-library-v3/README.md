# 双库 v3 升级（dual-library-v3 · 完成于 2026-09-03）

> manifest 归档（D-001）：改动分布在多个既有文件与新增目录，本体不搬移。

## 一句话
按五篇 SOTA Agent 记忆论文（A-MEM/Mem0/MemGPT/Generative Agents/Voyager）把 v2 双库升级为 v3：灵魂层、条目 schema v2、六步收尾、反思层、体检工具、首个固化技能。

## 复现
- 计划书：`workspace/双库v3优化计划书.md`（含用户三项裁决记录）
- 改动清单：soul/（SOUL.md、USER.md 新建）；AGENTS.md v3；pitfalls/patterns 7 条加字段；skills/task-start、wrap-up 升 v3；skills/reflect、skills/docx-pipeline 新建；tools/lint_knowledge_base.txt 新建；knowledge/_index.md v3；CronCreate automation-bb8b3e66（每月 1 号 9 点体检）

## 数据流
workspace/双库v3优化计划书.md →（用户裁决）→ soul/ + skills v3 + tools/ →（lint 验收）→ 本归档

## 关键决策
- 维持纯 Markdown 不引向量库（D-001 延续）；A-MEM 式演化用「修订原条目 + 版本号」实现。
- 灵魂层 2 文件控篇幅；USER.md 工作区为准、用户级 memory 只留指针（用户裁决）。

## 踩坑与经验
- 范式：patterns.md#pt-004（建库/升级路径 +1 次验证）
- Context7 MCP API key 失效（2026-09-03），网络调研改用 webReader。

## 复用提示
- ★★★ 高：其他工作区升级 v3 直接照 P0→P4 顺序；lint 工具复制即用（改 MD_DIRS）。

## 未竟事项
- reflect 首跑（待 wrap-up 计数满 5）；docx-pipeline 技能待下次 docx 任务实装验证（PT-002 将达 3 次，触发升级评审）。
