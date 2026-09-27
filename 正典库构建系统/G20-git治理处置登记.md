# G20 git 治理处置登记（2026-09-27）

## 分支全景（本仓 + 远端）

| 分支 | 位置 | 状态 | 处置 |
|---|---|---|---|
| `master` | 本仓（工作区仓） | 现役主线（4606445a） | 保持 |
| `exp/lightrag-fifth-path` | 本仓 | **已并入 master**（merge-base 核实 is-ancestor=yes，d79183ed 图链/增量同步/网络补充层三件为 master 所含） | 原样保留（铁律不删；价值内容已在主线） |
| `refactor/phase-a` | 远端 `master666-max/cbb-pipeline` | 上一会话经 REST 通道推送的工作镜像（远端头 a43c5f1d；f24388ec/5921a056 均在此分支——2026-09-27 审计勘误：此前总结中的 f24388e/30ada8d/5921a05 为**远端提交缩写**，本地 git log 无此号曾误判"不可采信"，实为两仓异构所致） | 保留；本地新工作待续推 |
| `refactor/reimagine` | 仅远端 cbb-pipeline | 本仓无此历史（孤儿历史在工作区仓不存在，无需 graft） | 登记：远端分支原样保留，本仓侧零处置 |
| `fix/audit-20260925` / `main` | 远端 cbb-pipeline | 技能包主线与外部审计修复线（另一工作线） | 不属本工单处置面 |

## 推送通道实况（P-025 勘误链）

- 本仓（工作区仓）**无 remote 配置**；与远端 `cbb-pipeline` 的同步走 **REST 通道**
  （gh api blob/tree/commit 选择性上传；git smart-http POST 被本地反代拦截，P-025）。
- 2026-09-27 审计曾误判"推送声称不可采信"——根因=拿本地 git log 验远端提交号。
  教训入 P-027 姊妹条：**跨仓对账先分清仓，再对号**。
- 待推清单（本地 master 领先远端镜像部分）：0a58df93（phaseF 全套）、27311158
  （调研矩阵）、a5f319e8（G16 首跑）、4606445a（fix-P028）及后续收束期批。
  推送动作=REST 通道续传，独立单元执行（非本登记范围）。

## 续推完成（2026-09-27 补记）

- 基线勘定：远端 refactor/phase-a tip 内容态=本地 `16b9faaa`（远端已含其独有件
  REVIEWS/regression-base.txt 实证；27311158→16b9faaa 历史序经 git log 域核实）。
- `tools/rest_push_phasea.py 16b9faaa refactor/phase-a` 原脚本续推：**27 件增量
  （本会话 4 提交 a5f319e8/bc439343/4606445a/8a6c52bf 全部文件）上传成功，远端新头
  `db65f82`**，回读确认在案。推送通道正式重建 ✓（后续续推=同脚本换基线参数）。
