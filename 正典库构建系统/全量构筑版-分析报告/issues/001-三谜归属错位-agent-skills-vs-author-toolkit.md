# Issue 001 · 三谜归属错位：agent-skills ↔ author-toolkit

> 提出方：构建线（U-A01 执行中）｜ 日期：2026-09-15 ｜ 状态：待审核线裁定
> 依据：R-014（下发文书=外来断言，接单即核证）+ R-016（宣称层≠实现层）

## 事实

1. STATE U-A02 与总纲 §W 均写：author-toolkit = 三谜仓，"5.8 万行 js 用途"。
2. 磁盘与两份在案文书相反：
   - 《索引清单.md》§各仓简历 8/15：author-toolkit（rhavekost）= 6 技能纯提示词 MIT，0 js；agent-skills（jwynia）= 119 技能。
   -《源码全量分析·工作量预设.md》§二普查表：agent-skills (jwynia) = 150 文件 "JS/TS" 58,386 行（谜在此）；author-toolkit = 79 文件纯提示词。
3. 主线实测（2026-09-15）：agent-skills 仓 `.js` 文件数=0，`.ts` 文件=150 共 58,386 行（详见报告 §1 谜底）。

## 判断

预播种时把 jwynia 仓的行数之谜错挂到 author-toolkit 头上（两仓都以提示词技能为主，易混）。"5.8 万行 js"谜的实体是 agent-skills (jwynia) 的 **TypeScript** 脚本资产。

## 构建线处置（保守，未擅改基线）

- U-A01 报告 §1 已给出该谜谜底（谜实在本仓，就地破解）。
- U-A02（author-toolkit）将照常做六节报告，其 §1 注明"本仓 0 js，行数之谜实挂 agent-skills，谜底见 U-A01 报告"。
- 本 Issue 登记错位，**留审核线改判**：是否修订总纲 §W/§R 的三谜仓归属文字、是否在 STATE 勘误。

## 连带口径建议（供 U-A17 与后续各仓报告统一）

"js 行数"统一按扩展名分列（.js / .ts），不再用"JS/TS"合并列转写，防同类失真。
