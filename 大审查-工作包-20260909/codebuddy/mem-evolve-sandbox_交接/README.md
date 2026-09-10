# mem-evolve-sandbox

记忆库自演化引擎的沙盒实验台。被测对象为 `bootstrap_v3.py`（v3.8.1）的真实记忆内核，
实验设计见 [`docs/实验设计.md`](docs/实验设计.md)。

## 快速开始

```bash
# Windows：python 可能是 Microsoft Store 存根，用 py 启动器
set BS3_PATH=<bootstrap_v3.py 的绝对路径>

py -3.14 harness/run.py selftest        # 门禁：等价性 + 多目标冲突
py -3.14 harness/run.py consistency     # C1–C5 一致性探针（真实源码）
py -3.14 harness/run.py concurrency     # v3 vs v4 并发写丢失率
py -3.14 harness/run.py evolve --terrain pseudo --cfgs static none two-tier --seeds 24 --gens 60
```

无第三方依赖，纯 stdlib。结果写入 `runs/<name>/{summary.json, log_*.json}`。

## 子命令

| 命令 | 作用 |
|---|---|
| `selftest` | 等价性门禁（参数化内核 ≡ 真实 `_rank_entries`）+ 多目标冲突门禁 |
| `consistency` | C1 五态对账 / C3 截断（内部 + 人侧锚点双口径）/ C4 并发 / C5 铁律 / Merkle 伸缩 / 自测诚实性 |
| `concurrency` | 12 进程并发 append：v3 read-modify-write vs v4 事件重放 |
| `evolve` | 主实验：`static / none / strict-admit / two-tier / two-tier+anchor / random` × 五地形 |
| `matrix` | 全场景矩阵 |
| `budget` | 注意力预算 → 终局效用曲线 |
| `importance` | 自称 vs 实测采纳率的 top-10 真实质量 |
| `reorg` | 平铺 vs 层次化归并 |
| `forget` | 目标切换后旧目标能力保留度（单一最优 vs Pareto） |
| `world` | 导出世界快照 |

## 三层边界

- **元层（冻结，人侧签名）**：K、评测协议、任务集、效用权重 W0、margin、tolerance
- **法层（可演化）**：`genome.py` 的 12 个基因——检索权重、热度预算、TTL、生存期、重组方式、importance 口径
- **行层（真实 v3 语义）**：`memory/ audit/ ledger/ state.json evals/` + 采纳日志

方向性约束：变更只能向上申请，系统无法修改评判自己的尺子。

## 纪律

1. 不复制粘贴 `bootstrap_v3.py` 的任何逻辑，一律 `importlib` 直调；重实现必须过等价性门禁。
2. 自报值（训练集效用、感知效用）与实测值（冻结审计集效用）分列；对外结论只用后者。
3. 验证一条护栏前，先构造它所防范的危险地形。
4. 否定性结果与肯定性结果同等记录，按预注册口径报告。
