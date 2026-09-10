# bootstrap_v3.py 修复工单集

- 来源：全量代码审查（2415 行静态通读 + 实际运行验证 + 17 组定向缺陷探针）
- 基线：VERSION=3.8.1，单文件；自测补齐夹具后 67/68 通过
- 工单总数：**33 张**（BUG 25 + ARCH 8）
- 批次：**P0 立即（4）→ P1 一周内（8）→ P2 本迭代（13）→ 架构改造（8）**

## 通用约定

- **分支/提交**：每个工单独立提交，commit message 前缀 `[P0-1]` 这类工单号
- **验收方式**：所有工单必须附新增/修改的自测用例，且通过 `python3 bootstrap_v3.py run-tests`；验收命令在工单内给出
- **回归红线**：任何工单不得降低现有 67 个用例的通过数；不得改变 `LAWS`/`REGISTRY`/`SCHEMA_V3` 的语义（改这些属于慢车道，须人类令牌）
- **注意 P0-1**：在 BUG-001 合入前，`run-tests` 的退出码与"全绿"结论不可信，所有工单的验收都要人工核对实际输出行数

## 优先级总表

| 工单 | 标题 | 级别 | 估时 | 依赖 |
|---|---|---|---|---|
| BUG-001 | 修 `run-tests` 异常捕获 + 去除 N/N 硬编码 | P0 | 0.5d | — |
| BUG-002 | 证据锚判空 + absorb-md 真实事件 id | P0 | 0.5d | — |
| BUG-003 | install 脏目录拒绝 + 写前移 attic | P0 | 1d | — |
| BUG-004 | 写路径加锁 + 派生量改账本重算 | P0 | 1.5d | ARCH-002 |
| BUG-005 | guard 解析 diff 路径而非文件名子串 | P1 | 1d | — |
| BUG-006 | 检索打分阈值 + 扩散前置条件 | P1 | 1d | — |
| BUG-007 | 条目 id 全局查重 | P1 | 0.5d | — |
| BUG-008 | UnitOfWork 统一入链/入账/刷根 | P1 | 1d | ARCH-002 |
| BUG-009 | 字段类型校验与强制转换 | P1 | 0.5d | — |
| BUG-010 | 审计链输入换行净化 | P1 | 0.5d | — |
| BUG-011 | verify 覆盖面诚实化 + 离线/超时 | P1 | 1d | — |
| BUG-012 | 测试套件封闭化（fixtures + 隔离） | P1 | 1d | — |
| BUG-013 | 清理 7 项死配置 | P2 | 0.5d | — |
| BUG-014 | manifest 哈希升至 256bit | P2 | 0.5d | — |
| BUG-015 | Merkle exclude 改相对路径匹配 | P2 | 0.5d | — |
| BUG-016 | resolve 改拓扑排序 | P2 | 0.5d | — |
| BUG-017 | absorb 缺件报告补全 | P2 | 0.5d | — |
| BUG-018 | absorb-md 未解析段计数 | P2 | 0.5d | — |
| BUG-019 | 版本号统一 | P2 | 0.1d | — |
| BUG-020 | build-docs 输出路径语义澄清 | P2 | 0.5d | — |
| BUG-021 | 渲染件落盘统一 write_bytes | P2 | 0.5d | — |
| BUG-022 | 未在册盲区文档化 | P2 | 0.2d | — |
| BUG-023 | doctor 口径排除 attic | P2 | 0.2d | — |
| BUG-024 | assert 迁移为运行时校验器 | P2 | 1d | ARCH-004 |
| BUG-025 | retire 幂等（跳过 attic 内条目） | P2 | 0.2d | — |
| ARCH-001 | 异常体系取代 sys.exit | 架构 | 1.5d | — |
| ARCH-002 | 分层拆包（保留单文件分发） | 架构 | 2d | ARCH-001 |
| ARCH-003 | 六铁律运行时不变式校验器 | 架构 | 1.5d | ARCH-002 |
| ARCH-004 | UnitOfWork + 文件锁 | 架构 | 1.5d | ARCH-002 |
| ARCH-005 | 并发模型显式声明 | 架构 | 0.5d | ARCH-004 |
| ARCH-006 | 检索层可插拔 scorer | 架构 | 2d | BUG-006 |
| ARCH-007 | 测试结果机器化（公理 G 落地） | 架构 | 1d | BUG-001 |
| ARCH-008 | guard 能力边界文档化 | 架构 | 0.3d | BUG-005 |

---

# P0 · 立即修复

## BUG-001 · 修 `run-tests` 异常捕获 + 去除「N/N」硬编码

| 项 | 内容 |
|---|---|
| 级别 | P0 |
| 位置 | `cmd_run_tests` L2377-2383；`render_quickref` L314 |
| 估时 | 0.5d |
| 依赖 | 无（**应最先合入**，否则后续工单的验收信号不可信） |

### 现状

```python
# L2379-2381
for fn in TESTS:
    try: fn(); print(f"  PASS {fn.__name__}")
    except Exception as ex: fails += 1; print(f"  FAIL {fn.__name__}: {ex}")
```

`SystemExit` 继承自 `BaseException`，不被 `except Exception` 捕获。而本文件把 `sys.exit()` 当作唯一错误通道（24 处调用点，覆盖 install / engine / verify / guard / migrate 全部失败路径）。任一未预期退出会导致整轮静默中止：不打印 FAIL、不累计、不打印 `run_tests` 汇总行。

### 复现

```bash
rm -rf bootstrap_data
python3 bootstrap_v3.py run-tests; echo "exit=$?"
```

实测输出：9 个 PASS 后进程退出，无汇总行，`exit=1`。使用者最自然的解读是"差不多都过了"。

### 第二部分（更严重）

```python
# L314
f"---\n*测试：run_tests {tests_n}/{tests_n}（计数由构建注入）*\n"
```

`tests_n` 传入 `len(TESTS)`，分子分母同一变量 → **渲染结果恒为 "68/68"，与实际执行无关**。每个 `install` 生成的库都携带这句未经测量的声明。违反公理 G（可证伪）。

### 修复方案

1. `cmd_run_tests`：
   ```python
   results = []
   for fn in TESTS:
       t0 = time.time()
       try:
           fn(); results.append((fn.__name__, "PASS", "", time.time()-t0))
       except AssertionError as ex:
           results.append((fn.__name__, "FAIL", str(ex), time.time()-t0))
       except SystemExit as ex:
           results.append((fn.__name__, "EXIT", f"意外 sys.exit: {ex}", time.time()-t0))
       except BaseException as ex:
           results.append((fn.__name__, "ERROR", f"{type(ex).__name__}: {ex}", time.time()-t0))
   ```
   汇总行改为打印 `PASS/FAIL/EXIT/ERROR` 四类计数，非零失败时 `sys.exit(1)`；**无论是否异常都必须打印汇总**（用 `try/finally` 或把循环整体包进 `BaseException` 捕获）。
