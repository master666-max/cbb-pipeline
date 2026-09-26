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

- GitHub 推送：git 协议两种后端均被阻（反代不吃 smart-http POST，P-025 同族）；REST 通道脚本 `tools/rest_push_phasea.py`（146 件 diff，基=远端 fd0fd6a 树）——**已执行**，远端确认 e297db6
- 人工桶 268 件清单待用户/下相处置（词根全异 71 建议逐条裁决；无 detail 188 建议按 detail 类型分桶）
- 信息保全 186 条：被舍弃更富值 human review（预期大头是「人物→人物(xxx)」精化值的反向情形）
- profiles `_review` 标记待人工审定后去除
- Phase B 入口：derive 模块（归属单键 ns/双时序列/债务 repay/D-21 拔除）

---

# Phase B 投影派生层（2026-09-27 收口）

| 单元 | 状态 | 判据留痕 |
|---|---|---|
| B01 投影检查点 | ✅ | ProjectionCheckpoint 原子写/回卷检测，5/5 测试 |
| B02 归属单键+双时序 | ✅ | NS_PROPERTY="group_id" 写读同源（D-13 根治）；**真图端到端烟测 PASS**（owned=1/valid_at=ch0014 读回，烟测件已清理） |
| B03 债务 repay | ✅ | DebtLedger incur/repay FIFO、open_count 归零可达（D-14 根治） |
| B04 D-21/D-15 拔除 | ✅ | neo4j_export 双拷贝：CONTAINER 改 env CBB_NEO4J_CONTAINER 无默认、docker inspect 凭据通道删除、docker_start 无容器名拒猜；环境自检 docstring 对齐出厂默认 7474；编译+回归 OK |
| B05 Graphiti 退役 | ✅ | 退役登记 cbb/tools/legacy-退役-GRAPHITI-裁四-20260927.md（复活条件在案；文件迁移 legacy/ 随 Phase E 构建产物化） |

- 验收：test_v3_derive 5/5 + test_neo4j_export OK + test_环境自检 OK + D-13 活体烟测 PASS
- 遗留：投影检查点与 lightrag_live 接线随 Phase C（runner 编排）；ns 写侧历史节点补钉（SET group_id 回填）待下轮图导出时顺带

---

# Phase C runner 编排层（2026-09-27 收口）

| 单元 | 状态 | 判据留痕 |
|---|---|---|
| C01 门控动态切分 | ✅ | cbb2/splitting：场景软标签（分隔符/时间跳变/对话密度机械信号）+split_decision θ 三条件（θ_len/θ_scenes/θ_newent env 可调）+segment_blocks 保段切分；**旗标 CBB_DYNAMIC_SPLIT 默认 off**（off=整章+无分段，行为与 v2 等价） |
| C02 承接摘要+三层上下文包 | ✅ | cbb2/context：carry_summary ≤200 字机械生成；三层包（实体卡新颖性门控+滚动摘要+近窗）预算硬顶；**sticky/cooldown 时间性激活**（lorebook 移植）；先验非事实源口径随包 |
| C03 runner 总装 | ✅ | prepare_chapter（派工卡=切分判定+软标签+承接+包）/finalize_chapter（身份缓存批量 write_decision→lightrag 检查点推进）；幂等重放测试过（P-017 repeated） |
| C05 D-29 判据面 | ✅ | 检索层双拷贝：rerank=True 却降级 mechanical ⇒ 口径显式登记"D-29 判据：能力未接线"；结果增 rerank_requested 字段；test_检索层 10/10 回归 |

- 验收：test_v3_phasec 6/6 + test_检索层 10/10 回归 + 既有套件不回退
- 遗留：模型路由/输出两段式旗标（§7.3，待重抽窗定标）；检索层 rerank 活体探活依赖 8081 llama-server（本轮未启，降级判据会响）


---

# Phase D 治理层（2026-09-27 收口）

| 单元 | 状态 | 判据留痕 |
|---|---|---|
| D01 票数晋升 G5 | ✅ | cbb2/promote：考官 env 编制（LOCAL/DEEPSEEK/QWEN，base/model 全 env 禁硬编码；**QWEN key 回落 DASHSCOPE_API_KEY**）+隔离评审答案对调+against>0 即 human+缩员/缺席降级显式标注；8/8 测试 |
| D02 对样双轨 | ✅ | cbb2/audit：发现轨 suspicious_rank / 估计轨 stratified_sample+LQAS（失败数≤d 验收）/ **Wilson 95% 区间**（30/30 下限 ≈0.887 实证，点宣称禁用） |
| D03 植物捕获 | ✅ | cbb2/plant：plant/capture_rate 往返+miss 清单（独立性假设绕开） |
| D04 缺口队列 | ✅ | cbb2/gaps：契诃夫超期/词表缺口/植物 miss/NLI 分歧 四扫描器→缺口队列.jsonl |
| D05 ER 归一三段 | ✅ | cbb2/er：NFKC+括注剥离归一/blocking 键/margin 判决（0.85 绝对带废弃）+MergeLog 可撤销（split 一等公民） |

- 验收：test_v3_phased 8/8 + test_v3_ops_nli 5/5 回归
- 待外部条件：DASHSCOPE_API_KEY 设入用户级 env 后 QWEN 考官通道即激活（当前编制=LOCAL+DEEPSEEK 满足 ≥2/3；QWEN 入编=3/3 满编）；植物捕获实际运行为下一抽取窗
- 遗留：信息保全 186 review / 人工桶 268 处置 / profiles 人工审定 / 共进化闭环旗标（待重抽窗）

- **G5 满编活体评审**：三考官（LOCAL=tifa-14b/DEEPSEEK=deepseek-chat/QWEN=qwen3.8-flash）全部在列无缺席；真评一例：LOCAL=unsure、DEEPSEEK=support → verdict=hold（判据会响实证）；QWEN 缺票=端点 403（maas.qianwenaiapi.com 镜像与 key 配对待用户核对，官方兼容端点备选 dashscope.aliyuncs.com/compatible-mode/v1）——通道架构已通，仅凭据配对问题


---

# Phase E 发布产物化（2026-09-27 收口 · 全量重构主体完成）

| 单元 | 状态 | 判据留痕 |
|---|---|---|
| E01 单命令构建 | ✅ | tools/build_release.py：build-managed 区同步（生产 cbb 六技能+contracts+tools、cbb-v2/cbb2 包）+退役族排除+HASHES.json manifest（123 件/89 py 编译）+--verify 复算模式——手改发布树即 FAIL（病1 拷贝漂移根治落地） |
| E02 发布树纠偏 | ✅ | test_graph_chain.py 从发布侧回收至生产源（发布独有件归源纪律）+重建 BUILT/verify ok |
| E03 import 冒烟 | ✅ | 发布布局 import：cbb2 全模块+六技能+contracts+核心工具全 OK（含负控制） |
| E04 发版说明 | ✅ | RELEASE-NOTES-v3.md：新东西 9 条/缺陷修复 13 条表/破坏性变更/env 契约/V6 重放指引 |
| E05 QWEN 诊断 | ✅ | 403=免费额度耗尽（端点/key 配对正确，/models 200 实证）；充值或关"仅免费"即激活；当前面板 LOCAL+DEEPSEEK 双编降级可用（判据会响） |

- **v3.0.0 发版**：tag 于 refactor/phase-a 远端提交（REST）；Qoder 消费者按 RELEASE-NOTES V6 节重放验收
- 全局：Phase A→E 全部收口；59 v3 测试全绿；PROVEN 等价锚不回退；开放缺陷 13 条修 11（余 4 条随后续批次）
