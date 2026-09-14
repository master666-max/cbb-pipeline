# sillytavern-skills (davidgibbons) 详报 · U-A12

> 分析日期：2026-09-15 ｜ 构建线产出，判定权在审核线
> 源码位置：`现成技能侦察/源码/sillytavern-skills/`（clone --depth 1，可见提交 f1a45bf Merge PR #1）
> 方法：主线直读（35 文件小仓；CCv3 技能全 references 结构+关键四件精读）

## §1 架构与数据流

**仓库形态**：SillyTavern 工作流技能仓（davidgibbons），**仅 2 技能**：
- `character-card-v3-generator`（主件，SKILL.md 100 行+10 references+3 模板 JSON+validate_card.py 160 行+3 examples）：CCv3 角色卡与 lorebook 的生成/升级/校验；
- `sillytavern-extension-builder`（脚手架件，扩展模板 manifest/index.js/settings.html/style.css+4 references+scaffold_extension.sh）。

**数据流**（CCv3 技能七步工作流，SKILL.md:12-58）：澄清需求（模板档位默认 standard）→ 从模板建骨架（**转换/升级走 minimal-diff transform，"preserve existing intent/content unless it conflicts with CCv3 structure"**）→ 高信号角色内容 → lorebook 策略 → 卡级 regex 脚本（仅确定性文本变换）→ **validate_card.py 结构校验+人工抽查触发词+质量审查** → 交付（JSON 与解说分离输出，"rationale in a separate prose section"）。

## §2 数据模型与接口

**CCv3 spec 字段映射**（references/spec-v3-field-map.md，source of truth=kwaroran/character-card-spec-v3）：顶层 spec/spec_version/data 三必填；data 核心 15 字段+可选 character_book/assets/creation_date 等。**双控制面设计（本仓最高价值）**：
- **`system_prompt`=持久契约**（"foundational contract"：角色边界/不变约束/世界逻辑不变量——禁放临时场景状态与重复大段 lore）；
- **`post_history_instructions`=末轮转向**（"final-turn steering"：格式/节奏/已知失败模式护栏——多数前端中它在消息历史之后注入，**有效优先级更高**）；
- 授权规则："Put durable identity/world contract in system_prompt. Put response-time steering in post_history_instructions. Keep them complementary, not contradictory"；失败模式："用 post_history_instructions 暗中对抗 system_prompt 会造成不稳定行为"——**显式层级优先于暗中覆盖**。

**lorebook 模型**：entries[] 每条 keys[]/content/extensions/enabled/insertion_order/use_regex+可选 constant/selective/secondary_keys/position/priority；书级 scan_depth/token_budget/recursive_scanning；**@@ 装饰器**（@@depth N/@@position/@@activate_only_after N 等，"sparingly; prefer clear fields first"）。

**lorebook 激活策略**（references/lorebook-guidelines.md:5-40）：**一条一概念**；条目 20-100 词（长概念拆多条）；强 keys 贴近用户实际措辞，同义词只在"提升召回不引噪"时加；scan_depth 限远距误触发；insertion_order 保证确定性排序；**token_budget 防世界书膨胀挤占对话历史**；selective+secondary_keys 处理单 key 过宽；**"Separate semantics from presentation——lorebook 决定行为/状态，后处理决定渲染"**。

**validate_card.py**（160 行零依赖）：15 必填 data 字段存在性+类型校验（is_str_list 等）+lorebook entry 六字段逐条类型校验（keys string[]/content str/enabled bool/insertion_order number/use_regex bool）——**轻量结构校验器**（与 CBB stdlib 校验器同思想，规模更小）。

