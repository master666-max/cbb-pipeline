# Decisions · 架构决策记录

> 记录「为什么这样做」，供未来会话理解设计意图，避免重新讨论已定结论。

---

### D-001 / 2026-09-03 / 根工作区归档采用「引用不搬移」（manifest 方式）

- 决策：mepub、语料分析、comfyui-docx-scratch 三个历史项目本体留在原位，archive/2026/09/ 下各放一个 README 记录其位置、复现方式与经验回链。
- 理由：三个项目的当前路径已被外部引用（用户记忆与笔记记录的成品位置、知识库 README 内部相对链接、脚本相对路径），搬移即断链；实验性双库工作区已验证此模式可行（其 D-003）。
- 否决的备选：实体搬移进 archive/2026/09/（需同步改所有引用方，收益为零）。日后若用户要求实体归档，先出移动清单再动。
- 实例：archive/_INDEX.md
- schema_version：3

### D-004 / 2026-09-04 / 六类记忆映射表（MIRIX 对齐）与密钥不入库纪律

- 决策：本库按 MIRIX 六类记忆对齐如下——核心记忆=soul/（SOUL+USER）；情景记忆=knowledge/trajectories/；语义记忆=pitfalls/patterns/reflections；程序记忆=knowledge/skills/；资源记忆=archive/。第六类 Knowledge Vault（加密敏感存储）**不设**，对应纪律：任何 API key、密码、token 一律不入工作区文件。
- 理由：单人单 Agent 场景六类映射天然成立，无需新增目录；Vault 的缺失用纪律补齐，成本低且防泄漏（本工作区曾多次接收用户的 key 报错信息，须防习惯性落盘）。
- 否决的备选：建 secrets/ 目录（引入密钥管理责任，收益为零）。
- 实例：AGENTS.md 铁律第 2 条（密钥不入库）
- schema_version：3

### D-003 / 2026-09-04 / 常驻上下文预算制（Anthropic context engineering 对齐）

- 决策：会话常驻层（SOUL.md + USER.md + _index.md）合计硬预算 ≤150 行；条目正文、skills、archive 一律 just-in-time 按需加载，不进常驻层。检索靠 `tools/search_knowledge.txt` 而非整库阅读。
- 理由：context rot——注意力预算随上下文膨胀衰减，Anthropic 官方实践主张「高信号小集合 + 按需取用」。索引是目录不是正文，保持瘦。
- 否决的备选：全库常驻（小库时代可行，条目过百即劣化）；向量检索（规模不到，D-001 延续）。
- 实例：tools/search_knowledge.txt（扩散激活检索，HippoRAG 2 简化版）
- schema_version：3

### D-002 / 2026-09-03 / 实验性双库工作区原样保留为体系参考，根双库为唯一活跃体系

- 决策：不在实验区上继续记账，也不把它合并进根双库；根目录 AGENTS.md 指向根双库，实验区仅作体系设计参照与 PT-002/PT-004 的另一验证实例。
- 理由：一个工作区只能有一个常驻知识索引，否则每次会话不知道读哪个；实验区价值在于验证过的方法论与文件（建库提示词、方法论 docx），按铁律 1 原样保留。
- 实例：AGENTS.md（根目录会话入口）
- schema_version：3
