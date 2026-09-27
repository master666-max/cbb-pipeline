# cbb-v2/specs · 不变式规格文档（G03 审计哲学路线落档）

> 来源：`全量重构-总工单-收束期-20260927.md` G03 单元——"审计哲学路三提案（TLA+/Alloy 伪代码）落为 `specs/` 规格文档（Quint 可选仿真）"。
> 提案原文：`前沿工具调研-审计学与哲学深度一路-20260927.md` §C「三个值得形式化的不变式提案」。
> 工具位（照录调研结论）：设计级 TLA+/Quint 跑 TLC/Apalache；结构级 Alloy 6；生产运行时用 Hypothesis 属性测试复刻同一谓词——**规格与运行时一式两份同源**。本目录当前只做**伪代码落档**，不引入任何运行时依赖；Quint 仿真为可选后续（登记，不在本单元判据内）。

## 本目录文件

| 文件 | 形式化对象 | 源码出处 |
|---|---|---|
| `写入决策树.tla.md` | store 写入决策树五分支 + 三态迁移 + 总性不变式 | `cbb2/store.py`（`write_decision` / `status_transition` / `admit`）、`cbb2/promote.py`（票门）、`cbb2/quarantine.py`（隔离区裁决） |
| `账本链完整性.alloy.md` | 哈希链账本 append-only 与篡改检测性 | `cbb2/ledger.py`（`line_hash` / `LedgerChain.verify` / `LedgedStore`） |

## 三不变式与源码对应表

收束期工单 G03 定义的三组属性（Hypothesis 侧对应 `tests/test_v3_properties.py`）与源码锚点：

| # | 不变式 | 一句话谓词 | 源码锚点 | 运行时测试锚点 | 规格落档 |
|---|---|---|---|---|---|
| 1 | **晋升单向性（confirmed-sink 写入面）** | 写入路径永不产出 confirmed；confirmed 仅能由 G5 票门晋升产生（≥⌈2/3⌉ 异构票 ∧ against=0 ∧ n≥2） | `cbb2/store.py` `write_decision` 各分支强制 `status="provisional"`（红队 P1-5 注释"confirmed 仅能由 G5 晋升产生"）；`cbb2/promote.py` `vote` 的 `need=math.ceil(2*full_size/3)` 与 `against>0→human` | `tests/test_v3_phased.py::test_vote_majority_and_swap_guard` / `test_vote_against_blocks_and_degrade`；`tests/test_v3_store.py::test_version_and_status_forgery_stripped` | `写入决策树.tla.md` 不变式 `PromotionMono` |
| 2 | **三态互斥（物理两态+隔离区第三态）** | 任一记录任一时刻恰处一态：confirmed/provisional 在 `libraries/<lib>/<status>/`（库里只有两态，B1），quarantine 在 `quarantine-zone/items.jsonl`（pending→confirmed/rejected） | `cbb2/store.py` `Store` 类注释（B1）、`_lib_path` 按 status 分目录；`cbb2/quarantine.py` `adjudicate`（verdict 合法=confirmed\|rejected） | `tests/test_v3_store.py` 全套（三态分轨断言）；`tests/test_v3_properties.py::test_write_decision_total`（track ∈ 六轨集合） | `写入决策树.tla.md` 不变式 `TriStateDisjoint` |
| 3 | **决策树总性（任意输入必落五轨之一或抛已知 ValueError）** | ∀(incoming, at)：`write_decision` 返回结果 `track ∈ {on-create, consistent-duplicate, complementary-statement, invalidation-update, uncertain-coexist, contradiction}`，或抛已知校验 ValueError——不崩、不出未分类异常 | `cbb2/store.py` `write_decision` 全分支收口（`contradiction` 轨含 `register_conflict=False` 的不造件回落） | `tests/test_v3_properties.py::test_write_decision_total`（Hypothesis 30 例/次，TRACKS 集合断言）；`::test_idempotent_replay`（同输入重放不产生新库件） | `写入决策树.tla.md` 不变式 `Totality` |

审计哲学路三提案与本仓库实现的对应（提案措辞→v3 落地面）：

| 提案（调研 §C） | 提案措辞 | v3 实现落点 | 备注 |
|---|---|---|---|
| 提案 1 三态迁移合法性（ClaimLifecycle） | superseded/void 是 sink 不可复活（StateInv） | v3 写入面上 confirmed 为 sink（仅晋升产生）；库件本体不可变（`_write_immutable`），状态演进全部走 append-only 旁车日志（`transitions.jsonl`，R13"文件不动"） | 提案状态集 {draft, active, superseded, void} 与 v3 三态命名不同，映射关系见 `写入决策树.tla.md` §状态集 |
| 提案 2 失效记账完整性（supersede 原子对+无孤儿） | 接任者必须存活∧不自接∧失效链可回溯 | `cbb2/store.py` `supersede`（禁止同 id、version+1、`supersede-index.jsonl` 原子对）+ 失效记账分支（`invalidations.jsonl` 幂等键含时序，红队 P1-9） | 未单独建规格，属性由 `写入决策树.tla.md` 分支④覆盖 |
| 提案 3 哈希链 append-only 与链完整性 | Genesis 锚+逐行 prevHash/hash 自洽 | `cbb2/ledger.py` `line_hash`（排除 hash 键后 canonical JSON 的 sha256）+ `verify`（断链/哈希不匹配/序号不连续/账本外改动四查） | `账本链完整性.alloy.md` 全文 |

## 边界与诚实声明

- 本目录为**设计级伪代码**，不参与任何构建/测试流程；与代码的同步靠人工（修改 `write_decision`/`verify` 时应回来对表）。
- 工单 G03 判据中"Hypothesis 三组属性全绿"的运行时部分归 `tests/test_v3_properties.py`（已存在）；本目录只承担"规格文档在案"半边判据。
- Windows 环境无 TLC/Apalache/Alloy 可执行件验证记录——伪代码未经模型检查器实跑【待确认：如需 TLC/Alloy 实跑验证，需 POSIX 环境或工具安装后补】。
