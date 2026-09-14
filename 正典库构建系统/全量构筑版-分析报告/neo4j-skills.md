# neo4j-skills (neo4j-contrib) 详报 · U-A09

> 分析日期：2026-09-15 ｜ 构建线产出，判定权在审核线
> 源码位置：`现成技能侦察/源码/neo4j-skills/`（clone --depth 1，可见提交 a9a5e78 2026-08-25 skill-refresh bot PR #53）
> 方法：前台子代理机制级深读 + 主线抽验 3 处关键断言（全中）
> ⚠️ 小勘误：README "Available Skills" 表仅列 24 技能，磁盘与 skills.sh.json 实测 29——文档口径滞后。

## §1 架构与数据流

**仓库形态**：Neo4j 官方贡献组技能仓——**29 个 neo4j-*-skill/ 目录**（每个=SKILL.md 入口+references/ 渐进加载，4 个含 scripts/）+ AGENTS.md 贡献规范 + skills.sh.json 机器清单 + CI 三件（skill-refresh/skill-lint/release，.github/workflows/）——**机器维护为主**（skill-refresh bot 按 Neo4j 版本发布说明自动刷新，可见提交即 bot 产物）。

**分层架构**（对 CBB 有意义的六件，其余见 §6）：
- **构建侧**：`neo4j-document-import-skill`（585 行，GraphSchema 约束式抽取+分块+实体归并）——KG 构建的家；
- **检索侧**：`neo4j-graphrag-skill`（555 行 v1.0.11）——**明确不做构建**（SKILL.md:10,33 "Does NOT handle KG construction — use neo4j-document-import-skill"），只管检索（retriever 决策树:42-68→vector+fulltext 索引:122-139→retrieval_query Cypher 图扩展:158-168→LLM）；
- **建模侧**：`neo4j-modeling-skill`（361 行，用例先行+反模式表）；
- **导入侧**：`neo4j-import-skill`（500 行，CSV/JSON/Parquet 多格式+冲突处理）；
- **记忆侧**：`neo4j-agent-memory-skill`（427 行，neo4j-labs 包权威文档镜像：三层记忆+POLE+O 实体模型）；
- **查询侧**：`neo4j-cypher-skill`（421 行 v1.0.22，Schema-First+12 硬默认）。

**端到端数据流**（GraphRAG 全链）：定义 GraphSchema（三档：字符串原型/生产级 NodeType+RelationshipType+patterns 约束合法三元组/"EXTRACTED"|"FREE" 放任，document-import SKILL.md:74-124）→ SimpleKGPipeline 抽取（`:150-159`，**抽取提示词由 schema 自动生成**，kg-builder.md:27-59）→ 分块（叙事文本 512-1024/80-128，`:208-232`）→ **实体归并**（`:236-264`）→ 写入 lexical graph（`(:Document)-[:HAS_CHUNK]->(:Chunk)-[:NEXT_CHUNK]->` 链 + `(:Chunk)-[:MENTIONS]->(:Person/:Organization)`，`:270-287`）→ graphrag 技能检索（Text2Cypher 先 EXPLAIN **写操作即拒** :219-222,322）。

## §2 数据模型与接口

**GraphSchema 三档模型**（document-import:74-124）：①字符串列表原型 ②生产级=NodeType/RelationshipType 带 description+patterns 约束合法三元组（**description 直接注入抽取提示词**）③EXTRACTED/FREE 放任抽取——**schema 严格度分级**是抽取质量的第一个旋钮。

**实体归并三档 Resolver**（document-import:236-264）：SinglePropertyExactMatchResolver（同名→merge，快基线）/ FuzzyMatchResolver（Levenshtein，threshold 0.9，需 rapidfuzz）/ SpaCySemanticMatchResolver（余弦相似，需 [nlp] 扩展）——**可按 label 过滤归并范围**（"WHERE n:Organization OR n:Person"）；"Run resolvers after ingestion, not inline — bulk merges are faster"；底层 apoc.refactor.mergeNodes（kg-construction.md:55-120 含阈值选择表与属性合并策略 combine/overwrite/discard）。

**事实级去重（v0.1.1+，agent-memory SKILL.md:286）**："auto-merges duplicate facts and preferences using subject/predicate matching plus embedding similarity (threshold ~0.95), and **updates confidence rather than creating new nodes**"——主谓匹配+嵌入 ~0.95 双条件合并，**更新置信度而非新建节点**。

