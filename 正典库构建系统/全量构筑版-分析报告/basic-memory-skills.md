# basic-memory-skills 详报 · U-A03

> 分析日期：2026-09-15 ｜ 构建线产出，判定权在审核线
> 源码位置：`现成技能侦察/源码/basic-memory-skills/`（clone --depth 1，可见提交 6d2b1d4 "fix: use uvx basic-memory for portable .mcp.json"）
> 方法：主线直读（35 文件小仓；10 技能 SKILL.md 全览 + 4 件精读）

## §1 架构与数据流

**仓库形态**：Basic Memory（basicmachines-co/basic-memory）MCP 服务的**官方配套技能仓**——纯提示词（2309 行 SKILL.md 合计，无代码），教 AI agent 用好 Basic Memory 的 MCP 工具（write_note/edit_note/search_notes/build_context 等，README.md:7-9）。

**三副本布局**：根目录 10 技能（含 memory-literary-analysis）+ `.agents/skills/` 9 技能副本（diff 实证与根同文件，无 literary-analysis）+ `.claude/skills/` 9 个符号链接（Windows clone 下为 34 字节失效链接文件，环境产物非设计）。`.mcp.json` 声明服务启动方式：`uvx basic-memory mcp`（.mcp.json:3-6）。

**十技能职能**（README.md:21-31 表）：memory-tasks（抗上下文压缩的任务追踪）/memory-schema（Picoschema 生命周期）/memory-reflect（睡眠时反思，引 Letta sleep-time compute）/memory-notes（笔记写法规范）/memory-metadata-search（frontmatter 结构化查询）/memory-defrag（碎片整理）/memory-lifecycle（实体生命周期）/memory-ingest（非结构化输入→实体）/memory-research（网络调研→实体）/memory-literary-analysis（**全书→知识图谱六阶段管道**，511 行，根布局独有）。

**端到端数据流**（literary-analysis 主管道，SKILL.md:19-26）：Phase 0 Setup（建项目+写 6 个 schema 笔记到 schema/）→ Phase 1 Seed（先建主要实体 stub 使 `[[wiki-link]]` 从开工即可解析，SKILL.md Phase 1 节）→ Phase 2 Process（按 ~10 章/批逐章处理：建章笔记+append 增富相关实体+Task 追踪进度）→ Phase 3 Cross-ref（角色弧/主题演化/章节对仗/分析综合笔记+新实体入图标准=出现于 3+ 章或有主题分量）→ Phase 4 Validate（schema_validate×6 类型+schema_diff 漂移检测+双向关系一致性抽查）→ Phase 5 Visualize（canvas 可视化）。

**sota-memory-radar 对照**（§W 线索要求）：`knowledge/references/sota-memory-radar.md` 七派（A 分层记忆OS/B 管线抽取/C 图联想检索/D 认知架构反思/E 生物启发遗忘/F 长上下文压缩/G 产品实践）**未收录 basic-memory**（grep 零命中，本报告补位登记）。定位：**C 派（图/联想检索）的本地 markdown 实现**——wiki-link 三元组（observations 语义分类+relations）即轻量知识图谱；memory-reflect 引入 **D 派思想**（sleep-time compute）；仓本身属 **G 派产品实践**（Basic Memory 商业云的官方配套，README.md:33-42 含推广码）。

## §2 数据模型与接口

**Picoschema**（memory-schema/SKILL.md:18-107）：YAML frontmatter 内联紧凑 schema 语法——`类型, 说明`（string/integer/number/boolean）、`?` 后缀可选、`(enum)` 枚举、数组、relations；**validation settings 可设 warn/strict**（literary-analysis 六 schema 全带 `"settings": {"validation": "warn"}`，Phase 0 节）。schema 笔记本身带 `version` 字段（Character schema 例 version:1）。

**笔记模型**（memory-notes + literary-analysis 实例）：frontmatter（tags/metadata）+ 正文 Observations（`- [category] 内容` 语义分类，如 `[arc]`/`[quote]`/`[foreshadowing]`）+ Relations（`- appears_in [[目标]]` wiki-link 有向边）。六实体 schema：Character（**status enum: alive/dead/unknown/transformed**+first_appearance，Phase 0 Character Schema 节）/Theme/Chapter（chapter_number+pov+narrative_mode enum）/Location（**real_or_fictional enum: real/fictional/both**）/Symbol/LiteraryDevice。

**对外接口**：MCP 工具调用（write_note/edit_note operation=append|prepend/schema_validate/schema_diff/canvas 等，全仓以 python 代码块示例形式给出调用契约）；装机走 `npx skills add`（README.md:47-58）。

**genre 适配矩阵**（literary-analysis Adapting 节）：Play 加 Act/Scene、Poetry 换 Poem（form/meter/rhyme_scheme）、Non-fiction 换 Section+Argument/Evidence、Epic 加 Deity/Prophecy、Memoir 加 relationship_to_narrator+Memory schema——schema 可扩展性的型谱。

## §3 可借鉴 / 不可借鉴清单

