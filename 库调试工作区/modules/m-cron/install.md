# modules/m-cron/install.md（v3.6/K-007a 渲染产物，手改即违例——v2.x 原文保留于包 bodies）

## 本模块在 v3 库中的等价物
- 审计链：audit/lifelog-*.md（engine append/wrapup/retire 自动入链，无需手动 lifelog_append）
- 变更账本：ledger/changes.jsonl（公理 C，全动作记账）
- 变异守卫：guard --diff <候选> --lib .（基准黑名单）+ guard --snapshot/--anchor（锚定）
- 条目读写：engine append / retrieve / eval（schema 十字段）
- 体检：engine doctor --lib .（memory/audit/ledger/审计链 四态）

## 本模块交付文件（2 个，已由 install 落盘）
- modules/m-cron/install.md
- modules/m-cron/template/SLEEP.md

## 校验
- install 校验模式（重复 install）：漂移/未在册/渲染件/根对账 四项
- v2.x 原文指南仅作历史参考，冲突处以本文件与 spec.md 为准。
