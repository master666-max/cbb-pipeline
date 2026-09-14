# task-040 · Tier 2 原装管道验证与 Step 0 收官（2026-09-14）

## 触发
用户「开工」——Tier 1 正式判定后的 Tier 2 原装 `add_episode` 管道验证（审核线获用户授权直接执行实验）。

## Tier 2 配置（三条件落地形态）
- graphiti-core(pip, uv3.12 venv) + Neo4j5(docker 容器 neo4j-step0) + DeepSeek-flash(LLM, base_url api.deepseek.com/v1) + Qwen3-Embedding-8B Q8@LMStudio(4096维) + NoopCrossEncoder(仅入库不检索)
- R6 领域规则经 `add_episode(custom_extraction_instructions=...)` 原生注入
- reference_time = 2000-01-01 + 集序天（叙事伪锚点：保章节序、不冒充真实日期）
- 断点续跑：每集入库前查 Episodic 节点，超时/崩溃可无损续

## 结果
- **4/4 集入库成功**（121s/110s/152s/4s），最终图 **40 实体/66 关系**（对照 Tier 1 八份独立抽取原始 233 边 → 去重合并）
- **三条件逐项验证通过**：①R6 元文本防御（excerpt4 仅 4 秒零元文本入图，对照 Tier 1 双模型全 FP）②伪锚点时序（45/66 边带 valid_at，无墙钟污染）③跨章去重（拉丝缇娅拉/迷宫/弗茨亚茨等跨切样单节点化）
- 实体名抽检与金标高度吻合（缇达/缇亚分立、店长/阳滝/诺文易漏项全在图）

## 调试记录（4 次发射 3 次折）
①cross_encoder 默认构造需 OPENAI_API_KEY → Noop 子类占位 ②续跑检查引用未赋值 driver → 提前赋值 ③属性名实为 self.driver 非 graph_driver → 改用 neo4j 官方驱动自建连接 ④neo4j DateTime 不可 JSON 序列化 → default=str

## 交付
- 报告-Tier1正式判定.md 增补 §六 Tier 2 验证（Step 0 最终判定：Graphiti 路线成立，L0-L2 地基定型，移交构建线进 P1 骨架）
- 结果/tier2/tier2-graph-export.json（全图导出）

## Step 0 收官状态
Phase 完成：金标(4×三轮自审+对抗5轮+终审) → Tier1(8抽取+双口径评分) → Tier2(原装管道三条件验证)。下一步=构建线 P1 骨架开发。
