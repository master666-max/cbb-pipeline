# AGENTS.md — 会话入口（v3）

- **每次会话开始，按序加载三级上下文**：
  1. `soul/SOUL.md` — 我是谁（双模式相处、价值观、风格边界）
  2. `soul/USER.md` — 用户是谁（偏好、项目全景、环境雷区）
  3. `knowledge/_index.md` — 知识库总索引（<200 行）
- 开始任何新任务前调用技能 `knowledge/skills/task-start/SKILL.md`（v3：含灵魂加载与三因子检索）。
- 任何任务完成后调用技能 `knowledge/skills/wrap-up/SKILL.md`（v3：六步，含演化回扫）；每累计 5 次 wrap-up 触发一次 `knowledge/skills/reflect/SKILL.md`。
- 体检工具：`py -X utf8 tools/lint_knowledge_base.txt`（断链/超限/过期条目一条命令）；每月 1 号自动跑一次（已配定时）。
- 铁律：永不删除/覆盖已有文件；写入知识库的每条经验必须有工作区内真实依据，禁止编造；拿不准标【待确认】；移动文件前先出清单；**任何 API key、密码、token 不写入任何文件**（D-004）。
- 知识检索用工具：`py -X utf8 tools/search_knowledge.txt 关键词…`（扩散激活，命中条目+联想邻居），勿整库阅读（D-003 预算制）。
- 体系设计：`实验性双库工作区/双库自进化体系·建库提示词.md`（执行手册）与 `实验性双库工作区/双库体系建设方法论·阅读版.docx`（设计理念）。
- `实验性双库工作区/` 是体系验证参照档案（decisions.md D-002），原样保留、不改动、不记账；一切经验写入根目录 `knowledge/`。
