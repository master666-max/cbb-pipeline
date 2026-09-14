# agent-skills (jwynia) 详报 · U-A01

> 分析日期：2026-09-15 ｜ 构建线产出，判定权在审核线
> 源码位置：`现成技能侦察/源码/agent-skills/`（clone --depth 1 快照，唯一可见提交 e02ec7e 2026-02-24 "Brave search"）
> 方法：两轮前台子代理侦察（结构层+对照层）+ 主线逐条抽验行号（R-016 纪律：抽验 12 处关键断言全部命中）

## §1 架构与数据流

**仓库形态**：单作者（jwynia，Narratome/storylib 作者）的 Agent Skills 集合仓，**技能资产 + 规划中枢**双体结构：
- `skills/`：6 分类树（creative/development/education/general/research/tech）+ README.md，实际 119 个 SKILL.md（creative 57 = fiction 54 + humor 1 + music 2；tech 28；general 32；development 1；education 1；research 0 仅剩 references 碎片）。fiction 七维切分属实：application(14)/character(6)/core(5)/craft(5)/orchestrators(1)/structure(12)/worldbuilding(11)（`ls skills/creative/fiction/` 实测）。
- `context-network/`：**本仓自己的规划/决策中枢运行实例**（不是模板），foundation/elements/connections/decisions/meta/archive 等层级；根指针 `.context-network.md:5` 规定新会话先读 `context-network/meta/session-bootstrap.md`，且"ALL planning documents MUST be stored within the context network"（`.context-network.md:7` 起 Location 节）。
- `.claude/commands/`：15 件斜杠命令（plan/research/implement/refactor/audit/review-code/review-tests/groom/maintenance/retrospective/discovery/checklist/daily-review/quick-sequences/README），与 context-network 联动（`research.md:12`："research outputs MUST be placed in the context network, NOT in the project root"）。
- `deno.json`：全仓工具链入口——`check/lint/fmt/test` 四任务全部指向 `skills/`（deno.json tasks 节），strict + explicit-function-return-type（deno.json lint 节）。

**端到端数据流**（两条）：
1. 消费侧：`npx skills add <tree-url>`（README.md:15-35）→ 技能（SKILL.md + scripts/ + references/）进用户技能目录 → 运行时由 agent 加载 SKILL.md，脚本按需前台执行。
2. 维护侧：会话开工读 `.context-network.md` → session-bootstrap.md（目录结构+关键决策表，session-bootstrap.md:38-42 列 organization-structure/deno-runtime-requirement/naming-strategy 三 ADR）→ discovery.md 层级导航 → 工作产出回流 context-network（research/discovery 文档化）。

**【三谜之一谜底】"5.8 万行 js"实为 TypeScript，用途 = 技能自带 Deno CLI 脚本资产**：
- 实测 150 个 `.ts` 共 58,386 行，`.js` 文件数为 **0**（`find . -name "*.js"` 空；task-036 表列"JS/TS"被总纲转写为"js"，属口径转写失真）。149 个在 skills/ 下，1 个是 `context-network/meta/templates/deno-script-template.ts`（111 行模板）。
- 分布头部（wc -l 聚合）：frontend-design 4514 行（7 脚本：generate-component 876/analyze-accessibility 669/…）、ebook-analysis 4469（13 脚本）、reverse-outliner 2675、github-agile 2628（gh-audit 850/gh-sync-context 773/…）、pptx-generator 2163、pwa-development 2086、typescript-best-practices 1974、godot-asset-generator 1943、adaptation-synthesis 1798、dna-extraction 1644、world-fates 1576、skill-builder 1474（validate-skill.ts 932）。单文件最大 `skills/tech/development/tooling/typescript-best-practices/scripts/scaffold-module.ts` 1013 行。
- 性质：全是**确定性 CLI 工具**（生成/校验/统计），非运行时库。抽读 dna-extraction `extract-functions.ts`（790 行）：纯 Deno CLI，生成问卷/空白模板/校验 JSON 完整性（:3-15, :563-626），grep api|fetch|http|model 无命中——"LLM 出判断、脚本出结构"分工。godot-asset-generator 是唯一外呼型：SKILL.md:5-6 声明 MIT + Deno runtime + 环境变量传 key（OPENAI_API_KEY/REPLICATE_API_TOKEN/FAL_KEY），generate-image.ts:1 shebang `#!/usr/bin/env -S deno run --allow-env --allow-net --allow-write`，封装 DALL-E/Replicate/fal.ai 三家图像 API。

