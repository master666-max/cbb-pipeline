# mutmut 变异对象清单（G06 · 以"清单在案"态收口）

> 工单出处：`全量重构-总工单-收束期-20260927.md` G06——"mutmut 试点：WSL/Linux 不可用则记录为'需 POSIX 环境'，先出变异对象清单。判据：清单在案+（如可跑）幸存者报告"。
> 工具结论（照录 `前沿工具调研-形式化与测试一路-20260927.md` Q2）：mutmut v3.8.0（2026-09-12，BSD-3）——**硬限制：POSIX only（fork），Windows 需 WSL/Linux CI**。
> 定位纪律（同调研文件）：变异分数是**趋势型审计指标，不是硬 KPI**（arXiv:2606.10417 实证行为盲区 17.5%）；每个幸存变异体翻译成一条新断言（B5 金丝雀升级口径），`mutate_only_covered_lines` + pragma 排除样板。

## 风险排序与逐项清单

排序原则：离"错误入库/错误放行"越近风险越高。对象与调用面全部以 `cbb-v2/cbb2/` 现源码为准。

### 1. `cbb2/store.py` · `write_decision` 五分支（风险最高：v3 唯一写入入口）

| 变异什么 | 哪条测试应杀死 | 幸存 = 什么缺陷信号 |
|---|---|---|
| `rec["status"] = "provisional"`（①④⑤ 分支）改成其他值/放过 incoming 自带 status | `tests/test_v3_store.py::test_version_and_status_forgery_stripped`；`test_v3_properties.py::test_write_decision_total`（track 集合不变，但 status 伪造需 store 断言抓） | 红队 P1-5 病灶复活：confirmed 免审直入，G5 票门被架空 |
| `rec["version"] = 1` 与 `rec.pop("supersedes", None)`（①④⑤）删除/放过 caller 值 | `test_v3_store.py::test_version_and_status_forgery_stripped` | 红队 P0-2 复活：version/status 伪造劫持身份解析与版本链 |
| `_admit_unique` 撞名改派 `-x{n}` 循环（改后缀/吞循环/返回旧 rid） | `test_v3_store.py::test_rid_collision_never_silent`；`test_v3_properties.py::test_idempotent_replay` | 红队 P0-1 复活：rid 撞名静默吞件+假成功回执 |
| `_tv_lt` 的 `<` 改 `<=`、缺位返回 False 改 True、ch 前缀比较改字符串序 | `test_v3_store.py::test_invalidation_mutable_with_temporal_order` / `test_mutable_without_temporal_order_falls_to_gate` / `test_caller_t_valid_not_trusted_for_ordering` | 时序洗白：相等时点/缺证据章也判"更新"，分支④把旧知识反向失效（拿旧知否新知的镜像病） |
| 分支④前提 `not imm and mut` 条件弱化（immutable/unclassified 混入也走失效） | `test_v3_store.py::test_immutable_conflict_routes_gate` / `test_entity_type_refinement_is_invalidation` | 不可变断言被自动失效——R10 攻击面（真矛盾洗白）重新打开 |
| `_append_complementary` 哈希域字段删减（去 about/at/证据） | `test_v3_store.py::test_complementary_event_id_scope`；`test_sidecar_idempotent_under_ledger` | 红队 P1-3 复活：不同记录/时点的互补事件 id 碰撞，互收对方的陈述 |
| invalidations 幂等键 `key=f"{rid}|{new_tv}|{at}"` 字段删减 | `test_v3_store.py::test_invalidation_mutable_with_temporal_order`（同时点二次失效场景属属性面：`test_idempotent_replay`） | 红队 P1-9/B3 复活：第二笔失效记账被幂等键误吞 |
| `_consistent_duplicate_v1` 的证据子集守卫 `_ev_set(incoming) <= _ev_set(existing)`、`CORROBORATION_BUMP` 的 `min/max` 算术 | `test_v3_store.py::test_on_create_and_consistent_duplicate_semantics_kept`；`test_v3_properties.py::test_idempotent_replay` | P-017 幂等守卫失效（重放膨胀版本链）或置信合成方向反（取 min 不取 max+BUMP）——等价锚面语义漂移 |
| `register_conflict=False` 早退分支删改 | `test_v3_store.py` contradiction 轨断言（重分流不反向造隔离件=彩排抓 bug #3） | 重分流场景污染 items.jsonl 顺序（A06 真库病灶复发） |

### 2. `cbb2/ledger.py` · `line_hash` / `verify`（账本可信性根基）

