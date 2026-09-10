# progress.md — 任务进度账本（固定 schema，防续跑风格漂移）

> 续跑会话第一步：运行 `py -X utf8 workspace-audit/tools/progress_hash.txt` 核对下表——
> 行数减少或哈希变动（git 基线 commit 之后的有意更新除外，见各阶段"产出登记"）→ 上游被篡改 → HALT。
> 基线 commit：`77fb1a0af30244d8d9846a2eedcc0f9b0916d2f3`（原工作区冻结点）。
> 注意：data/ 下原始数据与各账本只增不改（R7）；本表自身允许追加新阶段块。

---

## 阶段0 盘点与机械去重

- 进入时间：2026-09-09 ~18:10；完成时间：2026-09-09 ~19:05
- 产出登记（行数 + sha256 前16位，命令 `py -X utf8 workspace-audit/tools/progress_hash.txt`）：

| 文件 | 行数 | sha256[:16] |
|---|---|---|
| 00-PROMPT.md | 175 | b07c36c736133f97 |
| 00-盘点.md | 169 | 6d6e712186c74ea5 |
| 00-文献清单.md | 54 | 9c7e2ff680b6ec8e |
| 00-重复表.csv | 6759 | 1f062adef5fd6180 |
| audit-log.csv | 12 | aa33982c88a4ec21 |
| data/files.jsonl | 89768 | c22be34951922b4e |
| data/nested-repos-baseline.txt | 19 | bee66b570b8a63bd |

- 关键数字（命令存档）：89768 文件 / 1254.7 MiB（`tools/inventory_walk.txt`）；6758 重复组（`tools/inventory_summary.txt`）；676 个 citations.md 副本、24 个唯一 arXiv 号（`tools/arxiv_scan.txt`）。
- 关键分类决策（≤5）：
  1. 文献"新批次"判定为**无实体**：全库唯一 arXiv 号恰为 33 篇体系的 24 个 arXiv 子集，零体系外论文号——按 R3 登记【待确认】不裁决，三种解释并陈（见 00-文献清单.md 第四节）。
  2. bootstrap 包内"文献笔记库/综述"等 303–1801B 文件判为**模板**而非文献内容（骨架无实体论文）。
  3. glm/qwen/混元/豆包/deepseek 各分析报告判为**二次分析文献**（引用 33 篇体系做论证），非新文献。
  4. git 基线采用**三重覆盖**：根仓库 47730 文件 + files.jsonl 全量 89768 sha256 + 3 嵌套仓库 HEAD/status 快照（大审查 c31ad39 / 大审查-zcode e91bdef / 猴子记忆库推演 ad8b274）。
  5. 阶段0 抽检对象=00-文献清单.md 锚点断言（claim_ledger 尚未建立，属边界情况，抽检 id 用 `P0:文件:行` 形态）。
- 边界情况及处理：
  - 坏文件名 1 个（`语料分析/epub_extracted/text/400.*`，磁盘坏字节+surrogate）：git 不可索引，从基线豁免；sha256 已入 files.jsonl；00-盘点.md 设"乱码文件名清单"节登记。
  - 嵌套 git 仓库 3 个（大审查、大审查/zcode、猴子记忆库推演）：根仓库只记 gitlink，内部 4.2 万文件由 files.jsonl 覆盖；不动嵌套仓库自身（R1）。
  - 锚点抽检 1 条未命中（citations.md A14 行号 15→16 偏移）：audit-log.csv 追加更正行（R7 不删行），00-文献清单.md 同步修正，最终命中率 10/10。
- 未解决问题：
  - "新批次论文材料"实体缺失（【待确认】已登记，若用户后续放入新材料需追加清点）。
  - 根版总表 vs 修订版总表（14,279B vs 20,818B）内容差异未考——留给阶段1 版本谱系。
- 自检三问：断言均带锚点（两轴模型初版"该文件头部"不精确锚点已修正为 :4/:11/:14）；无合并矛盾（新批次缺口三解释并陈）；推定均标注【提取事实】/【研判推断】/【待确认】。

## 阶段0.5 试金石子集

- 进入时间：2026-09-09 ~19:10；完成时间：2026-09-09 ~19:50
- 产出登记（`py -X utf8 workspace-audit/tools/progress_hash.txt`）：

| 文件 | 行数 | sha256[:16] |
|---|---|---|
| 0.5-试金石.md | 36 | dc89c01ed7fb583d |
| claim_ledger.csv | 54 | ab594c2e956ff188 |
| supersede_log.csv | 3 | cc426805828c7ff2 |
| audit-log.csv | 55 | 3ac2b15d2da8c404 |

