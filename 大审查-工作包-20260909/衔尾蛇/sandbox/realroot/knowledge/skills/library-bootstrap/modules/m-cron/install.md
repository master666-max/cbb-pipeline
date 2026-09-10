# m-cron · 定时体检与睡眠整理

## 装什么
定时体检指引文档（knowledge/SLEEP.md）+ harness 定时能力适配。依赖 m-tools + m-reflect。

## install.md 步骤
1. 探测定时能力：harness 有 Cron 类工具（ZCode CronCreate）→ {{SLOT:CRON_MODE}}=auto，按 harness 工具配「每月 1 号 9 点跑 lint + 反思计数提醒」（prompt 模板见本文件末尾）；无 → manual，只在 SLEEP.md 写手动流程。
2. 复制 template/SLEEP.md → knowledge/SLEEP.md，填 {{SLOT:CRON_MODE}} 与 {{SLOT:PY_RUNNER}}。
3. 校验点：SLEEP.md 存在且模式字段已填。

## cron prompt 模板（auto 档）
「双库每月体检：cd 工作区根目录，运行 {PY_RUNNER} tools/lint_library.txt 如实汇报；读 knowledge/_index.md 反思计数，wrap-up 满 5 次提醒执行 reflect；只诊断不修改，问题列清单等用户裁决。」

## 溯源
Letta sleep-time compute + LightMem 睡眠时更新；本工作区 v4 实装（CronCreate automation-bb8b3e66）。
