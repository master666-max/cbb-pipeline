---
name: cbb-pipeline
description: 正典库构建流水线（Correct-by-Construction Canon Library）——把长篇小说原文转化为带证据四元组、三态写入、隔离区兜底的可查询正典库。当用户提到 正典库 canon 提取 小说入库 证据四元组 三态写入 隔离区 契诃夫枪 伏笔台账 实体别名 终审抽校 lore 知识图谱 时使用本技能。适用于任意长篇小说（含百万字级）的全文正典化：开书→逐章子代理抽取→三态门禁→全库终审。
license: CC-BY-4.0 (content)
compatibility: 需 Python 3.10+（Windows 用 py -X utf8 启动器）；嵌入扫描/图导出为可选增强（LM Studio/Neo4j），缺省不影响主链
metadata:
  version: "1.0"
  origin: CBB 全量构筑版（16 仓对比吸收 + 迷深 517 章实战沉淀，2026-09）
---

# cbb-pipeline · 正典库构建流水线

把一部长篇小说全本，转化为「带证据四元组、三态写入（confirmed/provisional/quarantine）、全局约束可校验」的正典知识库。**长上下文逻辑问题的解法**：逻辑不活在任何上下文里——活在库的记录与机械约束里；抽取无状态，记忆在库，全局账由门禁与终审算。

## 何时使用
- 新书开库：拿到小说全本（txt/md，含章节标记），要建正典知识库
- 续跑：已有 BUILD-STATE 与本体库，从游标继续
- 终审：全库入库完成，做十轮终审+抽检交付

## 目录地图（按需读取，勿一次全读）

| 文件 | 内容 | 何时读 |
|---|---|---|
| [references/编排与并发.md](references/编排与并发.md) | 调度员-子代理编排/上下文包四件套/两段式并发/限流与挂死诊断/NLI 预筛 | 派工与遇阻时 |
| [references/十查与终审.md](references/十查与终审.md) | 每批十查+全库终审十轮镜头（含门槛数值） | 批收口与终审时 |
| [references/抽取规范.md](references/抽取规范.md) | 子代理逐章抽取规范（R6 四面防御/契约/别名四分类/引文预检） | 每章抽取前（子代理必读） |
| [references/判例模板.md](references/判例模板.md) | 跨章裁决判例集格式（封顶 30 条） | 裁决时 |
| [scripts/GRAPHITI-READY.md](scripts/GRAPHITI-READY.md) | 图数据库就绪层三步启用+四触发器哨兵 | 需要 Neo4j/graphiti 时 |
| [scripts/cbb/](scripts/cbb/) | 六技能模块+四契约 schema（coordinate/anchor/extract/gate1/quarantine/store） | 实现与校验 |
| [scripts/cbb/tools/](scripts/cbb/tools/) | 上下文包生成/嵌入查重/图导出/账本链/NLI 矛盾对/graphiti 桥（各配单测） | 对应场景直接运行 |
| [assets/project.template.yaml](assets/project.template.yaml) | 开书参数模板（书名/语料/锚点/阈值） | 开新书写配置 |

## 流程路由

```
开书   ──→ 填 project.yaml → scripts/init_project.py 生成工作区+BUILD-STATE
边界   ──→ 解析章节标记（单一真值）+ 伪锚点树（2000-01-01+i，禁墙钟）
试车   ──→ 单章端到端+金标/抽样自检（预注册门槛，不过停单）
主队列 ──→ 调度员派子代理逐章抽取（规范+判例+上下文包+切片）
          → gate1 三域 → quarantine 三子类 → store 双轨入库
收口   ──→ 每 8 章轻收口（游标+scoped commit）；每段十查重项+召回探针
终审   ──→ 十轮镜头全库审计+confirmed 抽检≥95% → 隔离区报告 → 交付
```

## 核心纪律速查（全文见 references）

1. **三态写入**——错误可以产生，confirmed 的库里它进不来；矛盾不静默合并
2. **证据即公民**——每条记录带（卷,章,行,引文）四元组，引文逐字预检
3. **逻辑住在库里**——抽取无状态；上下文包是先验不是事实源，冲突以原文为准
4. **全局约束求解**——死人走路/契诃夫枪超期/悬空引用，门禁与终审机械执行
5. **隔离区一等公民**——处理不了显式隔离出报告，绝不静默丢弃
6. **子代理无状态**——每章新上下文，候选自写盘回执 ≤200 tokens；记忆在库不在脑
7. **断点纪律**——游标+逐批 scoped commit；STATE=缓存，磁盘+git=事实
8. **R6 四面防御**——元文本/禁词八类/防先验/注入，逐字执行
9. **许可红线**——只读参考仓零代码零文本接触，冲突即违令
10. **判定权分离**——执行无权自宣验收；量尺机械化，禁自抽自评
