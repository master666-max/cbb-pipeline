# legacy 退役件说明（G22 · D-27 · 2026-09-27）

> 本目录以下退役件**文件原地保留**（铁律：不删除），主链不再调用；每件附状态与替代路径。
> 卫生约定（D-27 修复后）：全部退役件 `py -X utf8 <件> --help` exit 0；带 `--dry-run` 的
> 盘点口零写盘零网络。Graphiti 裁决细节另见同目录《legacy-退役-GRAPHITI-裁四-20260927.md》。

| 退役件 | 状态 | 替代路径 |
|---|---|---|
| `build_index_v2.py` | 退役；D-27 已修（argparse+`--dry-run`+`--store`，`--help` 不再触达写盘路径） | 检索读面走 `cbb-v2/cbb2/fastscan.py`（多模式字面粗筛）＋`cbb-v2/cbb2/search.py`（别名精确+关键词+RRF+引文核验）；分析走 `cbb-v2/cbb2/lens.py`（DuckDB 只读） |
| `web_console.py`（含 `web_console.html`） | 退役；缺席声明在案（PhaseA 披露批）；`--dry-run` 补齐（只打印配置即退出，不绑端口；本件对库本就只读） | 检索/分析读面走 `cbb-v2/cbb2/search.py`＋`lens.py`；隔离区盘点走 `cbb-v2/cbb2/lens.py` tri-state |
| `graphiti_ingest.py` | 退役（裁决④裁四，2026-09-27）；原有 `--dry-run` 在位 | 双时序由 `cbb-v2/cbb2/derive.py` 独任（Neo4j 自建 valid_at/invalid_at） |
| `graphiti_spike.py` | 退役（裁决④裁四）；argparse+`--dry-run` 补齐（不 import graphiti_core 不连 Neo4j） | 同上 `cbb-v2/cbb2/derive.py` |
| `graphiti_dump.py` | 退役（裁决④裁四）；`--dry-run` 补齐（不连 Neo4j） | 图快照改走 `cbb/tools/neo4j_export.py` collect_graph（正典图 7695）或 `cbb-v2/cbb2/derive.py` 投影 |
| `graphiti_bridge.py` | 退役（裁决④裁四）；`--dry-run` 补齐（只打印预设） | 同上 `cbb-v2/cbb2/derive.py` |
| `graphiti_ready.py` | 退役（裁决④裁四）；`--dry-run` 补齐（本件本就只读） | 就绪自检口径并入 `cbb-v2/cbb2/ops.py` 四条件 BLOCKED/READY |

- **退役理由（Graphiti 族）**：上游三雷未修（失效全图误杀 #1728 / CJK MinHash 去重失效 #1357 /
  摄入静默丢失 #1707）；add_triplet 不绕失效与去重管线。
- **复活条件**：上游三 bug 合入发版 + 中文金标重测通过 + 确需第二独立双时序实现（详见裁四注记）。
- 退役件改动纪律：只允许卫生批（argparse/`--dry-run`/退役标注），**禁止**恢复为生产路径。
