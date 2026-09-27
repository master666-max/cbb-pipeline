# G11 conformal NLI 校准 — BLOCKED 登记（2026-09-27）

## 状态：BLOCKED（缺数据，非缺依赖）

- 代码就绪：`cbb-v2/cbb2/governance.py` `ConformalNLICalibrator`（标准 conformal 语义，
  nonconformity=1-score 不掺标签；测试 `test_v3_governance.py` 绿）。
- 判据要求：校准报告（覆盖率/错误率/预测集分布）——需要 **≥10 条人工核验判例**
  `(premise, hypothesis, label, score)`，其中 **score 必须来自 NLI 通道的真实打分**。

## 缺口实况（2026-09-27 盘点）

| 数据源 | 有无标签 | 有无通道分数 | 可用性 |
|---|---|---|---|
| 隔离区 604 矛盾件人工裁决（416 confirmed/188 rejected） | 有（human decision） | **无**（矛盾判定走嵌入相似度，NLI 未打分） | ✗ |
| G16/G16b 考官票面 | 无金标 | 票面非分数 | ✗ |
| A04 NLI 双通道 | 测试判例有标签 | 测试内即兴分数，非沉淀判例集 | ✗ |

结论：**分数-bearing 人工判例集=0**，校准无从谈起。不臆造判例（D-004 同族纪律：
数据缺口显式登记，不生产假信任）。

## 解锁路径

1. 从 G16b 晋升批抽取 30-50 件，人工复核为 (premise=证据摘录, hypothesis=canonical, label)；
2. 同批跑 NLI 通道留 score；
3. `ConformalNLICalibrator(alpha=0.10).calibrate(labeled)` → 校准报告落
   `迷深实战-本体库/G11-NLI校准报告.json`（覆盖率/错误率/预测集分布三件齐）。

预计工作量：半轮人工复核窗。触发条件：G16b 大批完成、人工审计窗开启时顺路产出
（与 Wilson 形式审计 n≥80 同窗复用同一批判例）。
