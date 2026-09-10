# bootstrap_v3.py 深度代码审查报告

- 审查对象：`bootstrap_v3.py`（2415 行，VERSION=3.8.1，单文件）
- 审查方式：静态全量通读 + 实际运行验证（构造 v2.x 源树跑通 absorb→install→engine→guard→doctor 全链路，另做 17 组定向缺陷探针）
- 复现环境：Python 3.10；合成 v2.x 源树 63 文件；`absorb` 后 `install L2`
- 自测基线：补齐合成夹具后 **67/68 通过**（唯一失败项 `t_full_render_rule` 因夹具 install.md 不足 10 个）；**干净检出（无 bootstrap_data/）下只能跑到第 9 个用例即中止**

---

## 结论摘要

| 级别 | 数量 | 一句话概括 |
|---|---|---|
| P0 严重 | 4 | 自测结论是写死的；证据准入可被空串绕过；install 中断重跑会覆盖用户文件；并发写丢更新 92% |
| P1 重要 | 8 | guard 可被 patch 形态绕过；检索排序与查询无关；同 id 跨层共存；三处写操作漏刷根；类型未校验崩溃；审计链换行注入；verify 覆盖面与标签不符；测试非封闭 |
| P2 建议 | 13 | 7 项死配置、64bit manifest、依赖顺序敏感、absorb 静默缺件、absorb-md 静默丢段、版本不一致等 |

**总体判断**：设计与公理层面（单一事实源、审计链只追加、回退移 attic、Merkle 根锚定）相当克制且自洽，属于少见的高成熟度个人工程。但**工程执行层存在系统性缺口**：`sys.exit` 被当作库函数错误通道（24 处）、写路径无锁、不变式靠 168 条 `assert` 承载、以及**自测结论被硬编码为"全绿"**——后者直接违反本项目自己的公理 G（可证伪）。

---

# P0 · 严重

## P0-1 自测套件可被 SystemExit 一击致命，且"全绿"从未被测量

**位置**：`cmd_run_tests` L2377-2383；`render_quickref` L314

```python
# L2379-2381
for fn in TESTS:
    try: fn(); print(f"  PASS {fn.__name__}")
    except Exception as ex: fails += 1; print(f"  FAIL {fn.__name__}: {ex}")
```

`SystemExit` 是 `BaseException`，**不是** `Exception`。而本文件把 `sys.exit()` 当作唯一错误通道（24 处调用点，覆盖 install / engine / verify / guard / migrate 全部失败路径）。任何一条未预期退出都会整轮静默中止：不打印 FAIL、不累计、不打印 `run_tests` 汇总行。

**实测证据**

```
$ python3 bootstrap_v3.py run-tests
  PASS t_chain_and_cross_month
  ...（前 9 个）
  PASS t_install_requires_bodies
v3.2/C-001：bodies 内容体为空——install 拒绝产出空库    ← stderr
REAL_EXIT=1
```

第 10 个用例 `t_merkle_root_consistency` 调用 `cmd_install` 撞上 `sys.exit` → 进程直接退出。使用者看到"9 个 PASS、无汇总、exit 1"，最自然的解读是"差不多都过了"。

**更严重的是第二半**：由该文件渲染的《提示词速查》永远写着

```python
# L314
f"---\n*测试：run_tests {tests_n}/{tests_n}（计数由构建注入）*\n"
```

`tests_n` 传入的是 `len(TESTS)`，分子分母同一个数 → **恒等于 "68/68"，与实际执行结果无关**。也就是说：文档向人侧声明了一个从未被测量的事实，`install` 生成的每个库都带着这句话。这与公理 G（可证伪：行为变更先 shadow，测不出差异即判表演）直接冲突，且与 `t_no_handwritten_counts`（L1242）想要防止的"手写计数"其实是同一类病灶，只是换了个形态。

**修复**

