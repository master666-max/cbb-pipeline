# AGENTS.md — 会话入口（{{SLOT:WORKSPACE_NAME}}）

- **每次会话开始，先读 `knowledge/_index.md`**（知识库总索引，<200 行常驻），再开始任务。
- 开始任何新任务前调用技能 `knowledge/skills/task-start/SKILL.md`（如已安装）。
- 任何任务完成后调用技能 `knowledge/skills/wrap-up/SKILL.md`（如已安装）。
- 铁律：永不删除/覆盖已有文件；写入知识库的每条经验必须有工作区内真实依据，禁止编造；拿不准标【待确认】；移动文件前先出清单；密钥不入库。
- 工具（如已安装 m-tools）：`{{SLOT:PY_RUNNER}} tools/lint_library.txt`（体检）、`{{SLOT:PY_RUNNER}} tools/search_knowledge.txt 关键词`（检索）。
{{SLOT:EXTRA_LINES}}
