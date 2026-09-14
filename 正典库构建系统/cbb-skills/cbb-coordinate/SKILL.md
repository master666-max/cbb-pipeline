---
name: cbb-coordinate
description: CBB P0 预处理与全局坐标系统。把中文小说章文本清洗并赋予全局坐标四元组（卷,章,段,行），产出幂等分块缓存。需要为正文建立可追溯证据定位（Record.evidence / 门1悬空引用校验 / 语料切块去重）时使用。
---

# cbb-coordinate（P0 预处理 + 坐标系统 · M1 骨架）

## 职责（P1 建设计划书 §三）

清洗 + 全局坐标 (卷, 章, 段, 行) + 幂等分块缓存。它是流水线的第一件：后续所有
Record.evidence 四元组、cbb-gate1 的悬空引用校验、抽取分块都以本件产出为坐标地基。

## 输入 / 输出

- 输入：UTF-8 纯文本，含语料章节标记 `<<<CHAPTER NNNN | 标题 >>>`（迷深语料格式）。
- 输出：章清单 manifest（JSON）——每章含 `vol/chapter/title/paragraphs`，
  每段含 `para/line_start/line_end/text/sha256`；另附扁平 `blocks` 列表
  （`block_id = v{vol:02d}c{chapter:04d}p{para:04d}`）。
- 行号口径：**章内物理行 1-based**（空行占号）；段 = 章内以空行分隔的非空行簇。
- 章标记之前的前导文本不静默丢弃（B6），落伪章 `chapter=0`，标题 `(preamble-无章标记)`。

## 幂等缓存

`process_file(source, cache_dir)` 以 `sha256(全文+参数)` 为键：命中即读缓存
（`cache_hit=true`），未命中才计算并落盘。manifest 不含任何时钟字段——
同输入必同输出，重跑零副作用（对账可逐字节比对）。

## 契约关联

- 证据四元组（卷,章,行,引文）的坐标语义由本件定义；
  `Record.evidence[].{vol,chapter,line}` 必须能落在本件产出的块坐标范围内（门1 G1-DANGLING/EVIDENCE 校验）。
- 本件不产 Record（P0 无抽取语义），块清单是 Record 的坐标地基。

## 三态写入桩（M1）

`three_state_write_stub(record, out_root, status)`：confirmed / provisional / quarantine
三池分目录、按记录 ID 命名、已存在即跳过（永不覆盖）。P2 起由 cbb-store 接管真实入库，
本桩仅保证技能可独立演示三态分离纪律。

## 用法

```bash
py -X utf8 cbb_coordinate.py --input 章文本.txt --cache .cache --vol 1
py -X utf8 test_cbb_coordinate.py   # 单测
```

## M1 边界（P2 扩展点）

- 卷级标记自动识别（当前 vol 为参数，默认 1）；
- 与 Graphiti episode 的 chunk 对齐策略（Step 0 Tier2 已验证 add_episode 路线）；
- 清洗仅做换行统一+行尾空白（P-003 教训：过度清洗制造误报，不动正文内容）。