- 试金石样本：①sota-memory-radar.md（66行·短）②自演化推演_实验总报告17轮后.md（879行·长复杂）③规划书 v1 vs v1.1（多版本演化）。结果：现行 51 条断言 100% 逐字命中、幂等全 PASS、200 字上限/锚重叠检查硬执行、supersede 链（v1:44→v1.1:49）工作正常。
- 关键分类决策（≤5）：
  1. **摘录入账纪律修订**：试金石#2 抓出手抄错误（2/39），改为一律 `ledger_add_extract()` 起止锚程序化截取，禁止手抄——已写入 0.5-试金石.md，阶段2 强制执行。
  2. **supersede 机制落位**：supersede_log.csv 独立于账本（R7 append-only 纯净），ledger_tool/ledger_verify 联动过滤。
  3. **experiment_id 宇宙前缀制**：SIM-*（离线推演）/REAL-*（真引擎沙盒）/RADAR（文献雷达）等，防同名实验撞车，阶段1 alias_map 正式化。
  4. 长实验报告（混元总报告）判 source_type=document（结构化实验报告非会话导出）；AI 作者自评语句未入账。
- 边界情况及处理：
  - 试金石#3 两条 extract 锚重叠/超长被当场拦截（规则生效的证据），缩短锚点后重跑通过。
  - spotcheck_p05 打印措辞 bug（"尾数7规则生效"实为全抽分支），行为正确不影响数据；audit-log 如实记录 43 条全抽。
- 未解决问题：
  - 提示词阶段7 所指 E28"对未收敛物强行固化"与 SIM-E28"层次化归并"名实差异待阶段1 澄清（可能有另一宇宙的 E28 或提示词记忆偏差）——已登记，不裁决。
- 自检三问：断言均带锚点；矛盾（名实差异）并陈登记；推定与机械事实分层标注。

## 阶段1 实体规范化

- 进入时间：2026-09-09 ~19:55；完成时间：2026-09-09 ~20:50
- 产出登记（`py -X utf8 workspace-audit/tools/progress_hash.txt`）：

| 文件 | 行数 | sha256[:16] |
|---|---|---|
| 1-实体总表.md | 45 | e015fd337bd05e41 |
| 1-版本谱系.md | 66 | a88ee1e950a2dc3f |
| alias_map.csv | 51 | 76de419324bdae0f |
| participants.csv | 15 | e9e4223dd2ef84f4 |
| mechanism-registry.csv | 46 | 597c60b269599db2 |

- 关键分类决策（≤5）：
  1. **宇宙前缀制正式化**：SIM（混元离线推演）/REAL（衔尾蛇）/R2（第二批）/DS/PART2/VERIF/DB-AGORA/DB-MEMEVO/CB/GLM-WEB/QWEN/PART1 共 12 宇宙；E81 澄清为跨宇宙引用而非撞号（`混元/…第十八轮.md:3`）。
  2. **引擎 hash 链实测**：9d8b3b0d→02931add→5f8199aa→ef2c645a→d5e4fb77；5f8199aa 三副本逐位一致（v3.0目录/库调试v3.2/猴子记忆库推演）。
  3. **VERSION 字符串矛盾登记不裁决**（三解释并陈，见 1-版本谱系.md §一）。
  4. 机制 45 条按 active(28)/refuted(12)/unknown(5) 入账，MECH-41/42/43 标 CONTRADICTION-CANDIDATE（跨宇宙矛盾）。
  5. 总报告版本演化线索：14轮后（codebuddy 依据）→17轮后→26轮（两轴模型口径）。
- 边界情况及处理：
  - 豆包 agora/memevo zip 未解包（【待确认】解包落 workspace-audit/data/ 是否合规；倾向合规因不动原件）。
  - qwen 工单文件名 v3.8 vs 内容 v3.9-1 版本错位——登记不裁决。
  - Windows 10（衔尾蛇口径）vs Windows 11（VERIF 口径）环境描述并陈【待确认】。
- 未解决问题：
  - SIM 第十八~二十八轮 E 编号全景（E81–E125?）待阶段2 逐轮读取。
  - 引用论文总表 原版 vs 修订版 diff 待考。
  - 提示词阶段7 的 E28"对未收敛物强行固化"名实差异仍未定位（SIM-E28=层次化归并）。
- 锚点抽检：109/109 全命中（尾数7 仅 7 条→全抽；机械校验+语义核对双过，audit-log phase=1）。
- 自检三问：alias/participants/mechanism 每条带锚点；三处矛盾并陈未裁决；推定均标【待确认】。

## 任务交接与插入指令登记（2026-09-09 晚）

- **用户裁决**：本考古任务「不需要再推进下去，另有新的对话接替」；插入指令「把衔尾蛇副本并入衔尾蛇文件夹内，并留下说明」。阶段2 进行至七条宇宙线入账后中止（claim_ledger 现行 **1,620 条**，100% 逐字验证；SIM/REAL/DS/DB-CB/VERIF/PART2/GLM-WEB-QWEN-复审-统合 已入账；knowledge 主库线未提取）。接替会话从阶段2 剩余线 + 阶段3 起继续。
  - 【数字更正 2026-09-09】本节初稿误写"1,364 现行"（漏计 real 批次 256 条），实为 1,620 现行，以 `ledger_tool.txt count` 实时输出为准。
