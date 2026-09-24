# 调研报告 · GraphRAG / LightRAG / LLM wiki 与同类技术：全景与取舍

- **日期**：2026-09-25
- **方法**：五路并行网络调研（GraphRAG 一手源深查 / "LLM wiki" 词义辨析 / 生产实践与反例 / 图 RAG 赛道全景 / 记忆与知识库赛道全景）。论文经 arXiv 页面直读，星标经 GitHub API 实查（2026-09-24/25），官方数字经原文核对。
- **核实口径**：凡查无一手来源的数字一律标【未核实】或【推算】；本报告不背书任何单一美元数字（见 §6.4"成本口径陷阱"）。

---

## 一、问题定义：这些技术都在答同一道题的三个切面

| 失效模式 | 含义 | 对应药方 |
|---|---|---|
| 上下文装不下 | 语料 >> 窗口，且全局性问题本质是摘要任务不是检索任务（arXiv:2404.16130 原话） | 结构化：图 / 树 / 页面 / 摘要层级 |
| 知识会演化 | 事实随剧情/时间失效，"作者吃设定" | 时序化：双时序图、失效不删除、增量更新 |
| 生成不可信 | 答案看着合理但没有出处支撑 | 纪律化：证据绑定、引文回落、弃答 |

---

## 二、GraphRAG（微软）：用索引期的钱买查询期的全局视野

**机制**：语料切 TextUnit（默认 1200 token）→ LLM 抽实体/关系/声明（claims 默认关）→ **Hierarchical Leiden** 层次社区检测（官方确认非 Louvain）→ 逐社区生成社区报告。查询四模式：**global**（全部社区报告 map-reduce，官方自称 resource-intensive）、**local**（实体向邻居扇出+原文块）、**DRIFT**（primer→follow-up→排序层级）、**basic**（等价普通向量检索）。

**评估方法**（论文）：Comprehensiveness / Diversity / Empowerment 三指标 + Directness 控制项，LLM judge 头对头、每对比较 5 次取平均、125 题。全局方法 comprehensiveness 胜率 72–83%（p<.001）；C0 层对向量 RAG 保持 72%/62% 胜率。

**官方承认的局限**：README"索引是昂贵操作，从小规模开始"；仓库已进入**维护模式**（不再接新 PR）；微软自家 GraphRAG accelerator 已 archived（2025-05）。

## 三、LightRAG：把 GraphRAG 的预付款砍掉

**机制三差异**（arXiv:2410.05779）：① 索引期只建实体关系图+向量表示，**不为社区预生成报告**；② 检索用**双层关键词**——低层（具体实体/属性）+ 高层（抽象概念/主题）各一路再融合；③ 自带**增量更新算法**。

**成本自述**（竞品论文口径，注意立场）：legal 语料检索 **<100 token + 1 次调用** vs GraphRAG **约 61 万 token + 数百次调用**；GraphRAG 增量更新需约 1399 万 token 重建社区报告，LightRAG 只付抽取开销。

## 四、"LLM wiki"词义辨析（先正名再讨论）

- arXiv 全库检索 `"LLM wiki"` **0 命中**——不是学术术语。
- **主含义**（2026-04 起压倒性用法）：Karpathy 的 gist《LLM Wiki》（2026-04-04）——`raw/`（不可变真源）+ `wiki/`（LLM 生成维护的互链 markdown 页）+ schema（CLAUDE.md/AGENTS.md）；操作 = Ingest / Query / Lint；理念 = **摄入时编译一次并持续保鲜**，自我定位明确对立于 RAG（点名 NotebookLM）。金句："Obsidian 是 IDE，LLM 是程序员，wiki 是代码库。" 反驳（HN 高赞）："This is just RAG，只是没用量化库。"
- **同名不同物**：DeepWiki / Google Code Wiki（2025-05 起，代码→文档站，早于主含义一年）；WikiChat / WikiRAG（Wikipedia 作语料）；A-MEM（arXiv:2502.12110，Zettelkasten 互链记忆，学术上最接近"wiki 形态记忆"的正式工作）。

## 五、全景族谱

