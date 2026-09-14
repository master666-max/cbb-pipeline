# BUILD-STATE · 本体构筑（全量构筑版阶段二 · 缓存，事实以磁盘+git为准）

> 建立：2026-09-15 审核线预播种。协议照《本体构筑-工单.md》（唯一指令源）。
> 双锚：/goal 目标=工单 §1 判据原文（用户侧设置或代理开场自设）；本头部为等价兜底锚。

目标判据：U-B00~U-B09 全部 done（每单位十轮自审留痕齐+出口门过；cbb/ 全量单测绿且 ≥73；逐单位 commit；U-B09 终报落盘）。

单位清单：
- U-B00 基线与整改 | 状态=done(2026-09-15) | 判据=实验版73绿(-B只读跑)+graphify-novel v1.1行号补强在位+cbb/骨架 | 证据=73绿=11+9+10+11+11+10+11全OK(EXIT0,git status零污染)；v1.1落盘26条行号引用≥10要求(grep独立抽验16/16精确)；cbb/树成型(contracts+六技能.gitkeep+smoke+自审日志+issues)；十轮自审出口门过=cbb/自审日志/U-B00.md | 幂等=测试只读(-B)；v1.1新文件
- U-B01 契约层修订 | 状态=done(2026-09-15) | 判据=四schema v2+校验器好/坏双向+单测绿 | 证据=四schema v2.0落地(record:verified_against三件套+observations19类词表+evidence可选file；issue:fix_action P0-P3+confidence_caliber+cites minItems1；verdict:critique键序强制+0-100定标+分带强制一致+rule_applied五派conflict必填；case:counter_example三段式配对强制+retro_tags)；单测33/33绿(实验版同套件11)双跑一致；不增设第四态有反例断言；十轮自审=cbb/自审日志/U-B01.md | 幂等=文件落盘skip-if-exists
- U-B02 cbb-coordinate | 状态=done(2026-09-15) | 判据=追加序+查重占位单测绿 | 证据=NumberingRegistry落地(追加序:story_pos只记录永不重排+by_story_order只读视图;查重占位:(series,key)幂等+append-only落盘即占位+断点重放)；幂等坐标/缓存断点协议v1.0回归7例保留；17单测绿(基线9,含乱序插入与查重占位用例)+CLI冒烟幂等；十轮自审=cbb/自审日志/U-B02.md | 幂等=纯函数+append-only账本重放
- U-B03 cbb-anchor 双时间轴 | 状态=done(2026-09-15) | 判据=双轴+as-of+缺坐标不可见单测绿+18条抽检回归 | 证据=双时间轴落地(tick摄入序单调必填/instant可回退倒叙合法/time人读不参与排序/asof双语义as_of_tick知识边界+as_of_instant世界状态AND/缺坐标判不可见宁可漏召回不可泄漏/story_order倒叙还原/replay章号轴降级)；instant_from_relative自研解析(day精度产出)；countdowns_due倒计时到点兑现；伪锚点禁墙钟+18条电池逐字回归(test_battery_count_18锁条数)；23单测绿(基线10)双跑一致；AGPL零代码接触(仅引我方详报转述)；十轮自审=cbb/自审日志/U-B03.md | 幂等=纯函数+版本化不覆盖
- U-B04 cbb-extract 三层防御 | 状态=done(2026-09-15) | 判据=四面防御逐面用例+元文本章零抽取+施工参数在位 | 证据=四面防御并配(①R6逐字照抄190字与实验版importlib比对一致+stub闸 ②禁词八类scan_banned逐类用例+transform/delete分族 ③防先验no_prior_fill证据交叉+//原文未提及占位+反推标注 ④注入防御四样本整块拒抽)；吸收六项(证据式条款/占位反推/别名四分类0.85门槛存疑分开/施工参数517章65批15KB→8K→√N/机械硬检查verify_evidence伪造捕获/编写前重读协议条款)；保留stub幂等+build_episode_kwargs；27单测绿(基线11)；十轮自审=cbb/自审日志/U-B04.md(R10一处当场修复=尾批语义补文档) | 幂等=stub+内容哈希
- U-B05 cbb-gate1 三域 | 状态=done(2026-09-15) | 判据=三域单测绿+每域≥1可执行反例 | 证据=三域重构(validate=SCHEMA+EVIDENCE/links=REF+REL-BACKLINK逆类型12对+对称12项双向回链/continuity=DEAD-WALK+FORESHADOW-ORDER+CHEKHOV≥3章超期+CONTRADICTION+TIME_INVERSION)；Issue v2.0落地(to_issue构造期合规+fix_action九码P0-P3+精确命令+caliber=deterministic+cites强制)；EXPLAIN拒写(零落盘+输入不可变+重跑一致三断言)；三域8可执行反例；24单测绿(基线11)；十轮自审=cbb/自审日志/U-B05.md | 幂等=纯函数
- U-B06 cbb-quarantine | 状态=done(2026-09-15) | 判据=三子类分流+urgency排序单测绿 | 证据=三子类(contradiction_pending/extrapolation_unverified/overdue_omission已裁决案)+五分组保留为细粒度入口+默认分流map+gate1显式子类优先；urgency公式(进度比×层级3.0/2.0/1.0+🔴到点即超期/🟡≥0.8定约/🟢+top_urgent前3条+超期压过层级实侧证)；[?]内联扫描+行号汇总报告；保留五分组请你确认+append-only裁决终态；18单测绿(基线10)；十轮自审=cbb/自审日志/U-B06.md | 幂等=append-only内容哈希
- U-B07 cbb-store 双轨+约束 | 判据=双轨分流+UNIQUE防重+漂移钩子+cbb-merge并入单测绿 | 证据=- | 幂等=skip-if-exists+旁车终态守卫
- U-B08 集成冒烟 | 判据=离线版全绿双跑EXIT0；真管道版done或blocked留痕 | 证据=- | 幂等=缓存+skip-if-exists
- U-B09 终报交接 | 判据=交接文书+实验版对比表(73 vs 新总数) | 证据=- | 幂等=快照型

前置事实（2026-09-15 审核线核证）：工单 v1.0 在位（唯一指令源）；实验版 FROZEN（只读，测试须 -B）；阶段一验收 17/17（task-047）；用户三裁决已录入工单 §0。

阻塞登记：（无）
勘误日志：（无）
