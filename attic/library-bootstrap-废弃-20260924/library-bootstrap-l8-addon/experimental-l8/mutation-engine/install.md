# exp8-mutation-engine · 变异引擎（DGM 移植 · L8 旗舰）

## 装什么
mutations/ 工作流模板 + SKILL 变异提案规范。依赖 exp8-constitution。

## install.md 步骤
1. 复制 template/MUTATION-SOP.md → knowledge/skills/（变异标准作业程序，agent 照做）。
2. 建 mutations/LEDGER.md（表头：编号/日期/目标文件/动机一句话/基准分/裁决）。
3. 在 SLEEP.md 流程追加第 6 步：「依据遥测提出至多 1 个变异候选（MUTATION-SOP）」。
4. 校验点：LEDGER 存在且含表头；SOP 含三件套清单（MOTIVATION/BENCHMARK/DIFF）。

## 运行约束（写进 SOP，宪章执行）
- 证据先行：变异动机必须引用 usage.log/lint/trajectory 中的具体证据，凭空变异违法。
- 每周期一个候选；基准（run_tests.txt 13 断言 + lint）跑挂自动否决。
- 台账所有动作入 lifelog 哈希链；晋升必须人类令牌。

## 溯源
DGM 变体档案+实证验证+垫脚石归档；Self-Evolving Survey「进化工具/架构」列。
