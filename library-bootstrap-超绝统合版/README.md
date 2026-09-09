# library-bootstrap · 超绝统合版（v2.0 · 123 文件）

> L0-L9 十档全链 + 10 功能模块 + 6 特色包 + L7 实验三件 + L8 自指演化七件 + L9 仿生八件 —— **一个包全装齐**。
> 任何 agent harness（ZCode / Claude Code / Cursor / Codex CLI / Trae…）：把本目录拷进工作区，按下方提示词发话即可。

## 包内地图

| 目录/文件 | 内容 |
|---|---|
| SKILL.md | 主入口：解析指令 → 选型 → 探测 → 安装 → 校验（L0-L9 路由全在） |
| 提示词速查.md | **所有建库分类 × 所需提示词**（L0-L9 十档 / 6 特色包 / 自由组合 / 运维 / 逃生舱） |
| presets/ | L0.md ~ L9.md + CUSTOM.md（十档定义，嵌套递进） |
| modules/ | m-core ~ m-radar 十模块（模板 + install.md） |
| packs/ | x-rp 角色扮演 / x-writer / x-corpus / x-code / x-research / x-multiagent |
| experimental/ | L7 实验：vector-search / auto-critic / dream-fusion |
| experimental-l8/ | L8 自指演化：constitution/lifelog/mutation-engine/tournament/council/twin/worldsim + 卫兵脚本 |
| experimental-l9/ | L9 BCA 仿生：constitution-bca/instrumentation/emotion/goalstack/dual-memory/gwt/sleep-pipeline/dmn + 5 脚本 |
| adapters/ | harness 环境探测 + AGENTS/CLAUDE/.cursorrules 三入口模板 |
| scripts/ + run_tests.txt | bootstrap_verify 校验器 + 自测套件（30/30） |

## 三种用法（自由度从低到高）

**① 一键默认**：`按 library-bootstrap 建库` → 交互向导 / 默认 L2。

**② 指定档位（推荐）**：
```
按 library-bootstrap 建 L4 灵魂库            ← 稳定实用
按 library-bootstrap 建 L6 全家桶 + 写作库    ← 前沿全家桶叠特色包
按 library-bootstrap 建 L7 实验库，全上      ← 尝鲜
```
**③ 激进三连（L8/L9 需逐级确认）**：
```
按 L8 档加装：先展示 L8-CONSTITUTION 宪章全文，确认后装全部七模块
按 L9 档加装：先展示 BCA 公理与验收三件（消融/干预/谄媚），确认后按序装八模块
```
> L8/L9 的逃生舱不因统合而取消：删 experimental-l8|9/ 对应目录即回退，主库无损。

## 自检

```
py -X utf8 run_tests.txt     → 30 PASS / 0 FAIL（T1-T17：安装/幂等/卫兵/闸门全链）
```

## 版本关系

| 包 | 内容 |
|---|---|
| library-bootstrap-v1.0-发布版 | L0-L7 纯净主包（保守用户用这个） |
| library-bootstrap-l8-addon / l9-addon | 单独加装 L8 / L9（增量用户用这个） |
| **本统合版** | 三合一全量（省事用户用这个） |

*配套：提示词速查.md 第八节「add-on 安装」在统合版中等价于「L8/L9 档位直装」。*
