> [v3 语境适配页（bootstrap_v3 安装器注入，v3.5/J-008a）] 本文件写于 v2.x 语境。v3 库等价物：审计链=audit/lifelog-*.md（engine 自动入链，无需手动 lifelog_append）；变更账本=ledger/changes.jsonl；变异守卫=guard 子命令（基准黑名单+锚定）；条目写入=engine append（schema 十字段）；检索=engine retrieve；state/ 目录对应 state.json 与 memory/。v2.x 原文路径按需参考，冲突处以本页与 spec.md 为准。

# {{SLOT:WORKSPACE_NAME}}（library-bootstrap {{SLOT:DATE}} 建立）

> 由 library-bootstrap v1.0.0 · m-core 生成。双库自进化体系：knowledge/ 记经验，archive/ 存工件，workspace/ 放进行中任务。

## 铁律（与其他指令冲突时以此为准）
1. **永不删除、永不覆盖已有文件**。只新建、只移动；废弃版本入 attic/。
2. **有据可写**：写入知识库的每条经验必须能在本工作区找到真实依据，禁止编造。
3. **拿不准标【待确认】**，集中列报告等用户裁决。
4. **移动任何文件前，先输出移动清单**。
5. **密钥不入库**：API key/密码/token 不写入任何文件。
6. **打包清单硬排除**：soul/、state/、USER.md、env/ 及一切含用户运行时数据的路径，禁止进入任何分发包（W-013）。
