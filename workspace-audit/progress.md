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

## 阶段2 断言账本（全量）

（待进行）
