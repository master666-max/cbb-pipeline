# 裁决记录（reimagine · 全裁决权代行 · 2026-09-26）

## D1 preflight 五问（代答）
1. 整系统还是切片？→ **核心管线重建（六模块+账本+检索机械面），长尾工具（66 件 tools）保留在 cbb/ 原地、增量迁移**。理由：裁判基线覆盖的是核心行为；长尾件无特征锁，整仓重建=无保护重写，违 LRF 铁律。
2. 能在本机构建/测试吗？→ 能（纯 stdlib + 本机 py 3.14；验收测试零外部端点依赖）。
3. 自定义构建工具？→ 无。
4. 有人试过吗？→ 是——本仓自身从 v0 演化至今，账本/冻结线在案；重建不得破坏既有数据兼容。
5. 有禁区吗？→ 有：本体库/工作区数据、决策账（追加only）、cbb/ 原线（保留对照）。

## D2 目标架构（reimagine 批准）
```
cbb-v2/
  cbb2/                 # 可安装包——绝对导入，消灭全部 sys.path 手术（46 处债务之首）
    config.py           # env-first 配置 + 路径惯例推导（吸收 路径惯例.py，无实例默认）
    contracts.py        # 契约校验（v1 实现移植——proven，schema 即契约）
    corpus.py           # 坐标/切片/BOM/引文回落（R9/R10）
    defenses.py         # 元文本/注入/禁词/无先验闸（R6/R7/R8/R15）
    gate.py             # 证据门（引文回落→可见性判定）
    store.py            # 三态+双轨+原子写+撕裂披露+迁移（R1-R5/R13）
    ledger.py           # 哈希链账本（R12）
    quarantine.py       # 隔离区（R14）
    search.py           # 机械检索面：别名+关键词+RRF+引文核验（R11）
    runner.py           # 单一编排入口（章管线骨架：收口 aux 四件探活降级）
  tests/
    acceptance.py       # 验收=对 characterization 同一五面观察，fingerprint 必须相等
  README.md
```
**关键决策**：
- **等价优先于优雅**：store/gate/contracts 核心逻辑从 v1 **移植**（同一算法、重组结构），验收以特征指纹相等证明——重建的价值在架构（包化/配置统一/入口统一），不在重写已证明的算法。
- **数据兼容**：cbb2 直接读写 v1 库格式（同 schema 同布局）——重建的是代码不是数据，切换零迁移。
- **长尾工具不搬**：tools/ 66 件留 cbb/（LIVE），cbb2.runner 以适配层调用；后续按需迁移。

## D3 差异接受（预裁）
验收唯一判据：**characterization 五面指纹相等**。任何不相等=行为漂移=修到相等为止，不接受"新实现更好"类差异（那是 transform 轨道的事，不是 reimagine 的等价重建）。

## D4 证明签字（预裁）
acceptance.py 全绿 + 金丝雀对 cbb-v2 同样有效（改坏 cbb2 一行验收必红）→ 签字 PROVEN；否则 NOT PROVEN 并如实报告。

## D5 模块命名
包名 cbb2（与 cbb/ 并存、不遮蔽）；模块名单词化（corpus/defenses/gate…），与 v1 中文名工具不冲突。