| 变异什么 | 哪条测试应杀死 | 幸存 = 什么缺陷信号 |
|---|---|---|
| `line_hash` 排除 `hash` 键的逻辑删除（载荷自含旧 hash 参与哈希） | `test_v3_properties.py::test_ledger_chain_recompute`（构链即入账，自引用会立即使 verify 不 ok） | 账本从第一行起全链报错——链可用性崩塌（比漏检响，但暴露构建/校验不对称） |
| `line_hash` 去 `sort_keys=True` / `ensure_ascii` 翻转 | `test_ledger_chain_recompute`（同进程写读一致，可能幸存！） | **跨实例/跨时点哈希不稳定**：同载荷算出不同 hash，篡改检测性依赖进程内缓存——读盘重算即断链。幸存者应翻译为"两次独立实例 line_hash 相等"断言 |
| `verify` 三查比较翻转/删除（`prev_hash != prev` 、`hash != line_hash(r)`、`seq != i+1`） | `test_v3_properties.py::test_tamper_detection`（单字节翻转必 ok=false）；`test_ledger_chain_recompute`（良构必 ok=true，防全报错变异） | **篡改漏检**：被改账本仍判 ok——审计学根基断裂（AS 1215 ¶.16 语义失效），最高优先级幸存者 |
| 坏行 `{"corrupt": …}` 占位分支删除（坏行直接抛异常） | `test_v3_properties.py` entry_strategy 保留 U+0085/U+2028 的行撕裂考题（间接）；坏行路径无专测【待确认：建议补坏行 fixture 直测】 | P-028 语义回归：审计工具对任意输入抛异常——"必须给判定，不许抛"口径被破坏 |
| corrupt 后 `prev_hash = None` 传导删除 | 同上（坏行直测缺位，可能幸存） | 坏行后续行断链被静默吞——损坏范围不可见 |
| `_rows` 的 `split(b"\n")` 变异回 `splitlines()` | 行撕裂考题间接（U+0085 在字符串值内时构行数变化→verify 报错，部分变异可被 `test_ledger_chain_recompute` 抓） | P-028 病灶复发：行内 Unicode 行分隔符撕碎 JSON |
| `idempotency_key_of` 键序（key/item_id/record_id）改序/删整对象哈希回落 | `test_v3_store.py::test_sidecar_idempotent_under_ledger` | 幂等键漂移：同件重放重复入账（账本膨胀）或异件误判同键（漏记账） |

### 3. `cbb2/promote.py` · `vote` 票门 need 计算（G5 晋升闸）

| 变异什么 | 哪条测试应杀死 | 幸存 = 什么缺陷信号 |
|---|---|---|
| `need = math.ceil(2 * full_size / 3)` 改 floor / 改 `len(votes)`（缩员口径） | `tests/test_v3_phased.py::test_vote_majority_and_swap_guard`（`need == 2` 精确断言）；`::test_vote_against_blocks_and_degrade`（单考官 support=1 < need=2 ⇒ hold，B13） | **B13 病灶复活**：缩员自动降门槛、单考官可晋升——无异构性可言的票决定正典 |
| `against > 0` 改 `>= 0`/`> 1`/删除 | `test_vote_against_blocks_and_degrade`（任何反对 ⇒ human） | 反对票被吞：真分歧信号直通晋升，"异构考官"设计失效 |
| `support >= need and n >= 2` 的 `and` 改 `or` / 删 `n >= 2` | `test_vote_against_blocks_and_degrade`（单考官 hold 断言） | 双考官下限失效（与 B13 同族） |
| `n == 0 → blocked` 分支删除/改 hold | `test_v3_phased.py` 票门断言（blocked 与 hold 口径不同：G5 阻塞 ≠ 存续待巡检） | 无考官时降级口径漂移——降级不显式标注 |
| `judge_isolated` 两序一致才采纳改单序采纳 | `test_vote_majority_and_swap_guard`（摇摆票 unsure 断言：两序不一 ⇒ unsure） | 位置偏见纠偏失效：答案对调设计名存实亡 |

### 4. `cbb2/schedule.py` · `solve_interval`（FSRS 调度反解）

| 变异什么 | 哪条测试应杀死 | 幸存 = 什么缺陷信号 |
|---|---|---|
| `max(1, round(S·log(r)/log(DECAY)))` 的 `max(1,…)` 删除 / `round` 改 `int`（floor） | `tests/test_v3_schedule.py::test_solve_interval_monotonic`（`solve_interval(1,0.9) >= 1` 且 S↑→N↑ 严格递增：S=5→1、S=10→2 两条路都压住 floor 变异） | 间隔为 0/负 ⇒ 巡检风暴（每区段全量复检）或永不巡检 |
| `log(DECAY)` 改 `log(r)`/符号翻转（`S·log(r)/log(DECAY)` 变形） | `test_solve_interval_monotonic`（`solve_interval(10,0.95) < solve_interval(10,0.90)` 双向单调断言） | FSRS 语义反装：目标保持率越高巡检越稀——半衰期调度失效 |
| 守卫 `stability <= 0 or target_r <= 0 or target_r >= 1 → return 1` 弱化/删除 | `test_solve_interval_monotonic` 首断言（S=1, r=0.9 合法路）；非法域路径无专测【待确认：建议补 S=0 / r=1 边界断言】 | 非法输入产 `ZeroDivisionError`/`ValueError`（log(≤0)）而非保守回落 1——调度器崩而非降级 |
| `record_check` 增长/衰减因子（×1.3 / ×0.5 / `max(1.0,…)` 下限） | `test_scheduler_pass_grows_fail_resets`（通过后 S 严格增、失败后严格降且不破下限的相对断言） | 巡检学习语义反转：通过反而缩间隔、失败后 S 跌破 1 又被守卫掩盖 |

