# 双库体系文档编制（2026-09-03 完成）

## 一句话
根据三份源 PDF 的精神 + 网页调研，产出「双库自进化体系」的可执行建库提示词（Markdown）与人类阅读版方法论（Word）。

## 复现
- 环境：Windows + Node 24（`npm install docx`）、Python 3.14（pypdf / docx2pdf / pymupdf）
- 提示词文件：直接文本产出，无需构建
- 阅读版 docx：docx-js 脚本生成 → `add_toc_placeholders.py --auto` 注入目录 → 页脚域后处理（ROMAN/arabic）→ postcheck 自动检查 → docx2pdf 转 PDF → 逐页渲染 judge 视觉验收（12/12 pass）
- 终版产物：工作区根目录 `双库自进化体系·建库提示词.md`、`双库体系建设方法论·阅读版.docx`

## 数据流
3 份源 PDF（Downloads 目录）→（py + pypdf 提取文本）→ 内容提炼
→ + WebSearch 调研（Anthropic Agent Skills 规范 / Self-Improving Agents / 持久记忆）→ 提示词文件 v2
→ docx 生成脚本 → 后处理与三重验收 → 阅读版 docx

## 关键决策
- 提示词做成「自包含可执行」而非对话摘录：任何有文件系统权限的 Agent harness 可一键运行（否决：附带对话原文——不可复现且冗长）
- Word 版与提示词分工：机器执行版讲究无歧义可校验，人类阅读版讲清设计来龙去脉（否决：只出一份合体文件——两种读者需求冲突）
- 双库建库后两份体系文件保留根目录不搬移：AGENTS.md 与 _index.md 常驻引用它们（否决：移入 archive——引用会断链，除非同步改全部引用方）

## 踩坑与经验
- 提炼到知识库：pitfalls.md#P-001（大 PDF 无法用 Read 直接读，Windows 下用 py 启动器 + pypdf 提取；计划模式会拦截 python/pdftotext）
- 本次验证的范式：patterns.md#PT-001（docx 生成验收流水线）、patterns.md#PT-002（空工作区建库执行路径）

## 复用提示
- ★★★ 高：同类「源材料 → 提示词文件 + 阅读版 docx」任务可直接复制本目录 README 为模板；docx 生成→验收流水线照 patterns.md#PT-001 执行
- 改动点：替换数据流里的源材料与章节内容；生成脚本已随任务结束清理，需按 PT-001 重建

## 未竟事项
- 见 HANDOFF.md
