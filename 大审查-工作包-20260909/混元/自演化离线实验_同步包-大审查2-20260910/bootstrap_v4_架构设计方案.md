# bootstrap v4 完全重构 · 架构设计方案

> 目标：从"四条平行真相 + 事后对账"重构为"单一事件流 + 可重建投影"。
> 全文基于已跑通的 v4 内核原型（实测数据见附录 A），非纸面推演。

---

## 零、先诊断：为什么 v3 需要重构而不是继续打补丁

v3 宣告了六条公理，但承载它们的执行机制只有两个：哈希链（append-only）与 Merkle 快照。其余靠字符串常量（`LAWS`）、168 条 `assert`、以及 `doctor` 的事后对账支撑。

**公理宣告的强度 > 实现承载的强度**，这个落差是所有 P0/P1 的共同根源。三个实测证据：

| 证据 | 说明 |
|---|---|
| `audit` 不含条目内容 | 公理 D 说 audit 是真相源，实测它只是指针日志 |
| 并发 `importance_accum` = 5/60 | state 是独立真相，read-modify-write 必丢更新 |
| 截断攻击检不出 | Merkle 锚定内容集合，不锚定序列长度 |

打补丁能修每一个症状，但**四个平行真相**这个结构不拆，同类问题会持续再生。

---

## 一、设计原则（从公理反推的硬约束）

| 原则 | 内容 | 反例（v3） |
|---|---|---|
| **P1 单一真相** | 事件流是唯一真相；其他一切可重建 | memory/state/ledger/audit 四真相 |
| **P2 纯函数折叠** | 状态 = `fold(events)`；无隐藏可变状态 | state 靠 read-modify-write |
| **P3 锚定序列而非仅集合** | 同时锚定内容集合与事件序列长度 | 只有 merkle_root |
| **P4 不变式可执行** | 六铁律是代码，不是字符串 | LAWS 是中文字符串 |
| **P5 正常路径全绿** | 任何"正常操作也报警"的信号必须拆出去 | eval 后就报根不一致 |
| **P6 能力即声明** | 措辞不得强于实现 | guard/令牌声明防②实际防不住 |
| **P7 确定性** | 同输入 → 同字节 → 同哈希（跨平台） | write_text CRLF 分歧 |

---

## 二、五个核心设计决策

### 决策 1：事件溯源（Event Sourcing）+ 可重建投影

**决定**：`audit/` 是唯一 append-only 真相；`memory/`、`state.json`、`ledger/` 都是它的投影。

**为什么**：一次性消除 lost update、漏刷根、id 冲突、四态对账——它们都是"没有单一裁决点"的症状。

**代价与取舍**：
- 审计文件变大（携带 payload）→ 接受，因为正确性优先，且当前规模下性能不是瓶颈（实测 0.005s/300 条目）
- 需要 replay 能力 → 用增量 fold 缓解（只读新增事件）

### 决策 2：事件行用单行 JSON，人类可读版本降级为渲染视图

**决定**：
- 真相：`audit/events-YYYY-MM.jsonl`，单行 JSON（`sort_keys` + 紧凑分隔）
- 视图：`audit/lifelog-YYYY-MM.md`，渲染产物，不参与 Merkle（公理 B）

**为什么**：
- JSON 天然转义换行 → 顺带消灭 P1-10（审计链注入）
- 规范化序列化 → 哈希稳定，跨平台确定
- 人类可读性不丢：靠 `engine log` 命令渲染，而非把真相格式降级成 markdown

**这个决策的关键洞察**：v3 把"真相格式"和"人类可读"绑在一起，导致既要解析 markdown 又要防注入。拆开后两者各自最优。

### 决策 3：三元组锚定，且必须抄录人侧

**决定**：`chain_tip` + `merkle_root` + `package_sha256`

**为什么（实测，见附录 A）**：

