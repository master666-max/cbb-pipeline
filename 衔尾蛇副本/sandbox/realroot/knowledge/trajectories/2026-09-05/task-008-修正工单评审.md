# Task-008 修正工单评审与源树修复 · 2026-09-05

> 原始轨迹层：只追加，只写不改。平时不加载，仅在复盘时引用。

## 任务
用户把另一独立工作区（D:\实验性记忆库工作区！！危险！！）实装 library-bootstrap v2.0 时发现的「三处偏差修正工单」+「v2.0.1 安装包」交给我：①审 v2.0.1 修得怎么样 ②检讨我为何写出这些 bug ③全量检查。

## 评审结论（v2.0.1）
- ✅ 偏差2 修得专业：PENDING/ABLATIONS 模板补齐且措辞如实（标注"只写不读、回读属机器变异候选"，完全合宪章）；还顺带抓到 m-core 的同类缺失（archive/_INDEX 只有目录没文件）补了真模板。
- ✅ 偏差3 修法正确：vector 空库守卫（exit 0 不崩）并回填包副本；行为冒烟验证通过。
- ⚠️ 偏差3 的 wrap-up 补装只改了现场库，包内模板/install.md 未同步（重装仍漏）；v2.0.1 无回归测试（run_tests 与 v2.0 相同）。
- ❌ 偏差1 包内未修：TWIN.md 模板仍带 miza 五问答全量画像（与 v2.0 零差异），只在安装现场清成骨架。

## 全量检查新发现（工单三处之外）
1. 引用完整性扫描：除工单已列的 PENDING/ABLATIONS/m-core，另有 6 处 install.md 复制源路径歧义（L8/L9 各模块写「scripts/xxx」但实际在兄弟目录 experimental-l8|l9/scripts/；x-multiagent 模板目录叫 agent-name 而 install.md 写 {agent}）。
2. 用户数据残留 grep：源树 8 文件含 miza/迷宫字样——TWIN 模板（真污染）为唯一需中性化的默认模板；CHARACTER 米莎范例带「可删」标注（用户授权示例）；其余为 install.md 溯源注释（可保留但注明来源工作区）。

## 源树修复（已回灌，发布包未动）
1. TWIN.md 中性化：清掉 miza 五问答与预演记录行，改为【待填充】+ 中性化声明（防未来装库者被装假用户模型）。
2. PENDING.md / ABLATIONS.md 模板补齐（内容取 v2.0.1 已验证版）。
3. m-core 补 archive/_INDEX.md、_cold/.keep、workspace/.keep 真模板，install.md 文件清单路径改 template/ 前缀。
4. broadcast.txt docstring 对齐 v2.0.1（如实标注 PENDING 只写不读）。
5. vector-search：exp_vector_search.txt 补空库守卫；install.md 把「wrap-up 重建行」从已知风险提升为显式补装步骤（第 4 步+入链+校验点）。
6. 六处 install.md 复制源路径歧义修正（scripts/ 写明包内全路径、agents 模板目录名写实）。
7. run_tests 扩 T18-T21d（8 断言）：TWIN 中性化/引用完整性（全包）/守卫与补装步骤/PENDING-ABLATIONS-broadcast-mcore 模板。首跑 37/38（T19 检查器自身基准 bug），修复检查器后 **38/38 全过**。

## 根因检讨（我为何写出这些 bug）
1. **TWIN 污染根因**：把「dogfood 示例」当「默认模板值」——没有"分发包模板默认值必须中性化"的纪律；铁律 2 只约束装库侧，没约束出包侧。miza 授权的 X-RP 迷宫范例（标注可删）被泛化成 TWIN 默认画像（未标注可删）。
2. **模板缺失根因**：install.md 步骤从计划书规格照抄，模板文件按脑内清单创建，两者从未做「引用完整性」对账；T13 只查 install.md 存在不查其引用存在。
3. **行为 bug 根因**：违反自己写的 PT-005——30 个断言里大部分是结构断言（文件在不在/格式对不对），真正执行脚本的只有 T11/T16 两个；broadcast/state/vector 全部只 py_compile 没跑过。空库边界（vector）与"注释写愿景、代码写现状"（broadcast docstring）全靠外部工作区实装才暴露。
4. **闭环缺失根因**：装库现场发现的 bug 没有「回流成回归测试」的通道——如果当时有把现场修复回灌 run_tests 的机制，v2.0.1 就不会在无回归测试下发布。

## 本次验证的模式
- PT-005 再实锤（第 5 次：T19 检查器又是自身 bug）；P-005 新条目（出包纪律）。
- 反思计数 1→2。

## 追加 · 说明书交付（2026-09-05，task-009 轻记录）
- 用户要求「严肃模式」的 L0-L9 内部机理说明书 Word 版，论文要贴。
- 走 PT-002 流水线：复用 ComfyUI generate.js 已验证模板（R1 封面配方 + 三节页码 + TOC），正文 13 章 + 附录 A（26 项论文资料题录，arXiv 编号全列）+ 附录 B（调研方法与可信度声明）。
- 过程磕绊 4 次：NODE_PATH 缺失、helper 作用域隔离（globalThis 注入）、pgSize/docHeader 截断缺失、heredoc 拼接笔误 require((——均为拼装类小错，逐一修复。教训同 PT-005：拼装产物必须跑，跑完才算数。
- 验收链全过：patch_footers（罗马 footer1/阿拉伯 footer2）→ add_toc_placeholders（58 标题）→ postcheck 0 错误 2 警告（均为模板既有模式）→ docx2pdf 27 页 → pymupdf 验收（空白页/溢出零问题；封面关键词检查为 ComfyUI 专用项不适用本档，如实注明）→ 封面/正文/表格三页渲染目检通过。
- 交付：根目录 library-bootstrap建库档位内部机理说明书.docx/.pdf；工作件在 workspace/_l9doc/。