1. `cmd_run_tests` 改为 `except BaseException`，区分 `AssertionError`（FAIL）/`SystemExit`（意外退出，记 FAIL 并打印退出消息）/ 其他（ERROR）；循环外加 `finally` 打印汇总并 `sys.exit(1 if fails else 0)`。
2. 引入 `last_test_run.json`（时间戳 + 包 sha256 + 逐用例结果），`render_quickref` 读真实结果；无法取得时渲染"未测量"而非 N/N。
3. 给每个用例套 `setup/teardown`，保证一个用例崩溃不影响后续（见 P1-12）。

---

## P0-2 铁律 2（证据准入）可被空字符串绕过，且 absorb-md 批量伪造证据锚

**位置**：`validate_entry` L244；`cmd_absorb_md` L497 / L510 / L521

```python
# L244
if "evidence" not in e and "source_event_id" not in e: errs.append("无证据锚(铁律2)")
```

只检查**键是否存在**，不检查值。实测：

```
validate_entry(source_event_id="")  → []        # 通过
→ 空证据锚条目写入成功: True
```

对单条写入尚可辩解为"调用方自律"，但 `absorb-md` 把这个问题放大成规模性缺陷——它给**所有**迁移条目统一写死：

```python
"source_event_id": "genesis-v4"   # L497 / L510 / L521
```

实测确认 `genesis-v4` 在审计链中**根本不存在**：

```
审计链中是否存在 genesis-v4 事件: False
```

而 `doctor` 的三方对账（L1036）用 `entry:(\S+) →` 从审计链提取 id，**并不校验 `source_event_id`**，所以伪造锚点对账不出来。结果是：一次批量迁移可以灌入任意条"看起来有证据锚、实际指向虚无"的条目，系统自检全绿。

顺带一提，`absorb-md` 还会把非法日期**硬编码改写**成 `2026-09-06`（L475）：

```
P-004 源日期 = "not-a-date"  →  入库 created_at = "2026-09-06"
```

在一个把引文纪律写进铁律的系统里，这是静默伪造。

**修复**

1. `validate_entry` 改为 `if not (e.get("evidence") or e.get("source_event_id"))`（判空而非判存在）。
2. 可选加强：校验 `source_event_id` 能在 `audit/` 中检索到对应行。
3. `absorb-md` 先 `chain_append` 一条 `M-00x bulk-import` 事件，用其真实哈希回填 `source_event_id`；日期无法解析时**拒绝并报告**，而非改写。

---

## P0-3 install 中断后重跑会覆盖用户文件，违反铁律 1

**位置**：`cmd_install` L763（首装判定）；`_deliver` L722-726（无条件写）

```python
is_first = not (target / "state.json").exists()   # L763 —— 唯一判据
...
dest.write_bytes(data)                            # L726 —— 无条件覆盖，无备份、无 attic、无事务
```

"是否首次安装"只看 `state.json` 在不在。如果 install 在写 state.json 之前崩了（L871 之前任何一步：磁盘满、权限、Ctrl-C、渲染异常），下次运行会被判定为首次安装，`_deliver` 把所有交付文件无条件重写一遍。

**实测证据**

```
构造：install L2 → 用户修改 modules/m-core/README.md → 删除 state.json（模拟中断）
重跑 install L2
→ README.md 内容: "# modules/m-core\n原始 v2.x 正文 A"   ← 用户修改被静默覆盖
→ 账本 install 次数: 2
```

`_deliver` 全程没有 attic 转移、没有备份、没有事务边界，而铁律 1 明文规定"永不删除/覆盖已有记录"。慢车道（公理 F）只管住了 L8/L9 安装，**真正会破坏数据的这条路径没有任何护栏**。

**修复**

1. 首装判定改为：`target` 非空 且 无 `state.json` → 判为"脏目录"，拒绝并要求 `--force` 或先人工清理。
2. `_deliver` 写前若目标已存在且内容与待写不同 → 先移 `attic/<ts>/` 并入账，再写。
3. 把 state.json 的写入提前为"预写占位 + 完成后落真值"，或加 `.install-inprogress` 标记，让中断可识别。

