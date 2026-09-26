# 业务规格（Given/When/Then）· 从代码与特征基线挖掘（2026-09-26）

> 来源：analysis/characterization.py（真实运行指纹）+ cbb 各模块在案测试（37 件）+ 全流程说明书。
> 每卡带 file:line 引用；imagine 重建必须满足全部 G/W/T（验收测试逐卡对应）。

## R1 三态写入（P0）
- **G** 任意 candidate 过契约校验
- **W** `admit(rec, "provisional")`（cbb_store.py:234）
- **T** 落 libraries/<lib>/provisional/<rid>.json；quarantine 决定不落 library（cbb_store.py:250）
- 引：test_cbb_store.py::test_admit_three_states

## R2 一致重复合并（P0）
- **G** 库内已有同身份记录，新观察一致（confidence 不低于库内）
- **W** `admit_or_merge(dup)`（cbb_store.py:353）
- **T** track="consistent-duplicate"，confidence 上调，版本 +1，**同内容重放零副作用**（P-017 证据子集守卫）
- 引：test_cbb_store.py::test_reingest_same_observation_idempotent

## R3 矛盾不静默合并（P0）
- **G** 同身份冲突字段（alive vs dead）
- **W** `admit_or_merge(conf)`
- **T** track="contradiction"，进隔离区 items.jsonl，**矛盾不落库**
- 引：smoke/run_smoke.py:186-188

## R4 原子写（P0）
- **G** 任何库文件写入
- **W** `_write_immutable`（cbb_store.py:193）
- **T** temp+os.replace；崩溃不留半截 JSON；落定失败清残件
- 引：test_cbb_store.py::test_a2b_crash_leaves_no_partial_file

## R5 撕裂 JSON 不崩全链（P0）
- **G** libraries 下存在撕裂/坏编码 JSON
- **W** `iter_records()`
- **T** 不抛异常，坏件入 iter_skipped 披露
- 引：test_cbb_store.py::test_a2a_torn_json_disclosed_not_crash

## R6 元文本闸（P0）
- **G** 标题含"章末说"或正文含"本章说/翻译：/转载请注明…"
- **W** `is_metatext`（cbb_extract.py:99）
- **T** True → 整章跳过抽取
- 引：characterization 抽取面；test_cbb_extract.py::test_metatext_chapter_yields_zero

## R7 注入闸（P0）
- **G** 正文含"忽略之前/system prompt/rm -rf/```"等
- **W** `has_embedded_instruction`（cbb_extract.py:110）
- **T** True → 整块拒抽（宁漏勿执行）
- 引：characterization 抽取面

## R8 跳过块登记（P1）
- **G** 抽取跳过块（元文本/注入）
- **W** `extract_stub(..., skipped_out=[])`
- **T** 每跳过块登记 {chapter, line_start, reason}——不静默丢弃
- 引：test_cbb_extract.py::test_a9_skipped_blocks_registered

## R9 引文逐字回落（P0）
- **G** 任意证据引文
- **W** `locate_quote(blocks, vol, chapter, quote)`（cbb_coordinate.py:104）
- **T** 首个 vol/chapter 匹配且 text 含 quote 的块；找不到=None（门1 判不可见）
- 引：characterization 坐标面

## R10 BOM 剥离（P0）
- **G** 语料带 UTF-8 BOM
- **W** `process_file`（cbb_coordinate.py:118）
- **T** decode("utf-8-sig")，首章标记必须匹配
- 引：test_cbb_coordinate.py::test_a8_bom_stripped_no_coordinate_shift

## R11 别名精确召回（P1）
- **G** 查询含实体名/别名
- **W** `alias_recall`（检索层.py:56）
- **T** 确定性命中，零模型依赖
- 引：characterization 检索面

## R12 账本哈希链（P0）
- **G** 任何 store 侧车写入
- **W** LedgedStore._append → ledger.jsonl 追加（sha_before/after+幂等键）
- **T** verify(store) ok=true；**旁路直写后 verify 必 false**
- 引：characterization 账本面；test_ledger_chain.py::test_tamper_detected

## R13 状态迁移有效态（P1）
- **G** 迁移轨迹（provisional→confirmed→provisional）
- **W** `status_transition` / `effective_status`
- **T** from 记有效态；幂等重放 repeated=True
- 引：test_cbb_store.py::test_a4_transition_from_is_effective_state

## R14 隔离区一等公民（P0）
- **G** 矛盾/低置信/超期件
- **W** zone.register（group/subclass/detail/record_id/source）
- **T** items.jsonl 登记；status 全法值；绝不静默丢
- 引：批次自检 c6；test_cbb_quarantine.py

## R15 批量计划确定性（P2）
- **G** plan_batches(20, 8)
- **T** [[1..8],[9..16],[17..20]]——同输入同输出
- 引：characterization 抽取面
