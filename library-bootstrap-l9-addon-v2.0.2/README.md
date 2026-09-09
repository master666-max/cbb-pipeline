# library-bootstrap L9 add-on v2.0.2 · BCA 内省仿生层（含偏差修正）

> 30 文件 · 2026-09-05 发布 · 前置：先装 L8 add-on v2.0.2（或统合版已含本层）。

## v2.0.2 变更（vs l9-addon v1.0）
- **PENDING.md / ABLATIONS.md 模板补齐**（v1.0 install.md 引用缺失，安装期只能手工补）。
- broadcast.txt docstring 与行为对齐（PENDING 如实标注"只写不读，回读属机器变异候选，走 MUTATION-SOP"）。
- 5 处 install.md 复制源路径修正（scripts/ 写明 experimental-l9/scripts/ 全路径）。
- 回归测试 T21 锁定（源树全套 38/38）。

## 使用
拷包 → 发提示词：「按 L9 档加装：先展示 BCA 公理与验收三件（消融/干预/谄媚），确认后按序装八模块」（提示词速查.md 第二节）
