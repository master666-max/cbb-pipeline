# BUILD-STATE · 迷深实战（全量构筑版阶段三 · 缓存，事实以磁盘+git为准）

> 建立：2026-09-15 审核线预播种。协议照《迷深实战-工单.md》（唯一指令源）。
> 双锚：/goal 目标=工单 §1 判据原文；本头部为等价兜底锚。
> 批游标：主队列进度以此为准——`游标=下一待入库章序号`（1 起算，对齐 clean_full.txt 第 N 个 <<<CHAPTER>>> 标记）。

目标判据：U-C00~U-C10 全部 done（入库 517 章、每批十查留痕、终审十轮+confirmed 抽检≥95%、隔离区报告、交接文书、逐批 commit）。

单位清单（状态）：
- U-C00 单章试车 | **done（2026-09-16）** | 判据=CHAPTER0014 亲抽端到端+金标 v5 自检 adjusted 实体 P≥0.70（预注册门槛,未达停单） | 证据=切样(行5516-5700,sha08cc9036f03ec9ee=金标同源)→77候选(34实体/38关系/4事件/1伏笔)→gate1 全过→store 76+锚点入库+1真隔离(low_confidence pending)；**评分 raw 实体 P=1.000(34TP/0FP/0FN)≥0.70 门槛通过**，adjusted 关系 38/38（评分/adjudication 件+score-adjusted 留档）；R6 全文内嵌 extraction _meta；幂等重放 76 consistent-duplicate 零增殖；十查留痕=工作区/logs/十查-U-C00-ch14-excerpt1.md | 幂等=双轨+游标
- U-C01 边界表与锚点树 | **done（2026-09-16）** | 判据=517 章边界+伪锚点树 v1 落盘+抽 5 章核对+cbb/tools 两件(嵌入查重/Neo4j增量导出)单测绿 | 证据=boundary-table-v1.json(517章,30NOISE+1DUP[0347=OF 0346 行108516,内容哈希幂等自去重])+anchor-tree.v1.json(517锚点tick=摄入序)+抽查5/5过+embed_dedup_scan(10测试绿,实链blocked按设计:judge档在载)+neo4j_export(8测试绿,实链已通:容器拉起→34节点37边导出→重放58/37幂等)；留痕=工作区/logs/U-C01-留痕.md | 幂等=版本化不覆盖
- U-C02 小队列 1-5 章 | **done（2026-09-16）** | 判据=0001 元文本章 R6 试金石+四章正常+抽检 2 条 | 证据=0001 零抽取(is_metatext 同判)+0003/0004/0005/0006 共 272 候选全过门1 入库(356 provisional 累计含 ch14)；**三组双名桥接**(基督=相川涡波假名/缇亚=迪亚布罗·西斯/玛利亚=玛利亚·迪斯特拉斯,relation 挂接留 R4)；守护者线(缇达败北+阿尔缇登场+遗愿)；引文预检机制固化；嵌入扫描实链(0.85-0.95 存疑 10 对入隔离只提示)；缇达/阿尔缇分类学 supersede 统一；十查=logs/十查-U-C02-第1-5章.md | 幂等=同上
- U-C03 主队列 6-102 | 进行中·批1 done(位置6-13: ch0007/0008/0009/0012/0013/0014补全/0015/0016/0017,260候选入库,库计580 provisional;游标=下一位置14=CHAPTER 0018) | 判据=游标至 102+每批十查留痕 | 证据=十查-U-C03-批1日志+嵌入扫描6章(疑重1对/存疑12对入隔离)+Neo4j 171节点;批内主线:三组双名relation挂接/拉丝缇娅拉=圣人缇娅拉再造肉体/守护者封印与消失机制/圣诞祭死期时限钩/组队系统与魔法体系机制全解 | 幂等=批游标+commit
- U-C04 主队列 103-199 | 判据=游标至 199+十查留痕 | 证据=- | 幂等=同上
- U-C05 主队列 200-296 | 判据=游标至 296+十查留痕 | 证据=- | 幂等=同上
- U-C06 主队列 297-393 | 判据=游标至 393+十查留痕 | 证据=- | 幂等=同上
- U-C07 主队列 394-490 | 判据=游标至 490+十查留痕 | 证据=- | 幂等=同上
- U-C08 主队列 491-517 | 判据=游标至 517+pending 清尾 | 证据=- | 幂等=同上
- U-C09 全库终审十轮 | 判据=十镜头留痕+confirmed 抽检≥95%(30条) | 证据=- | 幂等=只读审计
- U-C10 交接文书 | 判据=判据对照+全库统计+隔离报告移交+待确认 | 证据=- | 幂等=快照型

