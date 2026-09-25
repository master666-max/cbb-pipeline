# exp8-lifelog · 全息轨迹（哈希链信任锚）

## 装什么
knowledge/lifelog/{YYYY-MM}.mdl（append-only 哈希链日志）+ 写入器（constitution 模块已带）。

## install.md 步骤
1. 建目录 knowledge/lifelog/，当月文件由 lifelog_append.txt 初始化（'L8-INIT' 创世行）。
2. 在 task-start 与 wrap-up SKILL 各追加一行纪律：「L8 启用时，任务开始/收尾各入链一行（lifelog_append.txt）」。
3. 校验点：l8_guard 三项全绿。

## 格式
`YYYY-MM-DD | 事件 | 前行哈希 | 本行哈希`——任何一行被篡改，l8_guard 精确报出行号。

## 纪律
append-only 永不回写；永不进常驻上下文（仅审计与 reflect 取材）。

## 溯源
Zep 双时态与 MemOS 记忆完整性的简化实现；区块链哈希链思想的最小可用版。
