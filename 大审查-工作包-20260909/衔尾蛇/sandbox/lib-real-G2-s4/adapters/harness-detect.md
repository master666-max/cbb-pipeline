# harness-detect · 环境探测流程（安装第一步）

> 在任何安装动作之前跑。产出写入目标工作区 env/ENVIRONMENT.md，后续所有脚本形态与入口选择以它为准。

## 步骤

### 1. 解释器探测
```
依次尝试（agent 用 Bash/终端工具跑）：
  python3 --version   → 可用 → runner=python3
  py --version        → 可用 → runner=py（Windows 常见）
  都不可用            → E-manual（纯清单安装）
```
UTF-8 强制：非 UTF-8 默认的环境（Windows）给 runner 追加 `-X utf8`。

### 2. .py 拦截探测（E-full vs E-fallback）
```
写一个最小探针文件 probe_test.py（print('ok')）→ 用 runner 执行：
  成功 → E-full（脚本用 .py）
  被拦/失败 → 改名 probe_test.txt 再用 runner 执行：
    成功 → E-fallback（脚本一律用 .txt 形态）
  探针文件测完删除
```

### 3. cron 能力探测
- harness 有 Cron 类工具（如 ZCode CronCreate / 系统 crontab 可用）→ CRON_MODE=auto
- 都没有 → CRON_MODE=manual

### 4. 入口文件选择
| harness | 入口 |
|---|---|
| ZCode / 通用 | AGENTS.md |
| Claude Code | AGENTS.md（新版）或 CLAUDE.md（老版）——问用户或两者都建 |
| Cursor | .cursorrules（或 .cursor/rules/） |
| 其他/未知 | AGENTS.md（通用约定，多数 harness 都认） |

### 5. 落盘 env/ENVIRONMENT.md
```
# 环境档案（{DATE} 探测）
- env_tier: E-full / E-fallback / E-manual
- py_runner: {runner}
- cron_mode: auto / manual
- entry_file: {入口}
- harness: {harness 名【待确认】}
```
