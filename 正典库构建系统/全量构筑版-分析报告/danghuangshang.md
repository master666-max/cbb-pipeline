# danghuangshang 详报 · U-A06

> 分析日期：2026-09-15 ｜ 构建线产出，判定权在审核线
> 源码位置：`现成技能侦察/源码/danghuangshang/`（clone --depth 1，可见提交 acea185 PR #145 2026-05-22）
> 方法：前台子代理深读 + 主线抽验 6 处关键断言行号（全中）
> ⚠️ 对账勘误两条（详见文末）：①仓实为多 Agent 系统，小说仅一模块；②js 实测 45 文件/6,678 行，task-036 表 60/8,509 不符。

## §1 架构与数据流

**仓库真实身份**：「当皇上✖️OpenClaw」**明朝朝廷多 Agent 系统**（README.md:26-28），小说创作只是可选的"翰林院"模块（README.md:95、437-440）——索引清单"五文件档案（伏笔台账+关系网）"是其中的 novel 子系统，判定有效但**定位面收窄过**。

**规模实测**：388 文件/194 md 吻合；js 实测 45 文件/6,678 行（gui/server/index.js 2531 行 WebUI + scripts/*.js 基础设施 + tests），**非 task-036 表的 60/8,509**（口径差异待查，不影响结论方向）；py 6 个/396 行全在 scripts/（Notion 集成工具，与小说无关）。md 大头：docs/ 60、configs/ 人格与代理定义 39、ai-court-skill 19、tang-sansheng 14。

**小说链数据流**（README.md:447-456 + configs/ming-neige/agents/）：掌院学士（hanlin_zhang.md:3 拆任务+终审）→ spawn 修撰（架构：novel-worldbuilding 生成 plan.md+五文件）→ 掌院审批 → spawn 编修（逐章 ≥10000 字，novel-prose:14-43 分段写作法，写完**自归档**调 novel-archiving）→ spawn 检讨（novel-review 七维度 Red/Yellow/Green）→ 循环至全书完成 → 终审。庶吉士纯检索不改文件。

**断点续跑两层**：(a) 文件即记忆——"第100章时读文件就能回忆第1章设定"（skills/novel-memory/SKILL.md:89）；(b) 仓库级任务状态机 `scripts/task-store.js` + `docs/task-state-machine.md:14-38`（plan.json 拆步、依赖注入上游输出、status 查询）。另有 `extensions/novel-openviking/`（SKILL.md:15-28）把全部文件操作映射到语义记忆 memory_store/recall/forget——**同一 schema 双后端**（grep 文件 ↔ 语义向量）。

## §2 数据模型与接口

**五文件档案 schema**（skills/novel-memory/SKILL.md:14-29，本仓对 CBB 的核心资产）：`novel/{书名}/` = plan.md（总控大纲）+ 设定/ 五文件 + 正文/ + summary/：
- **characters.md**：全部角色；字段=姓名/年龄/外貌/性格/背景/动机/能力（novel-memory:43）；完整模板（skills/novel-worldbuilding/references/templates.md:56-95）：基础信息→外貌(标志性特征)→性格(说话方式/**口癖**/价值观)→背景(创伤/执念)→关系网络→弧线(起点/转折/终点)→**创作约束(绝不会做/必然会做/弱点)**。**角色状态追加不覆盖**，保留变化史（novel-memory:54、90）。
- **world.md**：力量体系（等级/核心规则/**代价/已知例外**）、政治结构、阵营表（势力|领袖|立场|目标|与主角关系，templates.md:100-126）。
- **foreshadowing.md**（伏笔台账）：行条目（novel-memory:99-104）=**F001 编号**+埋设(第X章+场景)+预计回收(第Y章)+状态(未回收/已回收(第Z章))+关联角色；表格式增强版（templates.md:135-146）七列 ID|内容|埋设章|预计回收|**实际回收**|状态|备注，**四态+超期态：⚪待埋设/🔵已埋设/✅已回收/🔴遗漏（超预计回收章未回收，需要处理）**。
- **timeline.md**：故事内时间进度+各章时间跨度（novel-memory:53）——**无专门模板**（五文件中最薄的一件）。
- **relations.md**：**无专属模板、无 mermaid/矩阵**——实际编码为人物档案内逐节点邻接表"与[角色B]：[关系类型]—[描述]"（templates.md:82-84）。
- **读写契约**：每章前必读=上章摘要+角色末尾状态段+未回收伏笔+时间线（novel-memory:60-65）；查询用 grep 定位（:67）。

**archiving 四步**（skills/novel-archiving/SKILL.md 全文）：每章正文完成后立即触发（:16）——①生成 `summary/chapter_{XX}.md`（模板 :24-55：情节要点、**角色状态变化表（角色|变化前|变化后|变化原因）**、新埋伏笔 F{XXX}、回收伏笔、时间线、关键对话、遗留问题）；②更新设定文件（伏笔标 ID+预计回收/原始章节，:65-67）；③条件触发更新 world/relations（触发清单 :78-84：新角色/新设定/关系重大变化/新能力/新势力）；④向掌院产出状态报告（:90-113：状态=完成/需修正、字数、伏笔增减、文件更新清单、问题报告）。常见错误专列：伏笔两处不同步/新角色漏登/时间线断裂（:128-133）。

**任务状态机**（scripts/task-store.js:33-46）：七态 pending/running/success/failed/retrying/cancelled/**revision_required**；ErrorType 三分 transient/permanent/**rejected（审查驳回）**——注释称支持 SQLite 持久化（:8），默认 tasks.json（:28）。

**Agent 权限沙箱**（scripts/permission-guard.js:208-217）：翰林默认权限=只能与 hanlin_* 交互、只用 novel-* 技能、**写路径白名单 `novels/`**——按来源隔离写入。

**量化审核**：review-template.md:7-9 报告含评分 X/5+字数统计（实际/10,000 目标）——确定性数值锚点。

## §3 可借鉴 / 不可借鉴清单

**可借鉴（MIT，wanikua；学设计零复制）**：
1. **伏笔台账五态**（含🔴遗漏超期态）——四态+超期警报比 chinese-webnovel 两态更完整，🔴遗漏≈CBB quarantine 的超时子类先例。
2. **角色状态变化表（变化前|变化后|变化原因）**——归档摘要里的状态演进三元组，CBB Record 状态变更日志的字段级参照。
3. **追加不覆盖的角色状态史**（novel-memory:90）——append-only 变更日志，类审计轨迹。
4. **归档四步流程+条件触发更新**（world/relations 只在五类触发条件下降临更新，非每章重写）——防档案抖动。
5. **每章前必读清单**（摘要+末状态+未回收伏笔+时间线）——上下文注入的最小集，CBB 查询侧的默认视图。
6. **任务七态+错误三分**（revision_required 独立于 failed；rejected 独立于 permanent）——CBB 三态写入与驳回语义的状态机工程化参照。
7. **写路径白名单按 agent 隔离**——可迁移为 CBB 按写入方限制 quarantine/reject 权（谁只能写隔离区）。
8. **双后端记忆抽象**（文件 grep ↔ 语义 memory_store 的操作映射表）——CBB 存储层（SQLite+可选向量）做抽象时的映射先例。
9. **量化审核字段**（评分/字数比目标）——防纯定性判断漂移。
10. **阵营表五列**（势力|领袖|立场|目标|与主角关系）——组织类实体的紧凑 schema。

**不可借鉴**：
1. 无 schema 校验器（五文件靠约定与自检清单，R-020 反面）；伏笔台账"两处不同步"恰是双写（行条目+表格两版式并存）自酿的风险。
2. relations.md 无独立模型（嵌在人物档案邻接表）——关系查询要全文 grep，规模上限低；CBB 关系表独立建模正确。
3. timeline.md 五文件中最薄（无模板无锚点规范）——时间归一是本仓最弱一环。
4. 多 Agent 朝廷架构（configs/ 39 个 md）对 CBB 无直接可移植性——我们的代理拓扑由 ZCode 会话承担。
5. js 基础设施（WebUI/权限/任务存储）绑定 OpenClaw 生态，抽出即失效。

## §4 许可与红旗

- **MIT 正式 LICENSE**（LICENSE:1-3，Copyright (c) 2026 wanikua）——无传染。
- 维护：shallow 单提交（acea185，PR #145，2026-05-22，boluobobo）——活跃社区 PR 形态，但主线历史不可见。
- 密钥/硬编码：update-oauth-token.py 为 Notion OAuth 工具（小说链不用）；gui/server 为本地 WebUI——未见明文 key（子代理 grep 未报命中）。无 GPL/AGPL。
- 红旗：无。仓内 ai-court-skill/tang-sansheng 等模块与小说无关，分析边界已在 §1 声明。

## §5 与 CBB 对照（Step 0 三条件 + 四契约/三态）

**三条件对照**（子代理 grep 于 skills/+configs/）：
1. **元文本防御：无**。`旁白|元文本|出戏|作者注释|打破第四面墙` 零命中；最近似物=novel-prose:49-54 视角一致性规则（防 POV 越界，非防旁白混入）。R6 独有性再+1。
2. **时间归一：字段有、防御无**。timeline.md 专记故事内时间+逐章跨度（novel-archiving:46-48）；"时间线错误"列为🔴致命（novel-review:77）；但**无防现实墙钟显式禁令**（`现实时间|墙钟|当前日期` 零命中）——靠字段设计不靠防御规则，cbb-anchor 仍必要。
3. **实体/事件去重：无系统机制**。最近似物=归档错误清单"新角色出现但没写入 characters.md→检查是否需要创建"（novel-archiving:132，防漏非去重）；检讨"人物一致性"（novel-review:36-40）靠 LLM 比对。无别名归一表。

**四契约/三态对照**：
- **Record ≈ 五文件+章节摘要**（伏笔带 ID/埋设章/回收章溯源；角色状态追加史）；
- **Issue ≈ 归档"问题报告"+检讨七维度 Red/Yellow/Green**；
- **Verdict ≈ 任务状态机 revision_required/rejected**——驳回是独立态而非异常，与 CBB 三态+Verdict 驳回语义**工程同构度最高的一件**；
- **Case ≈ summary/ 章节摘要**（含遗留问题=开环）；
- **三态映射**：⚪待埋设/🔵已埋设≈confirmed 的生命周期子态、🔴遗漏≈quarantine 超时子态、✅已回收≈终态——五文件体系是**迄今三态语义最丰富的域内先例**（三仓累计：webnovel 两态→danghuangshang 四态+超期）。

**金标方法学（§K2）**：无评测件；量化审核字段（字数/评分）是确定性锚点但非抽取精度——不适用。

## §6 处置建议

**四选一：借鉴设计（只学思路）**——理由：
1. 核心资产（五文件 schema/伏笔五态/状态变化表/归档四步/任务状态机）全在提示词与模板层，MIT 干净，吸收零成本；js 基础设施绑定 OpenClaw 生态不可抽出，无运行时件可装。
2. 它是"写作侧档案体系"最工程化的一仓（状态机+权限沙箱+量化审核），但其校验缺位与 timeline 薄弱恰是 CBB stdlib 校验器+cbb-anchor 的对照差异。
3. 与 chinese-webnovel-skills（档案格式）+claude-book（合并裁决）互补，三仓拼出 CBB Record/Issue/Verdict 的域内参照全集。

移交 U-A17 吸收项：①伏笔五态（含🔴超期）②角色状态变化表三元组 ③追加不覆盖状态史 ④归档四步+条件触发更新清单 ⑤每章必读清单（默认查询视图）⑥任务七态+错误三分（revision_required/rejected 独立）⑦写路径白名单按写入方隔离 ⑧双后端记忆操作映射 ⑨阵营表五列。

## 附：对账勘误（移交审核线）

1. **仓定位**：索引清单/task-036 按"五文件档案（伏笔台账+关系网）"收录——实测仓主体是明朝朝廷多 Agent 系统（README.md:26-28），小说是翰林院模块。收录动机仍成立（该模块确为精华），但报告定位已修正。
2. **js 统计口径**：task-036 表 60 文件/8,509 行，实测 45/6,678（find . -name "*.js" 排除 .git）。可能当时含 .bak/其他扩展或不同排除口径——建议 U-A17 汇总时统一按本次口径复核，或回查 task-036 脚本。
