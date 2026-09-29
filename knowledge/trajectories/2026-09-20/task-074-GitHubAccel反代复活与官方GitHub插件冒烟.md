# task-074 / 2026-09-20 / GitHubAccel 反代复活 + 官方 GitHub 插件冒烟

## 一句话
用户要试 ZCode 新装的官方 github 插件（v0.1.2），`gh auth refresh` 因本地反代死亡而失败；顺藤摸瓜复活 D:\GitHubAccel 反代、完成认证，插件读（repo view）写（secret gist）双测通过；复盘立 P-025。

## 复现
1. `gh auth status` 报 keyring token invalid → 后台跑 `gh auth refresh -h github.com` → `dial tcp 127.0.0.1:443 connectex 拒绝`。
2. 排障链：hosts 见 `gh-proxy BEGIN` 段（github 系域名全钉 127.0.0.1）→ netstat 无 443 监听 → gh-proxy.pid=67656 已死（gh-proxy.log 停在 09-19 07:57，机器重启、计划任务未注册未自启）。
3. 复活：`run-proxy.cmd`（pythonw 路径）静默拉不起；改 python.exe 直跑 `gh-proxy.py --port 443` 成功（PID 54776，挂在本会话后台任务上，会话结束即停）。
4. curl(schannel) 报 CRYPT_E_NO_REVOCATION_CHECK → `--ssl-no-revoke` 绕过 → github.com 200 / api.github.com zen 正常。
5. 设备码流程：用户浏览器授权 68A5-95F5 → `gh auth status` + `gh api user` 复验 master666-max（scope: gist/read:org/repo/workflow）。
6. 插件冒烟：`/github:repo` 语义下 `gh repo view cli/cli`（46.3k★，v2.101.0）读通；`/github:gist` 按规范走临时文件创建 secret gist（首次 502 上游抖动，重试成功）并读回验证。

## 关键决策
- 不重装/不重配 GitHubAccel，只拉起既有实例（工单 WO-SEC-GHACCEL-001 在案， hosts.backup-original.txt 与 certs/ 不动）。
- 秘密 gist 而非公开（免公开披露确认门）；内容即测试记录。
- 知识沉淀走 P-025 单条（排障流水线并入对策，不另立 PT 条目，避免同族拆两半）。

## 踩坑与经验
- **P-025 立条**：hosts 钉 127.0.0.1 的本地反代死后，故障伪装成 token 失效/断网——排障先传输层（hosts→监听→pid）后应用层。
- run-proxy.cmd 的 pythonw 静默失败（cmd 秒退 exit 0、日志零字节）【待确认】，python.exe 直跑无碍。
- gh v2.100.0 的 `gist view` 无 `--json` flag，用 `--files`/`--raw`。
- Git Bash 自带 curl 编译为 schannel 后端，对无吊销源的自签证书默认拒绝。

## 复用提示
- 以后任何「GitHub 连不上」类问题，第一步先 `grep -i github hosts` + `netstat -ano | grep 443`，别急着重登 token。
- 治本待办：管理员跑一次 `D:\GitHubAccel\开机自启.bat`（需用户操作）。
- 遗留物：secret gist b4d71dc8（可删）；后台 python.exe 实例随会话存活。