---

## P0-4 写路径无锁，并发下 state.json 丢失更新 92%

**位置**：`cmd_engine` append L936-941（同构于 wrapup L973-981 / retire L1089-1093 / reflect-done L1025-1030 / redeliver L826-827）

```python
st = json.loads(st_path.read_text(...))                       # 读
st["importance_accum"] = st.get("importance_accum", 0) + ...  # 改
st_path.write_text(json.dumps(st, ...), ...)                   # 写
```

经典 read-modify-write，全文件无一处 `fcntl` / `msvcrt` / `O_EXCL` / 临时文件 rename。

**实测证据**（12 进程 Barrier 对齐并发 append，每次 importance=5）

```
importance_accum = 5   （期望 60，丢失 91.7%）
落盘条目数: 12（文件本身没丢，但派生量全丢）
```

`importance_accum` 是反思触发（阈值 50）的唯一输入，丢更新的直接后果是**反思机制静默不触发**。审计链 `chain_append`（L220-238）是同构的 read-then-append 且同样无锁（本次未能强制复现断链，但代码上没有任何互斥保证）。

**修复**

1. 所有写路径取排他文件锁（`fcntl.flock` / `msvcrt.locking`），或统一走"写临时文件 + `os.replace` 原子替换"。
2. `importance_accum` 这类派生量从 `state.json` 移除，改为从 `ledger/changes.jsonl` 重算——从根上消除 lost update。
3. 若系统定位就是单写者，请在 `AGENTS.md` 与 `spec.md` 里显式声明，并在 append 时检测并发（如 PID 文件）后拒绝，而不是默默算错。

---

# P1 · 重要

## P1-5 guard 只做文件名子串匹配，真实 diff 形态完全可以绕过

**位置**：`cmd_guard` L1130-1137

```python
for p in (d.rglob("*") if d.is_dir() else [d]):
    name = p.name
    if any(b.lower() in name.lower() for b in BASELINE_BLACKLIST):   # L1134
        touched.append(str(p))
```

只看**文件名是否包含黑名单子串**，不看路径、不看内容、不看 hunk。

**实测证据**

```
构造 changes.patch，内容：
  --- a/run_tests.py
  +++ b/run_tests.py
  - assert x
  + pass

guard 输出：通过——diff 未触及基准黑名单（9 项）
```

三种常见变异形态全部逃逸：

- 把 diff 打成单个 `.patch` / `.diff` 文件（文件名不含 `run_tests`）
- **删除** `run_tests.py`（没有文件就没有名字可匹配）
- 改文件内容但保持文件名不变（只有 diff 内容体现）

而 `t_guard_rejects_baseline_touch`（L1324）测的是"候选目录里放一个名为 `run_tests.txt` 的文件会被拒"——它验证的是启发式本身，不是安全属性。

**注意**：`THREAT_MODEL` 已明示"不防完整权限蓄意 agent"，所以这不构成文档说谎。但 `AGENTS.md`（L350）把 guard 描述为"触碰基准黑名单即否决"，使用者很容易误读为有强制力。

**修复**：解析 unified diff 的 `---`/`+++` 路径与新增/删除标记，对路径做规范化后精确匹配；单独判负"删除基准文件"；无法解析的 diff 形态一律判为"需人工裁决"而非"通过"。

---

## P1-6 retrieve 排序与查询基本无关，links 扩散放大噪声

**位置**：`_rank_entries` L897-914

```python
scored[f.stem] = (kw_hit * 3 + c_hit + e.get("importance", 0) - 0.1 * age_days, ...)   # L906
...
for fid, (s, e, c) in list(scored.items()):
    if s <= 0: continue                    # L909 —— importance≥1 时几乎恒真
    for link in e.get("links", []):        # L910 —— 于是所有条目都向邻居传播
```

