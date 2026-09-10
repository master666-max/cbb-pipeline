# bootstrap_v3 → v4 重构工单集（独立第二批）

> 本工单集独立于前 33 张（BUG-001~025 / ARCH-001~008），目标版本 **v4.0**。
> 来源：深度架构审查（公理与实现的落差分析）+ 已跑通的 v4 内核原型验证。
> 编号 `V4-xx`，不与前批冲突。

## 与第一批工单的关系

- **第一批**修的是"工程执行层"（异常化、分层、UoW、检索层）——不改动数据模型
- **第二批（本集）**改的是"数据模型与信任模型"——事件溯源、双重锚定、状态机
- **执行顺序**：本集的 `V4-01` 与 `V4-03` 应**插到第一批的架构改造之前**（理由见"插入点说明"），其余在第一批阶段 2 之后

## 插入点说明

`V4-01`（state 改 fold）与 `V4-03`（chain_tip）合计约 1.5d，**不改动文件物理结构**，却能同时消掉 P0-4（并发丢更新 92%）与一个此前未发现的安全硬伤（截断攻击检不出）。性价比高于第一批中任何一项结构性重构，故提前。

```
第一批 P0（BUG-001/002/003）
   ↓
【插入】V4-03 → V4-01        ← 1.5d，安全与正确性
   ↓
第一批 P1（BUG-004~012）+ ARCH-001
   ↓
第一批 ARCH-002 分层 ──→ 本集 V4-02 / V4-11 / V4-12（数据模型升级）
   ↓
本集 V4-04 ~ V4-10
```

---

## 工单总表

| 编号 | 标题 | 级别 | 估时 | 依赖 |
|---|---|---|---|---|
| V4-01 | state 改为 fold 产物（消除 lost update） | 核心 | 1d | — |
| V4-02 | 审计事件携带 payload（完整事件溯源） | 核心 | 2.5d | V4-11 |
| V4-03 | chain_tip 双重锚定 + 人侧三元组 | 核心 | 0.5d | — |
| V4-04 | 健康信号矩阵解耦 | 重要 | 1d | V4-01 |
| V4-05 | 档位迁移 upgrade / downgrade | 重要 | 1d | V4-01 |
| V4-06 | 特色包账本声明式状态机 | 重要 | 1.5d | V4-02 |
| V4-07 | 人类令牌模型加固 | 重要 | 0.5d | — |
| V4-08 | 时钟注入 | 基础 | 0.3d | — |
| V4-09 | 文本落盘唯一出口 | 基础 | 0.3d | — |
| V4-10 | 测试契约化解耦（**先于分层**） | 基础 | 1.5d | — |
| V4-11 | 事件 schema 版本化与演进 | 核心 | 0.5d | V4-02 |
| V4-12 | v3.8.1 → v4 迁移器 | 核心 | 1d | V4-02、V4-11 |
| V4-13 | 明确不做清单（性能等） | 约束 | — | — |

**合计约 11.6 人日**（不含第一批）

---

# 核心工单

## V4-01 · state 改为 fold 产物（消除 lost update）

| 项 | 内容 |
|---|---|
| 级别 | 核心 · **应最先做** |
| 位置 | `cmd_engine` append L936-941；wrapup L973-981；retire L1089-1093；reflect-done L1025-1030 |
| 估时 | 1d |
| 依赖 | 无 |

### 问题

`importance_accum` / `emotion` / `merkle_root` 都是 read-modify-write 的独立真相。实测 12 进程并发 append（每个 importance=5）：

```
importance_accum = 5   （期望 60，丢失 91.7%）
```

`importance_accum` 是反思触发（阈值 50）的唯一输入 → 并发下反思机制静默失效。

### 方案

不改物理格式，只改**真值的来源**：

