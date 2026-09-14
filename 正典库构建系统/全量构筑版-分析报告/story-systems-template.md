# story-systems-template (bybren-llc) 详报 · U-A14

> 分析日期：2026-09-15 ｜ 构建线产出，判定权在审核线
> 源码位置：`现成技能侦察/源码/story-systems-template/`（clone 快照，可见提交 4a9e30c Merge PR #61 2026-08-05）
> 方法：前台子代理深读 + 主线抽验 3 处关键断言（statuses 四态/map-card/verified_against——全中）

## §1 架构与数据流

**定位**：Words To Film By™ (WTFB) 多智能体创作 harness 模板（J. Scott Graham/Bybren LLC，MIT）——11 agents/24 skills/34 commands，Claude Code+Gemini CLI 双支持，**编剧（screenplay）向**。

**双镜像去重结论**（在案线索"要去重"的答案）：`.claude`（109 文件）与 `.gemini`（96 文件）**非逐字节镜像**——①skills 24×2 内容近乎全同（diff 仅 frontmatter `wtfbId` 行）；②`.gemini/agents` 是压缩版（continuity-editor 136 行 vs 35 行）；③commands 格式不同（.md vs .toml）。**以 `.claude` 为正本（内容最全），`.gemini` 是运行时适配层，分析忽略之**——233 md 去重后约 173。

**数据流**（docs/WORKFLOW.md:30-105）：branch-per-scene 写作 → 写作中 `/check-format`+`/check-continuity` → PR checklist 含 continuity → squash merge；**从文本到正典**：场景切分（`^(INT\.|EXT\.…)` 或小说章节标记，continuity-sweep.md:32-35）→ 连续性检查产出 finding → `/bible` 命令将确认 finding **固化为 canon 卡**（bible.md:58）。

**校验双层**：确定性脚本层——validate-bible.js（311 行）+check-bible-drift.js（153 行，`--strict` 作 CI 门禁，npm scripts lint:bible/bible:drift 在案）；**连续性语义判断（时间矛盾/知识矛盾）是纯提示词，无脚本**；另有 .claude/hooks/（guard-git.sh 阻 push main 等）。

## §2 数据模型与接口

