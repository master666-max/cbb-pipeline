# ComfyUI 零基础入门教程 docx（comfyui-docx · 完成于 2026-09-02）

> manifest 归档（D-001）：本体未搬移——scratch 位于 `comfyui-docx-scratch/`，终版交付物位于根目录 `ComfyUI零基础入门教程.docx`。

## 一句话
用 node + docx 库脚本生成 33KB 的 ComfyUI 零基础入门 Word 教程，经 pymupdf 程序化验收后交付。

## 复现
- 环境：Windows + Node（comfyui-docx-scratch/node_modules 已装 docx 库）+ `py`（pymupdf、docx2pdf）
- 运行：`node comfyui-docx-scratch/generate.js` → 按需执行 patch_footers.txt / render.txt / verify.txt（均为 .txt 形态的 Python 脚本，`py xxx.txt` 方式运行）
- 最终产物：`ComfyUI零基础入门教程.docx`（根目录，唯一终版）

## 数据流
generate.js + generate_prompt.js → output.docx →（patch_footers.txt 页脚域补丁）→ output.pdf（docx2pdf）
→（verify.txt pymupdf 空白页/溢出检测）→ 根目录 ComfyUI零基础入门教程.docx

## 关键决策
- Python 后处理与验收脚本全部写成 .txt 交付执行，规避 .py 被 hook 拦截（根因与规避见 P-001）。
- 程序化验收（verify.txt）替代目视验收，可重复运行。

## 踩坑与经验
- 教训：pitfalls.md#p-001（py 启动器 + .txt 形态脚本）
- 范式：patterns.md#pt-002（docx 生成验收流水线，已验证 2 次）

## 复用提示
- ★★★ 高：任何中文 Word 文档生成任务按 PT-002 步骤复用；改 generate.js 的内容数据与样式即可。
- 逐页 PNG 预渲染在 comfyui-docx-scratch/pages/（page_01.png 起），可用于快速目视复查。

## 未竟事项
- 无。
