# exp9-instrumentation · 仪表盘与干预（BCA P0 · 公理 2，L9 必装基座）

## 装什么
state/ 目录 + .library-state.json（机读真身）+ DASHBOARD.md（人读）+ 三个工具脚本。

## install.md 步骤
1. 建 state/ 目录；复制 template/.library-state.json → state/（填 {{SLOT:DATE}}）。
2. 复制 scripts/state_snapshot.txt、state_intervene.txt、state_update.txt → tools/。
3. 复制 template/DASHBOARD.md → state/。
4. 在 wrap-up 第 5 步后追加：「跑 tools/state_snapshot.txt 更新仪表盘快照」。
5. 校验点：`py -X utf8 tools/state_snapshot.txt` 产出合法 JSON；`py -X utf8 tools/state_intervene.txt` 提示用法。

## 出口条件（BCA P0 同款）
能回答"这一轮为什么这么说"：决策日志（lifelog 依据路径 + STATE 快照）齐全。

## 溯源
BCA v0.1 §公理 2（没有仪表盘的机制不存在）；本库 manifest/卫兵哈希体系扩展。