## §2 数据模型与接口

**SKILL.md frontmatter schema**（机器校验，`skills/general/meta/skill-builder/scripts/validate-skill.ts`）：
- 必填 name/description/license + metadata.author/version/domain + 新必填 type/mode 及枚举（validate-skill.ts:44-50；VALID_TYPES=diagnostic/generator/utility，VALID_MODES=diagnostic/assistive/collaborative/evaluative/application/generative）。
- 正文按类型必选节（diagnostic 型需 States/Diagnostic Process/What You Do NOT Do 等，:71-86）；状态数≥3（:453-464）；状态命名前缀一致（:197-227, :497-510）；反模式≥3/2（:513-525）；integration 型须有 inbound 或 outbound（:527-545）；scripts 须在 SKILL.md 有文档（:598-609）；70% 加权分及格（:692-694）——24 分成熟度模型（Completeness11+Quality5+Usability4+Execution4，skill-builder SKILL.md:180-231）。

**对外接口**：`npx skills add` 装机（README.md:15-35）；`scripts/install-skills.sh`（1273 字节）本地安装。对 LLM 的接口即 SKILL.md 本身（提示词工程文档）。

**仓内三个数据模型**：
1. shared-world 正典条目：五态标记 + Sources 溯源（见 §5）。
2. DNA 文档 schema：六轴提取（Form/Structural/Character/Emotional/Thematic/Relational，dna-extraction SKILL.md:99-110）+ structural_necessity: high/medium/low 逐角色标注（:285-358 schema 节）；dna-library 三层 `{extractions,clusters,syntheses}` 链接网络（:289-298）。
3. Synthesis Document schema：function_to_form_mapping 每映射带 orthogonality_check（adaptation-synthesis SKILL.md:190-248）。

**context-network 文档网模型**：原子化"One concept = one file ... 100-300 lines maximum"（AGENTS.md:246-249）；connections/dependencies.md 与 interfaces.md 显式登记技能间依赖。

## §3 可借鉴 / 不可借鉴清单

**可借鉴（设计层，MIT 已声明无许可障碍）**：
1. **技能结构校验器**（validate-skill.ts 932 行）：frontmatter 必填+枚举+按类型必选节+状态数下限+70% 加权及格——CBB 技能族的 lint 件可直接学此设计（我们已有四契约 stdlib 校验器，可补"状态数≥3/命名前缀一致"这类结构规则）。
2. **状态机前缀化**：全仓技能用 SA1-SA8/CA1-CA8/EX0-EX7/F1-F5/SYN0-SYN7/CN0-CN6 统一编码状态（story-analysis:28-322、dna-extraction:26-97 等）——对 CBB 写 SKILL.md 的状态描述是好范式。
3. **shared-world 五态正典+Sources 溯源**（详见 §5）——设计思路级借鉴首选。
4. **fact-check"生成与验证分 pass"原则**（fact-check SKILL.md:18-31："生成与验证必须分离 pass，自证无效"）——支撑 CBB quarantined 隔离语义。
5. **context-network"规划文档全部入网+根目录禁放"纪律**（.context-network.md:7 起）——与 CBB"账本必须机器可读"（R-020）同向。
6. **dna-extraction 的"结构必然 vs 风格选择"判据**（"改动后故事是否崩坏"，:63-70, :274-283）——可服务 CBB 改编级深加工的要素分类。

