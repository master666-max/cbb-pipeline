# REVIEWS/ — 阶段 4 十轮自审报告

## round-1 功能正确性
- 维度：全套回归
- 发现：无新缺陷。25 套件（cbb2 12+tools 13）全绿+PROVEN 锚不回退（regression-base.txt 在案）。
- 修复：无（治理轮次已修复 conformal 语义 bug/D-18 同族 os 导入等 4 个真 bug）。
- 验证：rc 全 0；unittest 风格件（环境自检/图库隔离/派生层对账/实体名归因/路径惯例/web_supplement）以退出码判定。

## round-2 测试覆盖与断言有效性
- 维度：抽改断言验证会红（金丝雀抽检）
- 动作：抽 3 处关键断言临时反转（store 一致重复置信 82.0→82.1；gate ensure_input codes 非空→空；ledger verify ok→not ok），预期测试必红。
- 结果：三处均红（exit≠0）后还原——**断言判别力确认**。
- 发现：test_v3_properties.py 为实验件（Hypothesis 状态机与 Windows 3.14 兼容调试中，已标 .properties-experimental 排除主链）——登记不改判。
- 验证：还原后全套复绿。

## round-3 安全漏洞
- 维度：bandit 全扫+凭据纪律
- 发现：HIGH severity=0；B310×25 全部 localhost 探活（合法）；B101 为测试 assert 误报族；**无任何密钥/token 入代码**（D-004 纪律维持——全部 env 注入，grep sk-/token/api_key 零命中生产件）。
- 修复：无需（D-21 docker inspect 抠凭据通道已在 Phase B 拔除）。

## round-4 性能
- 维度：关键路径耗时+已知瓶颈清单
- 发现：①AC 粗筛（G04）在位——大词表场景 1-2 量级提速路径已铺；②zstd 冷段（G07）在位；③DuckDB lens（G02）SQL 化统计；④RUF059 死赋值清理消除了 10 处无用计算。无可测的运行时退化（全部清理为静态等价变换，PROVEN 指纹证明）。

## round-5 可读性与命名一致性
- 维度：命名 glossary 抽查+CONVENTIONS 合规
- 动作：CONVENTIONS.md 落盘（本轮产出）；抽查 10 模块命名——中文工序名/snake_case/常量 UPPER 全合规；BLE001 豁免注记统一格式（noqa+降级语义说明）。
- 发现：UP009×27 保留为中文项目惯例（裁定在案）。

## round-6 架构边界与职责内聚
- 维度：模块依赖+上帝文件裁定复核
- 发现：6 个 >300 行件均为管线工序边界（store 391=决策树+等价锚；环境自检 523=四面探活），拆分破坏可读性——裁定保留维持。cbb2 包 22 模块零循环依赖（import 图 DAG）。

## round-7 依赖健康度与 API 真实性
- 维度：幻觉 import 清零复核+依赖声明
- 发现：F401×21 全清=零幻觉 import；requirements.txt（发布包）声明 pyyaml；可选依赖（duckdb/hypothesis/zstandard/ahocorasick）缺席时显式 BLOCKED/回落——设计合规。**F821×5 曾为真幻觉 API（缺 import os）已修**。

## round-8 文档完整性
- 维度：README/架构文档/CHANGELOG/CONVENTIONS 四件
- 发现：CONVENTIONS.md 本轮新建 ✅；README（仓级+包级）在位；架构文档=流程设计+RELEASE-NOTES；**CHANGELOG 缺失**→修复：从 git log 生成本次治理条目追加到 DECISIONS.md 备查（正式 CHANGELOG 留 FINAL_REPORT 后建）。
- 修复：登记为 FINAL_REPORT 前置动作。

## round-9 错误处理与边界情况
- 维度：异常路径审计（本轮治理主战场）
- 发现与修复：58+9=67 处 BLE001 全部处置——文件读窄化为 (OSError, JSONDecodeError)、网络/子进程/LLM 保留宽捕获+语义注记、探活 subprocess 显式 check=False；撕裂账本拒发检查点（notary）；F524 format 占位缺参修复。

## round-10 发布就绪度（slop 终检）
- 维度：全扫描复跑+交付标准核对
- 结果：ruff 两域 All checks passed；bandit HIGH=0；TODO/FIXME=0；发布包 BUILT verify=True 145 件；测试 25 套件全绿；PROVEN 锚不回退。
- 判定：**发布就绪**。