| 场景 | 库内锚点 | 人侧锚点 |
|---|---|---|
| 删 audit 尾，未同步改 state | ✅ 检出 | ✅ 检出 |
| 删 audit 尾 **且** 同步改库内 state | ❌ 检不出 | ✅ 检出 |
| 篡改中间行 payload | ✅ 断链 | ✅ 检出 |

**这不是实现缺陷，是信任模型的必然**——库内的一切都能被同等权限修改。所以：
- 库内锚点防②（意外/未同步篡改）
- 人侧锚点防③（蓄意）
- 文档必须写明这个边界（原则 P6）

### 决策 4：单写者锁 + seq 序号（不做多写者乐观并发）

**决定**：全写路径 `flock`，事件带单调递增 `seq`。并发写者被串行化，第二个写者 seq 递增而非覆盖。

**为什么**：append-only + seq 让"并发丢更新"从根上消失——实测 12 进程并发 → `accum=60`（v3 是 5）。多写者冲突消解（CRDT/merge）是**当前不需要的复杂度**（原则：不要提前设计）。

**声明**：单写者模型写进 `spec.md`；若未来需要多写者，在事件层加冲突消解，不改上层。

### 决策 5：分层，但用 zipapp 保住单文件分发

**决定**：

```
bs3/
  sources/     纯数据 + JSON Schema（REGISTRY/TUNABLES/LAWS/LEVELS/PACKAGES/SCHEMA/PKG_LEDGERS）
  core/        events / store / fold / projections / invariants / merkle / uow / errors / clock / fsio
  render/      spec / quickref / citations / entrypoint / adapter / installer pages / audit view
  cli/         子命令：参数解析 + 用例编排（唯一 sys.exit 边界）
  tests/       pytest + fixtures + 契约测试
bootstrap_v3.py   thin launcher（或 zipapp 单文件）
```

**附带收益**：现在配置与代码共用一个哈希——改 `emotion_decay` 会使 `self_hash()` 变化，人侧锚点全部失效。分离后锚点只覆盖"代码 + 铁律 + 事件 schema"，参数变更走账本留痕。

---

## 三、数据模型

### 3.1 事件

```python
@dataclass(frozen=True)
class Event:
    v:    int            # schema 版本（V4-11）
    seq:  int            # 单调递增，库内唯一
    ts:   str            # ISO-8601（由注入的 Clock 提供）
    type: str
    payload: dict
    prev: str            # 上一行哈希（跨月续接）
    # h = sha256(prev + "\0" + canon({v,seq,ts,type,payload}))
```

**事件类型**：

| 类型 | payload | 说明 |
|---|---|---|
| `SCHEMA_EPOCH` | from_version, pkg_sha256, schema_v | 流首事件；迁移时承接 v3 链尾 |
| `LIB_CREATED` | level, packages, delivered | install |
| `ENTRY_APPENDED` | 完整条目字段 | **携带 payload**（v3 只有指针） |
| `ENTRY_INVALIDATED` | id, t_invalid | 失效标记（不删除） |
| `ENTRY_RETIRED` | id | 移 attic |
| `EMOTION_DECAYED` | decay, result | wrapup |
| `REFLECT_DONE` | — | 累计器归零 |
| `EVAL_RECORDED` | n, recall@5, MRR | 评测结果入流 |
| `LEVEL_CHANGED` | from, to | upgrade/downgrade |
| `PKG_LEDGER_TRANSITION` | pkg, id, from, to, data | 特色包状态机 |
| `HUMAN_TOKEN_SPENT` | level, token_id | 慢车道留痕 |
| `DELIVERY_REPAIRED` | files | redeliver |
| `SHADOW_OBSERVED` | text | 公理 G 预演 |

### 3.2 状态（fold 产物，纯函数）

