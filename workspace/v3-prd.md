# PRD · library-bootstrap v3.0 重构（路线 B：v3 直接上位）

> 版本：v1.0 ｜ 日期：2026-09-06 ｜ 状态：待用户批准（PRD-driven：批准前不动代码）
> 载体：以用户提供的 `bootstrap_v3.py`（v3.0.0 单文件统合版）为骨架。
> 路线裁决（用户 2026-09-06 拍板）：v3 直接上位，**不再执行 v2.1.3/v2.1.4 工单的 v2.x 文书修复波次**；四轮审查的机制层条目由 v3 架构吸收，逐条对账见第 4 节。

---

## 1. 目标与不目标

**目标**
1. `bootstrap_v3.py` 成为 library-bootstrap v3.0 的唯一分发物（代码 1 文件 + `bootstrap_data/` 内容体），包自哈希即锚点（公理 E）。
2. 修复骨架文件中的全部已知 bug（第 2 节 BR 清单），run-tests 全绿。
3. absorb 成功从本工作区 v2.x 源树机械抽取内容体，verify 对 arXiv API 逐条对账留痕。
4. v2.x 资产妥善冻结：源树与四包保留不删（铁律 1），标注 legacy；`migrate` 支持存量库续链。

**不目标**
- 不重生成 v2.x 说明书（v2.1 版即 v2.x 终版历史件）。
- 不新增 L10+ 档位、不改 SCHEMA_V3 八字段定稿。
- 不把 referee 做成代码（单文件边界诚实声明：referee 以提示词形态随内容体分发）。

## 2. Bug 修复需求（BR，全部必须有回归断言）

| # | 缺陷 | 修复 | 验收 |
|---|------|------|------|
| BR-1 | `cmd_migrate` glob `lifelog-*.md` 匹配不上 v2.x 存量链 `knowledge/lifelog/YYYY-MM.mdl`，`assert files` 恒死 | glob 双模式兼容：`*.mdl` 与 `lifelog-*.md` 都认，取最新文件末行哈希续链 | 真实 v2.x 链（本工作区或沙盒构造 .mdl 两行链）上 migrate 成功续接，行哈希连续 |
| BR-2 | REGISTRY 编号冲突：2507.21046 误占 A28（v2.x 的 A22），v2.x 的 A28（Manus）丢失 | 恢复 v2.x 编号：A22=Self-Evolving Agents（2507.21046）、A28=Manus（非 arXiv，doc）；absorb-pending 名单同步（A22 移出 pending） | `t_registry_corrected` 扩展：A22.arxiv_id=2507.21046、A28 为 doc 型且不含 arxiv_id |
| BR-3 | `t_dag_cycle_rejected` 恒真：`resolve` 无环检测，测试构造的环不在解析路径上 | `resolve` 实现拓扑排序环检测（发现环即 sys.exit 列出环路径）；测试改为注入 `L2` 可达的真环并断言拒绝 | 构造 m-a↔m-b 环且挂在 L2 依赖链上 → install/resolve 报环；正常档位全通过 |
| BR-4 | 测试用 `Path("/tmp/...")`，原生 Windows Python 解析为盘根 `\tmp` | 全部换 `tempfile.mkdtemp()`（with 清理） | Windows 本机 run-tests 全绿且无盘根残留 |
| BR-5 | A31 Damasio 年份 1996 vs v2.x 1994 不一致 | 定稿：1994（初版 G.P. Putnam's Sons），note 注明 1996 为平装年版 | REGISTRY A31 year=1994 |
| BR-6 | `governance_budget` owner 标「R5 新增」来源悬空（本库 reflections 无此编号洞察） | 来源改标「v3 骨架提案新增，【待确认】」，或补一条 reflection 后再引用 | TUNABLES 无悬空引用 |
| BR-7 | verify 标题匹配按冒号切首段子串匹配过糙，且 A17 title 已知与 API 有差 | 保留报警器定位，但 diff 输出加「人工裁决」字段与建议动作；匹配逻辑改为规范化（大小写/空白/连字符折叠）后包含比较 | 对 14 条有 arxiv_id 的题录 verify 出报告；已知差异全部落 overrides 而非误判 match |

## 3. 数据对账与 absorb 适配

