# 交接包_零损失 · 说明（README）

> 本目录 = 自演化验证沙盒实验项目的**自包含交接包**：全部源代码 + 交接文档 + 全部报告文档。
> 配套阅读：00_交接文档_零损失.md（先读；§13 有开机自检清单）。

## 目录结构
- 00_交接文档_零损失.md — 零损失交接文档（§0 权威入口 / §7 复现 / §13 自检）
- code/ — 全部源代码（镜像原工程结构）
  - bootstrap_v3.py — 真实记忆库基座源码（v3.8.1，被测对象）
  - （sandbox 根级 .py）world_gen / engine_gate / lib_bridge / ops_row / run_evolve_v2 /
    env_check / probe2_p5 / probe4_budget / probe5_h4 / run_sandbox(V1 参照)
  - analysis/analyze.py、analysis/full_stats.py
  - batch_r1..r5/probe_r*.py — 全部批次探针源
- doc/ — 全部报告文档（md/html 镜像）
  - 对外完整版总报告_v3.1.0.md/.html（主文+35 原文附录）
  - 滚动总报告/结项总报告/探针1-6/综合/统计协议/设计/路线图/版本索引等（根级）
  - batch_r1..r5/结果_*.md — 批次与逐实验报告
  - env_check.out.txt；_外部资产_* — 父目录三份权威报告（只读参考）
- 未包含（请回原工作区取，或按 §7 复现）：
  - out_* 数据目录（rows/traj/manifest/parity/p5/真实库快照/libs_snapshot）
  - batch_rN/out_rN_* 数据、*.log 运行日志、__pycache__、tmp_*、临时诊断文件
  - 原因：数据可由固定 seed + manifest 一键复现；日志/临时文件为过程物。

## 复现入口（在 自演化验证/sandbox_experiment 下运行；本包 code 亦可直接 import 使用）
1) py -3 env_check.py
2) py -3 run_evolve_v2.py --stage parity --out out_v2
3) 详见 00_交接文档_零损失.md §7 完整命令与 §8 数据 schema。
批次探针：cd code/batch_rN && py -3 probe_rN_*.py（输出到运行目录 out_rN_*）。

## 版本基线
- 报告链：v1.0.0 基线 → R1..R5(1.1-1.5) → 滚动 v2.1.0 → 对外完整版 v3.1.0
- 校验：00_交接文档 §13 七项自检全过 = 交接完成。
