> [v3 语境适配页（bootstrap_v3 安装器注入，v3.5/J-008a）] 本文件写于 v2.x 语境。v3 库等价物：审计链=audit/lifelog-*.md（engine 自动入链，无需手动 lifelog_append）；变更账本=ledger/changes.jsonl；变异守卫=guard 子命令（基准黑名单+锚定）；条目写入=engine append（schema 十字段）；检索=engine retrieve；state/ 目录对应 state.json 与 memory/。v2.x 原文路径按需参考，冲突处以本页与 spec.md 为准。

# 消融/干预实验留档（A1/A2/A3 验收）

> 每次消融/干预实验在此记录（操作走 tools/state_intervene.txt）。
> 验收：A1 消融可测差异 / A2 干预方向可预测 / A3 谄媚监控（纠错率不降超 3%）。

| 日期 | 实验 | 操作 | 结果 | 结论 |
|---|---|---|---|---|
