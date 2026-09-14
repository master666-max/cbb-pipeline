# webnovel-writer (lingfengqaq) 详报 · U-A15

> 分析日期：2026-09-15 ｜ 构建线产出，判定权在审核线
> 源码位置：`现成技能侦察/源码/webnovel-writer/`（clone 快照，master 最新 878ce26 2026-08-31；master=v6.2.1 维护中/v8 开发中）
> 方法：前台子代理契约级深读 + 主线抽验 3 处核心断言（时序回放 SQL/urgency 公式/memory 四态——全中）
> ⚠️ **GPL-3.0 红旗铁案（LICENSE:1-2，仅此一份无双授权）：代码零借鉴零复制零链接**；本报告只读理解设计。索引清单"7.1k★"本地不可核（仅 trendshift 徽章+star-history 图，README.md:7,355）。

## §1 架构与数据流

**定位**："跑在 Claude Code 上的长篇网文创作插件——面向长篇连载的一致性系统"（README.md:3,16-17）；8 命令（init/plan/write/review/query/learn/dashboard/doctor，README.md:62-71）。

**构成**：插件主体嵌套于 `webnovel-writer/` 子目录；py 202 个/53,243 行——`scripts/data_modules` 66 个/20,751 行（**核心数据层**）+tests 76 个/18,555（**测试占 37%**）+scripts 29/9,469+dashboard 6/1,182+memory 8/1,376 等；js 23/655（dashboard 前端）。工程纪律强（R-016 核证其为真工程，非简历项目）。

**数据流**：写作会话 → chapter-commit 事件提交（事件名归一，chapter_commit_schema.py:51-56）→ **事件投影路由**（event_projection_router.py）分发到三库 → 写前上下文装配（context_manager._build_pack 分区+预算+排序）→ PreToolUse hook 保护运行时文件。

