# SOTA 记忆架构全面轰击调研（sota-bombardment · 完成于 2026-09-04）

> manifest 归档（D-001）：调研成果本体在 `knowledge/references/sota-memory-radar.md`（常驻知识库），本目录只记录过程。

## 一句话
三轮 webReader 共 14 发轰击（9 篇新论文 + 3 官方文档 + 1 搜索页 + 1 版本核对），产出七派谱系雷达图 v1（21 条目 + 升级触发器），确认本库 v3/v4 对 SOTA 的吸收度并留下重评触发器。

## 复现
- 调研方法：webReader MCP 抓 arXiv 摘要页 + 官方文档 + `bing.com/search?q=` 搜索页（WebSearch 超时时的替代搜索方案，可复用）
- 完整信源清单与逐条判定：见 radar 文档「谱系总览」各表

## 数据流
三轮 webReader 信源 → knowledge/references/sota-memory-radar.md（七派/21 条目/触发器）→ trajectory task-004

## 关键决策
- 调研成果放 knowledge/references/（常驻语义层）而非 archive/（它是升级前的必查参考，不是一次性交付物）。
- 不适用条目（MemAgent/G-Memory/Mem0-RL 等）不删除，绑定触发器留档。

## 踩坑与经验
- docs.claude.com 会网络错误，Anthropic 文档用 platform.claude.com 域名可达。
- Context7 API key 持续失效（第三工作日确认）；WebSearch 持续 60s 超时——MCP webReader 是本机当前唯一稳定调研通道。

## 复用提示
- ★★★ 高：季度例行调研照 trajectory task-004 三轮结构跑；radar 图按「触发器」清单决定是否重评。

## 未竟事项
- Reflexion 式「失败自省段」未进 wrap-up（待演化）；radar 触发器 1-4 未命中。
