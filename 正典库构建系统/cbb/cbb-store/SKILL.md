# cbb-store（本体版 v2 · 双轨合并+约束族+cbb-merge 并入）

> B1/B5 三态写入+版本化+双轨合并存储（jsonl-file 后端；Neo4j/Graphiti 归 P2）。前置：contracts v2.0、cbb-quarantine。

## 双轨合并（重构核心；`dual_track`/`admit_or_merge`）
- **一致重复**（身份键同、canonical 无同键异值）→ confidence 上调合并：`max(双值)+2.0`（CORROBORATION_BUMP，CBB 定约，封顶 100）+证据并集，经 **supersede 出新版本**（旧件字节不动）。
- **矛盾**（身份键同、字段冲突）→ **quarantine（contradiction_pending）+Verdict**（critique 先行/label=conflict/分带一致/rule_applied=并陈 documented_variance，构造期契约校验）——**不静默合并**。
- **无既存** → ON CREATE（provisional 起步）。
- 身份键：entity=库名+canonical.name；relation=三元组；其余=record_id（内容寻址）。

## 吸收项（U-A17 §3）
- **UNIQUE 约束族**（schema 层防重，文件后端等价）：别名复合 PK `register_alias(alias,entity_id,entity_type)`／关系三元组唯一 `relation_triple_exists`（同三元组再入=双轨一致重复）／出场唯一 `record_appearance(entity,chapter)`。
- **verified_against 漂移钩子**（story-systems）：`drift_check(record, 当前SHA)` 源变更→stale；`stale_records({path:SHA})` 全库重验门扫描。
- **ON CREATE/ON MATCH 幂等**（neo4j MERGE 语义）= `admit_or_merge`。
- **时序回放查询**（chapter<=? ORDER BY 顺序覆盖）：`log_state_change` 追加日志+`entity_state_at_chapter(entity, chapter)` 任意章状态快照。
- **写入安全围栏**：`_assert_within_root`（根围栏：写出库根即拒；record_id 注释攻击实测拦截）+符号链接拒绝（祖先级 symlink 一律拒写）+命令白名单思想（store 层零 shell 调用，CLI 仅 --stats 声明动词）。
- **cbb-merge 并入**（用户裁决：规模小不拆独立技能）：`multiversion_merge`——Keep（全源同值→规则值）/Range（数值波动→min-max 区间）/Flag（单源特有→保留+待证）/Pick（异值→取最长，CBB 定约）+冲突表（Sources vary 并陈）。

## 保留面（v1.0，16 仓无更优完整替代）
三态写入（confirmed/provisional 入库、quarantine 走隔离区）；旁车 transitions.jsonl（append-only，文件写后不改，幂等迁移）；supersede 版本化（新版本新文件+索引旁车）；置信度路由（confirmed 永不因置信度单独达成）。

## GPL 合规声明
webnovel-writer（时序回放/UNIQUE 约束族/urgency 设计源）为 GPL 仓：本实现**按设计重写、零源码引用**，`全量构筑版-分析报告/webnovel-writer.md` 为唯一转述层（该详报合规提示原文要求）。

## 用法
```bash
py -X utf8 cbb/cbb-store/cbb_store.py --root kb --stats
```