2. 结果落盘 `last_test_run.json`（时间戳 + 包 sha256 + 逐用例结果 + 耗时），供 ARCH-007 与渲染使用。
3. `render_quickref(tests_n)` 改签名为 `render_quickref(last_run: dict | None)`：有真实结果渲染 `测试：62/68（最近一次 2026-09-08，包 sha=xxxx）`；无结果渲染 `测试：未测量（先跑 run-tests）`——**禁止任何形态的 N/N**。

### 验收标准

- [ ] `rm -rf bootstrap_data && run-tests` 打印完整汇总行，退出码 1，不再静默中止
- [ ] 人为在某用例中 `sys.exit("boom")`，该用例被记为 EXIT，后续用例继续执行
- [ ] `render_quickref` 在 `last_test_run.json` 缺失时输出含"未测量"，不含形如 `68/68` 的字符串
- [ ] 新增用例 `t_run_tests_survives_sysexit`：注入一个 `sys.exit` 的临时用例，断言汇总行仍出现且计数正确
- [ ] `t_no_handwritten_counts`（L1242）扩展：断言渲染结果中不存在 `(\d+)/\1` 模式

---

## BUG-002 · 证据锚判空 + absorb-md 使用真实事件 id

| 项 | 内容 |
|---|---|
| 级别 | P0 |
| 位置 | `validate_entry` L244；`cmd_absorb_md` L475、L497、L510、L521；`cmd_engine` doctor L1036 |
| 估时 | 0.5d |

### 现状

```python
# L244
if "evidence" not in e and "source_event_id" not in e: errs.append("无证据锚(铁律2)")
```

只判键存在，不判值。实测 `validate_entry(source_event_id="")` 返回 `[]`，条目成功落盘。

`absorb-md` 放大该缺陷——所有迁移条目统一写死 `"source_event_id": "genesis-v4"`，实测该事件在审计链中不存在。而 `doctor` 用 `entry:(\S+) →` 从审计链提取 id（L1036），**不校验 `source_event_id`**，所以伪造锚点对账不出来。

附带问题：日期无法解析时硬编码改写（L475）：

```python
MON["no_date"].append(eid); date = "2026-09-06"
```

实测源日期 `not-a-date` 的 P-004，入库 `created_at` 变成 `2026-09-06`。在把引文纪律写进铁律的系统里，这是静默伪造。

### 复现

```python
B.validate_entry({... "source_event_id": ""})   # → []（通过）
# absorb-md 后：
#   审计链中是否存在 genesis-v4 事件: False
#   P-004 created_at: 2026-09-06（源为 not-a-date）
```

### 修复方案

1. `validate_entry`：`if not (e.get("evidence") or e.get("source_event_id")):`（判空）
2. `validate_entry` 增加可选强校验（默认开）：`source_event_id` 必须能在 `audit/` 中检索到对应 `entry:` 行，或属于白名单（如 `genesis`）
3. `absorb-md`：
   - 迁移开始前 `h = chain_append(lib/"audit", f"M-00x bulk-import from {src}")`，用该真实哈希回填所有条目的 `source_event_id`
   - 日期无法解析 → 该段**拒绝并计入 `MON["rejected_date"]`**，报告里打印 id 清单；禁止写死日期
4. `doctor` 增加第五项对账：memory 条目的 `source_event_id` 在审计链中不可解析的数量（先只报告，不判负，避免存量库大面积告警）

### 验收标准

- [ ] `validate_entry({... "source_event_id": ""})` 返回含"无证据锚"
- [ ] 新增用例 `t_evidence_empty_rejected`：空/空白/None 证据锚一律拒绝
- [ ] 新增用例 `t_absorb_md_uses_real_event`：迁移后所有条目 `source_event_id` 均能在 `audit/` 中找到对应行
- [ ] 新增用例 `t_absorb_md_bad_date_rejected`：非法日期段进入 `rejected_date` 计数，不静默改写
- [ ] 现有 `t_bulk_import_note`、`t_absorb_md_idempotent` 仍通过

---

## BUG-003 · install 脏目录拒绝 + 写前移 attic

| 项 | 内容 |
|---|---|
| 级别 | P0 |
| 位置 | `cmd_install` L763；`_deliver` L722-726 |
| 估时 | 1d |

### 现状

```python
is_first = not (target / "state.json").exists()   # L763 —— 唯一首装判据
...
dest.write_bytes(data)                            # L726 —— 无条件覆盖
```

若 install 在写 `state.json`（L871）之前中断（磁盘满/权限/Ctrl-C/渲染异常），下次运行被判为"首次安装"，`_deliver` 无条件重写全部交付文件。全过程无备份、无 attic、无事务。违反铁律 1（永不删除/覆盖；回退一律移 attic）。

慢车道（公理 F）只拦 L8/L9 安装与重交付，**真正会破坏数据的这条路径没有护栏**。

### 复现

```
install L2 → 修改 modules/m-core/README.md → 删除 state.json → 重跑 install L2
→ README.md 内容恢复为 "# modules/m-core\n原始 v2.x 正文 A"（用户修改被覆盖）
→ 账本 install 次数: 2
```

### 修复方案

1. 首装判定增强：
   - `state.json` 不存在 且 `target` 非空 → 判为**脏目录**，`sys.exit` 要求显式 `--force`（或先人工清理 / 先 `migrate`）
   - `state.json` 不存在 且 `target` 为空 → 正常首装
2. `_deliver` 写前保护：
   - 目标已存在且内容与待写不同 → 先 `shutil.move` 到 `attic/<YYYYmmdd-HHMMSS>/<rel>`，`_ledger_append(..., "deliver-overwrite", ...)`，再写
   - 目标已存在且内容相同 → 跳过（幂等）
3. 事务标记：首装开始写 `.install-inprogress`（含 pid/ts/level），成功后删除；检测到残留标记即报"上次安装未完成"并指引人工处理

### 验收标准

- [ ] 新增用例 `t_install_dirty_dir_refused`：非空目录无 state.json → 拒绝且提示 `--force`
- [ ] 新增用例 `t_install_no_silent_overwrite`：改过的内容被覆盖前，attic 下出现原文件副本，账本有 `deliver-overwrite` 记录
- [ ] 新增用例 `t_install_inprogress_marker`：模拟中断（写标记后抛异常）→ 重跑报"上次安装未完成"
- [ ] `t_install_l2_smoke`、`t_reinstall_reports_unregistered` 仍通过

---

## BUG-004 · 写路径加锁 + 派生量改由账本重算

| 项 | 内容 |
|---|---|
| 级别 | P0 |
| 位置 | `cmd_engine` append L936-941；wrapup L973-981；retire L1089-1093；reflect-done L1025-1030；`cmd_install` redeliver L826-827 |
| 估时 | 1.5d |
| 依赖 | ARCH-002（异常体系），可与 BUG-008 合并实施 |

### 现状

```python
st = json.loads(st_path.read_text(...))                       # 读
st["importance_accum"] = st.get("importance_accum", 0) + ...  # 改
st_path.write_text(json.dumps(st, ...), ...)                   # 写
```

