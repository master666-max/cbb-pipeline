# Task-003 双库 v4 升级轨迹 · 2026-09-04

> 原始轨迹层：只追加，只写不改。平时不加载，仅在复盘时引用。

## 任务
用户指令「疯狂的运用mcp，看看还有没有优化的地方，还有没有更新更先进的库架构」。

## 过程
1. webReader MCP 抓 8 个新信源：MemOS(2507.03724)、Zep/Graphiti(2501.13956)、HippoRAG 2(2502.14802)、MIRIX(2507.07957)、Sleep-time Compute(2504.13171)、Anthropic 上下文工程、OpenClaw、(docs.claude.com 网络错误弃用)；Context7 两次确认 API key 失效。
2. 写计划书 workspace/双库v4优化计划书.md（增量均可逆、无用户专属裁决项，未打断用户直接执行）。
3. P0：7 条条目升 schema v3（补 来源/置信度/状态，MemCube/Zep）。
4. P1：tools/search_knowledge.txt 扩散激活检索（HippoRAG 2 简化版）；实测抓出正则 bug（[PDRT] 匹配不了 PT-），修复后验收通过：「EPUB 清洗」→ PT-001 12 分居首。
5. P2：CronUpdate 月度任务升级为体检+睡眠整理报告（Letta sleep-time，只建议不执行）。
6. P3：decisions.md 增 D-003（常驻预算制）、D-004（六类映射+密钥不入库）；AGENTS.md 补铁律与检索工具行；task-start v3.1 接入工具检索。
7. 事故与修复：往 decisions.md 插入 D-004/D-003 时误替换了 D-002 标题行（其正文成孤儿），当场发现并恢复（2026-09-04）；教训待复盘——多块插入不要用单行锚点。
8. PT-004 验证 +1 达 3 次阈值：按规则只列「建议升级为独立 skill」，未自动执行。

## 本任务验证的模式
- PT-004（升级路径）验证 +1；search_knowledge.txt 是首个「写完即被实测并抓出自身 bug」的工具条目。