- **衔尾蛇副本并入执行**（用户指令，考古 R1 因任务交接由本指令豁免）：
  - `衔尾蛇副本/`（40,800 文件 / 35.46MB）→ `大审查/衔尾蛇/attic/衔尾蛇副本-冻结快照-20260909/`，robocopy /MOVE，0 失败。
  - 验证：目的地计数 40,800 一致；随机 8 文件 sha256 对照本账本 files.jsonl 基线 8/8 一致（`tools/verify_move.txt`）。
  - 说明落盘：`大审查/衔尾蛇/attic/并入说明-2026-09-09.md`。
  - 【追加二 2026-09-09】用户指令"把大审查目录做成临时工作包，放到主工作区外"：已复制为 `D:\临时工作区\大审查-工作包-20260909\`（robocopy /E，82,878 文件/124.42MB/0 失败；全量对账源vs包逐一 sha256 **82,878/82,878 一致**，`tools/verify_workpkg.txt`）；包内含嵌套 git（大审查 c31ad39、zcode e91bdef）与 attic 快照；包说明见包根 `工作包说明.md`。主区原地不动（冻结），包为可写工作副本。
  - 【追加 2026-09-09】用户指令"确保完全并入后删掉衔尾蛇副本"：源目录实际已随 robocopy /MOVE 删除（根级复核无残留）；全量对账（`tools/verify_move_full.txt`，40,800 条逐一 sha256）一致 40,800 / 缺失 0 / 不符 0 / 反向多出 0——并入完备性为穷尽验证。
  - 注意：首次 MSYS `mv` 因 Permission denied 被拒（无副作用，数据无损），改 robocopy 成功；attic 目录位于 大审查 嵌套仓库工作树内，untracked。
  - 边界情况：目的地处 MSYS `mv` 报错后一次误读（"已不在根级"），复查确认源在、git 零 diff，无数据损失——如实登记。
- **对账提示**：本次移动后，files.jsonl 基线中 `衔尾蛇副本/` 前缀的 40,800 条记录对应路径已变更（新前缀 `大审查/衔尾蛇/attic/衔尾蛇副本-冻结快照-20260909/`）。基线文件本身不改（R7）；接替会话做全树重扫时按新路径对账。

## 阶段2 断言账本（全量）——进行中，接替点

- 进入时间：2026-09-09 ~21:00；状态：**七线已入账，knowledge 线待接替**
- 账本现状（`py -X utf8 workspace-audit/tools/ledger_tool.txt count`，2026-09-09 23:30 实测）：
  - 总行数 1,622（含试金石期 2 条 superseded），现行 **1,620**
  - 按类型：hypothesis 151 / method 242 / parameter 110 / result 591 / verdict 526
  - 按状态：verified 969 / open 565 / refuted 42 / superseded 36 / contradicted 8
- 已完成入账的提取批次：`ds.jsonl`（264+1手工）、`sim2.jsonl`（516）、`arch.jsonl`（147+53修复）、`dbcb.jsonl`（149）、`verif.jsonl`（179+1手工）、`real.jsonl`（256）、副本说明快照元数据（3）
- 中间清单存档：`data/extract/*.jsonl`（子代理产出，均经程序化锚点复核后入账）
- 质量门记录：`ledger_verify.txt` 全程 100% 逐字命中（现行口径；已内置 衔尾蛇副本 路径迁移映射）；ingest 失败累计 55 条，53 条重定位修复、2 条手工修正，未解决残留 0
- 接替会话注意：①knowledge 主库线（pitfalls/patterns/decisions/reflections/两轴模型等）未提取，提取提示词模板见本 progress 历史（子代理模式：只产 data/extract/*.jsonl，主会话 ingest 验证）；②arch.jsonl 提取员的 qwen 行号漂移教训——.extract.txt 文件有 `\r\r\n` 行尾，Read 行号与 Python readlines 行号不一致，ingest 失败时跑 `tools/repair_relocate.txt`；③阶段4 独立校验质量门未做，阶段3 分支树未开始。

## 阶段2 断言账本（全量）——已完成（2026-09-10 接替会话收尾）

- 接替会话进入时间：2026-09-10；完成时间：2026-09-10
- 续跑核对：阶段0/0.5/1 全部哈希逐位一致；claim_ledger 1,622 行与交接记录吻合（无篡改）。
- 收尾范围圈定（`tools/gap_scan.txt` + `tools/gap_dedup.txt`）：全树叙事文件 − 已入账 − 43 个哈希级副本 − 边界剔除 = **终选 178 文件**（去重口径：同 sha256 且任一副本已入账 → COPY-SKIP；未入账同哈希对取一份、另一份登记跳过）。
- 六批次提取（子代理，均先读 `tools/extractor-guide.md`——**提取模板已持久化固化**，修复交接期模板仅存会话历史的问题；自检 `tools/extract_check.txt` 全 PASS 后入账）：

| 批次 | 文件数 | 断言数 | sha256[:16] |
|---|---|---|---|
| know.jsonl（knowledge 主库+trajectories 29） | 35 | 266 | f0b423a95d0cab37 |
| sim3.jsonl（混元 R3–R17+总报告版本链+方法论+工单） | 29 | 578 | 4f1ca103cfa765f9 |
| part2.jsonl（PART2 十二轮预注册/报告+根级账本） | 41 | 402 | f6fa7a3eb91f3c23 |
| oreal.jsonl（大审查残留+衔尾蛇快照版本对） | 16 | 204 | 5cbe54ec05dd3489 |
| deploy.jsonl（库调试两实例+_l8_lab+根meta+两轴模型） | 26 | 399 | b62dc8cf241d282e |
| ds2.jsonl（DS 交接包独有：批次R2-R5+探针4-6+v3.1.0） | 30 | 455 | 0a96a5fb17fa6310 |

- **账本终态**（`ledger_tool.txt count`）：总行数 **3,926**（现行 **3,924**）；类型 hypothesis 233 / method 657 / parameter 474 / result 1,512 / verdict 1,048；状态 verified 3,079 / open 702 / superseded 67 / refuted 52 / contradicted 24。claim_ledger.csv 3,927 行（含表头）sha256[:16] `faf6f5f8885340df`；audit-log.csv 293 行 `8a8da3274ed4d33a`；supersede_log.csv 不变（3 行）。
- 质量门：`ledger_verify.txt` 全账本 **100% 逐字命中**（3,924/3,924 现行口径）；抽检 `spotcheck_p2b.txt` 尾数逢7 共 129 条 **129/129 命中**（audit-log phase=2b）；ingest 六批 2,304 条 **零失败**。
- 关键分类决策（≤5）：
  1. **宇宙前缀扩容**：新增 KB-（knowledge 主库）、PART1-（四轮审查链）、L8LAB-、DEPLOY-（库调试部署）、META-（根级元文档）五前缀，连同旧 12 宇宙入 `extractor-guide.md` 前缀表。
  2. **版本对并陈不裁决**：v3.9 工单三版本（现行<zcode<快照）、总树两版、豆包总报告两版（副本=六轮33实验→9.9日版=七轮45实验）、DS v3.0.0/v3.1.0（主文逐字节一致仅尾加3行，未改判）——各版入账，差异处重点锚定，可定序标 superseded、不可定序标 contradicted。
  3. **交接验收类文书**（混元交接验收/DeepSeek交接验收）按"跨宇宙对账核心证据"高密度提取，note 标 REAL验收SIM 等。
  4. trajectories 撞号如实保留（task-018/020/024 跨日期重名）——源库 W-5 真实缺陷的证据，不代为修复。
  5. sim3 发现：HANDOVER-ZCode线 顶部"28 轮后阴性结论全部不可直接引用"为波及面最大的 superseded 声明（11 条版本链改判入账）。
- 边界情况及处理（边界清单存 `data/gap-final-list.txt` 尾行统计）：
  - 代码/脚本不入账：zcode/sandbox_r2/*.txt（21个Python实验脚本）、衔尾蛇/proto/*、_l8_lab/tools/*、混元 *.py（其断言由对应叙事报告覆盖）。
  - 引擎样板不入账：两部署实例 SKILL.md、citations.md（属 676 副本家族）；库调试两实例 references/ 四件同哈希取工作区版。
  - 文献线延迟：引用论文总表.md（根）+ 豆包/引用论文总表_修订版.md → 阶段6 lit-ledger 处理。
  - 非实验项目区不入账：语料分析/迷深清洗工作/mepub/ComfyUI/comfyui-docx-scratch/soul/archive/attic/workspace/.zcode；实验性双库工作区 按 AGENTS.md D-002 为冻结参照档案跳过（【待确认】若用户要求并入需补提）。
  - qwen .extract.txt 的 `\r\r\n` 行尾漂移在自检脚本复现（arch.jsonl 53 条历史 FAIL 属已知已修复项，账本侧 100%）——子代理改用 Python readlines 实测行号后零漂移。
- 未解决问题：
  - 豆包 agora/memevo 两沙盒 zip 仍未解包（【待确认】延续）；沙盒总报告（agora 34 条/记忆库 mem-evo 35+5 条）已入账提供线级覆盖。
  - SIM 第一/第二轮文件名未见于 混元/ 目录（R01/R02 断言仅存于总报告转述）——若在自演化离线实验/ 数据目录内有早期轮次，属数据目录边界未提取。
- 自检三问：本阶段新断言全部带锚点（程序化截取+双重校验）；版本冲突全部并陈（superseded/contradicted 标注，未裁决）；推定（跨宇宙对账语义、版本定序）均落在 note/状态标注且有文内依据。

## 阶段3 分支树构建——已完成（2026-09-10）

- 进入/完成：2026-09-10。产出登记：

| 文件 | 行数 | sha256[:16] |
|---|---|---|
| tree_edges.csv | 174 | e765c0b8db0e6bf7 |
| 20-分支树.mmd | 391 | 01ecd2001a44ccca |
| ghost_list.csv | 4 | ddef5dfd3a80e500 |
| 3-分支树.md | 59 | 91ead5afc077d196 |
| data/tree-nodes.csv | 644 | b1fa3dcf9cf887be |
| data/tree-candidates.csv | 656 | 7444973e1ba6db1f |

- 关键数字（`tools/tree_scan.txt` + `tools/tree_validate.txt`）：643 节点/20 宇宙；173 边（replicates 65/refutes 39/motivated_by 35/supersedes 22/contradicts 10/extends 2）；INFERRED 55（31.8%）；触点 183、孤立 460、25 簇、最大簇 116、最深链 13（PART2 轮次链）。
- 关键分类决策（≤5）：①"未复现"=refutes（E80 八驳边）；②E57 双裁决并陈（REAL驳/DS剂量化复现）；③修正编号≠实验号（修正57≠E57）；④版本链只连相邻；⑤混元/任务报告.md 与 codebuddy 同源存疑 → SIM-TASK 线弃边留人工。
- 边界情况：E0/E4 命名空间冲突（两轴模型信任轴 vs SIM 实验号）、E132 假阳性（SIM-WEB- 前缀漏配）——3 候选全消解，0 真幽灵；460 孤立节点半数为 KB 记账条目（常态，见 3-分支树.md §五）。
- 质量门：173/173 边 anchor 机械校验在账本（validate 脚本）；TIME-ANOMALY 0；抽检 24 条（每7取1）入 audit-log phase=3。
- 自检三问：无边无锚（INFERRED 均带推断链）；E57/同文件矛盾并陈未裁决；§五孤立节点解读显式标【研判推断】。

## 阶段4 独立校验——已完成·判决 HALT（2026-09-10）

- 进入/完成：2026-09-10。**判决：对账不一致率 57.3%~58.9%，超 >25% 阈值 → 按 R9 中止，细节见 HALT.md 与 04-diff.md。**
- 产出登记：

| 文件 | 行数 | sha256[:16] |
|---|---|---|
| 04-diff.md | 54 | 192fbdc57b13702d |（原登记 63 为录误：git 首提交 92701b5 起即 54 行从未变动；2026-09-10 续跑会话实测修正）|
| HALT.md | 68 | commit 后见 git |
| data/extract/blind-sim{a,b,c}.jsonl | 302+281+504 | 盲建中间产物（自检 1,087/1,087 PASS） |
| data/phase4-diff-detail.csv | 1582 | diff 全量明细 |
| data/phase4-content-uncovered.csv | 226 | 内容未覆盖清单 |

- 协议：最大体量主题簇=SIM 宇宙（48 叙事文件，账本现行 1,111 条）；3 个盲代理只给 00-PROMPT.md 原始操作定义+文件清单+机械自检脚本（禁读一切中间产物）；预登记匹配口径先于运行固定。
- 关键数字：v1 同行重叠 57.7%（首跑 58.9%，修正孪生映射后复算）/ v2 同行包含 57.9% / v3 ±3行邻域 57.3% / 内容级折算覆盖 79.5%；Jaccard 选择分歧 53.9%；匹配对内 type/status 分歧 31.9%；A 未匹配 409=粒度分歧 187+真覆盖分歧 222。
- 关键分类决策（≤5）：①质量门按预登记口径执行不事后放宽（四透镜全报）；②孪生映射 bug 当场发现当场修（混元/实验设计.md=codebuddy docs 副本≠deepseek 版，04-diff §四.4）；③内容级透镜作为诊断补充不改判决；④HALT 而非回炉——回炉分支仅授权 10-25% 区间；⑤出路 A/B/C 只列不裁（R3）。
- 边界情况：盲建代理复现 Read 行号漂移（22-62 条/代理，机械校正）；盲建 CONTRADICTION-CANDIDATE 与账本同位（矛盾登记可复现）。
- 未解决问题：阶段5-11 全部未启动，等用户对 HALT.md §四 出路的裁决。
- 自检三问：diff 全部数字脚本产生（命令入档）；两边并陈未裁决；HALT 原因与证据链完整落盘。

## 阶段4 裁决登记（2026-09-10 用户裁决，HALT 解除）

- **裁决要点**（六条，全文见 `gate-revision.md`）：
  1. 定性修正：本次 diff = **可复现性方差**（非真实性污染，毒为零）；原单阈值质量门标 **superseded**，改为**两级门**：真实性门（抽检<80%→HALT，不变）/ 可复现性门（不触发 HALT，触发**方差标注义务**）。
  2. 方法论发现入账：experiment_id=**方法论-01**"无死规则下 LLM 提取判断方差"——claim_ledger **+14 条**（现行 **3,938**，100% 逐字）；**incident-log.csv 首次建立**（阶段2 遗留缺口）并记入；alias_map 追加 `方法论-01` 命名空间行；死因分类=门设计缺陷（单阈值混两失败模式）。
  3. 采纳 **A 定位**：账本定稿为"逐字锚定断言样本"；阶段5-11 照跑。硬规则：全部统计**区间输出不给点估计**；引用处**区间与点值同现**；违者红队按**"伤"级**计。
  4. 终报增节《选择方差与两级质量门》；**B 计划预注册**（第二圈升格操作定义重提同批文件，round2-vs-round1 diff = 方差实测 = delta 曲线误差棒）；须写明 B 通过仅证"规则可机械导出"，不证"读者自然一致"。
  5. **回炉上限两轮**，之后固化为"已知方差"入终报，禁止无限回炉。
  6. **交集核本轮不执行**；机制清单/LM 矩阵行用**全集（宁多勿漏）**；对外定量结论留待 B 后的交集核托举。
- 产出登记（本次裁决执行）：

| 文件 | 行数（wc -l 实测） | 备注 |
|---|---|---|
| gate-revision.md | 71 | 修订记录本体（原定义 superseded 的声明处） |
| incident-log.csv | 3 | **首次建立**（表头+方法论-01 行） |
| alias_map.csv | 53 | 追加 方法论-01 行（只增不改） |
| HALT.md | 80 | 追加 §六 裁决解除（§一~§五 原地保留） |
| claim_ledger.csv | 3,941 | +14 条 方法论-01（现行 3,938，100% 逐字） |
- **任务状态**：阶段5-11 **未启动**；按用户指示**新会话以闲时任务接续**（本会话执行完裁决修订即停，不再推进主任务）。
- 接续会话入口：先读 `progress.md`（本块）→ `gate-revision.md`（两级门/硬规则/B 计划）→ 从**阶段5 景观五区**起。

## 续跑会话开工登记（2026-09-10 · v2 规格 · 阶段5 起接续）

- 收到 PROMPT-SPEC-v2；规格 v2 全文已存档为本目录 `PROMPT-SPEC-v2.md`（此前盘上只有 v1=00-PROMPT.md，后续会话需要 v2 文字），此后只追加不修改。
- **续跑核对**（`py -X utf8 workspace-audit/tools/progress_hash.txt` + 逐文件 `wc -l`/`sha256sum`，2026-09-10 实测）：
  - 00-PROMPT/00-盘点/00-文献清单/00-重复表/data.files.jsonl 等=阶段0 登记**逐位一致**；claim_ledger **3,941 行**、alias_map 53、tree_edges 174（`e765c0b8db0e6bf7` ✓）、incident-log 3、ghost_list 4（✓）、mechanism-registry 46（✓）、participants 15（✓）、supersede_log 3（✓）、audit-log **317**（=阶段2 的 293+阶段3 抽检 24，吻合）、HALT 80、gate-revision 71——与阶段1-4+裁决登记一致。
  - `ledger_tool.txt count`：现行 **3,938**（verified 3,093 / open 702 / refuted 52 / contradicted 24 / superseded 67；hypothesis 233 / method 662 / parameter 476 / result 1,515 / verdict 1,052）——与裁决登记一致。
  - **一处录误就地修正**：阶段4 块 04-diff.md 登记"63 行"，实测 **54 行**；git 三提交（92701b5/22f1d14/d90e3f6）均 54 行、sha16 `192fbdc57b13702d` 从未变动——判为登记录误非篡改（先例：d90e3f6 同类修正）。
  - `git status workspace-audit/` 干净（HEAD=d90e3f6）。
- **v2 规格文字 vs 盘上裁决出入登记**（按规格"已发生的事实优先于规格文本"逐条裁定）：
  1. v2 云"若 workspace-audit/ 已存在改用 workspace-audit-v2/"：本目录即本任务首轮（阶段0-4）产物，且人工裁决（gate-revision.md）明示"阶段5-11 照跑、从阶段5 起"——**裁定续用 workspace-audit/，不另建 v2 目录**（建新目录=强制重做已完成阶段，违反规格自身续跑条款）。
  2. v2 以"HALT-RESOLVED.md"为恢复凭证名：盘上实际凭证=`gate-revision.md`（用户裁决）+HALT.md §六（裁决解除节）——实质一致（人工裁决解除 HALT），文件名不同，如实登记不改动。
  3. v2 阶段4 两级门文字与 gate-revision.md §三-§七 一致，无实质出入；方差纪律 V1-V4 与裁决 §五-§七 一致。
- 边界情况：incident-log.csv 第 2/3 行为**逐字节重复行**（裁决执行时双写；R7 不删行保留原样；后续一切 incident 计数按唯一行计——已预注册入 tools/phase5-guide.md）。
- 本会话任务：阶段5 → 11.5 依序推进（方差纪律 V1-V4 全程生效）。

## 阶段5 景观五区划分——已完成（2026-09-10，v2 规格）

- prompt_version：PROMPT-SPEC-v2.md（本日存档）；规则预注册 `tools/phase5-guide.md`（v1+§九v2 修订块）。
- 产出登记（wc -l + sha256[:16]）：

| 文件 | 行数 | sha256[:16] |
|---|---|---|
| 30-景观五区.md | 254 | f3f608c9904f59ff |
| tools/phase5-guide.md | 93 | 08b288455e6b47a7 |
| tools/phase5_zones.txt | 179 | 2494115fab92ec30 |
| tools/phase5_fragments.txt | 49 | 783de62c9325997d |
| data/phase5-zone-assignments.csv | 3,872 | bbfb0125736c6ce1 |
| data/phase5-death-causes.csv | 53 | 862e63d545f30c30 |
| data/phase5-frontier-ranked.csv | 161 | 6b92bc6203247b1a |
| data/phase5-summary.txt | 105 | 66c7cf1f1b9d4d81 |

- 关键数字（全部点值+区间同现，因子 0.795/1.358）：收敛区 3,093 [2,458,4,201]（tier-1 跨宇宙确认仅 164 [130,223]）/ 开放前线 702 [558,954]（hypothesis 160，**97 条 IV=0 孤立**）/ 坟场 52 [41,71]（死因 DC-1 未复现 16 居首）/ 矛盾区 24 [19,33]（E14 簇最大）/ 幽灵区 3 候选 0 真幽灵；四区和=3,871=人口 PASS。
- 关键分类决策（≤5）：
  1. 统计总体 P=3,871（status≠superseded ∧ ∉supersede_log）——与 ledger_tool"现行"口径差异 67 行（superseded-status 仍计入 tool 现行但按有效版本规则不入分区），预注册于 guide §一。
  2. tier 确认边取 replicates|extends 入边、跨宇宙（tree-nodes universe 列）判 tier-1；宇宙级端点边（REAL→SIM 等 5 条）不计入实验 tier，单独并陈。
  3. IV=实验关联边数（含全部 relation），排序 IV→实验 open 假设数→claim_id。
  4. 死因关键词表 v1 覆盖率 50% → 按 R10 追加 v2 块（DC-7 新类+3 类扩词）→ 86.5%，DC-0 剩 7 条中 5 条为 hypothesis 行结构性局限（引文=假设原文），如实呈现不再迭代。
  5. 机制矛盾候选双口径：字面 CONTRADICTION-CANDIDATE=1（MECH-41）vs 阶段1 登记语义三件套 3——并陈不裁决。
- 边界情况及处理：①mechanism-registry 字面/语义标记差 2 条（见决策5）；②坟场 DC-0×claim_type 交叉表呈现结构性局限；③incident 计数唯一行规则（重复行事件不双计）已入 guide §七；④阶段5 无新入账断言，锚点抽检不适用，替代质量门=基数硬校验（脚本 exit 码）+全表脚本产出零手抄。
- 未解决问题：开放前线 97 条 IV=0 假设的"孤立性"是提取密度方差还是真实无连线——留阶段9/10 用（B 计划后可复核）。
- 自检三问：见 30-景观五区.md §七（三段研判推断显式隔离；矛盾三口径并陈；区间因子外推假设页首声明）。

## 阶段6 文献全摄入 LIT-ABSORB——已完成（2026-09-10，v2 规格）

- 规则预注册：`tools/phase6-guide.md`（v1+§十 v2 块：S4 自注计数 8→10 修正）。R5 全程：lit 摘录 100% 程序化逐字（构建脚本 assert 全过才落盘）。
- 产出登记（wc -l + sha256[:16]）：

| 文件 | 行数 | sha256[:16] |
|---|---|---|
| lit-ledger.csv | 117（116 行+表头） | c93f1186f7902f3b |
| ordering-claims.csv | 9（8+表头） | ca9e821f574bea87 |
| ghost-papers.csv | 35（34+表头） | 410b41b52d301d6c |
| 06-新旧文献交叉.md | 68 | 61609fdaeaef1bb2 |
| tools/phase6_build.txt | 252 | fdbff9944d4462b0 |
| data/phase6-build-log.txt | 10 | 5072994ddedf7a43 |

- 关键数字【全量枚举，不乘方差因子（phase5-guide §六先例）】：lit-ledger 116 行（旧33×95/雷达综述×21/新批次×0；row_type：简介33/落地33/雷达判定21/题录自注10/核对结论5/核对问题7/原版用途7）；EXTERNAL-CLAIM 6 行（其中 S5:22 的 27% 系正则误捕的内部统计，如实登记）；叙事丢弃 399 行（机械口径）；ghost-papers 34（N=33+A24 提取本 Y）；ordering-claims 8（E链前提4/L↔E映射1/跨轴禁则2/能力阶梯1）。
- 关键分类决策（≤5）：
  1. **"新批次"终局**：无实体；阶段1 遗留"原版vs修订版差异"了结=同体系版本链（S1→S5→v3.8.2 补丁→S2），非两批次；S5:87 T4 计数行标 superseded-by-patch。
  2. lit-ledger 用超集 schema（spec 字段全含+anchor/row_type/status 列）；摘录=行前 200 字符硬切（≤200 铁律），lit_id=sha256(paper_id+anchor+quote[:80]) 幂等。
  3. 可测性映射机械化：S2 落地层级 T1*/T2*→Y、T3→N、例外 A17/A19→需权重访问（RL 核心）；雷达行 ✅→Y/⏸→N。
  4. batch 值扩展 {旧33, 雷达综述, 新批次}（雷达系自产综述，非 33 体系；对 spec 二分假设的偏差已在 guide §二登记）。
  5. EXTERNAL-CLAIM 正则捕获两个边角如实登记：S5:22 内部统计误捕、"10-12x"仅逐字捕"12x"。