**三库分立**：
- **index.db**（index_manager.py，18 表）：entities/aliases/state_changes/relationships/relationship_events/appearances/chapters/scenes + 追读力族（override_contracts/**chase_debt**/debt_events/chapter_reading_power/invalid_facts/review_metrics/rag_query_log/tool_call_stats/writing_checklist_scores）；
- **vectors.db**（rag_adapter.py）：vectors（embedding BLOB）/bm25_index/doc_stats/**rag_schema_meta（schema_version 版本化+迁移前备份 ：139-152）**；
- **events.db**（event_log_store.py）：story_events（event_id UNIQUE）。
长期记忆不用 SQLite：memory_scratchpad.json（atomic_write_json+FileLock，memory/store.py:40-41）。

## §2 数据模型与接口

**核心表 schema**：`entities`（id PK/type/canonical_name/tier/current_json/first_last_appearance/is_protagonist/**is_archived**，index_manager.py:300-314）；`aliases`（**复合 PK=alias+entity_id+entity_type**，:317-325）；`state_changes`（entity_id/field/old_value/new_value/**reason/chapter**，:328-339）；`relationships`（**UNIQUE from+to+type**，:342-353）；`relationship_events`（polarity/strength/evidence/**confidence**，:388-404）；`appearances`（**confidence REAL+UNIQUE entity+chapter**，:274-283）。时间戳几乎全表（created_at/updated_at）；实体更新=current_json 字段级覆盖合并（index_entity_mixin.py:90），无历史快照（时序靠 state_changes 追加日志）。

**query-entity-state=时序回放**（knowledge_query.py:16-45）：`entity_state_at_chapter` 取 `state_changes WHERE entity_id=? AND chapter<=? ORDER BY chapter ASC, id ASC` **顺序覆盖 field→new_value 重建任意章状态快照**——"查询实体在指定章节时的状态（从 state_changes 反推）"；关系同法（:46-77）；别名消歧走 aliases 表+UncertainMention/confidence/adopted（schemas.py:57-63）。**纯 SQL 精确匹配+章节回放，非模糊非 RAG**——event sourcing 的小说实现。

**open-loops 机制**：memory category "open_loop"+事件名归一（open_loop/loop_closed→open_loop_created/closed）；**urgency 公式**（status_reporter.py:507-546）：`urgency=(已过章节/目标回收章节)×层级权重`，三层级**核心 3.0（必须回收否则剧情崩塌）/支线 2.0（否则显得作者健忘）/装饰 1.0（可回收可不回收仅增加真实感）**（config.py:305-307）；状态🔴已超期/🟡警告/🟢正常；写前注入 urgent_loops **前 3 条**（memory_contract_adapter.py:219-221）。

**memory 四态**（memory/schema.py:15）：`active/outdated/contradicted/tentative`；七 category→bucket 映射（:18-27，含 reader_promise）。

**RAG 装配**：**云端 embedding**（OpenAI 兼容 /v1/embeddings，默认 text-embedding-3-small，api_client.py:14-16）+rerank 默认 Jina v2 multilingual（:19-21）；检索=向量余弦（小库全表/大库 BM25+近章预筛）+自实现 BM25（k1=1.5/b=0.75）→**RRF 融合**（1/(k+rank+1)，rag_adapter.py:1246-1253）→rerank 精排；graph_hybrid_search 以别名/实体 ID 提种子+图谱先验加分（同实体/相关实体/近章 recency，:941-963）；**检索自动带 chapter<=? 时间闸防剧透**（:718-735）；embed 失败 BM25 降级兜底。注入分区（core/scene/global/story_contract/runtime_status/prewrite_validation/reader_signal/writing_guidance/alerts）；**预算按字符不按 token**（context_extra_section_budget=800，config.py:215；≤30 章/≥120 章动态权重 ：259-267）；排序 recency 0.7/frequency 0.3（context_ranker.py:51-52）。

**项目根保护三层**（hooks/guard_runtime_write.py）：①PreToolUse hook——PROTECTED_SUFFIXES（.story-system/commits/、index.db、vectors.db、memory_scratchpad.json、projection_log.jsonl，:17-23）写命中即 deny（:131-135）+**bash 重定向/python 绕过命令拦截**（:103-112）+**白名单仅 chapter-commit/write-gate/projections retry|replay 四命令**（:24-30）；state.json 故意不保护（:14-16 注释：审计需批量修）；②git 备份——GitBackupManager 每章自动 commit+checkout 回滚（backup_manager.py:75-92），commit message 经 sanitize **防注入**（:63）；③根解析——project_root 必须含 .webnovel/state.json（webnovel.py:48-53）。

## §3 可借鉴 / 不可借鉴清单

**⚠️ GPL-3.0 边界：以下全部为设计思想层借鉴（经本报告文字转述），CBB 零代码接触。**

**可借鉴（设计思想）**：
1. **state_changes 时序回放**——任意章状态重建的 SQL 范式（追加日志+顺序覆盖）：与 nb-memory as-of-instant 同族但**用章号轴+SQL 实现**（更轻）；CBB store 的历史查询（"第 N 章时角色状态"）直接采用此设计。
2. **UNIQUE 约束族防重**——aliases 复合 PK/relationships UNIQUE(from,to,type)/appearances UNIQUE(entity,chapter)：**把去重交给 schema 约束**（与 neo4j 唯一约束+MERGE 同哲学的 SQLite 版）。
3. **confidence 字段多处+apply_confidence_filter**——置信度入库+上下文装配时按置信度过滤：R-010 的存储层落地。
4. **urgency 公式化开环提醒**——三层级权重（3.0/2.0/1.0 语义清晰）+进度比公式+🔴🟡🟢 三档+只注入前 3 条——**开环管理的最完整工程实现**（超越 danghuangshang 🔴遗漏态与 story-skills 契诃夫枪的单一阈值）。
5. **memory 四态**（active/outdated/contradicted/tentative）——contradicted 独立成态（矛盾态）与 CBB quarantine 的对照素材。
6. **检索 chapter<=? 时间闸防剧透**——检索层防未来泄漏（与 nb-memory"缺坐标不可见"同族，实现更简单）。
7. **PreToolUse 保护后缀+命令白名单+绕过拦截**——agent 写入防护的完整 hook 设计（bash 重定向/python 绕过都拦）；commit message sanitize 防注入。
8. **schema_version 版本化+迁移前备份**——库 schema 演化的安全件。
9. **RRF 融合+BM25 降级兜底**——混合检索工程参数（k1=1.5/b=0.75、RRF 公式）。
10. **三层级语义注释**（"否则剧情崩塌/显得作者健忘/仅增加真实感"）——开环分级的可读化表达。

**不可借鉴**：
1. **全部代码（GPL-3.0）**——零复制零改写；连 SQL 语句也不宜逐字照抄（保守口径），按设计重写。
2. 云端 embedding 依赖（OpenAI/Jina）——CBB 用本地 Qwen3-Embedding（Step 0 已定），且其默认模型中文效果未验。
3. 字符预算制（非 token）——设计缺陷，CBB 用 token 预算。
4. 长期记忆 JSON 文件+FileLock（未入 SQLite）——与其三库分立架构不一致的技术债（v8 开发中可能重构）；R-020 角度 CBB 全部入账本。
5. 追读力族表（chase_debt/reading_power 等）为网文商业指标域，正典库不需要。

## §4 许可与红旗

- **GPL-3.0**（LICENSE:1-2）——**红旗铁案维持**（总纲 §K3：代码零借鉴，除非用户改判）；设计思想借鉴合法且经转述。
- 维护：master 最新 2026-08-31 仍在维护（v6.2.1 只修致命 bug，v8 开发中，README.md:20-24）——头部仓活跃度可信。
- 密钥：api_client 走环境变量/配置（云端 key 不落代码）；无硬编码凭据命中。
- 红旗：GPL 为唯一红旗；工程质量本身是 16 仓最高梯队（测试 37%+hook 防护+schema 版本化）。

## §5 与 CBB 对照（Step 0 三条件 + 四契约/三态）

**三条件对照**：
1. **元文本防御：弱（提示词级）**——placeholder_scanner.py 仅扫设定文件占位符（`[待*]`/（暂名），:16-19）+写前闸阻断；正文元叙述仅 prompt 参考（style-adapter.md:49"不做元叙述"）；**无程序化正文扫描**——R6 独有性+1（头部仓亦缺位，反向证明该坑无现成解）。
2. **时间归一：无**——chapter 主轴+time_hint 自由文本（schemas.py:66-73）；仅章节字段归一（planted/target/resolved_chapter）与 urgency 数值归一——cbb-anchor 仍独有。
3. **实体/事件去重：多层、约束式**——事件 event_id UNIQUE+INSERT OR IGNORE（幂等，event_log_store.py:115,132）+事件名别名归一；实体三 UNIQUE 约束+current_json 字段级合并；记忆 category 键去重+冲突检测（store.py:183）——**约束式去重的 SQLite 完整实现**（与 oh-story 规则层、neo4j 算法层三方互补）。

**四契约/三态对照**：
- **Record ≈ entities+state_changes+appearances**（confidence+chapter 溯源+追加日志）；
- **Issue ≈ invalid_facts 表+prewrite_validator**（写前闸）；
- **Verdict ≈ urgency 状态分档+memory 四态**（contradicted≈quarantine、tentative≈draft、outdated≈stale（story-systems 同族））；
- **Case ≈ review_metrics/writing_checklist_scores**（章级评审留痕）；
- **三态映射**：memory 四态+urgency 三档+is_archived——**状态语义在库表层的多实例**；CBB 三态仍是最小完备集，四态中 contradicted 是否并入 quarantine 移交 U-A17。

**金标方法学（§K2）**：有 evals/ 目录（README :71 learn 命令族）但为产品自用，无公开精度宣称——不收编。

## §6 处置建议

**四选一：只读参考（GPL 铁案）**——理由：
1. GPL-3.0 决定代码零接触（铁案维持，除非用户改判）；**不装外挂、不复制任何 SQL/代码**。
2. 设计价值极高（§3 十条，尤其时序回放/UNIQUE 约束族/urgency 公式/时间闸四件是 CBB store 层的直接设计输入），全部经本报告转述吸收。
3. 定位：**域内工程完成度最高的同类系统**（中文网文一致性），其"三库分立+事件投影+hook 防护"架构是 CBB 的对照组；其短板（字符预算/无时间归一/记忆未入库/云依赖）恰是 CBB 差异化清单。

移交 U-A17 吸收项：①state_changes 时序回放（任意章快照，章号轴 SQL 范式）②UNIQUE 约束族（aliases 复合 PK/关系三元组唯一/出场唯一）③confidence 入库+装配过滤 ④urgency 公式（三层级 3.0/2.0/1.0+进度比+三档+前 3 条注入）⑤memory 四态对照（contradicted 并入 quarantine 裁决题）⑥检索 chapter 时间闸防剧透 ⑦PreToolUse 保护+命令白名单+绕过拦截+commit sanitize ⑧schema_version+迁移备份 ⑨RRF+BM25 参数（重写不照抄）⑩三层级语义注释风格。**GPL 合规提示：CBB 实现时按设计重写，不引用其源码文件；本文档为唯一转述层。**
