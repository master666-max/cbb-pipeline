# m-core · 骨架与铁律（必选基座）

## 装什么
工作区根的目录骨架 + 铁律 README + 知识分类空表。这是唯一必选模块，其他一切叠加其上。

## 文件清单
| 模板源 | 目标 | 说明 |
|---|---|---|
| template/ROOT-README.md | ./README.md | 工作区说明+铁律（填 {{SLOT:WORKSPACE_NAME}}） |
| template/pitfalls.md | knowledge/pitfalls.md | 空表+条目格式模板 |
| template/patterns.md | knowledge/patterns.md | 空表+条目格式模板 |
| template/_trajectories.md | knowledge/trajectories/.keep | 轨迹层占位 |
| archive/_INDEX.md | archive/_INDEX.md | 工件索引空表 |
| archive/_cold/.keep | archive/_cold/.keep | 冷区占位 |
| workspace/.keep | workspace/.keep | 热区占位 |

## install.md 步骤（agent 照单执行）
1. 创建目录：knowledge/{skills,trajectories}、archive/{_cold,2026}、workspace。
2. 逐文件复制模板并填槽：{{SLOT:WORKSPACE_NAME}}、{{SLOT:DATE}}。
3. 已存在的文件跳过，记录到安装报告（铁律 1：永不覆盖）。
4. 校验点：`ls knowledge archive workspace` 结构齐；README 含「铁律」节。

## 溯源
源自实验性双库工作区《双库自进化体系·建库提示词.md》Phase 1；本工作区 task-001 实装验证；PT-004 已验证 3 次。
