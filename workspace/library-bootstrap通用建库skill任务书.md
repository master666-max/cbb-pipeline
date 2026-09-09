# 任务书：library-bootstrap —— Agent Harness 通用建库 Skill

> 起草 2026-09-04。**本文件是任务书，经用户批准后才开工。**
> 一句话目标：做一个可拷贝到任何 agent harness（ZCode / Claude Code / Cursor / Codex CLI / Trae…）的 skill 包，输入一句话指令（如「建 L4+RP 库」），即在该 harness 的工作区一键建出结构完全一致、可校验、可维护的双库体系。

---

## 一、设计目标与硬性要求对照

| 用户要求 | 设计回应 | 验收标准 |
|---|---|---|
| 1. 多选项：架构与功能自由安装组合 | 10 个功能模块（M-*）+ 6 个特色包（X-*），模块级点菜 | 任一合法模块组合均可安装成功 |
| 2. 多预设：从最稳定到最前沿，颗粒度稍多 | L0~L7 八档嵌套预设 + 自由组合模式 | 每档预设有明确定义文件与模块清单 |
| 3. 特色预设：按用途与技术独特性 | 6 个特色包：RP/写作/语料/代码/研究/多 Agent | 每个特色包有专属模板与检索特化 |
| 4. 稳定性强、可维护性高 | 模板复制式安装（非自由生成）+ manifest + 幂等 + 移植 lint | 空目录重复安装两遍，第二遍零改动；lint 0 问题 |

## 二、核心设计思想：强 Agent 可复现性

不同 harness 的模型不同、会话不同，若靠 agent「自由发挥」建库，每次产物必有差异。可复现性来自三件事：

1. **模板复制 > 自由生成**：所有结构文件（骨架、索引、技能、脚本）以模板文件形式随 skill 携带，安装=复制+填槽。模板中变量用 `{{SLOT:说明}}` 标注，agent 只填槽不改结构。
2. **清单式安装**：每个模块自带 `install.md`（确定性步骤：复制哪些文件、填哪些槽、跑哪个校验），agent 照单执行，每步可验证。
3. **manifest 收尾校验**：建库完成后根目录生成 `.library-manifest.json`（预设名/版本/模块清单/harness 适配/日期），配套 `lint_portable` 脚本对照 manifest 逐项校验——结构不符即报错，防走样。

## 三、Skill 包结构（交付物）

```
library-bootstrap/
├── SKILL.md                  # 入口：路由决策树（用户说要建库 → 问/解析 预设+模块 → 调 install 流程）
├── presets/                  # 8 个预设定义 + 6 个特色包定义（每档一个 md：模块组合表+参数+适用场景）
├── modules/                  # 模块模板库
│   ├── m-core/               #   骨架+铁律+README（必选基座）
│   ├── m-index/              #   双索引（knowledge/_index + archive/_INDEX）
│   ├── m-loop/               #   task-start / wrap-up 闭环技能
│   ├── m-tools/              #   lint + search（纯标准库，.txt 后备形态）
│   ├── m-schema3/            #   条目 schema：关键词/关联/版本/来源/置信度/状态
│   ├── m-evolve/             #   wrap-up 演化回扫（第 6 步）
│   ├── m-soul/               #   SOUL.md + USER.md + 三级加载入口
│   ├── m-reflect/            #   reflect 技能 + reflections.md
│   ├── m-cron/               #   定时体检指引（有 cron 的 harness 用内置，没有则手动模式）
│   └── m-radar/              #   前沿雷达参考图（精简版）
├── packs/                    # 特色包（叠加在任意 L≥1 之上）
│   ├── x-rp/                 #   角色扮演库
│   ├── x-writer/             #   小说/剧本写作库
│   ├── x-corpus/             #   语料分析库
│   ├── x-code/               #   代码工程项目库
│   ├── x-research/           #   研究/文献综述库
│   └── x-multiagent/         #   多 Agent 协作库
├── adapters/                 # harness 适配层
│   ├── harness-detect.md     #   环境探测流程（python3/py/node 探测、hook 拦截探测、cron 能力探测）
│   └── entries/              #   AGENTS.md / CLAUDE.md / .cursorrules 三套入口模板
├── scripts/
│   ├── bootstrap_verify.txt  #   manifest 校验（对照预设定义逐文件检查，纯标准库）
│   └── lint_portable.txt     #   移植版体检（断链/行数/frontmatter/schema）
└── references/
    ├── decision-tree.md      #   选型决策树（给 agent 的路由手册）
    └── compatibility.md      #   harness 兼容矩阵（探测结果×功能可用性）
```

