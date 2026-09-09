> [v3 语境适配页（bootstrap_v3 安装器注入，v3.5/J-008a）] 本文件写于 v2.x 语境。v3 库等价物：审计链=audit/lifelog-*.md（engine 自动入链，无需手动 lifelog_append）；变更账本=ledger/changes.jsonl；变异守卫=guard 子命令（基准黑名单+锚定）；条目写入=engine append（schema 十字段）；检索=engine retrieve；state/ 目录对应 state.json 与 memory/。v2.x 原文路径按需参考，冲突处以本页与 spec.md 为准。

---
name: worldsim
description: 反事实沙盘（L8 实验）。触发词：世界线、如果当时、反事实、worldsim。为已完成任务写「另一条路」的虚拟轨迹供反思采掘，虚拟必须显式标注。
---
# 世界线模拟

1. **选支点**：挑一个已完成任务的关键决策点（trajectory 里写过的「否决的备选」是天然支点）。
2. **推演**：写虚拟轨迹——如果当时选了备选方案，后面会怎么走？≤20 行，标 `【虚拟】`。
3. **采掘**：虚拟轨迹与真实轨迹对照，提炼 1-2 条教训（例：「当时否决 X 是对的，虚拟线在 Y 处会撞上 P-001」或「X 其实可行，当时高估了风险」）。
4. **落盘**：虚拟轨迹存 knowledge/trajectories/{日期}/worldsim-{task}.md（文件头大字标注虚拟）；教训进 reflections.md 或修订条目。
5. 入链。

## 红线
- 虚拟轨迹永不混入实证层：文件头、条目、索引必须带【虚拟】标注，检索时视为低置信。
- 一个支点一篇，不无限分叉。
