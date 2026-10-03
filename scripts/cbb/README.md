# scripts/cbb/ — 抽取期实现层（六模块 + 契约 + tools）

> 抽取期六模块（coordinate/anchor/extract/gate1/quarantine/store）＋四契约＋tools 工具族，各模块与工具配随仓单测。
> 收束期核心见 [`../cbb2/`](../cbb2/)，收束期运行件见 [`../pipeline/`](../pipeline/)；总入口见仓根 [SKILL.md](../../SKILL.md) 与 [README.md](../../README.md)。

## 目录

- `contracts/` — 四契约 schema v2（case/issue/record/verdict）+ 校验器 `cbb_contracts.py` + 判卷契约 `judge-v2.2.txt`
- `cbb-coordinate/` — 幂等坐标+追加序纪律（引文四元组落坐标）
- `cbb-anchor/` — 双时间轴 tick/instant/time
- `cbb-extract/` — 四面防御抽取
- `cbb-gate1/` — 证据门：三域九码确定性硬校验（validate/links/continuity）
- `cbb-quarantine/` — 三子类隔离区+urgency
- `cbb-store/` — 双轨合并+UNIQUE 约束族（说明见其 [README.md](cbb-store/README.md)）
- `tools/` — 派生与巡检工具族：词表/批次自检/环境自检/图库隔离/检索层/neo4j 导出/图对账/实体名归因/派生层对账/连续性巡检等（各配单测）
