# Step 0 社区实测情报（审核线 → 构建线）

> **结论先行**：社区**没有**可直接引用的"中文文本实体抽取 P/R"级定量实测——本地 Step 0 不能免做；但主源（graphiti 源码）+ GitHub issues 情报足以**把实验瘦身一半、并预标三个最可能翻车的点**。调研日期 2026-09-14。

## 一、检索覆盖与所获

| 渠道 | 所获 | 空白 |
|---|---|---|
| graphiti 源码亲查（31k★ main） | 无自带 benchmark；抽取提示词**强制 fact 保留原文专有名词**、去重**保留原名**，但**无"以原文语言输出"硬指令**；Python ≥3.10；Neo4j 驱动为核心依赖，Kuzu 后端已弃用 | 语言输出行为只能实测 |
| 中文社区（知乎/CSDN/博客园/掘金） | [知乎技术调研](https://zhuanlan.zhihu.com/p/1934705795024552027)（评测的是**节点更新与查询**，非抽取精度）、[博客园 Graphiti+MCP 实战部署](https://www.cnblogs.com/treasury-manager/p/19718069)、[CSDN 原理文](https://blog.csdn.net/m0_59164520/article/details/147594803) | **中文抽取精度定量实测：零篇** |
| GitHub issues（API 检索） | CJK 支持史 + 本地模型雷区（见下） | 无中文小说域案例 |

官方 paper（arXiv 2501.13956）的基准为英文数据集；有社区 issue 明确呼吁"标准化检索质量基准"尚无着落——全网确实没有可抄的数。

## 二、GitHub issues 情报（对 Step 0 直接有用）

**CJK 支持现状 = "踩过坑、修了一部分"：**
- ✅ 已修：非 ASCII 序列化 saga 收敛（`ensure_ascii` 默认 False）；MinHash 模糊去重的 CJK 字符 bug 已修 → 中文**能跑**
- ⚠️ 仍开：BM25 全文检索的 CJK 分词缺口（韩语词元分析 RFC 开放中，中文同病）——**不影响抽取精度实验，但 P2 检索层记入风险清单**
- ⚠️ "Multi-language support" 为开放议题：语言行为依赖所用模型

**本地弱模型是已知雷区（正中我们 LM Studio 14B 路线）：**
1. `extract_edges` **硬编码 max_tokens=16384**，覆盖模型真实预算 → 小预算模型输出截断、报无消息异常——Step 0 首要观察项
2. **OpenAIGenericClient + 本地服务（vllm gpt-oss-20b 案）输出不稳定**——我们走 LM Studio OpenAI 兼容端点正是同族路径
3. **节点去重只靠 embedding 相似度**，低于余弦阈值的精确重名会漏——迷深人名别名（转写名/昵称/称号）正是靶心
4. `LLMClient.generate_response` 存在 message 复用导致的 language instruction 堆叠问题（已修 PR 在案）

**可利用的钩子**：`custom_extraction_instructions` 已暴露——第二轮实验可注入"中文小说领域指令"与基线对比，这是免费的提精度手段。

## 三、对 Step 0 实验设计的修订建议（供构建线采纳）

1. **瘦身**：4 章 × 全指标 → **先 1 章最小验证**（跑通全链 + 第一眼质量量级）；质量即崩（如 fact 整句漂英文）当场证伪；接近可用再补满 4 章出正式数。省约一半工时。
2. **新增检测项**：fact/实体名的**语言漂移**（源码无语言硬指令 + 社区 Multi-language 议题开放 → 弱模型下高风险）。
3. **预标雷区清单**（出问题时不误判为"中文不行"）：max_tokens 截断 / 本地客户端输出不稳定 / dedup 漏别名 / CJK 分词缺口（仅检索层）。
4. **判定线不变**：P≥0.85 / R≥0.70 / 方向≥0.80 / 时间≥0.60 仍是业务口径，社区无数据可对表——这正是本地实验不可免的理由。
5. 模型信息强制披露（审核单附注已含）：社区全用强云模型，本地 14B 级结果只会更低——社区证据=上界参考。

## 四、检索留痕

- WebSearch×2（中文社区）+ GitHub API issues 检索×3（chinese / multilingual+language / extraction quality）；Z.ai 搜索后端一度 429，GitHub API 通道正常
- 源码查证对象：/tmp/refcheck/graphiti（main，depth 1）
- 相关审核工件：`step0-验收审核单.md`（轻量档：D4/D5/E1 门禁 + 模型披露附注）

## 五、补充（2026-09-14 晚）：Reranker 与 API 路线的查证结论

1. **用户手上有 Qwen3-Reranker-4B-q4_k_m**：对应 graphiti 的 cross_encoder 槽位，**仅查询期重排用，Step 0 抽取阶段完全用不上**。部署注意（已查证）：LM Studio **无原生 `/v1/rerank` 端点**（Cherry Studio #7167、RAGFlow #8116 双确认），reranker 加载进 LM Studio 也无法直用；可用路径 = llama.cpp `llama-server`（已原生支持 Qwen3-Reranker + /v1/rerank，注意 `pooling=rank` 近零分坑，参考 VooDisss gist）+ 为 graphiti 写自定义 CrossEncoderClient adapter。→ **记入 P2 检索层待办，Step 0 不碰。**
2. **云 API LLM 路线**：~~迷深为 R18 语料，有内容审核拦截风险，维持纯本地~~ **【2026-09-14 勘误：此论证被用户事实双重证伪】** ①迷深**不是** R18（用户裁决；审核线抽查计数佐证：四类明确敏感词 0 命中）——原判断系审核线从无关线索（本地装有无审查 RP 模型 + 序章"痴汉"字样）错误拼图；②**用户的迷深清洗实践一贯用云 API**——"云审核会拦"的担忧被操作史直接证伪。修订结论：**Step 0 抽取 LLM 主线改走云 API**（用户既有实践 = 未来部署形态，代表性更好；模型质量断代更强），本地 LM Studio 降为对照/备选；LLM 上云后本地显存全空，8B embedding 可自由部署。施工工单已同步修订。