经典 read-modify-write，全文件无一处 `fcntl` / `msvcrt` / `O_EXCL` / 临时文件 rename。

### 复现

12 进程 `Barrier` 对齐并发 append（每个 importance=5）：

```
importance_accum = 5   （期望 60，丢失 91.7%）
落盘条目数: 12（文件未丢，派生量全丢）
```

`importance_accum` 是反思触发（阈值 50，L984）的唯一输入 → 并发下反思机制静默不触发。`chain_append`（L220-238）是同构 read-then-append，同样无互斥（本次未强制复现断链，但代码无保证）。

### 修复方案

1. **优先做根治项**：`importance_accum` 从 `state.json` 移除，改为从 `ledger/changes.jsonl` 实时重算（`sum` 所有 `action=append` 的 importance，减去 `reflect-done` 之后的累加）。从根上消除 lost update，比加锁更彻底。缓存可选，但必须以账本为真值。
2. **加锁兜底**：所有写路径进入时取排他锁 `lib/.lock`（`fcntl.flock` / `msvcrt.locking`），覆盖"读 state → 写文件 → 入链 → 入账 → 刷根"整段。锁文件不参与 Merkle（加入 exclude）。
3. **原子替换**：`state.json` 统一走"写 `state.json.tmp` + `os.replace`"；`os.replace` 在 POSIX/Windows 均为原子。
4. 锁获取失败（超时 5s）→ 明确报错"库被其他进程占用"，不静默继续。

### 验收标准

- [ ] 新增用例 `t_concurrent_append_no_lost_update`：12 进程并发 append(importance=5)，`importance_accum` 或通过账本重算得 60
- [ ] 新增用例 `t_concurrent_chain_intact`：并发后 doctor 报"审计链 连续"，无断链
- [ ] 新增用例 `t_state_write_atomic`：写 state 过程中被中断（模拟）→ 磁盘上仍是旧值或新值，无半截 JSON
- [ ] 单进程行为不变：`t_ledger_changes`、`t_reflect_trigger`、`t_reflect_done` 通过

---

# P1 · 一周内

## BUG-005 · guard 解析 diff 路径而非文件名子串

| 项 | 内容 |
|---|---|
| 级别 | P1 |
| 位置 | `cmd_guard` L1130-1137；相关文档 `render_entrypoint` L350；`AGENTS.md` 渲染 |
| 估时 | 1d |

### 现状

```python
for p in (d.rglob("*") if d.is_dir() else [d]):
    name = p.name
    if any(b.lower() in name.lower() for b in BASELINE_BLACKLIST):   # L1134
```

只看文件名是否含黑名单子串，不看路径、不看内容、不看 hunk。

### 复现

```
changes.patch 内容：
  --- a/run_tests.py
  +++ b/run_tests.py
  - assert x
  + pass

guard 输出：通过——diff 未触及基准黑名单（9 项）
```

三种常见变异形态全部逃逸：单个 `.patch` 文件、**删除** `run_tests.py`（无文件则无名字）、改内容但保持文件名。

`t_guard_rejects_baseline_touch`（L1324）测的是"目录里放一个名为 `run_tests.txt` 的文件会被拒"——验证的是启发式本身，不是安全属性。

### 修复方案

1. 实现 `_parse_diff_touched(text) -> list[str]`：解析 unified diff 的 `---`/`+++` 头与 `diff --git` 行，抽出路径（去 `a/`、`b/` 前缀），规范化后精确匹配 `BASELINE_BLACKLIST`
2. 对 `.patch`/`.diff` 单文件：读内容后按上述解析，而非看文件名
3. 新增**删除检测**：diff 中出现基准文件路径且 hunk 表明该文件被删除 → 判负
4. 无法解析的 diff 形态 → 输出"需人工裁决"并以 exit 2 结束，**不得输出"通过"**
5. 目录形态仍保留文件名扫描，但作为辅助手段，命中即报"疑似"而非直接判负

### 验收标准

- [ ] 新增用例 `t_guard_patch_form_rejected`：`changes.patch` 含 `--- a/run_tests.py` → 判负
- [ ] 新增用例 `t_guard_deletion_rejected`：diff 表示删除 `l8_guard.py` → 判负
- [ ] 新增用例 `t_guard_unparsable_needs_human`：随机文本 diff → 输出"需人工裁决"，exit 2
- [ ] 新增用例 `t_guard_path_normalized`：`a/b/../../run_tests.py` 归一化后命中
- [ ] `t_guard_rejects_baseline_touch`、`t_guard_anchor` 仍通过

---

## BUG-006 · 检索打分：零命中过滤 + 扩散前置条件

| 项 | 内容 |
|---|---|
| 级别 | P1 |
| 位置 | `_rank_entries` L897-914（关键：L906、L909、L910-914） |
| 估时 | 1d |

### 现状

```python
scored[f.stem] = (kw_hit * 3 + c_hit + e.get("importance", 0) - 0.1 * age_days, ...)   # L906
for fid, (s, e, c) in list(scored.items()):
    if s <= 0: continue                    # L909 —— importance≥1 时几乎恒真
    for link in e.get("links", []):        # L910 —— 于是所有条目都向邻居传播
```

1. `importance`（1-10）与命中数（0-3/词）同权相加 → 重要度主导排序
2. 扩散前置 `s <= 0` 因 `importance ≥ 1` 几乎恒真 → 所有条目都把一半分数传给邻居，与是否命中查询无关

### 复现

```
库：boss(importance=9, links=[ghost]) / ghost(1) / plain(1)，内容互不相干
查询「完全不存在的查询词」→ 8.32 boss / 4.48 ghost / 0.32 plain
```

查询词完全不匹配仍返回高分结果 → `recall@5` 虚高（top5 几乎总能撞中），`eval` 基线（L961）与劣化告警（L964-967）失去判别力。

### 修复方案

1. 扩散加前置：`if not (kw_hit or c_hit): continue`（只有真实命中才扩散）
2. 零命中条目不返回：`if kw_hit == 0 and c_hit == 0: continue`
3. `importance` 归一化后作 tie-breaker：`score = kw_hit*3 + c_hit + min(importance,10)/10 - 0.1*age_days`
4. 打分器抽成函数 `score_entry(e, q, age_days) -> float`，为 ARCH-006 留接口
5. 中文查询：`q.split()` 按空白切词对中文退化为整串匹配，短期改为同时尝试 n-gram（n=2）子串命中

### 验收标准

- [ ] 新增用例 `t_retrieve_zero_hit_filtered`：查询词与全库无关 → 返回空，不返回"高分噪声"
- [ ] 新增用例 `t_retrieve_diffusion_requires_hit`：被高 importance 条目链接但自身零命中的条目，得分不高于同等 importance 的未链接条目
- [ ] 新增用例 `t_retrieve_importance_is_tiebreak`：命中数相同的两条，importance 高者在前；命中数不同时命中多者在前
- [ ] 跑 `engine eval`，记录修复前后 `recall@5`/`MRR`，在工单中注明指标变化（允许下降——这是判别力恢复的证据）
- [ ] `t_retrieve_keywords_boost`、`t_eval_retrieval`、`t_eval_degradation` 仍通过

