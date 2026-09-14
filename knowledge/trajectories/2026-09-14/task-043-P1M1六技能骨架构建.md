# task-043 · P1-M1 六技能骨架构建（构建线 · 交互式执行路径）

> 日期：2026-09-14 ｜ 执行工位：CBB 构建线执行代理（本会话切位，闲时任务未开通 →
> 用户以 /goal+下发单正文的交互式路径投喂，= 模板 A2 推荐替代路线）
> 上游：task-041（模板）/ task-042（下发单落盘）｜ 交付：`正典库构建系统/cbb-skills/`

## 任务与判据

按《CBB技能族·P1建设计划书》M1 落六技能骨架（各含 SKILL.md+入口脚本+单测）+U0 外挂装机。
判据（/goal 原文）：U0-U8 全部 done、六技能齐备含三态写入桩、py -X utf8 单测全绿、
cbb-extract 内置 R6 标配、cbb-anchor 过时间精度抽检、逐单位 commit 可证、U7 集成冒烟通过。

## 执行记录（9 单位 10 commit，逐单位 BUILD-STATE 对账）

- U0 外挂：evals-skills(7)+neo4j-skills(29)=36 技能 cp -n 装 ~/.zcode/skills/，SKILL.md 在位 36/36；
  安检 1 命中=Neo4j 官方安装器文档（curl|bash 静态说明，原样保留+警示登记）；【待确认】命名空间裁剪。
- U1：contracts/ 四契约 schema（Record/Issue/Verdict/Case 照抄 Part IV，含 B4 minItems1 与
  candidate 边界 $comment）+stdlib 最小校验器；cbb-coordinate（章标记解析/四元组/幂等缓存无时钟）。
- U2：cbb-anchor——伪锚点 2000-01-01+i 天、源码级禁墙钟（静态+功能双检）、锚点=契约 Record
  默认 provisional（人工前置不改判）、树版本化 vN 新文件、18 条时间精度抽检电池、三显式隔离标记。
- U3：cbb-extract——R6 四条规则逐字内置（Step0 Tier2 验证文本）、stub 确定性抽取
  （元文本章零抽取/证据强制/record_id 内容哈希幂等）、build_episode_kwargs（伪锚点+R6，已测）；
  graphiti 运行时=P2 复用 Tier2 管道，不写未测代码。
- U4：cbb-gate1——四校验 G1-SCHEMA/EVIDENCE/REF/TIME_INVERSION，粗精度时间不硬判（保守），
  verdict_id 内容哈希可重放；拦截→隔离分组映射=M1 暂定（issues/Issue-1）。
- U5：cbb-quarantine——五类分组、append-only 双日志、登记幂等、人工裁决终态留档不删、
  报告=第一产出（阻塞下游降序+请你确认）。
- U6：cbb-store——三态路由（quarantine 不落任何 library 目录=B1）、置信度路由永不单凭置信给
  confirmed、supersede version+1 旧件字节不动+索引链、迁移旁车日志。
- U7：集成冒烟 20/20 双跑 EXIT=0（坐标→锚点→抽取 R6→门1→隔离→入库全链断言）；
  **抓出真缺陷**：transitions 旁车重跑重复追加 → 终态守卫修复（→P-017）。
- U8：交接文书+issues 三件+6 待确认；全量单测终跑 73/73。

## 关键决策（保守口径，均已在文书登记）

1. candidate 不进 Record.status 枚举（schema 照抄不动，$comment+代位校验处理接缝）。
2. 月/年/季粒度时间不折天（compare 返回 None=不判倒置）——B1 宁缺毋滥。
3. confirmed 只走人工/门2b 通道，置信度路由最高只给 provisional。
4. 元文本双闸：stub=确定性启发式词表；真实路径=R6 指令注入（Tier2 已验证）。

## 收尾

wrap-up 六步：P-017 入库（幂等断言/旁车终态守卫）；_index 同步（反思计数 3/5；
task-042 索引行顺带补登注记归属审核线）；本轨迹。反思未触发（<5）。