**检索侧五族**：

| 族 | 共同思想 | 代表（星标=GitHub 实查） |
|---|---|---|
| 摘要层级族 | 聚类→摘要→再聚类 | RAPTOR（arXiv:2401.18059，QuALITY +20%；官方仓库两年未动，思想被广泛吸收）；GraphRAG 社区摘要同思想 |
| 图上扩散族 | 检索=图上算法遍历，结构替代多轮 LLM 迭代 | HippoRAG 2（arXiv:2502.14802，ICML'25，PPR 扩散+段落节点；多跳超 SOTA 至 +20%，比 IRCoT 便宜 10–30 倍）；G-Retriever（Steiner 树取子图，另一问题设定）；PropRAG（EMNLP'25，命题路径 beam search；具体数字仅二手【未核实】） |
| 低成本图索引族 | 廉价替身逼近全量建图 | KET-RAG（arXiv:2502.09304：LLM 只处理 PageRank 选出的关键 chunk 建"骨架图"，其余用文本-关键词二部图；索引成本降超一个数量级）；fast-graphrag / nano-graphrag 为工程复刻，均停更约一年 |
| 检索决策族 | 不改索引，改"何时检索、信不信结果" | Self-RAG（反思令牌）、CRAG（评估器→改写重检/转网络搜索）、Adaptive-RAG（按复杂度路由）——与图路线**正交** |
| 上下文增强族 | 索引前注入情境 | Anthropic Contextual Retrieval（Haiku 生成 50–100 token 前缀；官方：失败率 5.7%→嵌入+BM25+重排后 1.9%，降 67%） |

另：**KAG**（蚂蚁，arXiv:2409.13731，9,074★）：KG 与原文 chunk 互索引 + 逻辑形式混合推理，2wiki F1 +19.6% / HotpotQA +33.5%；工业推理导向。框架层：LlamaIndex PropertyGraphIndex（编排层）、Neo4j graphrag-python / llm-graph-builder、FalkorDB GraphRAG-SDK（**MENTIONED_IN 溯源边 + 证据不足弃答**）。

**记忆侧五族**：分页上下文族（MemGPT/Letta 24,868★、MemOS）；抽取-操作族（Mem0 65,947★：ADD/UPDATE/DELETE/NOOP）；时序图族（Zep/Graphiti 31,130★ 双时序、cognee 30,962★、WeKnora 29,678★ 可回滚 wiki）；互链页面族（A-MEM）；文件即记忆族（Manus"file system is the ultimate context"、Claude Code auto memory）。

## 六、证据与反例（取舍的依据）

### 6.1 增益窄：图方法不是普遍更好
- **GraphRAG-Bench**（arXiv:2506.02404，700 万词/1018 题/16 学科）：最佳图方法 73.58 vs TF-IDF 71.71——**仅 +1.9pp**；多选题/判断题上**输给不检索的 LLM 基线**；原话"除非检索高度准确，否则 GraphRAG 收益有限"。
- **RAG vs GraphRAG 系统评估**（arXiv:2502.11371）：NQ 上 RAG F1 64.78 vs GraphRAG-Global 54.48；**但** MultiHop-RAG 上 Local 版 69.01 反超 67.02。构建耗时 135s vs 5,560–7,702s。
- 结论：**图方法只在多跳/全局摘要类问题上成立；单点事实题上朴素检索经常更好。**

### 6.2 瓶颈在推理端
arXiv:2603.14045：多跳 QA 中 **77%–91% 的金答案已在检索上下文里，准确率只有 35%–78%**；73%–84% 的错误是推理失败。→ 检索架构继续加码的边际收益递减。

### 6.3 记忆赛道基准危机（对"花哨架构"的整体冷水）
- LOCOMO 仅 10 段对话/约 26k token，饱和且各家口径不可比。
- **Mem0 自己论文 Table 2：full-context 72.90% > Mem0g 68.44% > Mem0 66.88%**；营销页宣称 92.5 与论文脱节。
- Zep/Mem0 互相揭短（Zep 博客《Lies, Damn Lies, & Statistics》；Mem0 反击复现 Zep 仅 58.44%）——至今各执一词。
- **Letta 文件系统实验**：不建记忆架构，文件+grep/open 工具，LOCOMO **74.0%** > Mem0g 68.5%——agent 能力比记忆工具重要。

