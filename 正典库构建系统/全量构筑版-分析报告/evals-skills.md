# evals-skills (hamelsmu) 详报 · U-A07

> 分析日期：2026-09-15 ｜ 构建线产出，判定权在审核线
> 源码位置：`现成技能侦察/源码/evals-skills/`（clone --depth 1，可见提交 22418da "Point deprecation notice at renamed repo"）
> 方法：主线直读（14 文件/1,266 行全量级；judge 两技能全文精读+其余五技能结构扫+meta-skill 全读）
> ⚠️ 重要状态：**上游已弃用本仓**（README.md:3-8：技能迁至 ai-evals-course/evals-skills，Shreya Shankar 与 Hamel Husain 共同维护，`npx skills add https://github.com/ai-evals-course/evals-skills`）

## §1 架构与数据流

**仓库形态**：Hamel Husain（AI Evals 课程作者，助 50+ 公司做评测的经验沉淀，README.md:12）的 LLM 评测方法学技能插件——**纯提示词（0 代码）**，7 技能 + meta-skill（技能写作指南）+ questions.md（免费学习资源索引）+ .claude-plugin 双 json。

**七技能职能流**（README.md Available Skills 表 + 各 SKILL.md）：
- **error-analysis**（164 行）——读 trace 建失败模式目录（评测项目的起点，"after significant pipeline changes...when production metrics drop"触发）；
- **write-judge-prompt**（144 行）——为单一失败模式设计 LLM-as-Judge；
- **validate-evaluator**（215 行）——对人工标注校准 judge（TPR/TNR+偏差修正）；
- **eval-audit**（183 行）——审计既有评测管道（诊断项：缺错误分析/**未验证的 judge**/虚荣指标），README.md:19-25 给出标准用法（每诊断区一个子代理并行调查后汇总）；
- generate-synthetic-data（131 行）——维度元组合成测试输入；evaluate-rag（177 行）——RAG 检索+生成双质量；build-review-interface（96 行）——人工标注界面。
- 典型链：error-analysis（找失败模式）→ write-judge-prompt（造 judge）→ validate-evaluator（校准）→ eval-audit（周期审计）。

**数据流**：trace 样本（真实>合成，100+ 真实 trace 时不许合成，generate-synthetic-data description）→ 人工二值标注（~50 Pass+~50 Fail，**领域专家优先于外包标注**，validate-evaluator Prerequisites）→ 三分割（train/dev/test）→ dev 迭代 → test 一次性终测 → Rogan-Gladen 修正到生产数据。

## §2 数据模型与接口

**write-judge-prompt 四要素模型**（skills/write-judge-prompt/SKILL.md 全文）：
1. **任务+单一判据**（"One failure mode per judge"，:15）；
2. **严格二值 Pass/Fail 定义**——**反 Likert 量表论证**（Anti-Patterns 节：标注者对 3/4 分边界无法达成一致，judge 继承该噪声；二值强迫先定义清晰决策边界，使标注者间一致性可测；需要严重度就拆多个二值 judge——"factually wrong"与"dangerously wrong"）；
3. **少样本**：必含 1 清晰 Pass+1 清晰 Fail+**1 borderline 边界例（"Borderline examples are the most valuable — they teach nuance"）**；只能从 train split 取（dev/test 进 few-shot=**数据泄漏**）；2-4 例典型，4-8 后收益平台；
4. **结构化输出且 critique 先于 verdict**（"Placing the critique first forces the judge to articulate its assessment before committing to a decision"）——JSON `{"critique": ..., "result": Pass|Fail}`。
配套：投喂最小集表格（tone 判定只需 persona+email，长文档只喂相关片段）；**穷尽代码检查再造 judge**（"many failure modes that seem subjective reduce to keyword checks...when you understand the domain"，Prerequisites 例：面试教练"general 问题"检测看似需语义理解，实际关键词查 usually/typical/normally 即可）。

**validate-evaluator 校准协议**（skills/validate-evaluator/SKILL.md 全文）：
- 三分割 train 10-20%/dev 40-45%/test 40-45%（分层抽样代码在文，:Step 1）；
- **TPR/TNR 双指标**（明确反对 precision/recall 与 raw accuracy——类别失衡下误导；Cohen's Kappa 只用于人与人标注者间，:Step 3）；
- 分诊表（:Step 4）：False Pass=judge 太宽→强化 Fail 定义；False Fail=太严→澄清 Pass 定义；
- 停止判据：目标 TPR>90% 且 TNR>90%（dev 迭代），最低可接受双 80%；双低→换更强模型；双平台→**判据分解为更原子检查**；
- **test 集只跑一次**（"Do not iterate after seeing test set results"，:Step 6）；
- **Rogan-Gladen 偏差修正**（:Step 7）：θ̂=(p_obs+TNR−1)/(TPR+TNR−1)，例算 TPR0.92/TNR0.88/观测 0.80→真实 0.85；TPR+TNR−1≈0 时失效（judge 不比随机好）；
- **Bootstrap 95% CI**（:Step 8，2000 次重采样代码在文；judgy 库替代）；
- 运行纪律：**锁模型版本**（dated snapshot id 而非浮动别名，防供应商静默漂移）；改提示词/换模型/CI 异常变宽→重新校准；~100 例下限（<60 则 CI 太宽）；**提高 TPR 比 TNR 更能收窄 CI**（修正公式分母效应）。

**meta-skill.md 技能写作七原则**（131 行，对 CBB 写 SKILL.md 直接可用）：Write directives not wisdom（给指令不给道理，附 Bad/Good 对照）/Cut general knowledge（删 agent 已知内容）/Scope to build task（每句都须帮 agent 干活）/Start with good defaults（先最简正确路径，进阶技术显式声明前置条件）/Be concrete（含 Pass/Fail 具体例）/警告转指令或反模式（反模式一行一条，需段落解释的=wisdom 应回转指令）/No quotes or citations。

