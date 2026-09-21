# cbb-pipeline

**Correct-by-Construction Canon Library Pipeline** — 把百万字级长篇小说全本，转化为带证据链、可校验、可查询的**正典知识库**。

> 面向 Agent 的技能入口见 [SKILL.md](SKILL.md)（[agentskills.io](https://agentskills.io) 规范格式）。本仓库为该技能的完整发布。

## 它解决什么问题

长文本（百万字小说）的正典提取有一个根本矛盾：**任何单上下文都装不下全书，而跨章逻辑（别名、伏笔、人物生死、前后矛盾）恰恰活在中断的地方**。

本流水线的解法是**逻辑不活在上下文里，活在账本与约束里**：

- **抽取无状态**——每章由一个全新上下文的子代理抽取（带 library 派生的有界先验包），永不依赖"记得前面写了什么"；
- **跨章记忆外置**——所有事实落盘为带（卷,章,行,引文）证据四元组的结构化记录，可检索、可回滚、可审计；
- **全局约束求解**——抽的时候允许局部盲，入库后由确定性算法全库校验：死人走路拦截、契诃夫枪超期报警、悬空引用扫描、矛盾双轨路由；
- **三态写入**——confirmed / provisional / quarantine，**错误永远进不了 confirmed**；处理不了显式隔离出报告，绝不静默。

## 安装

```bash
# 复制到 ZCode / Claude 技能目录（全局或项目级均可）
cp -r . ~/.zcode/skills/cbb-pipeline
```

无第三方依赖；Python 3.10+。嵌入查重（LM Studio）与图导出（Neo4j）为可选增强，缺省不影响主链。

## 快速开始（新书三步）

```bash
# 1. 填写开书参数（书名/语料路径/锚点纪元/阈值，全部可调）
cp assets/project.template.yaml project.yaml   # 编辑
# 2. 生成书房骨架（幂等）
py -X utf8 scripts/init_project.py project.yaml
# 3. 按SKILL.md流程路由逐章派子代理抽取 → gate1 → quarantine → store
```

## 仓库结构

| 路径 | 内容 |
|---|---|
| `SKILL.md` | Agent 技能入口（流程路由+十纪律速查） |
| `references/` | 编排与并发 / 十查与终审 / 抽取规范（R6 四面防御）/ 判例模板 |
| `scripts/cbb/` | 六技能模块（coordinate·anchor·extract·gate1·quarantine·store）+ 四契约 schema（Record/Issue/Verdict/Case） |
| `scripts/cbb/tools/` | 上下文包生成 / 嵌入查重 / Neo4j 图导出 / 账本哈希链 / NLI 矛盾对 / graphiti 桥（各配单测） |
| `assets/` | project.yaml 模板 |

## 质量基线

- 七主套件 + 五工具套件单测全绿；端到端冒烟通过
- 实战：长篇连载全本入库验证（含倒叙卷、噪音章、双译本重叠判例）
- 设计来源：16 个同类开源项目的系统对比吸收（吸收/外挂/只读三档裁决）+ 专有判例

## License

内容与文档 CC-BY-4.0；代码可自由使用，禁止行为仅一条：**声称未经本管线校验的库为"已校验正典"**。