前置事实（2026-09-15 审核线核证）：语料=语料分析/corpus/clean_full.txt（517 章实测）/mishen_full.txt 参照；**路线=GLM 亲抽单路线（用户裁决 v1.1，主抽取零付费 API；v1.2 存量资源整合：本地 judge 锚定评分/Embedding 8B 相似度扫描/Reranker 4B 抽检重排辅助（无 /v1/rerank 经 llama-server，失败降级可选）/Neo4j 图层增量导出+Cypher 终审；DeepSeek 第三方抽检 ≤¥5 硬顶仅限抽检）**；本体验收 10/10（task-050）。

U-C00 固化决议（抽取规范 v2，主队列沿用）：
- **行号口径**：evidence.line=章内物理行（cbb-coordinate，=切样/文件行号−1）；verified_against 三件套=path(语料分析/corpus/clean_full.txt)+sha(git blob 全长 e1a96061…)+日期。
- **canonical 最小稳定**：实体=name+entity_type（人物→character 库/其余→setting 库）；关系=三元组+claim；事件/伏笔涉事者用 canonical.entities（名称数组）。**entity_refs(id) 不进 canonical**（trial-v0 实证：派生 id 随上游修正漂移→双轨假矛盾）；id 级 REF/死人走路批内休眠，孤悬引用审计=U-C09 R2 按名称全扫（责任转移）。
- **别名**：不进 canonical，走 aliases.jsonl 复合 PK（register_alias）；『大小姐』类称号永不合并（别名四分类 descriptor/title 类）。
- **摄入序≠章号**：伪锚点 i=<<<CHAPTER>>> 标记序（0 起算）；章号 0002/0010/0011 等缺号（557 编号存 517）；ch0014 摄入序=10。
- **置信校准**：0.90=直接命名+行为事实；0.85~0.88=verbatim 提及/声称类；<0.85(如对象反推)→路由隔离 low_confidence（TAU_PROVISIONAL=0.85）。
- **judge 锚定评分**：按 §0⑤ 段尾批评档（不逐批）——U-C00 试车章并入 U-C03 段（6-102 含 14）收口执行。
- **评分器适配（R-018 留痕）**：adapt_record_to_tier1.py（cbb/tools/）——entity→entities(name/type/summary)，relation→edges(source/target/fact，claim 前缀【声称】），event/foreshadow/anchor 不映射，time_expressions 恒 []；评分器与金标本体零改动。
- **提取者已见金标披露**：U-C00 评分属管线试车门非盲测；无偏对照=段末 DeepSeek 抽检。

阻塞登记：（无）——v1.1 免费路线无外部服务依赖。嵌入扫描/Reranker/Neo4j 辅助项未启动（工具 U-C01 交付；探活降级条款照 §0②③④）。
勘误日志：2026-09-15 v1.0→v1.1 路线改判（DeepSeek 付费路线砍除，LM Studio/Neo4j 依赖随路线移除），审核线执行用户裁决。
勘误日志：2026-09-16 U-C00 试车两起留档——①亲抽引文笔误（所在之处→何处）被门1 G1-EVIDENCE 拦截后修正重抽（trial-v0 隔离区 rejected 裁决在档）；②entity_refs 漂移假矛盾 10 条→设计 v2（refs 出 canonical，见固化决议）；trial-v0 本体库整体移档 工作区/trial-v0-本体库/（移动清单在档，81 文件零删除）。
