> [v3 语境适配页（bootstrap_v3 安装器注入，v3.5/J-008a）] 本文件写于 v2.x 语境。v3 库等价物：审计链=audit/lifelog-*.md（engine 自动入链，无需手动 lifelog_append）；变更账本=ledger/changes.jsonl；变异守卫=guard 子命令（基准黑名单+锚定）；条目写入=engine append（schema 十字段）；检索=engine retrieve；state/ 目录对应 state.json 与 memory/。v2.x 原文路径按需参考，冲突处以本页与 spec.md 为准。

# Pitfalls · 错误教训库

> 编号自 P-001 起。每条四要素：场景/教训（根因）/关键词/实例。实例链接必须指向工作区内真实存在的文件。
> 没有真实依据的教训不写——宁可留空，禁止编造（铁律 2）。

---

<!-- 条目格式模板：
### P-001 / {日期} / {一句话标题}
- 场景：{在什么情况下遇到的}
- 教训：{核心结论，一句话 + 根因}
- 实例：{真实存在的路径}
-->
