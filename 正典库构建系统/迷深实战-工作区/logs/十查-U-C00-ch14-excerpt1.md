# 十查留痕 · U-C00 单章试车（CHAPTER 0014 切样 = 金标覆盖单元 clean_full 行5516-5700）

- 批号：U-C00-trial（单章批，2026-09-16）
- 判据锚：工单 v1.2 §3；U-C00 预注册门槛=adjusted 实体 P≥0.70

| # | 检查 | 结果 | 证据 |
|---|------|------|------|
| ① | 工作区健康 | PASS | 起点核验：STATE 全 todo ↔ 磁盘无迷深实战交付物（cbb 本体在位、无 store jsonl/tools）→冷启动属实；本批产物全部新路径，无覆盖 |
| ② | 边界表切片正确 | PASS | 切样 sha256_16=08cc9036f03ec9ee 与金标 provenance 逐字一致；章题『第二卷-第三章-第四位同伴』与 marker 对质一致；章内行号基准=切样行号−1（coordinate 口径） |
| ③ | R6 生效 | PASS | 抽取规范内嵌 R6 全文（extraction-ch14-excerpt1.json `_meta.r6_verbatim`，逐字照抄 cbb-extract 内置版）；本章为正文章非元文本章，候选 77 条证据全部回落正文块（gate1 G1-EVIDENCE 全量机械复核）；0001 元文本章试金石留 U-C02 |
| ④ | reference_time=伪锚点无墙钟 | PASS | 摄入序=10（clean_full 第 11 个 <<<CHAPTER>>> 标记，章号≠摄入序：0002/0010/0011 缺号）→tick=10→伪锚点 2000-01-11（anchor-v01c0014 入库 timeline 库）；候选零墙钟字符串（time_verbatim 仅原文短语；verified_at 为契约三件套字段非叙事时间） |
| ⑤ | 抽取量合理区间 | PASS | 185 行切样→77 候选（34 实体+38 关系+4 事件+1 伏笔+1 锚点），与金标计数口径（34 实体/38 关系）同量级；无空记录章 |
| ⑥ | quarantine 分流正常 | PASS | 生产库 pending 1 条=low_confidence（拉丝缇娅拉\|离家出走\|弗茨亚茨：对象系反推，conf 0.80<0.85 路由隔离）——三子类位 extrapolation_unverified 细分组 low_confidence；另 trial-v0 现场含 G1-EVIDENCE 拦截 2 条（rejected 裁决关闭）+refs 漂移假矛盾 10 条（设计缺陷实证，见移动清单） |
| ⑦ | 去重与双轨命中入账 | PASS | 幂等重放：76 条全 consistent-duplicate（repeated=True，库文件 77 个不增殖，P-017 守卫生效）；UNIQUE 约束族登记：别名 8 条（aliases.jsonl 复合 PK）+出场 34 条（appearances.jsonl）；嵌入相似度扫描=工具 U-C01 交付后启用并回补首扫（本批无嵌入依赖，如实登记） |
| ⑧ | 证据四元组抽检对原文 | PASS | 抽 4 条（超 2 条要求）回 clean_full grep 全中：『所在何处』→行5637／『十四层的高温』→行5525／『塞拉自报家门』→行5554／『Foam辅助Dimension』→行5670；本地 judge 锚定评分=按 §0⑤ 显存调度段尾批评档设计，并入 U-C03 段（6-102 含 ch14）收口执行，登记 STATE |
| ⑨ | verified_against 真实三件套 | PASS | 77 候选+锚点全部 path=语料分析/corpus/clean_full.txt + sha=e1a96061d25b0016094dd8daec82769ee80fc3bb（git blob 全长）+ verified_at=2026-09-16；占位值 0 条 |
| ⑩ | STATE 游标+scoped commit | PASS | U-C00 置 done（证据栏填齐）；本批 scoped commit（只 add 本批交付路径） |

## U-C00 门槛判定

- **raw 实体 P=1.000（34 TP/0 FP/0 FN）≥ 0.70 预注册门槛 → 通过**（自动保守匹配即满分，无需裁决补配）
- adjusted 视图（评分器 --adjudication 原生机制，补配 12 条被端点贪心抢占的同端点边）：关系 P/R=1.000（38/38），方向准确率 0.974（1 swapped=『与·在迷宫结识』主客方向约定差异，金标以基督为主语、本库以拉丝缇娅拉为主语）
- raw 关系 P=0.684 的 12 条"失配"全部归因：评分器按端点对贪心匹配且不看谓词文本，同端点相邻边（接受决斗/应约条件、朋友/庇护等）互相抢占——内容 38/38 实际对应（adjudication 件留档 评分/adjudication-ch14-excerpt1.json）
- time_usability=0.267 仅参考（R-018：time_expressions 恒置空，本门槛只看实体 P）

## 试车发现（事件留档：logs/trial-v0-移动清单.md）

1. 门1防线有效性实证：亲抽引文笔误（所在之处 vs 原文所在何处）被 G1-EVIDENCE 证据回落当场拦截
2. 设计缺陷修正 v2：entity_refs（派生 id）不进 canonical（上游修正→id 漂移→双轨假矛盾 10 条）；关系按名称引用、事件/伏笔 canonical.entities 名称数组；id 级 REF/死人走路批内休眠，孤悬引用审计责任转移至 U-C09 R2 按名全扫
3. 提取者已见金标（工单把金标自检设为门槛→试车门性质），无偏对照=DeepSeek 第三方抽检（§0，段末执行）
