# cbb-guard · CBB 守门插件（v0.1.0）

> 形态裁定 2026-09-24：①**项目级**安装 ②hook"二拦二警"照准（拦①冻结线覆盖②红区 Write；决策账与副本漂移不进 hook）③命令中文名。
> 安装形态＝**本地市场直接引用版本源**（`../cbb-guard`，零拷贝＝零漂移，T-8 纪律）。

## 它拦什么

| 规则 | 触发 | 处置 |
|---|---|---|
| A 冻结线原位保全 | Write/Edit/Bash 覆盖或清理 `迷深实战-{本体库,工作区}` 与 `迷深实战-{工单,发车件,BUILD-STATE}.md` 的**已有文件** | **exit 2 拦截**（新建文件放行——additive 不算覆盖） |
| B 红区 Write | `cbb/contracts/*.schema.json`、两份在案工单、`决策账.jsonl` 的 **Write 整体覆盖**（Edit 追加放行） | **exit 2 拦截** |

**旁通（唯一合法通道）**：env `CBB_HOOK_BYPASS=<裁定引用>`——设了就放行，并自动追加"旁通"条目到 `正典库构建系统/决策账.jsonl`（无账引用的绕过＝硬拦）。

## 它不拦什么（裁定原文）

- 决策账先写后动 → **工具内断言**（自决策层 U-E02），不进 hook；
- 副本漂移 → **`/状态报告` 常设项**（＋可选每日自动任务），不进 hook。

## 三条命令

`/cbb-guard:批次自检` ／ `/cbb-guard:状态报告` ／ `/cbb-guard:覆盖复算` ——薄壳，只编排既有脚本与手工配方；脚本缺席时报明确错误。

## 安装（项目级 · 本地市场）

注册表已登记：`known_marketplaces.json`（cbb-local → `cbb-marketplace/`）＋ `installed_plugins.json`（cbb-guard@cbb-local，installPath=版本源本体）。**新会话生效**（当前会话的插件加载是启动时快照）。
卸载＝删两条注册表项＋删 `.bak` 前缀的备份恢复。

## 自检

```bash
printf '%s' '{"tool_name":"Write","tool_input":{"file_path":"D:/zcode专用！！！！危险！！！！！！！！！/正典库构建系统/迷深实战-本体库/ledger.jsonl"}}' | node hooks/guard.mjs   # → exit 2（拦）
printf '%s' '{"tool_name":"Write","tool_input":{"file_path":"D:/zcode专用！！！！危险！！！！！！！！！/新建件.md"}}' | node hooks/guard.mjs   # → exit 0（放）
```
七发验证（2026-09-24）：冻结覆盖拦✓／新建放✓／红区 Write 拦✓／冻结件 Edit 拦✓／旁通入账✓／Bash 清理拦✓／红区 Edit 放✓。

## 落点自陈

本插件的强制力＝**进程退出码**（L4：能拦）；但它拦不到 Bash 里的间接写（如 python 脚本写文件）——v1 只看 Write/Edit/MultiEdit 的 file_path 与 Bash 命令行正则。删掉本插件目录＝守门消失（这也是它自己的落点）。
