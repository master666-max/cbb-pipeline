# DeepSeek 交接包 · 验收报告（PT-011 三态表）

> **验收对象**：`大审查/deepseek/交接包_零损失/`（记忆库自演化引擎 V2 沙盒实验：batch_r1~r5、engine_gate、lib_bridge、真引擎基座、33 条金标查询评测体系），交接方=DeepSeek 谱系会话。
> **日期**：2026-09-09 · 验收方式：隔离复跑（code/ 复制至衔尾蛇副本/sandbox/deepseek_intake/，原包零改动）+ 官方两步复现入口 + 独立核对。

## 一、验收结论：**✅ 通过，正式接管**

| # | 检查 | 状态 | 证据 |
|---|---|---|---|
| 1 | 官方复现第 1 步：env_check.py（真实 b3 全链路） | ✅ | append/retire/retrieve/doctor 全通，「五态 全一致」，env_check OK |
| 2 | 官方复现第 2 步：run_evolve_v2 --stage parity | ✅ | `{'total': 100, 'ok': 100, 'rate': 1.0, 'diffs': []}` |
| 3 | 基座身份核验 | ✅* | bootstrap_v3.py = 5f8199aa（v3.8.2 中性化，2415 行，VERSION 3.8.1）；文档称 v3.8.1 属实（中性化仅注释级，功能性等价） |
| 4 | engine_gate/world_gen 常量 vs 交接文档 | ✅ | 8/8 数值一致（MARGIN0 0.02 / TOL_ARCH 0.04 / CAP_PARETO 8 / STALL_GEN 5 / AUDIT_EVERY 3 / K_TOPK 5 / LINKS_GAIN 0.5 / SPUR_FRAC 0.30） |
| 5 | R1-1 探针独立复跑（reward 切换与灾难性遗忘） | ✅ | 6/6 种子：single bestA=0.000 vs **Pareto bestA=1.000**——灾难性遗忘结论复现 |
| 6 | env_check 可复现性 | ✅ | 我方隔离复跑核心链路（五态→retire→检索排除→投毒防线→OK）与其留档注记一致；**他们独立记录的「eval 后根不一致 S7」与衔尾蛇线发现的健康信号过载完全相同（双线同病互证）** |
| 7 | 文件盘点 | ✅ | code/ 30 个 py（batch_r1~r5 探针全在）；doc/ 交接包内在位（本次隔离运行仅复制 code/） |

*#3 注记：严格哈希为 5f8199aa 而非 9d8b3b0d 原版——中性化（注释级）差异，功能性等价，如实记录。

## 二、包内容与谱系定位

- **同研究计划第三条独立路径**：DeepSeek 线与混元线（26 轮/125 实验）、衔尾蛇线（真引擎 280+ run）同源同构——基座同为 bootstrap_v3 v3.8.1 谱系，架构同为「参数化检索同构 + 真引擎落盘桥（lib_bridge ≈ 我方 law_shim/lib_bridge）+ 门控/停摆/Pareto/审计」。
- **独立收敛的结论**（三线互证）：灾难性遗忘 Pareto 防护（R1-1 复现 ✓）、eval 后根不一致 S7（双线同病）、真引擎桥接模式。
- **DeepSeek 线独有**：scenes 含 dup-drift/stale/composite 等八场景、统计协议（exact Wilcoxon 并列平均秩 + bootstrap 10⁴ + F1 判定）、R1 批次的 reward 切换/judge 污染/v3 缺陷回归/审计成本曲线四探针、v3.1.0 对外完整版（213KB 主文 + 35 附录 + HTML）。

## 三、遗留与对接选项

1. batch_r2~r5 探针未逐一抽验（R1-1 已抽验通过，其余同构）；需要时可按同法逐个复跑。
2. out_* 数据目录不在包内（README 声明固定 seed 可复现）——parity 100/100 与 R1-1 复跑已部分实证该声明。
3. 三线对接候选：DeepSeek 的八场景世界生成器 + 统计协议 ↔ 混元的 kernel.py v1（盲评/危险降档）↔ 衔尾蛇的真实库实测场地（库调试工作区）。

## 四、验收环境备注

- 隔离副本：`衔尾蛇副本/sandbox/deepseek_intake/code/`（原包 `大审查/deepseek/交接包_零损失/` 零改动）。
- 关联事件说明：昨晚 00:35 出现在 库调试v3.2 的 `bootstrap_v3.py`（147380B）经字节数比对即本包 `code/bootstrap_v3.py`（5f8199aa）——当时「他方会话」实为在执行引擎落地动作，本验收报告同时澄清了该事件的来源。