1. **A 编号映射表定稿**（BR-2 一部分）：v3 REGISTRY 以 v2.x 附录 A（A1-A33）为准逐条对齐；A24/A26 为 doc 型。absorb 时据 v2.x 题录行回填 absorb-pending 条目，回填后必须跑 `verify`（对账先行，不许凭记忆改）。
2. **absorb slot 规则适配 v2.x 真实布局**：`experimental-l8/`、`experimental-l9/`、`modules/`、`presets/`、`packs/`、`references/PROMPTS-建库提示词速查.md`、`SKILL.md`——映射规则从「packages/ 与特色关键词」改为按目录前缀显式映射；抽取报告列出全部 slot 与 sha256，人工抽查后冻结。
3. **LEVELS 模块名映射**：骨架的 m-lint/m-search/m-sleep 等与 v2.x 的 m-tools/m-cron 差异，由 absorb 盘点回填 mapping 表（落 `bootstrap_data/level_mapping.json`），install 按真实模块名复制。
4. **TUNABLES 沿用**：broadcast_weights owner（禁挂检索评测）、reflect_trigger 双轨、index_hot_budget 逐出、eval_n 功效口径全部保留（即 v2.x 的 Z-013/Z-015/W-022 纪律在 v3 的落点）。

## 4. 四轮审查条目吸收对账表（v2.1.3 X-001~026 + v2.1.4 M-1~M-10 → v3 处置）

**处置类别**：【吸收】v3 落地即达成，无需另做｜【重表述】在 v3 载体上重新实现｜【冻结】随 v2.x 文书体系冻结而终结（v2.1 说明书为历史终版）。

| 条目 | 内容 | v3 处置 |
|---|---|---|
| X-001 闸门执行机制披露 | sleep_gate 机械执行披露 | 【重表述】sleep-gate 内容体 docstring 自带；spec.md 渲染含闸门段 |
| X-002 DGM 入宪章立法说明 | objective hacking 案例入宪章 | 【吸收】CHARTER_L8 第 3 段已含（术语正确） |
| X-003 A14/A20 题录 + Kang 等 | | 【吸收】REGISTRY A14/A20（+BR-5 年份、BR-2 编号） |
| X-004 断言数统一 + T 定义 | 61 断言文书 | 【冻结+替代】v2.x 61 断言体系冻结；v3 TESTS 自注册为唯一断言账 |
| X-005 双最高法 + 逃生舱 attic | | 【吸收】公理 F + CHARTER 第 1/5 段 + t_escape_pod_wording |
| X-006 A29-A33 补录 | | 【吸收】REGISTRY A29-A33 |
| X-007 断言号闭包 | T 号必须存在 | 【吸收】T 号=函数名自注册，空洞结构性不可能 |
| X-008 题录对账 | arXiv 逐条 diff | 【吸收】cmd_verify（BR-7 升级匹配） |
| X-009 计数单一来源 | | 【吸收】公理 A/B + t_no_handwritten_counts |
| X-010+P-7 变异基准三件套 + SOP 守卫 + 三档声明 | | 【吸收】CHARTER 第 2/4 段 + THREAT_MODEL + bootstrap_data 属人侧；【重表述】L8 守卫行为断言 absorb 后追加 TESTS（骨架声明①） |
| X-011 记忆投毒防线 | 检索结果按数据处理 | 【吸收】engine retrieve 输出投毒防线声明 |
| X-012 锦标赛信号 + 采纳操作化 | 机械判据为主 | 【重表述】usage 记录入 ledger/audit；「实际采纳=执行动作+日志」写入锦标赛内容体（absorb 源） |
| X-013~015 发布前机械检查 + 流程成文 | 工单发现项逐条落地证据 | 【重表述】v3 发布门 = verify + run-tests 全绿 + 包自哈希留痕，写入 PRD 第 6 节发布流程并随 spec 渲染 |
| X-016 七字段 | 实查定改向 | 【冻结+替代】SCHEMA_V3 八字段定稿（JSON 化），字段之争终结 |
| X-017 题注计数 | 五→六条 | 【冻结】文档即产物，无手写题注 |
| X-018 跨月断点 | prev=上月末行 | 【吸收】chain_append 根治形态（BR-1 保 migrate 兼容） |
| X-019+M-6 哈希口径 | 16 hex=64bit 歧义 | 【吸收】公理 E：Merkle 256bit 全长 hex，禁截断 |
| X-020+M-8 context rot 归属 | Chroma/Hong | 【吸收】REGISTRY A25 |
| X-021 议会偏离声明 | 单实例分饰 adaptation | 【重表述】议会/referee 提示词（随内容体）内含偏离声明 |
| X-022 MemAgent 措辞 | 覆写非分页 | 【吸收】REGISTRY A17 note |
| X-023 广播自有评测 | 不挂 W-022 | 【吸收】TUNABLES broadcast_weights owner |
| X-024 索引逐出规则 | 200 行预算配套 | 【吸收】TUNABLES index_hot_budget owner=A14 热度逐出 |
| X-025 7.1 越界引用 | | 【冻结】v2.x 文书 |
| X-026 审计包 | 随包运行日志 | 【重表述】install/verify 自报 pkg_sha256 + Merkle 根 + verify_report.json 即审计包 |
| M-1/M-2/M-3/M-9 交叉引用/void 跳号/计数注入/T-registry | | 【吸收/冻结】T 号自注册使 registry 与 void 概念消失 |
| M-4 七字段实查 | | 【冻结】SCHEMA_V3 定稿 |
| M-5 A33 心境一致性 | | 【吸收】REGISTRY A33 |
| M-7 锚定权限模型 | ③档前提 | 【吸收】THREAT_MODEL 第③段 + 公理 E 人侧抄录 |
| M-10 venue/DOI/仓库消歧 | | 【吸收】REGISTRY A14 字段 |

