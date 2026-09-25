# m-tools · 校验与检索工具

## 装什么
tools/lint_library.txt + tools/search_knowledge.txt（纯 Python 标准库，.txt 形态，任何解释器可跑）。

## install.md 步骤
1. 复制两个脚本到目标 tools/。
2. 按 {{SLOT:PY_RUNNER}} 在 README/_index 的「工具」节写正确用法（E-manual 档则只留文档说明不装）。
3. 校验点：跑一遍 lint_library.txt，输出「体检文件 N 个…0 问题」即通过（空库也应 0 问题）。

## 溯源
本工作区 v3 lint（实测抓过 2 个自身 bug）+ v4 search（扩散激活，HippoRAG 2 简化版）；P-001 的 .txt 形态经验内置。