**不可借鉴**：
1. 文档计数失修（README 自称 112、树图 57/25/28、清单 ~57/~26/~29、skills/README 114，磁盘真实 119——四处口径不一）——提醒 CBB：清单类文书必须机器生成（我们 lint_knowledge_base 同理）。
2. 文档引用失修：session-bootstrap.md:28/66 引用 `reference/agentskills/skills-ref/` 但目录不存在；commands/README.md:30,33 宣传 /status /sync 但无此文件——个人仓"文档先行、快照陈旧"通病。
3. 技能粒度无运行时耦合校验（各技能独立，无跨技能契约测试）——与 CBB 四契约跨技能咬合相反，勿学。

**代码级借鉴判定**：117/119 技能 frontmatter 声明 MIT（仅 npm-package/npx-cli 未标注，`grep -L "^license:"` 实测），借鉴设计无传染风险；但按 CBB"只读不抄"总纪律（模板 C 节），本仓同样**零代码复制**，validate-skill.ts 只读作设计参考。

## §4 许可与红旗

- **仓根无 LICENSE 文件**（`find -maxdepth 2 -iname "LICENSE*"` 为空；README/AGENTS/.gitmodules grep license/MIT/Apache/copyright 零命中）——索引清单"未标注许可"判定在仓级属实。
- **技能级**：118 行 `license: MIT` 分布于 117 个 SKILL.md（`grep -h "^license:" | sort | uniq -c`），例 godot-asset-generator SKILL.md:5。**两件未标注**：skills/tech/development/tooling/npm-package/SKILL.md、npx-cli/SKILL.md——若引用这两件需注意。
- **AGENTS.md 与 CLAUDE.md 逐字节相同**（diff 仅标题行 1c1），核心是"Slow Down to Go Fast"（AGENTS.md:3-7）、决策暂停点（:83-91）、Friction Rule（:131-137）、5 分钟无进展即停（:161-165）。
- 硬编码/密钥：godot 技能 key 全走环境变量（SKILL.md:6）✓；其余 ts 脚本无 API 外呼。无可疑代码。
- 维护状态：shallow clone 只见 1 提交（2026-02-24），作者仅 jwynia；inbox/ 已空（剩 .DS_Store）、processes/ 残留 *.bak——**个人仓，活跃度与长期维护无保证**。
- submodule `collections/awesome-claude-skills`（.gitmodules）本地未初始化，collections/ 不存在——若需该子仓须另 clone。

## §5 与 CBB 对照（Step 0 三条件 + 四契约/三态）

**三条件对照**（子代理 grep -rniE 全 skills/ 扫描，主线认可其检索式）：
1. **元文本防御：无**。关键词 narrator|metatext|paratext|author's note|authorial|fourth wall|aside 命中均为写作技法（prose-style 的叙事者声音 :173,190；dialogue "Emotional Narrator" 标签 :205），无任何技能处理"作者旁白混入抽取数据"。最接近的是 shared-world "document what exists"（SKILL.md:510，不投机建档）——**R6 元文本防御仍是 CBB 独有配置**。
2. **时间归一：部分、无机制化**。shared-world 有 in-world calendar 字段（SKILL.md:44-45, :392；init-world.ts:178-193）；flash-fiction 做时间线矛盾检查（:300-313）；world-fates 评估触发含 Time skip=故事内时间跳跃（SKILL.md:231-232）。但**无时间戳归一化、无禁现实钟**；chapter-drafter 进度日志反而用现实 [timestamp]（SKILL.md:238, 251）——反面印证 cbb-anchor 伪锚点禁墙钟的必要性。
3. **去重：弱存在**。shared-world check-conflicts.ts 仅精确同名检测（:9, :108-114，无别名合并）；claim-investigation Phase 2 实体消歧（:59-76）最接近跨源去重；endings/setup-payoff.ts 按文本相似度去重（:198-204）；reverse-outliner 跨章人物仅按名字频次≥5（track-characters.ts:296-297）。**无跨章事件级去重**——CBB 去重条件（Qwen3-Embedding 4096 维）无现成件可抄，维持自研。

