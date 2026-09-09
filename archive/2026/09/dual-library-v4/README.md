# 双库 v4 升级（dual-library-v4 · 完成于 2026-09-04）

> manifest 归档（D-001）：改动分布在多个既有文件，本体不搬移。

## 一句话
按 2025-2026 新一代记忆架构（MemOS/Zep/HippoRAG 2/MIRIX/Sleep-time/Anthropic 上下文工程）把 v3 双库升级为 v4：条目元数据（来源/置信度/状态）、扩散激活检索、月度睡眠整理、预算制与密钥纪律。

## 复现
- 计划书：`workspace/双库v4优化计划书.md`（七信源增量对照表）
- 改动清单：pitfalls/patterns 7 条 schema v3；tools/search_knowledge.txt 新建（含正则 bug 修复实录）；CronUpdate automation-bb8b3e66（体检+睡眠整理报告）；decisions.md D-003/D-004；AGENTS.md 铁律+检索行；task-start v3.1；_index v4

## 数据流
workspace/双库v4优化计划书.md →（webReader 十信源调研）→ 条目 schema v3 + 检索/睡眠工具 →（lint + 检索实测）→ 本归档

## 关键决策
- 不引向量库与外部记忆服务（D-001 延续）：Zep/MemOS 的时序与元数据思想用「状态字段+来源字段」在 Markdown 上落地；HippoRAG 2 的扩散激活用「[[邻居]]一跳折半计分」简化实现。
- 睡眠整理只输出建议清单不自动改库（维持"列建议不自动执行"纪律）。

## 踩坑与经验
- 事故：decisions.md 插入新条目时用 D-002 标题行作锚点，把标题替换掉了（正文成孤儿），当场恢复。教训：**多块插入不要用既有内容作唯一锚点，应在文件尾部追加或用带上下文的完整锚点**。
- search 工具首版正则 `[PDRT]-\d+` 匹配不了 PT- 前缀，实测抓出后改 `[A-Z]{1,2}-\d+`。
- Context7 MCP API key 持续失效（2026-09-03/04 两次确认），网络调研统一走 webReader。

## 复用提示
- ★★★ 高：其他工作区升 v4 照计划书 P0→P3 顺序；search/lint 两工具复制即用。

## 未竟事项
- PT-004 达 3 次阈值，建议升级为独立 skill `library-upgrade`——等用户裁决。
- reflect 首跑仍待 wrap-up 计数满 5。
