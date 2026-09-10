# Task-004 SOTA 记忆架构全面轰击调研 · 2026-09-04

> 原始轨迹层：只追加，只写不改。平时不加载，仅在复盘时引用。

## 任务
用户指令（2026-09-04）：「更疯狂轰击 MCP，额度用不完」——火力全开调研最前沿记忆架构并落库。

## 过程
1. 三轮 webReader 共 14 发全部命中（初记 16 发系夸大，复盘修正——真实弹药数：第一轮 6 + 第二轮 6 + 第三轮 2）：
   - 第一轮 6 论文：MemoryBank(2305.10250)、Reflexion(2303.11366)、CoALA(2309.02427)、MemoryOS(2506.06326)、G-Memory(2506.07398)、Zhang 综述(2404.13501)
   - 第二轮 6 混合：MemAgent(2507.02259)、Memory-R1(2508.19828)、LightMem(2510.18866)、Letta memory docs、OpenClaw soul docs、Anthropic memory tool docs（docs.claude.com 域名换 platform.claude.com 后成功）
   - 第三轮 4 补漏：Bing 搜索页（webReader 抓搜索页 = WebSearch 超时时的替代搜索方案，本条可复用）、Mem0 docs、HippoRAG 2、Sleep-time Compute（后两个为雷达表补全版本核对）
2. 产出 knowledge/references/sota-memory-radar.md v1：七派谱系 21 条目（含 v3/v4 已研），每条标「已吸收/部分吸收/不适用+重评触发条件」。
3. USER.md 相处记录追加「火力全开」偏好。

## 结论
- 本库（v3/v4）对七派核心思想的吸收度已较高；剩余不适用项均绑定明确触发器（条目>100、多 Agent、超长上下文）。
- 发现可复用技巧：webReader 抓 Bing 搜索页实现搜索，绕开 WebSearch 超时。
- Reflexion 派可加强项（未执行）：任务失败时 trajectory 显式写「自省段」——留给下次 wrap-up 演化。
