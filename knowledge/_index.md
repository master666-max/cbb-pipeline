# 知识库索引（2026-09-04 · v4 更新）

> ✅ **解冻公告（2026-09-09 深夜）**：主工作区冻结已由用户解除，恢复正常工作。
> 冻结期：2026-09-09（交接文件：根 `HANDOVER.md` 总册 + `大审查/混元/HANDOVER-ZCode线-20260909.md` 混元线分册，保留作史）。
> 解冻后第一动作：知识库 lint 体检（已完成，见 trajectory task-025）。

> **每次任务开始必读本文件。** 常驻 AI 上下文，保持 200 行内。
> 加载顺序：`soul/SOUL.md` → `soul/USER.md` → 本文件。
> 维护规则：每次 wrap-up 的第 5 步同步更新；按验证次数/触发频率排序；断链当场修复（或跑 `py -X utf8 tools/lint_knowledge_base.txt`）。

## 反思计数
- 自最后反思以来 wrap-up 次数：0（2026-09-15 reflect R-021+R-022 后清零；前轮 5 次=①F3 task-045 ②F2 task-046 ③阶段一验收 task-047 ④工单固化 task-048 ⑤本体构筑执行 task-049）
- 最后反思：2026-09-15（R-021 无人值守可靠性来自协议三件套：判据前置+留痕强制+出口门条件化 / R-022 分析-构筑合规流水：详报唯一转述层+按设计重写+合规声明随交付落盘）

