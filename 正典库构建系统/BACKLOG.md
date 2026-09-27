# BACKLOG.md — 待结项清单（阶段 1a 产出，唯一任务源）

> 基线 2026-09-27；tag pre-slop-clean。扫描范围：cbb-v2/cbb2/ + cbb/tools/ + cbb-pipeline-skill/。

| 编号 | 优先级 | 项 | 位置 | 状态 |
|---|---|---|---|---|
| T-001 | P0 | runner.py `__main__` 块缺 `import sys`（F821×2，直跑即崩） | cbb-v2/cbb2/runner.py:107 | 待修 |
| T-002 | P0 | context.py save_state 重复定义（F811，前版被静默覆盖） | cbb-v2/cbb2/context.py:57+62 | 待修 |
| T-003 | P1 | ledger.py `_wrap_appends` 内 `root` 变量赋值未用（F841） | cbb-v2/cbb2/ledger.py:137 | 待修 |
| T-004 | P1 | runner.py finalize_chapter 内 `chain` 变量赋值未用（F841） | cbb-v2/cbb2/runner.py:48 | 待修 |
| T-005 | P1 | fastscan.py `import re` 未用 + scan_patterns 里 try-except-pass（S110+BLE001） | cbb-v2/cbb2/fastscan.py:10,78 | 待修 |
| T-006 | P1 | coldstore.py `import json` 未用（F401） | cbb-v2/cbb2/coldstore.py:10 | 待修 |
| T-007 | P1 | governance.py `import random`/`Counter` 未用 + lambda 默认值（F401×2+PIE807） | cbb-v2/cbb2/governance.py:10,11,88 | 待修 |
| T-008 | P1 | lens.py `import json` 函数内重复导入（F401） | cbb-v2/cbb2/lens.py:64 | 待修 |
| T-009 | P1 | nli.py `import urllib.request` 未用（F401） | cbb-v2/cbb2/nli.py:15 | 待修 |
| T-010 | P2 | gate.py `# noqa: F401` 指向已不需要的位置（RUF100） | cbb-v2/cbb2/gate.py:21 | 待修 |
| T-011 | P2 | audit.py range(0, d+1) 冗余 start（PIE808） | cbb-v2/cbb2/audit.py:60 | 待修 |
| T-012 | P2 | defenses.py 字典迭代应用 .keys()（PERF102） | cbb-v2/cbb2/defenses.py:49 | 待修 |
| T-013 | P2 | notary.py subprocess.run 无 check 参数（PLW1510×2 含图库隔离） | cbb-v2/cbb2/notary.py:63 | 待修 |
| T-014 | P2 | governance.py import 块未排序（I001） | cbb-v2/cbb2/governance.py:6 | 待修 |
| T-015 | P3 | 27 处 `# -*- coding: utf-8 -*-` 冗余声明（UP009，Py3 默认 utf-8） | 全包各文件 | 保留（中文注释惯例，防旧工具误判；降级裁定） |

## 状态说明
- P0=功能性缺陷（崩/静默覆盖）；P1=死代码/未用导入；P2=风格/性能；P3=裁定保留
- 编号任务唯一来源；完成后标 ✅ 并附 commit hash
