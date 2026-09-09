# Task-006 L8 超绝激进档 · 2026-09-04

> 原始轨迹层：只追加，只写不改。平时不加载，仅在复盘时引用。

## 任务
用户问「有没有超绝激进的 L8」，授权 webReader 猛蹬+自主思考，先规划后执行。计划书 workspace/L8超激进档计划书.md，五项待确认按建议执行：全做/遥测收/USER.md 起步/独立分包/开沙盒。

## 调研（webReader 4 发，3 中 1 偏）
- DGM (2505.22954)：变体档案/实证基准/人类监督/垫脚石归档 → L8 三护栏
- Self-Evolving Survey (2507.21046)：What/When/How/Where 分类学 → L8 补「工具与架构」进化列
- Multiagent Debate (2305.14325) → 心智议会
- 2503.01176 打偏（晶圆抛光论文），Gödel Agent 精确出处未验证不硬凑

## L8 设计（theme：自指演化——库演化自己的机器）
七模块：constitution（宪章+l8_guard 卫兵+lifelog_append）/ lifelog（哈希链）/ mutation-engine（MUTATION-SOP：遥测→单候选→基准→台账→人类令牌）/ tournament（usage.log 遥测+季度锦标赛零删除）/ council（四席位两轮+少数派保留）/ twin（TWIN.md 预演，仅咨询不代行）/ worldsim（反事实沙盘，虚拟显式标注）。
稳定性 ☆；独立 add-on 分包（library-bootstrap-l8-addon/，17 文件）；逃生舱=删两目录。

## 测试（T8-T12 扩展）
首跑 19/21：T10 断言关键词与模板措辞不一致（「30 天豁免」vs「30 天内豁免」）→ 统一措辞；T12 卫兵只对账 skill 前缀路径 → 改为对账 manifest 全部文件。终跑 **21/21 全过**（原 13 + 新 8）。

## 沙盒
_l8_lab/ 试装完成：宪章+卫兵+写入器就位，LEDGER 空台账建好，创世块 d59ce42e 入链，guard 0 问题。下月 1 号体检时跑变异引擎第一轮（依 usage 遥测，本沙盒暂无 usage.log，预计首轮提案=给 run_tests 补 L8 沙盒集成断言）。

## 本任务验证的模式
- PT-004 +1（第 5 次：增量档位扩展是建库路径的再验证）
- P-004 教训被遵守：全部模板用 Write 逐个写，零 sed 翻车
- 反思计数 3→4（下次 wrap-up 满 5，触发首次 reflect）

## 追加 · wrap-up 记录（2026-09-04，第 5 次 wrap-up 触发首次 reflect）
- 清场：workspace/_methodology_extract.txt → attic/（v3 临时残留）；四份计划书保留（归档 README 引用中）。
- TWIN 首次预演验证：计划书预演①「要更狠」→ 用户追问过更激进并在 L8 批准全六模块+worldsim，命中；预演②「担心发布包安全」→ 用户未置评，采纳建议方案视为默认命中；预演③「额度管够」→ 命中。TWIN 判定：3/3 命中（宽松口径）。
- reflect 首跑：R-001/002/003 入库，R-003 升格 PT-005；反思计数清零。
- 过程事故：演化回扫时 Edit 误击 P-001 关联行（内容错配），当场发现当场修复——工具纪律第 4 次实锤（改完必自查）。
