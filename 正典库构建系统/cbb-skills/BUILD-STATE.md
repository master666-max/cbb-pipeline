# BUILD-STATE（缓存，事实以磁盘+git为准）

> 生成：2026-09-14，P1-M1 构建线执行代理全新开工（本文件此前不存在，②视为全新开工）。
> 双锚：/goal 目标模式由用户侧设置（在位）；本头部判据为等价兜底锚（④）。
> 开工环境快照（2026-09-14 本会话实测）：neo4j-step0 容器 Up；LM Studio 8080 在位含 text-embedding-qwen3-embedding-8b@q8_0；DEEPSEEK_API_KEY / NEO4J_PASSWORD 用户级变量存在（仅探真值，未读值，D-004）。

目标判据：P1-M1完成：正典库构建系统/cbb-skills/ 下 U0-U8 全部 done（六技能骨架齐备含三态写入桩、py -X utf8 单测全绿、cbb-extract 内置 R6 标配、cbb-anchor 过时间精度抽检、逐单位 commit 可证、U7 集成冒烟通过）

单位清单：
- U0 外挂装机（evals-skills+neo4j-skills） | 判据=两仓技能装入 ~/.zcode/skills/ 且 SKILL.md 在位 | 状态=done
  | 证据=36/36 SKILL.md 在位验证通过（evals 7 件 + neo4j 29 件）；源=现成技能侦察/源码/ 本地仓（task-034 已 clone）；方式=cp -n 零覆盖；记录=cbb-skills/u0-外挂装机记录.md | 幂等说明=cp -n + 存在即 SKIP，重跑零副作用
- U1 cbb-coordinate 骨架＋四契约 JSON Schema | 判据=contracts/ 四 schema 落地+coordinate 清洗/坐标(卷,章,段,行)/幂等缓存可跑，py -X utf8 单测绿 | 状态=done
  | 证据=py -X utf8 contracts/test_contracts.py → 11 tests OK；py -X utf8 cbb-coordinate/test_cbb_coordinate.py → 9 tests OK；四 schema=record/issue/verdict/case（照抄 Part IV，含 B4 minItems1 与 candidate 边界 $comment） | 幂等说明=process_file 缓存命中即读不重算，manifest 无时钟字段同输入同输出；三态桩已存在即跳过
- U2 cbb-anchor 骨架 | 判据=伪锚点 2000-01-01+i 天/禁墙钟/锚点树版本化/时间精度抽检单测绿 | 状态=done
  | 证据=py -X utf8 cbb-anchor/test_cbb_anchor.py → 10 tests OK（含 18 条时间精度抽检电池/禁墙钟静态+功能双检/版本化不覆盖）；CLI --chapters 14,38,114 出树正常 | 幂等说明=save_tree 同版本已存在即跳过；归一化纯函数无副作用；锚点 Record 契约校验内建于构造
- U3 cbb-extract 骨架 | 判据=R6 元文本规则内置为标配常量+event/entity 两类候选带证据四元组+stub 模式离线可测 | 状态=done
  | 证据=py -X utf8 cbb-extract/test_cbb_extract.py → 11 tests OK（R6 四条规则逐字在档/元文本章零抽取/证据回落坐标块/record_id 内容哈希幂等/kwargs 伪锚点+R6 形态）；graphiti 运行时=P2 实装（kwargs 组装器已测，管道复用 Tier2 已验证脚本） | 幂等说明=stub 纯函数+内容哈希 record_id，重跑候选逐条一致；env_probe 只出布尔不读值
- U4 cbb-gate1 骨架 | 判据=确定性四校验（schema 必填/证据四元组完整/悬空引用/时间倒置）+原因码拦截，单测绿 | 状态=todo
  | 证据= | 幂等说明=
- U5 cbb-quarantine 骨架 | 判据=五类分组+阻塞下游计数排序+"请你确认"报告生成+裁决通道（留档不删），单测绿 | 状态=todo
  | 证据= | 幂等说明=
- U6 cbb-store 骨架 | 判据=三态写入纪律（candidate→confirmed/provisional/quarantine 分池）+版本化 supersedes（不覆盖旧件），单测绿 | 状态=todo
  | 证据= | 幂等说明=
- U7 集成冒烟 | 判据=六技能串跑最小样本（含元文本章）：坐标→锚点→抽取(stub,R6)→门1→隔离→入库，断言计数全中，退出码 0 | 状态=todo
  | 证据= | 幂等说明=
- U8 交接文书 | 判据=cbb-skills/交接文书-P1M1.md 落盘（判据达成状态/单位终态/git 摘要/待确认清单/经验候选） | 状态=todo
  | 证据= | 幂等说明=

阻塞登记：（无）

勘误日志：2026-09-14 全新开工，无对账差异（cbb-skills/ 此前不存在，BUILD-STATE 亦不存在）。