## 5. TESTS 计划（自注册追加序）

现有 9 条（最小行为集）。absorb 后追加：`t_l8_guards`（三守卫对真实 MUTATION-SOP 内容体跑：触碰基准否决/判据不可见/SOP 条款守卫）、`t_install_l2_smoke`（L2 冒烟安装+Merkle 根稳定）、`t_install_l8_gate`（无 --yes 拒绝、--yes 通过）、`t_migrate_mdl`（BR-1）、`t_absorb_mapping`（slot 全命中、level_mapping 回填完整）、`t_engine_lifecycle`（append 拒坏证/retrieve 投毒声明/wrapup 衰减/shadow 不改状态）。目标 16 条全绿；每条=行为断言非措辞断言。

## 6. 发布形态与流程

1. **发布物**：`bootstrap_v3.py` 单文件 + `bootstrap_data/`（bodies.json、level_mapping.json、registry_overrides.json、verify_report.json）。包锚点 = 文件 sha256，每次命令自报。
2. **发布门（X-013~015 的 v3 形态）**：`verify`（对账报告无不一致）→ `run-tests` 全绿 → 包自哈希写入发布记录。三步缺一不出包。
3. **v2.x 处置**：源树、四包、说明书全部原地保留标注 legacy（铁律 1）；根目录 README 加一行 v3 指引。v2.1.3/v2.1.4 工单标记「由 v3 吸收而关闭」，台账登记。
4. **存量库迁移**：`migrate` 续链（BR-1），条目回填 source_event_id=genesis，parity 门 recall@5 ≥ 基线−0.03。

## 7. 里程碑与验收

| 里程碑 | 内容 | 验收 |
|---|---|---|
| M1 | BR-1~7 修复 + A 编号映射定稿 | run-tests 9/9 绿（BR 断言在内） |
| M2 | absorb 对本工作区 v2.x 跑通 + verify 对账报告 | 抽取报告 slot 全命中；verify 报告留痕 |
| M3 | TESTS 扩至 16 条全绿 | 行为断言，Windows 本机 |
| M4 | L2/L8 冒烟安装 + engine 四操作 + migrate 续链 | 沙盒全通过，Merkle 根人侧留痕 |
| M5 | 发布 v3.0 + 台账 + memory/轨迹登记 | 发布门三步证据齐 |

## 8. 开放问题（批准时可一并裁决，否则按默认执行）

1. 【默认：是】TESTS 追加采用「absorb 后立即补」节奏，还是 M3 集中补？→ 默认 M3 集中。
2. 【默认：1994】A31 年份（BR-5）→ 1994 初版。
3. 【默认：保留】v2.x 四包是否出「deprecated」标注文件放包内？→ 默认在每包根加 DEPRECATED-见-v3.md（新建，不覆盖）。
4. 【待确认】`governance_budget`（元工作上限 0.20）是否保留在 TUNABLES？来源悬空是 BR-6；若保留则本轮补登记一条 reflection。→ 默认保留+补登记。