1. `state.json` 降级为**缓存快照**（含 `seq` / `chain_tip` / fold 结果的副本），不再是真相
2. `importance_accum`、`emotion` 改为从 `ledger/changes.jsonl` + `audit/` **实时 fold** 得出
3. 提供 `rebuild_state(lib) -> State`：纯函数，可随时从事件流重建
4. 写路径从「读 state → 改 → 写」变为「append 事件 → fold → 写快照」——快照写错可重算，不影响正确性

### 原型已验证

```
12 进程并发 append(importance=5) → importance_accum = 60（期望 60）| 条目 12 | 审计链连续 True
```

对比原版 `5/60`。核心差别：append 是原子追加，fold 是纯函数，不存在 read-modify-write 窗口。

### 验收标准

- [ ] 新增用例 `t_concurrent_accum_exact`：12 进程并发 append，`importance_accum` 恰好 60
- [ ] 新增用例 `t_state_rebuildable`：删除 `state.json` 后执行 `engine rebuild-state`，结果与删除前逐字段一致
- [ ] 新增用例 `t_state_snapshot_stale_ok`：手工篡改 `state.json` 的 `importance_accum`，`doctor` 检出"快照与重算不一致"并指引 rebuild
- [ ] 单进程行为不变：`t_reflect_trigger`、`t_reflect_done`、`t_root_refresh_on_write` 通过

---

## V4-02 · 审计事件携带 payload（完整事件溯源）

| 项 | 内容 |
|---|---|
| 级别 | 核心（**改动最大、收益最大**） |
| 位置 | `chain_append` L220-238；`cmd_engine` 全部写路径 |
| 估时 | 2.5d |
| 依赖 | V4-11（schema 版本化） |

### 问题

公理 D 宣告 `lifelog = 审计面（真相源）`、`记忆条目 = 投影`。实测：

```
审计链中关于 e0 的全部信息：entry:e0 → intermediate
→ audit 是否含条目内容: False
```

审计链只记指针、不含 payload。真相的载体只在 `memory/` 里，因此系统实际是**四条平行真相**（audit / ledger / memory / state），`doctor` 的四方对账是四个真相两两交叉核对。

这是 P0-4、P1-7、P1-8 的共同根源——它们都是"没有单一裁决点"的不同症状。

### 方案

1. **事件流成为唯一真相**：
   - 单行 JSON（`canon()` 规范化：sort_keys + 紧凑分隔），天然消除换行注入（P1-10）
   - 事件携带完整 payload（条目全部字段）
   - 分片 `audit/events-YYYY-MM.jsonl`，跨月续接 `prev`（沿用现有正确逻辑）
2. **审计视图渲染化**：`audit/lifelog-YYYY-MM.md` 降级为**渲染视图**（公理 B：文档即产物，手改即违例），不参与 Merkle 根
3. **`memory/` 成为投影**：`fold(events).entries` 的物化，可随时重建
4. **`ledger/changes.jsonl` 保留**：作为事件的读优化索引（供人快速浏览），或改为事件子集视图
5. **事件类型**：`LIB_CREATED` / `ENTRY_APPENDED` / `ENTRY_INVALIDATED` / `ENTRY_RETIRED` / `EMOTION_DECAYED` / `REFLECT_DONE` / `EVAL_RECORDED` / `LEVEL_CHANGED` / `SHADOW_OBSERVED` / `HUMAN_TOKEN_SPENT` / `DELIVERY_REPAIRED`

### 原型已验证

```
事件流含 payload 正文: True
删掉 memory/ 后从事件流重建: ['e0.json', ... 'e4.json']（完整恢复）
```

### 验收标准

- [ ] 新增用例 `t_audit_carries_payload`：审计行可被解析出完整条目字段
- [ ] 新增用例 `t_memory_rebuildable`：删除整个 `memory/` 后 `engine rebuild`，所有条目逐字段恢复
- [ ] 新增用例 `t_projections_consistent`：`memory/` + `state.json` 与 `fold(events)` 的结果完全一致（作为 doctor 的核心校验）
- [ ] 新增用例 `t_audit_view_is_rendered`：`lifelog-*.md` 被手改后不影响校验结果，且被报"渲染件被改"
- [ ] 人类可读性：`engine log --tail 20` 能渲染出可读的审计时间线

