> [v3 语境适配页（bootstrap_v3 安装器注入，v3.5/J-008a）] 本文件写于 v2.x 语境。v3 库等价物：审计链=audit/lifelog-*.md（engine 自动入链，无需手动 lifelog_append）；变更账本=ledger/changes.jsonl；变异守卫=guard 子命令（基准黑名单+锚定）；条目写入=engine append（schema 十字段）；检索=engine retrieve；state/ 目录对应 state.json 与 memory/。v2.x 原文路径按需参考，冲突处以本页与 spec.md 为准。

# SLEEP · 定时体检与睡眠整理（{{SLOT:DATE}} 建立）

> 模式：{{SLOT:CRON_MODE}}（auto=harness 定时任务已配；manual=手动）。依据：sleep-time compute——空闲期整理，查询期省力。

## 每月流程（1 号 9 点或手动触发）
1. 跑 `{{SLOT:PY_RUNNER}} tools/lint_library.txt`，如实汇报（断链/超限/frontmatter）。
2. 睡眠整理报告（只建议不执行）：
   - 验证 ≥3 次的 pattern → 建议升级 skill
   - 验证 0 次且超 30 天条目 → 建议归档
   - 表述相似条目 → 建议合并
   - archive 12 个月未引用项目 → 建议移 _cold
3. 读 knowledge/_index.md「反思计数」，满 5 → 提醒执行 reflect。
4. 全部输出为建议清单，等用户裁决，不自动改库。
