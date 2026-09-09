---
name: task-start
description: 开始任何新任务前必须调用。当用户开启新任务、要求分析/写代码/处理数据/写文档时使用。v3：先加载灵魂层，再按 recency/importance/relevance 三因子检索双库，开工前声明规避项与复用项。
---
# 任务启动（v3 · 四步）

0. **加载灵魂**：读 `soul/SOUL.md` 与 `soul/USER.md`，确认本次任务的相处模式与用户偏好（如"先计划书后执行"）。
1. **检索知识库**（v3.1）：先读 `knowledge/_index.md` 掌握全貌，再用 `py -X utf8 tools/search_knowledge.txt 任务关键词…` 精确检索（输出直击★+联想邻居☆），按三因子（recency/importance/relevance）挑条目细读。
2. **读 `archive/_INDEX.md`**，找出可复用 ★★★ 项目作为脚手架候选。
3. **开工前向用户声明**：本次规避哪些坑、复用哪个范式/模板，确认后再动手。

## 执行纪律
- 若索引为空或无相关条目，直接声明「无既有经验可复用」即可开工，不要阻塞。
- 命中的 pitfall 在任务中要主动规避；命中的 pattern 要按其核心步骤执行，并把验证结果反馈给 wrap-up。
- 实验性双库工作区/ 是本体系的参照档案，不作为记账对象；一切经验写入根目录 knowledge/。
