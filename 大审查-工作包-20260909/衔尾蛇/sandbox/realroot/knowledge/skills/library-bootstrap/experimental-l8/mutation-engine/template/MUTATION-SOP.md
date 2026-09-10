# MUTATION-SOP · 机器变异标准作业程序

> 触发：月度睡眠任务第 6 步。频率：每周期 ≤1 候选。法律：L8-CONSTITUTION。

## 提案流程
1. **取证**：读 tools/usage.log（锦标赛遥测）、最近 lint 输出、近 5 条 trajectory——找「机器哪里被用得最狠/最常出问题」。
2. **定靶**：选一个 live 文件（模板/工具/SKILL），写清改什么、为什么。
3. **建档**：`mutations/candidates/MUT-{NNN}/` 三件套：
   - `MOTIVATION.md` — 动机 + 遥测证据引用（文件:行）
   - `DIFF.md` — 具体改动（旧内容/新内容对照，可直接人工评审）
   - `BENCHMARK.md` — 实际跑分记录：`py -X utf8 run_tests.txt` 与 lint 的输出摘要；任何一项不过 = 自否决
4. **登记**：LEDGER.md 追加一行（状态 proposed）；`py -X utf8 tools/lifelog_append.txt "MUT-NNN proposed"`。
5. **等令牌**：向用户汇报候选摘要，批准 → 执行晋升（旧版进 attic、新版就位、manifest 重登记、LEDGER 状态改 approved→promoted、入链）；否决 → 状态 rejected，候选目录**永久保留**（垫脚石）。

## 红线
- 不得改 soul/ 数据与 knowledge/ 条目正文（宪章第六条）。
- 不得在提案里改 live 文件（写 DIFF 就好）。
- 自批违法（第三条）。
