> [v3 语境适配页（bootstrap_v3 安装器注入，v3.5/J-008a）] 本文件写于 v2.x 语境。v3 库等价物：审计链=audit/lifelog-*.md（engine 自动入链，无需手动 lifelog_append）；变更账本=ledger/changes.jsonl；变异守卫=guard 子命令（基准黑名单+锚定）；条目写入=engine append（schema 十字段）；检索=engine retrieve；state/ 目录对应 state.json 与 memory/。v2.x 原文路径按需参考，冲突处以本页与 spec.md 为准。

# Trajectory 结构化头规范（海马体侧 · 快记忆）

> 新轨迹文件头必带以下三行（一次成型，追加不改）：
---
> 情绪快照：valence=__ / arousal=__ / certainty=__ / stakes=__（写文件时的 STATE 值）
> 重要性分：__ / 10（= 情绪向量范数 × 目标相关度，wrap-up 打）
> 目标关联：{{GOALS 主目标}}
---
历史轨迹不回溯补头（只增不改纪律）；本规范自安装日起生效。
