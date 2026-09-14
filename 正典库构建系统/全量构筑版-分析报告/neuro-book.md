# neuro-book (notnotype) 详报 · U-A10

> 分析日期：2026-09-15 ｜ 构建线产出，判定权在审核线
> 源码位置：`现成技能侦察/源码/neuro-book/`（clone --depth 1，可见提交 106f5e7 Merge PR #232）
> 方法：主线摸底证伪 + 前台子代理定向深读（六区）+ 主线抽验 4 处关键断言（全中）
> ⚠️ **AGPL-3.0 红旗仓：代码零借鉴零复制铁律最高优先级适用**（LICENSE:1-2,660）；本报告只读理解设计。

## §1 架构与数据流

**【三谜之三谜底】"54.7 万行 js 疑 vendored"双重翻案**：
1. **扩展名翻案**：`.js` 实测仅 **4 文件/313 行**；巨量实为 **`.ts` 2,285 文件/541,951 行**（+.tsx 18/3,518、.mjs 37/4,816、.vue 447/112,375）——task-036 的"JS/TS"合并桶再次转写失真（与 agent-skills 同款，Issue 001 口径建议适用）。
2. **vendored 证伪**：无 node_modules（bun.lock 517KB 只是锁文件）；542k 行 TS 是**真源码**——12 个 workspace 的 monorepo（README.md:170 自述；packages/ 下 neuro-book 主包+neuro-book-manager+nb-history+nb-workflow+nb-memory+neuro-agent-harness+llmlint+contracts 等+AGENTS.md 文档）。**这是一个真产品工程，不是打包产物仓**。
体积注：工作区 139M（+.git 85M）——索引清单 223MB 为含 .git 总量。

**产品定位**：AI 辅助长篇小说写作桌面应用（中文开发者作品，源码注释中文）——README.md:5「用工程的方法，写完你的长篇」、:28「世界状态由引擎推算…伏笔像技术债一样记账追踪，成稿用 360 条规则做 lint。你的作品是本地的 Markdown 文件和 SQLite」。四大能力：World Engine（:82）/Plot Workbench 承诺系统（:96）/多 Agent 工作室（:107-109）/llmlint（:114）。desktop/ 双壳（Electron 主进程+Tauri 外壳+shared 合同，desktop/README.md:7-17）。

**数据流**：Web UI 写作 → Agent 经 harness（独立包：Run Kernel/append-only Session/Invocation 生命周期/approval/compaction/事件恢复）调工具 → 落盘三轨：①人类可读 workspace 文件（lorebook/manuscript/simulation，assets/reference/content/project-structure.md:72-76）②SQLite 应用库 `workspace/.nbook/neuro-book.sqlite`（Prisma+迁移，server/database/app-sqlite-migrations.ts）③会话 append-only JSONL `.nbook/agent/sessions/<id>.jsonl`（session/session-repo.ts:309-315，schema 版本化 AGENT_SESSION_SCHEMA_VERSION=2 agent-session-store.ts:14，崩溃恢复 sentinel+lease 互斥锁）。

