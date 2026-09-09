> [v3 语境适配页（bootstrap_v3 安装器注入，v3.5/J-008a）] 本文件写于 v2.x 语境。v3 库等价物：审计链=audit/lifelog-*.md（engine 自动入链，无需手动 lifelog_append）；变更账本=ledger/changes.jsonl；变异守卫=guard 子命令（基准黑名单+锚定）；条目写入=engine append（schema 十字段）；检索=engine retrieve；state/ 目录对应 state.json 与 memory/。v2.x 原文路径按需参考，冲突处以本页与 spec.md 为准。

# PENDING · GWT 落选队列

> GWT 广播仲裁（tools/broadcast.txt）的落选候选在此排队留档，不丢弃，供人工检视与后续机制取用。
> 当前 broadcast.txt 只写不读本队列（install.md 的"候选源含 PENDING"为设计意图）；回读功能属机器变异候选，需走 MUTATION-SOP 提案。