### 6.4 成本口径陷阱（引用任何数字前先问配置）
- 微软官方论文/博客**零美元数字**。唯一"同语料+同系统+公开美元"锚点：5.64MB（≈127 万 token）索引 **$2.30–$24.94**，11 倍差**完全来自未披露的 chunk 配置**（arXiv:2502.09304 / 审计 arXiv:2608.16096）。
- 标准化 $/MB：HippoRAG-2 $0.28；GraphRAG 低配 $0.41 / 高配 $4.42；KET-RAG $0.34；Text-RAG（纯向量）$0.02 量级。
- 官方 LazyGraphRAG 博客：索引成本=向量 RAG=**全量 GraphRAG 的 0.1%**，查询成本低 **>700×**（**仅博客一处一手源，无论文交叉验证**）。
- 租 vs 拥有（arXiv:2608.16096）：嵌入成本比图构建低 7.5–900×；一年 10,000 查询/天的回答成本（$361–836）仍比 1TB 建图（外推 $428K–4.6M）低 350× 以上。**查询稀疏时"租"几乎永远便宜。**

### 6.5 可信度实证：没有证据绑定的代价
- Wikipedia 2025 清理：178/3078 篇 AI 生成条目中 **>2/3 "failed verification"**（引用真实来源但来源不支撑句子），仅 7% 伪造来源——失效点在"归属错配"而非"编造来源"。
- NotebookLM 句级幻觉 13% vs ChatGPT/Gemini 约 40%（arXiv:2509.25498）——source-grounding 有效，但错误形态变为"解释性过度自信"。
- 行业收敛信号：FalkorDB SDK 内置溯源边+弃答；Contextual Retrieval 注入情境。**"引文可回落"是还没普及的终态。**

### 6.6 时序图（Graphiti）要点
双时序两轴：**T=事件在现实中何时为真**（t_valid/t_invalid）、**T′=数据摄取顺序**（t'created/t'expired），每事实 4 时间戳；矛盾时旧边**只标记失效不删除**（失效时刻=新事实生效时刻）；检索=语义+BM25+图遍历，不依赖 LLM 摘要。与 GraphRAG 官方对照：静态摘要 vs 持续演化、批处理 vs 增量、基础时间戳 vs 显式双时序。

---

## 七、取舍讨论（本报告核心）

### 7.1 七条取舍轴

1. **问题类型适配**——错配=白花钱。单点事实→朴素 RAG；多跳→图扩散/双层关键词；全局主题→摘要层级（GraphRAG global 的 map-reduce 最对口）；时序演化→双时序图；开放世界→网页搜索（唯一选项）。
2. **成本记账**——租（按查询付）vs 拥有（索引预付）。语料越大、查询越稀疏，越不该预付全量 LLM 索引；预付也要选"骨架"路线（KET-RAG 降一个数量级、LazyGraphRAG 索引期零 LLM）。
3. **增量与演化**——静态语料 GraphRAG 可忍；持续追加则 LightRAG 增量算法 / Graphiti 双时序 / KET-RAG 局部更新，GraphRAG 的社区重建是死穴。
4. **证据绑定**——**默认全都没有**。要"可核验"必须自己建：引文逐字回落 + 落不回即弃答/标未核实。摘要层是有损压缩，审计必须能回落原文。
5. **延迟与规模**——LightRAG/Graphiti 亚秒低 token；GraphRAG global 秒到数十秒、单查可达 61 万 token；HippoRAG 毫秒级图算+一次 LLM。
6. **工程复杂度与依赖**——LightRAG 轻可改；GraphRAG 管线重且维护模式；HippoRAG 要图库；Agentic/Contextual 路线零索引结构改动。
7. **可复算性**（审计视角）——LLM 抽取层对提示词高度敏感（微软 auto-tuning 博客：同语料实体 1,796→4,896、关系 2,851→8,210、社区 352→1,027），换 prompt=换仪器；judge 也脆（跨嵌入器 self-kappa 0.137，arXiv:2608.00705）。凡进审计链的检索面，配置必须入档。

