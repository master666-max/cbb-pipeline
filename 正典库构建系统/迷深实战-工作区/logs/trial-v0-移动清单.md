# trial-v0 本体库移动清单（U-C00 试车期现场留档）

- 时间：2026-09-16（U-C00 试车当日，未 commit 前的运行现场）
- 动作：`迷深实战-本体库/`（81 文件，361K）整体移动 → `迷深实战-工作区/trial-v0-本体库/`，随后以 v2 设计重建生产库于原路径。
- 性质：**移动留档，非删除**。全部字节原样保留（含首跑门1拦截 2 条、误引文裁决 2 条、entity_refs 漂移导致的 10 条假矛盾隔离项完整现场）。

## trial-v0 两起事件（证据链在档）

1. **门1逮住亲抽引文笔误**（防线有效性实证）：候选引文"所在之处"vs 原文"所在**何处**"，G1-EVIDENCE 证据回落拦截 2 条（拉丝缇娅拉实体+发誓帮忙寻找关系），修正引文重抽后入库；被拦件在 trial-v0 隔离区走 rejected 裁决关闭（note 在 adjudications.jsonl）。
2. **entity_refs 漂移假矛盾**（设计缺陷实证）：run1 拦截拉丝缇娅拉实体期间，12 条下游记录的 canonical.entity_refs 指向其旧 record_id；引文修正后实体换新 id，run2 重放时 entity_refs 字段与库内不一致 → canonical_conflicts 误判 10 条 contradiction_pending。
   - 根因：entity_refs（派生自上游内容哈希 id）放进 canonical 参与双轨一致性比对，天然随上游修正漂移。
   - 修正（v2 设计，写入抽取规范）：canonical 不再携带 entity_refs；关系以 subject/object 名称引用实体，事件/伏笔以 canonical.entities（名称数组）标注涉事者；id 级 REF/死人走路检查在批管线中休眠，孤悬引用审计改由 U-C09 R2 按名称全扫承担（责任转移登记 STATE）。

## trial-v0 目录内容（81 文件）

- aliases.jsonl / appearances.jsonl / supersede-index.jsonl（如有）
- libraries/{character,setting,relation,event,foreshadow,timeline}/provisional/*.json（76 条入库记录：74 首跑 + 2 修正重抽）
- quarantine-zone/items.jsonl（13 条：2 首跑拦截 + 1 置信路由 + 10 假矛盾）
- quarantine-zone/adjudications.jsonl（2 条 rejected 裁决）

## 为何留档而非删除

- 永不删除铁律；事件 1/2 是工单 §3 十查⑥（隔离分流）与防线有效性的第一手证据；
- 审核线复算可完整重放：两个 trial 库并存对拍即可复现 entity_refs 漂移机制。
