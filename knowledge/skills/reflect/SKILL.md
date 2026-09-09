---
name: reflect
description: 周期性反思合成，触发条件：每累计 5 次 wrap-up、用户说「反思」、或每月定时提醒命中且计数已满。读近期轨迹与新增条目，合成高层洞察写入 knowledge/reflections.md，并把需长期记住的结论回写 soul/USER.md。
---
# 反思合成（v3 · Generative Agents 式）

## 触发
- 每 5 次 wrap-up（计数由 wrap-up 第 6 步维护，见 knowledge/_index.md「反思计数」行）。
- 用户明说「反思」；或每月 lint 定时任务提示计数已满。

## 步骤
1. **取材**：读自上次反思以来的全部 trajectory 文件 + 本期新增/修订的 pitfalls/patterns 条目（recency 因子筛选）。
2. **合成**：提炼 2~3 条**高层洞察**——不是复述单条经验，而是跨任务的规律。例：「用户的项目集中在中文文本处理，环境坑集中在 Windows 编码与 hook 拦截」。
3. **落盘**：洞察追加写入 `knowledge/reflections.md`（编号 R-001 起，注明依据的条目/轨迹链接）；其中属于用户长期画像的部分回写 `soul/USER.md`。
4. **演化**：若洞察与某旧条目冲突，按 A-MEM 规则修订旧条目（版本号 +1），不删除。
5. **计数清零**：更新 knowledge/_index.md 的「反思计数」与「最后反思」日期。

## 纪律
- 洞察必须有据（列出依据条目），无据不写；与已有洞察重复则合并并升版本。
- reflections.md 只增不改条目号，修订用版本号表达。
