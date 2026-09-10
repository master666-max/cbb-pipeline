# Task-018 · 外部技能装机：12 个 Agent Skills + lark-cli（2026-09-08）

## 一句话
应「要最新最叼的插件/技能」需求，调研 skills.sh 等信源后，从 4 个上游仓库精选 12 个技能手动装入 ZCode 用户技能目录，并装好飞书官方 CLI 本体。

## 复现
1. `git clone --depth 1` 四仓库到临时目录：mattpocock/skills、vercel-labs/skills、K-Dense-AI/claude-scientific-skills、larksuite/cli；
2. 逐个读 SKILL.md frontmatter 安检（name / allowed-tools / compatibility / metadata.requires）；
3. `cp -rn`（no-clobber，防覆盖）拷入 `C:\Users\26672\.zcode\skills\`；
4. CLI 依赖单独装：`npm install -g @larksuite/cli`（v1.0.94），`lark-cli --version` 验货通过。

## 装机清单（12 技能 + 1 CLI）
| 来源 | 技能 |
|---|---|
| mattpocock/skills | grill-me、grilling（grill-me 的引擎，隐藏依赖）、tdd |
| vercel-labs/skills | find-skills（skills.sh 全时段榜一元技能） |
| K-Dense claude-scientific-skills | consciousness-council、literature-review、paper-lookup、database-lookup、citation-management、scientific-writing（六件精选；其 docx/pdf/pptx/xlsx **故意不装**——与 ZCode 官方 document-skills 重名冲突） |
| larksuite/cli | lark-doc、lark-shared（CLI 配套技能，官方中文） |

## 关键决策
- 走「clone→手动拷贝」而非 `npx skills add`：后者对 ZCode 目录的支持【待确认】，手动路径 100% 可控且符合不覆盖铁律。
- K-Dense 只装 6/134：用户点名「文献检索和文档类 + Consciousness Council」；若装 K-Dense 版文档四件套会与已有官方 document-skills 打架。
- grill-me 单装会变空指针——其 SKILL.md 正文仅一行「Call the Skill tool with "grilling"」，引擎 grilling 必须随行。

## 踩坑与经验
- npm v12 默认拦截 @larksuite/cli 的 postinstall 脚本（allowScripts 机制），但二进制自愈下载成功、`lark-cli --version` 正常——**拦截≠装坏，先验货再决定是否补 `--allow-scripts`**。
- lark-doc 有两层前置依赖：`bins: ["lark-cli"]` + `skills: ["lark-shared"]`——**装技能前必读 frontmatter 的 metadata.requires**。
- K-Dense 精选件依赖现状：paper-lookup 要 Python 3.11+（纯标准库，本机走 py 启动器，具体版本【待确认】）；citation-management 要 Python requests 包；literature-review 的 OPENROUTER_API_KEY 为可选（不填可用）——呼应 [[P-001]]。
- lark 实际使用前需 `lark-cli auth login --recommend` 浏览器授权（用户本人操作；凭证入 OS 钥匙链不入文件，符合 D-004）。

## 复用提示
- 装任何外部 skill 的标准动作：先看 SKILL.md 的 requires / allowed-tools / compatibility 三字段，再 `cp -n`；bins 型依赖装本体并 `--version` 验货。详见 [[PT-008]]。
- 新装技能需**新会话**才会出现在 ZCode 的 Skill 工具列表（会话启动时扫描）。

关联：[[PT-008]] · [[P-001]]