两个问题叠加：

1. `importance`（量级 1-10）与命中数（量级 0-3/词）同权相加，**重要度主导排序**；
2. 扩散的前置条件 `s <= 0` 因 `importance ≥ 1` 几乎恒真，等于"每条都把一半分数传给邻居"，与是否命中查询无关。

**实测证据**

```
库：boss(importance=9, links=[ghost]) / ghost(1) / plain(1)，内容互不相干

查询「完全不存在的查询词」→
   8.32  boss    与公司战略无关的备忘
   4.48  ghost   零相关条目          ← 仅因被 boss 链接，凭空 +4.16
   0.32  plain   另一条零相关条目

查询「备忘」→ 12.32 boss / 6.48 ghost / 0.32 plain
```

查询词完全不匹配时依然返回"高分结果"。后果是 `recall@5` 指标虚高（top5 几乎总能撞中），`eval` 基线（L961）与劣化告警（L964-967）因此失去判别力。

**修复**：扩散加前置条件 `if kw_hit or c_hit`；`importance` 归一化后作为小权重 tie-breaker；零命中结果整体过滤（不返回）；把打分函数参数化以便 eval 对比。

---

## P1-7 同一 id 可跨层共存，doctor 看不见

**位置**：`cmd_engine` append L927-933

```python
dest = lib / ("memory/longterm" if e.get("importance",0) >= 7 else "memory/intermediate")   # L927
epath = dest / f"{e['id']}.json"
if epath.exists(): sys.exit(...)   # L930 —— 只查目标层
```

存在性检查只在**目标层**做。同一 id 先以 importance=1 写入 intermediate，再以 importance=9 写入 longterm，两次都放行。

**实测证据**

```
同 id 二次写入成功 → ['memory/intermediate/dup.json', 'memory/longterm/dup.json']
doctor: memory 1 / audit 1 / ledger 1 / 审计链 连续 / state 根一致   ← 报告一切正常
```

`doctor` 的 `mem` 用 `{f.stem}` 去重（L1033）所以察觉不到；`_rank_entries` 用 `scored[f.stem]` 建键（L906），后写者覆盖先写者，检索结果取决于遍历顺序。铁律 1 的"永不覆盖"在这里被绕过（虽然不是同一文件覆盖，但语义上就是同一条目被替换）。

**修复**：按 id 全局查重（扫描 `memory/**`）；若允许"升层"，走 `移 attic + 写新 + 账本` 的显式流程。

---

## P1-8 三条写路径漏刷 Merkle 根，doctor 恒报"根不一致"，自毁信任

`Y-001` 时序纪律（入链 → 入账 → 刷根）在多数路径被遵守，但三处遗漏：

| 路径 | 写入文件 | 位置 | 刷根 |
|---|---|---|---|
| `engine eval` | `evals/baseline.json` | L968 | ❌ |
| `engine reflect` | `memory/reflect/materials-*.md` | L1022 | ❌ |
| `guard --snapshot` | `anchor_snapshot.json` | L1111 | ❌ |

**实测证据**

```
append 后:   doctor: ... 审计链 连续 / state 根一致
eval 后:     doctor: ... 审计链 连续 / state 根不一致（最近写操作未刷根？）
reflect 后:  doctor: ... state 根不一致
```

也就是说：**只用官方命令、不做任何篡改，doctor 就会报"根不一致"**。而 doctor（L1073-1074）的输出是"五态全一致 / 差异等用户裁决"——正常操作被标记成可疑，久而久之人不信这个信号，真正的篡改也就被淹没。

**修复**：抽 `UnitOfWork` / `_commit(lib, action)`，把"入链 + 入账 + 重算根"收敛为唯一出口（见架构建议 D）；或 doctor 维护"已知产物白名单"，把已知生成物与未知变更分开报告。

---

## P1-9 importance 类型未校验 → 崩溃

**位置**：`cmd_engine` L927

