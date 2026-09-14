# author-toolkit (rhavekost) 详报 · U-A02

> 分析日期：2026-09-15 ｜ 构建线产出，判定权在审核线
> 源码位置：`现成技能侦察/源码/author-toolkit/`（clone --depth 1，可见提交 b782870 "docs: drop private-path mention..."）
> 方法：主线直读（79 文件小仓，6 技能全结构+关键正文精读）

## §1 架构与数据流

**【三谜错位注明】本仓 0 个 js/ts 文件（`find . -name "*.js" -o -name "*.ts"` 为空；72 md + 3 json + 2 LICENSE + ATTRIBUTION + .claude-plugin 双 json）。STATE/总纲所挂"5.8 万行 js 用途"谜实体在 agent-skills (jwynia)，谜底见 U-A01 报告 §1（150 .ts/58,386 行 Deno CLI 脚本）；错位登记于 Issue 001。本仓真实形态=纯提示词 Claude Code 插件。**

**仓库形态**：Claude Code plugin（`.claude-plugin/plugin.json` v1.3.1 + `marketplace.json`），作者 rhavekost（rob@kostlabs.com），6 技能：
- `fiction-workshop`——三阶段编辑工作流（Story Bible Building → Chapter Development → Reader Testing），五编辑人格（Developmental/Line/Character/Continuity Tracker/Brainstorm），SKILL.md:9-11；
- `character-archetypes`——双分类法（Vogler/Campbell 8 叙事角色 + Jungian 12 人格）×四模式（Analyzer/Audit/Conformance/Ensemble）（README.md:31-43）；
- `story-structure`——百分比锚定宏观结构（Weiland 11 landmark beats + Bell 14 signposts）+Map/Audit 双向（README.md:45-52）；
- `prose-mechanics`——19 审计 pass（见 §2）；
- `narrative-nonfiction`——叙事非虚构对应件（reveal engineering 八法）;
- `avoid-ai-writing`——**vendored 第三方技能**（作者 Conor Bronsdon，上游 commit b38ee9f8 原样保全，ATTRIBUTION.md:8-19）。

**端到端数据流**：会话开工读持久状态（fiction-workshop 读 `story-bible.md` + 扫 `sessions/` 未决线索，SKILL.md:13-17；prose-mechanics 读 `audit-tracker.md`，SKILL.md:11-15）→ 人格/审计按需加载单个 reference 文件（"Do not preload all references—it wastes context budget"，fiction-workshop SKILL.md:66-68）→ 产出 findings（finding-schema.json 统一格式）→ 会话末写 `sessions/YYYY-MM-DD_topic-slug.md` 断点笔记（2-5 句，SKILL.md:15-16）→ 基础设定变更时立即更新 bible（"The Story Bible is the source of truth, not a one-time template"，SKILL.md:17-18）。

## §2 数据模型与接口

**finding-schema.json（全仓唯一机器契约，JSON Schema draft 2020-12）**：required = audit/technique/severity/location/issue/confidence（references/finding-schema.json:4-6）：
- severity 枚举 note/suggestion/warning（:9）；
- location 必含 file/line/quote 三字段（:10-19）——**每条发现带原文引用**；
- confidence 枚举 **deterministic/judgment**（:26）——确定性判定与主观判断显式分口径。

**prose-mechanics 19 审计三分类**（SKILL.md:55-75 表）：deterministic（sentence-variance/readability/echoes/frequency/crutch-words/filter-words/adverb/sticky/starters/invented-term 共 10）/ hybrid（active-passive/dialogue-tags/tense/clichés/ai-isms 共 5）/ semantic（parallel-structure/pronoun-clarity/show-vs-tell/pov 共 4）。审计**有序执行**：frequency 族先行（其结果配置 crutch-words）、mechanical 先于 semantic（"judgment-expensive; don't run on prose about to be reworked"，SKILL.md:50-53）。

**引擎钩子**（SKILL.md:87-101 "Engine Hook"）：先探 `command -v scriptorium`——deterministic 审计跑 `scriptorium prose audit` 且"treat its JSON as authoritative — do not re-derive findings by hand"；hybrid/semantic 用 `prepare` 取候选/原文再人工判；无引擎则对话式执行且"This is the audit's full specification, not an abbreviated fallback"。**外部确定性引擎存在时权威化、缺失时降级不缩水**的双模设计。

