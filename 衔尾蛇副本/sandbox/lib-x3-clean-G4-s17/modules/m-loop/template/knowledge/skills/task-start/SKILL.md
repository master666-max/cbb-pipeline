> [v3 语境适配页（bootstrap_v3 安装器注入，v3.5/J-008a）] 本文件写于 v2.x 语境。v3 库等价物：审计链=audit/lifelog-*.md（engine 自动入链，无需手动 lifelog_append）；变更账本=ledger/changes.jsonl；变异守卫=guard 子命令（基准黑名单+锚定）；条目写入=engine append（schema 十字段）；检索=engine retrieve；state/ 目录对应 state.json 与 memory/。v2.x 原文路径按需参考，冲突处以本页与 spec.md 为准。

---
name: task-start
description: 开始任何新任务前必须调用。当用户开启新任务、要求分析/写代码/处理数据/写文档时使用。读取知识库索引，检索相关教训与范式，开工前声明规避项与复用项。
---
# 任务启动三步

1. **读 `knowledge/_index.md`**，列出与当前任务类型相关的 pitfalls 与 patterns。
2. **读 `archive/_INDEX.md`**，找出可复用 ★★★ 项目作为脚手架候选。
3. **开工前向用户声明**：本次规避哪些坑、复用哪个范式/模板，确认后再动手。

## 执行纪律
- 若索引为空或无相关条目，直接声明「无既有经验可复用」即可开工，不要阻塞。
- 命中的 pitfall 在任务中要主动规避；命中的 pattern 要按其核心步骤执行，并把验证结果反馈给 wrap-up。