## 四、预设梯度（要求 2：从最稳到最前沿，8 档嵌套）

| 档位 | 名称 | 模块组合 | 理论依据 | 稳定性 |
|---|---|---|---|---|
| L0 | 裸奔版 | m-core | 零依赖，纯目录+铁律+README，任何 harness 都能跑 | ★★★★★ |
| L1 | 基础闭环版 | +m-index +m-loop +适配入口 | v2 复刻（实验区已验证） | ★★★★★ |
| L2 | 标准校验版 | +m-tools | L1+lint/search，建完即可自检 | ★★★★☆ |
| L3 | 演化版 | +m-schema3 +m-evolve | A-MEM：条目属性+回扫修订 | ★★★★☆ |
| L4 | 灵魂版 | +m-soul | Letta block / OpenClaw SOUL 生态 | ★★★☆☆ |
| L5 | 反思版 | +m-reflect +m-cron | Generative Agents + sleep-time | ★★★☆☆ |
| L6 | 前沿全家桶 | +m-radar | 本库 v4 完整复刻，21 条 SOTA 雷达 | ★★★☆☆ |
| L7 | 实验版 | L6+向量检索等实验模块 | 雷达图「不适用待触发」项，装时弹风险提示 | ★☆☆☆☆（明标） |

- **嵌套规则**：Ln 自动包含 L0..Ln-1 全部模块，无需重复指定。
- **自由组合模式**：不吃嵌套，直接点菜（如「m-core+m-index+m-soul，不要 loop」），bootstrap_verify 会拒绝非法组合（m-evolve 依赖 m-schema3，m-reflect 依赖 m-loop 等依赖表见 decision-tree.md）。

## 五、特色包设计（要求 3）

每个特色包 = 替换/扩展 m-core 的知识域模板 + 特化检索关键词 + 专属 wrap-up 复盘问题。**只换知识域骨架，双库机制不动**（稳定性复用）。

| 特色包 | soul 层替换 | knowledge 域特化 | archive 域特化 | 特色检索 |
|---|---|---|---|---|
| X-RP 角色扮演 | 角色人格卡（语气/口癖/立场） | 世界观/角色卡/剧情线/名场面四库 | 跑团记录/对话存档 | 按角色出场检索、剧情线时间轴 |
| X-Writer 写作 | 作者文风画像 | 设定集/时间线/伏笔账本/文风样本 | 章节废稿 attic | 伏笔未回收检索、设定冲突检查 |
| X-Corpus 语料 | 分析师画像 | 清洗规则库/统计范式库 | raw→interim→processed 数据流（DVC 提示） | 规则命中检索 |
| X-Code 代码 | —（m-soul 可选不装） | bug 模式库/ADR 决策记录/范式库 | 项目 manifest 归档 | bug 症状→根因检索 |
| X-Research 研究 | —（可选） | 文献笔记/综述演化/来源可信度分级 | 文献归档 | 主题→文献网络 |
| X-MultiAgent | 协作契约（分工/权限） | 共享语义层+各 agent 分区 | 各 agent 产出归档 | 按 agent/按主题双维检索 |

（X-RP 依据本工作区 mepub 项目的角色卡/世界书/咏唱分类实战经验提炼；X-Corpus 依据语料分析项目实战。）

