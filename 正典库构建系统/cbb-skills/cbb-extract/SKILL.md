---
name: cbb-extract
description: CBB P2 最小版抽取器。只抽 event/entity 两类候选记录，每条强制带证据四元组；内置 R6 元文本防御规则（Step 0 验证文本）作为生产标配。需要从小说正文产出候选记录、或组装 Graphiti add_episode 抽取参数时使用。
---

# cbb-extract（P2 抽取 · M1 最小版骨架）

## 职责（P1 建设计划书 §三）

只抽 event / entity 两类，每条强制带证据四元组（B4：无证据不入库）。
产出 = **candidate 候选记录**（入库前状态，门1 校验后才由 cbb-store 三态路由）。

## R6 元文本规则 = 生产标配（Step 0 三条件之一）

`R6_CUSTOM_EXTRACTION_INSTRUCTIONS` 常量**内置**本模块，逐字照抄
Step 0 Tier2 已验证文本（P1执行区/step0-抽取精度实验/脚本/run_tier2_pipeline.py）：

> 元文本（作者杂谈/翻译组公告/论坛吐槽/现实日期/话数卷数/平台与作品名）一律不得抽取任何实体或关系；
> 无专名但固定出场且有关键行为的职务称呼（如店长）应抽取为实体；
> 专有名词保留原文写法，不翻译不改写；
> 信件/传闻/指控中的声称按文本事实抽取，并在 fact 中标注"据某某声称"。

Tier1 双模型在粉丝公告章 100% 超抽（15 实体/16 边全 FP）→ Tier2 管道内注入 R6 后
该章零污染。真实抽取路径**必须**经 `custom_extraction_instructions` 原生注入本常量。

## 双模式

- **stub 模式（M1 默认，离线确定性）**：`extract_stub(blocks, lexicon, event_patterns)`
  词典/关键词驱动的规则抽取，产出契约合规的 candidate 记录——供单测与 U7 冒烟。
  record_id 由内容哈希决定（重跑幂等）。
- **graphiti 模式（P2 实装）**：`build_episode_kwargs(i, body, …)` 组装
  add_episode 参数——`reference_time=pseudo_anchor(i)`（伪锚点纪律，禁墙钟）+
  `custom_extraction_instructions=R6…`；完整管道复用 Step0 Tier2 已验证脚本
  （venv312 + DeepSeek + LM Studio 嵌入），M1 不重复实现未测代码。

## 元文本前置过滤（stub 模式）

`is_metatext(title, text_sample)`：确定性启发式（标题/正文命中元文本特征词→整章跳过）。
stub 模式的第一道闸；真实模式的对应防线 = R6 指令注入（已验证）。
启发式词表是 M1 简版，P2 按语料扩。

## 契约关联

候选 = Record 全字段（status="candidate"，入库前态不在库枚举——
`validate_record(allow_candidate=True)` 校验其余字段全合规）。
evidence 四元组坐标语义来自 cbb-coordinate；story_time 挂靠来自 cbb-anchor。

## 三态写入桩（M1）

`three_state_write_stub`：candidate 先落 quarantine 演示位不是本件的职责——
本件只产候选；三态分池发生在门1 判定后的 cbb-store。桩保留用于独立演示。

## 用法

```bash
py -X utf8 cbb_extract.py --manifest 坐标manifest.json --lexicon 缇达,迷宫 --events 拔出了剑
py -X utf8 test_cbb_extract.py
```

## M1 边界（P2 扩展点）

- LLM 真实抽取（graphiti 管道接线，含抽取先例注入 gate_scenario="extraction"）；
- QA 驱动补抽/自校验轮/覆盖率检查（FMEA 抽取漏检三防）；
- 实体消歧三层（词典→LLM→人工，P3 Reversible Canonicalizer）。
