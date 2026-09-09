# Task-007 L8+L9 并入 library-bootstrap · 2026-09-04

> 原始轨迹层：只追加，只写不改。平时不加载，仅在复盘时引用。

## 任务
用户指令：「把新增的 L8，和 L9，写进之前的那个建库 skill 里」——L8 源树此前已就位，本次校验完整性并把它正式纳入发布链；L9 按规划书（workspace/L9内省仿生档计划书.md，BCA v0.1 指导思想）全新写入 skill。

## 过程
1. 盘点：源树 experimental-l8/ 完整（7 模块+scripts）、presets 已含 L8.md；发布链为「主包纯净 + addon 分包」两轨制。
2. experimental-l9/ 八模块全建：constitution-bca（BCA 四公理追加模板）/ instrumentation（.library-state.json + DASHBOARD + 快照脚本）/ emotion（STATE.md 4 维+stakes 红线）/ goalstack（GOALS.md）/ dual-memory（轨迹快照头规范）/ gwt（broadcast.txt 仲裁器）/ sleep-pipeline（sleep_gate.txt 三道闸门 + DISTILL.md）/ dmn（OPEN-QUESTIONS.md）。5 个可执行脚本全部纯标准库。
3. presets/L9.md + decision-tree L9 行 + SKILL.md 快速参考更新。
4. 测试扩 T13-T17（8+1 断言）：模块齐/install 含步骤/脚本编译/STATE 四维+红线/闸门行为（坏草稿拦、好草稿放）/预设链 L0-L9+CUSTOM。首跑 29/30：T13 把 scripts/ 目录误判为模块——修过滤器。终跑 **30/30 全过**。
5. 发布：library-bootstrap-l9-addon/（28 文件，README 含八步安装+三验收+逃生舱）；主发布包同步最新 SKILL/decision-tree/L8.md/L9.md（仅文档指针，模块代码保持主包外）。

## 过程事故
- T13 首跑把 experimental-l9/scripts/ 当模块（8+1 个目录）——测试过滤器漏排除公共目录；教训同 PT-005：测试自身 bug 首跑必现，当场修当场验。

## 本任务验证的模式
- PT-004 +1（第 6 次：档位体系 L0→L9 全链落地）
- PT-005 第 4 次实锤（T13 又是测试自身 bug）；R-001（主线：能力固化环节）再验证
- 反思计数 0→1（上次 reflect 后第 1 次 wrap-up）

## 追加 · 统合版发布（2026-09-04）
- 用户要求三包统合 → 产出 `library-bootstrap-超绝统合版/`（v2.0，123 文件）：以 skill 完整源树为底（与 30/30 测试同源），加统合 README（包内地图/三种用法/L8-L9 直装说明/版本关系）+ 根级「提示词速查.md」（头部改标统合版，注明 L8/L9 无需另装分包）。
- 包内自测：统合版目录内直接跑 run_tests.txt → 30/30 PASS（证明包自洽，非仅源树健康）。
- 发布链现为四轨：纯净主包 / l8-addon / l9-addon / 超绝统合版（全量）。
