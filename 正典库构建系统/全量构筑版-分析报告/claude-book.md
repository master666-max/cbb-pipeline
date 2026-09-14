# claude-book (ThomasHoussin) 详报 · U-A05

> 分析日期：2026-09-15 ｜ 构建线产出，判定权在审核线
> 源码位置：`现成技能侦察/源码/claude-book/`（clone --depth 1，可见提交 3fdebbb Merge PR #2）
> 方法：主线直读（217 文件；README/CLAUDE.md/2 核心技能/4 状态模板/timeline/2 脚本头部/bible 样例精读）

## §1 架构与数据流

**【三谜之二谜底】191 篇 md = "框架 + 完整实例项目"双重身份**：本仓不是纯工具仓，而是带成品的多代理写作框架——`analysis/output/club-des-cinq-01~18/`（56 md，《五伙伴历险记》法语系列 18 本书的分析输出）+ `state/chapter-01~18/`（76 md，每章 4 个状态文件归档+template 4）+ `story/`（20 md：synopsis/plan/18 章法语正文成品）+ `bible/`（14 md：canonical bible——7 角色+3 地点+模板）+ `.claude/`（14：4 skills+6 agents）+ timeline 2 + 其他 9。**191 md 的大头是"一个跑完的实例"的产物，不是文档**。
**24MB 体积谜底**：工作区（不含 .git）实测 14M——大头 `ebook/` 12M（`assets/images/OLD/cover.png` 5.7M 单文件+`build/` 4.1M 含成品 epub/azw3 电子书 2.1M+2.0M）+ `state/` 804K + `analysis/` 368K；其余约 10M 在 .git 二进制历史。**无隐藏大代码，体积=电子书资产与构建产物**。

**架构**：Claude Code 多代理小说写作框架（README.md:1-40）：
- **双技能管"正典构建"**：`book-analyzer`（源书→结构化 bible 抽取）+ `bible-merger`（多书分析→合并 canonical bible）——**与 CBB 抽取入库作业同名的两个核心件**；另有 story-ideator（从 bible 生成原创剧情）+ perplexity-improver（去 AI 味）。
- **六代理管"写作流水线"**：chapter-planner/chapter-writer/character-reviewer/continuity-reviewer/state-updater/style-linter（.claude/agents/）。
- **永久/瞬态双层**：`bible/`=**PERMANENT**（"read-only, never modify during writing"，CLAUDE.md Files 节）；`state/`=**TRANSIENT**（每章版本化：state/chapter-NN/ 归档 + `state/current` symlink 指最新）。

