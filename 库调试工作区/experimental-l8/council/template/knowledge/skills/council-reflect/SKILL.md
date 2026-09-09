> [v3 语境适配页（bootstrap_v3 安装器注入，v3.5/J-008a）] 本文件写于 v2.x 语境。v3 库等价物：审计链=audit/lifelog-*.md（engine 自动入链，无需手动 lifelog_append）；变更账本=ledger/changes.jsonl；变异守卫=guard 子命令（基准黑名单+锚定）；条目写入=engine append（schema 十字段）；检索=engine retrieve；state/ 目录对应 state.json 与 memory/。v2.x 原文路径按需参考，冲突处以本页与 spec.md 为准。

# council-reflect · 心智议会（L8 实验技能）

---
name: council-reflect
description: reflect 的议会升级版。当反思素材信息冲突大、或用户明说「开议会」时调用。四席位两轮辩论产出综合报告与少数派异议。
---
# 心智议会流程

1. **入席**：同一 agent 分饰四席（强 harness 可换真子代理）：
   - 档案官：只陈述证据（trajectory/条目/usage.log 的原文位置）
   - 批评家：专挑夸大、无据、归因错误
   - 梦想家：跨域狂想（可引 dreams.md）
   - 用户代言人：读 soul/USER.md，以用户偏好质询前三席
2. **第一轮**：各席独立写 ≤5 行立场。
3. **第二轮**：互读修订，可改判。
4. **综合**：多数意见进综合报告（写入 knowledge/reflections.md，编号 R-）。
5. **少数派异议**：未被采纳的立场原样保留进综合报告「异议」节——**不可吞掉**。
6. 入链：`lifelog_append.txt "council R-NNN"`。

## 红线
- 用户代言人不代替真实用户确认（宪章第三条）。
- 预算 2 轮封顶；超预算自动收敛。
