# GRAPHITI-READY — graphiti 增值层三步启用（U-C03.7 · 工单 v1.8 §0）

> 用户裁决："接口端口准备好，加个 LLM 就能用。" 本目录代码件=端口；本件=启用文档。

## 三步启用

1. **配 LLM 环境变量**（D-004：key 只走环境变量，永不落盘）：
   - DeepSeek 付费档：`setx DEEPSEEK_API_KEY <你的key>`（模型=deepseek-flash）
   - 本地免费档：LM Studio 加载 GLM-5.3flash 监听 `:1234`（`LMSTUDIO_API_KEY` 可选）
   - Neo4j：`setx NEO4J_PASSWORD <密码>` + `docker start neo4j-step0`（bolt 127.0.0.1:7687）
   - 嵌入（已知档）：qwen3-embedding-8b（q8_0，4096 维）经 LM Studio 暴露 `:8080`
2. **跑就绪自检**：`py -X utf8 cbb/tools/graphiti_ready.py --preset deepseek`
   → 四项全 READY 才继续；任一 BLOCKED 按清单逐项解除。
3. **ingest**：
   ```python
   import sys; sys.path.insert(0, r"cbb/tools")
   import graphiti_bridge as gb
   g = gb.make_graphiti("deepseek", "bolt://127.0.0.1:7687", "neo4j", "")  # 密码走 NEO4J_PASSWORD
   # 章记录 → add_episode（kwargs 全部复用 cbb-extract build_episode_kwargs：伪锚点+R6 标配）
   results = gb.ingest_candidates(g, {14: [记录dict...], 15: [...]}, group_id="mishen-canon")
   ```

## 四触发器哨兵（随段收口校准报告输出；RED=增值层启用哨）

| 触发器 | 定义 | 阈值 | 解锁 |
|---|---|---|---|
| A | 全局归纳型查询计数（`工作区/logs/global-query-count.txt`） | ≥3 → RED | 社区检测+GraphRAG 摘要 |
| B | 多版本语料入库标志（库内 verified_against.path 多路径） | 多版本 → RED | Resolver |
| C | 按章回溯操作计数（`工作区/logs/chapter-backtrack-count.txt`） | ≥3 → RED（阈值=就绪层建议值） | episode 三层 |
| D | 隔离矛盾积压 / 裁决滞后 | >50 → RED；滞后>14 天（载体无日期字段=UNKNOWN，如实披露） | NLI 预筛 |

跑法：`py -X utf8 cbb/tools/graphiti_ready.py --sentinel --store 迷深实战-本体库`

**启用动作=段收口呈报审核线裁决，哨兵只报告不动作。**

## 边界

- 主抽取路线（GLM 亲抽/jsonl 本体库）**不依赖**本层——graphiti 是派生增值层（Neo4j 同 D1 定位）。
- ingest 桥**禁重造**参数组装：reference_time=伪锚点、R6 custom_extraction_instructions 一律经 `cbb-extract build_episode_kwargs`（Step0 Tier2 已验证形态）。
- 单测离线可测（stub 协议=add_episode(**kwargs)），真连测试=可选臂。