**可借鉴（设计层）**：
1. **六阶段"全书→图"管道骨架**（Setup→Seed→Process→Cross-ref→Validate→Visualize）——与 CBB 抽取入库管道（extract→gate→store）同题；其 **Seed 先行**（先建 stub 让 wiki-link 即时可解析，防悬空引用累积）是 CBB 实体首见登记的好前置。
2. **validation warn/strict 双档**——软校验（warn 记录不阻断）适合 CBB quarantine 侧、硬校验适合 gate 侧，一档二字段即可表达。
3. **Phase 4 三重校验**（schema_validate+schema_diff 漂移+双向关系一致性抽查"If Chapter X features [[Character]], does Character have observations referencing Chapter X? Fix gaps"）——双向边一致性是 CBB store 关系写入应补的校验维度。
4. **观察语义分类**（[arc]/[quote]/[foreshadowing]/[event] 等约 30 类目）——CBB Record 的 observation 分类词表素材。
5. **新实体入图门槛**（3+ 章出现或有主题分量）——防碎片实体的量化判据，CBB 实体去重/合并的同类设计。
6. **memory-lifecycle "archive, never delete"**（唯一删除例外=误建/真重复，SKILL.md:17-29）+ 文件夹即状态（active/archive/pipeline）——与 CBB append-only 铁律同构；其 Revert/Reactivate 边例处理（撤销误完成）值得参照。
7. **memory-defrag 审计底线**：保原始日记（"they're the audit trail"）+ 不确定时打 `(review needed)` 标签而非删（Guidelines 节）——≈【待确认】纪律；矛盾解决原则 "Resolve to ground truth"（Process 表 Inconsistencies 行）。
8. **主观解释显式标记**（"In my reading..."/"I find..." 且论点须带章节出处，literary-analysis Adding Prose 节）——R-010 证据语气三分离的英文版先例。
9. **"Read the source text. Don't rely on memory or summaries. Textual evidence is everything"**（Guidelines 节）——对账先行的文学版。

**不可借鉴**：
1. **无三态/裁决语义**：笔记无 quarantined 类中间态（schema validation warn 只是校验档位不是实体状态）；矛盾靠 defrag 周期性人工收敛，无逐条裁决记录——CBB Verdict 契约无对应物。
2. **无抽取精度防护**：整条管道假设 LLM 读章抽取即可信，无金标对账、无元文本防御——Step 0 教训未被此仓覆盖。
3. defrag 的删除口径（completed tasks >14 天可删）与 CBB 永不删除铁律冲突，只可借鉴其"先计划后执行+前后对照防丢信息"流程。
4. 商业推广嵌在技能 README（云服务+折扣码）——若整文引用需剥离。

## §4 许可与红旗

- **README.md 末节文字声明 "License: MIT"，但仓内无 LICENSE 正文文件**（find -iname "LICENSE*" 零命中）——索引清单"未标注"判定**部分失准**：有仓级文字声明、无正文文件。借鉴设计无风险；若需复制正文，建议以文字声明为准并留截图证据（保守口径）。【待确认：审核线是否认可 README 文字声明为有效许可表达】
- 维护状态：shallow 单提交（6d2b1d4，fix 类）；上游 basic-memory 产品活跃（README 提及云服务/多 agent 场景），技能仓本身迭代平缓。
- 硬编码/密钥：零代码零 API 外呼（`.mcp.json` env 为空对象）；无可疑内容。
- 无 GPL/AGPL 传染风险。

## §5 与 CBB 对照（Step 0 三条件 + 四契约/三态）

**三条件对照**：
1. **元文本防御：无**。逐章处理假设输入即正文；无 narrator/旁白/作者注过滤设计。CBB R6 仍独有。
2. **时间归一：无**。Chapter schema 只有 chapter_number 顺序字段（Phase 0 Chapter Schema 节），无故事内时间戳、无归一化、无墙钟禁令。**反面教材**：说明"章序号≠时间轴"的意识在同类工具中普遍缺失，cbb-anchor 的必要性再加证。
3. **去重：文件级有、实体级弱**。memory-defrag merge duplicates（文件级合并，Process 表 Duplicate info 行）；literary-analysis 靠"Seed 先行+新实体 3+ 章门槛+Phase 4 双向关系抽查"**预防**重复实体（治未病），但无别名归一、无嵌入相似度、无事件级去重——CBB Qwen3-Embedding 去重仍无现成件。

**四契约/三态对照**：
- **Record ≈ note（frontmatter+observations+relations）**，quote 带章节出处（"with chapter attribution"，Guidelines 节）≈ 溯源字段；
- **Issue/Verdict 无对应物**（矛盾解决内嵌在 defrag 流程，无逐条裁决文书）；
- **三态 ≈ 间接表达**：lifecycle 文件夹状态（active/pipeline/archive）≈ 实体生命周期；Character status enum（alive/dead/unknown）≈ 实体终态；`(review needed)` 标签 ≈ 待确认态——**状态语义散落三处未统一**，反衬 CBB 三态集中写入的设计优势；
- schema version + evolution 流程（memory-schema/SKILL.md:201-227）≈ 契约版本化。

**金标方法学（§K2）**：本仓无评测件、无精度宣称——不适用。

## §6 处置建议

**四选一：借鉴设计（只学思路）**——理由：
1. 最有价值件（literary-analysis 管道+Seed 先行+三重校验+lifecycle archive 纪律）全是流程/schema 设计，且依赖 Basic Memory MCP 运行时——CBB 不引入该运行时（已有 neo4j-skills 装机外挂覆盖图存储需求），故不装外挂。
2. 无代码可抄（纯提示词），MIT 文字声明下借鉴设计无障碍。
3. 它是"记忆架构技能"而非"正典构建技能"：缺三态/裁决/精度防护三件 CBB 核心件，是同题友军非竞品。

移交 U-A17 吸收项：①Seed 先行防悬空引用 ②validation warn/strict 双档 ③双向关系一致性校验 ④观察分类词表（~30 类）⑤新实体 3+ 章入图门槛 ⑥lifecycle archive-never-delete+Revert 边例 ⑦主观解释标记纪律。