### 5. `cbb2/contract.py` · `is_pseudo_date`（时间位门卫）

| 变异什么 | 哪条测试应杀死 | 幸存 = 什么缺陷信号 |
|---|---|---|
| 正则锚 `^…$` 删除、`{4}` 改 `+`、`ch\d{1,5}` 放宽 | `tests/test_v3_store.py::test_at_required_without_at_rejected` / `test_t_valid_format_rejected`（经 write_decision 间接杀） | 墙钟散文/任意串混入时间位——D-2/D-24"禁墙钟"防线穿孔 |
| `str(v)` 转型删除（非字符串输入直接走正则） | **无直接测试覆盖非字符串 at 路径**（属牲测试 at 只采样 chNNNN 字符串；store 测试均传字符串）——预期幸存 | 非字符串 at（如 int/None 以外类型）抛 TypeError 而非已知 ValueError——`写入决策树.tla.md` Totality 不变式的"已知异常族"出现缺口。幸存者应翻译为"at=20240101 ⇒ ValueError"断言 |
| `IGNORECASE` 删除 / `bool()` 包装删除 | 大概率**等价幸存**（调用面全传小写 ch/规范日期，大小写差异路径无考题） | `CH0014` 大写变体行为在调用方与 spec 间漂移——低危，幸存者可判等价变异归档而非补断言 |

### 6. `cbb2/governance.py` · `ConformalNLICalibrator` 分位数（conformal NLI 校准）

| 变异什么 | 哪条测试应杀死 | 幸存 = 什么缺陷信号 |
|---|---|---|
| `q = math.ceil((n + 1) * (1 - self.alpha)) - 1` 的 off-by-one 族（ceil→floor、`(n+1)`→`n`、`1-alpha`→`alpha`） | `tests/test_v3_governance.py::test_conformal_calibrate_and_predict`（n=10 固定向量：threshold>0 + 高分采纳/低分弃权两根边界） | 覆盖率保证漂移（α 语义变质）：弃权率失控——分流器退化为不设防（假矛盾入库）或全交人审（治理闭环空转）。现测试断言较粗（threshold>0），部分 off-by-one 可能幸存——幸存者应翻译为固定 score 向量的**精确阈值断言** |
| `idx = max(0, min(n - 1, q))` 夹取删除 | `test_conformal_calibrate_and_predict`（n=10, α=0.1 时 q=9 恰在界内，此变异大概率幸存——n<α 倒挂的小样本场景无考题）【待确认】 | 极小校准集下 IndexError/负索引——小样本崩而非拒绝（`len<10` 守卫挡住 n<10，故实际暴露面窄） |
| `len(labeled) < 10` 守卫改 `<=`/删除 | `test_conformal_calibrate_and_predict` 未考校准集下限——预期幸存 | 9 条判例也能"校准"——conformal 语义（有限样本交换性）失效而无人知 |
| `predict` 的 `abstain = nc > threshold` 比较翻转/`1.0 - score` 改 `score` | `test_conformal_calibrate_and_predict`（高分采纳 p1、低分弃权 p2 两向断言） | 分流方向反装：低自信放行、高自信弃权 |

## 幸存者处置口径

1. 幸存 ≠ 缺陷判决：先判**等价变异**（行为语义不变，如第 5 项 IGNORECASE），归档不追杀。
2. 非等价幸存者 ⇒ 翻译成一条**新断言**进对应 test 文件（B5 金丝雀升级口径），本清单"幸存"列即断言草稿。
3. badge/分数只做趋势审计指标，不进硬 KPI（调研 Q2 结论：coverage/kill score 是"实现中心"度量）。

## 环境与判据如实记录

- **mutmut 仅 POSIX（fork 机制），Windows 本机不可跑**（调研 Q2 硬限制原文：Windows 需 WSL/Linux CI）。
- 本单元判据按工单 G06 以**"清单在案"态收口**；**幸存者报告需 WSL/POSIX 环境**【待确认-环境就绪后补：跑法=WSL 下 `pip install mutmut`，pyproject 配 `[tool.mutmut]` 面向 `cbb2/` 定向 `mutmut run`，产出幸存变异体清单回填本文件】。
- 本清单所列"哪条测试应杀死"均以 `cbb-v2/tests/` 现存测试为准逐一核对（test_v3_store 18 条 / test_v3_phased 8 条 / test_v3_schedule 5 条 / test_v3_governance 4 条 / test_v3_properties 4 条 / test_v3_contract 4 条）；标注【待确认】处为测试覆盖缺口的如实登记，非杜撰结论。
