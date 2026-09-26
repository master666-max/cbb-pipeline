# PHASE-A BUILD-STATE（全量重构·Phase A 地基）—— 已收口

- 契约: v3.0.0-alpha | 词表: 类型映射 v1（词表类型映射-20260926.json，103 无争议+冲突清单）| 指纹: acceptance aafe38042b28f0c2（等价锚不回退）| 锚: v2-baseline(fd0fd6a0)
- 工单: 《全量重构-工单-PhaseA-地基-20260926.md》v1.0 | 开工 2026-09-26 | **收口 2026-09-26**

## 单元进度（终态）

| 单元 | 状态 | 判据留痕 |
|---|---|---|
| A00 开工门 | ✅ | tag v2-baseline；自检留痕 logs/环境自检-PhaseA开工-20260926.json（复跑翻红根因=docker/LM Studio 停机，离线先行偏差已登记；服务恢复后复检 E1/G1 READY） |
| A01 契约v3+profile | ✅ | profiles 六库草案（_review 待人工审定）；正负对照+宽容读旧测试 4/4；全库校验经 U-A06 真库 6,172 件扫描实证 |
| A02 store 写入决策树 | ✅ | 五分支 10/10 测试；一致重复面 82.0 不回退；at 缺参拒写 |
| A03 gate 健壮档 | ✅ | ensure_input 出码不崩 5/5；D-1/D-25 转绿 |
| A04 NLI 双通道+契约闸 | ✅ | 5/5；**活体冒烟**：本地 LLM 通道 entails/contradicts 两判真通（model=tifa-deepsex-14b-cot-chat via env）；Erlangshen 通道=惰性加载缺依赖即降级（py3.14 transformers 待装，BLOCKED 不阻塞） |
| A05 修前反例包 | ✅ | 13 条登记表（下表）；转绿 6 条 ≥5 达标；红证据=tests/修前反例-红证据-20260926.txt |
| A06 604 重分流 | ✅ | **预注册四判据全过**：dry-run 逐类一致 / 矛盾 pending 604→268（仅剩人工桶）/ 对样 20/20=100%（门槛≥95%）/ 账本零新增错误 |
| A07 词表类型映射 | ✅ | 映射表 103 无争议条 + 冲突变体清单（「人物→40+富值」类为逐件对齐场景，非全局映射场景） |
| A08 特征基线扩展 | ✅ | 8 面=5 锚（PROVEN 不回退）+3 v3 件（contract/store/gate）；金丝雀改坏→exit1→还原→exit0 |
| A09 收口 | ✅ | 本文件+交接文书+scoped commits |

## A06 执行结果（真库）

- executed **336**（richer/stored-vocab 现役全对齐→一致重复/互补陈述）| manual **268**（词根全异 71+无 detail 188+候选缺席 9）| **信息保全 186** 条（被舍弃的更富值，留人审）
- 真库现状：库件 6,278（+106 合并/失效新版本）；隔离区 confirmed 336 / pending 1,037（矛盾 268+推断 769）
- 账本：零新增错误（adjudicate 双行入账修复后）

## 彩排抓 bug 记录（演练副本 4 轮，真库零事故）

1. profile entity_type 误定 immutable → 实证三代精化链（人物→人物(迷宫生物)→人物(迷宫守护者)）改 mutable+失效记账（信息不丢，旧版本 t_invalid 留存）
2. zadjudicate 记账张冠李戴（items 的 sha 记到 adjudications 目标）→ 双行修复
3. residual 冲突反向注册新隔离件（污染 items.jsonl 顺序）→ register_conflict=False 参数化
4. executor 对齐语义改为**现役全对齐**（旧章候选反向失效新知识=拿旧知否新知，禁止）；被舍弃更富值入信息保全清单

## 反例包（13 条开放缺陷）状态

| 缺陷 | 状态 | 去向/证据 |
|---|---|---|
| D-1 canonical 串使门崩 | ✅ 转绿 | gate.ensure_input→G1-SCHEMA 码 |
| D-2 双轨隔离不透传 at | ✅ 转绿 | write_decision at 强制 |
| D-23 陈述位当断言位 | ✅ 转绿 | 互补陈述分支+修前红证据 |
| D-24 隔离件墙钟日期 | ✅ 转绿 | 同 D-2 |
| D-25 门无候选态输入档 | ✅ 转绿 | null id→哈希占位 |
| D-6 隔离件不存全文 | ✅ 转绿（加分） | 拦截件全文.jsonl |
| D-28 凭证在位即 READY | 🟩 机制已建 | 运行契约闸；v1 环境自检修补随 Phase B |
| D-13/D-14/D-15/D-21 | 🔜 Phase B | derive/config 单源 |
| D-18/D-19/D-20/D-27/D-29 | 🔜 Phase C | runner/CLI 卫生/检索面 |

## 验收记录

- 全套：24 v3 测试 + PROVEN 锚 + 金丝雀 + 真库对账 → `cbb-v2/logs-PhaseA验收-20260926.txt`
- A06 三件报告：logs/积压重分流-执行报告、logs/积压重分流-对样、积压重分流-人工桶/信息保全（迷深实战-工作区）

## 十轮自审记录（R1-R10，2026-09-26）

- R1 架构漂移：变更面=cbb-v2+白名单执行件+STATE/文档；`cbb/tools/` v1 生产件零改动（git diff 核对）✅
- R2 契约合规：全部写路径经 write_decision（at 强制+profile 分类）✅
- R3 幂等重放：sidecar 账本幂等（测试）+adjudicate 幂等包装+重跑跳过已裁决件 ✅
- R4 真缺陷：彩排抓 3 bug 全修；真库零事故 ✅
- R5 时间纪律：新增写路径全显式 at；墙钟残留面=quarantine._today 兜底（直调场景，登记 Phase B 修补）⚠️在案
- R6 零 LLM 红线：store/gate/contract/ledger 零 LLM；唯一 LLM 面=nli.py（只分流不裁决）✅
- R7 判据会响：金丝雀 改坏→exit1→还原→exit0 ✅
- R8 静默失败：executor 异常→人工桶带原因码；对样门 FAIL→exit1；残留=候选索引解析失败静默计数（实测=0）✅
- R9 跨件一致：归属键/端点本相未触；词表分类单源=profiles ✅
- R10 红队：真矛盾洗白攻击面=entity_type 改 mutable——缓解链=richer/vocab 对齐规则+时序序证+信息保全清单+对样 20/20；残余风险=LCS≥2 偶合误并（对样未见，登记 Phase B 加验）⚠️在案
- **出口门：R9/R10 两轮零新发现 ✅**

## 遗留与移交

- GitHub 推送：git 协议两种后端均被阻（反代不吃 smart-http POST，P-025 同族）；REST 通道脚本 `tools/rest_push_phasea.py`（146 件 diff，基=远端 fd0fd6a 树）
- 人工桶 268 件清单待用户/下相处置（词根全异 71 建议逐条裁决；无 detail 188 建议按 detail 类型分桶）
- 信息保全 186 条：被舍弃更富值 human review（预期大头是「人物→人物(xxx)」精化值的反向情形）
- profiles `_review` 标记待人工审定后去除
- Phase B 入口：derive 模块（归属单键 ns/双时序列/债务 repay/D-21 拔除）