## §3 可借鉴 / 不可借鉴清单

**可借鉴（MIT；设计+文本层皆可，按总纪律仍不逐字复制正文）**：
1. **Rogan-Gladen 修正+Bootstrap CI 全套**——CBB 未来用 judge 量抽取通过率时的必配；公式与代码 MIT，可直接实现（非抄文本而是实现公式）。
2. **critique 先于 verdict 的输出结构**——Verdict 契约可增 critique 字段且强制次序（先陈述证据再下结论）——与我们 LLM-judge 锚定纪律互证。
3. **二值裁决反 Likert 论证**——Step 0 事实级裁决（claim=true 方向对错）本质二值，此论证可写进 CBB 评测方法论文档作理论依据。
4. **三分割+test 只跑一次+数据泄漏禁令**——Step 0 金标流程的姊妹约束（我们已实践对抗轮与终审分离，但"few-shot 只能取自 train split"的显式禁令值得补进文档）。
5. **TPR/TNR 而非 precision/accuracy**——R-018（自动评测器先过对账）的指标层落地。
6. **"穷尽代码检查再造 judge"原则**——与 CBB"确定性校验器优先、LLM 判断后置"分工完全同构，其关键词化案例是好例证。
7. **judge 失败分诊表**（False Pass/False Fail→对应修法）——gate1 原因码设计的参照。
8. **锁模型版本+重校准触发器**——LM Studio judge（M-Prometheus-14B 本地无漂移）+未来云 API judge（会漂移）的差异化纪律。
9. **meta-skill 七原则**——CBB 六技能 SKILL.md 文本的质检清单。
10. **eval-audit 的"未验证 judge"审计项**——审核线验收单可加同款检查项。

**不可借鉴**：
1. 面向 LLM 产品 trace 评测域（客服邮件/SQL/RAG），无小说正典场景——技能正文不可直接复用，只吸收方法学。
2. 无中文场景验证（judge 提示词英文；我们 Step 0 已证中文抽取需自测）。
3. build-review-interface 建浏览器标注界面——CBB 人工裁决走 ZCode 会话+文书，无需独立 Web 标注件。

## §4 许可与红旗

- **MIT 正式 LICENSE**（LICENSE:1-3，Copyright (c) 2026 Hamel Husain）——无传染。
- **维护状态：上游弃用+迁移**（README.md:3-8 弃用公告置顶；git 22418da 即该公告提交）——内容仍为作者正版方法学，新家为双人维护的 ai-evals-course/evals-skills 插件。
- 密钥/硬编码：纯提示词无代码无 API——零风险。
- 红旗：无内容红旗；唯一注意项=装机件的上游生命周期（见 §6）。

## §5 与 CBB 对照（Step 0 三条件 + 四契约/三态）

**三条件对照**：评测方法学域，三条件（元文本/时间归一/去重）**均不适用**——本仓贡献在评测层而非抽取层。但间接咬合：①"未验证的 judge"审计项与 R-018 同构；②"穷尽代码检查再造 judge"=CBB 确定性优先分层；③generate-synthetic-data 的**维度元组**合成与迷深语料分层抽样同族，可用于 CBB 测试集扩充（R6 元文本防御的反例样本可合成）。

**四契约/三态对照**：
- **Verdict ≈ judge 输出**（critique+result 二元结构；裁决可校准可修正——CBB Verdict 若带 TPR/TNR 元数据则"这个裁决器多可信"机器可读）；
- **Record ≈ 人工标注集**（领域专家标注=金标来源，"应抽样本非穷尽"原则一致）；
- Issue/error-analysis：失败模式目录≈Issue 分类词表；
- 三态：judge 二值（Pass/Fail）+校准三带（>90%/80-90%/<80% 可信度）——**裁决可信度分带**是 CBB Verdict 可借鉴的第三维度（裁决+证据+可信度）。

**金标方法学（§K2）**：**本仓即金标方法学本身**——strict/adjusted 双口径（我们的）与 TPR/TNR+修正（它的）是同一方法学的两半：我们量"抽取对没对"，它量"裁决器本身可信吗"。两半合体=完整评测闭环。

## §6 处置建议

**四选一：装外挂（进运行时）·维持已装机并登记上游迁移**——理由：
1. 本仓是实验版 U0 已装机外挂（§K4 默认沿用）——**内容无降级证据**（方法学仍为业界正统、MIT、纯提示词无依赖），沿用判定成立。
2. 但上游已弃用迁移（README.md:3-8）：**【待确认：审核线裁定是否将装机源切换到 ai-evals-course/evals-skills 新家】**。保守处置=现装机件不动（内容自足、不依赖上游运行），迁移决策留审核线；若切换，走 PT-008 装机路径重装并 diff。
3. 已装机七技能与本报告 §3 的十条吸收项并存不悖：外挂管"用的时候照着做"，吸收项管"CBB 本体设计内化"（如 Verdict 增 critique 字段、评测文档补 Rogan-Gladen）。

移交 U-A17 吸收项：①Verdict 契约增 critique 字段+次序强制 ②裁决可信度分带（>90/80-90/<90）③Rogan-Gladen+Bootstrap CI 进评测工具箱 ④few-shot 数据泄漏禁令进 Step 0 文档 ⑤judge 失败分诊表进 gate1 原因码 ⑥锁模型版本纪律（云 judge 场景）⑦meta-skill 七原则作 SKILL.md 质检表 ⑧"未验证 judge"进审核线验收单 ⑨【待确认】装机源迁移新家。