**story-bible-template.md 数据模型**（assets/story-bible-template.md 章节结构）：Quick Reference/Premise & Theme/Plot Foundation/**Character Registry**（want-need-wound-arc 四件套，:73-97）/World Details/**Timeline**（:152）/**Object/MacGuffin Tracking**（:173）/**Knowledge States**（:181）/Research Notes（**Verified Facts 与 Questions to Research 分节**，:162-167）。

**exemplar 机制**：findings 可带 exemplar 引用，渲染时解析到 `references/exemplars/<ref>.md`（SKILL.md:80-85），12 个改动前后样例对（deep-pov/filter-removal-01 等）。

**avoid-ai-writing 双模式**：rewrite（默认）vs detect（只标记不改写，适用已发布/他人文本/有意为之的 AI 味，SKILL.md:16-24）。

## §3 可借鉴 / 不可借鉴清单

**可借鉴（MIT，无许可障碍；仍按"只读不抄"零代码复制）**：
1. **finding-schema 的 confidence 双口径**（deterministic/judgment）——与 R-010 证据语气三分离同构，CBB 的 Issue/Verdict 契约可引入此字段：哪条结论来自确定性校验器、哪条来自 LLM 判断，机器可辨。
2. **location(file/line/quote) 三元组**——与总纲 §R"断言带文件:行号"判据同构，quote 字段（原文引用）值得纳入 CBB Record 溯源。
3. **审计三分类+引擎权威化**——deterministic/hybrid/semantic 分类法与"外部确定性引擎在则权威、缺则全量降级"设计，直接映射 CBB 的 stdlib 校验器+LLM 抽取分工。
4. **审计顺序依赖声明**（frequency→crutch-words 配置链、mechanical→semantic）——CBB 管道（extract→gate→quarantine→store）的顺序理由应同样显式写明。
5. **Session Continuity 双例**（bible+audit-tracker 都是持久状态、会话末断点笔记）——与 BUILD-STATE+轨迹同构，其"2-5 句够用"的低成本断点值得学。
6. **bible 模板的 Knowledge States/Verified Facts vs Questions 分节**——前者≈confirmed 记录、后者≈【待确认】，模板层即可落地三态语义。
7. **vendoring 纪律**（ATTRIBUTION.md 记录上游 commit+LICENSE 原样保全+"No changes have been made"声明）——CBB 若引用外部技能正文可照此办理。

**不可借鉴**：
1. findings 无状态流转（flag 之后无 resolved/quarantined 终态跟踪，audit-tracker 只记"跑过什么"不记"每条发现的处置结果"）——CBB 三态写入必须超出此设计。
2. 无任何抽取/入库机制（它是编辑工具不是知识库工具），数据模型止于 md 模板+单 json schema。
3. 五人格切换靠口头 invocation（"As developmental editor..."），无机器可验的角色边界。

## §4 许可与红旗

- **仓级 LICENSE = MIT**（LICENSE:1-3，Copyright (c) 2026 rhavekost）；plugin.json:11 同声明。索引清单"MIT"判定属实。
- avoid-ai-writing 为 vendored 技能：上游 MIT，ATTRIBUTION.md:8-19 完整记录来源/commit/许可保全——**vendoring 合规范例**，无红旗。
- 硬编码/密钥：全仓无代码无 API 外呼，无可疑内容。`compatibility` 字段声明"No external tools or APIs required"（avoid-ai-writing SKILL.md:8）。
- 维护状态：shallow 单提交（b782870，docs 类提交），v1.3.1 有版本纪律（avoid-ai-writing CHANGELOG.md 在案）；个人仓，长期维护无保证。
- 注：ATTRIBUTION.md:13 上游 URL 写 `github.com/coneorbronsdon/avoid-ai-writing`（作者名 Conor Bronsdon）——引用时照抄勿改。

## §5 与 CBB 对照（Step 0 三条件 + 四契约/三态）

**三条件对照**：
1. **元文本防御：无**。本仓不抽取设定，无元文本问题域；avoid-ai-writing 处理的是"AI 味"（em-dash 滥用/"delve"类词汇）非作者旁白。不适用。
2. **时间归一：有意识、无机制**。continuity-tracking.md Timeline Continuity 五项（day/date 追踪/角色年龄/事件时长/"Meanwhile"多线协调/**"Historical references matching the setting's year"**，references/continuity-tracking.md:18-24）——最后一项是"防现实历史锚点混入故事年"的红线意识，与 reference_time 污染（Step 0 Tier 2 教训）同题；红旗模式"Time passing faster or slower than physical travel allows"（:48）。但只有人工审查清单，无归一化算法、无禁墙钟规则。
3. **去重：无**。echoes audit 是**文风**重复（100 词内词重复，SKILL.md:61）非实体/事件去重；knowledge states 追踪靠人工维护。

**四契约/三态对照**：
- **finding-schema ≈ Issue 契约的精简版**：有 severity（≈优先级）/location+quote（≈溯源）/confidence（≈证据语气）；缺状态机与处置闭环。
- **Verified Facts ≈ Record（confirmed 子集）**；Knowledge States 章节（who knows what when）是 CBB 实体状态字段（state）的人工模板对应物。
- **无 Verdict/Case 对应物**；无三态写入——findings 单向输出，处置留在人侧。
- **continuity 修复策略 ≈ supersedes 思想**："Note which is earlier (thus 'established')"（先确立者为正典，continuity-tracking.md Feedback Format 节）+ Major Fixes 四步（document both→identify→trace dependencies→fix comprehensively，:90-96）+ Retcon 三步（改早期引用→更新 bible→查下游，:98-102）——与 CBB supersedes 版本化+依赖回扫同构，但其实现是人工流程非机器账本。

## §6 处置建议

**四选一：借鉴设计（只学思路）**——理由：
1. 全仓最有价值的三件（confidence 双口径、审计三分类+引擎权威化、bible 模板三态语义分节）都是 schema/流程设计，吸收进 CBB 契约与模板即可，无运行时依赖价值（纯提示词，无可装外挂件）。
2. MIT 无许可障碍，但"只读不抄"总纪律维持。
3. 与 CBB 关系是"编辑侧同题友军"（连续性审查），其人工流程反衬 CBB 机器账本（R-020）的必要性。

移交 U-A17 吸收项：①Issue/Verdict 契约增 confidence(deterministic/judgment) 字段提案 ②Record 溯源增 quote 原文引用字段提案 ③bible 模板 Knowledge States/Verified Facts 分节式 ④vendoring ATTRIBUTION 纪律 ⑤审计顺序依赖的显式声明式写法。
