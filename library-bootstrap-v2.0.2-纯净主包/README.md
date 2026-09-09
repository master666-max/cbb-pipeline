# library-bootstrap · 纯净主包 v2.0.2（L0-L7 稳定档）

> 87 文件 · 2026-09-05 发布 · 修复源：三处偏差修正工单 + 全量检查。

## v2.0.2 变更（vs v1.0-发布版）
- m-core 模板补齐：archive/_INDEX.md、_cold/.keep、workspace/.keep 真模板（v1.0 只建目录无文件），install.md 文件清单路径修正。
- vector-search 空库守卫内置（`--build` 空库 exit 0）；wrap-up 补装步骤提升为 install.md 显式第 4 步。
- 回归测试 T18-T21 同步（全套 38/38，源树验证）。
- L8/L9 不在本包（纯净设计）；如需请装对应 add-on 或直接换超绝统合版 v2.0.2。

## 使用
拷包 → 对 agent 发「提示词速查.md」里的指令（L0-L7 直接可用；L8/L9 提示词需先装 add-on）。
