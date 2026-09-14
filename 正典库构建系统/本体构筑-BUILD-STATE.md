# BUILD-STATE · 本体构筑（全量构筑版阶段二 · 缓存，事实以磁盘+git为准）

> 建立：2026-09-15 审核线预播种。协议照《本体构筑-工单.md》（唯一指令源）。
> 双锚：/goal 目标=工单 §1 判据原文（用户侧设置或代理开场自设）；本头部为等价兜底锚。

目标判据：U-B00~U-B09 全部 done（每单位十轮自审留痕齐+出口门过；cbb/ 全量单测绿且 ≥73；逐单位 commit；U-B09 终报落盘）。

单位清单：
- U-B00 基线与整改 | 状态=done(2026-09-15) | 判据=实验版73绿(-B只读跑)+graphify-novel v1.1行号补强在位+cbb/骨架 | 证据=73绿=11+9+10+11+11+10+11全OK(EXIT0,git status零污染)；v1.1落盘26条行号引用≥10要求(grep独立抽验16/16精确)；cbb/树成型(contracts+六技能.gitkeep+smoke+自审日志+issues)；十轮自审出口门过=cbb/自审日志/U-B00.md | 幂等=测试只读(-B)；v1.1新文件
- U-B01 契约层修订 | 状态=done(2026-09-15) | 判据=四schema v2+校验器好/坏双向+单测绿 | 证据=四schema v2.0落地(record:verified_against三件套+observations19类词表+evidence可选file；issue:fix_action P0-P3+confidence_caliber+cites minItems1；verdict:critique键序强制+0-100定标+分带强制一致+rule_applied五派conflict必填；case:counter_example三段式配对强制+retro_tags)；单测33/33绿(实验版同套件11)双跑一致；不增设第四态有反例断言；十轮自审=cbb/自审日志/U-B01.md | 幂等=文件落盘skip-if-exists
- U-B02 cbb-coordinate | 判据=追加序+查重占位单测绿 | 证据=- | 幂等=纯函数
- U-B03 cbb-anchor 双时间轴 | 判据=双轴+as-of+缺坐标不可见单测绿+18条抽检回归 | 证据=- | 幂等=纯函数+版本化不覆盖
- U-B04 cbb-extract 三层防御 | 判据=四面防御逐面用例+元文本章零抽取+施工参数在位 | 证据=- | 幂等=stub+内容哈希
- U-B05 cbb-gate1 三域 | 判据=三域单测绿+每域≥1可执行反例 | 证据=- | 幂等=纯函数
- U-B06 cbb-quarantine | 判据=三子类分流+urgency排序单测绿 | 证据=- | 幂等=append-only内容哈希
- U-B07 cbb-store 双轨+约束 | 判据=双轨分流+UNIQUE防重+漂移钩子+cbb-merge并入单测绿 | 证据=- | 幂等=skip-if-exists+旁车终态守卫
- U-B08 集成冒烟 | 判据=离线版全绿双跑EXIT0；真管道版done或blocked留痕 | 证据=- | 幂等=缓存+skip-if-exists
- U-B09 终报交接 | 判据=交接文书+实验版对比表(73 vs 新总数) | 证据=- | 幂等=快照型

前置事实（2026-09-15 审核线核证）：工单 v1.0 在位（唯一指令源）；实验版 FROZEN（只读，测试须 -B）；阶段一验收 17/17（task-047）；用户三裁决已录入工单 §0。

阻塞登记：（无）
勘误日志：（无）
