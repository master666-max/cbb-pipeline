# m-index · 双索引与会话入口

## 装什么
knowledge/_index.md（总索引骨架）+ archive/_INDEX.md 条目表（m-core 已建空文件，本模块写入表格头）+ 会话入口文件。

## install.md 步骤
1. 写 knowledge/_index.md（模板填 {{SLOT:DATE}}）。
2. 确认 archive/_INDEX.md 有表头（m-core 装过则跳过）。
3. 生成会话入口：读 adapters/harness-detect.md 结果定 {{SLOT:ENTRY_FILE}}；从 adapters/entries/ 复制对应模板填槽。
4. 校验点：_index 行数 <200；入口文件存在且含「每次会话开始」。

## 溯源
实验区 Phase 3；本工作区 task-001 实装。
