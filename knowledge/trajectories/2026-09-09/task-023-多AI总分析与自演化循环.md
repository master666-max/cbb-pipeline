# task-023 · 多AI沙盒总分析 + 开放式自演化研究循环（2026-09-09）

## 一句话
四部分任务全量完成：PART I 六阶段分析（承接首批 8 commit，99-FINAL→06-ANALYSIS-FINAL 归位）+ PART II 十二轮预注册研究循环（26 假设：12 SUPPORTED/4 REFUTED/10 INCONCLUSIVE）+ PART III 元观测双轨 + PART IV 终报，大审查/ 仓库 23 commits。

## 复现
- 工作根：`大审查/`（git 仓库，progress.md 为断点登记表）。
- PART II 判据全部锁定：`sandbox/meta/registry.md`（hash 账本）；数据快照 `sandbox/out/*.json`。
- 元指标：`py -X utf8 sandbox/final_metrics.txt`；机测反推：`py -X utf8 sandbox/meta_metrics.txt`。

## 数据流
unified/*.jsonl（PART I 归一化 2593 行）→ R1/R5/R7 数据假设；最小引擎族（engine_r2/3/4/6/8/9）+ 仪器化重放（replay_regions/replay_gradient，验证门与锁定 JSON 逐 run 全等）→ R2-R4/R6/R8-R12；data-archive.csv（26 行）+ meta_log/meta_check 双轨 → 99-FINAL.md 五曲线。

## 关键决策
- 99-FINAL.md 旧名占用 → git mv 归位为 06-ANALYSIS-FINAL.md（清单登记 progress.md），99 留给总终报。
- 判据不合理走 OBL 出口（3 条：联合判据不分主次/单点阈值/阈值贴边），不改已锁判据。
- 大审查/ 自身为 git 档案，不做 archive/ 搬移（任务书规定仓库内流转）。

## 踩坑与经验
- P-011（手算 12% 错误率，自测门全拦）、P-012（登记层自错三类：hash 手抄/heredoc 断链/自填反转）。
- 流程违规 3 起（R2 锁定时序、R7/R12 FAIL 后执行）全部 registry 留痕——账本可查是违规自曝的前提。

## 复用提示
- PT-012 流水线可直接复用于任何"自拟实验→自判分"循环；校准曲线（先验桶 vs 实际命中）是发现过度自信带的唯一手段。
- 梯度定律（门控假采纳率=局部信噪比单调函数，0.85→0.59→0.16 跨世界稳定）是 C6 矛盾的机制层候选解释，待真实数据复检。