**modeling 五律**（modeling SKILL.md:62-67）：用例先行（≥5 查询再建模）/节点=名词、关系=动词带方向/**MERGE 目标必建唯一约束**/禁泛型标签与关系（`:Entity`/`:RELATED_TO`/`:HAS` 全禁 :67）/中间节点模式（关系需带属性、连 >2 实体、独立可查时升级为节点，:103-132——**事件建模直接可用**）。反模式表 :269-282（无约束 MERGE 产生重复 :278、日期存字符串 :282）。

**import 冲突处理**（import SKILL.md:60-64,100-110,184-217）：约束先于导入（"Constraints BEFORE import"）/`MERGE...ON CREATE SET/ON MATCH SET` 区分首建复见（复见仅刷 updatedAt）/`CALL IN TRANSACTIONS` 四种 ON ERROR 模式+REPORT STATUS **错误行可审计**。

**cypher 12 硬默认**（cypher SKILL.md:44-57）：首 token `CYPHER 25`/MERGE 仅限受约束键/探索读默认 LIMIT 25/禁无标签 MATCH/Schema-First（优先读项目内 `<db-name>-schema.json`，无则实测 `db.schema.visualization()`，**禁止猜测标签名**）。

**py 脚本 9 件**（合计 1,590 行，无泄密）：Aura 三件（fetch_schema 337 行拉 schema.json/invoke_agent/manage_agent）+cypher 三件（generate_schema 从 APOC 导出/define_schema 交互式定义/import_neo4j_schema 格式互转）+validate_queries 148 行（批量验证，≥60% 过线）+仓库维护两件（bump-version/lint_skills 223 行按 agentskills.io 规范 lint）。**全部凭据走环境变量**（NEO4J_URI 默认 bolt://localhost:7687，generate_schema.py:8）；仅有的 URL 是公共 API 端点 api.neo4j.io。

## §3 可借鉴 / 不可借鉴清单

**可借鉴（MIT，Neo4j Contrib；设计+正文皆可参照）**：
1. **事实级去重"更新 confidence 而非新建节点"**（agent-memory:286）——**与 CBB 三态写入最同构的单条设计**：重复事实合并=confirmed 增强（confidence 上调），非重复=新 Record——CBB store 的 supersedes/merge 语义直接参照。
2. **Resolver 三档+阈值表**——CBB 实体去重（Qwen3-Embedding 4096 维）的分级策略：Exact（别名归一后）/Fuzzy（编辑距离，防 OCR 错字）/Semantic（嵌入阈值）三档流水，且**范围可按 label 过滤**（人物与地点的去重阈值应不同）。
3. **GraphSchema 三档严格度**——CBB 抽取 schema 的旋钮设计：原型（快速）/生产（patterns 约束合法三元组）/放任（对照实验用）。
4. **schema description 注入抽取提示词**——实体类型描述即提示词的一部分，CBB 抽取器的类型描述词表可复用此机制。
5. **modeling 五律+中间节点模式**——CBB 图 schema 设计守则（事件=中间节点；禁泛型关系；约束先行）。
6. **ON CREATE/ON MATCH SET 首建复见区分+错误行可审计**——CBB 入库幂等（P-017 姊妹设计：断状态不断过程在数据库层的落地）。
7. **Text2Cypher EXPLAIN 拒写**——检索层永不写库的防御（review 不写盘的数据库版）。
8. **Schema-First 禁猜测**——与 R-014/R-016（宣称层≠实现层）同构的查询纪律。
9. **POLE+O 实体模型**（Person/Organization/Location/Event/Object）——与小说五要素同构的基线类型学。
10. **分块参数表**（叙事 512-1024/重叠 80-128）——迷深类长篇的实测起点参数。
11. **lint_skills.py**（agentskills.io 规范 lint）——CBB 技能族 CI 参照。

**不可借鉴**：
1. 约 17 个产品向技能（aura 云运维/kafka/spark 流批/5 个语言 driver/graphql/spring-data/nvl/migration/security 等）与 CBB 无关——装机时不必全装（见 §6）。
2. agent-memory 是文档镜像非可执行流程（无 DDL 级 schema）。
3. modeling SKILL.md:357 引用 references/modeling-patterns.md 但该技能无 references 目录——**死链**（官方仓也有文档失修）。
4. 中文场景零验证（分块参数/embedding 阈值全为英文语料标定——Step 0 已证中文需自测，此仓数字仅作起点）。