---

## BUG-007 · 条目 id 全局查重

| 项 | 内容 |
|---|---|
| 级别 | P1 |
| 位置 | `cmd_engine` append L927-933；`doctor` L1033；`_rank_entries` L906 |
| 估时 | 0.5d |

### 现状

```python
dest = lib / ("memory/longterm" if e.get("importance",0) >= 7 else "memory/intermediate")   # L927
epath = dest / f"{e['id']}.json"
if epath.exists(): sys.exit(...)   # L930 —— 只在目标层查
```

同 id 先以 importance=1 写 intermediate、再以 importance=9 写 longterm，两次均放行。

### 复现

```
同 id 二次写入成功 → ['memory/intermediate/dup.json', 'memory/longterm/dup.json']
doctor: memory 1 / audit 1 / ledger 1 / 审计链 连续 / state 根一致   ← 报告一切正常
```

`doctor` 的 `mem` 用 `{f.stem}` 去重 → 察觉不到；`_rank_entries` 用 `scored[f.stem]` 建键 → 后写者覆盖先写者，结果取决于遍历顺序。语义上等同"同一条目被替换"，绕过铁律 1。

### 修复方案

1. append 前扫描 `lib/"memory"/**/`，按 id 全局查重（可维护 `memory/.index.json` 加速，但需纳入 Merkle 与 doctor 对账）
2. 命中重复 → 拒绝并提示"条目已存在于 <层>；升层请走显式流程"
3. 若需要支持升层：实现 `engine promote --id X`（移 attic 旧副本 + 写新层 + 账本 + 审计链）
4. `doctor` 增加检测：同一 stem 出现在多个层 → 报 [id 冲突]

### 验收标准

- [ ] 新增用例 `t_append_dup_across_tier_rejected`：同 id 跨层写入被拒
- [ ] 新增用例 `t_doctor_detects_id_conflict`：手工构造跨层同 id 文件 → doctor 报 [id 冲突]
- [ ] `t_append_rejects_dup_id`（L1892）仍通过（同层重复）

---

## BUG-008 · UnitOfWork 统一「入链 → 入账 → 刷根」

| 项 | 内容 |
|---|---|
| 级别 | P1 |
| 位置 | 漏刷点：`eval` L968、`reflect` L1022、`guard --snapshot` L1111；已刷点：append L934-941、wrapup L978-980、retire L1087-1092、reflect-done L1027-1029 |
| 估时 | 1d |
| 依赖 | ARCH-002 |

### 现状

`Y-001` 时序纪律（入链 → 入账 → 刷根）被手抄 6 遍，其中 3 处遗漏：

| 路径 | 写入 | 位置 | 刷根 |
|---|---|---|---|
| `engine eval` | `evals/baseline.json` | L968 | ❌ |
| `engine reflect` | `memory/reflect/materials-*.md` | L1022 | ❌ |
| `guard --snapshot` | `anchor_snapshot.json` | L1111 | ❌ |

### 复现

```
append 后:   doctor: ... 审计链 连续 / state 根一致
eval 后:     doctor: ... state 根不一致（最近写操作未刷根？）
reflect 后:  doctor: ... state 根不一致
```

**只用官方命令、不做任何篡改，doctor 就报"根不一致"**。而 doctor 输出是"五态全一致 / 差异等用户裁决"——正常操作被标记成可疑，长期看会摧毁这个信号的公信力，真正的篡改反而被淹没。

### 修复方案

```python
class UnitOfWork:
    def __init__(self, lib, action): ...
    def write(self, path, data): ...          # 副作用（写前按 BUG-003 保护）
    def chain(self, text): ...                # 审计面
    def __enter__/__exit__:                   # __exit__ 自动：写 ledger → 重算 merkle_root → 原子替换 state.json
```

- 所有 7 条写路径改为 `with UnitOfWork(lib, "eval") as uow:`
- 配合 BUG-004 的锁与原子替换
- 铁律 1/4（只追加、不覆盖）与 Y-001 时序从"靠人记住"变成结构保证

### 验收标准

- [ ] 新增用例 `t_all_writes_refresh_root`：依次执行 install/append/wrapup/eval/reflect/reflect-done/retire/shadow/guard-snapshot，每步后 doctor 报"根一致"
- [ ] 新增用例 `t_uow_ledger_ordering`：每个写操作的账本行时间戳不早于审计链行
- [ ] `t_root_refresh_on_write`（L1586）、`t_ledger_changes` 仍通过

---

## BUG-009 · 字段类型校验与强制转换

| 项 | 内容 |
|---|---|
| 级别 | P1 |
| 位置 | `cmd_engine` L927；`entry_normalize` L249-258 |
| 估时 | 0.5d |

### 现状

`validate_entry` 只查字段存在、不查类型；`entry_normalize` 只强转了 `keywords`/`links`（v3.7/L-006）。

实测 `importance="9"` → `TypeError: '>=' not supported between instances of 'str' and int`（L927）。作者知道这个坑（才写了 L-006），但只补了 2 个字段。

### 修复方案

1. `validate_entry` 增加类型校验：`importance` 必须 int/float 或可转数字；`created_at`/`updated_at` 必须匹配 `^\d{4}-\d{2}-\d{2}`；`validity` 必须 dict；`content` 必须 str
2. `entry_normalize` 扩展为完整 coercion：`importance` → int（越界截断到 0-10），`keywords`/`links` → list[str]，`confidence` → 枚举归一
3. 字段类型校验纳入 `SCHEMA_V3` 的声明式定义（建议改为 `{name: type}` 或 dataclass），避免"字段清单"与"校验规则"两处维护

### 验收标准

- [ ] 新增用例 `t_importance_str_coerced`：`"9"` 被转为 9 并落到 longterm，不崩溃
- [ ] 新增用例 `t_bad_type_rejected`：importance={} / created_at="昨天" → 拒绝并给出字段级错误信息
- [ ] 新增用例 `t_entry_normalize_types`（L2250）扩展覆盖 importance/validity
- [ ] `t_large_entry`、`t_append_max_bytes` 仍通过

---

## BUG-010 · 审计链输入换行净化

| 项 | 内容 |
|---|---|
| 级别 | P1 |
| 位置 | `chain_append` L236-237 |
| 估时 | 0.5d |

### 现状

```python
fh.write(f"- {time.strftime(...)} | prev:{prev or 'genesis'} | h:{h} | {text}\n")
```

`text` 直接拼入格式化行，未做换行转义。

### 复现

```
engine shadow --text "正常\nabc | prev:genesis | h:000…0 | 伪造事件"
→ 审计文件出现 3 行，第 3 行完全由输入控制
```

`doctor`（L1052-1057）会判"断链"（伪造行哈希对不上）。但审计面只追加（铁律 4）→ **断链无法修复，只能整体移 attic**。一条注入即可废掉整个库的审计真相源。对记忆库而言，注入源可能是被检索回来的外部文本。

