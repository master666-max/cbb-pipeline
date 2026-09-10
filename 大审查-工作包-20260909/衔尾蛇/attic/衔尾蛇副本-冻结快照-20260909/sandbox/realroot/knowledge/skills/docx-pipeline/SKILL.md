---
name: docx-pipeline
description: 生成正式中文 Word 文档（报告/教程/说明书）时调用。触发词：docx、Word 文档、生成文档、写报告出 docx。v3 首个带可执行脚本的固化技能（源自 PT-002，已验证 2 次），含生成/后处理/验收三段脚本。
---
# docx 生成验收流水线（PT-002 固化版）

## 环境前提
- Node + docx 库（`npm i docx`，参考 scripts/generate.js 的用法）；Python 用 `py`（勿用 python，见 pitfalls P-001）。
- `docx2pdf`（需本机 Word）、`pymupdf` 按需 `py -m pip install`。
- `.py` 被 hook 拦时，后处理脚本已是 .txt 形态，直接 `py -X utf8 scripts/xxx.txt` 运行。

## 流程三段
1. **生成**：写 generate 脚本（模板：scripts/generate.js，封面/目录 TableOfContents/HeadingLevel 用法都在里面；内容数据与样式按新任务改写）→ `node generate_xxx.js` 产出 docx。
2. **后处理**：`py -X utf8 scripts/patch_footers.txt`（页脚域：罗马/阿拉伯页码格式开关，清空 pgNumType）——路径与文件名按项目改。
3. **验收**：`py -X utf8 scripts/verify.txt`（pymupdf 逐页检查空白页、文本溢出右缘，0 问题才交付）→ `py -X utf8 scripts/render.txt` 渲染逐页 PNG → 视觉复核（或 judge 代理）。

## scripts/ 说明
- generate.js / generate_prompt.js：ComfyUI 教程的已验证实例（48KB/39KB），当模板抄结构、换内容。
- patch_footers.txt / verify.txt / render.txt：通用工具脚本，改动量小（改输入输出文件名）。

## references/
- pipeline.md：PT-002 完整步骤与两次验证记录。

## 完成后
- 按 wrap-up 六步：新验证把 patterns.md#PT-002 验证次数 +1；交付物归档（引用不搬移则写 manifest README）。