---

## V4-03 · chain_tip 双重锚定 + 人侧三元组

| 项 | 内容 |
|---|---|
| 级别 | 核心 · **安全硬伤，应最先做** |
| 位置 | `state.json` 结构；`doctor` L1048-1073 |
| 估时 | 0.5d |
| 依赖 | 无 |

### 问题（实测）

```
构造：append 5 条 → 删掉 audit 尾部 2 行 → 重算 Merkle 根并更新 state.json
doctor: memory 5 / audit 3 / ledger 5 / 审计链 连续 / state 根一致
→ 检出: False
```

Merkle 根锚定**内容集合**，不锚定**序列长度**。截断后剩余各行仍自洽（每行的 `prev` 指向前一行，逐行重算全通过）。只要同步更新 `state.json` 的根，截断就永久隐形。`state` 中无任何字段记录"链应该有多长"。

严重性高于 BUG-005（guard 绕过）——它打击的是审计面本身。

### 方案

`state.json` 增加 `chain_tip`（事件流末行哈希），与 `merkle_root`、`package_sha256` 构成**三元组锚点**：

| 锚点 | 防护对象 |
|---|---|
| `chain_tip` | 事件序列的长度与顺序（防截断、防回滚） |
| `merkle_root` | 内容集合（防改/增/删文件） |
| `package_sha256` | 安装器自身（防包被替换） |

`doctor` 增加 `chain_tip` 校验项。

### ⚠️ 关键约束：锚点必须抄录人侧

原型实测证明了这一点的必要性：

| 场景 | 库内 chain_tip | 人侧 chain_tip |
|---|---|---|
| C：只删 audit 尾，未同步改 state | ✅ 检出 | ✅ 检出 |
| B：删 audit 尾 **且** 同步改库内 state | ❌ 检不出 | ✅ 检出 |
| D：篡改中间行 payload | ✅ 断链 | ✅ 检出 |

**库内锚点只防"意外/未同步篡改"（②档）；防蓄意（③档）必须靠人侧保管。** 这不是实现缺陷，是信任模型的必然——库内的一切都能被同等权限修改。

因此：三元组必须在 `install` 时**打印并提示抄录人侧**，并在 `README.md` 中明确其用途与局限。

### 验收标准

- [ ] 新增用例 `t_chain_tip_recorded`：`state.json` 含 `chain_tip` 且等于事件流末行哈希
- [ ] 新增用例 `t_truncation_detected`：删尾部 N 行（未同步改 state）→ `doctor` 报"截断"，exit 非 0
- [ ] 新增用例 `t_anchor_triplet_printed`：install 输出含三元组三个值，README 含"抄录人侧"指引
- [ ] 新增用例 `t_guard_anchor_supports_tip`：`guard --anchor` 支持人侧三元组文件（含 `chain_tip`）对账
- [ ] 文档：明确"库内锚点防②、人侧锚点防③"

---

# 重要工单

## V4-04 · 健康信号矩阵解耦

| 项 | 内容 |
|---|---|
| 级别 | 重要 |
| 位置 | `doctor` L1032-1074 |
| 估时 | 1d |
| 依赖 | V4-01 |

### 问题

`merkle_root` 一个信号同时承担"内容完整性 / 写入纪律 / 篡改检测"三个职责。而 P1-8 已证明**正常操作就会触发它**（`eval`/`reflect`/`guard --snapshot` 之后必然报"根不一致"）。

后果：只用官方命令、不做任何篡改，doctor 就说"根不一致 / 差异等用户裁决"。用户对这个信号脱敏后，真正的篡改被淹没。这是可观测性的经典反模式——**既报故障又报正常的信号，等于没有信号**。

### 方案

拆为独立信号，各自独立报告、独立决定是否阻塞：

