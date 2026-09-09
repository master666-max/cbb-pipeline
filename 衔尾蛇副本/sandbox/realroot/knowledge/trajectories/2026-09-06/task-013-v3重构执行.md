# 任务 013 · v3.0 重构执行（M1-M5 全绿，2026-09-06，只追加）

## 裁决与依据
- 用户拍板路线 B：bootstrap_v3.py 单文件统合直接上位为 library-bootstrap v3.0；v2.1.3/v2.1.4 文书波次终止，条目由架构吸收（对账表=PRD 第 4 节）。
- 唯一执行依据：workspace/v3-prd.md（PRD-driven；用户要求开 prd-driven-dev 技能——技能列表无此技能，已告知并按 PRD 精神人工落 PRD）。

## 执行记录
- **M1（BR 修复）**：工作副本 workspace/v3-dev/bootstrap_v3.py。BR-1 migrate 双目录双格式兼容（knowledge/lifelog/*.mdl + 截 16 hex 竖线行解析）；BR-2 A22/A28 编号修复；BR-3 resolve 实装 DFS 三色环检测+真环断言；BR-4 tempfile.mkdtemp；BR-5 A31=1994；BR-6 governance_budget 来源标注；BR-7 verify 标题规范化匹配+mismatch 附人工裁决建议；**BR-8（新发现）**：ESCAPE_POD/CHARTER 措辞自爆断言（「删除」二字）——回退措辞与事实性引文区分处理。
- **首跑抓 bug（PT-005 再实锤 ×3）**：①chain_append 目录语义错位（骨架原测试也必挂）；②migrate 续接行 prev=genesis——续接点链实际仍断，改为 chain_append 显式 prev_override（仅首次续接允许）；③t_escape_pod_wording 过宽。全回流为断言。
- **M2**：absorb 对 v2.x 源树一次跑通：131 内容体（modules=85/packages=27/presets=11/docs=8），MODULE_MAPPING 18 键路径全校验，level_mapping.json 落盘；verify 对 arXiv API 14/14 零不一致（规范化匹配）。
- **M3**：TESTS 9→15 条全绿（PRD 目标 16，t_l8_guards 合并守卫语义，等效覆盖；t_l8_guards 实证 v2.x SOP 缺「不可见条款」→守卫由宪章承担，SOP 升级记 v3.1 内容体项）。
- **M4**：L2/L8 慢车道门（无 --yes 拦截/含宪章展示）、engine 全生命周期（append 证据锚拦截/密钥拦截/retrieve 投毒防线/shadow 不改状态/wrapup 0.7 衰减+64 位 Merkle 根）、migrate 对仿真 v2.x .mdl 链续接成功——全部行为断言实测。
- **M5 发布**：根目录 `library-bootstrap-v3.0/`（bootstrap_v3.py + bootstrap_data/ + 渲染件 spec.md/提示词速查.md + RELEASE.md）。包锚点 sha256=813fcd55eb8bed70…；发布门在发布目录原地复跑：run-tests 15/15 + verify 14/14。
- **legacy 标注**：13 个 v2.x 包根全部新建 DEPRECATED-见-v3.md（不覆盖任何文件）；REVISION-LEDGER 追加关闭记录。

## 待办（v3.1 候选）
- v2.x SOP「不可见条款」注入（内容体升级）；真实存量库 migrate（等用户指令，会写 audit/）；reflect 阈值主轨（importance 累加）实装；referee 提示词随内容体分发。

## 经验
- PT-005 三连实锤：骨架文件的测试自己就是坏的（目录语义、自爆断言、恒真环断言）——「别人的代码也要当场跑」。
