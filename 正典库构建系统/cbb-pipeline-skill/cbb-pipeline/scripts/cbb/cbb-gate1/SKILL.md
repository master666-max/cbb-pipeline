# cbb-gate1（本体版 v2 · 三域）

> 门1：确定性规则硬校验（无 LLM/网络/时钟；同输入必同判定）。前置：contracts（v2.0）+coordinate（坐标回落）+anchor（时间比较）。

## 三域（story-skills 三域分离架构）

| 域 | 检查 | 原因码 |
|----|------|--------|
| **validate** 结构/schema | 契约 v2.0 全量校验；证据四元组+原文坐标回落（悬空检测） | G1-SCHEMA / G1-EVIDENCE |
| **links** 引用完整性 | 引用悬空（entity_refs/causal_predecessors/supersedes）；**关系逆类型 12 对+对称 12 项双向回链**（"parent"必须被"child"回指；sibling/spouse 等 12 项要求同型对称边） | G1-REF / G1-REL-BACKLINK |
| **continuity** 连续性 | 死人走路（死亡实体被后续章引用）；伏笔时序倒置（payoff 早于 setup）；契诃夫枪≥3 章超期（开环未兑现）；同字段矛盾（同批双状态未走 supersedes）；因果前驱时间倒置（v1 保留） | G1-DEAD-WALK / G1-FORESHADOW-ORDER / G1-CHEKHOV-OVERDUE / G1-CONTRADICTION / G1-TIME_INVERSION |

## 吸收项（U-A17 §3）
- **Issue v2.0 落地**（`to_issue`）：每违规→契约合规 Issue（构造期 validate_issue），带 fix_action（P0-P3 优先级+精确命令——P0=SCHEMA/EVIDENCE/CONTRADICTION/DEAD-WALK，P1=REF/回链/时间/伏笔序，P2=契诃夫超期复核）、confidence_caliber="deterministic"（确定性校验器产物）、cites=[被检记录]（Cites 强制列）。
- **EXPLAIN 拒写**（检索层永不写库）：check/to_issue 纯函数零落盘；Issue 只产不写，路由权在裁决通道——测试断言零文件+输入不可变+重跑一致。
- **可执行反例测试纪律**：每域≥1 反例（story-skills 100% 覆盖门禁思想），test 文件三域各设 counterexample 用例。
- 拦截→隔离区映射收敛为 **quarantine 三子类**（矛盾待裁决/外推待证/超期遗漏——U-A17 采纳案，v1 暂定映射就此关闭，实验版 issues 在案事项落地）。

## v1 保留面
四校验语义（SCHEMA/EVIDENCE/REF/TIME_INVERSION）+ check_batch 批量/摘要/gate_trace（verdict_id 内容哈希）+ 候选间互联合法。

## 移出
三态写入桩 → cbb-store（U-B07）。

## 用法
```bash
py -X utf8 cbb/cbb-gate1/cbb_gate1.py --candidates cands.json --manifest coord.json --current-chapter 20
```