## 高频 Pitfalls（按触发次数排序）
- [P-017 幂等系统断言断状态不断过程；append-only 旁车日志追加前先查终态](pitfalls.md#p-017) — 2 次触发（P1-M1 集成冒烟双证据 + task-049 本体版：同目录双跑抓 store 两真幂等缺陷→v2 增补「单测全绿≠集成幂等，三断言=摘要全等+文件集不变+库字节不变」）
- [P-016 importlib 动态加载含 @dataclass 模块：先注册 sys.modules 再 exec_module](pitfalls.md#p-016) — 1 次触发（内核验收工具链通用化三脚本同崩）
- [P-014 接手外来实验线先查并行产出；下发文书断言对账线内最新在案记录](pitfalls.md#p-014) — **3 次触发**（第二十八轮 2a 更正事故；豆包线原作者端侧分支；F1 下发单「两振」口径滞后于 R2 线三振在案事实，v3）
- [P-015 消融「边际≈0」≠「护栏无用」，先构造它所防范的危险](pitfalls.md#p-015) — 1 次触发（codebuddy §7.6 + 混元 E41 双线独立发现）
- [P-001 Windows 脚本执行：用 py 启动器，.py 被拦就写 .txt](pitfalls.md#p-001) — 多次触发（EPUB/PDF 提取、docx 后处理、验收均命中）
- [P-002 EPUB 解包文件名 cp437 乱码须修复](pitfalls.md#p-002) — 1 次触发
- [P-003 清洗误报三陷阱：正文词/破折号字形/半角方括号](pitfalls.md#p-003) — 1 次触发
- [P-004 含特殊字符/格式文本的生成与编辑别走 shell（sed/bash 双引号 -c 都是坑）：一律 Write/Edit](pitfalls.md#p-004) — 已验证 3 次（模板生成翻车 + 反引号吃记录两起）
- [P-005 分发包模板中性化 + install.md 引用完整性](pitfalls.md#p-005) — 1 次触发（独立工作区实装抓出，T18-T21 锁定）
- [P-006 核验报告附证据快照 + 同构案件判例回收对齐](pitfalls.md#p-006) — 1 次触发（P3-10 双标事故，v2.1.2 转单）
- [P-007 沙盒度量缓存须随库写递增 rev（pre≡post 假象）](pitfalls.md#p-007) — 1 次触发（自演化沙盒 X2d）
- [P-008 Electron 桌面应用秒崩：残缺记录+下载器国内网络未处理异常](pitfalls.md#p-008) — 1 次触发（ComfyUI Desktop 修复，含隔离对照法）
- [P-009 MSYS 工具链路径须 /c/ 原生格式 + subprocess errors=replace](pitfalls.md#p-009) — 1 次触发（GPG 签名验证三态对照实测）
- [P-011 预注册手算答案 12% 错误率，自测门全拦](pitfalls.md#p-011) — **2 次触发**（大审查自演化循环 5 处手算错；P-B3 回测 NA 计数 3→4 错又被拦，v2）
- [P-012 登记层自错：hash 手抄/heredoc 断链/自填反转](pitfalls.md#p-012) — 1 次触发（registry 与 meta 双轨对照实证）
- [P-010 长会话运营三事故：相对路径三路不同源 + 管道截断留存 + 异常归因先想别人](pitfalls.md#p-010) — 1 次触发（v3.9 应用轮路径事故+误判他方，含绝对路径取证法）
- [PT-010 Electron 应用「转储解剖→隔离对照→缓存投喂→记录手术」排障流水线](patterns.md#pt-010) — 已验证 1 次 · 适用：桌面应用点了没反应/秒崩
- [PT-007 文档缺陷与实现状态分开判 + 题录改动对账先行](patterns.md#pt-007) — **已验证 5 次**（P3-10 + X-003 + 内核包 53 断言对账 + DX 假红归因 + F4 冻结接单对账）
- [PT-008 外部 Agent Skills 手动装机路径](patterns.md#pt-008) — 已验证 1 次 · 适用：装第三方技能（clone→安检→cp -n→CLI 依赖随行）
- [PT-009 真引擎沙盒演化实验流水线](patterns.md#pt-009) — 已验证 1 次 · 适用：真实系统外挂自优化机制的可行性验证（等价门→基线→演化→危险矩阵→内核对比）
- [PT-012 预注册研究循环流水线](patterns.md#pt-012) — **已验证 4 次** · 适用：自拟实验→自判分的开放式研究循环（锁定/自测门/双轨/机测反推/OBL 出口；v2 增「前提检查门槛」；v4 增「外来预注册提案本地评估：预承诺规则+敏感性全披露」实证）
- [PT-013 小说角色卡/世界书批量语料校验流水线](patterns.md#pt-013) — 已验证 1 次 · 适用：RP 角色卡+世界书对照原著全量核对（正史分层/别名矩阵/同源传染/断点续传；2026-09-13 补登，条目实建于 2026-09-09）
- [PT-014 跨区责任田接单整合记账流水线](patterns.md#pt-014) — **已验证 4 次** · 适用：跨区下发记账/整合工单（机械对账→处置留痕→映射稿分流→滞后披露（v2：含语义级滞后=叙事层/制图层互矛盾）→活页视图；F1/F3/F4/F2 四族全验证）
- [PT-015 跨账本双侧监控协议](patterns.md#pt-015) — 已验证 1 次 · 适用：多线并行下的系统连续监控（对接三账本/双侧化/标定全档/同数据对照/口径联动；W-4 接口条款兑现产物）
- [PT-011 对抗式验证流水线：基线+沙盒+静态数字核验+每结论一脚本+三态总表](patterns.md#pt-011) — **已验证 5 次** · 适用：核验外来 AI 报告/工单属实性（v5：F2 下发单核证全属实·轻量静态应用）

## 验证过的 Patterns（按验证次数排序）
- [PT-004 双库建库执行路径](patterns.md#pt-004) — **已验证 5 次** · 已 skill 化 → `skills/library-bootstrap/`（v1.1：发布包 + L8 add-on 分包）
- [PT-005 工具交付当场自测](patterns.md#pt-005) — 已验证 4 次 · 适用：任何自产脚本/测试交付前
- [PT-002 docx 生成验收流水线](patterns.md#pt-002) — 已验证 2 次 · 适用：正式 Word 文档 · **已固化 → skills/docx-pipeline/**
- [PT-001 EPUB → AI 知识库清洗流水线](patterns.md#pt-001) — 已验证 1 次 · 适用：汉化小说/多章 HTML → Markdown 库
- [PT-003 语料清洗与统计分析流水线](patterns.md#pt-003) — 已验证 1 次 · 适用：整本小说量化分析

## 可用 Skills
- `task-start` v3.0 — 触发词：新任务、开始、启动（灵魂加载 + 三因子检索）
- `wrap-up` v3.0 — 触发词：wrap-up、任务完成、收尾（六步闭环，含演化回扫）
- `reflect` v1.0 — 触发词：反思；每 5 次 wrap-up 自动提醒
- `docx-pipeline` v1.0 — 触发词：docx、Word 文档、生成文档（带脚本的固化技能）
- `library-bootstrap` v1.2 — 触发词：建库、一键建库、建 L{n} 库、迁移双库（10 预设 L0-L9/10 模块/6 特色包；L8/L9 add-on 分包：根目录 l8-addon + l9-addon）
- `council-reflect` / `worldsim` / `broadcast` v1.0 — L8/L9 实验技能（装对应 add-on 后可用）

## 架构决策（Decisions）
- [D-001](decisions.md) 根工作区归档采用「引用不搬移」manifest 方式
- [D-002](decisions.md) 实验性双库工作区原样保留为体系参照，根双库为唯一活跃体系
- [D-003](decisions.md) 常驻上下文预算制 ≤150 行 + just-in-time 取用（context rot 对策）
- [D-004](decisions.md) 六类记忆映射表（MIRIX 对齐）+ 密钥不入库纪律

## 反思洞察（Reflections，高层规律）
- [R-001 中文文本资产库化主线](reflections.md#r-001) — 六项目一条线，patterns 优先服务主线
- [R-002 激进×稳定双轨制](reflections.md#r-002) — 方案层火力全开，流程层先计划后执行
- [R-003 工具首跑必抓 bug](reflections.md#r-003) — 已升格 PT-005
- [R-004 对抗式外部审查+纪律双向咬合](reflections.md#r-004) — 四轮审查链 60+ 条、属实率 ~90%
- [R-005 凭记忆写事实=第一大错误源，对账先行根治](reflections.md#r-005) — 已升格 PT-007
- [R-006 文书递归边际衰减，收敛判据=工件日志](reflections.md#r-006) — v2.1.4 起停止审工单文本
- [R-010 证据语气三分离：实测/预期/未测](reflections.md#r-010) — 混用即生产假信任；对账手法各配其矛（2026-09-11）
- [R-014 下发文书=外来断言·接单即核证](reflections.md#r-014) — 文书层对事实层系统性滞后；四族接单日独立兑现（F1 振数滞后/F4 spur30 证伪/F2 全属实亦系核证产物）（2026-09-13）
- [R-015 共享账本并发写纪律](reflections.md#r-015) — 先读后写撞车重读合入/append-only 下顺带入库无害化（注记归属）/编号即占位；R-012 的记账层姊妹条（2026-09-13）
- [R-016 宣称层≠实现层](reflections.md#r-016) — 外部技术情报先普查后计价，简历级结论作废于文件级实测（webnovel-writer 53k 行真工程/neuro-book 547k 行疑打包）；R-014 的情报载体层姊妹条（2026-09-14）
- [R-017 专职审核工位三件套](reflections.md#r-017) — 事前基线探针+验收审核单+三态判定；核证从临场发挥升级为工位化检查表（2026-09-14）
- [R-018 自动评测器自己也要先过对账](reflections.md#r-018) — 评分脚本输出是新一层"宣称"：键名归一/类型匹配/金标映射三坑，交付前用已知小样本自测（2026-09-14）
- [R-019 对抗审查防循环污染三件套](reflections.md#r-019) — 挑战仅提案·裁决权在裁决方/贡献项打标签/受影响分数双口径；对抗的价值在强迫显式化不在采信率（2026-09-14）
- [R-021 无人值守可靠性来自协议三件套](reflections.md#r-021) — 判据前置+十轮留痕强制（零发现须列检查证据）+出口门条件化；审核线/构建线权责经 task-047~049 三连跑通验证（2026-09-15）
- [R-022 分析-构筑合规流水](reflections.md#r-022) — 详报=唯一转述层/实现按设计重写零源码/合规声明随 SKILL 落盘；AGPL+GPL 双高危仓零事故，全量分析路线产出质量验证（2026-09-15）

## 前沿雷达（References）
- [sota-memory-radar.md](references/sota-memory-radar.md) — SOTA 记忆架构七派全景：21 条目 + 升级触发器（升级前必查）

## 原始轨迹（Trajectories，平时不加载）
- `trajectories/2026-09-03/task-001-建库.md` — v2 建库过程
- `trajectories/2026-09-03/task-002-v3升级.md` — v3 升级（灵魂层/演化/反思/固化）
- `trajectories/2026-09-04/task-003-v4升级.md` — v4 升级（MemCube 元数据/扩散检索/睡眠整理）
- `trajectories/2026-09-04/task-004-轰击调研.md` — 14 信源 SOTA 调研
- `trajectories/2026-09-04/task-005-library-bootstrap.md` — 通用建库 skill 开发（13/13 测试）
- `trajectories/2026-09-04/task-006-L8超激进档.md` — L8 自指演化层（21/21 测试，DGM 三护栏）
- `trajectories/2026-09-04/task-007-L8L9并入skill.md` — L8/L9 并入建库 skill（30/30 测试）
- `trajectories/2026-09-05/task-008-修正工单评审.md` — v2.0.1 偏差核验 → v2.0.2（T18-T21）
- `trajectories/2026-09-06/task-009-v21统合修订.md` — v2.1 说明书+三包重发布（智谱首轮审查转 Z-001~019）
- `trajectories/2026-09-06/task-010-v212核验与转单.md` — 第二轮审查核验（P3-10 改判/DGM 三件套闭环）→ v2.1.2 工单
- `trajectories/2026-09-06/task-011-v213核验与转单.md` — 第三轮审查核验（六项全属实/现行犯自认）→ v2.1.3 权威工单
- `trajectories/2026-09-06/task-012-v214核验与修订令.md` — 第四轮审查核验（G1~G10 全属实+自我纠错）→ v2.1.4 修订令，文本递归收敛
- `trajectories/2026-09-08/task-018-外部技能装机.md` — 12 个外部 Agent Skills 入 ~/.zcode/skills/ + lark-cli v1.0.94（详见 PT-008）
- `trajectories/2026-09-08/task-020-自演化沙盒.md` — 自演化引擎可行性论证 232 run（H1 24 种子坐实 / E14 复现 / 伪特征免疫否定性，详见 PT-009）
- `trajectories/2026-09-09/task-023-多AI总分析与自演化循环.md` — 大审查四部分任务：PART I 收口 + 12 轮循环 26 假设 + 元观测 + 终报（详见 PT-012/P-011/P-012）
- `trajectories/2026-09-09/task-021-comfyui修复.md` — ComfyUI Desktop 秒崩修复（minidump 解剖/隔离对照/12 路并发绕限速/venv 补造，详见 P-008 + PT-010）
- `trajectories/2026-09-11/task-026-内核交接包本地复跑.md` — 云端工单 WO-20260911-K01 四脚本复跑：T15 翻红证伪「53/0」宣称 + 断言数对账（详见 PT-011 v3 / R-010）
- `trajectories/2026-09-11/task-027-内核修复最终验收.md` — v1.1 修复版最终验收门：修复本体无回归（探针 15/15+DX 10/11），3 FAIL 全归因（审计零差异形态/T5 不显著/DX 假红）（详见 PT-011 v4）
- `trajectories/2026-09-11/task-028-v22关单版终验.md` — v2.2 可证伪重设计终验 + **关单**：T4 分位门校准为配对 t 门（原件未动+修订注释），31/31+DX 11/11 全绿 exit 0 逐字节复现；结单报告在内核修复闭环执行区
- `trajectories/2026-09-11/task-029-豆包线十三轮收口与分支接收.md` — E80-E84 五实验（红线 78-85/F33-36/S25-27）+ 原作者端侧平行分支接收（E61-E70 编号双占用警示）+ WO-AUDIT-豆包审计规划（详见 P-014 v2）
- `trajectories/2026-09-13/task-030-F3接单整合记账.md` — F3 基础设施族接单：四前缀 73 节点对账零差异 + 四要点处置 + alias_map 追加稿分流审计区（详见 PT-014）
- `trajectories/2026-09-13/task-031-F1实验族接手整合记账.md` — F1 实验族接手：R2/R2A 并账视图（R2A=R2 线批次 A 专账）+ E80 第三振终裁权口径冲突（下发单两振 vs R2 线三振已收线）+ alias_map 建议行 + spur30/RADAR 勘误（详见 PT-014 v2 / P-014 v3）
- `trajectories/2026-09-13/task-032-F4档案冻结族冻结登记.md` — F4 工位接单（责任田第三次移交）：九前缀 FROZEN-READONLY 原位保全 + 活引用两条不解引（E57 端点/5f8199aa）+ 三触发器维持 + 轨迹编号三方争用实录，嵌套仓 2bf1b0c（详见 PT-007 v5 / PT-014 v3）
- `trajectories/2026-09-13/task-030-F2验证方法学族接手记账.md` — F2 验证方法学族接单：下发单三要点核证全属实（VERIF 协议升审计线标准件·复用链四环锚定 / PART2 DC-3 恰 13 条=P-B3 直接数据源排 W-6 后 / AUDIT2 54 行在账画像）+ alias_map 追加草案 3 行分流审计区下圈（详见 PT-011 v5 / PT-014 v4；task-030 与 F3 线编号双占用，文件名区分）
- `trajectories/2026-09-13/task-033-CBB现成技能生态侦察.md` — CBB v1.0 组件×现成 Agent Skill 映射：npx skills find ×35 关键词 + clone 15 仓本地核证（头部=webnovel-writer 7.1k 星 SQLite+RAG+伏笔开环 / oh-story 6.8k 星拆文管道 / danghuangshang 五文件档案含伏笔台账+关系网 / story-skills CLI 确定性校验 / evals-skills judge 方法学 / neo4j 官方图谱件）；核心缺口=三态门禁/证据四元组/隔离区/VerdictKB/KBI 无任何现成件（详见 PT-008 clone 路径）
- `trajectories/2026-09-14/task-034-技能源码下载与索引清单.md` — 16 仓 305 技能源码入库（`正典库构建系统/现成技能侦察/`）+ 简历式索引清单（半自动构建器可复现）+ 外来 MVP 路线断言对账（Graphiti 31k★属实需中文自测/Revise.net 证伪→ProseEngine·NovelCrafter 才是 canon 一致性商业品）；许可红旗 GPL/AGPL 双仓在案
- `trajectories/2026-09-14/task-035-路线裁决与P1计划书.md` — 用户裁决「力求绝对干净的正典库」：B 路线（自建 cbb-* 技能族）锁定、方案 A 收窄为两件零悔恨外挂；P1 建设计划书 v1.0（范围冻结自 Part XV + Step 0 Graphiti 中文精度证伪实验 + judge 基线中文适配提议 + 三项待确认）
- `trajectories/2026-09-14/task-036-源码全量分析工作量预设.md` — 16 仓普查实测（8800 文件/8.3 万行 py/70 万行 js）+ 三档深度计价：全量三层 170-200 轮（并行子代理 1-1.5 天）vs 精简一期 Tier A 70-90 轮（半天）；三谜待析（neuro-book 547k 行 js 疑 vendored/jwynia 58k js 用途/claude-book 191 篇 md）
- `trajectories/2026-09-14/task-037-分工裁决与Step0审核单.md` — 用户裁决双会话分工（本对话=审核线/另对话=构建线）；环境探针转用为审核基线 B1-B6（Docker daemon 未运行/无凭据环境变量/LM Studio 三模型在案）+ step0-验收审核单 24 项；反思 R-016/R-017 满计数触发执行
- `trajectories/2026-09-14/task-038-Step0社区实测情报.md` — 判定社区无中文抽取精度定量实测（本地 Step 0 不可免）但可瘦身一半（1 章最小验证先行）；主源查证 graphiti 提示词无原文语言硬指令 + issues 三雷区（max_tokens 硬编码截断/本地客户端不稳定/去重漏别名）；交付 P1执行区/step0-社区实测情报.md
- `trajectories/2026-09-14/task-039-Step0全量判定.md` — **与豆包线 task-039 编号双占用（R-015 再现：并行会话各自取号，文件名区分、编号不搬、此处登记）**。Step 0 正式判定：4金标（三轮自审+对抗5轮255挑战裁决+用户终审）×双模型8份抽取×事实级裁决→**混合分支**（实体 adjusted P 0.79-1.0/方向 0.857-1.0 达标；时间归一化双败→cbb-anchor 自研触发；元文本零抽取双败→R6 规则必配；reference_time 污染/schema 双兼容/重复边三大 Tier 2 教训）；交付 报告-Tier1正式判定.md
- `trajectories/2026-09-14/task-039-豆包线十四轮与DISPATCH-P2执行.md` — E86-E91 跨线对账与防御闭环（锚定剂量对账未决 S28/软保底互证/幻影多点 F40 阈值脆弱修正 E84/限速否定 S30/令牌面 κ≈0.25 决定性/附录A 方差推翻双峰夹谷 S29）；红线 91/F40/S30（详见手册 §9 十五轮候选）
- `trajectories/2026-09-14/task-040-Tier2管道验证与Step0收官.md` — 原装 add_episode 4/4 集入库（40实体/66关系，Tier1 八份原始233边去重合并）；三条件验证全过：R6 元文本防御（excerpt4 零污染 vs Tier1 双败）/伪锚点时序45边/跨章去重；4次发射3折调试记录（cross_encoder占位/driver作用域/属性名/DateTime序列化）
- `trajectories/2026-09-14/task-041-闲时任务机制调研与下发模板.md` — 官方文档核证闲时任务（免费排队/到点回队续跑/后台子代理不支持/人工介入不免费）与 /goal 目标模式；交付 `正典库构建系统/P1执行区/闲时任务提示词模板.md` v1：三层架构（闲时任务外壳//goal 内核/BUILD-STATE+逐件commit 磁盘锚，锚层不依赖会话），STATE=缓存磁盘=事实（R-014 入断点协议），含 P1-M1 预填示例
- `trajectories/2026-09-14/task-042-P1M1下发准备与首阻.md` — （审核线会话产出；索引行由构建线 wrap-up 顺带补登，归属审核线）P1-M1 下发准备与首发受阻：环境实测全绿+凭证 setx 用户级+模板 v1.3（scoped-add），OffPeakCreate 被拒（账号未开通闲时任务）→ 下发单落盘 P1执行区/待发
- `trajectories/2026-09-14/task-043-P1M1六技能骨架构建.md` — 构建线执行 P1-M1（交互式路径=/goal+下发单正文，闲时任务替代路线首发跑通）：U0 36 技能外挂装机（安检 1 命中=Neo4j 官方安装器文档）；四契约 schema 照抄 Part IV+stdlib 校验器；六技能骨架（coordinate 幂等坐标/anchor 伪锚点禁墙钟+18 条精度抽检/extract R6 内置 stub 抽取/gate1 四校验原因码/quarantine 五分组请你确认报告/store 三态+supersedes 版本化）；73 单测全绿+六技能集成冒烟 20/20 双跑（抓出 transitions 非幂等真缺陷→P-017）；9 commit 逐单位可证；交接文书+issues 三件+6 待确认（详见 `正典库构建系统/cbb-skills/交接文书-P1M1.md`）
- `trajectories/2026-09-14/task-044-全量构筑版开线与实验版冻结.md` — 用户裁决转全量构筑版（先 16 仓全量分析再构筑，极致时间换质量）：cbb-skills 冻结为实验版（FROZEN 原位保全，交接 73 单测基线/P-017/issues 三件/R6+伪锚点样例）；总纲六节报告判据（三谜仓必答）+17 单位预播种；一句话提示词=规则外置指针化（长模板管开线、一句话管流水）；Step 0 三条件作每仓 §5 硬对照
- `trajectories/2026-09-14/task-045-F3线P3任务执行.md` — W-4 接口条款兑现（冒烟复跑+口径变更误报实证→PT-015 采纳）+ DEPLOY/L8LAB 并档收尾确认 + KB 月度体检首次窗口 0 问题/4 legacy 提醒（详见 PT-015）
- `trajectories/2026-09-14/task-046-F2线P3任务执行.md` — P-B3 阈值自举回测（解锁条件 068e2ed 核证；闭案门未触发方法保留；汇总臂救回 H-R2-1 一例但边缘翻转 +0.0061；DC-3 桶异质分解可救仅 1/4；自举带表交下一轮）+ W-7 档认领评审九项裁决（归 F2 三/转线四/归档二）（详见 PT-012 v4 / P-011 v2）
- `trajectories/2026-09-15/task-047-全量构筑版阶段一验收.md` — 审核线验收 17/17 通过（U-A08 有条件：节名+直引可核但行号系统性缺失→整改）；三谜独立复测全命中（author-toolkit 0/0、agent-skills 150.ts、neuro-book 2285.ts/54.2万行/node_modules=0、claude-book 191md）；引证抽验实质 5/5、行号精确 4/5；Issue 001 采信→总纲 v1.1 归属勘误；U-A17 八条待确认 triage（2 已裁/1 采纳/1 预批准/2 用户裁决/1 保守维持/1 挂账）；验收判定=全量构筑版-分析报告/验收判定-阶段一.md
- `trajectories/2026-09-15/task-048-本体构筑工单固化与goal发车件.md` — 三裁决落定（第四态不增设/cbb-merge并入/basic-memory保守）；本体构筑-工单v1.0=唯一指令源（U-B00~B09/§3十轮自审协议：十镜头R1-R10逐轮留痕+零发现须列检查证据+出口门=最后两轮零新发现/到点回队是常态不许降标收工）；STATE预播种；实验版只读跑测须-B；发车件指针化交用户经闲时任务下发
- `trajectories/2026-09-15/task-049-本体构筑执行.md` — U-B00~B09 全量交付（构建线/goal 无人值守）：cbb/ 本体版 v2 落地（契约 v2.0 十一新字段+coordinate 编号注册表+anchor 双时间轴+extract 四面防御+gate1 三域+quarantine 三子类 urgency+store 双轨 UNIQUE 约束族）161/161 单测绿≥73 基线+集成冒烟 74/74 同目录双跑 EXIT 0+真管道 blocked 留阶段三（Neo4j 未监听）+十单位十轮自审出口门全过+10 笔 scoped commit；交接文书=cbb/交接文书-本体构筑.md（11 条待确认移交审核线；构建线无权自宣验收）

## 工具与自动化
- **本地 LLM-judge API**（2026-09-11 收录为可用工具，当日活体冒烟通过：服务在线、锚定提示词下返回纯 JSON）：LM Studio OpenAI 兼容服务 @ `127.0.0.1:8080`，judge 模型 M-Prometheus-14B；快速接入=根目录 `LLM-judge-API-快速接入.md`（全量版 `大审查/混元/本地LLM-judge-API-使用说明与接入文档.md`，Python 入口 `judge_adapter.make_judge("llm-api")`，缺环境变量即拒绝启动）。调用红线（违反即数据作废）：送评 canonical order（该 judge 位置偏见 .65）/ rubric 锚定必开（无锚定实测跑飞说英文）/ 分数只作内部比较不外报（冒烟中正确答案被打 0 分）/ temp=0 跨会话留 ±0.05 / `llm_judge_cache_*.json` 不许删。适用边界：探针与试点评分（本地 ~0.6s/次、并发 8→3.5 calls/s，全量实验切 DeepSeek flash API）；**不进 memevo 等确定性沙盒的评分回路**（零依赖+两次逐行一致契约）
- 外部技能装机（2026-09-08，PT-008）：`~/.zcode/skills/` 新增 12 技能——grill-me/grilling/tdd、find-skills、K-Dense 六件（consciousness-council/literature-review/paper-lookup/database-lookup/citation-management/scientific-writing）、lark-doc/lark-shared；lark-cli v1.0.94 已装（用前需 `lark-cli auth login --recommend`）
- `tools/search_knowledge.txt` — 知识检索：关键词直击 + [[邻居]]联想一跳（HippoRAG 2 简化版）
- `tools/lint_knowledge_base.txt` — 全库体检：断链/超限/frontmatter/schema/过期条目（`py -X utf8` 运行）
- 每月 1 号 9:00 自动体检 + 睡眠整理报告（Letta sleep-time 模式，只建议不执行）
- L8 沙盒 `_l8_lab/`（2026-09-04 启用）：自指演化试验田，月度体检跑变异引擎首轮
