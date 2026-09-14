# Step 0 施工工单（投喂给构建对话用 · 自包含）

> 把本文件全文粘贴给构建对话即可开工。工单已合并：实验设计（P1 计划书第二节）+ 社区情报修订（step0-社区实测情报.md）+ 环境事实 + 红线。构建对话无需任何前置上下文。

---

## 任务一句话

验证 Graphiti（`pip install graphiti-core`）对**中文小说文本**的实体/关系/时间抽取是否达到可用精度，产出三柴油账数字，判定 L0-L2 地基走 Graphiti 还是自研。这是可行性实验，只出一个决策信号，不建任何生产代码。

## 已知环境（审核线 2026-09-14 实测，直接用，勿重复勘探）

| 项 | 事实 |
|---|---|
| 语料 | `D:\zcode专用！！！！危险！！！！！！！！！\语料分析\corpus\clean_full.txt`（15,916,773 字节，UTF-8） |
| 章节标记 | `<<<CHAPTER NNNN | 标题 >>>`；CHAPTER 0001 是"新人观众推荐事先阅读本文"（作者杂物，作序章型材料） |
| LLM 通道 | **两梯级**：Tier 1（先行）=审核线子代理直接执行 graphiti 真实提示词做抽取（GLM 系模型，零端点依赖）；Tier 2（本工单主体）=构建线跑**原装 add_episode**，LLM **定案云 API=DeepSeek**——端点 `https://api.deepseek.com`（OpenAI 兼容，`/v1` 可用），模型 `deepseek-chat` 起步（`deepseek-reasoner` 备用，抽取无需思维链）；注意 graphiti 结构化输出需走其 JSON-schema fallback 分支（DeepSeek 支持 response_format=json_object）。key 由用户向构建对话提供，**不入任何文件**。本地 LM Studio（`tifa-deepsex-14b-cot-chat`/`hermes3.6-35b-a3b-*`）为对照变量；`m-prometheus-14b.i1` 是评分器，禁止用作抽取 |
| Embedding（已定案并实测✅） | 本地 Qwen3-Embedding-8B GGUF **Q8**。2026-09-14 实测：精确 ID `text-embedding-qwen3-embedding-8b@q8_0`，**维度 4096**，端点 `http://127.0.0.1:8080/v1/embeddings` 正常出向量；同库另有 `@q4_k_m` 备胎。`qwen3-reranker-4b` 亦已加载，但 LM Studio 无 `/v1/rerank` 端点（P2 检索层用 llama-server 方案，见情报文件§五） |
| 图库 | Docker 29.6.2 已装但 **daemon 未运行**（需先启动 Docker Desktop）；备选 FalkorDB 容器。Kuzu 后端上游已弃用，别用 |
| Python | `py` = 3.14.7；uv 有 3.12.14。graphiti-core 要求 ≥3.10 → **建议 `uv venv` 开 3.12 虚拟环境** |
| 网络 | pip 无镜像配置；Tier 2 抽取走云 API（用户侧提供凭据），Embedding 定案走本地 |

## 执行步骤

**阶段 A · 1 章最小验证（先跑这个）**
1. 从语料选 1 章对话密集的中篇幅章（自看标题抽一章），切 3-5k token，存 `材料/` 并记录 CHAPTER 编号+字节偏移+sha256
2. 起 Neo4j（Docker）→ `uv` 3.12 环境 `pip install graphiti-core` → 配 OpenAI 兼容客户端指向**用户指定的云 API 端点**（模型名+base_url+temperature=0；本地 LM Studio 仅作对照变量时才启用）
3. embedding：LLM 上云后本地显存全空——本地加载 Qwen3-Embedding（8B/4B/0.6B 按需）或直接用云 embedding 均可；用随机向量 stub 则必须**在报告显式声明**（影响去重、不影响单章抽取测量）
4. `add_episode` 喂入，导出全部节点+边（JSON）
5. **第一眼判定（定性，出结论 A）**：实体名是否保持中文（语言漂移检查）？fact 句子通不通？实体/关系量级是否合理？——崩了（比如 fact 全变英文、实体全是乱码）当场停，写报告证伪；能用 → 进阶段 C

**阶段 B · 补满 4 章 + 金标对账（A 通过后）**
6. 再切 2 章对话密集 + 1 章低密度（序章型用 CHAPTER 0001 节选），全部 `add_episode`
7. 金标：等审核线（另一对话）对同一切样出的金标 JSON，放 `金标/`（若审核线金标未就绪，可先自标初稿，但须标注"构建线自标，待审核线复核"）
8. 写对账脚本算四个数：实体 precision / recall（匹配规则：精确+包含+别名，逐例可查）、关系方向正确率（头尾实体+关系三对齐）、时间表述可用率；输出原始 TP/FP/FN

**判定线（业务口径，不许事后调）**：实体 P≥0.85 且 R≥0.70 ｜ 关系方向≥0.80 ｜ 时间≥0.60。
**结论三分支**：全过→P2 走 Graphiti 地基；仅时间不过→时间归一化自研（cbb-anchor）；崩线→自研抽取+轻存储。

## 已知雷区（出问题先对表，别误判"中文不行"）

1. `extract_edges` **硬编码 max_tokens=16384**：模型 token 预算小于此会截断报错——遇到先降 chunk 大小，并在报告记录
2. OpenAI 兼容客户端+本地模型**输出不稳定**（社区有 vllm 案例）：temperature=0、失败重试、抽样人工看原始返回
3. 节点去重只靠 embedding 相似度：多章之间转写名/昵称漏合并是已知行为，记录即可（这正是 CBB 要自建的部分）
4. BM25 全文检索 CJK 分词缺口：只影响检索不影响抽取，记入报告"P2 风险"节

## 交付物（五件套，落 `P1执行区/step0-抽取精度实验/`）

材料/（切样+溯源信息）｜金标/（JSON）｜脚本/（可一键复现）｜结果/（图导出 JSON+指标表含 TP/FP/FN）｜报告.md（**必须披露**：抽取模型名、embedding 方案、图后端、temperature、四个指标、结论分支、雷区对表情况）

## 红线

- API 密钥**不入任何文件**：key 由用户自行注入（环境变量或对话内提供），报告只写模型名与端点形态，绝不写 key 字面量（D-004）
- 只装 graphiti-core 及其依赖；**不安装** 16 个参考仓的任何技能
- 语料源文件只读（大小/时间戳不可变）
- 完成后通知用户，审核线按轻量档出判定（只卡：指标无事后调线、结论按三分支、密钥合规）
