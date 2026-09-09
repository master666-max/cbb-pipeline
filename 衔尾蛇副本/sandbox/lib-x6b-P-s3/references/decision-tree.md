# library-bootstrap 选型决策树（agent 路由手册）

> agent 读本文件决定装什么；用户一句话指令 → 解析 → 走 install 流程。
> 规则：先解析预设档位/特色包 → 展开嵌套模块 → 校验依赖 → 环境探测 → 逐模块安装 → manifest 校验。

## 一、指令解析

| 用户说 | 解析为 |
|---|---|
| 「建库」/「建一个库」（无修饰） | 交互式向导（harness 支持）或默认 L2 |
| 「建 L{n} 库」/「{档位名}」 | 对应预设（见 presets/L*.md） |
| 「建 {特色} 库」（角色扮演/写作/…） | L2 + 对应 X 包（特色包基座默认 L2） |
| 「建 L{n}+{特色} 库」 | 显式组合 |
| 「只要 {模块名} 不要 {模块名}」 | 自由组合模式，进依赖校验 |
| 「升级库」/「加装 {模块}」 | 读 .library-manifest.json → 增量安装 |

## 二、模块依赖表（安装顺序即列顺序，安装器按此拓扑排序）

| 顺序 | 模块 | 依赖 | 提供物 |
|---|---|---|---|
| 1 | m-core | —（必选基座） | 目录骨架 + 铁律 README + knowledge/pitfalls/patterns 空表 |
| 2 | m-index | m-core | 双索引 + 会话入口条款 |
| 3 | m-loop | m-index | task-start / wrap-up 技能 |
| 4 | m-tools | m-core | lint + search 脚本 |
| 5 | m-schema3 | m-core | 条目字段升级（模板+示例） |
| 6 | m-evolve | m-loop + m-schema3 | wrap-up v3 六步 + [[]] 双链规范 |
| 7 | m-soul | m-core | soul/SOUL+USER + 三级加载 |
| 8 | m-reflect | m-loop | reflect 技能 + reflections.md |
| 9 | m-cron | m-tools + m-reflect | 定时体检指引（能力探测三档） |
| 10 | m-radar | m-core | SOTA 雷达精简版（references/） |

- m-soul 与 m-loop 相互独立可任选；m-evolve 是唯一强依赖链（schema3+loop）。
- 特色包（X-*）依赖：m-core（最低）；推荐基座 L2（含 tools 可自检）；X-RP 额外推荐 m-soul（人格卡就是 soul 形态）。

## 三、档位 → 模块展开

| 档 | 模块集合（展开后） |
|---|---|
| L0 | m-core |
| L1 | m-core, m-index, m-loop |
| L2 | + m-tools |
| L3 | + m-schema3, m-evolve |
| L4 | + m-soul |
| L5 | + m-reflect, m-cron |
| L6 | + m-radar |
| L7 | L6 + 实验模块（experimental/，装时风险确认） |
| L8 | L7 + experimental-l8 七件套（**独立 add-on 分包**，装前强制宪章确认；宪章 L8-CONSTITUTION 至上） |
| L9 | L8 + experimental-l9 八件套（**独立 add-on 分包**，装前强制 BCA 公理确认；指导思想=BCA v0.1，验收=消融/干预/谄媚三件） |

## 四、环境探测三档（adapters/harness-detect.md 流程）

| 档 | 判定 | 影响 |
|---|---|---|
| E-full | python3 或 py 可用，且 .py 可执行 | scripts 用 .py |
| E-fallback | 解释器可用但 .py 被拦 | scripts 用 .txt 形态（内容同） |
| E-manual | 无 Python | 纯清单式安装，脚本只留文档说明 |

cron 能力另测：有（ZCode CronCreate 类）→ m-cron 自动配；无 → m-cron 只写手动模式说明。

## 五、风险提示点（安装时必须明示）

- L7：实验模块未经长期验证，可能随上游论文迭代失效；仅建议尝鲜/隔离目录使用。
- X-MultiAgent：共享语义层有写冲突风险，需契约文件约束（包内自带）。
- 自由组合：绕过嵌套时依赖校验失败必须拒绝安装并打印缺项。

## 六、槽位总表（agent 填槽，禁止改结构）

| 槽 | 出现于 | 填什么 |
|---|---|---|
| {{SLOT:WORKSPACE_NAME}} | 各 README/入口 | 工作区名或用途一句话 |
| {{SLOT:HARNESS_NAME}} | 入口文件、env | harness 名（ZCode/Claude Code/…） |
| {{SLOT:ENTRY_FILE}} | 安装清单 | AGENTS.md / CLAUDE.md / .cursorrules（探测+询问） |
| {{SLOT:DATE}} | manifest、各文件头 | 安装日期 YYYY-MM-DD |
| {{SLOT:OWNER_NAME}} | m-soul/USER、X-RP 人格卡 | 用户自称（如 miza） |
| {{SLOT:PY_RUNNER}} | 工具文档 | python3 / py / py+txt（探测结果） |
| {{SLOT:CRON_MODE}} | m-cron | auto / manual |