- 边界情况及处理：①guide §二预告的"A24/A29/A32/A33 四纸行标 superseded-by-patch"在提取区细化后落于 S5:87 计数行（四纸 T4 判定行不在冻结提取区，其改判由 S2 落地行承载）——偏差登记于本块；②A24 ghost 标 Y(提取本)（attic/_bca_extract.txt 在位，原始 doc 形态未考）；③尾数逢7 仅 5 条→全抽 5/5 命中（audit-log phase=6 追加 5 行）。
- 未解决问题：E1/E2/E4 前提与实验数据的一致性=未测（非确认）——留阶段10 LIT-gap 争议清单。
- 自检三问：文献断言全部带锚点（程序化 assert）；S1/S2/S5 三版本主张并陈未裁决（superseded-by-patch 标注依据=S2:11 逐字，非考古员裁决）；06 文档【机械事实】/【提取事实】/【研判推断】三层显式标注。

## 阶段7 L 轴重设计——已完成（2026-09-10，v2 规格）

- 规则预注册：`tools/phase7-guide.md`（v1+§八 v2 关键词补丁）；定级脚本 `tools/phase7_grade.txt`（ALL ASSERTS PASS）。
- 产出登记（wc -l + sha256[:16]）：

| 文件 | 行数 | sha256[:16] |
|---|---|---|
| 07-L轴.md | 108 | 61ac54c40831d40b |
| data/phase7-grades.csv | 70（45机制+24事故+表头） | cf32dde84b70f2c4 |
| data/phase7-summary.txt | 60 | d779c74707fbb772 |
| incident-log.csv | 26（表头+25 行=追加 INC-02..24 共 23 行，幂等） | 331e6a1a07dc1421 |

