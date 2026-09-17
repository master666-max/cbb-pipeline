# task-065 · graphiti 就绪层裁决与工单 v1.8（审核线 · 2026-09-18）

## 触发
用户裁决："graphiti 的接口端口准备好！以后需要用了，直接加个 LLM 就能用，同时 A,B,C,D 四个触发器也要做好准备"。

## 裁决理解与落定
- 需求未到不预支成本，但**接口端口与哨兵先备**——把未来启用成本压缩为"一次 LLM 配置"。
- 工单 v1.8 §0 新增 graphiti 就绪层条款：U-C03.7 构建线代码件（graphiti_bridge.py：LLMConfig 工厂双预设 DeepSeek 付费/本地 5.3flash 免费+嵌入已知档+ingest 桥复用 build_episode_kwargs；graphiti_ready.py 一键自检；GRAPHITI-READY.md 三步启用文档）；**四触发器哨兵**随段收口校准报告输出 GREEN/AMBER/RED——A 全局归纳查询≥3、B 多版本语料标志、C 按章回溯计数、D 隔离矛盾积压>50 或裁决滞后>14 天；RED=增值层启用哨。

## 设计要点
- 复用优先：ingest 桥接 build_episode_kwargs（U-B04 已测形态），不重造；stub 单测离线可测（真连=可选臂）。
- 哨兵寄生在既有校准报告（W4 条款）上，零额外流程成本。
- 启用时的 LLM 候选：本地 5.3flash 夜间免费（呼应零成本路线）或 DeepSeek 付费档，双预设工厂直接切。

## 关联
task-060（决策补记录）/ 迷深实战-工单 v1.8 §0 / R-026（排期不闭环/备而不用）
