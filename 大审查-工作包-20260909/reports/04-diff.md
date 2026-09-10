# 04 · 独立校验 diff 报告（阶段4）

> 校验对象：体量最大源 **衔尾蛇**（40,423 文件；结构化提取主账 = data/ 264 文件 + 3 份报告表）。
> 子代理：全新 general-purpose 代理，上下文隔离（提示词仅含原始文件路径 + schema 定义 + 读写出入约束；明确禁止读取 unified/、reports/、sandbox/ 其余内容、progress.md、git 历史、其他源文件夹）。其口径自决文档：sandbox/independent/README_口径.md。
> 比对器：sandbox/diff_calc.txt（锚=(raw_file 规范化, raw_line_no)）；第二层按文件内 (round, gen_score, adopt_count, drift_flag) 元组对齐。全量差异明细：sandbox/diff_stats.json。
> **本报告只并陈，不裁决，不解释优劣。**

## 1. 总量对照
| | 主线（阶段1） | 子代理（独立） |
|---|---|---|
| 记录行数 | 1,485（衔尾蛇.jsonl 1,464 + 衔尾蛇reports.jsonl 21） | 1,473 |
| run 划分 | 252 + 12（去重后 256） | 318 |
| 脏行 | 0 | 2 |
| 处理文件 | data/ 264（22 个汇总/探针/输入文件登记为 0 行）+ 报告 3 表 | data/ 267（3 个配置文件无记录）+ 汇总/探针文件亦提取（213 行落在主线跳过清单内） |

## 2. 核心：共同锚点字段比对
- 共同锚点 **1,008** 条（同文件同行号）：**round / gen_score / adopt_count / drift_flag 四字段零分歧**（diff_stats.json `field_diff_records: 0`）。
- 即：两个独立提取在"落到同一原文行"的每一条记录上，数值完全一致。

## 3. 锚点不重合部分（459 仅主线 / 457 仅子代）——双列并陈
### 3.1 逐代 log（x2_clean 族）
| 主线 | 子代理 |
|---|---|
| 每文件 26 行：25 代行（round=gen, gs=train_U, ac=promoted, 锚在 `"gen":` 行）+ 1 行 result 汇总行（gs=**null**，锚在 `"held_U":` 行，notes 含 held/audit/train 三行逐字） | 每文件 26 行：25 代行（**与主线逐行同值同行号**，如 L26 gs=−0.5537 ac=0；L38 gs=0.2938 ac=1）+ 1 行终态行（gs=**audit_U**（G2-s1=0.85），round=**组号 2**，锚在 L12） |

### 3.2 x3 族（168 文件）
| 主线 | 子代理 |
|---|---|
| 每文件 2-3 行：G0 行（round=0, gs=g0_audit_U_true, 锚 g0 行）＋终态行（round=null, gs=audit_U_true, 锚 audit 行）＋检出行（drift_flag=true, round=detect_gen, 锚 detect_gen 行） | 每文件 1 行＋检出：终态行（gs=audit_U_true（与主线终态同值，如 0.85），round=**组号**（G2→2/G4→4/G5→5），drift_flag=**detect_gen!=null**（无检出=false），锚在文件头 L1） |

### 3.3 x5_real 族（20 文件）
| 主线 | 子代理 |
|---|---|
| 每文件 2 行：G0 行 + 终态行，gs 皆 **null**（audit 为 {recall5, mrr} 双指标字典，主线选择不选不猜，notes 逐字含双指标） | 每文件 1 行：终态行 gs=**mrr**（G6-clean-s5=1.0），round=组号 6 |

### 3.4 汇总/探针文件（主线跳过清单 22 个 vs 子代提取 213 行）
| 主线 | 子代理 |
|---|---|
| 登记为 0 行（聚合/探针/输入粒度，非 run×round；清单见 01-归一化.md §2.1） | 提取了 x0_*/x1_probes/x2bc*/x2d_*/x3b/x4_results/全部 *_summary（run 按子块划分，如 x2bc_results、x24_summary） |

### 3.5 报告表（X0/X1）
| 主线 | 子代理 |
|---|---|
| X1 每行拆 2 条（round=0/1, gs=G0/G1 审计效用）；X0 只取 audit 行；共 17+4 行 | 部分锚点与主线重合（值一致）；其余行因 round 口径差异落入单侧（语义层 only_mine R:X1=16） |

### 3.6 脏行
| 主线 | 子代理 |
|---|---|
| 0 | 2 条：x2bc_results.json 与 x2bc_results_coef0.08.json **字节级完全相同**且数据内无 coef 字段可区分（语义不明登记） |

## 4. 旁证（机械事实，非裁决）
- 子代理"x2bc 两文件字节级相同"的主张与主线阶段0 清单 SHA1 独立吻合：x2bc_results.json 与 x2bc_results_coef0.08.json 的 sha1_8 均为 `99b619df`，coef0.25 为 `9f1258d9`（reports/00-inventory.tsv）。
- 子代理自报其 notes_raw 经程序化核验 1473/1473 为原文逐字前缀（其 README 记录；主线未复核其核验过程，仅抽样比对未见出入）。

## 5. diff 结论的记录性陈述
两套提取在**所有共同锚点（1,008 条）上数值零分歧**；全部差异集中于：①记录切分粒度（G0 行/终态行是否独立成行）②flat 文件的 round 语义（null/0/detect_gen vs 组号）③个别主分数口径（train_U vs audit_U；null vs mrr）④汇总/探针文件是否入库⑤x2bc 重复文件的脏行处置。以上五类均为**口径选择差异**，未发现任何一条"同一原文行读出不同数字"的情形。
