> [v3 语境适配页（bootstrap_v3 安装器注入，v3.5/J-008a）] 本文件写于 v2.x 语境。v3 库等价物：审计链=audit/lifelog-*.md（engine 自动入链，无需手动 lifelog_append）；变更账本=ledger/changes.jsonl；变异守卫=guard 子命令（基准黑名单+锚定）；条目写入=engine append（schema 十字段）；检索=engine retrieve；state/ 目录对应 state.json 与 memory/。v2.x 原文路径按需参考，冲突处以本页与 spec.md 为准。

# SLEEP · 定时体检与睡眠整理（2026-09-21 建立，WP-C2）

> 模式：auto（**每日档已建**：automation-333bf023，每日 09:00 recurring，下次触发 2026-09-22 09:00；首触发实测 ✓ 2026-09-21 00:13:35 automation-f6c19799）。依据：sleep-time compute——空闲期整理，查询期省力。
> 建立依据：下发单-WP-C2-mcron定时批量同步启用-20260921（模块=modules/m-cron，blob acd83d6d/5054ff50，bootstrap v3.9，现役引擎见 RELEASE.md）。

## 每日同步窗口（每日 09:00，wrap-up 前置收集）
1. 跑 `py -X utf8 bootstrap_v3.9.py engine doctor --lib .`（五态对账：memory/audit/ledger/审计链/state），如实汇报。
2. 跑 `py -X utf8 modules/m-tools/template/tools/lint_library.txt`，如实汇报（断链/超限/frontmatter，报错也是结果）。
3. 清点：evals/eval_history.jsonl 行数与最后一条读数、ledger/changes.jsonl 行数、modules/ 十模块在位性。
4. 睡眠整理报告（只建议不执行）：
   - doctor 差异/stale 条目（verified_against 落后 instant）→ 列清单等裁决
   - eval 序列异常（护栏观察态旗标/缺失读数日）→ 列清单等裁决
   - 表述相似或内容重复条目 → 建议合并（content_hash 查重 warn 级提示复核）
5. 读 knowledge/_index.md「反思计数」，满 5 → 提醒执行 reflect（本库无 _index 则跳过本条并如实注记）。
6. **全部输出为建议清单，写入 knowledge/SLEEP-诊断-YYYYMMDD.md，等用户裁决，不自动改库（只诊断不修改）。**