```python
dest = lib / ("memory/longterm" if e.get("importance", 0) >= 7 else "memory/intermediate")
```

`validate_entry` 只查字段存在、不查类型；`entry_normalize`（L249-258）只强转了 `keywords`/`links`，漏了数值字段。

**实测**：`importance="9"` → `TypeError: '>=' not supported between instances of 'str' and int`

作者显然知道这个坑（才写了 `entry_normalize` 的"类型强转 v3.7/L-006"），但只补了两个字段。

**修复**：`validate_entry` 加类型校验；`entry_normalize` 扩展为完整 coercion（`importance` → int，`confidence`/`created_at` → 格式校验）。

---

## P1-10 审计链无换行净化，可被注入破坏（且不可修复）

**位置**：`chain_append` L236-237

```python
fh.write(f"- {time.strftime(...)} | prev:{prev or 'genesis'} | h:{h} | {text}\n")
```

`text` 直接拼进格式化行，未做换行转义。实测：

```
engine shadow --text "正常\nabc | prev:genesis | h:000…0 | 伪造事件"
→ 审计文件出现 3 行，其中第 3 行是攻击者完全可控的文本
```

好消息是：伪造行的哈希对不上，`doctor`（L1052-1057）会判"断链"。坏消息是：审计面只追加（铁律 4），**断链无法修复，只能整体移 attic**——一条注入就能废掉整个库的审计真相源。对 RAG/记忆库而言，注入源可以是被检索回来的外部文本。

**修复**：写入前 `text.replace("\n", "\\n").replace("\r", "")`；或直接拒绝含控制字符的输入。

---

## P1-11 verify 覆盖面与"verified"标签不符，且无超时/离线模式

**位置**：`cmd_verify` L592 / L601-603；`t_registry_corrected` L1258

1. **9/33 条题录永远不被对账**：`if not meta.get("arxiv_id"): continue`（L592）。A24/A25/A26/A28/A29-A33 无 arXiv 编号，`cmd_verify` 完全跳过，但它们的 `status` 硬写 `"verified"`。而 `t_registry_corrected`（L1258）断言的正是这个硬写的字符串——测试只是在确认"我把 verified 写进去了"。
2. **"一致"不等于同一篇**：判据是包含关系而非相等（L601-603）：
   ```python
   n_api == n_mine or n_api in n_mine or n_mine in n_api or (first_seg and first_seg in n_mine)
   ```
   题录历史事故（A14 标题作者全错、A28 编号错配）说明这个宽松度是有代价的。
3. **无超时无离线开关**：24 条 ×（2 次尝试 × 15s timeout + 2s 降速）→ 断网时 `run-tests` 会挂 10 分钟以上（本次审查必须给 `_urllib_read` 打桩才能跑完）。

**修复**：无 arXiv 的条目 `status` 改为 `"doc-unverifiable"`（诚实标注可校验性）；给 doc 型条目补 URL 字段并做 HTTP 可达性 + 标题抽取对账；加 `--offline` 与全局超时预算。

---

## P1-12 测试套件非封闭，依赖外部夹具与可变的全局状态

- **依赖真实夹具**：`cmd_install` 系列依赖 CWD 下 `bootstrap_data/bodies.json`（须先跑真实 v2.x 源树的 `absorb`）；`t_l8_guards`（L1411）要求 MUTATION-SOP 正文含 `BENCHMARK`/`否决`；`t_full_render_rule`（L2128）要求 ≥10 个 `install.md`。干净检出只能跑 9 个用例。
- **直接改动全局**：`t_install_requires_bodies`（L1264-1273）重命名真实的 `BODIES_FILE`；多个用例 monkeypatch `urllib.request.urlopen` 与 `DATA_DIR` 后靠 `finally` 手工还原——任何一个用例在 patch 期间失败，后续用例全部被污染。