```python
@dataclass
class State:
    seq: int; chain_tip: str
    level: str; packages: list
    entries: dict          # id -> entry
    importance_accum: int
    emotion: dict
    ledger: dict           # 特色包状态机当前态

def fold(events) -> State           # 全量
def apply(state, event) -> None     # 单事件推进（增量 fold 的基础）
```

### 3.3 投影

| 投影 | 内容 | 物化位置 | 可重建 |
|---|---|---|---|
| 条目视图 | `entries` | `memory/{longterm,intermediate}/*.json` | ✅ |
| 库状态视图 | 非条目部分 | `state.json`（**缓存**，非真相） | ✅ |
| 审计视图 | 人类可读时间线 | `audit/lifelog-*.md`（渲染件） | ✅ |
| 变更索引 | append 等动作流水 | `ledger/changes.jsonl` | ✅ |
| 检索索引 | 倒排（可选） | `memory/.index.json` | ✅ |

**所有投影都可以删掉重建**——这是 v3 与 v4 最本质的区别。

---

## 四、核心流程

### 4.1 写路径（唯一入口）

```
cmd → UoW.begin()              # 取 flock
        ├─ store.append(type, payload)     # 原子追加（seq+1, prev=tail.h）
        ├─ state = fold(read_since(last))  # 增量 fold
        ├─ materialize(state)              # 刷新投影
        └─ state.json = snapshot(state)    # 写缓存快照（原子替换）
      UoW.commit()              # 放锁
```

关键点：**没有 read-modify-write**。状态永远是 fold 出来的，快照写错可重算。

### 4.2 读路径

```
retrieve → 读投影（memory/ + 可选索引）→ scorer 打分 → 返回结果
```

检索只读投影，不碰事件流。索引缺失时从投影重建。

### 4.3 校验路径（doctor）

```
doctor:
  chain_integrity       逐行重算 h 与 prev            ← 防篡改
  chain_tip_match       fold().chain_tip vs 快照/人侧  ← 防截断
  content_drift         manifest 256bit 比对           ← 防改文件
  unregistered          目录扫描（memory/ 是已知盲区）  ← 防加文件
  projection_consistency 重建 vs 现有投影               ← 防投影漂移
  view_freshness        state.seq vs 事件流末 seq      ← 防漏写
  anchor_match          与人侧三元组比对（可选）
```

**七条信号独立报告**。硬性纪律：标准操作序列（install/append/wrapup/eval/reflect/retire/shadow）之后**必须全绿**。

---

## 五、铁律 → 可执行不变式

| 铁律 | 机器校验点 | 违反后果 |
|---|---|---|
| 1 不覆盖/回退移 attic | UoW 写前检测：目标存在且内容不同 → 必须先移 attic 且账本有记录 | 拒绝写 |
| 2 证据准入 | `payload.source_event_id`/`evidence` 非空**且可在事件流中解析** | 拒绝（消灭 P0-2 的空串绕过） |
| 3 引用给出处 | content 含他人观点 → 必须有 REGISTRY id | 警告 + 入报告 |
| 4 审计面只追加 | `chain_integrity` + `chain_tip` | 拒绝写 |
| 5 不存密钥 | 写入前密钥模式扫描（含 payload 全字段） | 拒绝 |
| 6 慢车道 | 变更 laws/宪章/基准 → 需人侧令牌并核销 | 拒绝 |

`invariants.py` 统一入口 `verify(lib) -> [Violation]`，替换 168 条 `assert`（`-O` 下会失效）。

---

## 六、重构实施顺序

**总原则：先定义不变式，再定数据模型，再定流程，最后才动代码结构。**
顺序错了会反复返工——v3 的教训正是"先写了 2400 行，再补公理"。

### 阶段 0 · 冻结契约（1.5d）

**目标**：让重构可执行。

- 把 68 个内联测试改为**契约测试**（只通过 CLI 与库目录断言驱动），内部函数只留纯函数单测
- 建立 `run CLI(argv) -> (code, stdout, stderr)` 契约层