## §4 许可与红旗

- **MIT 正式 LICENSE**（LICENSE:1,3，Copyright (c) 2026 Neo4j Contrib）——官方件，无传染。
- 维护：**机器维护活跃**（skill-refresh bot 按 Neo4j 发布说明自动更新，可见提交 2026-08-25；CI 三件+linter 齐备）——可持续性好。
- 密钥/硬编码：**零命中**（环境变量/dotenv；公共 API 端点非密钥）——§4 干净。
- 红旗：装机安检当时 1 命中（Neo4j 官方安装器文档含安装指令类内容）——属文档性质非代码风险，维持装机判定。README 24 vs 磁盘 29 的口径滞后是小瑕疵。

## §5 与 CBB 对照（Step 0 三条件 + 四契约/三态）

**三条件对照**：
1. **元文本防御：无**（grep narrat|aside|paratext|meta-text|fiction 全仓，仅命中分块粒度表"Narrative / news articles"一行 document-import:229——是分块建议非防御指令）。R6 独有性+1（16 仓累计：仅 graphify-novel 有安全层近亲，语义层全空白）。
2. **时间归一：存储类型规范有、归一管线无**——modeling:282 反模式"日期存字符串→用 date()/datetime()"；import:106 导入时 CASE WHEN 转 date()；ZONED DATETIME 与 date() 混比返回 0 行（cypher-syntax.md:287,487）。**缺**：异构时间格式归一、虚构故事时间处理——cbb-anchor 仍独有；但"存储类型必须原生 temporal"是 CBB 时间字段的硬规矩（避免字符串比较陷阱）。
3. **实体/事件去重：16 仓最强**——三层完备：抽取后归并（Resolver 三档+mergeNodes 属性合并策略）/写入防重（约束+MERGE 原子锁）/事实级（主谓+嵌入 0.95+confidence 更新）+离线工具（--skip-duplicate-nodes）。**CBB 去重条件（Qwen3-Embedding）的工程化蓝图基本齐了**，缺中文阈值标定（Step 0 补）。

**四契约/三态对照**：
- **Record ≈ 图节点+约束**（唯一键+ON CREATE/ON MATCH 幂等）；
- **Issue ≈ import 错误行 REPORT STATUS 可审计**；
- **Verdict ≈ EXPLAIN 拒写**（检索层裁决权分离）；
- **Case ≈ 无对应物**；
- **三态 ≈ confidence 更新式合并**——quarantined/confirmed 之外的第三思路：重复不隔离而是**置信度合并**（对"同一事实多次出现"场景比三态更经济；对"矛盾事实"仍需三态）——CBB 可双轨：一致重复→confidence 合并，矛盾→quarantine+Verdict。

**金标方法学（§K2）**：validate_queries.py 的 ≥60% 过线是最低门槛不是金标——不收编其阈值；evals/dataset.json 是其自有评测集（产品向）。

## §6 处置建议

**四选一：装外挂（进运行时）·维持已装机**——理由：
1. 实验版 U0 已装机（§K4 默认沿用）——**无降级证据**：MIT 官方件、机器维护活跃、零密钥、图层六件（document-import/graphrag/modeling/import/agent-memory/cypher）对 CBB 直接可用，去重三档是 CBB 去重条件的工程蓝图。**沿用判定成立，且为 16 仓中唯一"运行时价值>设计价值"的仓**。
2. 优化建议（非阻塞）：装机范围可裁剪——产品向约 17 技能与 CBB 无关，未来若重装可只取图层六件+getting-started（PT-008 cp -n 路径按技能名挑）；当前全装不产生害处（技能按需加载）。
3. 与 neo4j-skills 的关系定位：**CBB 的图层执行件**——CBB 四契约三态在 SQLite 账本层，图存储与查询走本外挂；本报告 §3 的 11 条吸收项把其纪律内化进 CBB 契约。

移交 U-A17 吸收项：①事实级去重 confidence 更新式合并（与三态双轨）②Resolver 三档+label 过流+阈值表（中文标定留 Step 0 后续）③GraphSchema 三档严格度旋钮④类型 description 注入提示词⑤modeling 五律+事件中间节点⑥ON CREATE/ON MATCH 幂等⑦EXPLAIN 拒写⑧Schema-First 禁猜测⑨POLE+O 基线类型学⑩叙事分块参数起点⑪lint_skills CI 化。
