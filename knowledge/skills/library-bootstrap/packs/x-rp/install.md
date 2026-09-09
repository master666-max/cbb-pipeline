# X-RP · 角色扮演库特色包

## 定位
把双库机制用于角色扮演（RP/跑团/AI 人设对话）：soul 层换成角色人格卡，知识域换成世界观四库，archive 存跑团记录。机制层（闭环/演化/检索）与通用库完全一致——只换知识域。

## 装什么（叠加在 L≥2 上，推荐 L4+：人格卡即 soul 形态）
| 模板 | 目标 | 说明 |
|---|---|---|
| template/soul/CHARACTER.md | soul/CHARACTER.md | 角色人格卡（替代或并列 SOUL.md） |
| template/knowledge/世界设定.md | knowledge/世界设定.md | 世界观条目库（编号 W-001） |
| template/knowledge/角色卡库.md | knowledge/角色卡库.md | 出场角色卡（编号 C-001） |
| template/knowledge/剧情线.md | knowledge/剧情线.md | 时间轴+剧情线（编号 S-001） |
| template/knowledge/名场面.md | knowledge/名场面.md | 对话/事件存档（编号 M-001） |

## install.md 步骤
1. 建目录 knowledge/ 已有；复制五个模板，填 {{SLOT:WORKSPACE_NAME}} 等。
2. 若装了 m-soul：入口文件加载顺序改为 CHARACTER → USER → _index（纯 RP 库可不放 SOUL）。
3. wrap-up 复盘问题特化：本场哪些角色行为 OOC（Out of Character）？世界观有无自相矛盾？剧情伏笔哪些未回收？
4. 检索特化：search 关键词约定为「角色名/地点/组织/事件」；grep 角色卡库查出场。
5. 校验点：四库+人格卡齐；CHARACTER.md 含「OOC 边界」节。

## 溯源与范例
范例填槽素材来自本工作区 mepub 项目（《异世界迷宫最深部为目标》知识库：世界观/角色/剧情/咏唱分类实战，miza 2026-09-04 授权用作范例）。