**修复**：引入 `tests/fixtures/` 合成源树 + pytest fixture 做 setup/teardown；`DATA_DIR` 改依赖注入（见架构建议 A/B）。

---

# P2 · 建议

| # | 问题 | 位置 | 说明 |
|---|---|---|---|
| 13 | **7 项死配置** | `TUNABLES` L82-95 | `broadcast_weights` / `reflect_trigger` / `index_hot_budget` / `eval_n` / `review_intervals` / `merkle_refresh_trigger` / `governance_budget` 代码引用次数为 **0**，却作为"唯一事实源"渲染进 spec。要么实现要么删除，否则公理 A 失真 |
| 14 | **manifest 只有 64bit** | L727 | `hash_algo: "sha256-16"` → 16 hex = 64bit，生日碰撞界 2^32；与 state 里 256bit Merkle 根口径不一致。漂移检测实际只靠 64bit |
| 15 | **Merkle 按文件名排除** | L262-263 | `p.name not in exclude` → 任意层级名为 `state.json` 的文件都被排除，构成藏匿面。另：每次 append 全树 O(n) 重算（`TUNABLES` 已登记"不动手"） |
| 16 | **依赖校验顺序敏感** | L290-296 | `dep not in got and dep not in order` 把模块名与档位名集合比较（恒真），实际判据只剩 `LEVELS[lv]["adds"]` 的声明顺序。顺序写反就误报。应改拓扑排序 |
| 17 | **absorb 静默缺件** | L415-421 | 映射校验只覆盖 `MODULE_MAPPING`/`PACKAGE_MAPPING`，`presets/`、`SKILL.md`、`references/`、`adapters/` 缺失时不报错。实测出现过 `presets=0 docs=0` 却打印"映射路径校验通过" |
| 18 | **absorb-md 静默丢段** | L465-483 | 实测 4 段中 1 段因标题格式不符被丢弃，报告只说"解析 3 条"，无"丢弃 N 段"计数。迁移工具宣称守恒，却没有未解析计数 |
| 19 | **版本号漂移** | L20 vs 文件头 | `VERSION="3.8.1"`，但 docstring 写"v3.8.2 中性化修正"。渲染产物与发布说明版本不一致，而包锚点 `self_hash()` 并不校验版本号 |
| 20 | **build-docs 输出分裂** | L636-655 | `--lib X --out Y` 会把 spec/quickref/citations 写到 Y、AGENTS/README 写到 X；`if lib and out == Path("./dist")` 是死分支（此时 out 已被赋成 `Path(lib)`） |
| 21 | **CRLF 处理不一致** | L726 vs L845-853 | `_deliver` 用 `write_bytes` 防 CRLF（注释里明确说明过），但渲染件用 `write_text` → 同一库跨 Windows/Linux 的 Merkle 根不同，人侧锚点对账会误报 |
| 22 | **memory/ 是未在册盲区** | L780 | `RUNTIME_PREFIX` 含 `memory/`，实测往 `memory/longterm/evil.json` 投文件不被报"未在册"。设计上可理解（条目区是运行时面），但需在文档写明"条目区完整性只由 Merkle 根覆盖" |
| 23 | **doctor 口径含 attic** | L1033 | `mem` 用 `memory.rglob` 含 `attic/` → 已出仓条目仍计入 memory 数，三方对账数字偏大 |
| 24 | **168 条 assert 承载不变式** | L618-622 等 | `python -O` 下全部失效，包括"铁律 6 条""题录状态全 verified"这类治理级断言。应改运行时校验器（见架构建议 C） |
| 25 | **retire 重复记账** | L1077-1086 | 二次执行时 attic 内条目被 `shutil.move` 到自身路径（no-op），但仍计入 `moved` 并重复入账 |

---

# 架构优化探讨

## A. 分层：把"五层压平"拆开，但保住单文件分发