| 信号 | 含义 | 数据来源 |
|---|---|---|
| `chain_integrity` | 链连续 + tip 匹配 | 逐行重算 + `chain_tip` |
| `content_drift` | manifest 在册文件被改 | 256bit manifest 比对 |
| `unregistered` | 新文件未在册（注明 `memory/` 盲区） | 目录扫描 |
| `view_freshness` | 物化视图落后于事件流 | `state.seq` vs 事件流末 seq |
| `anchor_match` | 与人侧三元组比对 | 人侧输入（可选） |
| `projection_consistency` | memory/state 与 fold 结果一致 | V4-02 的重建比对 |

输出从"五态全一致"的二元结论改为**信号矩阵**（每条含状态与可信度）。

**硬性纪律**：任何"正常操作也会报警"的信号必须修复或拆出去。新增用例锁定"标准操作序列后全绿"。

### 验收标准

- [ ] 新增用例 `t_doctor_signals_independent`：构造只违反 `content_drift` 的场景，其余信号仍为绿
- [ ] 新增用例 `t_normal_ops_all_green`：执行 install/append/wrapup/eval/reflect/retire/shadow 全流程后，所有信号为绿
- [ ] 新增用例 `t_view_freshness_detects_stale`：手工回退 `state.seq`，`view_freshness` 报警而 `chain_integrity` 仍绿

---

## V4-05 · 档位迁移 upgrade / downgrade

| 项 | 内容 |
|---|---|
| 级别 | 重要 |
| 位置 | `cmd_install` L760-875；`state.json.level` |
| 估时 | 1d |
| 依赖 | V4-01 |

### 问题

`level` 在 install 时写死，之后无任何变更路径。`--redeliver` 只修漂移文件，不改档位。想从 L2 升到 L5 只能**重装**，而重装会撞上 P0-3（脏目录 + 无条件覆盖用户文件）。

`LEVELS`（L123-134）的定义本身就是累积式（`L5.adds ⊇ L3.adds`），说明设计意图是可叠加的，但缺操作入口。

### 方案

`engine upgrade --to L5` 作为一等公民：

1. `resolve(目标档位)` 与当前档位求差集
2. 只交付**新增**部分（复用 `_deliver` 的 prefix 逻辑）
3. 入账本 + 入事件流（`LEVEL_CHANGED`）
4. 更新 `state.level`
5. 旧档位内容**不删除**（铁律 1）
6. `downgrade` 只做标记（`LEVEL_CHANGED` + 账本），不移除任何文件
7. 涉及 L8/L9 时，慢车道门禁生效（复用 N-004 逻辑）

### 验收标准

- [ ] 新增用例 `t_upgrade_delivers_delta`：L2 → L5 只新增 L3/L4/L5 的模块，L0-L2 文件不动
- [ ] 新增用例 `t_upgrade_preserves_user_files`：用户改过的 L1 文件在 upgrade 后保持原样
- [ ] 新增用例 `t_downgrade_is_marker_only`：downgrade 后文件数不减少，账本有记录
- [ ] 新增用例 `t_upgrade_l9_gated`：升到 L9 未带令牌 → 拒绝

---

## V4-06 · 特色包账本声明式状态机

| 项 | 内容 |
|---|---|
| 级别 | 重要 |
| 位置 | `PACKAGES` L165-178；`render_pkg_template` L381-389 |
| 估时 | 1.5d |
| 依赖 | V4-02 |

### 问题

`PACKAGES` 为 12 个包定义了 `ledger`（如 `x-writing` 的"伏笔账本(planted/recovered)"），但代码里**没有任何状态机实现**。包 = 目录 + README 模板。

**最差异化的部分（账本状态机）恰恰是完全没实现的部分**——12 个包退化为 12 个文件夹 + 12 句描述。

### 方案

把 `ledger` 从字符串升级为声明式状态机定义（纳入 SOURCES，公理 A）：

```python
"x-writing": {
  "libs": ["文风画像", "设定集", "时间线"],
  "ledger": {
    "kind": "foreshadow",
    "states": ["planted", "recovered", "abandoned"],
    "transitions": {"planted": ["recovered", "abandoned"], "recovered": [], "abandoned": []},
    "required_fields": ["planted_at", "chapter"],
    "terminal": ["recovered", "abandoned"]
  }
}
```

