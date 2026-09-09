# Patterns · 规律范式库

> 编号自 PT-001 起。比 pitfalls 多一层「验证状态」，验证状态是进化循环的驱动数据。
> 每条必须带至少一个真实存在的实例链接（铁律 2）。

---

### PT-001 / 2026-09-03 / docx 生成验收流水线
- 适用场景：需要产出正式中文 Word 文档（报告、方法论、说明书）且质量要求可验证的任务。
- 核心步骤：docx-js 脚本生成（封面用配方、目录用 TableOfContents 元素、正文标题用 HeadingLevel）→ `add_toc_placeholders.py --auto` 注入目录占位 → 页脚域后处理（罗马/阿拉伯页码格式开关 + 清理空 pgNumType）→ `postcheck.py` 自动检查（0 错误才继续）→ docx2pdf 转 PDF → pymupdf 渲染逐页 PNG → judge 视觉验收（全 pass 才交付）。
- 验证状态：已验证 1 次（12 页文档，自动检查 0 错误 + 视觉验收 12/12 pass）
- 实例：archive/2026/09/dual-library-docs/README.md（「复现」节有完整步骤）

### PT-002 / 2026-09-03 / 空工作区建库执行路径
- 适用场景：在无历史内容的工作区首次搭建双库体系（Phase 0 确认为空后）。
- 核心步骤：按提示词跳过 Phase 2 → 搭骨架（knowledge/skills/trajectories + archive/_cold + workspace）→ 建分类文件（pitfalls/patterns/decisions 带格式模板头，暂无依据则留空）→ 写 task-start / wrap-up 两个 SKILL.md → 建双索引与 AGENTS.md 会话入口 → 程序化互链校验（引用路径逐一 exists 检查 + frontmatter 合规 + 索引行数 <200）。
- 验证状态：已验证 1 次（本工作区，互链抽查 14/14 通过）
- 实例：knowledge/trajectories/2026-09-03/task-001-建库.md；执行依据：双库自进化体系·建库提示词.md

<!-- 条目格式模板：
### PT-001 / {日期} / {模式名}
- 适用场景：{什么样的任务触发这个模式，越具体越好}
- 核心步骤：{方法论概述}
- 验证状态：{待验证 / 已验证 N 次}
- 关联：{链接到 pitfalls 相关条目或 Skill}
- 实例：{archive/... 实例链接，必须真实存在}
-->