当前单文件里同时住着：数据（REGISTRY/TUNABLES/LAWS，约 185 行）、基础设施（哈希链/Merkle/schema）、渲染器、9 个子命令的领域逻辑、以及 68 个内联测试。函数长度分布印证了这一点：`cmd_engine` 184 行、`cmd_install` 116 行、`cmd_absorb_md` 81 行。

建议切分：

```
sources/    纯数据 + JSON schema（REGISTRY/TUNABLES/LAWS/LEVELS/PACKAGES）
core/       chain.py / merkle.py / schema.py / storage.py / uow.py（加锁与原子写）
render/     spec / quickref / citations / entrypoint / adapter pages
cli/        子命令 → 只做参数解析与用例编排
tests/      pytest + fixtures（独立于产品代码）
```

**单文件体验不必牺牲**：用 `zipapp`/`shiv` 打包成单个可执行文件，或保留一个 `bootstrap_v3.py` 作为 thin launcher。公理 A（单一事实源）不受影响——数据源仍在 `sources/`，反而更适合改成 JSON + schema 校验（现在改一个 tunable 要动 Python 代码并改变 `self_hash()`，见下条）。

**顺带解决一个隐性设计问题**：现在配置与代码共用一个哈希。改 `emotion_decay` 会让 `self_hash()` 变化，进而使人侧抄录的包锚点全部失效。把 `TUNABLES` 分离为可版本化的数据文件后，锚点可以只覆盖"代码 + 铁律"，参数变更走账本留痕。

## B. 错误模型：用异常取代 sys.exit（本次最该先做的重构）

24 处 `sys.exit` 作为库函数出口，是 P0-1 的直接成因，也导致：领域逻辑无法被复用（任何 import 都可能在深处终止进程）、测试无法区分"预期拒绝"与"意外崩溃"。

```
BootstrapError(Exception)          # 基类，带 code + 结构化 detail
├─ SchemaRejected / LawViolation / BaselineTouched / MissingBodies ...
```

领域函数 raise，只有 `cli/` 边界捕获并转 exit code。这一改能同时消掉 P0-1 与 P1-12 的一半。

## C. 不变式分层：把六铁律从"字符串 + assert"升级为运行时校验器

现在 `LAWS`（L97-104）是给人读的中文字符串，机器侧的实现散落在 `validate_entry`、`chain_append`、各处的 `if` 里——**没有单一执行点**，意味着铁律变更要同时改注释、字符串、和多处实现。

建议：

```python
# invariants.py
LAW_1 = lambda ctx: check_no_overwrite(ctx)      # 回退必须移 attic
LAW_2 = lambda ctx: check_evidence_anchor(ctx)   # 证据非空且可追溯
...
def verify_invariants(lib) -> list[Violation]    # 统一入口，结果进 verify_report
```

这样"铁律"才真正成为单一事实源，也让 `assert`（P2-24）退出历史舞台。

## D. 写入路径收敛为 UnitOfWork

P1-8（三处漏刷根）不是疏忽那么简单，而是"入链 → 入账 → 刷根"这段纪律被手抄了 6 遍。抽出来：

```python
with UnitOfWork(lib, action="append") as uow:
    uow.write(entry_path, data)        # 副作用
    uow.chain(f"entry:{eid} → {tier}") # 审计面
    # __exit__ 自动：写 ledger → 重算 merkle_root → 原子替换 state.json
```

铁律 1/4（只追加、不覆盖）与 Y-001 时序就从"靠人记住"变成"结构保证"。配合文件锁（P0-4）可以一次性收口。

## E. 并发模型：先明确，再加固

先回答一个问题：这个库是**单写者**还是**多写者**？

- 若单写者：在 `AGENTS.md` 显式声明，并加 PID/lock 检测，并发时**拒绝**而非默默算错。
- 若多写者：全写路径 `flock` + 临时文件 `os.replace`；`importance_accum` 从 state 移除改为账本重算（消除 lost update 根源，比加锁更彻底）。

## F. 检索层：从裸算术到可插拔 scorer

