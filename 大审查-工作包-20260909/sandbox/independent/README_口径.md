# 独立提取口径说明（衔尾蛇/data → xws_independent.jsonl）

- 提取者：独立数据提取工程师（从零开始，未参考任何先前提取结果）
- 提取日期：2026-09-08
- 输出：`sandbox/independent/xws_independent.jsonl`（每行一条记录，UTF-8，字段顺序固定为 schema 顺序）
- 失败/异常清单：`sandbox/independent/dirty_independent.txt`
- 提取脚本：`sandbox/independent/write_extract.txt`（`py -X utf8 write_extract.txt` 可复现，幂等覆盖输出）
- 辅助核验脚本：`inspect1~4.txt`（结构探查）、`verify1.txt`/`verify2.txt`（输出核验）

## 0. 总量

| 项 | 值 |
|---|---|
| data/ 目录扫描文件数 | 267（266 个 .json + 1 个 .jsonl） |
| 产出记录的文件数 | 264 |
| 无记录文件（3 个） | `meta_layer.json`（冻结参数/元层配置）、`tasks_seed1.json`（任务集定义 40/32/8）、`tasks_seed1_train_eval.json`（train 集 query/expected 清单）——均为配置/任务定义，不含实验测量记录 |
| 输出记录总数 | 1473 |
| run_id 划分数 | 318 |
| dirty 条数 | 2（x2bc 重复异常，见 §5） |

## 1. 通用约定

- **run_id 命名**（全表一致）：
  - 一文件=一次实验运行的：run_id = 文件名去 `.json`（如 `x2_clean-G3-s2`、`x3-pseudo-G5-s12`、`x5_real-G4-drift-s1`、`x6b-PL-s3`、`x3c-G2-s7`）；
  - JSONL（x1_static.jsonl）：每行一个种子 run，run_id = `x1_static_s{seed}`；
  - 聚合/摘要文件：run_id = 文件名去后缀，必要时加子块后缀（如 `x3_summary_drift`、`x2d_stage2_R`、`x5_real_summary_g0`、`x6c_e32-A-held-s1`、`x6c_e32_top8`）。
  - x6c 行级 run_id 中 `自称A→A`、`实测B→B`。
- **round（代数/轮次）**：本实验群的 G0/G1/G2..G6 是"库/参数代数"（依据 `reports/X1_静态基线.md`：G0=v3 默认参数，G1=一次性人工调参，G2..G6=演化代数组），故 G 映射为 round 的数字部分。x2_clean 文件内 `log` 的 `gen`(1..25) 是该 run 内逐代记录，映射为 round。x2d_stage1 的 pre/post（wrap-up 前后）映射 0/1。P/PL（x6b）、default/evolved（x2d_stage2）、lib/set（x6c）是"臂/组"而非代数概念，round=null。
- **notes_raw**：一律为原文逐字摘录（从锚点行起、≤200 字符，多行保留换行）。已程序化核验 1473 条全部是原文自 raw_line_no 起的逐字前缀（verify1.txt，异常 0）。
- **raw_line_no**：多行 pretty-printed JSON 用"顺序游标锚点"定位（每记录在原文中找其首个特征键所在行，按文件内出现顺序推进）；单记录小文件（x3-*/x5_real-*/x6b-*）=1；JSONL=行号。核验无回退（无一条走到 fallback=1 的 dirty）。
- **数值不猜**：所有 gen_score/adopt_count 均直接取自原文字段；`"8/8"` 类分式只取分子作为采纳数（即采纳种子/次数），分母在 notes_raw 里保留原文。

## 2. 逐文件族口径表