### 修复方案

1. `chain_append` 入口净化：`text.replace("\\", "\\\\").replace("\n", "\\n").replace("\r", "")`，并拒绝/替换其他控制字符
2. 或：拒绝含 `\n`/`\r`/`\x00` 的输入（`raise`），由调用方负责单行化
3. `engine shadow` 与 `append` 的 `text`/`content` 入口同样净化
4. 存量库：提供 `doctor --fix-chain-note` 只报告不修（修违反铁律 4）

### 验收标准

- [ ] 新增用例 `t_chain_newline_neutralized`：含 `\n` 的文本入链后，审计文件行数仅 +1，且该行可被 `prev/h` 正则完整解析
- [ ] 新增用例 `t_chain_injection_detected`：注入伪造行后 doctor 报断链（现状行为，固化为回归保护）
- [ ] `t_chain_and_cross_month`、`t_cross_month_real`、`t_doctor_chain_check` 仍通过

---

## BUG-011 · verify 覆盖面诚实化 + 离线/超时

| 项 | 内容 |
|---|---|
| 级别 | P1 |
| 位置 | `cmd_verify` L592、L601-603；`t_registry_corrected` L1258 |
| 估时 | 1d |

### 现状

1. **9/33 条题录永不被对账**：`if not meta.get("arxiv_id"): continue`（L592）。A24/A25/A26/A28/A29-A33 无 arXiv 编号被完全跳过，但 `status` 硬写 `"verified"`；`t_registry_corrected`（L1258）断言的正是这个硬写字符串——测试只确认"我把 verified 写进去了"
2. **"一致"不等于同一篇**：判据是包含关系而非相等（L601-603）
3. **无超时无离线开关**：24 条 ×（2 次尝试 × 15s + 2s 降速）→ 断网时 `run-tests` 挂 10 分钟以上（本次审查必须给 `_urllib_read` 打桩才能跑完）

### 修复方案

1. 无 arXiv 的条目 `status` 改为 `"doc-unverifiable"`，并在渲染的 `citations.md`/`spec.md` 中标注"可校验性"而非笼统 verified
2. doc 型条目补 `url` 字段，实现 HTTP 可达性 + `<title>` 抽取对账（与 arXiv 路径共用三态分离）
3. 加 `--offline`（跳过全部网络对账，报告标记 `未对账`）与 `--timeout-budget N`（总秒数预算，超预算剩余条目标 `未对账`）
4. 判据收紧：主判据改相等，包含关系降级为"近似-需人工确认"输出
5. `t_registry_corrected` 改为断言"覆盖范围"（所有条目要么有 arXiv 要么有可校验 url）而非断言字符串

### 验收标准

- [ ] 新增用例 `t_verify_covers_all_entries`：33 条全部进入对账流程并有三态结果，无 `continue` 跳过
- [ ] 新增用例 `t_verify_status_honest`：无 arXiv 且无 url 的条目 status 为 `doc-unverifiable`
- [ ] 新增用例 `t_verify_offline_mode`：`--offline` 下 0 次网络调用，全部标记"未对账"，累计耗时 < 2s
- [ ] 新增用例 `t_verify_timeout_budget`：预算 5s 时不超时退出，剩余条目如实标记
- [ ] `t_verify_exit_codes`、`t_verify_overrides_applied`、`t_absorb_overrides_loop` 仍通过

---

## BUG-012 · 测试套件封闭化（fixtures + 状态隔离）

| 项 | 内容 |
|---|---|
| 级别 | P1 |
| 位置 | `t_install_requires_bodies` L1264-1273；`t_l8_guards` L1411；`t_full_render_rule` L2128；多处 monkeypatch |
| 估时 | 1d |
| 依赖 | BUG-001（先让失败可见） |

### 现状

- **依赖真实夹具**：`cmd_install` 系列依赖 CWD 下 `bootstrap_data/bodies.json`（须先跑真实 v2.x 源树的 absorb）；`t_l8_guards` 要求 MUTATION-SOP 正文含 `BENCHMARK`/`否决`；`t_full_render_rule` 要求 ≥10 个 `install.md`。干净检出只能跑 9 个用例
- **污染全局状态**：`t_install_requires_bodies` 重命名真实 `BODIES_FILE`；多个用例 monkeypatch `urllib.request.urlopen` 与 `DATA_DIR` 后靠 `finally` 手工还原——任一用例在 patch 期间失败，后续全部被污染

### 修复方案

1. `tests/fixtures/make_v2x_tree(dst)` 合成最小 v2.x 源树（覆盖 MODULE_MAPPING/PACKAGE_MAPPING 全部路径 + presets + SKILL.md + references + adapters + L8/L9 各 ≥5 个 install.md + MUTATION-SOP 含 BENCHMARK/否决）
2. 每个用例用 `with isolated_env() as env:` 上下文：自动切 `DATA_DIR` 到 tmp、还原所有 monkeypatch（用 `unittest.mock.patch` 或自写 registry）
3. 禁止用例直接操作真实的 `bootstrap_data/`；`run-tests` 启动时断言未在真实数据目录上运行
4. CI 加一条：clean checkout 直接 `run-tests` 必须跑到 100% 用例（不再止步第 9 个）

### 验收标准

- [ ] `rm -rf bootstrap_data` 后 `run-tests` 能跑完全部用例（不再第 10 个中止）
- [ ] 用例可乱序执行（`--shuffle` 或手工打乱 `TESTS` 顺序）结果一致
- [ ] 单个用例失败不影响后续用例（人为让第 5 个用例 monkeypatch 后抛异常，后续仍正常）
- [ ] 新增用例 `t_tests_are_hermetic`：断言测试运行期间真实 `bootstrap_data/` 未被创建/修改

---

# P2 · 本迭代

## BUG-013 · 清理 7 项死配置

| 项 | 内容 |
|---|---|
| 级别 | P2 |
| 位置 | `TUNABLES` L82-95 |
| 估时 | 0.5d |

`broadcast_weights` / `reflect_trigger` / `index_hot_budget` / `eval_n` / `review_intervals` / `merkle_refresh_trigger` / `governance_budget` —— 代码引用次数均为 **0**，却作为"唯一事实源"渲染进 spec。公理 A 失真。

**方案**：逐项二选一 —— 实现（给 owner 明确落点，如 `broadcast_weights` 落到 ARCH-006 scorer）或删除并在 RELEASE.md 登记删除理由。保留者必须有至少一个读取点，用测试锁定。

**验收**：新增用例 `t_no_dead_tunables`：遍历 `TUNABLES`，断言每项在代码中至少被读取 1 次（正则扫描源码，白名单除外）。

---

## BUG-014 · manifest 哈希升至 256bit

| 项 | 内容 |
|---|---|
| 级别 | P2 |
| 位置 | `_deliver` L727；`cmd_install` L777、L813、L817、L821 |
| 估时 | 0.5d |

`hash_algo: "sha256-16"` → 16 hex = 64bit，生日碰撞界 2^32；与 state 中 256bit Merkle 根口径不一致。漂移检测实际只靠 64bit。

