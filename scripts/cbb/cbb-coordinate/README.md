# cbb-coordinate（本体版 v2）

> 全局坐标系统+编号注册表。前置技能：无（P0 最底层）。契约：间接消费（block_id 供 Record.evidence 定位）。

## 职责
1. **全局坐标**：`(卷, 章, 段, 行)` 四元组坐标化全文——章标记 `<<<CHAPTER N | 标题>>>`，行号=章内物理行 1-based（空行占号），preamble 不静默丢弃（章 0 收容）。
2. **幂等缓存=断点协议**：`process_file` 以 sha256(全文+vol+算法版本) 为缓存键；命中即跳过计算，输出除 `cache_hit` 外逐键一致。长篇分批处理状态在盘不在内存。
3. **编号注册表**（v2 新增，`NumberingRegistry`）：
   - **追加序纪律**（吸收 graphify-novel）：ID 按分配序单调递增；`story_pos` 只记录不参与编号——追溯补录（乱序插入）是预期行为，**永不重排、永不复用**；`by_story_order()` 提供故事序只读视图（查询可排序，编号不重排）。
   - **先查重即占位**（吸收 R-015）：`register(series, key)` 幂等于 `(series, key)`，同键返回既有号；发号即追加落盘（append-only JSONL），落盘即占位；取号前 `reload()` 重放最新账本（多实例纪律；跨进程互斥不在本层职责，残余竞态已在类 docstring 披露）。

## v1.0 → v2 变更
- 保留：coordinate/locate_quote/process_file（算法未动，缓存键 algo=coord-v1 兼容）。
- 新增：NumberingRegistry + CLI `--register SERIES KEY STORY_POS`（`-` 表示无 story_pos）。
- 移出：三态写入桩 → cbb-store（U-B07）接管真实三态/版本化/双轨合并（实验版桩是 M1 占位，本体版不再需要）。

## 确定性纪律
输出与账本不含任何时钟/随机字段（有反例单测锁定）。

## 用法
```bash
py -X utf8 cbb/cbb-coordinate/cbb_coordinate.py --input 全文.txt --cache .cache --vol 1
py -X utf8 cbb/cbb-coordinate/cbb_coordinate.py --registry reg.jsonl --register EVT 事件键 14
```
