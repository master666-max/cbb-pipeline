# BUILD-STATE · 全量构筑版阶段一（缓存，事实以磁盘+git为准）

> 建立：2026-09-14 审核线预播种。协议照《全量构筑版-总纲.md》§S。
> 双锚：/goal 由用户侧设置（判据见总纲 §G）；本头部为等价兜底锚。

目标判据：U-A01~U-A17 全部 done；16 仓各一份独立详报落 `全量构筑版-分析报告/`（§R 六节齐备、断言带 文件:行号、三谜仓给出谜底）；U-A17 跨仓综合报告落盘；逐单位 commit 可证。

单位清单（状态：todo）：
- U-A01 agent-skills | 状态=done | 判据=总纲§R 六节报告落盘+错挂本仓的"5.8万行js"谜底已给 | 证据=全量构筑版-分析报告/agent-skills.md（六节齐、断言带文件:行号、主线抽验12处行号全中；谜底=150个.ts共58,386行技能自带Deno CLI脚本，.js为0）+ Issue 001 | 幂等说明=报告快照型，重写走新版本
- U-A02 author-toolkit | 状态=done | 判据=六节报告落盘（三谜"5.8万js"经Issue 001证错挂本仓：实际0 js，谜底在U-A01已给，本仓报告§1已注明） | 证据=全量构筑版-分析报告/author-toolkit.md（六节齐+断言带文件:行号；亮点=finding-schema confidence双口径/审计三分类+引擎权威化/continuity修复策略≈supersedes） | 幂等=报告快照型，重写走新版本
- U-A03 basic-memory-skills | 状态=done | 判据=六节报告落盘（含 sota-memory-radar 对照：七派未收录此件，定位C派图联想检索实现+D派反思思想） | 证据=全量构筑版-分析报告/basic-memory-skills.md（六节齐+断言带文件:行号；亮点=literary-analysis六阶段管道/Seed先行/validation warn-strict双档/lifecycle archive-never-delete；许可=README文字声明MIT但无LICENSE正文文件【待确认】） | 幂等=报告快照型，重写走新版本
- U-A04 chinese-webnovel-skills | 状态=done | 判据=六节报告落盘（清洗口径对照=引号规范版本化治理 CHANGELOG v0.29.1） | 证据=全量构筑版-分析报告/chinese-webnovel-skills.md（六节齐+断言带文件:行号；至今最贴域内：八档案模型/伏笔编号台账/时间线绝对锚点+倒计时兑现/知情人名单/世界状态量化/七条逻辑链/失忆三临界点50-100-300章；MIT最干净+维护最活跃；短板=自由文本无校验/两态无隔离——差异化恰为CBB四契约三态） | 幂等=报告快照型，重写走新版本
- U-A05 claude-book | 状态=done | 判据=六节报告+三谜(191篇md)谜底已给 | 证据=全量构筑版-分析报告/claude-book.md（谜底①=191md乃框架+完整实例双重身份：club-des-cinq 18本书分析56+state章状态76+法语正文20+bible14等；谜底②=体积在ebook资产12M/旧封面5.7M/成品电子书4M+.git二进制；同构度第一仓：book-analyzer证据式抽取/bible-merger冲突解决表(后书优先+并陈)/bible永久state瞬态双层/六gate+3迭代/knowledge含dramatic irony；MIT干净） | 幂等=报告快照型，重写走新版本
- U-A06 danghuangshang | 状态=done | 判据=六节报告落盘（五文件schema精读+主线抽验6处全中） | 证据=全量构筑版-分析报告/danghuangshang.md（五文件档案=characters/world/foreshadowing/timeline/relations；伏笔五态含🔴遗漏超期态；角色状态变化表(前|后|因)+追加不覆盖；任务状态机七态含revision_required+错误三分含rejected=Verdict工程同构最高件；写路径白名单；勘误两条=仓实为当皇上×OpenClaw多Agent系统小说仅翰林院模块+js实测45/6678非60/8509） | 幂等=报告快照型，重写走新版本
- U-A07 evals-skills | 状态=done | 判据=六节报告落盘（含已装机外挂沿用判定=维持+【待确认】上游迁移） | 证据=全量构筑版-分析报告/evals-skills.md（judge四要素:单一判据/二值反Likert/borderline例/critique先于verdict；校准:三分割+TPR-TNR+test只跑一次+Rogan-Gladen修正+Bootstrap CI+锁模型版本；meta-skill七原则；**上游已弃用迁移ai-evals-course/evals-skills**README:3-8→待确认装机源切换；与Step0金标方法学=同一方法学两半合体） | 幂等=报告快照型，重写走新版本
- U-A08 graphify-novel | 状态=done | 判据=六节报告落盘 | 证据=全量构筑版-分析报告/graphify-novel.md（601行SKILL.md设计密度第一梯队：EXTRACTED/INFERRED边证据分层≈R-010图谱版/[?]内联不确定标记+行号汇总≈quarantine内联式/review不写盘+update必先review+正典至上三条款/事件ID追加序/slug主键+aliases别名归一字段级最强/knows-unaware_of双清单/提示注入防御16仓首见/批扫章协议；依赖外部graphify工具不装外挂图层已由neo4j覆盖） | 幂等=报告快照型，重写走新版本
- U-A09 neo4j-skills | 状态=done | 判据=六节报告落盘（含已装机外挂沿用判定=维持，唯一运行时价值>设计价值仓） | 证据=全量构筑版-分析报告/neo4j-skills.md（29技能官方件机器维护活跃MIT零密钥；图层六件可用：document-import构建/graphrag检索明确分工/modeling五律/import冲突处理/agent-memory事实级去重confidence更新而非新建节点=三态最同构单条/cypher 12硬默认；去重三档Resolver=16仓最强(Exact/Fuzzy0.9/SpaCy语义+label过滤流)；元文本防御无/时间归一仅存储类型规范；小勘误README24vs磁盘29） | 幂等=报告快照型，重写走新版本
- U-A10 neuro-book | 状态=done | 判据=六节报告+三谜(54.7万js疑vendored)谜底已给 | 证据=全量构筑版-分析报告/neuro-book.md（谜底双重翻案：①.js实测仅4文件,巨量实为.ts 2285文件/541,951行(+vue/tsx/mjs)——task-036 JS桶并了TS系同Issue001口径失真②vendored证伪:无node_modules,12包monorepo真源码=AI小说写作桌面应用真产品;AGPL红旗维持=代码零接触,设计思想经报告文字转述吸收;nb-memory双时间轴tick/instant+as-of双语义+缺坐标判不可见=16仓时间设计之冠,cbb-anchor第一对照项;canon晋升门控/issue二态E-A/StoryPromise到章注入/读写分权14人格/会话JSONL+lease） | 幂等=报告快照型，重写走新版本
- U-A11 oh-story-claudecode | 状态=done | 判据=六节报告落盘 | 证据=全量构筑版-分析报告/oh-story-claudecode.md（拆文七阶段管道+长篇三件套：章节边界表单一切片真值/逐章子代理5-8批/降维聚合15KB章→≤8K回传→√N合并(914章61批实测)；别名四分类proper_name-nickname-descriptor-title+0.85门槛+存疑分开建=去重规则层最强(与neo4j算法层互补)；机械硬检查grep计数不依赖自报=R-018落地；timeline双视图reveal_chapter；append/revision事务分离；元文本防御缺口反面样本+1(章末求月票无过滤)；MIT极活跃；爬虫件ToS风险排除） | 幂等=报告快照型，重写走新版本
- U-A12 sillytavern-skills | 状态=done | 判据=六节报告落盘 | 证据=全量构筑版-分析报告/sillytavern-skills.md（2技能小仓；CCv3双控制面=system_prompt持久契约vs post_history_instructions末轮转向+禁暗中对抗；lorebook激活参数族scan_depth/insertion_order/token_budget/selective+secondary_keys=X-RP下游导出字段语义；validate_card.py 160行轻量校验器；审查八节含Safety-Leakage独立节；无LICENSE=零复制只读参考；与PT-013互补=它格式侧我们内容侧） | 幂等=报告快照型，重写走新版本
- U-A13 story-skills | 状态=done | 判据=六节报告落盘（Tier A 契约级精读+主线抽验4处全中） | 证据=全量构筑版-分析报告/story-skills.md（编译器哲学仓：三域分离validate-links-continuity统一{ok,errors,warnings}/关系逆类型12对+对称12项双向回链校验/契诃夫枪≥3章超期算法/P0-P3修复行动生成器每条附精确命令/章号三处一致强制/writeChanged内容不变不写+打包逐字节一致/写入安全围栏/可执行反例+100%覆盖门禁=工程纪律16仓最强;MIT;缺口=无JSON输出(R-020反面)/章号全序替代时间/无别名去重;勘误=CLI实为src三件套非单story.js,skills内3211行是打包产物） | 幂等=报告快照型，重写走新版本
- U-A14 story-systems-template | 状态=done | 判据=六节报告落盘（双镜像去重=.claude为正本.gemini适配层） | 证据=全量构筑版-分析报告/story-systems-template.md（verified_against SHA漂移钩子+timestamp=最后验证时非编辑时+stale重验门=Record溯源三件套16仓最完备,多版本语料直接可用;四态canon-draft-provisional-cut(cut=墓碑态第四态裁决题);map-card引用不复述≤50行强制;Knowledge按场表;外观状态三件套ChainOfCustody/伤情演进/服装;findings强制Cites列;Wardrobe勘误=无独立模板折叠进character+prop;MIT;连续性语义纯提示词弱于story-skills） | 幂等=报告快照型，重写走新版本
- U-A15 webnovel-writer | 状态=done | 判据=六节报告落盘（GPL红旗复核=GPL-3.0确认,只读不抄铁案维持） | 证据=全量构筑版-分析报告/webnovel-writer.md（域内工程完成度最高同类系统:三库分立;state_changes时序回放重建任意章快照=event sourcing小说版;UNIQUE约束族=约束式去重SQLite完整实现;urgency公式三层级3.0-2.0-1.0+进度比+前3条注入=开环管理最完整工程实现;检索chapter时间闸防剧透;PreToolUse保护+命令白名单;memory四态含contradicted;短板=字符预算/无时间归一/记忆未入库/云依赖=CBB差异清单） | 幂等=报告快照型，重写走新版本
- U-A16 worldbook-skill | 状态=done | 判据=六节报告落盘（许可勘误=索引清单"定制"精确化CC BY-NC-SA 4.0双证） | 证据=全量构筑版-分析报告/worldbook-skill.md（PT-013直系:禁词剔除八类表=16仓最接近R6机制(输出侧清洗:比喻转白描/万能修饰删/默认特征删"AI数据库已有");错误5提取AI已知信息=防先验污染16仓首见显式命名;不确定四规则=原文未提及占位+反推标注+首次出场为基准(vs claude-book后书优先两派并陈);行号索引+四类标记[W][C][I][★];编写前重读纪律;SubAgent禁词扫描门;错误9例三段式=Case最佳文档形态;中文语料原生成;零文本复制ShareAlike保守） | 幂等=报告快照型，重写走新版本
- U-A17 跨仓综合报告 | 判据=16详报汇总裁决→全量构筑版本体路线修订书(对照实验版重构/保留清单) | 证据=- | 幂等=同上

前置事实（2026-09-14 审核线核证）：实验版 cbb-skills/ 已冻结（FROZEN-实验版声明.md）；16 仓源码在 现成技能侦察/源码/；evals-skills+neo4j-skills 已装机（实验版 U0）。

阻塞登记：（无）
勘误日志：
- 2026-09-15 构建线对账发现：三谜"5.8万行js"归属错位——STATE U-A02/总纲§W 挂 author-toolkit，实测（索引清单§8/15+工作量预设§二+主线 find/wc）谜实体在 agent-skills (jwynia)（150 .ts/58,386 行，.js=0）。处置=谜底就地落 U-A01 报告§1；U-A02 将注明错位；Issue 001 落 分析报告/issues/ 待审核线改判基线文字。未发现其他对账差异（17 单位 todo 与磁盘无报告、git 无报告提交一致）。
