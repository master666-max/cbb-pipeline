# Task-005 library-bootstrap 通用建库 Skill · 2026-09-04

> 原始轨迹层：只追加，只写不改。平时不加载，仅在复盘时引用。

## 任务
用户裁决后执行任务书（workspace/library-bootstrap通用建库skill任务书.md）：做一个可迁移到任何 agent harness 的一键建库 skill。裁决：①打包版要做 ②特色包 6 个全保留 ③L7 必做且要更激进 ④参数式+交互式都要 ⑤X-RP 用迷宫最深部做范例（用户自称 miza）。

## 过程（Ph1-Ph7）
1. Ph1 设计冻结：references/decision-tree.md（指令解析表+依赖表+环境三档+槽位总表）、references/manifest-spec.md。
2. Ph2 十模块模板：m-core/index/loop/tools/schema3/evolve/soul/reflect/cron/radar，每模块 install.md + template/。
3. Ph3 六特色包：x-rp（CHARACTER 人格卡+世界设定/角色卡/剧情线/名场面四库，迷宫范例）、x-writer（文风画像+伏笔账本）、x-corpus（三层数据流）、x-code（bug 模式库+ADR）、x-research（演化综述+信源分级）、x-multiagent（CONTRACT 契约+分区）。
4. Ph4 适配器：harness-detect.md（解释器→.py 拦截→cron→入口四步探测）、三套入口模板（AGENTS/CLAUDE/.cursorrules）、scripts/bootstrap_verify.txt（--init/--deps/校验三模式，sha1_8 哈希）。
5. Ph5 预设：L0-L7 八档 + CUSTOM；L7 实验三件套 vector-search/auto-critic/**dream-fusion**（梦境融合：随机抽 3 条不相关条目强行联想——「更激进」的回应）；SKILL.md 主入口（frontmatter+主流程 7 步+纪律）。
6. Ph6 测试：run_tests.txt 模拟安装器（沙盒装 L1/L6/L4+RP + 幂等 + 依赖拒绝 + 双入口同构 + 清单完备）。首跑 12/13，T1 失败是**测试自身 bug**（L1 无 m-tools 却断言跑 lint），修后 **13/13 全过**。
7. Ph7 发布：library-bootstrap-v1.0-发布版/（78 文件，含 README）。

## 过程事故
- sed 批量生成 RP 模板翻车（模板串含斜杠未转义，角色卡库.md 成 1 行残片）→ 改 Write 逐个重写。教训：**含特殊字符的批量文本生成别用 sed，直接 Write**。
- Write 工具拒绝覆盖 sed 产出的未读文件 → 先 Read 再重写，流程正确。

## 本任务验证的模式
- PT-004 +1（第 4 次：skill 化本身是建库路径的再验证）→ 已达 4 次，继续列建议。
- PT-002 docx 流水线未用（本任务纯 Markdown+py）。
