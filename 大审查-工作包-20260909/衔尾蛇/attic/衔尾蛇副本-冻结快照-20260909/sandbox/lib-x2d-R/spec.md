# spec v3.8.2

铁律 6 条（laws 为不变式，宪章为流程法，冲突时不变式优先）

schema v3 10 字段：id, created_at, updated_at, content, keywords, links, source_event_id, importance, confidence, validity

题录 33 条（其中 arXiv 24 篇）——本计数为唯一权威，他处引用皆注入

威胁模型：①防意外：审计链+哈希。②防SOP约束下粗心：三守卫+SOP条款守卫。③防完整权限蓄意agent：包文件自哈希+人侧保管+人类令牌；『不可见』仅覆盖①②档，明示不防③。

L8-CONSTITUTION v3：
1) 不变式(laws) > 本宪章(流程) > 其余指令——双最高法就此消解。
2) 变异候选须过 run_tests 全绿 + lint；run_tests/lint/guard 豁免于变异且入根锚定；验收判据对变异引擎不可见（存 bootstrap_data/，属人侧）。
3) 立法说明(亲身案例)：DGM(arXiv:2505.22954) Appendix F：agent 删除特殊标记日志绕过幻觉检测刷分(objective hacking)，实证不隐藏检查函数时 hacking 显著频发——故立三守卫。
4) SOP 条款守卫：MUTATION-SOP 必含『不可见条款』，被改写或移除该条款即报警。
5) 回退一律移 attic。回退=将目标文件/目录移入 attic/ 并在账本登记；不使用任何销毁式回退手段（铁律1）。