**端到端数据流**（CLAUDE.md Workflow 13 步）：读 state/current/situation.md → planner 出章计划 → writer 写稿（注入 bible/style+相关 characters+state/current/*）→ perplexity-improver 去 AI 味 → **六道 gate**（style-linter/character-reviewer/continuity-reviewer 等）→ 任一 gate 失败则带报告回 writer 循环（**max 3 iterations**，CLAUDE.md:24）→ state-updater 建新章状态目录+更新 symlink → timeline/current-chapter.md **append 进 history.md 后清空**（章切换时）→ 正文入 story/chapters/。

## §2 数据模型与接口

**book-analyzer 输出模型**（.claude/skills/book-analyzer/SKILL.md）：`analysis/output/[book]/{style.md, structure.md, characters/[name].md, universe/[name].md}` 四件套。抽取五维清单：style（POV/主次时态/抽样 50 句平均长度/20-30 特征词汇/对话标签/对话占比）、characters（3-5 核心特质**各带证据**+5-10 对话引用）、structure（四幕/章节模式）、universe（地点引用）。**Evidence-Based Extraction 强制条款**："Every trait, pattern, or rule must be supported by: Direct quotes (with chapter reference) / Quantitative data"——附 Bad/Good 对照例（"Claude is stubborn" ✗ → "stubborn (Ch.2: refuses...; Ch.5: insists...)" ✓）。输出语言分层：内容法语+元数据英语。

**bible-merger 合并模型**（.claude/skills/bible-merger/SKILL.md）：
- style 合并四动作：**Keep**（ALL 书都出现的模式→规则）/**Range**（有波动的指标用 min-max）/**Flag**（单书特有词汇，记录不强制）/**Pick**（各书最佳引用）；
- characters 合并：**核心特质只在全部出场中都展示才保留**+演化记录（Evolution）+语音常量；
- **冲突解决表**：Style patterns→最常见优先；Character traits→**show 优先于 tell**；Facts→**后书优先（later books take precedence）**；All conflicts→**文档化并陈**（"Sources vary: book-1 says X, book-3 says Y"）；
- 产出 `analysis/merge-report.md`：一致性分析（高度一致/有变化/单书特有）+角色覆盖率（appears in X/Y books）+冲突解决清单。

**state 四文件模型**（state/template/）：`knowledge.md`（**Known to all / Known to specific characters / Unknown (dramatic irony——读者先知角色后知) / Clues found** 四节）、`situation.md`（Time/Location/Weather/**Tension level 1-10**+Open hooks 开环）、`characters.md`（每角色 Location/Emotional state/Current goal/Active conflicts）、`inventory.md`（随身物品/重要物品/Lost or destroyed/**Hidden——存在但未被发现**）。

**timeline 双文件**：`history.md`（**append-only**，注释明示"Append-only: add new entries after each chapter"；条目按"Chapitre 1 → **Jour 1 - Après-midi**"绝对日+时段组织，含"date précise inconnue"的诚实标注）+ `current-chapter.md`（当前章事件，章末归档进 history 后清空）。

**两脚本接口**（scripts/）：`detection.py`（1199 行）=**AI Slope 诊断器**——本地跑 Qwen3 8B/Mistral 算 perplexity，检测低困惑度块（"Low PPL = well-trodden path"）/相邻低块/低方差窗口，docstring 明示"This is NOT an 'AI vs Human' detector...Use this as a DIAGNOSTIC tool, not a judgment"（detection.py:2-17）；`style_checker.py`（787 行）=把 bible/style.md 规则自动化（字数 2800-3200/句均 12-20/句长上限 35 等 Constants 区），报告落 .work/ 供 style-linter 代理用。

**bible 条目样例**（bible/characters/claude.md）：Identity/Appearance 各字段+**Evidence 区块**（法语原文引用「Claude avait des cheveux courts...」）——字段与证据分离排版。

## §3 可借鉴 / 不可借鉴清单

**可借鉴（MIT；零代码复制，学设计）**：
1. **Evidence-Based Extraction 条款+Bad/Good 例句**——CBB 证据四元组的英文先例；"trait 必须带章节引用或量化数据"可直接写进 cbb-extract 的 SKILL.md。
2. **bible-merger 冲突解决表**——最接近 CBB 跨源合并裁决的现成规则集：事实后书优先+show 优先+全部冲突并陈文档化。"Sources vary: X says A, Y says B" 句式≈我们的并陈纪律。
3. **Keep/Range/Flag/Pick 四动作合并词汇**——多源模式合并的类型学（全现→规则/波动→区间/单源→标记）。
4. **bible PERMANENT / state TRANSIENT 双层**——正典不可变+状态可变的分层与 CBB canonical 库/工作区分离同构；symlink current+章目录归档=低成本版本化。
5. **六道 gate+max 3 iterations 循环**——每道审校是独立代理+失败带报告回写+迭代上限（防无限循环）——CBB gate 链设计参照。
6. **knowledge.md 四节模型**——尤其 **dramatic irony 节**（读者知道而角色不知道）：这是信息不对称的第三维度，CBB knowledge states 可补此维度（迷深 RP 场景直接可用）。
7. **inventory.md 的 Hidden 节**（存在但未发现的物品）——伏笔实体的一种受控状态。
8. **timeline append-only+绝对日锚点+时段+未知日期诚实标注**（"date précise inconnue"）。
9. **merge-report 的角色覆盖率**（appears in X/Y books）——多源实体覆盖度的量化表达。
10. **detection.py 的"诊断非判决"自我定位**——与 LLM-judge 使用纪律（分数只作内部比较）同精神。

**不可借鉴**：
1. 抽取/合并全靠 LLM 单遍判断，**无金标对账、无精度验证**（18 本书分析的质量无从证伪）——Step 0 方法论缺口原样存在。
2. 无三态/quarantine：冲突并陈了但无隔离态与终裁记录；"后书优先"是硬规则无申诉通道（若后书系续作者代笔则劣化——仓未考虑此风险）。
3. state 四文件是自由文本无 schema 校验；symlink 方案在 Windows/克隆环境下失效（本地 state/current 即断链）——CBB 用显式路径+校验器更稳。
4. 框架面向**法语/英语写作**，中文场景未验证；输出语言分层（内容法/元数据英）对 CBB 的启示是"内容语言与账本语言分离"，但其双语约定本身不可移植。

## §4 许可与红旗

- **MIT 正式 LICENSE**（LICENSE:1-3，Copyright (c) 2025 Thomas HOUSSIN）——索引判定属实，无传染。
- 维护状态：shallow 可见 1 merge 提交（PR #2 翻译 agents 为英语）；含 COMPLETION_REPORT.md（完工报告）——个人项目一次性完工形态，迭代平缓。
- 硬编码/密钥：detection.py 依赖本地 transformers 模型（Qwen3 8B/Mistral3），无云 API 调用、无 key；ebook build 用本地 PowerShell 脚本。无可疑内容。
- 红旗：无。**本仓是 16 仓中与 CBB 概念同源度最高的干净仓**（canonical bible 同名同题）。

## §5 与 CBB 对照（Step 0 三条件 + 四契约/三态）

**三条件对照**：
1. **元文本防御：无**。book-analyzer 抽取时无旁白/叙述层过滤；Evidence 条款保证"有证据"但不保证"证据非元文本"——R6 仍独有。
2. **时间归一：写作侧强、抽取侧无**。timeline 绝对日锚点（Jour 1+时段）+situation.md Time 字段+history append-only——领域纪律与 chinese-webnovel 同级；但 book-analyzer 抽取五维中**无时间轴抽取项**（源书的时间结构不被抽取）——CBB cbb-anchor 的抽取侧空白在此仓同样存在。
3. **去重：跨书实体合并=同族操作**。bible-merger 按角色名+LLM 判断合并多书实体（核心特质取交集+演化记录）——**无别名归一、无嵌入、无事件级去重**，但"特质交集保留+演化另记"是 CBB 实体合并（supersedes 前的 consolidation）可直接参照的语义规则。

**四契约/三态对照**：
- **Record ≈ bible 条目**（字段+Evidence 引用块，溯源到章节）；
- **Issue ≈ merge 冲突登记**（"Sources vary"并陈）；
- **Verdict ≈ 冲突解决规则表**（事实后书优先/show 优先/最常见优先）——**有裁决规则但无裁决文书**（选了哪条、为何、何时选的不可追溯，只在 merge-report 留一次性清单）；
- **Case ≈ merge-report**（含覆盖率与一致性分析）；
- **三态：无系统三态**——bible 条目无 confirmed/quarantined 语义；Flag（单书特有）≈弱化的"单源待证"态，是最接近 quarantined 的概念；
- **状态演进**：state/chapter-NN 版本化归档+symlink current≈CBB 快照断点；timeline history append-only≈我们的轨迹纪律。

**金标方法学（§K2）**：无评测件；detection.py 的 perplexity 是风格诊断不是抽取精度——不适用。

## §6 处置建议

**四选一：借鉴设计（只学思路）**——理由：
1. **本仓与 CBB 同题同构度第一**（analyzer/merger/bible/state/timeline 五件全对得上 CBB extract/merge/canonical/快照/轨迹），设计层吸收密度最高；但其实现全为提示词+自由文本，无机器校验层（R-020 反面），无运行时件值得装。
2. MIT 干净+概念同源，借鉴设计零风险零成本。
3. 其缺口（无金标/无三态/裁决不可追溯/抽取无时间轴）恰好逐项对上 CBB 四契约+Step 0 三条件的差异化存在价值——**"它证明了这条流水线能跑通，CBB 证明它能被验证"**。

移交 U-A17 吸收项：①Evidence-Based Extraction 条款句式（进 cbb-extract）②冲突解决表（后书优先/show优先/并陈句式）③Keep/Range/Flag/Pick 合并词汇 ④PERMANENT/TRANSIENT 双层+章目录版本化 ⑤六 gate+3 迭代上限 ⑥knowledge 四节（dramatic irony 维度）⑦inventory Hidden 节 ⑧角色覆盖率（X/Y sources）表达 ⑨timeline 未知日期诚实标注。