**story-bible 六卡型**：character/location/**timeline-event**/prop/theme/arc——schema 由 `story-bible/_meta/vault-config.json` 统一定义：frontmatter 必填 8 字段（type/title/description≤160/tags/timestamp/status/sources/**verified_against**）；**statuses 四态 `[canon, draft, provisional, cut]`**（vault-config.json:22）；受控 tag 词表（:56-67）；每类型固定 sections。

**verified_against 漂移机制（本仓最高价值）**（story-bible/_meta/CONVENTIONS.md:26-37）：
- `timestamp` = **"date this card was last VERIFIED against its sources (not last edited)"**（:26）——验证时而非编辑时；
- `verified_against` = 声明所对的 git SHA（:30）；
- **"sources+verified_against are the drift hooks. When a sources file changes after verified_against, the card is stale — re-read the scene, update the claims, then bump"**（:35-37）——CI 强制"改场景必须配对 bump 卡片"（check-bible-drift.js:11-13）。

**map-card 原则**（CONVENTIONS.md:13-15）："A card **cites** the manuscript; it does **not** restate it...they *will* diverge. Keep every card under **50 lines**"——validate-bible.js:198 确定性强制。

**5 registry（continuity-tracking/SKILL.md:24-31）**：Character（外貌/知识/关系）/Timeline（编年/场时序）/Location/Prop（所有权/状态）/Wardrobe。**勘误：Wardrobe 无独立模板**——内嵌于 Character 的 Wardrobe Log 表（Scene|Page|Costume，:53-58）；持久层将其"folded into character(signature look→Traits)+prop(剧情服装单开卡)"（:281）——五 registry 实为四+折叠。

各 registry schema 要点：Character 含 **Knowledge State 表（By Scene|Knows|Doesn't Know，:60-66）**+Arc Tracking；Timeline=Story Span+按 Day 的 Chronological 表+**Flashbacks 表（Present Day|Flashback To|Purpose）**+Time Validation checklist（:121-125）；Prop=Tracking 表（Scene|Page|Status|Location，状态 Introduced/Used/Destroyed）+**Critical Props List 含 Chekhov's gun 列**（:186-190）；timeline-event 卡 When 段="story-time anchor+ordering note"且**链接相邻事件卡**表达顺序（_meta/templates/timeline-event.md:22-28），tag 用 present/flashback/flash-forward（:5）。

**登记与查询**：`/bible` 五步（选类型→模板或原地编辑→**sources 引用手稿+盖 verified_against SHA**（bible.md:36-39）→登记 _meta/manifest.json（id/type/title/path/sources）→lint）；`/check-continuity` 三类检查表+⚠️标记（DAY after NIGHT-CONTINUOUS/角色无位移时间/道具毁后复现/Chekhov 未兑现）；`/continuity-sweep` **每场派一个 continuity-editor 子代理**，以 story-bible 为 ground truth，**findings 表强制含 Cites 列指向 canon 卡路径**（continuity-sweep.md:47-54）；"/check-continuity treats status: canon cards as ground truth"（SKILL.md:293）。

**validate-bible.js 校验项**：frontmatter 完整性/status/tag 词表/描述长度/timestamp 格式/SHA 格式/sources 路径存在性/sections 精确匹配/单 H1/≤50 行/链接规则（禁 wikilink、禁根斜杠、出 bundle 外链仅限 Appears In，:203-221）。

## §3 可借鉴 / 不可借鉴清单

**可借鉴（MIT；设计层）**：
1. **verified_against SHA 漂移钩子**——**CBB"三态写入+引用完整性"的现成轻量实现**：Record 声明验证时所对版本，源变更→卡 stale→强制重验——迷深 517 章多版本语料（文库/web 版对齐）的场景**直接可用**（不同译本/修订版间卡片有效性可机判）。
2. **timestamp=最后验证时（非编辑时）**——时间戳语义的精细化：与"claimed verified"绑定而非"touched"。
3. **四态 canon/draft/provisional/cut**——cut=已删设定保留供参考的**墓碑态**（CONVENTIONS.md:58）：比 CBB 三态多一层"历史正典"（改编场景砍掉的设定仍可溯源）——CBB 是否需要第四态移交 U-A17 裁决。
4. **map-card 原则（引用不复述+≤50 行强制）**——正典抽取的黄金纪律：oh-story"事实 grep 回原文"的写入侧兄弟。
5. **Knowledge State 按场表**——"谁知道什么/何时知道"第四次出现且最表格化（author-toolkit→claude-book→story-skills→本仓），本仓还称其为"dramatic irony 的 spine"（SKILL.md:283）。
6. **外观状态三件套**：Chain of Custody（道具逐场 holder/state）、**Physical Injury Progression（Scene Acquired→Healed/Resolved）**、Wardrobe 逐场表——"身体与外观随时间演化"是其他仓罕见的正典维度；其折叠妥协（SKILL.md:281）提示 CBB **为外观状态设独立记录型而非折叠进人物**。
7. **findings 强制 Cites 列**——"断言带出处"做进 LLM 输出格式：CBB 抽取断言 schema 直接采用。
8. **timeline-event 链接相邻卡+flashback 三 tag**——事件顺序用链接表达而非全局时间轴（轻量替代方案，可与 nb-memory 双时间轴互补：无秒级时序需求时用链）。
9. **manifest.json 注册表+id 唯一锚**。
10. **git 参数注入防御**（check-bible-drift.js:21-24 注释+execFileSync 数组传参+--end-of-options，:109-115）——工具层安全工程细节。

**不可借鉴**：
1. 连续性语义判断纯提示词无脚本（确定性覆盖面远低于 story-skills）；
2. 编剧向（Fountain 格式/INT-EXT 场标）——小说场景需适配（其场景切分正则含小说章节标记分支，可参考）；
3. 双镜像维护成本（60 md 冗余）——CBB 单目标宿主不需要；
4. 无时间归一（Story Day+相对时段表格化，无 ISO/归一）。

## §4 许可与红旗

- **MIT 正式 LICENSE**（LICENSE:1-3，Copyright (c) 2026）——无传染。
- 维护：PR #61（2026-08-05）活跃；CONVENTIONS.md:7-9 自述改编自 safe-agentic-workflow 仓的 OKF v0.1 vault 机制（**出处诚实**——机制源头另有其仓，借鉴时留意）。
- 密钥/硬编码：脚本纯本地 git/文件操作；hooks 为 shell 防护件。零风险。
- 红旗：无。

## §5 与 CBB 对照（Step 0 三条件 + 四契约/三态）

**三条件对照**：
1. **元文本防御：无（LLM 层）**——grep injection/untrusted 唯一命中是 git 参数注入防御（工具层）；手稿当指令的防护不存在——R6 仍独有。
2. **时间归一：无形式化**（grep normalize/ISO 8601 零命中）——Story Day+相对时段+flashback 表是**故事内时间表格化**（写作侧纪律同 chinese-webnovel 层级）；cbb-anchor 仍独有。
3. **去重：半措施**——aka 别名字段（容纳非消解）+manifest id 唯一锚+命名一致提示词规则；无自动消解——CBB 需 oh-story 四分类+neo4j Resolver。

**四契约/三态对照**：
- **Record ≈ 六卡型**（8 必填 frontmatter+verified_against+sources——**溯源三件套：路径+SHA+验证时**，16 仓最完备）；
- **Issue ≈ /check-continuity findings**（三类检查表+⚠️，且**强制 Cites 列**）；
- **Verdict ≈ canon 卡固化流**（finding 确认→bible 卡，"canon cards as ground truth"）+stale 重验门；
- **Case ≈ continuity-report 模板**（含伤情演进/服装表的综合报告）；
- **三态映射：四态 canon/draft/provisional/cut**——provisional≈quarantine（暂定）、cut≈墓碑、draft≈待验、canon≈confirmed——**状态词汇表最丰富的域内样本**，CBB 三态+可选第四态（cut）的裁决素材。

**金标方法学（§K2）**：不适用（无评测件）；validate-bible 确定性 lint 是结构校验非语义。

## §6 处置建议

**四选一：借鉴设计（只学思路）**——理由：
1. 最高价值件（verified_against 漂移钩子/四态/map-card/Knowledge 按场表/外观三件套/findings Cites 列）全是 schema 与流程设计，MIT 干净；
2. 其确定性校验弱于 story-skills、连续性语义靠提示词——CBB 校验器主参照仍是 story-skills，本仓补**卡片生命周期与溯源**维度；
3. 编剧向模板不可直接移植（小说场景适配成本 > 收益），不装外挂。

移交 U-A17 吸收项：①verified_against SHA+timestamp=验证时+stale 重验门（多版本语料场景直接可用）②四态词汇表（canon/draft/provisional/cut——第四态 cut 裁决题）③map-card≤50 行+引用不复述 ④Knowledge 按场表 ⑤外观状态三件套（Chain of Custody/伤情演进/服装）⑥findings 强制 Cites 列 ⑦timeline-event 链接式顺序+flashback 三 tag ⑧manifest 注册表 ⑨git 参数注入防御细节。