**审查体系**（references/reviewing-cards.md 八节+评分表）：Spec Compliance/**Prompt-Field Governance (Critical)**（双控制面不打架，"If post_history_instructions intentionally tightens rules, the override is explicit and justified"）/Character Consistency/Dialogue Quality/Lorebook Effectiveness/Token Efficiency/**Safety and Leakage Checks**（隐藏状态模式如 XML 注释的泄密风险+卡级 regex 检查）/Portability/Multi-Character。

**assets 条目**：type/uri/name/ext 四必填；多 icon 时恰一个 name:"main"——规范级细节。

## §3 可借鉴 / 不可借鉴清单

**可借鉴（设计层；许可未标注故零文本复制）**：
1. **双控制面分层**（持久契约 vs 末轮转向+显式层级禁暗中对抗）——CBB 提示词工程直接可用：cbb-* 技能的 SKILL.md（持久）与任务级指令（转向）应显式分层；也适用于迷深 X-RP 的角色卡提示词治理。
2. **lorebook 激活参数族**（scan_depth/insertion_order/token_budget/selective+secondary_keys）——CBB 若向 SillyTavern 生态导出世界书（X-RP 下游），这是**目标格式的完整字段语义**；token_budget 思想对 CBB 上下文注入预算也有参照价值。
3. **一条一概念+20-100 词拆条**——正典条目粒度设计的经验值。
4. **minimal-diff 转换原则**（升级保内容，仅结构冲突才改）——与我们"永不覆盖/新版本文件"纪律同构。
5. **reviewing 八节+评分表**——验收单结构参照（尤其 Safety and Leakage Checks 独立成节）。
6. **extensions 命名空间隔离**（"Treat these as frontend-specific...do not promote them to new top-level spec fields"）——CBB 契约的向前兼容纪律：非标数据进扩展字段不升顶层。
7. **JSON 与解说分离输出**——机器可读与人类可读分轨（R-020 同向）。

**不可借鉴**：
1. 无抽取/正典构建机制（纯生成侧工具）；三条件域外。
2. regex_scripts 卡级正则（SillyTavern 专有，误触发风险自担——其自身也警告"test on sample dialogue before shipping"）。
3. CCv3 spec 是外部规范（kwaroran 仓），本仓只是映射文档——溯源以 spec 仓为准。

## §4 许可与红旗

- **无 LICENSE 文件、无许可声明**（find -iname "LICENSE*" 零命中；README/SKILL.md grep license 零命中）——索引清单"未标注"判定属实：**默认保留全部作者权利，代码与文本零复制**，只读参考其设计。
- 维护：shallow 单 merge 提交（PR #1）；技能体量小、文档质量高（references 结构清晰、examples 三件）。
- 密钥/硬编码：validate_card.py 纯标准库；scaffold_extension.sh 本地脚手架——零风险。
- 红旗：无内容红旗；唯一约束=许可缺失（处置见 §6）。

## §5 与 CBB 对照（Step 0 三条件 + 四契约/三态）

**三条件对照**：生成侧工具，三条件**均不适用**；一个近亲：**Safety and Leakage Checks 的"隐藏状态泄密风险"**（hidden XML comments 的 leak-risk caveats）与 nb-memory"缺坐标判不可见"同族——**防信息泄漏**在 RP 场景的具体化（读者不该知道的设定不泄漏），对 CBB 的 RP 应用层（X-RP）有直接用途。

**四契约/三态对照**：
- **Record ≈ CCv3 卡+lorebook 条目**（spec 字段+extensions 命名空间）；
- **Issue ≈ reviewing 八节清单**（含 Pass criteria 逐节判定）；
- **Verdict ≈ validate_card.py+审查评分表**（结构校验=机器裁决，评分=人工裁决，两轨分离）；
- **Case ≈ examples/ 三件**（command-orchestration/format-comparison/secret-reveal 模式样例——尤其 secret-reveal-pattern.md 是"信息揭示"的用例文档，与 reveal_chapter 同题）；
- **三态：无系统三态**（enabled bool 是条目开关非裁决态）——不构成参照。

**金标方法学（§K2）**：无评测件；validate_card.py 是结构校验非语义评测——不适用。

**PT-013 对照**（知识库在案：角色卡/世界书批量语料校验流水线，2026-09-09 X-RP 实战）：本仓提供了**校验的规范侧基准**（CCv3 spec 字段+审查八节）——PT-013 的"对照原著全量核对"是内容侧，本仓是格式侧，互补；CBB 若做角色卡导出（正典→CCv3），字段映射可直接采用 spec-v3-field-map.md 的结构（引用 spec 仓为准）。

## §6 处置建议

**四选一：只读参考**——理由：
1. 许可未标注（保守=零复制零装机）；且为生成侧工具，与 CBB 抽取侧方向不同——不装外挂、不借鉴代码。
2. 参考价值集中在**双控制面分层与 lorebook 激活字段语义**（对 X-RP 下游导出）与**审查清单结构**——设计层吸收即可。
3. 若未来 CBB 需正式导出 CCv3（角色卡/世界书），建议届时引用上游 spec 仓（kwaroran/character-card-spec-v3，规范本体）而非本仓。

移交 U-A17 吸收项：①双控制面分层（持久契约 vs 末轮转向+禁暗中对抗）②lorebook 激活参数族语义（X-RP 下游导出参照）③一条一概念+20-100 词粒度 ④minimal-diff 转换原则 ⑤审查八节结构（Safety and Leakage 独立节）⑥extensions 命名空间隔离纪律 ⑦JSON/解说分离输出。