**为什么最先**：测试若锁死内部实现，分层拆包时每个改名都要同步改测试，重构会在半途卡住、最后退回单文件。这是"重构失败"最常见的死法。

**产出**：`tests/contract/`，用例数 ≥68，重命名内部函数后测试无需修改。

### 阶段 1 · 异常化（1.5d）

- `BootstrapError` 体系取代 24 处 `sys.exit`；`cli/` 是唯一 exit 边界

**为什么第二**：所有后续工单的"拒绝路径"测试都依赖能 `except` 到具体异常类型。

### 阶段 2 · 安全与正确性（1.5d，**不改动文件结构**）

- `chain_tip` 三元组锚定（V4-03）
- `state` 降级为 fold 产物（V4-01）

**为什么插在分层之前**：改动小、不动物理结构，却消掉 P0-4 和安全硬伤。性价比高于任何结构性重构。

**产出**：截断可检出；并发 `accum` 正确；`state` 可重建。

### 阶段 3 · 数据模型升级（3.5d）

- 事件 schema 版本化（V4-11）
- 事件携带 payload，memory 成为投影（V4-02）
- v3→v4 迁移器（V4-12）

**为什么在分层之后或与之并行**：这是改动最大的一步，需要分层后的 `core/` 承载。若工期紧，可与阶段 4 交错：先落 `core/events` + `core/store` + `core/fold`，旧代码继续跑，双写验证后再切换。

**产出**：`memory/` 删掉可完整重建；存量库迁移通路 + dry-run 对账。

### 阶段 4 · 结构重构（3.5d）

- 分层拆包（ARCH-002）+ zipapp 单文件
- UoW + 锁 + 原子写（ARCH-004）
- 文本落盘唯一出口（V4-09）、时钟注入（V4-08）

### 阶段 5 · 语义升级（4d）

- 不变式校验器（ARCH-003）
- 健康信号矩阵（V4-04）
- 可插拔 scorer + 中文分词（ARCH-006）
- 测试结果机器化（ARCH-007）

### 阶段 6 · 价值兑现（3d）

- 档位迁移 upgrade/downgrade（V4-05）
- 特色包账本状态机（V4-06）
- 人类令牌加固（V4-07）

**总计约 18.5 人日**（不含前批 BUG 修复）

---

## 七、迁移路径（v3.8.1 存量库）

```
1. dry-run 对账：fold(候选事件) vs 现有 memory/ 逐条目比对
   → 不一致则拒绝迁移并报告（不迁坏库）
2. 现有 audit/lifelog-*.md 只读保留（v3 段）
3. 追加 SCHEMA_EPOCH 事件：prev 承接 v3 链尾哈希  ← 链不断（铁律 4）
4. 追加 LEGACY_SNAPSHOT 事件：现有 memory/ 全部条目固化为 payload
5. 旧 state.json / ledger 移 attic/migrate-v3-<ts>/  ← 不销毁（铁律 1）
6. 生成三元组，打印提示抄录人侧
7. doctor --verify-migration 对账
```

---

## 八、风险与对策

| 风险 | 影响 | 对策 |
|---|---|---|
| 事件流膨胀 | 库变大 | 接受（正确性优先）；提供 `engine compact` 生成快照事件（不删旧事件，只加速 fold） |
| replay 变慢 | 大规模库启动慢 | 增量 fold + 定期快照事件；当前规模下非问题 |
| 迁移失败 | 存量库损坏 | dry-run 强制前置 + 旧文件全移 attic + 可回滚 |
| 分层后单文件体验丢失 | 使用者不适应 | zipapp 产出单文件；launcher 保持 `bootstrap_v3.py` 同名同参数 |
| 测试重写工作量 | 工期 | 契约化后**重写一次即永久解耦**，后续重构不再改测试 |

---

## 九、明确不做