### 7.2 GraphRAG vs LightRAG 正面对决

| 维度 | GraphRAG | LightRAG |
|---|---|---|
| 全局主题题 | **对口**（社区报告 map-reduce 为此设计；论文胜率 72–83%） | 高层关键词路是代理品，摘要概括力弱一档 |
| 多跳/局部题 | local 可用但重 | **对口**（双层关键词+图，检索 <100 token） |
| 索引成本 | 高（$0.41–4.42/MB；且 prompt 敏感） | 低（无社区预摘要） |
| 增量更新 | 差（重建社区报告 ≈ 千万 token 级） | **好**（增量算法） |
| 查询成本 | global 61 万 token/次量级 | <100 token/次 |
| 工程与维护 | 重管线，官方维护模式 | 轻，可自改 |
| 适用判据 | 静态语料+全局题占比高+预算足 | 其余绝大多数场景 |

**判定**：LightRAG 是"GraphRAG 思想的记账优化版"，在 90% 的现实场景（持续增长的语料、混合问题分布、预算有限）是更优默认；GraphRAG 的社区摘要层只有在"全局主题问题成为主要负载"时才值回票价——而这恰应该用触发器门控（见 §8）。

### 7.3 决策树（文字版）

```
语料封闭吗？
├─ 否（开放世界/时效信息）→ 网页搜索/agentic search + 逐条核验（没有别的选项）
└─ 是 ↓
   问题分布里有"全局主题"类问题吗？
   ├─ 没有 → 别建摘要层。向量+FTS(+重排) 足够；图方法在单点题上不赚（GraphRAG-Bench）
   └─ 有 ↓
      语料持续增长吗？
      ├─ 是 → LazyGraphRAG/KET-RAG 思路：索引期不付/少付 LLM 钱，社区摘要按需生成
      └─ 否（已冻结）→ 可考虑全量建图；但仍先算 $/MB 与查询频率的回收期
   多跳关系题占比高吗？高 → 图上扩散族（HippoRAG 2）或双层关键词（LightRAG）
   知识持续演化且要时间推理？→ 双时序图（Graphiti 式），失效不删除
   无论选谁：证据绑定自己建（引文逐字回落 + 弃答），否则 6.5 的实证代价照单全收
```

### 7.4 反面清单（何时不要用图 RAG）

- 语料 < 10 万 token：直接全塞上下文——Mem0 论文里 full-context 自己赢了自己的图变体（72.90 vs 68.44）；Letta 文件+grep 74.0%。
- 问题分布以单点事实为主（GraphRAG-Bench：多选/判断题输基线）。
- 查询稀疏（租几乎永远便宜：年 10k 查询/天 $361–836 vs 1TB 建图外推 $428K+）。
- 无人力治理抽取提示词质量，或无人审计图质量（实体数对 prompt 敏感 3 倍）。
- 需要"每个答案可核验"而方案不提供逐字回落——先补绑定再上图。

---

## 八、对 CBB 的映射与建议

| # | 建议 | 依据 |
|---|---|---|
| 1 | 四路召回已"半 LightRAG 化"（别名精确=低层实体、关键词 bigram=文本路、图扩展=结构路）；**补一层"主题词"路**（抽象概念维，按章标注，零 LLM 成本） | §3 双层关键词 |
| 2 | 全局问题维持**哨兵 A 门控**；触发后走**骨架图路线**：社区检测是纯图算法零 LLM，仅"社区摘要生成"按需付 LLM 钱 | §6.4 / §7.2 / LazyGraphRAG+KET-RAG |
| 3 | **不引入** Agentic RAG 框架——G2 证据门≈CRAG、哨兵≈Adaptive-RAG、落不回标未核实≈弃答，机制等价物已在 | §5 检索决策族 |
| 4 | Contextual Retrieval 记为**可选实验**：evidence 行本就带章节坐标，118,189 行已建，边际收益存疑，按需再试 | §5 上下文增强族 |
| 5 | **推理优先**：投判卷/双独立复查/SPRT，不追加检索花活——77–91% 金答案已在上下文 | §6.2 |
| 6 | wiki 形态=**导出视图**（人物册/设定页，带引文脚注、可重建、派生件纪律），绝不做第二真源 | §4 / WeKnora 可回滚 wiki |
| 7 | Graphiti 双时序已在 L4——保持，不换 | §6.6 |
| 8 | 任何检索面配置（嵌入档/rerank/图参数）随仪器指纹入档——LLM 抽取对 prompt 敏感 3 倍，换配置=换仪器 | §7.1 轴 7 |