**方案**：升为完整 sha256，manifest 增加 `hash_algo: "sha256"` 与 `schema_version`；提供 `install --migrate-manifest` 对存量库重算并记账（旧 manifest 移 attic）。所有读写点统一走 `_manifest_digest(data)` helper。

**验收**：新增用例 `t_manifest_full_256`：manifest 中每个值为 64 hex；篡改单字节必被漂移检测捕获（构造 64bit 前缀相同的内容验证不再误判为一致——可用 mock hash 前缀验证）。

---

## BUG-015 · Merkle exclude 改相对路径匹配

| 项 | 内容 |
|---|---|
| 级别 | P2 |
| 位置 | `merkle_root` L262-263 |
| 估时 | 0.5d |

`p.name not in exclude` → 任意层级名为 `state.json` 的文件都被排除，构成藏匿面（在 `modules/` 下放一个 `state.json` 即可逃出根的计算）。

**方案**：改为按相对 root 的 POSIX 路径精确匹配（`str(p.relative_to(root)) not in exclude`），exclude 相应改为路径集合 `{"state.json", ".lock"}`。另：每次 append 全树 O(n) 重算（`TUNABLES` 已登记"不动手"），本工单只做口径修正，性能优化归 ARCH-006 后续。

**验收**：新增用例 `t_merkle_exclude_is_path_scoped`：`modules/state.json` 参与根计算（修改它根会变），root 下 `state.json` 仍被排除。

---

## BUG-016 · resolve 改拓扑排序

| 项 | 内容 |
|---|---|
| 级别 | P2 |
| 位置 | `resolve` L290-296；`detect_cycle` L270-283 |
| 估时 | 0.5d |

`if dep not in got and dep not in order` 把模块名（`m-evolve`）与档位名集合（`L0..Ln`）比较 → 恒真，实际判据只剩 `LEVELS[lv]["adds"]` 的声明顺序。顺序写反就误报。

**方案**：对 `DEPS` 做 Kahn 拓扑排序，返回拓扑序模块清单；`detect_cycle` 保留作为前置门（已实现三色 DFS，可直接复用）。`LEVELS[lv]["adds"]` 仅作为"本档新增"的声明，不再隐含顺序语义。

**验收**：新增用例 `t_resolve_order_independent`：打乱 `LEVELS[*]["adds"]` 顺序，resolve 结果集合与依赖满足性不变；新增用例 `t_resolve_missing_dep_reported`：声明依赖但未包含在档位内 → 报"缺依赖"（现状恒真分支无法覆盖）。

---

## BUG-017 · absorb 缺件报告补全

| 项 | 内容 |
|---|---|
| 级别 | P2 |
| 位置 | `cmd_absorb` L415-421 |
| 估时 | 0.5d |

映射校验只覆盖 `MODULE_MAPPING`/`PACKAGE_MAPPING`；`presets/`、`SKILL.md`、`references/`、`adapters/` 缺失时不报错。实测出现过 `presets=0 docs=0` 却打印"映射路径校验通过"。

**方案**：把 `presets/`、`SKILL.md`、`references/`、`adapters/` 加入必检清单；缺失时与 MODULE_MAPPING 同等处理（列清单并 exit）。增加 `--allow-missing <slots>` 供部分源树场景显式豁免，豁免须入账本。

**验收**：新增用例 `t_absorb_reports_missing_presets`：源树无 presets/ → 报错并列出；新增用例 `t_absorb_allow_missing_ledgered`：`--allow-missing presets` 时通过且账本有记录。

---

## BUG-018 · absorb-md 未解析段计数

| 项 | 内容 |
|---|---|
| 级别 | P2 |
| 位置 | `cmd_absorb_md` L465-483（`_parse`） |
| 估时 | 0.5d |

实测 4 段中 1 段因标题格式不符被丢弃，报告只说"解析 3 条"，无"丢弃 N 段"计数。迁移工具宣称守恒却没有未解析计数。

**方案**：`MON` 增加 `unparsed_blocks`（无法匹配 `### <prefix>-N / date / title` 的 `###` 段落数）与 `unparsed_lines`；报告强制打印；守恒校验 `源 ### 段数 == parsed + skipped_template + unparsed`。

**验收**：新增用例 `t_absorb_md_conservation`：构造含 2 个畸形段的输入，断言 `parsed + skipped_template + unparsed = 源段数` 且报告含"未解析"。

---

## BUG-019 · 版本号统一

| 项 | 内容 |
|---|---|
| 级别 | P2 |
| 位置 | `VERSION` L20 vs 文件头 docstring |
| 估时 | 0.1d |

`VERSION="3.8.1"`，docstring 提及"v3.8.2 中性化修正"。渲染产物与发布说明版本不一致，而 `self_hash()` 不校验版本。

**方案**：统一为 3.8.2（若确实是 3.8.2）；把版本号纳入 verify 的静态不变式（与 RELEASE.md 首行/最新条目比对）。

**验收**：新增用例 `t_version_consistent`：VERSION 与 docstring/RELEASE.md 提及的最新版本一致。

---

## BUG-020 · build-docs 输出路径语义澄清

| 项 | 内容 |
|---|---|
| 级别 | P2 |
| 位置 | `cmd_build` L636-655 |
| 估时 | 0.5d |

`--lib X --out Y` 会把 spec/quickref/citations 写到 Y、AGENTS/README 写到 X，输出分裂；`if lib and out == Path("./dist")`（L642）是死分支（此时 out 已被赋成 `Path(lib)`）。

**方案**：明确两种模式 —— (a) 打包模式：仅 `--out`，渲染三件套；(b) 库刷新模式：仅 `--lib`，渲染三件套 + AGENTS/README + 刷 state。同时给 `--out` 和 `--lib` → 报错要求二选一，或引入 `--out` 表示"库刷新时额外另存一份"。删除死分支。

**验收**：新增用例 `t_build_docs_out_lib_exclusive`；`t_build_docs_lib_default_out`、`t_build_docs_lib_nostate`、`t_build_docs_refreshes_render` 仍通过。

---

## BUG-021 · 渲染件落盘统一 write_bytes

| 项 | 内容 |
|---|---|
| 级别 | P2 |
| 位置 | `_deliver` L726（`write_bytes`）vs `cmd_install` L845-853、`cmd_build` L639-641（`write_text`） |
| 估时 | 0.5d |

代码注释已明确"write_text 在 Windows 写 CRLF，与 LF 哈希记账天生不符"（L742、L748），但只有部分路径修了。同一库跨 Windows/Linux 的 Merkle 根不同 → 人侧锚点对账误报。

**方案**：统一 helper `_write_text_deterministic(path, text)` → `path.write_bytes(text.encode("utf-8"))` 且确保 text 内部为 `\n`；全量替换 `write_text`（除账本/审计链的 append 场景，那里换行由写入内容决定）。

**验收**：新增用例 `t_render_newlines_are_lf`：所有渲染产物落盘后不含 `\r\n`；新增用例 `t_root_stable_across_write_paths`：在 `newline="\r\n"` 模式下重新渲染，根不变。

