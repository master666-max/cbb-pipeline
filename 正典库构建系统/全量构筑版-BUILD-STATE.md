# BUILD-STATE · 全量构筑版阶段一（缓存，事实以磁盘+git为准）

> 建立：2026-09-14 审核线预播种。协议照《全量构筑版-总纲.md》§S。
> 双锚：/goal 由用户侧设置（判据见总纲 §G）；本头部为等价兜底锚。

目标判据：U-A01~U-A17 全部 done；16 仓各一份独立详报落 `全量构筑版-分析报告/`（§R 六节齐备、断言带 文件:行号、三谜仓给出谜底）；U-A17 跨仓综合报告落盘；逐单位 commit 可证。

单位清单（状态：todo）：
- U-A01 agent-skills | 状态=done | 判据=总纲§R 六节报告落盘+错挂本仓的"5.8万行js"谜底已给 | 证据=全量构筑版-分析报告/agent-skills.md（六节齐、断言带文件:行号、主线抽验12处行号全中；谜底=150个.ts共58,386行技能自带Deno CLI脚本，.js为0）+ Issue 001 | 幂等说明=报告快照型，重写走新版本
- U-A02 author-toolkit | 状态=done | 判据=六节报告落盘（三谜"5.8万js"经Issue 001证错挂本仓：实际0 js，谜底在U-A01已给，本仓报告§1已注明） | 证据=全量构筑版-分析报告/author-toolkit.md（六节齐+断言带文件:行号；亮点=finding-schema confidence双口径/审计三分类+引擎权威化/continuity修复策略≈supersedes） | 幂等=报告快照型，重写走新版本
- U-A03 basic-memory-skills | 状态=done | 判据=六节报告落盘（含 sota-memory-radar 对照：七派未收录此件，定位C派图联想检索实现+D派反思思想） | 证据=全量构筑版-分析报告/basic-memory-skills.md（六节齐+断言带文件:行号；亮点=literary-analysis六阶段管道/Seed先行/validation warn-strict双档/lifecycle archive-never-delete；许可=README文字声明MIT但无LICENSE正文文件【待确认】） | 幂等=报告快照型，重写走新版本
- U-A04 chinese-webnovel-skills | 判据=六节报告 | 证据=- | 幂等=同上
- U-A05 claude-book | 判据=六节报告+三谜(191篇md)谜底 | 证据=- | 幂等=同上
- U-A06 danghuangshang | 判据=六节报告 | 证据=- | 幂等=同上
- U-A07 evals-skills | 判据=六节报告 | 证据=- | 幂等=同上
- U-A08 graphify-novel | 判据=六节报告 | 证据=- | 幂等=同上
- U-A09 neo4j-skills | 判据=六节报告 | 证据=- | 幂等=同上
- U-A10 neuro-book | 判据=六节报告+三谜(54.7万行js疑vendored)谜底 | 证据=- | 幂等=同上
- U-A11 oh-story-claudecode | 判据=六节报告 | 证据=- | 幂等=同上
- U-A12 sillytavern-skills | 判据=六节报告 | 证据=- | 幂等=同上
- U-A13 story-skills | 判据=六节报告 | 证据=- | 幂等=同上
- U-A14 story-systems-template | 判据=六节报告 | 证据=- | 幂等=同上
- U-A15 webnovel-writer | 判据=六节报告(GPL红旗复核) | 证据=- | 幂等=同上
- U-A16 worldbook-skill | 判据=六节报告 | 证据=- | 幂等=同上
- U-A17 跨仓综合报告 | 判据=16详报汇总裁决→全量构筑版本体路线修订书(对照实验版重构/保留清单) | 证据=- | 幂等=同上

前置事实（2026-09-14 审核线核证）：实验版 cbb-skills/ 已冻结（FROZEN-实验版声明.md）；16 仓源码在 现成技能侦察/源码/；evals-skills+neo4j-skills 已装机（实验版 U0）。

阻塞登记：（无）
勘误日志：
- 2026-09-15 构建线对账发现：三谜"5.8万行js"归属错位——STATE U-A02/总纲§W 挂 author-toolkit，实测（索引清单§8/15+工作量预设§二+主线 find/wc）谜实体在 agent-skills (jwynia)（150 .ts/58,386 行，.js=0）。处置=谜底就地落 U-A01 报告§1；U-A02 将注明错位；Issue 001 落 分析报告/issues/ 待审核线改判基线文字。未发现其他对账差异（17 单位 todo 与磁盘无报告、git 无报告提交一致）。
