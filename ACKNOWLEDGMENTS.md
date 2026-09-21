# Acknowledgments & Provenance（研究出处声明）

本项目的流水线设计经过对 16 个同类开源项目的**设计级研究**后构建。
郑重声明：**仅吸收设计思想，未复制任何第三方代码或文本**；下表所列
GPL / AGPL / 无许可证 / NC 项目均为**零代码、零文本接触**（仅阅读公开
文档与目录结构作对比研究，污染审计见项目内部记录 task-060）。

## 研究项目一览

| 项目 | 许可证 | 研究方式 | 关键借鉴（思想级） |
|---|---|---|---|
| agent-skills | 仓级无 / 技能级 MIT | 设计研究 | 正典状态机、fact-check 分 pass |
| author-toolkit | MIT | 设计研究 | 置信度双口径（确定性/判断） |
| basic-memory-skills | README 声明 MIT（无正文）→ **按无许可处理，仅只读** | 设计研究 | 六阶段分析管道、never-delete |
| chinese-webnovel-skills | MIT | 设计研究 | 时间线绝对锚点、伏笔台账 |
| claude-book | MIT | 设计研究 | 证据式抽取、冲突解决表 |
| danghuangshang | MIT | 设计研究 | 伏笔五态、任务状态机 |
| evals-skills | MIT（上游已迁移） | 已安装使用 | judge 四要素、校准协议 |
| graphify-novel | MIT | 设计研究 | 边证据分层、批扫章协议、注入防御 |
| neo4j-skills | MIT（官方） | 已安装使用 | 图建模五律、MERGE 幂等 |
| neuro-book | **AGPL-3.0 → 零接触** | 只读文档对比 | 双时间轴 tick/instant 概念（自研实现） |
| oh-story-claudecode | MIT | 设计研究 | 逐章子代理+降维聚合、别名四分类 |
| sillytavern-skills | 无许可证 → **零复制** | 只读文档对比 | 双控制面分层概念 |
| story-skills | MIT | 设计研究 | 三域校验、关系逆类型、契诃夫枪算法 |
| story-systems-template | MIT | 设计研究 | verified_against 漂移钩子 |
| webnovel-writer | **GPL-3.0 → 零接触** | 只读文档对比 | 时序回放/UNIQUE 约束概念（自研实现） |
| worldbook-skill | **CC BY-NC-SA 4.0 → 零文本复制** | 只读文档对比 | 输出侧禁词分类概念（自建词表） |

## 红线（对本项目未来贡献者）

1. 上述 **GPL-3.0 / AGPL-3.0 / 无许可证 / CC BY-NC-SA** 四仓永远保持零代码、
   零文本接触——任何直接复制即污染本仓许可，违者回滚；
2. 若未来从 **MIT 仓**直接复制代码（当前没有），必须在该文件头附原仓版权
   与 MIT 声明；
3. 设计思想（ideas）不受版权保护——本仓所有代码均为对照约束下的独立实现，
   并有单元测试与污染扫描记录为证。