---

## BUG-022 · 未在册盲区文档化

| 项 | 内容 |
|---|---|
| 级别 | P2 |
| 位置 | `RUNTIME_PREFIX` L780；`render_readme` L376 |
| 估时 | 0.2d |

`RUNTIME_PREFIX` 含 `memory/` → 实测往 `memory/longterm/evil.json` 投文件不被报"未在册"。设计上可理解（条目区是运行时面），但未声明。

**方案**：在 `README.md`/`spec.md` 明确"条目区完整性只由 Merkle 根覆盖，不在未在册检测范围内"；可选：对 `memory/` 下非 `.json` 文件仍报未在册。

**验收**：文档断言用例 `t_readme_declares_memory_scope`。

---

## BUG-023 · doctor 口径排除 attic

| 项 | 内容 |
|---|---|
| 级别 | P2 |
| 位置 | `doctor` L1033 |
| 估时 | 0.2d |

`mem` 用 `memory.rglob` 含 `attic/` → 已出仓条目仍计入 memory 数，三方对账数字偏大，且"attic 有而 memory 无"这类差异被掩盖。

**方案**：`mem` 排除 `attic/`；单独统计 `attic_n` 并在输出中列出，作为"已出仓"信息而非差异项。

**验收**：新增用例 `t_doctor_excludes_attic`：retire 后 doctor 的 memory 数下降，attic 数上升，不产生 `audit 有而 memory 无` 差异。

---

## BUG-024 · assert 迁移为运行时校验器

| 项 | 内容 |
|---|---|
| 级别 | P2 |
| 位置 | L618-622（`cmd_verify` 内的静态不变式）等；全文件 168 条 assert |
| 估时 | 1d |
| 依赖 | ARCH-004 |

`python -O` 下全部 assert 失效，包括"铁律 6 条""题录状态全 verified""宪章含 objective hacking"这类治理级断言。

**方案**：把治理级断言迁到 `invariants.py`（见 ARCH-004），`verify` 调用后输出结构化 `Violation` 列表并影响退出码；性能敏感的内部断言可保留。

**验收**：新增用例 `t_invariants_survive_O_flag`：以 `python -O` 运行 `verify`，治理级不变式仍被检查（可通过子进程调用验证）。

---

## BUG-025 · retire 幂等

| 项 | 内容 |
|---|---|
| 级别 | P2 |
| 位置 | `retire` L1077-1086 |
| 估时 | 0.2d |

二次执行时 attic 内条目被 `shutil.move` 到自身路径（no-op），但仍计入 `moved` 并重复入账。

**方案**：遍历时跳过 `memory/attic/` 下的文件；`moved` 只计真实移动。

**验收**：新增用例 `t_retire_idempotent`：连续两次 retire，第二次 `moved=0` 且账本无新增 retire 记录（或记录 moved=0）。`t_retire_ttl` 仍通过。

---

# 架构改造

## ARCH-001 · 异常体系取代 sys.exit

| 项 | 内容 |
|---|---|
| 级别 | 架构（**建议最先做**） |
| 估时 | 1.5d |
| 依赖 | 无 |

**动机**：24 处 `sys.exit` 作为库函数出口，是 BUG-001 的直接成因，也导致领域逻辑无法复用（任何 import 都可能在深处终止进程）、测试无法区分"预期拒绝"与"意外崩溃"。

**方案**：

```
BootstrapError(Exception)            # 基类：code + 结构化 detail + 面向人的消息
├─ SchemaRejected(LawViolation)
├─ LawViolation(law_no, ctx)
├─ BaselineTouched(paths)
├─ MissingBodies(slots)
├─ DirtyTarget(path)
├─ AlreadyExists(id, tier)
├─ ChainIntegrityError(...)
├─ NeedsHumanAdjudication(reason)
```

领域函数一律 `raise`；只有 `cli/` 边界（`__main__` 分发处）捕获并转 exit code：`BootstrapError → 1`，`NeedsHumanAdjudication → 2`，未预期异常 → 3 + traceback。

**验收**：无一处领域函数（非 `cmd_*` 的 cli 层）直接调用 `sys.exit`；新增用例 `t_errors_are_structured`：每类错误可被 `except` 捕获且带 code；BUG-001 的 EXIT 类型归零。

---

## ARCH-002 · 分层拆包（保留单文件分发）

| 项 | 内容 |
|---|---|
| 级别 | 架构 |
| 估时 | 2d |
| 依赖 | ARCH-001 |

**动机**：单文件里同时住着数据（约 185 行）、基础设施、渲染器、9 个子命令领域逻辑、68 个内联测试。函数长度印证：`cmd_engine` 184 行、`cmd_install` 116 行、`cmd_absorb_md` 81 行。

**目标结构**：

```
sources/    纯数据 + JSON schema（REGISTRY/TUNABLES/LAWS/LEVELS/PACKAGES）
core/       chain.py / merkle.py / schema.py / storage.py / uow.py / invariants.py / lock.py
render/     spec / quickref / citations / entrypoint / adapter pages / installer pages
cli/        子命令：只做参数解析与用例编排
tests/      pytest + fixtures（独立于产品代码）
bootstrap_v3.py   thin launcher（或 zipapp/shiv 打包成单文件可执行）
```

**关键收益（顺带解决一个隐性设计问题）**：现在配置与代码共用一个哈希——改 `emotion_decay` 会让 `self_hash()` 变化，进而使人侧抄录的包锚点全部失效。把 `TUNABLES` 分离为可版本化的数据文件后，锚点可以只覆盖"代码 + 铁律"，参数变更走账本留痕。

**约束**：公理 A（单一事实源）不受影响——数据源仍在 `sources/`，改为 JSON + schema 校验后反而更严格。单文件体验用 `zipapp`/`shiv` 保住。

**验收**：`python -m zipapp` 产出的单文件可通过现有全部用例；`self_hash()` 语义文档化（明确覆盖哪些文件，不含 `sources/tunables.json`）。

---

## ARCH-003 · 六铁律运行时不变式校验器

| 项 | 内容 |
|---|---|
| 级别 | 架构 |
| 估时 | 1.5d |
| 依赖 | ARCH-002 |

**动机**：`LAWS`（L97-104）是给人读的中文字符串，机器侧实现散落在 `validate_entry`、`chain_append`、各处 `if` —— **没有单一执行点**。铁律变更要同时改注释、字符串和多处实现。

**方案**：

```python
# invariants.py
LAWS: dict[int, Invariant]
# 1: 不覆盖 —— 写前目标存在则必须移 attic 且账本有记录
# 2: 证据准入 —— source_event_id/evidence 非空且可追溯
# 3: 凡引用给出处 —— content 含他人观点时必须有 REGISTRY id
# 4: 审计面只追加 —— 链连续、跨月首行 prev 正确
# 5: 永不存密钥 —— 密钥模式扫描
# 6: 慢车道 —— live 工具/宪章/laws 变更须令牌；自动变更仅限声明级

def verify_invariants(lib) -> list[Violation]   # 统一入口
```

