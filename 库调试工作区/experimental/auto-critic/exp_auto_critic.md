> [v3 语境适配页（bootstrap_v3 安装器注入，v3.5/J-008a）] 本文件写于 v2.x 语境。v3 库等价物：审计链=audit/lifelog-*.md（engine 自动入链，无需手动 lifelog_append）；变更账本=ledger/changes.jsonl；变异守卫=guard 子命令（基准黑名单+锚定）；条目写入=engine append（schema 十字段）；检索=engine retrieve；state/ 目录对应 state.json 与 memory/。v2.x 原文路径按需参考，冲突处以本页与 spec.md 为准。

# auto-critic · 批评家 pass（实验技能）

> wrap-up 后追加的对抗视角检查。限 3 条以内，只挑有证据的。

## 步骤
1. 重读本次 trajectory，切换批评家视角，专挑三类问题：
   - 报喜不报忧（成果写了、失败/将就没写）
   - 归因错误（表面现象当根因）
   - 无据/过度概括（经验条目找不到工作区实例）
2. 每条批评必须引用 trajectory 原文位置。
3. 「批评家备忘」追加进 trajectory；用户说「跳过批评」可跳过本步。
