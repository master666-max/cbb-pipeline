# 知识库索引（2026-09-04 · v4 更新）

> **每次任务开始必读本文件。** 常驻 AI 上下文，保持 200 行内。
> 加载顺序：`soul/SOUL.md` → `soul/USER.md` → 本文件。
> 维护规则：每次 wrap-up 的第 5 步同步更新；按验证次数/触发频率排序；断链当场修复（或跑 `py -X utf8 tools/lint_knowledge_base.txt`）。

## 反思计数
- 自最后反思以来 wrap-up 次数：2（2026-09-08 外部技能装机、自演化沙盒 task-020）
- 最后反思：2026-09-06（R-001~006）

## 高频 Pitfalls（按触发次数排序）
- [P-001 Windows 脚本执行：用 py 启动器，.py 被拦就写 .txt](pitfalls.md#p-001) — 多次触发（EPUB/PDF 提取、docx 后处理、验收均命中）
- [P-002 EPUB 解包文件名 cp437 乱码须修复](pitfalls.md#p-002) — 1 次触发
- [P-003 清洗误报三陷阱：正文词/破折号字形/半角方括号](pitfalls.md#p-003) — 1 次触发
- [P-004 批量生成含特殊字符文本别用 sed，直接 Write](pitfalls.md#p-004) — 1 次触发（library-bootstrap 模板生成翻车）
- [P-005 分发包模板中性化 + install.md 引用完整性](pitfalls.md#p-005) — 1 次触发（独立工作区实装抓出，T18-T21 锁定）
- [P-006 核验报告附证据快照 + 同构案件判例回收对齐](pitfalls.md#p-006) — 1 次触发（P3-10 双标事故，v2.1.2 转单）
- [P-007 沙盒度量缓存须随库写递增 rev（pre≡post 假象）](pitfalls.md#p-007) — 1 次触发（自演化沙盒 X2d）
- [PT-007 文档缺陷与实现状态分开判 + 题录改动对账先行](patterns.md#pt-007) — 已验证 2 次（P3-10 双标案 + X-003「Wang 等」现行犯）
- [PT-008 外部 Agent Skills 手动装机路径](patterns.md#pt-008) — 已验证 1 次 · 适用：装第三方技能（clone→安检→cp -n→CLI 依赖随行）
- [PT-009 真引擎沙盒演化实验流水线](patterns.md#pt-009) — 已验证 1 次 · 适用：真实系统外挂自优化机制的可行性验证（等价门→基线→演化→危险矩阵→内核对比）

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

## 工具与自动化
- 外部技能装机（2026-09-08，PT-008）：`~/.zcode/skills/` 新增 12 技能——grill-me/grilling/tdd、find-skills、K-Dense 六件（consciousness-council/literature-review/paper-lookup/database-lookup/citation-management/scientific-writing）、lark-doc/lark-shared；lark-cli v1.0.94 已装（用前需 `lark-cli auth login --recommend`）
- `tools/search_knowledge.txt` — 知识检索：关键词直击 + [[邻居]]联想一跳（HippoRAG 2 简化版）
- `tools/lint_knowledge_base.txt` — 全库体检：断链/超限/frontmatter/schema/过期条目（`py -X utf8` 运行）
- 每月 1 号 9:00 自动体检 + 睡眠整理报告（Letta sleep-time 模式，只建议不执行）
- L8 沙盒 `_l8_lab/`（2026-09-04 启用）：自指演化试验田，月度体检跑变异引擎首轮
