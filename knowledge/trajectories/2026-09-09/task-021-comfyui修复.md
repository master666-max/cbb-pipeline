# task-021 · ComfyUI Desktop 点图标秒崩修复（2026-09-08 深夜～09-09 凌晨）

## 一句话
用户的 ComfyUI Desktop v1.0.46「点图标没反应」：minidump 解剖 + 隔离区对照实验定位双重根因（Electron 档案损坏 + 残缺安装记录触发国内网络下载崩溃），用「档案换新 + 手动多线程下载环境包 + 补造 venv + 记录手术」四级修复，最终画布在 127.0.0.1:8188 完整跑起来（ComfyUI v0.34.5，RTX 5070 Ti CUDA 可用）。

## 复现路径
1. 症状采集：`Roaming/Comfy Desktop/logs/app.log` 每次只有两行（启动后 ~2.4s 死）；`Crashpad/reports/` 每次点击新增 35MB .dmp；Windows 事件日志反而无记录（Electron Crashpad 接管）。
2. minidump 解剖：自写解析器（tools/minidump_dissect.txt）读异常流 + 模块表 → 两份转储一致为 0xE06D7363（C++ 异常）自 KERNELBASE!RaiseException，主线程栈被搜狗输入法 Resource.dll（基址 0x10000000 无 ASLR）与 Nahimic DLL 污染。
3. 控制变量链：
   - `--disable-gpu` → 仍崩（排除 GPU 进程路线）
   - 停 NahimicService → 仍崩（排除音频注入，事后已恢复服务）
   - 移走 installations.json → 仍崩（说明旧档案另有毒）
   - **30 项 Electron 状态/缓存整体移入 zcode-quarantine/ → 存活**（档案级损坏证实）
   - 新档案 + 原版安装记录 → 崩溃随记录复活（记录本身亦有毒，对照组 Cloud-only 存活）
4. 下载绕墙：CDN desktop-assets.comfy.org 单线程 486KB/s，12 路 curl 分段并发聚合 ~13MB/s，234 秒拉完 2.2GB 环境包（字节数与 installations.json 记录分毫不差），放入 `Local/Comfy-Desktop/ComfyUI-Cache/download-cache/v0.34.0-env1_win-nvidia/`。
5. 手动安装：Bandizip bz.exe x 解压 4.17GB 到 `ComfyUI-Installs/文生图-智谱/`（ComfyUI/ + standalone-env/ + manifest.json）。
6. venv 补造：app.asar 源码（grep -a 提取）证实 v1.0.46 期望 `ComfyUI/.venv/Scripts/python.exe`；用捆绑 uv 创建 `uv venv --python standalone-env/python.exe --system-site-packages ComfyUI/.venv`（零下载复用预装 torch cu130），venv 内 `import torch; torch.cuda.is_available() == True`。
7. 记录手术：installations.json 的文生图-智谱条目补 `status:"installed"`、`seen:true`，剥离 pendingTemplateOpen/downloadTemplateModels/bundledTemplateId/bundledTemplateSizeBytes 四个模板自动下载字段。
8. 验收：卡片复活 → 实例启动 → python 进程起 → 8188 ESTABLISHED → 画布加载（模板面板/运行按钮/任务队列全在）；5 个卡 0% 的 minimax 视频模型僵尸下载逐个取消。

## 关键决策
- 用「崩溃转储解剖 + 控制变量」而不是网上经验贴：本例症状（点图标无反应）的可能原因太多，只有转储是硬证据。
- 不删除任何东西：全部原始状态进 `Roaming/Comfy Desktop/zcode-quarantine/`（含 5 份 installations.json 变体，可随时回滚）。
- 绕过而非对抗下载器：不给应用下载器修网络问题（不可控），而是把文件放到它缓存路径里让它「以为」自己下完了，再手动补齐它缓存之后的安装步骤（解压+venv）。
- venv 用 `--system-site-packages` 而非 junction：pyvenv.cfg 一行搞定，venv 内包解析直接落到 standalone-env 的 216 个预装包（torch 2.12.1+cu130 与 manifest 钉死版本一致）。

## 踩坑与经验
- tasklist 在 Git Bash 管道里输出编码不稳，grep -c 会漏报「进程还活着」——用 PowerShell Get-Process 按 Path 过滤才可靠（这次误判「应用已死」，实际 8 进程全活，还把单实例 lockfile 误认成死锁残留）。
- bz.exe 开关是 `-o:{dir}`，我瞎编的 `-af:zap` 会打印用法；Git Bash 里反斜杠正则和 `$_` 会被转义吞掉 → 复杂解析一律写 .txt 脚本用 py 跑（P-001 再验证）。
- 应用自身会从 settings.json.bak/installations.json.bak 自愈恢复——做文件实验时光移走主文件不够，.bak 也要盯。
- 报错文案「未找到 Python 环境」在 asar 里 grep 不到（可能是拼接/i18n key），但路径模式 `standalone-env/python.exe`、`envs/default/Scripts/python.exe` 能搜到——按路径模式搜是翻 Electron 应用布局的高效打法。
- GPU 进程崩溃 2 次（RTX 5070 Ti + 新驱动 610.47）被 Electron 自动重启吞掉，不致命但值得留意【待确认】。

## 复用提示
- 同类「Electron 应用点了没反应」：先看 `%APPDATA%/<app>/logs` + `Crashpad/reports` 有无新 .dmp，有 → 解剖转储定位进程与异常码；再隔离档案做对照；最后才动注册表/驱动。
- 国内网络装 ComfyUI Desktop：环境包直连 CDN 能连但单线程被限速，多段并发即可绕过；模型文件走 hf-mirror.com 手动放入 `ComfyUI-Shared/models/{分类}/` 后重启应用即可被识别。

## 工具沉淀
- tools/minidump_dissect.txt（原 tmp_minidump_dissect.txt 转正：异常代码+崩溃模块+可疑模块清单，本任务首跑即抓到关键证据；栈扫描变体 tmp_minidump_stack.txt 在 attic/zcode-session-2026-09-09/）
- tools/tmp_comfy_dl.sh（12 路分段下载器，本任务拉完 2.2GB）