`_rank_entries` 现在是 `kw×3 + hit + importance − 0.1×age` 的裸算术，无归一化、无阈值、无中文分词（`q.split()` 按空白切词，中文查询退化为整串子串匹配）。建议：

- 打分器接口化（`bm25` / `embedding` / `hybrid`），`broadcast_weights` 这类死参数才有落点；
- `eval` 从"打印 + 可选 exit 2"升级为发布门（CI 里跑，劣化即 fail）；
- `index_hot_budget`、`merkle_refresh_trigger` 要么实现要么删除。

## G. 可证伪性（公理 G）需要机器支撑

公理 G 说"测不出差异即判表演"，但系统里唯一的质量信号是自测——而自测结论被硬编码成 N/N（P0-1）。建议引入 `last_test_run.json`（时间戳 + git rev + 包 sha256 + 逐用例结果 + 耗时），由 `build-docs` 渲染**真实值**，并让 `verify` 检查其新鲜度。否则公理 G 只是一条宣言。

## H. 威胁模型自洽：把 guard 定位说清楚

`THREAT_MODEL` 明示不防"完整权限蓄意 agent"（③档），这一点很诚实。但 `AGENTS.md`（L350）把 guard 写成"触碰基准黑名单即否决"，而实际它是**文件名子串启发式 + 无强制力**。建议文档把 guard 明确定位为"报警 + 强制人工裁决"，并写明其盲区（patch 形态、删除、内容变更）。诚实标注不是缺陷，措辞与能力不匹配才是。

---

# 修复优先级排期

| 阶段 | 内容 | 理由 |
|---|---|---|
| **立刻（1 天）** | P0-1（测试可观测性 + 去掉 N/N 硬编码）、P0-2（证据锚判空 + absorb-md 真实事件）、P0-3（脏目录拒绝 + 写前移 attic） | 三个都是"信任基础设施"级问题：一个让质量信号失真，一个让铁律 2 形同虚设，一个会真丢数据 |
| **一周内** | P0-4（锁 + 派生量重算）、P1-5（guard 路径解析）、P1-6（排序阈值与扩散条件）、P1-7（id 全局查重）、P1-8（UoW 统一刷根） |  correctness 与核心机制正确性 |
| **本迭代** | P1-9~12、P2-13/14/16/17/18/21/22/23 | 类型健壮性、测试封闭性、口径一致性 |
| **架构改造** | 先 B（异常化）→ D（UoW+锁）→ A（分层）→ C（不变式校验器）→ F（检索层） | B 与 D 能同时消掉多个 P0/P1，是性价比最高的切入点；A 在 B/D 完成后做才不会反复搬迁 |

---

# 附：复现方式

```bash
# 1) 构造 v2.x 源树并跑通全链路（需覆盖 MODULE_MAPPING/PACKAGE_MAPPING 全部路径，
#    另需 presets/、SKILL.md、references/、adapters/，否则 absorb 静默缺件）
python3 bootstrap_v3.py absorb v2x
python3 bootstrap_v3.py install L2 --target mylib --yes

# 2) 干净检出下自测中止（第 10 个用例）
rm -rf bootstrap_data && python3 bootstrap_v3.py run-tests; echo "exit=$?"

# 3) 并发丢更新（12 进程 Barrier 对齐 append，importance=5）
#    → importance_accum = 5（期望 60）

# 4) guard 绕过
#    changes.patch 含 "--- a/run_tests.py" → guard 输出「通过」
```

**值得肯定的部分**（避免报告只读起来像批判）：跨月哈希链续接、Merkle 根排除自身持有者、`--redeliver` 显式授权才重交付、`verify` 三态分离（error 不计入通过）、慢车道只拦写操作不拦读操作（N-004）、以及 `THREAT_MODEL` 明示不防 ③ 档——这些都体现了相当克制的设计判断。本次列出的 P0/P1 主要是**工程执行层**的缺口，不是设计方向的错误。