| 文件族 | 记录数 | run 划分 | round | gen_score（主分数）及理由 | adopt_count | drift_flag |
|---|---|---|---|---|---|---|
| `x1_static.jsonl` | 16（8 行×2） | 每种子一 run（8） | G0→0，G1→1 | `G0_audit_U` / `G1_audit_U`：审计集效用（X1 口径：audit 永不参与演化，是金标主分数；train/held 在 notes_raw） | null | null |
| `x0_equivalence.json` | 1 | 1 | null | null（等价性检验无数值主分） | null | `not equivalent`（=false：无不一致） |
| `x0_results.json` | 11（10 步+1 基线） | 1 | 基线 G0→0 | 步骤=null；基线=`baseline.audit.utility`（-0.4062，audit 金标口径） | null | 步骤=`not ok`（检出=失败；本批全 false） |
| `x1_probes.json` | 4 | 每探针一 run（4） | null | 并发/截断/遗忘=null（无数值分）；配对块=`mean`（+0.793，G1−G0 配对差均值，Δ口径） | null | 并发=true（丢更新 30/40 实测发生）；截断=`set_layer_flagged`；遗忘=`doctor_caught_manual_edit`；配对=null |
| `x2_clean-G*-s*.json`（40 文件） | 1040（40×26） | 每文件一 run（40） | result=G 组号；log=gen 1..25 | result=`audit_U`（审计集效用，金标）；log=`train_U`（日志逐代仅含训练集 U，别无选择，见 notes_raw） | log=`promoted`（晋升次数）；result=null | null |
| `x2_clean_summary.json` | 6 | 1 | G1..G6→1..6 | G2..G6=`audit_U_mean`；G1 及格线=null（0.793 是阈值非分数，值在 notes_raw） | null | null |
| `x24_summary.json` | 5 | 1 | 按 G：H1→4、H2_G2→2、H2_G4→4 | `mean`（ΔG0 口径） | 采纳w_f1 分子（19、17） | null |
| `x2bc_results*.json`（3 文件） | 84（28×3） | 每文件一 run（3） | null | pure_greedy/w_imp_scan=`train`（作弊构型训练集 U，族内主指标）；x2c rows=`A_end`（演化后存档 UA 终值）；retention 均值=保持率（独立口径） | x2c rows=`b_promos`（B 晋升数） | null（verdict_作弊不可表达、v1_否定性登记只入 notes） |
| `x2d_R_entries.json` | 3 | 1 | null | null（库内容条目，非测量） | null | null |
| `x2d_stage1.json` | 5 | 1 | pre→0、post→1 | 四臂各=`audit_U` | null | reflect_triggered 单列 1 条=true（触发） |
| `x2d_stage2.json` | 7 | 4（R/C/compare/ctrl） | null（臂非代数） | R/C 四臂=`audit_U`；compare=null（保持率类，不与 U 混） | null | null |
| `x3-{clean,drift,noisecorr,noiseind,pseudo}-G*-s*.json`（144 文件） | 144 | 每文件一 run（144） | G 组号 | `audit_U_true`（真实效用——X3 系防"自报偏高"专门给的真实口径，优于自报字段） | null | `detect_gen != null`（检出=漂移被检测到；clean 等场景字段存在而未检出→false） |
| `x3c-G*-s*.json`（24 文件） | 24 | 每文件一 run（24） | G 组号 | 同上 `audit_U_true` | null | 同上 |
| `x3_summary.json` | 12（4 场景×3 组） | 每场景一 run（4） | G 组号 | `dG0_mean`（ΔG0 口径，摘要层唯一可比主指标） | `adopt_w_f1` 分子 | `detect_gens` 非空→true（仅 drift/G5） |
| `x3b_valley.json` | 9（8 行+1 摘要） | 2 | null | 行=`L_u`（每种子观测到的局部/谷底效用；`G_u` 为全局常量 0.8238，在 notes_raw）；摘要=null | null | 行=`valley`（该种子检出山谷）；摘要=null |
| `x3c_summary.json` | 4（3 组+E80） | 1 | G 组号（E80=null） | G 组=`dG0_mean`（Δ口径）；E80 检验=null（差值统计量不与 U 混，值在 notes_raw） | `adopt_w_f1` 分子 | G 组同上 |
| `x4_results.json` | 4 | 1 | null | V1=`jaccard`（重建等价度，该记录主指标）；V2/V3/V4=null | null | V2=`accum != expected`（本批 false：40/40 无丢失）；V3=`snapshot_tip != recomputed_tip`（true：截断被 tip 检出）；V1/V4=null |
| `x5_real-G*-s*.json`（20 文件） | 20 | 每文件一 run（20） | G 组号 | `audit_true.mrr`：真实语料无主题元数据，只给 recall5/mrr；recall5 在 G0 已饱和=1.0，MRR 是唯一有区分度的主分数（x5_real_summary 的 g0 佐证：audit_recall5=1.0 而 audit_mrr∈[0.27,0.6]） | null | null |
| `x5_real_summary.json` | 5（仅 g0） | 1 | 0（G0） | `audit_mrr`（同上口径） | null | null |
| `x6a_summary.json` | 20（16 行+4 摘要） | 行=每行一 run（16）+摘要 1 | 行=G 组号 | 行=`audit_U_true`；摘要 G2/G4=`审计ΔU均值`（Δ口径）；操纵检查/H2判定=null（结论文本入 notes） | 摘要=`采纳w_f1` 分子（5、6） | null |
| `x6b-P/PL-s*.json`（16 文件） | 16 | 每文件一 run（16） | null（P/PL 是臂不是代数） | `audit_U`（与全库 U 口径一致；kw_recall/audit_recall5 差异见 notes_raw） | `links_added`（链接算子采纳的提议数） | null |
| `x6b_summary.json` | 3 | 1 | null | P/PL=`audit_U_mean` | `links_total`（0、33） | null；判定文本单列 1 条 |
| `x6c_e32_summary.json` | 30（2 摘要+20 行+8 top8） | 行=每行一 run（20）+摘要 1+top8 1 | null（lib/set 是臂） | 行=`mrr`（同 x5 口径）；摘要=`mrr增益`（A−B，Δ口径）；top8=实测重要度分值 | null | null |

