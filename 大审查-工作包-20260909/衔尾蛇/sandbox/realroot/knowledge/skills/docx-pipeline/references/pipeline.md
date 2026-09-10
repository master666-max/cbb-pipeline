# PT-002 docx 生成验收流水线 · 详细参考

来源：knowledge/patterns.md#pt-002（修订 v2）。本文件为技能级展开，条目正文以 patterns.md 为准。

## 已验证实例
1. 实验性双库工作区 dual-library-docs（2026-09-03）：12 页《双库体系建设方法论·阅读版.docx》，自动检查 0 错误 + 视觉验收 12/12 pass。
2. 本工作区 ComfyUI 零基础入门教程（2026-09-02）：33KB docx，verify.txt 程序化验收通过，成品在根目录。

## 步骤细节
1. **生成**：node + docx 库。封面用预制配方；目录用 TableOfContents 元素；正文标题一律 HeadingLevel（保证目录能抓到）。脚本见 scripts/generate.js（实例）。
2. **目录占位**：docx 库生成的 TOC 需要打开后更新域；早期做法用 add_toc_placeholders.py --auto 注入占位，Word 首开更新域即得真实页码。
3. **页脚后处理**：patch_footers.txt——罗马/阿拉伯页码格式开关、清理空 pgNumType；直接改 docx 的 XML。
4. **程序化验收**：verify.txt——pymupdf 逐页：空白页检测（text_len<5）、文本块溢出右缘检测（x1 > W-40）；0 问题才继续。替代目视验收，可重复跑。
5. **渲染**：render.txt——pymupdf 逐页导出 PNG 供视觉复核。

## 环境坑（P-001）
- Windows 会话 `python` 不可用 → `py`；脚本文件用 .txt 形态规避 .py 拦截，`py -X utf8 xxx.txt` 执行。
- docx2pdf 依赖本机安装的 Word（COM 组件）；无 Word 时改用 LibreOffice 或跳过 PDF 环节改纯程序化验收。
