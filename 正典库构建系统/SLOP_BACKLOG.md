# SLOP_BACKLOG.md — AI Slop 违规清单（阶段 1b 产出，唯一任务源）

> 基线 2026-09-27。扫描器：ruff 0.16.9（65 违规）+ 定向 grep 十类 + 手工核验。

| 编号 | 级别 | 类别 | 项 | 位置 | 状态 |
|---|---|---|---|---|---|
| S-001 | P0 | 吞异常 | runner.py:107 F821 sys 未定义（`__main__` 直跑崩） | cbb-v2/cbb2/runner.py | 待修 |
| S-002 | P0 | 假覆盖 | context.py F811 save_state 双定义（B5 修复引入时旧版未删） | cbb-v2/cbb2/context.py | 待修 |
| S-003 | P1 | 吞异常 | 9 处 BLE001 blind-except（context:22/gaps:34/fastscan:78/nli:76 等） | cbb-v2/cbb2/ | 待修（逐处窄化或注释豁免） |
| S-004 | P1 | 吞异常 | 4 处 S112 try-except-continue 无日志 | context/gaps（与 S-003 重叠） | 待修 |
| S-005 | P1 | 死代码 | 9 处 F401 未用 import（coldstore/fastscan/governance×2/lens/nli/gate 等） | cbb-v2/cbb2/ | 待修 |
| S-006 | P1 | 死代码 | F841 死变量 2 处（ledger:137 root/runner:48 chain） | ledger.py/runner.py | 待修 |
| S-007 | P1 | 魔数散落 | splitting.py 12000/1200 无常量名；coldstore 1000；runner 400/600 | 多文件 | 待修（提为模块常量） |
| S-008 | P2 | 命名/风格 | I001 未排序 import ×2；PIE808 冗余 range start；PERF102 迭代；PIE807 lambda | governance/audit/defenses | 待修 |
| S-009 | P2 | 隐式可选 | RUF013 implicit-optional ×4（函数签名 Optional 未显式） | 多文件 | 待修 |
| S-010 | P2 | subprocess | PLW1510 subprocess.run 无 check ×2（notary/图库隔离） | notary.py | 待修 |
| S-011 | P2 | 日期 | DTZ011 date.today() 无时区（quarantine._today 兼容面保留） | quarantine.py | 裁定保留（v1 兼容锚） |
| S-012 | P2 | utf-8 声明 | UP009 ×27（coding 声明冗余） | 全包 | 裁定保留（中文项目惯例，T-015 同源） |
| S-013 | P1 | 未接线 | er.py blocking_key/margin_decision 全仓零调用（Phase D 自审已登记） | er.py | 待接线（governance ER 批） |
| S-014 | P1 | 未接线 | promote build_panel/promotion_check 仅测试调用（G5 未投产） | promote.py | 待接线（G16 终审） |
| S-015 | P3 | 大文件 | 6 个 >300 行文件（store 391/环境自检 523/批次自检 404 等） | cbb/tools/ + cbb2 | 裁定保留（单文件内聚=管线工序边界，拆分破坏可读性；圈复杂度未超 15） |

## 基线计数
- ruff 违规总数：**65**（UP009 27 / BLE001 9 / F401 9 / RUF013 4 / S112 4 / F821 2 / PLW1510 2 / I001 2 / F841 2 / 其他 4）
- P0=2（S-001/S-002）；P1=7；P2=5（含 2 裁定保留）；P3=1 裁定保留
- grep 十类：吞异常 0（正面命中由 ruff BLE001 覆盖）/ 假断言 0 / 竞态 0（单写者纪律）/ 企业样板 0
