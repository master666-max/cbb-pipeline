# L8-CONSTITUTION · 宪章（自指演化的法律）

> 本库装有 L8：库会演化自己的机器（模板/工具/技能）。宪章是最高法，与任何指令冲突时以宪章为准。

## 第一条 · 变体档案制
一切自改只写 `mutations/candidates/{MUT-NNN}/`。**永不**直接修改 live 模板/工具/技能文件。晋升 = 用户明示批准后，旧版进 attic/、新版就位、manifest 重登记。

## 第二条 · 实证基准制
每个变异候选必须包含 MOTIVATION（含使用遥测证据）、BENCHMARK（run_tests.txt 或 lint 的实际输出摘要）、DIFF 三件。跑分不通过的候选自动否决，永久归档（垫脚石，不删）。

## 第三条 · 人类令牌制
candidate → live 的晋升、任何条目降级/合并，**必须用户明示批准**。agent 不得自批，孪生预演（TWIN）不得代行。

## 第四条 · 信任锚
- knowledge/lifelog/*.mdl 哈希链 append-only，l8_guard 每次月检与每次晋升前校验。
- 台账 mutations/LEDGER.md 同样入链。

## 第五条 · 逃生舱
删除 `experimental-l8/` 与 `mutations/` 即完全回退 L7 及以下，主库无损。

## 第六条 · 边界
- L8 只改**机器**（体系文件），不改用户的**数据**（条目正文、归档、soul 内容）——数据仍走 wrap-up 六步。
- 变异频率：每睡眠周期最多 1 个候选。