## 九、主要来源

- GraphRAG 论文 https://arxiv.org/abs/2404.16130 ；官方文档 https://microsoft.github.io/graphrag/ ；LazyGraphRAG 博客 https://www.microsoft.com/en-us/research/blog/lazygraphrag-setting-a-new-standard-for-quality-and-cost/ ；动态社区选择 https://www.microsoft.com/en-us/research/blog/graphrag-improving-global-search-via-dynamic-community-selection/
- LightRAG https://arxiv.org/abs/2410.05779 ；HippoRAG https://arxiv.org/abs/2405.14831 / 2 https://arxiv.org/abs/2502.14802 ；RAPTOR https://arxiv.org/abs/2401.18059 ；KET-RAG https://arxiv.org/abs/2502.09304 ；PropRAG https://arxiv.org/abs/2504.18070 ；KAG https://arxiv.org/abs/2409.13731 ；G-Retriever https://arxiv.org/abs/2402.07630 ；DALK（正号 2405.04819，二手常误标为 KAG 的 2409.13731）
- Self-RAG https://arxiv.org/abs/2310.11511 ；CRAG https://arxiv.org/abs/2401.15884 ；Adaptive-RAG https://arxiv.org/abs/2403.14403 ；Contextual Retrieval https://www.anthropic.com/news/contextual-retrieval
- 反例：GraphRAG-Bench https://arxiv.org/html/2506.02404v1 ；RAG vs GraphRAG https://arxiv.org/html/2502.11371v3 ；推理瓶颈 https://arxiv.org/abs/2603.14045 ；成本审计 https://arxiv.org/html/2608.16096v1 ；judge 脆弱性 https://arxiv.org/abs/2608.00705
- 记忆：Mem0 https://arxiv.org/abs/2504.19413 ；Zep https://arxiv.org/abs/2501.13956 ；A-MEM https://arxiv.org/abs/2502.12110 ；MemOS https://arxiv.org/abs/2507.03724 ；MIRIX https://arxiv.org/abs/2507.07957 ；Sleep-time Compute https://arxiv.org/abs/2504.13171 ；Letta 基准 https://www.letta.com/blog/benchmarking-ai-agent-memory ；Zep 批 Mem0 https://blog.getzep.com/lies-damn-lies-statistics-is-mem0-really-sota-in-agent-memory/
- LLM wiki：Karpathy gist https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f ；HN 讨论 https://news.ycombinator.com/item?id=47640875 ；DeepWiki https://cognition.ai/blog/deepwiki
- 可信度：Wikipedia 清理 https://wikiedu.org/blog/2026/01/29/generative-ai-and-wikipedia-editing-what-we-learned-in-2025/ ；Not Wrong But Untrue https://arxiv.org/abs/2509.25498

## 十、核实缺口与【待确认】

1. 全量 GraphRAG 索引的**官方美元成本不存在**；一切金额均为第三方实测或外推。
2. LazyGraphRAG 三个数字（0.1% / >700× / 4%）仅博客一手源，无论文；主仓库未确认完整落地。
3. PropRAG 的具体 Recall@5 只在二手页；DALK 的 arXiv 号二手普遍误标。
4. 微软 Tech Community《GraphRAG Costs Explained》返回 403，未引用。
5. WeKnora 未见论文；Claude 消费级记忆套餐门槛未核实到官方全文。
6. 各 GitHub 星标为 2026-09-24/25 实查值，会漂移。
