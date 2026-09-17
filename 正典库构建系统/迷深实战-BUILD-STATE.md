# BUILD-STATE · 迷深实战（全量构筑版阶段三 · 缓存，事实以磁盘+git为准）

> 建立：2026-09-15 审核线预播种。协议照《迷深实战-工单.md》（唯一指令源）。
> 双锚：/goal 目标=工单 §1 判据原文；本头部为等价兜底锚。
> 批游标：主队列进度以此为准——`游标=下一待入库章序号`（1 起算，对齐 clean_full.txt 第 N 个 <<<CHAPTER>>> 标记）。

目标判据：U-C00~U-C10 全部 done（入库 517 章、每批十查留痕、终审十轮+confirmed 抽检≥95%、隔离区报告、交接文书、逐批 commit）。

单位清单（状态）：
- U-C00 单章试车 | **done（2026-09-16）** | 判据=CHAPTER0014 亲抽端到端+金标 v5 自检 adjusted 实体 P≥0.70（预注册门槛,未达停单） | 证据=切样(行5516-5700,sha08cc9036f03ec9ee=金标同源)→77候选(34实体/38关系/4事件/1伏笔)→gate1 全过→store 76+锚点入库+1真隔离(low_confidence pending)；**评分 raw 实体 P=1.000(34TP/0FP/0FN)≥0.70 门槛通过**，adjusted 关系 38/38（评分/adjudication 件+score-adjusted 留档）；R6 全文内嵌 extraction _meta；幂等重放 76 consistent-duplicate 零增殖；十查留痕=工作区/logs/十查-U-C00-ch14-excerpt1.md | 幂等=双轨+游标
- U-C01 边界表与锚点树 | **done（2026-09-16）** | 判据=517 章边界+伪锚点树 v1 落盘+抽 5 章核对+cbb/tools 两件(嵌入查重/Neo4j增量导出)单测绿 | 证据=boundary-table-v1.json(517章,30NOISE+1DUP[0347=OF 0346 行108516,内容哈希幂等自去重])+anchor-tree.v1.json(517锚点tick=摄入序)+抽查5/5过+embed_dedup_scan(10测试绿,实链blocked按设计:judge档在载)+neo4j_export(8测试绿,实链已通:容器拉起→34节点37边导出→重放58/37幂等)；留痕=工作区/logs/U-C01-留痕.md | 幂等=版本化不覆盖
- U-C02 小队列 1-5 章 | **done（2026-09-16）** | 判据=0001 元文本章 R6 试金石+四章正常+抽检 2 条 | 证据=0001 零抽取(is_metatext 同判)+0003/0004/0005/0006 共 272 候选全过门1 入库(356 provisional 累计含 ch14)；**三组双名桥接**(基督=相川涡波假名/缇亚=迪亚布罗·西斯/玛利亚=玛利亚·迪斯特拉斯,relation 挂接留 R4)；守护者线(缇达败北+阿尔缇登场+遗愿)；引文预检机制固化；嵌入扫描实链(0.85-0.95 存疑 10 对入隔离只提示)；缇达/阿尔缇分类学 supersede 统一；十查=logs/十查-U-C02-第1-5章.md | 幂等=同上
- U-C03 主队列 6-102 | 进行中·批1-7(位置6-56 done, **游标=71=ch0089 第九卷第一章（1404行）；72-75=ch0090~0093 叙事；76-78=ch0094/0095/0096 NOISE**)；批7-8=**编排切换+放量批**（位置54-61=ch0066/69/70/71/72/73/74/77 全入库，每章评估器判门后入库）：ch0066 特典 NOISE 零抽取(tick54)+**A/B 门重测双章过门放量**——ch0069(45候选/33+9+3矛盾)+ch0070(68候选/50+10+8矛盾,修正循环1轮)+ch0071(48候选/40+7+1矛盾,修正循环1轮：首轮召回78.9%→97.5%)+ch0072(59候选/50+8+1)+ch0077(45候选/39+4+2)+ch0073/0074 NOISE(tick59/60)+ch0083(35候选)+ch0081(52,修正1轮)+ch0082(75,修正1轮:64一致合并+11矛盾)+ch0084(29)+ch0085/0086 NOISE(tick69/70)——**位置54-70全清17位置**；调度层机械修正3处(ch0079 library枚举location/magic→setting×4/ch0082 setting挂别名移除/ch0084漏章补派)；账本接线缺口修复(b26a6b0e:zone写入入账+rebaseline,勘误上笔commit失实message)；**子代理产物门1零拦截全部一次过**（引文预检由子代理自完成+机械评估器双保险：悬空0/673、封套0违约、召回90.6%~100%）；**v1.6 编排全前置件落地**：上下文包生成器(机械1298字≤2K预算)/切批脚本/规范v1.1追加(relationship→relation勘误+写盘名extraction-+封套纪律+密度锚+轨道纪律+滚动摘要汇入)/滚动摘要种子54行+追加机制；**A/B 重测(R-018机械口径)**：ch0069 一次过门(悬空0/162+库内召回29/32=90.6%+封套0)；ch0070 首轮覆盖FAIL(召回69.9%,海因/莱纳/次元系漏抽)→**修正循环第1轮**(miss清单22项回炉)→召回75/75=100%过门——两轮数据=库喂抽取闭环(上下文包)有效+修正循环1轮收敛；**裁定=并发3放量生效**(工单v1.4待确认⑤/v1.6迭代制)；十查=批收口执行(本批引文预检/游标推进已做) | 判据=游标至 102+每批十查留痕 | 证据=ab-gate重测件(runners/ab_retest_eval.py机械判)+logs/ch0069|0070-pipeline-summary.json | 幂等=批游标+commit
- U-C03.5 漂移修正落地（v1.4 §0） | **done（2026-09-17）** | 判据=D2 schema 回补+导出回填/W4 三阈值+校准报告/W1 judge 补考，前两件配单测 | 证据=①D2：record.schema.json evidence[].graph_edge 可选位（edge_id+valid_at/invalid_at，旧记录零改动、评分器与金标零改动）+neo4j_export 补 D1 时序字段（edge_id 确定性三元组哈希/valid_at=证据最早章/invalid_at=活版本 null）+evidence_edge_backfill 侧车回填（键级去重、库内文件字节不动）=test_d2_graph_edge.py 11 测试绿+存量 8/33 零回归；②W4：cbb_store 三阈值显式 TAU_CONFIRMED/TAU_PROVISIONAL/TAU_QUARANTINE=0.97/0.85/0.85（三档两边界，B1 confirmed 永不因置信度单独达成；调整=审核线建议制）+calibration_report（分布 vs 假设，--calibration CLI）=test_w4_thresholds.py 5 测试绿+存量 19 零回归+真库实跑（1006 记录：≥τ_conf 210/prov 带 796/低于 τ_quar 0；隔离 pending 66=contradiction 63+low_conf 3；如实披露：置信双轨刻度——抽取 0~1 与佐证上调 0~100 封顶并存，max42.9 属佐证轨，CBB 既有定约不改）；③W1 补考：**未过线**——分离度 0.5455<0.70（12 基样×56 调用，mismatch 0.92/fabricated 0.67/char_swap 0.36/**punct_mut 0.11**：judge 对字符级近失引文报 verbatim=true=失明，考卷与轨迹=工作区/评分/judge-exam-2026-09-17.json+缓存不删）→ **按 W1 条款机械执行：judge 评分停用**，段尾批评/十查⑧改机械引文对原文核验（gate1 G1-EVIDENCE+precheck 已覆盖且更强）；低分路由保守默认=可疑候选全入隔离（本就未接线 judge 分数，无行为回退）；已产出 judge 评分=无（试车期 judge 一直未启用，无 retroactive 标注量）；判卷红线全合规（rubric 锚定/temp=0/稳定键排序/分数不外报/缓存不删；response_format 需 json_schema 本版 LM Studio 不支持 json_object——适配留痕） | 幂等=考卷确定性可重放
- U-C03.6 吸收件（v1.5 §0） | **done（2026-09-18）** | 判据=store账本哈希链(sha_before/after+碰撞跳过)+仪器指纹四元组,单测+真库实跑 | 证据=cbb/tools/ledger_chain.py（LedgerChain哈希链+LedgedStore包装ThreeStateStore._append汇聚点,行为等价性单测在案；语义参考反向包append2.py按cbb契约改写零直拷）+test_ledger_chain.py 6测试绿；真库genesis基线6 jsonl+verify ok；run_chapter.py已接线LedgedStore(批7起每次追加自动入账)；仪器指纹fingerprint子命令(ranker/criterion/sort/params)待首次抽检使用即入STATE | 幂等=链式追加+genesis幂等
- U-C03.7 graphiti就绪层（v1.8 §0） | **done（2026-09-18）** | 判据=bridge双预设+ready自检+四触发器哨兵+启用文档+stub单测离线可测 | 证据=cbb/tools/graphiti_bridge.py（LLMConfig双预设DeepSeek付费/LMStudio 5.3flash,凭证环境变量缺失即报错D-004；嵌入已知档qwen3-embedding-8b 4096d@8080；ingest_candidates复用cbb-extract build_episode_kwargs禁重造）+graphiti_ready.py（四项READY/BLOCKED自检+trigger_sentinel四触发器）+GRAPHITI-READY.md三步启用文档+test_graphiti_bridge.py 5测试绿(stub协议离线)；真库哨兵实跑：A=0/B=单版本/C=0 GREEN，**D=RED(矛盾积压76>50,启用NLI预筛=段收口呈报审核线)**；裁决滞后UNKNOWN(载体无日期字段,建议补adjudications日期位)——启用动作权在审核线,哨兵只报告 | 幂等=只读哨兵
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
勘误日志：2026-09-16 批4 两起留档——①0039 沃克家引文问号/逗号笔误被门1拦截（修正重跑，隔离留档）；②0041 舞斗大会/圣人缇娅拉 entity_type 分类学未对齐库内（概念(大会)/人物 vs 概念/人物(传说)）双轨矛盾→对齐重抽+裁决 rejected。记账口径勘误：批3 STATE『766现役/775盘面』与批4身份法核对不符（HEAD@批3末去重身份实为664）——批4起 STATE=去重身份（现役）+盘面文件双轨记账，历史口径 U-C09 R1 统一对账。
勘误日志：2026-09-16 仪器身份补记（R-025）：U-C00~U-C03 已入库部分的抽取引擎=闲时任务 **GLM-5.3 正式版·极致档思考**（用户确认）。换引擎（如本地夜跑 5.3flash）属换考官——U-C00 金标 P=1.000 不跨引擎继承，重考门槛 adjusted 实体 P≥0.70 必须先过方可放量（审核线）。
【待确认】①玛利亚↔相川阳滝 实体合并（对证事实已入 setting『手环的深层心理写入（梦中揭示）』，合并归 R4+审核线）；②『ImpulseBreak』↔『Impulse』同名系派生（嵌入0.9373，分立入库，R4复核）；③引文自动定位预检段待固化为独立工具件；④帕林库洛『劳拉维亚本国』措辞与警备章地理口径（公会驻地=劳拉维亚城vs联合国）U-C09复核；⑤子代理并行亲抽提案（工作区/子代理并行亲抽-评估与放量方案.md，2026-09-16）——精度层=确定性门不受影响（本窗口实证：本人被门拦引文15处/行号自动修正39处）、判断层风险四层机制补齐（指南+查库+主线握持+十查）；放量前置门=2章双盲A/B对照（悬空率≤10%/关键事实覆盖≥90%）；**已裁决采信合并（commit 636954e8）：v1.3 编排主形态+首 2 章 A/B 双盲门放量，过门并发 3、不过回落亲抽呈报**；⑥judge m-prometheus 补考未过（2026-09-17 分离度 0.5455，字符级近失失明）——评分停用已生效；若修订考纲/提示词后允许补考=审核线裁决（考卷件 judge_exam.py 确定性可重放）；⑦子代理放量修订提案→**已闭环（2026-09-18 重测过门）**：任务包四件已固化（规范v1.1追加节+上下文包+封套样例指针+判例4连读）；A/B重测=ch0069一次过门+ch0070修正循环1轮收敛过门（R-018机械口径：库内召回硬门90%+悬空≤10%+封套0拦截；数据件ab-gate/）；**并发3放量已生效**，回落亲抽条款保留为引擎故障兜底；⑧ch0055 特典闲话『想养宠物』箱内短篇（非元文本，诺文/莉帕住史诗探索者时间线存疑）判例2 沿用零抽取——特典闲话正典地位=审核线裁定，需补抽走 W2 通道。
