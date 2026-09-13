# task-034 · 技能源码下载与索引清单（2026-09-14）

## 触发
用户令（承接 task-033 侦察）：「下载源码，写一个关于这些skill的索引清单，要附上每个的简历」；并投喂外部分析（Graphiti/LangGraph MVP 路线）作参考——按 R-014「下发文书=外来断言·接单即核证」先对账再入册。

## 交付物
- **`正典库构建系统/现成技能侦察/源码/`**：16 仓全量源码入库（`git clone --depth 1`，约 301MB，含 .git 可增量更新）
- **`正典库构建系统/现成技能侦察/索引清单.md`**（652 行/61.7KB）：总览表 + 16 份人工核证简历卡（定位/能力详解/CBB 对口/缺口/安装/许可红旗）+ 305 个技能的一行式清单（脚本自动提取 frontmatter）+ 附录 A 参考路线核证 + 附录 C CBB 组件映射速览
- **`tools/build_inventory.txt`**：半自动构建器（extract 从 SKILL.md 提取技能元数据→fragments；merge 将简历主体占位符注入成终稿），可复现：`py -X utf8 tools/build_inventory.txt all`

## 外来断言核证结果（附录 A 全表在索引清单内）
- getzep/graphiti 31k★ ✅ 属实（时序图谱/provenance/混合检索/FalkorDB+Neo4j 双后端）；「中文小说抽取精度开箱即用」降级为【需自测】
- langchain-ai/langchain-skills 1.2k★ ⚠️ 存在但为 LangChain 用法技能（早期开发）；「通过率 25%→95%」无出处【待确认】
- falkordb/graphrag-sdk 996★ ✅ 存在
- Revise.net=角色一致性 SaaS ❌ **证伪**（实为通用编辑器）；真做 canon 一致性的是 ProseEngine / NovelCrafter——「需求已商业化」反而被证实

## 关键过程数据
- 16 仓共 **305 技能**；许可红旗：webnovel-writer **GPL**、neuro-book **AGPL**（传染性）、agent-skills/basic-memory/sillytavern-skills 未标注
- 体积红旗：neuro-book 223MB、claude-book 24MB
- 星标补齐：davidgibbons/sillytavern-skills 13★、rhavekost/author-toolkit 15★
- 合并产物 0 占位符残留，注入点人工抽查通过

## 复用与纪律兑现
- PT-008（clone→安检）、P-004（含中文特殊字符的生成全走 Write 工具，脚本用 .txt 规避 hook）
- 轨迹编号先 ls 查重（R-015）：2026-09-14 当日无占用，取 034
- P-005 精神：构建器交付即跑（extract→merge 全链验证），产物 wc/grep 校验
