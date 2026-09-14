# task-042 · P1-M1 下发准备与首发受阻（审核线 · 2026-09-14）

## 触发
用户令：环境就绪，检查闲时任务提示词，准备开工。

## 做了什么
1. **下发前环境实测全绿**：DEEPSEEK_API_KEY（35 位）/ NEO4J_PASSWORD（14 位）用户级变量 PowerShell 直读验证通过（注册表兜底通道可用）；neo4j-step0 容器 Up 6h；LM Studio 嵌入模型 text-embedding-qwen3-embedding-8b@q8_0 在位；依据双文件（CBB v1.0.md / P1建设计划书）在架。
2. **模板 v1.3**（下发前终检补刀）：③ 补 scoped-add 纪律——commit 只 add 本单交付物路径与 STATE，禁 `git add -A/.`（工作区有并行会话改动，扫荡式暂存=把别人半成品算进检查点）。此前 v1.2 补的：⑧ Windows 注册表兜底取凭证条款（老进程看不到 setx 新变量）；C 节 A+B 融合落位（U0 外挂装机件 + 14 仓只读不抄 GPL 防污染禁令）。
3. **凭证部署**：用户裁决临时 key 用完即删，setx 写入 DEEPSEEK_API_KEY；NEO4J_PASSWORD 直接从 neo4j-step0 容器配置提取写入（未回显未落盘）。
4. **首发受阻**：OffPeakCreate 返回 "Idle-time tasks are not enabled for this account right now"（账号未开通闲时任务，非提示词/环境问题；按规不重试）。
5. **下发单落盘**：`正典库构建系统/P1执行区/下发单-P1M1-闲时任务.md`——模板 v1.3 B 节槽位已按 P1-M1 填死（U0-U8 全判据+路线边界+注册表兜底），开通后一键重发或用户经自动化页手动贴（权限模式 yolo）。

## 判断与依据
- "老进程看不到 setx 新变量"是 Windows 环境常理，本会话实测证实（printenv 无、PowerShell 读注册表有）→ 模板⑧兜底条款有实测依据，非纸面设计。
- OffPeakCreate 失败信息按系统规则如实转述不重试；下发单落盘把阻塞转化为用户侧手动可执行步骤。

## 遗留
- 【待确认】用户账号闲时任务开通状态：自动化侧栏有无"闲时任务"tab / 套餐是否含此功能。开通后审核线可一键重发下发单。
- 备选路径（若长期不开通）：定时任务（Cron，消耗套餐额度，非免费）或恢复构建线会话交互式执行——用户裁决项，审核线不擅动。
- P1-M1 收官后提醒用户删除临时 DeepSeek key。

## 关联
task-041（模板与机制调研）/ R-014 / P-001 / P-009（reg query 旗标被 Git Bash 吃路径，MSYS_NO_PATHCONV 或 PowerShell 侧验证规避）/ D-004
