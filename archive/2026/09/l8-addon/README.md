# L8 超绝激进档（l8-addon · 完成于 2026-09-04）

> manifest 归档（D-001）：skill 源在 knowledge/skills/library-bootstrap/experimental-l8/ + presets/L8.md；发布包在根目录 library-bootstrap-l8-addon/；本库试装沙盒在 _l8_lab/。

## 一句话
library-bootstrap v1.1 的 L8 层：自指演化——库演化自己的机器（模板/工具/技能），DGM 三护栏（变体档案/实证基准/人类令牌）+ 哈希链信任锚 + 逃生舱，七模块 21/21 测试通过。

## 复现
- 测试：`py -X utf8 knowledge/skills/library-bootstrap/run_tests.txt` → 21/21 PASS（T8：破坏基准候选自动否决+live 树不变；T9 议会格式；T10 锦标赛零删除；T11 篡改 lifelog 精确报行号；T12 live 漂移报警）
- 安装：拷 library-bootstrap-l8-addon/ 到已装主包的工作区，按 README 顺序七步装（宪章确认强制）

## 数据流
workspace/L8超激进档计划书.md（webReader 3+1 信源）→ experimental-l8 七模块 → T8-T12 测试 → l8-addon 分包 + _l8_lab 沙盒试装（创世块 d59ce42e）

## 关键决策
- L8 主权边界（宪章第六条）：只改机器不改数据；变异频率 ≤1/周期；晋升必须人类令牌。
- 独立分包：主发布包保持纯净（L0-L7），L8 add-on 需显式安装——防小白一键咬到自己。
- twin 初始语料用 USER.md 互动史（用户裁决），首个预演记录状态【待验证】（本计划书流程即 dogfood）。

## 踩坑与经验
- T10 失败根因：测试断言与模板措辞没对齐（「30 天豁免」vs「30 天内豁免」）——测试即规格，措辞变更要同步断言。
- T12 失败根因：卫兵初版只对账 skill 前缀路径，沙盒场景下 manifest 文件不在该前缀——对账应面向「manifest 全部文件」，授权修改后重登记即可。

## 复用提示
- ★★★ 高（对已装主包的库）；☆ 风险自担（对库本身）

## 未竟事项
- 下月 1 号体检：变异引擎首轮提案（沙盒缺 usage.log，预计=补 L8 沙盒集成断言）；TWIN 首个预演验证；反思计数 4/5 满后首跑 reflect。
