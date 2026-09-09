# X-Code · 代码工程项目库特色包

## 定位
长期维护的代码工程：bug 模式库 + ADR 架构决策记录。knowledge 只存「跨任务可复用」的工程知识，单项目代码本身进 archive。

## 装什么（叠加在 L≥2 上）
| 模板 | 目标 | 说明 |
|---|---|---|
| template/knowledge/bug模式库.md | knowledge/bug模式库.md | BUG-001 起：症状→根因→修法 |
| template/knowledge/ADR.md | knowledge/ADR.md | 架构决策记录（ADR-001 起，本库 decisions.md 的项目级版本） |

## install.md 步骤
1. 复制两模板。
2. wrap-up 复盘特化：本次 bug 是否新 BUG 条目（症状去重——同一根因不同症状要合并）？架构改动是否有 ADR？
3. 检索特化：报错原文关键词 → bug模式库 症状检索；改架构前先 grep ADR 防推翻已定结论。
4. 校验点：两文件齐；ADR 模板含「否决的备选」字段。

## 溯源
ADR 是业界标准实践；bug 模式库源自 pitfalls 的工程特化；本工作区 docx-pipeline 三脚本即「修法实例」形态。
