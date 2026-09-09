> [v3 语境适配页（bootstrap_v3 安装器注入，v3.5/J-008a）] 本文件写于 v2.x 语境。v3 库等价物：审计链=audit/lifelog-*.md（engine 自动入链，无需手动 lifelog_append）；变更账本=ledger/changes.jsonl；变异守卫=guard 子命令（基准黑名单+锚定）；条目写入=engine append（schema 十字段）；检索=engine retrieve；state/ 目录对应 state.json 与 memory/。v2.x 原文路径按需参考，冲突处以本页与 spec.md 为准。

# SOTA 记忆架构雷达 · 精简版

> 升级本库前先扫一眼：想上的机制是否已有、属于哪派、触发条件到了没。
> 完整谱系（21 条目）见 library-bootstrap 源工作区 knowledge/references/sota-memory-radar.md。

## 七派一句话
1. **分层记忆 OS**（MemGPT/MemOS/MemoryOS）：主上下文+外部存储分层，记忆为一等资源。
2. **管线抽取**（Mem0/Memory-R1/MemInsight）：抽取→整合→双写，RL 可训记忆管理器。
3. **图/联想检索**（HippoRAG/Zep/G-Memory）：扩散激活、时序知识图谱、多 Agent 图。
4. **认知架构/反思**（CoALA/Generative Agents/A-MEM/Reflexion）：记忆分类学+反思合成+记忆演化。
5. **生物启发/遗忘**（MemoryBank/LightMem/Sleep-time）：遗忘曲线、睡眠时整理。
6. **长上下文压缩**（MemAgent）：固定记忆分页处理超长流。
7. **产品实践**（Letta/OpenClaw/Anthropic/Manus）：memory blocks、SOUL 文件、客户端记忆、KV-cache 优先。

## 重评触发器（命中再升级，不提前）
- 条目总数 > 100 → 重评向量检索（2/3 派）
- 多 Agent 协作 → 重评 G-Memory、MemOS 调度
- 百万 token 长文档任务 → 重评 MemAgent、MemoryOS 页调度
- 每季度 → 搜索最新综述扫一遍新范式