## 3. 主分数口径速览（重点族）

- **x2_ 族**：终态=`audit_U`（审计集效用，金标）；逐代 log=`train_U`（原文逐代只给这个）；x2bc 作弊构型=`train`、存档=`A_end`；x2d 各臂=`audit_U`；摘要层=`audit_U_mean` 或 `dG0_mean`/`mean`（Δ口径，已注明）。
- **x3_ 族**：一律 `audit_U_true`（真实效用口径）；摘要层 `dG0_mean`（ΔG0）。
- **x5_ 族**（真实语料）：`audit_true.mrr` / `audit_mrr`（recall5 已饱和无区分度）。
- **x6b_ 族**：`audit_U` / `audit_U_mean`（区分度实际在 kw_recall/audit_recall，保留于 notes_raw）。
- **x1_static**：`G0_audit_U` / `G1_audit_U`（每行拆 2 条记录，round=0/1）。

## 4. 去重决策（避免同数据双份记录）

以下嵌入块与独立文件逐一比对**完全相等**后跳过嵌入块，只保留独立文件一侧：

1. `x5_real_summary.json` 的 `results.*` 四个数组（20 元素）≡ 20 个 `x5_real-*.json` 文件内容；
2. `x6b_summary.json` 的 `rows`（16 元素）≡ 16 个 `x6b-*.json` 文件内容；
3. `x2d_stage2.json` 的 `r_entries` ≡ `x2d_R_entries.json`（R-1/2/3），取独立文件为准；`ctrl`（R-CTRL）为独有，保留 1 条。

## 5. dirty 清单（2 条，均非解析失败，为语义异常登记）

- `x2bc_results.json` 与 `x2bc_results_coef0.08.json` **字节级完全相同**（sha256 前 16 位 028be96e99a05516），且数据内无 coef 字段可区分两文件对应的系数取值——语义不明，登记之；两文件仍各自按原样提取（raw_file 可区分），下游合并需按内容去重。`x2bc_results_coef0.25.json` 与两者在 x2c 数值上确有差异，是独立运行。

## 6. 明确跳过的非记录性内容（均无测量值）

各文件的 `wall_s/wall_total_s`、`ts`、`merkle16`、`doctor/doctor_ok`（布尔已含于 notes_raw）、`meta_layer` 全部、tasks 两文件、`x2d_stage1.materials_file/wrapup` 文本、`x3_summary.compound_watch`、`x2bc.x2c.version`、`x5_real_summary.note/n_entries/n_tasks`、`x0_results.verdict/absorb_mode/gate_ok` 等结论文本（X0 步骤明细已逐条提取）。x3-clean 仅存在 G4-s9..s24（无 s1..s8 与其他组文件），x3-pseudo G2/G4 为 24 种子、G5 为 8 种子——这是原始覆盖面如此，非提取遗漏。

## 7. 校验记录

- 1473 行全部可被 `json.loads` 解析；字段名/顺序与 schema 一致；
- notes_raw 长度 ≤200 且逐字为原文前缀（0 异常）；
- round/drift_flag 类型检查（0 异常）；gen_score 非空 1435 条、adopt_count 非空 1085 条、drift=true 28 条（x3-drift-G5 全 8、x3c-G5 全 8、x3b 山谷 5、探针 3、reflect 1、x3/x3c 摘要各 1、x4-V3 1）。
