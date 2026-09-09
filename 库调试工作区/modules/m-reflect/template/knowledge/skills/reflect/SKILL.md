> [v3 语境适配页（bootstrap_v3 安装器注入，v3.5/J-008a）] 本文件写于 v2.x 语境。v3 库等价物：审计链=audit/lifelog-*.md（engine 自动入链，无需手动 lifelog_append）；变更账本=ledger/changes.jsonl；变异守卫=guard 子命令（基准黑名单+锚定）；条目写入=engine append（schema 十字段）；检索=engine retrieve；state/ 目录对应 state.json 与 memory/。v2.x 原文路径按需参考，冲突处以本页与 spec.md 为准。

---
name: reflect
description: 周期性反思合成，触发条件：每累计 5 次 wrap-up、用户说「反思」、或定时提醒命中且计数已满。读近期轨迹与新增条目，合成高层洞察写入 knowledge/reflections.md，并把需长期记住的结论回写 soul/USER.md。
---
# 反思合成

## 触发
- 每 5 次 wrap-up（计数由 wrap-up 第 6 步维护，见 knowledge/_index.md「反思计数」）。
- 用户明说「反思」。

## 步骤
1. **取材**：读自上次反思以来的全部 trajectory 文件 + 本期新增/修订的 pitfalls/patterns 条目。
2. **合成**：提炼 2~3 条**高层洞察**——不是复述单条经验，而是跨任务的规律。
3. **落盘**：洞察追加写入 `knowledge/reflections.md`（编号 R-001 起，注明依据链接）；属于用户长期画像的部分回写 `soul/USER.md`。
4. **演化**：若洞察与某旧条目冲突，修订旧条目（版本号 +1），不删除。
5. **计数清零**：更新 knowledge/_index.md 的「反思计数」与「最后反思」日期。

## 纪律
- 洞察必须有据（列出依据条目），无据不写；与已有洞察重复则合并并升版本。
- reflections.md 只增不改条目号，修订用版本号表达。