## 六、稳定性与可维护性设计（要求 4）

1. **幂等**：安装前扫描目标目录，已存在的文件一律跳过并在报告中列出（铁律 1 移植：永不覆盖）；重复安装 = 增量补齐 + 零改动。
2. **环境探测先行**：`harness-detect` 第一步跑探测脚本（python3 / py / node 可用性、.py 拦截测试、cron 能力），结果写入库根 `env/ENVIRONMENT.md`；后续所有脚本形态按探测结果选择（py / python3 / .txt 后备），把本机 P-001 类坑变成 skill 内置免疫。
3. **零第三方依赖**：scripts 全部只用 Python 标准库；无 Python 环境时降级为「清单式手工安装」（install.md 本身就是完整步骤）。
4. **版本化与升级**：`.library-manifest.json` 记录 preset 名+skill 版本+模块清单；skill 升级时 diff manifest 决定增量动作，已建库不推倒重来。
5. **双向可追溯**：skill 内每个模块注明「源自本工作区哪个实例/哪条 pattern」；装出去的库根 README 注明由 library-bootstrap vX 生成——出问题能回溯到源头。
6. **测试即验收**：见第七节。

## 七、测试计划（在本机 ZCode 内模拟多 harness）

| # | 场景 | 断言 |
|---|---|---|
| T1 | 空目录装 L1 | manifest 齐全、lint_portable 0 问题 |
| T2 | T1 后再跑一遍 L1 | 第二遍零文件改动（幂等） |
| T3 | 空目录装 L6 | v4 等价结构 100% 就位 |
| T4 | 空目录装 L4+X-RP | 灵魂层=角色人格卡、四库骨架就位、检索特化生效 |
| T5 | 非法组合（m-evolve 无 m-schema3） | bootstrap_verify 拒绝并说明依赖 |
| T6 | 双入口（AGENTS.md+CLAUDE.md） | 两入口都生成且内容一致仅引用路径差异 |
| T7 | 无 Python 降级 | 清单式手工安装路径走通（文档演练） |

## 八、执行阶段（批准后）

| 阶段 | 内容 | 产出 |
|---|---|---|
| Ph1 | 设计冻结：模块依赖表、manifest JSON schema、槽位清单 | decision-tree.md + manifest 规范 |
| Ph2 | 模块模板制作（10 个 M-*） | modules/ 全目录 |
| Ph3 | 特色包制作（6 个 X-*） | packs/ 全目录 |
| Ph4 | 适配器 + 脚本（探测/校验/lint 移植） | adapters/ + scripts/ |
| Ph5 | 预设组装 + SKILL.md 路由 | presets/ + SKILL.md |
| Ph6 | T1-T7 测试 + 修复 | 测试报告 |
| Ph7 | wrap-up 六步收尾（归档 + PT-004 验证 +1 + memory 同步） | 归档 README |

## 九、【待确认】清单（开工前请裁决）

1. **skill 安放位置**：建议 `knowledge/skills/library-bootstrap/`（本库可路由使用，拷走整个目录即迁移）。要不要同时在根目录放一个「发布副本」方便打包？
2. **特色包取舍**：拟了 6 个（RP/写作/语料/代码/研究/多 Agent），有没有要加/砍的？
3. **L7 实验档**：要不要做（涉及向量检索等不稳定项，标 ★ 只给尝鲜）？还是砍掉保持 7 档全稳定？
4. **交互方式**：默认「参数式」（一句话指令直达）+ 有 AskUserQuestion 能力的 harness 加「交互式向导」，可以吗？
5. **X-RP 的知识域模板**：直接以迷宫最深部项目做范例填槽，还是用架空示例（避免剧透内容随 skill 迁移出去）？我建议架空示例。

---
*依据：本库 PT-004（3 次验证的建库路径）、knowledge/references/sota-memory-radar.md（七派 21 条目）、实验性双库工作区建库提示词 v2。本任务书本身遵循「先计划书后执行」铁律。*