- 关键数字【全量枚举】：机制 L 分布 L5:3/L4:6/**L3:23**/L2:3/L1:9/L0:1；事故 24 条（层级冻结判定+severity/blindness 关键词度量）；**单调性双双重构**：盲度中位数序列 [0,1.5,1.5,0,0,0]（反例对 L2→L3）、破坏度非单调（L1=[4,4]）。
- 关键分类决策（≤5）：
  1. **轴修订 v1.1**：保留触及深度定级语义；撤销"层级→危险度"单调含义（实测不成立）；危险评估改（层级×盲度）二维；P1 弱化为机制存在性命题（五锚点）、P2（破坏度正交）实证成立。
  2. incident 宇宙从 1 扩到 24（冻结清单 guide §四，摘录=账本既有锚点行复用，R2/R5 自动满足）；incident-log 追加 23 行。
  3. 机制定级全机械（关键词表 UNMATCHED 即退出）；事故层级=冻结人工判定（R10 外化，非脚本复算——与规格三预期是交叉检验非独立复算，如实声明）。
  4. 规格三预期在对应物上 3/3 一致（INC-02→L4/INC-10→L2/INC-08→L4）；两处名实差异并陈（SIM-E28 本体 MECH-30=L1、SIM-E11 本体 MECH-02=L1，独立定级不受预期影响）。
  5. 两个度量噪声案例如实登记不改数（INC-02 摘要行无盲度语汇、INC-21 claim_id 最小规则取到纯数字行）——度量=quote 文本函数是已知局限。