通用命令：`engine ledger --pkg x-writing --id F-001 --to recovered [--data '{...}']`
→ 校验转移合法性 → 入账本 → 入事件流（`PKG_LEDGER_TRANSITION`）→ 可选物化到 `packs/<pkg>/<ledger>.md`

状态机定义同样由 SOURCES 渲染进文档（公理 B）。

### 验收标准

- [ ] 新增用例 `t_ledger_transition_valid`：合法转移成功并入账本
- [ ] 新增用例 `t_ledger_transition_invalid`：非法转移（如 `recovered` → `planted`）被拒
- [ ] 新增用例 `t_ledger_required_fields`：缺 `required_fields` 被拒
- [ ] 新增用例 `t_ledger_defs_rendered`：12 个包的状态机定义出现在渲染文档中
- [ ] 至少实现 3 个包（建议 `x-writing` / `x-code` / `x-life`）作为样板

---

## V4-07 · 人类令牌模型加固

| 项 | 内容 |
|---|---|
| 级别 | 重要 |
| 位置 | `cmd_install` L764-767、L856-858 |
| 估时 | 0.5d |

### 问题

慢车道实现是命令行 `--yes`。`THREAT_MODEL` 声明"防②防SOP约束下粗心"，但**任何能调用命令的 agent 都能加上 `--yes`**——而 ② 档的"粗心"恰恰表现为随手加 flag 让流程走下去。

结论：**声明防②，实际防不住②**。与 guard（ARCH-008）是同一类病灶：措辞与能力不匹配。

### 方案（按强度递增，选一档）

1. **弱**：`--yes` 时强制回显——打印宪章全文并要求命令携带宪章中随机指定的片段（如 `--yes --echo "objective hacking"`），确保"读过"而非"跳过"
2. **中**（推荐）：人侧生成一次性 token 文件（人侧持有），命令读取并**核销**（用后删除），token 与 `level` + `package_sha256` 绑定
3. **强**：人侧私钥签名，包内置公钥验签

同时把 `THREAT_MODEL` 措辞校准为"②档提供阻力与留痕，不提供强制拦截"。

### 验收标准

- [ ] 新增用例 `t_token_required_for_l8`：无令牌 → 拒绝（现状行为，固化为回归保护）
- [ ] 新增用例 `t_token_bound_to_level`：为 L8 签发的 token 不能用于 L9
- [ ] 新增用例 `t_token_consumed_once`：token 用后失效
- [ ] 文档：`THREAT_MODEL` 措辞与实际能力一致

---

## V4-08 · 时钟注入

| 项 | 内容 |
|---|---|
| 级别 | 基础 |
| 位置 | `chain_append` L234；`_rank_entries` L893；`retire` L1083 |
| 估时 | 0.3d |

### 问题

`time.strftime("%Y-%m")`、`time.time()` 直接调用 → **跨月逻辑与 TTL 逻辑无法在测试中模拟**。现有 `t_cross_month_real`（L2232）依赖真实跨月，一年里只有极少数时候能覆盖到目标路径。

跨月链接续接是公理明确要求的能力，却实际测不到。

### 方案

抽 `Clock` 接口（`now()` / `stamp()` / `month_key()`），生产注入系统时钟，测试注入 fake clock。

### 验收标准

- [ ] 新增用例 `t_cross_month_simulated`：fake clock 跨月，`chain_append` 正确续接上月末行哈希
- [ ] 新增用例 `t_retire_ttl_simulated`：fake clock 快进 91 天，条目正确出仓
- [ ] `t_cross_month_real` 保留（真实时钟冒烟），但主覆盖交给模拟用例

---

## V4-09 · 文本落盘唯一出口

| 项 | 内容 |
|---|---|
| 级别 | 基础 |
| 位置 | L742、L748（`write_bytes`）vs L845-853、L639-641（`write_text`） |
| 估时 | 0.3d |