**四契约/三态对照（全仓最同构机制：shared-world 正典状态系统）**：
- 五态 Established✓/Proposed?/Deprecated✗/Contradicted⚠/Speculative~（shared-world SKILL.md:92-96），规则"Established 不可被直接矛盾，须先弃用"（:100-104）——比 CBB 三态（confirmed/quarantined/rejected）多出 Speculative（外推）与 Deprecated（版本化终态）两义，其中 **Deprecated≈CBB store 的 supersedes 版本化**、Contradicted≈quarantined 的"待裁决"细分。可考虑：CBB 是否需要在 quarantined 内细分"矛盾待裁决"与"外推待证"。
- 每条 canon 记录 Sources（章节/页码/日期，SKILL.md:111 起 Sources 节）≈ Record 的溯源字段。
- 四角色权限 Reader/Writer/Editor/Canon Authority + Propose→Review→Integrate→Track 流（:194-210）≈ CBB 构建线/审核线分工。
- 写入两态落地：world-fates "先建 Proposed? 条目，人批准后转 Established✓"（:382-386）——与 CBB"无权自宣验收"同构。
- **fact-check ≈ Issue+Verdict 对**：claim 分解→验证→五态结论 Confirmed/Partially supported/Not found/Contradicted/Outdated（fact-check SKILL.md:109-117）+ 置信四档 High/Medium/Low/Unreliable（:121-128）。
- **claim-investigation ≈ 抽取侧方法学**：六类分类 ENTITY/EVENT/STATE/PROCESS/CAUSATION/NARRATIVE（:42-49）可对照 CBB 实体/事件抽取的类型学；实体消歧（:59-76）；五级 Certain/Probable/Possible/Unclear/False（:190-198）；"逐组件判真伪，不许一错全否"（:361-363）≈ CBB 事实级裁决粒度。

**金标方法学套用（§K2）**：本仓无任何带定量评测的组件（validate-skill 是结构校验非语义评测），无精度宣称可收编——不适用。

## §6 处置建议

**四选一：借鉴设计（只学思路）**——理由：
1. 本仓是提示词工程+确定性 CLI 的方法论矿，与 CBB 的契约/三态/断点架构不同层；最有价值的四件（五态正典/分 pass 验证/技能校验器/状态机前缀化）全部是设计层资产，吸收思路即可，无需进运行时。
2. 已装机外挂两件（evals-skills+neo4j-skills）不含本仓；本仓技能非 CBB 运行时依赖，装外挂无必要。
3. 个人仓+文档失修+shallow 单提交，长期可用性弱，不宜成为运行时依赖。
4. 许可面安全（117/119 MIT），设计借鉴无传染；维持"只读不抄"零代码复制。

具体吸收项移交 U-A17 汇总：①quarantined 细分提案（矛盾待裁决/外推待证）②技能结构 lint 规则补强（状态数≥3/命名前缀一致）③SKILL.md 状态机前缀化写法 ④shared-world Sources 溯源字段式。

## 附：对账勘误（移交审核线）

1. **三谜归属错位**：STATE U-A02/总纲 §W 把"5.8 万行 js 用途"谜挂 author-toolkit（task-036 实测纯提示词 0 js），实际挂本仓（agent-skills/jwynia，150 ts/58,386 行）。谜底已在本报告 §1 给出（TypeScript、技能自带 Deno CLI 脚本）。详见 `issues/001-三谜归属错位-agent-skills-vs-author-toolkit.md`。
2. task-036 表列"JS/TS"转写失真：本仓 js=0、ts=150 文件——后续各仓报告将统一按扩展名分列。
