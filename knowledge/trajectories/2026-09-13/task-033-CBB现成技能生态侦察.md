# task-033 · CBB 现成技能生态侦察（2026-09-13）

## 触发
用户令：围绕 `正典库构建系统/正典库构建系统 CBB v1.0.md`（构造即正确的小说正典库流水线设计基线），「仔仔细细的，穷网络信息搜索方法，看看有没有现成的skill」。

## 方法（可复用路径）
1. 本地 `find-skills` 技能引路 → `npx skills find` 关键词矩阵 **~35 查询**（knowledge graph / entity extraction / timeline / consistency / fact check / llm judge / graphrag / neo4j / obsidian / novel / fiction / story bible / lorebook / worldbuilding / canon / plot / ebook / literary / corpus / 知识库 / 小说 / 世界书 / 网文 / 伏笔 / 角色卡 / 设定集 / story analysis / world bible…）
2. WebSearch ×6：官方源（anthropics/skills 无小说/知识库专项，17 个顶层技能均为文档/创意/技术/企业向）、生态清单（ComposioHQ）、SillyTavern lorebook 生成工具、目录站（skillsdirectory/awesomeskill/mcpmarket/skillsmp 8 万+）
3. **clone 16 仓 → 本地读 SKILL.md 核证**（PT-008 路径；15 成功，honestman9527/novel-studio 已 404）。raw.githubusercontent.com 直连超时、api.github.com 空响应 → 改 git clone + shields.io `.json` 星标接口。

## 关键发现（星标 | skills.sh 安装量 | 核证结论）
| 仓库 | 星 | 装机 | 与 CBB 对口点 |
|---|---|---|---|
| lingfengqaq/webnovel-writer | 7.1k | ~800/技能 | **工程化最完整**：SQLite+RAG+dashboard；`knowledge query-entity-state/query-relationships`、`memory-contract get-open-loops`（伏笔开环）、webnovel-doctor 只读体检 |
| zenstory-ai/oh-story-claudecode | 6.8k | 13.8K(analyze) | 长篇拆文管道（黄金三章→逐章摘要→聚合→**设定关系**落盘拆文库/）+ story-import 逆向重建写作工程；明确适配 ZCode（检测 .zcode/ 降级 solo） |
| wanikua/danghuangshang | 2.7k | ~100/技能 | 中文小说五文件档案：characters/world/**foreshadowing 伏笔台账**/timeline/**relations 关系网** + novel-archiving 每章归档 + novel-review 引用原文审核 |
| hamelsmu/evals-skills | 1.7k | 1.3K | judge 方法学：write-judge-prompt / validate-evaluator / eval-audit / error-analysis（对口 CBB 门2 与校准器） |
| danjdewhurst/story-skills | 220 | ~600 | **story bible CLI**：story validate/reindex 确定性校验 + revision-continuity（矛盾/时间线/promises-payoffs 伏笔对账）+ `story import` 从手稿产实体候选 |
| echo-xianyu/worldbook-skill | 198 | 15 | SillyTavern 角色卡/世界书；**二创=从既有作品提取设定**（information-extraction-guide）+ card-generator.py |
| jwynia/agent-skills | 157 | 80-700 | 112 技能矿：dna-extraction（功能 DNA）、story-analysis、reverse-outliner、ebook-analysis、fact-check、worldbuilding 11 件套 |
| neo4j-contrib/neo4j-skills | 110 | 600-1.1K | 官方 29 技能：modeling/document-import/graphrag/cypher/agent-memory（对口 CBB Graph Store=Graphiti+Neo4j） |
| tance-mang/chinese-webnovel-skills | 60 | ~17/技能 | **continuity 七条逻辑链体检**（行为/因果/资源/知情人名单/伤势/战力/情绪+时间线+世界状态）≈ CBB 门3 的写作侧镜像；memory 档案含 03_伏笔追踪 planted→回收表 |
| anshler/graphify-novel | 68 | 170 | 事件带 ID(E001)的情节树 + thread(开/闭环) + query/path 图查询 + review against bible |
| bybren-llc/story-systems-template | 66 | 60 | 编剧向 5 registry（角色/时间线/地点/道具/服装）连续性追踪 |
| notnotype/neuro-book | 641 | ~1-800 | 网文工作台：SillyTavern 卡导入、番茄 reference 导入、llmlint、RP 模式 |
| thomashoussin/claude-book | 115 | ~16 | book-analyzer（书→style/characters/universe bible）+ bible-merger（多书合并 canonical bible） |
| basicmachines-co/basic-memory-skills | 25 | 521 | memory-literary-analysis + ingest/defrag/lifecycle |

## 缺口分析（核心结论）
**无任何现成 skill 实现 CBB 的"构造即正确"路线**。生态全部是"写作侧档案 + 事后核对"：最接近的门禁件也只有确定性结构校验（story validate）与 LLM 逐链核对（continuity），均无——三态写入（confirmed/provisional/quarantine）、证据四元组 (卷,章,行,引文) 强制、隔离区一等公民、锚点树人工前置、置信度校准三阈值、VerdictKB 先例库、KBI 联邦端口、影子审计/冻结回测。

## 复用与纪律兑现
- PT-008（clone→安检）全程；R-014 精神：对 skills.sh 宣称安装量不轻信，全部本地 clone 开棺核证 SKILL.md 原文
- find-skills 质量门标准执行（安装量+星标双指标）
- 轨迹编号先 ls 查重（R-015）：今日 030×2/031/032 在案，取 033

## 环境新证（已回写 USER.md 环境雷区）
raw.githubusercontent.com 直连超时（ECONNRESET/-connect timeout）；api.github.com 星标查询返回空——shields.io `/<repo>.json` + `git clone --depth 1` 为可靠替代。