### 问题

代码注释自曝了这个问题（L742："write_text 在 Windows 写 CRLF，与 LF 哈希记账天生不符"），但只修了两处。`cmd_install` L845-853 与 `cmd_build` L639-641 仍在用 `write_text`。

后果：**同一库在 Windows 与 Linux 上产生的 Merkle 根不同**，人侧锚点对账误报。

### 方案

`fsio.write_text_deterministic(path, content)` 作为**唯一出口**：统一 LF 换行、UTF-8 编码、原子替换（临时文件 + `os.replace`）。全项目禁止裸 `write_text` / `write_bytes`（账本/审计链的 append 场景除外，那里换行由内容决定）。

### 验收标准

- [ ] 新增用例 `t_no_bare_write_text`：源码扫描，`render/` 与 `cli/` 下无裸 `write_text`
- [ ] 新增用例 `t_root_stable_across_newline_modes`：在 `newline="\r\n"` 环境重新渲染，Merkle 根不变
- [ ] 新增用例 `t_write_is_atomic`：写入过程中被中断，磁盘上要么是旧值要么是新值

---

## V4-10 · 测试契约化解耦（**先于分层**）

| 项 | 内容 |
|---|---|
| 级别 | 基础 · **顺序关键** |
| 位置 | 全部 68 个 `@t` 用例 |
| 估时 | 1.5d |

### 问题

68 个测试与实现同文件，且大量**直接调用内部函数**（`chain_append` / `validate_entry` / `merkle_root` / `render_*`）。

真正的代价不是"文件太大"，而是：**测试锁死了内部实现**。一旦做分层拆包（ARCH-002），每个内部函数改名/移动都要同步改测试——重构会在半途卡住，最后大概率放弃分层、退回单文件。

### 方案

测试只通过**公共契约**驱动（`cmd_*` / `engine` 的命令行语义与输出），内部函数用契约测试间接覆盖。

- 契约层：`run CLI(argv) -> (exit_code, stdout, stderr)` + 库目录断言
- 内部函数：仅保留少量**纯函数单元测试**（`line_hash` / `canon` / `fold`），这些不随重构移动

**执行顺序**：本工单应与 ARCH-001（异常化）并列为**最先**完成的两项，两者都是让 ARCH-002 真正可执行的前提。

### 验收标准

- [ ] 用例中不出现对 `chain_append` / `merkle_root` / `render_*` 的直接调用（纯函数除外）
- [ ] `grep -c "def t_"` 用例数不减少（68 → ≥68）
- [ ] 人为重命名内部函数（如 `chain_append` → `append_event`），测试**无需修改**即可通过

---

## V4-11 · 事件 schema 版本化与演进

| 项 | 内容 |
|---|---|
| 级别 | 核心 |
| 位置 | 事件流格式定义 |
| 估时 | 0.5d |
| 依赖 | V4-02 |

### 问题

一旦审计事件成为唯一真相且只追加，格式就**不可变更**（铁律 4）。若 v4.1 想给事件加字段，老事件无法回溯修改。

### 方案

1. 事件行包含 `v: 1` 版本字段；`canon()` 只序列化已知字段，未知字段**保留不丢**
2. `EventStore` 读取时按版本分派到对应的 `parse_v1` / `parse_v2`
3. `fold` 按版本分派 `apply_v1` / `apply_v2`
4. 事件流头部写入 `SCHEMA_EPOCH` 事件，记录格式版本与包 sha256
5. 升级器（`upgrade-events`）生成**新版本事件**追加（如 `ENTRY_APPENDED_V2`），不改写旧事件

### 验收标准

- [ ] 新增用例 `t_event_v1_roundtrip`：v1 事件序列化→解析→哈希一致
- [ ] 新增用例 `t_event_unknown_field_preserved`：含未知字段的事件被读取后字段不丢失
- [ ] 新增用例 `t_mixed_version_fold`：v1/v2 混合事件流正确 fold

