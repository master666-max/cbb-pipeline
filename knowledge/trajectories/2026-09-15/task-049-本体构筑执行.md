# task-049 · 本体构筑执行（U-B00~U-B09 全量交付）

- 日期：2026-09-15 ｜ 会话角色：CBB 构建线执行代理（/goal 无人值守）
- 一句话：按《本体构筑-工单.md》v1.0 完成十单位全量构筑——cbb/ 本体版 v2 落地（四契约 v2.0+六技能重构），161/161 单测绿（≥实验版 73 基线），集成冒烟 74/74 双跑一致 EXIT 0，真管道 blocked 留阶段三，十单位十轮自审出口门全过，10 笔 scoped commit 可证。
- 复现：`py -X utf8 -B -m unittest discover -s <各技能目录> -p "test_*.py"`（合计 161）；`py -X utf8 -B cbb/smoke/run_smoke.py`（74/74 EXIT 0）；`--probe` 真管道探活。
- 数据流：coordinate（坐标+编号注册表）→anchor（双时间轴）→extract（四面防御 stub）→gate1（三域+Issue v2.0）→quarantine（三子类+urgency）→store（双轨+UNIQUE 约束族）。
- 关键决策：①契约 v2.0 十一新字段全落地（critique 键序/分带强制/两派并陈/三段式配对）；②双时间轴=neuro-book（AGPL）设计转述零源码；③webnovel-writer（GPL）按设计重写零源码；④store 双轨一致重复上调 max+2.0（CBB 定约）；⑤三态桩五处移除统一归 store。
- 踩坑与经验：①集成同目录双跑暴露 store 两真幂等缺陷（find_by_identity 活版本/证据子集守卫）——单测全绿≠集成幂等；②multiversion 分支序真缺陷被测试当场抓（单源判定须前置 all-equal）；③R6 验证文本防漂移=importlib 双载逐字比对。
- 复用提示：cbb/ 六技能+契约可直接作阶段三（真管道）基底；施工参数（5-8 章/批+15KB→8K→√N）迷深 517 章直接可用。
- 交付：`正典库构建系统/cbb/`（交接文书-本体构筑.md=总入口）；STATE=正典库构建系统/本体构筑-BUILD-STATE.md；commit 724edb29→a39a16a9 十笔。
- 判定权在审核线（构建线无权自宣验收通过）。
