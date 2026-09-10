# 裸奔骨架 · library-bootstrap v3.8.2 库

- 锚点（公理 E）：包 sha256 见 state.json 的 package_sha256；库根（Merkle，排除 state.json）见 merkle_root 字段——抄录人侧保管。
- 结构：`memory/`（intermediate/longterm/attic 条目，JSON 十字段）· `audit/`（lifelog 哈希链，真相源）· `ledger/changes.jsonl`（统一账本，公理 C）· `evals/`（评测基线）· `spec.md`/`提示词速查.md`（渲染产物，手改即违例）。
- 回退（公理 F）：一切回退=移 attic 并在账本登记；不使用销毁式回退。
- 威胁模型：①防意外：审计链+哈希。②防SOP约束下粗心：三守卫+SOP条款守卫。③防完整权限蓄意agent：包文件自哈希+人侧保管+人类令牌；『不可见』仅覆盖①②档，明示不防③。
