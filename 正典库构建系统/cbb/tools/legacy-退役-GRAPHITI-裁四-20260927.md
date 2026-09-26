# Graphiti 族退役登记（裁决④ · 2026-09-27）

- 范围：graphiti_ingest / graphiti_spike / graphiti_dump / graphiti_bridge / graphiti_ready 五件归档出主链（文件原地保留，本注记为退役标记；构建产物化后迁 legacy/ 命名空间）。
- 理由：上游三雷未修（失效全图误杀 41% 误标 #1728 / CJK MinHash 去重失效 #1357 半年无进展 / 摄入静默丢失 #1707）；add_triplet 不绕失效与去重管线，两雷仍命中喂入三元组。
- 需求承接：双时序由 cbb2/derive（Neo4j 自建 valid_at/invalid_at 列）独任；六检索模式无 Graphiti 独立路。
- 复活条件：上游三 bug 合入发版 + 中文金标重测通过 + 确需第二独立双时序实现。