`cmd_verify` 调用后输出结构化结果并入 `verify_report.json`，治理级违反影响退出码。同时替换 BUG-024 中的 assert。

**验收**：每条铁律至少 1 个"违反必被检出"的用例（构造违反场景）；`verify` 输出包含 6 条铁律的逐条状态。

---

## ARCH-004 · UnitOfWork + 文件锁

| 项 | 内容 |
|---|---|
| 级别 | 架构 |
| 估时 | 1.5d |
| 依赖 | ARCH-002 |

把 BUG-008（统一时序）与 BUG-004（加锁/原子写）收敛为同一套基础设施：

```python
with UnitOfWork(lib, action="append") as uow:   # __enter__ 取锁
    uow.write(path, data)      # 副作用，写前按铁律1保护
    uow.chain("entry:X → tier")  # 审计面
# __exit__：写 ledger → 重算 merkle_root → os.replace 原子替换 state.json → 放锁
```

铁律 1/4 与 Y-001 时序从"靠人记住"变成"结构保证"。锁文件进入 Merkle exclude（配合 BUG-015 的路径级 exclude）。

**验收**：7 条写路径全部改走 UoW；`t_all_writes_refresh_root` 与 `t_concurrent_*` 全绿。

---

## ARCH-005 · 并发模型显式声明

| 项 | 内容 |
|---|---|
| 级别 | 架构 |
| 估时 | 0.5d |
| 依赖 | ARCH-004 |

先回答：这个库是**单写者**还是**多写者**？

- **单写者**：在 `AGENTS.md`/`spec.md` 显式声明；append 时检测并发（PID/lock 文件）并**拒绝**，而非默默算错
- **多写者**：全写路径 flock + `os.replace`；`importance_accum` 从 state 移除改为账本重算（消除 lost update 根源，比加锁更彻底）

无论哪种，都要写进文档并有用例锁定行为。

**验收**：spec/AGENTS 含并发模型章节；新增用例验证所选模型下的行为（单写者 → 并发被拒；多写者 → 并发正确）。

---

## ARCH-006 · 检索层可插拔 scorer

| 项 | 内容 |
|---|---|
| 级别 | 架构 |
| 估时 | 2d |
| 依赖 | BUG-006 |

**动机**：`_rank_entries` 是 `kw×3 + hit + importance − 0.1×age` 的裸算术，无归一化、无阈值、无中文分词（`q.split()` 按空白切词，中文退化为整串子串匹配）。

**方案**：

- scorer 接口化：`bm25` / `embedding` / `hybrid`，让 `broadcast_weights`（现为死配置）有落点
- 中文分词：引入轻量切分（jieba 或 2-gram 倒排）
- `eval` 从"打印 + 可选 exit 2"升级为发布门（CI 中运行，劣化即 fail），基线入库 `evals/baseline.json` 并纳入版本控制
- `index_hot_budget`、`merkle_refresh_trigger` 要么实现要么删除（关联 BUG-013）
- 增量 Merkle（现全树 O(n)）：按 `merkle_refresh_trigger` 阈值触发增量哈希树

**验收**：至少 2 个可切换 scorer；`engine eval` 在 CI 中可作为门；中文查询 recall@5 有 measurable 提升（记录修复前后数值）。

---

## ARCH-007 · 测试结果机器化（公理 G 落地）

| 项 | 内容 |
|---|---|
| 级别 | 架构 |
| 估时 | 1d |
| 依赖 | BUG-001 |

公理 G 说"测不出差异即判表演"，但系统里唯一的质量信号是自测——而自测结论被硬编码成 N/N。

**方案**：

- `last_test_run.json`：时间戳 + 包 sha256 + git rev + 逐用例结果 + 耗时 + Python 版本
- `build-docs` 渲染**真实值**（含"最近一次运行时间"），无法取得时渲染"未测量"
- `verify` 检查新鲜度：包 sha256 与当前不符 → 警告"测试结论已过期"
- `engine shadow`（公理 G 的落地工具）产出的影子日志应可被 `eval` 消费，形成"预演 → 测量 → 判决"闭环

**验收**：新增用例 `t_render_uses_real_test_result`；修改任一测试用例使其失败后，渲染产物中的计数随之变化。

---

## ARCH-008 · guard 能力边界文档化

| 项 | 内容 |
|---|---|
| 级别 | 架构 |
| 估时 | 0.3d |
| 依赖 | BUG-005 |

`THREAT_MODEL` 明示不防"完整权限蓄意 agent"（③档），这一点很诚实。但 `AGENTS.md`（L350）把 guard 写成"触碰基准黑名单即否决"，而实际是**文件名子串启发式 + 无强制力**。

**方案**：文档把 guard 明确定位为"报警 + 强制人工裁决"，写明盲区（patch 形态、删除、内容变更）与不防场景（③档）。诚实标注不是缺陷，**措辞与能力不匹配才是**。

**验收**：`AGENTS.md`/`spec.md` 渲染结果含 guard 能力边界段；新增用例 `t_docs_declare_guard_limits`。

---

# 执行顺序建议

```
第一批（信任基础设施，1 个工作日）
  BUG-001 → BUG-002 → BUG-003
  ↑ 先合入 BUG-001，否则后续所有验收信号不可信

第二批（正确性，1 周）
  ARCH-001（异常化）→ ARCH-002（分层）
  → BUG-004 + BUG-008 合并为 ARCH-004（UoW + 锁）
  → BUG-005 / BUG-006 / BUG-007 / BUG-009 / BUG-010 / BUG-011 / BUG-012

第三批（一致性与健壮性，本迭代）
  BUG-013 ~ BUG-025

第四批（架构演进）
  ARCH-003 / ARCH-005 / ARCH-006 / ARCH-007 / ARCH-008
```

**为什么 ARCH-001/002 排在大部分 BUG 之前**：BUG-008（UoW）与 BUG-004（锁）本质上都是 ARCH-002 分层后的产物；先做异常化能让后续所有"拒绝路径"的测试从"捕获 SystemExit"退化为"断言异常类型"，大幅降低测试脆弱性。若工期紧张，至少先做 ARCH-001（1.5d），它能同时降低 BUG-001 与 BUG-012 的实施成本。

---

# 附：审查中确认无问题的部分（勿在重构中破坏）

以下设计经实测验证有效，重构时需保持语义：

- **跨月哈希链续接**：`chain_append` 的 `prev_override` 仅在目录为空时生效（防分叉），语义正确
- **Merkle 根排除自身持有者**：`exclude={"state.json"}` 避免自指悖论
- **`--redeliver` 显式授权才重交付**（L799-830）：默认不覆盖，符合铁律 1
- **`verify` 三态分离**（L589-614）：error=未对账，不计入通过，判定诚实
- **慢车道只拦写操作**（N-004，L764）：已装库的纯校验是读操作，豁免——判断精准
- **`THREAT_MODEL` 明示不防 ③ 档**：威胁模型自洽，是有意为之的克制
