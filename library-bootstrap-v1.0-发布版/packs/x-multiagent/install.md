# X-MultiAgent · 多 Agent 协作库特色包

## 定位
多个 agent（或多个 harness 会话）共写一个工作区：共享语义层 + 各 agent 分区 + 写冲突契约。⚠ 装时弹风险提示：共享层有写冲突风险，必须装契约。

## 装什么（叠加在 L≥3 上——演化与 schema 是协作刚需）
| 模板 | 目标 | 说明 |
|---|---|---|
| template/CONTRACT.md | CONTRACT.md | 协作契约：分工/权限/冲突处理（根目录） |
| template/agents/{agent}/README.md | agents/{name}/README.md | 每 agent 分区说明（装时按实际 agent 名复制） |
| template/knowledge/协作教训库.md | knowledge/协作教训库.md | COLLAB-001 起：跨 agent 协作的坑 |

## install.md 步骤
1. 复制 CONTRACT.md 并与用户逐条确认分工/权限（这是本包唯一必须人工确认的步骤）。
2. 按当前 agent 清单建 agents/{name}/README.md（名字填实际值）。
3. 共享层（knowledge/、archive/）写入契约：条目由谁审、冲突时谁让（建议：后写让先写，先写条目升版本而非删除）。
4. 校验点：CONTRACT.md 存在且含「冲突处理」节；agents/ 至少一个分区。

## 溯源
G-Memory（多 Agent 记忆图）+ MemOS（记忆资源调度）的 Markdown 降维版；冲突处理规则源自 A-MEM 演化（升版本不删除）。