---

## V4-12 · v3.8.1 → v4 迁移器

| 项 | 内容 |
|---|---|
| 级别 | 核心 |
| 位置 | `cmd_migrate` L1152-1174 |
| 估时 | 1d |
| 依赖 | V4-02、V4-11 |

### 问题

存量 v3.8.1 库是"四条平行真相"格式，需要无损迁移到事件溯源格式，且**审计链不能断**（铁律 4）。

### 方案

1. 现有 `audit/lifelog-*.md` **只读保留**（v3 段），不改写
2. 追加 `SCHEMA_EPOCH` 事件，记录 `from=v3.8.1`、旧链尾哈希、包 sha256，其 `prev` 承接 v3 链尾（链不断）
3. 追加 `LEGACY_SNAPSHOT` 事件：把现有 `memory/` 全部条目固化为 payload（v4 的 genesis 状态）
4. 现有 `state.json`、`ledger/changes.jsonl` 移 `attic/migrate-v3-<ts>/`（铁律 1，不销毁）
5. 生成 `chain_tip` + `merkle_root` + `package_sha256` 三元组，打印提示抄录人侧
6. 迁移前自动 dry-run：fold 结果与现有 `memory/` 逐条目比对，不一致**拒绝迁移**并报告
7. 提供 `bs3 doctor --verify-migration` 迁移后对账

### 验收标准

- [ ] 新增用例 `t_migrate_chain_unbroken`：迁移后新事件流首行的 `prev` 等于 v3 链尾哈希
- [ ] 新增用例 `t_migrate_lossless`：迁移后 `fold(events).entries` 与迁移前 `memory/` 逐字段一致
- [ ] 新增用例 `t_migrate_dry_run_mismatch_rejected`：构造不一致的存量库，dry-run 拒绝迁移
- [ ] 新增用例 `t_migrate_preserves_old`：旧 `lifelog-*.md` 仍在（只读保留），旧 state 在 attic
- [ ] 迁移后跑 `doctor` 全绿

---

## V4-13 · 明确不做清单

| 级别 | 约束 |
|---|---|

以下项在 v4 **明确不做**，避免过度设计：

1. **性能优化**：实测 300 条目库 `merkle_root` 0.005s、`retrieve` 全库扫描 0.008s——**当前规模性能不是瓶颈**。即便万级条目单次也在 0.1s 量级
2. **增量 Merkle / `index_hot_budget` 单独实现**：`TUNABLES` 里的 `index_hot_budget` 与 `merkle_refresh_trigger` 不必单独实现——**事件溯源落地后 fold 本身就是可增量的**（只需 replay 新增事件），顺势接入即可
3. **③ 档（完整权限蓄意 agent）防御**：`THREAT_MODEL` 已明示不防，架构上不追加对抗措施，只保证②档防住且③档留痕可查
4. **多写者乐观并发**：v4 采用**单写者锁**（`flock` + `seq` 序号）。若未来需要多写者，再引入事件级冲突消解——不要提前设计
5. **分布式 / 多库同步**：超出单库边界，v4 不涉及

---

# 交付检查点

| 检查点 | 包含工单 | 产出 |
|---|---|---|
| CP1 安全与正确性 | V4-03、V4-01 | 截断可检出；并发无 lost update；state 可重建 |
| CP2 重构解锁 | V4-10、ARCH-001 | 测试契约化；无 sys.exit 领域函数 |
| CP3 数据模型升级 | V4-11、V4-02、V4-12 | 事件溯源内核；memory 可重建；存量库迁移通路 |
| CP4 结构重构 | ARCH-002、ARCH-004 | 分层；UoW + 锁 |
| CP5 语义升级 | V4-04、ARCH-003、ARCH-006 | 信号矩阵；不变式校验器；可插拔 scorer |
| CP6 价值兑现 | V4-05、V4-06、V4-07、V4-08、V4-09 | 档位迁移；包状态机；令牌加固；时钟注入；写入唯一出口 |