1. **性能优化**：实测 300 条目 `merkle_root` 0.005s、`retrieve` 0.008s，不是瓶颈
2. **增量 Merkle 单独实现**：fold 天然可增量，`index_hot_budget`/`merkle_refresh_trigger` 顺势接入
3. **③ 档防御**：`THREAT_MODEL` 已明示不防，只保证②档防住 + ③档留痕可查
4. **多写者并发**：单写者锁 + seq 足够，不提前引入 CRDT
5. **分布式**：超出单库边界

---

## 附录 A · v4 内核原型实测

原型位于 `proto/bs3v4.py`（约 120 行），验证四项核心机制：

```
=== V1 事件流为唯一真相 ===
  entries=5 importance_accum=25（期望 25）
  memory/ 物化: ['e0.json' ... 'e4.json']
  事件流含 payload 正文: True
  删掉 memory/ 后从事件流重建: ['e0.json' ... 'e4.json']   ✅

=== V2 并发 append（12 进程，每个 importance=5）===
  importance_accum = 60（期望 60）| 条目 12 | seq 13
  审计链连续: True                                          ✅
  （v3 同场景实测：5 / 60）

=== V3 截断攻击 ===
  场景 C（删尾、未同步改 state）→ 库内 chain_tip 检出      ✅
  场景 B（删尾 + 同步改库内 state）→ 库内检不出，人侧检出   ✅
  场景 D（篡改中间行 payload）→ 逐行重算断链                ✅

=== V4 性能 ===
  300 条目：merkle_root 0.005s；retrieve 全库 0.008s       → 非瓶颈
```

**核心代码骨架**（原型，非生产）：

```python
@dataclass(frozen=True)
class Event:
    seq: int; ts: str; type: str; payload: dict; prev: str = ""
    @property
    def body(self): return canon({"seq":self.seq,"ts":self.ts,"type":self.type,"payload":self.payload})
    @property
    def h(self): return sha(self.prev + "\x00" + self.body)

class EventStore:
    def append(self, type, payload):
        with flock(LOCK_EX):
            seq, prev = self.tail()
            ev = Event(seq+1, now(), type, payload, prev)
            self._shard(ev.ts).open("a").write(ev.line() + "\n")   # 原子追加
            return ev

def apply(state, e):        # 单事件推进
    if e.type == "ENTRY_APPENDED":
        if e.payload["id"] in state.entries: raise ValueError("id 重复")   # 铁律1 天然保证
        state.entries[e.payload["id"]] = e.payload
        state.importance_accum += int(e.payload.get("importance", 0))
    ...
    state.seq, state.chain_tip = e.seq, e.h

def fold(events) -> State:  # 纯函数
```

**注意**：`id 重复` 在 fold 时天然被拒——v3 的"同 id 跨层共存"（P1-7）在事件溯源下不可能发生，因为唯一性由 fold 保证，而不需要在文件系统层做查重。

---

## 附录 B · 与 v3 的对照

| 维度 | v3.8.1 | v4 |
|---|---|---|
| 真相源 | 四条平行（audit/ledger/memory/state） | 单一事件流 |
| 状态获取 | read-modify-write | `fold(events)` 纯函数 |
| 并发 | 丢更新 92% | append + fold，实测 60/60 |
| 截断防护 | 无 | `chain_tip`（库内防②，人侧防③） |
| 注入防护 | 依赖调用方（换行可注入） | JSON 天然转义 |
| 唯一性 | 文件系统查重，跨层可绕过 | fold 保证 |
| 不变式 | 字符串 + 168 assert | `invariants.py` 可执行 |
| 健康信号 | 1 个过载信号 | 7 条独立信号 |
| 档位 | 写死，升级需重装 | `upgrade`/`downgrade` |
| 特色包 | 目录 + 描述 | 声明式状态机 |
| 令牌 | `--yes`（②档可绕过） | 一次性 token + 核销 |
| 跨平台确定性 | CRLF 分歧 | 唯一写入出口 |
