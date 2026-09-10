# progress.md · 多AI沙盒自演化实验总分析（断点续跑登记表）

> 规则：每阶段结束 git commit + 更新本文件。恢复时先读本文件，从断点继续，禁止重算已完成阶段。
> 目录约定：大审查/ 为工作根；8 个源文件夹=data（只读）；产出只写 unified/ sandbox/ reports/。
> 环境：`py -X utf8`；.py 会被 hook 拦，脚本一律写 .txt 后缀（如 sandbox/inv.py.txt），用 `py -X utf8 xxx.txt` 执行。

## 状态总览

| 阶段 | 状态 | commit | 产出 |
|---|---|---|---|
| 0 盘点 | ✅ 完成 | 4e7ec03 | reports/00-盘点.md、reports/00-inventory.tsv（40521 文件全量清单）、sandbox/inv.py.txt |
| 1 归一化 | ✅ 完成 | ff2210b | reports/01-归一化.md、unified/*.jsonl×5（2593行/1320run）、unified/dirty/（1条）、sandbox/norm_*.txt×5 |
| 2 分析器自测门 | ✅ 完成 | （本阶段 commit） | sandbox/analyze.txt、sandbox/synth/×4、sandbox/合成自测答案.md（PASS）、sandbox/metrics_real.json、reports/02-统计.md |
| 3 机械标记 | ⬜ 未开始 | — | — |
| 4 独立校验 | ⬜ 未开始 | — | — |
| 5 综合研判 | ⬜ 未开始 | — | — |
| 6 终报 | ⬜ 未开始 | — | — |

## 已完成阶段要点

### 阶段0（2026-09-09）
- git 基线 commit `e6a1d19`（8 源原始快照，只读基线）。
- 全库 40,521 文件 / 37,423,329 字节。体量最大源=衔尾蛇（40,423 文件，其中 data/ 264 个 JSON/JSONL 为核心结果，sandbox/ 40,104 为实验产物库）。
- 可提取性预判：A级=衔尾蛇data；B级=deepseek/混元/豆包agora/衔尾蛇reports 的 md；C级（预期0提取）=glm/qwen/复审/统合报告/工单类。
- 关键结构发现：衔尾蛇 x2_*.json 结构为 `{"result":{...}, "log":[{gen,promoted,mainline,train_U}...]}`，直接映射 schema（round=gen, gen_score=train_U, adopt_count=promoted）。

### 阶段1（2026-09-09）
- **unified 5 文件共 2,593 行 / 1,320 run / 1 脏行**（豆包agora E10"∞"）。映射口径逐表登记于 reports/01-归一化.md §2。
- schema 扩展 1 个机械溯源字段 raw_file（无新增语义字段）。
- 交叉校验结果（代码输出）：①衔尾蛇 X1报告 vs x1_static.jsonl 同 run 同 round **16/16 一致**；②deepseek 结果报告 vs 综合报告 **30 对重复 0 冲突**；③混元 E14 已现 3 组同 run 不同值（第四轮缓存bug数据 vs 第五轮重跑）——阶段3 将正式打标 DUP_CONFLICT。
- x1_static 的 gen_score=G{n}_audit_U（审计口径，与 X1 报告表对齐；train/held 整行逐字留档）。
- C级源（glm/qwen/复审/统合报告）grep 核验无数值实验表，0 行登记。

## 下阶段入口信息（阶段2）
- 数据读取：`glob unified/*.jsonl`（5 文件；source 字段区分源；衔尾蛇=衔尾蛇.jsonl+衔尾蛇reports.jsonl 两个文件同 source）。
- 需算指标：各 run 留出集/主分曲线（round 非 null 的行）、采纳率（adopt_count 非空行/run 总代数）、漂移检出代数（drift_flag=true 行的 round）、护栏触发次数（drift_flag=true 行计数；md 表的审计触发类列仅在 notes_raw）、代际提升斜率（round≥3 且 gen_score 非空的 run 线性拟合斜率）。
- 已知坑：round=null 行是终态/汇总行，序列类指标必须过滤；x2_clean 的 gen_score=train_U（逐代），x3/x5/x1=audit 口径，跨族不直接比较。
- 自测门：先造 3 份合成数据（手算答案记录在 sandbox/合成自测答案.md），analyze.py 输出与手算完全一致才许跑真实数据；脚本+用例+答案存 sandbox/。

## 阶段1登记表（逐源）
| 源 | 状态 | 输出行数 | 脏行数 | 备注 |
|---|---|---|---|---|
| 衔尾蛇 data/ | ✅ | 1464 | 0 | 22 个汇总/输入文件 0 行登记 |
| 衔尾蛇 reports/ | ✅ | 21 | 0 | X1 交叉校验 16/16 一致 |
| deepseek | ✅ | 74 | 0 | 跨文件 30 对重复 0 冲突 |
| 混元 | ✅ | 627 | 0 | E14 三组值待阶段3 打标 |
| 豆包 | ✅ | 407 | 1 | E10"∞"入脏 |
| glm/qwen/复审/统合报告 | ✅ | 0 | 0 | C级核验无实验数值表 |

### 阶段2（2026-09-09）
- 自测门 **PASS**（字符串级）：sandbox/run_selftest.txt 比对 analyze.txt vs 手算 expected.json。
- 修正两处后再次 PASS：①--out 参数解析；②x5_real 的 audit 为双指标字典→gen_score=null+逐字块（01-归一化.md 已同步登记）。
- 真实数据指标：sandbox/metrics_real.json（1312 run）。54 run 可算斜率；39 次护栏触发；61 run 有采纳数据。要点见 reports/02-统计.md。
- 下阶段入口（阶段3）：flag 规则表见任务书；DUP_CONFLICT 判定采用"同(source,run_id,round)存在≥2个不同非空 gen_score"；每条 flag 附 notes_raw/原行逐字摘录≤200字；产出 reports/03-flags.md + sandbox/flags.json。

### 阶段3（2026-09-09）
- sandbox/flagger.txt 按固定规则表打标：**139 条 flag**（SUSPECT_JUMP 75 / INCOMPLETE 53 / DUP_CONFLICT 6 / STALLED 5 / CONTRADICTION 0），0 条无摘录丢弃。全量：sandbox/flags.json；解读与分布：reports/03-flags.md。
- DUP_CONFLICT=混元E14 跨轮次双值（缓存bug语境）；STALLED 全部 x2_clean（采纳后 20+ 代同分）；INCOMPLETE 多为口径性命中（检出型/双指标终态）。
- 下阶段入口（阶段4）：挑体量最大源=衔尾蛇（40,423 文件；其中结构化提取主账=unified/衔尾蛇.jsonl+衔尾蛇reports.jsonl）。子代理只给：data/ 原始文件清单 + schema 定义 + X0/X1 报告路径，禁止透露主线任何产物；让其独立输出提取 JSONL 到 sandbox/independent/；逐行 diff 出 reports/04-diff.md，分歧不裁决。

### 阶段4（2026-09-09）
- 隔离子代理（agent_f0cf39b0，general-purpose）独立重提取衔尾蛇：1,473 行/318 run/2 脏，口径自决（sandbox/independent/）。
- 逐行 diff（sandbox/diff_calc.txt + diff_stats.json）：**共同锚点 1,008 条四字段零分歧**；差异全为口径类（切分粒度/round 语义/主分口径/汇总文件是否入库/x2bc 重复脏行）。报告：reports/04-diff.md（双列并陈，不裁决）。
- 旁证：子代理 x2bc 字节级重复主张与阶段0 清单 SHA1 吻合（99b619df=99b619df）。
- 下阶段入口（阶段5）：只引用 reports/00-04 + unified/notes_raw + flags.json 摘录 + metrics_real.json；三问：跨实验稳健结论（≥3独立AI同方向）/互相矛盾点/可信度存疑 run。证据格式：源名+run_id+行号+摘录。

### 阶段5（2026-09-09）
- reports/05-研判.md：①R1-R6 跨实验稳健结论（4数据源内判定，每条 源+run_id+行号+逐字摘录）；②C1-C6 矛盾点双列并陈（含 E14 双值、E41/E42 与 E54/E113 跨轮反转、E25 零检出反例、护栏代价方向对立）；③可信度存疑清单（E14 第四轮侧/x2bc 字节级重复/重复md 383ec344/高flag密度8run/x5与检出型INCOMPLETE族/∞脏行）。
- 下阶段入口（阶段6）：99-FINAL.md 三层置信度分档（机械事实/提取事实/研判推断）+ 各源脏行率表 + flag 总表 + diff 要点 + 合成自测记录；commit message=final。

### 阶段6（2026-09-09）
- reports/99-FINAL.md：三层置信度分档（机械事实6条/提取事实7条/研判推断4条）+ 四附表（脏行率/flag总表/diff要点/合成自测记录）。
- 全流程收口：7 个 commit（baseline→…→final）。恢复点=本文件；如需复核从 99-FINAL.md 的出处列回溯。

---

# PART II · 开放式自演化研究循环（2026-09-09 启动，新任务书）

## 文件移动清单（铁律"移动前先出清单"）
| 原路径 | 新路径 | sha256（移动前后不变） | 理由 |
|---|---|---|---|
| reports/99-FINAL.md | reports/06-ANALYSIS-FINAL.md | 2565ae79801f44278e97da66abaf37c95ee8b6dadd3a2d1522ebf864e05c570a | 新任务书规定阶段6产出=06-ANALYSIS-FINAL.md，99-FINAL.md 路径留给 PART IV 总终报；内容未改动，git mv 保全历史 |

## PART II 状态总览
| 轮次 | 状态 | commit | 产出 |
|---|---|---|---|
| 基建 | ✅ | 3b14c3b（随 round-1） | data-archive.csv、directions.csv、lab-notebook.md、meta_log.csv、sandbox/meta/registry.md、sandbox/meta_metrics.txt（修复2处标记解析bug后机测=自填） |
| Round 1 | ✅ | 3b14c3b | round-1-预注册/报告、judge_r1_adoption.txt（SELFTEST 8/8，锁定后修 chdir bug 已补记 registry v2=068ef85e）。结果：假采纳率0/176 SUPPORTED / 复合变更不占优 REFUTED / 首采纳弱主导0.5127 SUPPORTED |
| Round 2 | ✅ | （本轮 commit） | round-2-预注册/报告、engine_r2、judge_r2_noise（SELFTEST 7/7）。结果：噪声敏感性机制成立但阈值先验错 REFUTED（0.085→0.433→0.546）/ margin内点最优 INCONCLUSIVE（+0.036 未达阈）。意外：平坦景观吸收假采纳代价。⚠registry写入晚于执行已登记 |
| Round 3 | ✅ | （本轮 commit） | round-3-预注册/报告、engine_r3、judge_r3_switch（先锁后跑✓，SELFTEST 12/12）。结果：E16强复现0.3782 SUPPORTED / Pareto缓解+0.343但塑性代价-0.066双INCONCLUSIVE（OBL-001）。自填meta_log一处反转错误差值保留 |
| Round 4 | ✅ | （本轮 commit） | round-4-预注册/报告、engine_r4、judge_r4_sharp（先锁后跑✓）。结果：吸收论边界坐实 SUPPORTED 0.3508双峰/塌缩双因素 INCONCLUSIVE（门控不对称论被修正） |
| Round 5 | ✅ | （本轮 commit） | round-5-预注册/报告、judge_r5_meta（SELFTEST 8/8先锁后跑; 自测门抓出2处手算错）。结果：早信号符号一致0.9268 SUPPORTED(r=0.36幅度弱) / 平台化0.875 SUPPORTED |
| R5-REVIEW | ✅ | 471375c | 5簇全满/证伪无共同原因/R6候选B2世界景观+反例约束 |
| Round 6 | ✅ | （本轮 commit） | round-6-预注册/报告、engine_r6、judge_r6_multipeak（先锁后跑✓）。双INCONCLUSIVE贴阈值（trap0.832/stay0.67）; OBL-003; 自填错×1（REVIEW_DRIVEN_n） |
| Round 7 | ✅ | （本轮 commit） | round-7-预注册/报告、judge_r7_stratify（v2）。双守卫INCONCLUSIVE：档案无小增益run(n=0)无其他源长序列(n=0)——R5双结论证据底盘=单族大增益; v1流程违规已记registry; 手算累计4错自测门全拦 |
| Round 8 | ✅ | （本轮 commit） | round-8-预注册/报告、engine_r8、judge_r8_twostage（先锁后跑✓）。双SUPPORTED：两阶段双轴占优margin加码（0.2991/0.7984 vs 0.3102/0.7648） |
| Round 9 | ✅ | （本轮 commit） | round-9 三件套（先锁后跑✓）。双SUPPORTED：两阶段尖峰不占优0.3372(收敛20%)/假采纳抑制保真0.5399——荒漠假采纳=探索功能件 |
| Round 10 | ✅ | （本轮 commit） | round-10 三件套（重放v2验证门全等）。NARRATIVE三区定律被REFUTED——真相U形(缓坡0.015<<峰0.32<荒漠0.854)/尖峰守卫INC |
| R10-REVIEW | ✅ | （本轮 commit） | 6簇/3证伪无共同原因/R11候选B6梯度信噪(与人工计划收敛) |
| Round 11 | ✅ | （本轮 commit） | round-11 三件套（重放验证门全等）。平坦梯度律SUPPORTED 0.89>0.61>0.16/尖峰守卫INC方向一致; registry hash事故当场修正 |
| Round 12 | ✅ | （本轮 commit） | round-12（v2）。红队失败=梯度律鲁棒(两套扰动带严格单调min gap 0.688)/池化跨世界SUPPORTED 0.848>0.592>0.160; 手算第5错+heredoc断链事故已记; 循环12轮终止 |
| PART IV 终报 | ✅ | final（本 commit） | sandbox/final_metrics.txt + reports/99-FINAL.md：七节全（三态清单/五曲线/红队战果/自述/诚实失败清单） |

## 全程收束
- 26 假设：12 SUPPORTED / 4 REFUTED / 10 INCONCLUSIVE；四类 source_type 齐备；停摆闸未触发。
- 核心机制成果：梯度定律（门控假采纳率=局部信噪比单调函数，跨世界/跨扰动带稳定）。
- 恢复点：本文件；如需复核任何数字 → sandbox/judges/（锁定判据）+ sandbox/out/（数据快照，hash 在 registry）。|

## 恢复入口（最新）
- 当前断点：PART II Round 1 未开始。基建文件已建。
- 每轮流程：拟题（读 data-archive.csv + lab-notebook.md + E 系列编号表）→ 预注册 reports/round-N-预注册.md → sha256 锁入 sandbox/meta/registry.md → 判据脚本 sandbox/judges/（自测 3 例）→ 执行 → 双轨记录 → 入档 → reports/round-N-报告.md → meta_log.csv + meta_check.txt 跑 → commit。
- E 系列结论源：../猴子记忆库推演/自演化推演_实验总报告17轮后.md（E1-E18）+ 后续轮次散布（E29-E80）；引用时只取编号+结论句。

## 任务后追加（2026-09-09）
- reflect 技能执行：R-007~009 入 knowledge/reflections.md（先验三区/门结构普适/账本腐坏），反思计数清零。
- 用户指令追加交付：reports/98-反思与报告.md（commit 03ea79f）——全程深度反思：科学层发现链收束/自我层校准测量/事故解读/下轮 7 建议。