- 边界情况及处理：①guide 首跑 UNMATCHED（MECH-08）→ §八 v2 块补三关键词（判别/w_age/步长）后通过；②L3 机制占 51% 与 L2 事故>机制（6>3）的"制度化欠账"对照为【研判推断】。
- 未解决问题：severity/blindness 关键词度量的文本依赖（n=24 小样本）——若第二圈 B 计划做事故双度量盲建可给误差棒。
- 自检三问：见 07-L轴.md §八。

## 阶段8 LM 矩阵——已完成（2026-09-10，v2 规格）

- 规则预注册：`tools/phase8-guide.md`；构建 `tools/phase8_matrix.txt`（270 格，own 层分布计数断言全过）。
- 产出登记（wc -l + sha256[:16]）：

| 文件 | 行数 | sha256[:16] |
|---|---|---|
| lm-matrix.csv | 271（270+表头） | e7e113b269669732 |
| 08-LM矩阵.md | 49 | 26462a1f5ea8c516 |
| data/phase8-empty-cells.csv | 121（120+表头） | 975f43ad0df33402 |
| data/phase8-summary.txt | 31 | 63ad6751d4940c47 |

- 关键数字【全量枚举】：270 格=已验 19/存疑 22/证伪 12/计划 1/不可达 96/空白-没人做过 93/被证伪后放弃 27；覆盖率 19/270（7.0%）。
- 关键分类决策（≤5）：
  1. 格子语义冻结：自有层按 registry+M 验证名单；向上默认因果不可达（写路径半序），向下默认空白；例外表 10 格（观测路径向上 6+执法路径向上 2+L1 跨层 3，含重叠编号 8 个唯一格）。
  2. M 验证名单冻结（已验 13/计划 1/存疑 19/证伪 12），依据=registry note 跨宇宙标记。
  3. 关键发现：L2 流程层已验格=0（与阶段7"L2 事故>机制"互证=制度化欠账区）；L0 话语层 32 空白；L5 治理层仅 3 格且 2/3 存疑。
  4. 不可达 96 格标注为写路径半序的结构噪声，不计入机会空间（机会=空白 93+存疑 22+计划 1）。
- 边界情况：例外表内 MECH-14 双格（(L5,MECH-14) 执法向上 + own L5）——执法路径使 L5 机制在 L5 有直接实现记录，语义自洽。
- 未解决问题：L0 空白 32 格中"话语层效应免检"是设计选择还是盲区——留阶段10 c 源评估。
- 自检三问：格子值全部规则生成（脚本断言）；半序 vs 观测/执法路径的张力以例外表显式暴露未合并；【研判推断】三条显式标注。