**内置 14 代理人格**（assets/workspace/.nbook/agent/profiles/builtin/*.profile.tsx）：writer/inline.editor/leader.default/leader.assets/director/memory.curator/researcher/retrieval/summarizer/world.engine/rp.leader/rp.writer/simulator.leader/simulator.actor——**读写分权**（"leader 可写、writer 只读"，README.md:88；writer.profile.tsx:19-24 绑定 plotReadBindings 只读 plot/world）；结构化输出契约（DirectorOutputSchema status 三值 completed/needs_user/blocked，profiles/builtin-contracts.ts:43-60）。

## §2 数据模型与接口

**nb-memory 双时间轴（16 仓时间维度最先进设计）**（packages/nb-memory/src/core/types.ts:4-30，注释自述"对齐 graphiti 的 bi-temporal"，ADR 0005）：
- **tick**=摄入序/叙事推进序（transaction time，宿主发放全序整数，**永远单调**，知识边界权威，必填）；
- **instant**=故事时间秒数（valid time，自世界零点，由 CalendarPort 从人读串解析；**可回退**——倒叙/插叙/回忆章 tick 递增而 instant 后退，"这正是必须双轴的原因"；可空）；
- **time**=人读原文标记（"第三天下午"；**不可比较**，不参与任何过滤排序，仅展示回流）；
- **as-of 双语义**：asOfTick=知识边界（"叙事推进到这里时知道多少"）/asOfInstant=世界状态（"故事时间这一刻世界什么样"）/双轴 AND 约束/双空=全知；
- **缺坐标判不可见**："给了某轴而记录缺该轴坐标时一律判为不可见：无法安放的记录宁可漏召回，也不能泄漏进它可能并不属于的时间窗口"。

**实体四件**：Episode（append-only 原始叙事单元，`source:"chapter:03"` 来源标注，types.ts:49-59）/Fact（happening **永不失效**；subjectIds≥2 即边；episodeId 溯源，:62-80）/Subject 注册表（aliases 带 **sinceTick/sinceInstant"何时得知同一性"**认知事件，:89-114）/StateEntry（可变认知，topic/view+sinceTick+**invalidatedAtTick 失效语义**，:117-131）。FactMeta 预留"角色视角可信度标记"（:41，扁平标量以便 SQLite 生成列）。

**lorebook canon 层与晋升门控**（assets/reference/content/lorebook.md:3-8,100-110）：lorebook="mostly stateless, omniscient canon layer"（稳定事实/原型/规则/可复用指令）；**"Initialization notes and low-confidence material that have not yet been promoted into stable canon"**（低置信材料存 canon 旁待晋升）；**"Do not use lorebook for: Temporary plot plans / Subject private knowledge, current mind state or inventory snapshots"**——正典层与瞬态层职责边界成文；SillyTavern 导入"not automatically canon until reviewed"（project-structure.md:94）。

**World Engine issue 契约二态**（assets/reference/world-engine/issues.md:17-22；server/world-engine/world-issue-catalog.ts:24,37,89）：`label E1-E5/A1-A2 + severity error|advisory`——error 必修/advisory 确认即可，附 subjectId/attr 定位。

**StoryPromise 承诺账本**（README.md:96；server/plot/contracts/plot-repositories.ts:7-8）：StoryPromise/StoryPromiseBeat 挂场景，写到目标章自动注入写作指令——伏笔=技术债的机器记账版。

**llmlint**（packages/llmlint/，独立技能可 npx skills add notnotype/llmlint）：规则库 **360 total/266 active**（PROJECT-STATUS.md:64）=245 regex/7 density/6 handler/8 semantic（:221），50+ namespaces；每规则三轴 **fixability=auto/candidate/manual（fix 只应用 auto）+review=human（置信度不足禁 Agent 自动改）+tier 四档 core 13/standard 71/wide 100/full 266 嵌套**（skill/README.md:102-111）；`.agent/` 台账 `{version:2,rounds:[]}` 只追加（PROJECT-STATUS.md:88）。

**.agents/tasks 开发治理档案**（根 .agents/README.md:5-9：works/=current Work/Task 唯一入口，Work 是 Task 强制容器；tasks/=legacy 归档；roles/ 角色合同）：全仓 1,199 个任务 md；抽样 56-world-engine/（README 章程=User Request/Goal/Current State/**45+ 轮迭代记录**+schema-design 等子文档）——"每轮定论写回文档+显式作废旧记录"的 agent 长任务断点续作档案。

## §3 可借鉴 / 不可借鉴清单

**⚠️ AGPL 边界声明**：以下"借鉴"全部是**设计思想层**（观其形、明其理、自行实现）——AGPL 下任何代码复制/改写/链接都触发传染，CBB 零接触代码，本节与 §6 处置一致。

**可借鉴（设计思想）**：
1. **双时间轴+as-of 双语义+缺坐标判不可见**——**16 仓时间设计之冠**，直接对标 cbb-anchor：tick（叙事序）与 instant（故事时间）分离解决"倒叙章"难题；"time 人读原文不可比较不参与排序"=伪锚点禁令的正面表述；"宁可漏召回不可泄漏"=时间窗口防御原则。CBB 时间字段设计的**首要参照**（且其注释自认对齐 graphiti bi-temporal——与我们 Step 0 调研 graphiti 的结论汇合）。
2. **happening/state 二分**——Fact 永不失效（append-only）vs StateEntry 带 invalidatedAtTick 失效语义：CBB Record 的两种类型（事件记录 vs 状态快照）的成熟分法。
3. **aliases 带 sinceTick"何时得知同一性"**——别名归一不止"是同一人"，还记"何时起知道是同一人"——比 graphify-novel 的静态 aliases 更进一步（认知事件化）。
4. **canon 晋升门控**——低置信材料存 canon 旁待晋升+导入材料不自动成正典：CBB quarantine→confirmed 的晋升流域内最正式表述。
5. **issue 二态 E/A+severity**——error 必修/advisory 确认即可：gate 原因码的分级设计（硬门/软门）。
6. **StoryPromise 挂场景+到章自动注入**——开环不止记录，还**驱动**后续写作（伏笔到回收章自动进指令）。
7. **读写分权 profiles**（writer 只读 plot/world）+输出契约 status 三值（completed/needs_user/blocked）——权限与状态机结合。
8. **会话 JSONL append-only+schema 版本化+lease 互斥+回滚快照**——P-017 幂等与断点恢复的工程级实现。
9. **llmlint 三轴规则（fixability/review/tier）+台账 append-only**——CBB lint 件（文本质量侧）的规则元数据设计。
10. **.agents/tasks 轮次回写档案**——与 BUILD-STATE+轨迹同构的大任务治理实证（45+ 轮的 world-engine 开发史全程可溯）。

**不可借鉴**：
1. **全部代码（AGPL）**——零复制零改写零链接；连"参照其代码结构重写"都应避免（思想/协议层面的借鉴以本报告文字转述为准）。
2. 桌面双壳/UAC 提权/provider 配置等工程基建与 CBB 无关。
3. nb-memory 是 spike（README 自述"记忆框架 spike"）非成品；BM25+planner 检索未含中文验证。
4. .agents/tasks 是开发治理非运行时机制（1,199 md 的历史包袱本身也是教训：任务档案需归档纪律）。

## §4 许可与红旗

- **AGPL-3.0**（LICENSE:1-2 "GNU AFFERO GENERAL PUBLIC LICENSE Version 3"，:660 适用条款）——**16 仓唯一强传染许可，红旗在案维持**：代码级零借鉴是铁案（总纲 §K3）；设计思想借鉴合法且必要（本报告 §3 已全部转述为文字，后续 CBB 设计文档引用本报告即可，无需再接触其源码）。
- 维护状态：**极活跃**（PR #232、RELEASE.md/PROJECT-STATUS.md/WATCHDOG.md 齐备、CI+release 流程、38 个 llmlint 测试文件）——个人/小团队的高工程纪律产品。
- 密钥/硬编码：探活未见（子代理六区扫描无报告）；AGPL 本身是最大合规约束。
- ACKNOWLEDGEMENTS.md 在案（依赖致谢规范）。

## §5 与 CBB 对照（Step 0 三条件 + 四契约/三态）

**三条件对照**：
1. **元文本防御：无显式**——但其"lorebook 不存 subject private knowledge/mind state"的层界纪律是语义分层的近亲（防错层存放）；R6（防旁白混入）仍独有。
2. **时间归一：16 仓最强，且与 cbb-anchor 直接同题**——双时间轴设计恰好是 Step 0"时间归一化双败→cbb-anchor 自研触发"的**正面参照答案**：tick/instant 分离处理倒叙、"第三天下午"原文保留不参与比较、缺坐标判不可见防泄漏。**cbb-anchor 的设计文档应把本仓双轴模型列为第一对照项**（文字转述，不抄代码）。
3. **去重：Subject 注册表+aliases 认知事件化**——别名归一+何时得知同一性；无嵌入合并（nb-memory 是 spike）——与 neo4j-skills Resolver 三档互补（它是字段/认知层，neo4j 是算法层）。

**四契约/三态对照**：
- **Record ≈ Episode/Fact/StateEntry 三件**（source/episodeId 溯源+append-only+失效语义）；
- **Issue ≈ WorldIssue 二态**（E/A+severity error/advisory）；
- **Verdict ≈ canon 晋升门控**（"not yet promoted"/"not automatically canon until reviewed"——审核裁决的域内最正式表达）；
- **Case ≈ .agents/tasks 档案**（45+ 轮迭代史）；
- **三态映射**：低置信待晋升≈quarantine、stable canon≈confirmed、invalidate（StateEntry invalidatedAtTick）≈rejected 的温和版（失效非否决）——**三态语义在本仓以"晋升/失效"词汇出现的最完整工程表达**。

**金标方法学（§K2）**：llmlint evals/ 在案（规则评测）但无抽取精度宣称——不适用。

## §6 处置建议

**四选一：只读参考（不借鉴代码、不装外挂）**——理由：
1. AGPL 决定代码零接触（铁案）；llmlint 虽是独立可装技能（npx skills add notnotype/llmlint），但其许可证随本仓 AGPL——**装外挂=引入 AGPL 件进运行时，与"绝对干净的正典库"路线冲突**，不装（文本质量检查 CBB 可用自建规则表起步）。
2. 设计思想价值极高（§3 十条），全部经本报告文字转述吸收——**"读它、学它、不碰它"**。
3. 与 CBB 的关系定位：**域内最先进的同类工程**（时间轴/晋升门控/承诺账本三件是 CBB 对口设计的最高水位参照），其 spike 状态（nb-memory）与 AGPL 约束共同决定"参照不依赖"。

移交 U-A17 吸收项：①双时间轴 tick/instant+as-of 双语义+缺坐标不可见（cbb-anchor 第一对照项）②happening/state 二分+invalidatedAtTick ③aliases sinceTick 认知事件化 ④canon 晋升门控词汇 ⑤issue 二态 E/A+severity ⑥StoryPromise 到章注入 ⑦读写分权+status 三值 ⑧会话 JSONL+lease+回滚快照 ⑨llmlint 三轴规则元数据 ⑩任务档案轮次回写纪律（+归档教训）。**AGPL 合规提示移交：CBB 设计文档引用本仓设计时引"全量构筑版-分析报告/neuro-book.md"转述，不直接链接其源码。**
