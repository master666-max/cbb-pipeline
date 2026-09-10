# 自演化内核 v1（最新版）

把 **40 轮推演**的结论落实为可运行代码。每条设计都有实验依据编号。

> ⚠️ **本文件已更新至 E150（第 40 轮）。**
> 旧版本写的是"26 轮 / 27 项验收"，**已过期**。当前：**53 项验收全过**。

```
kernel.py          内核本体（约 700 行）★ 含 __main__ 演示入口
verify_kernel.py   53 项验收测试
vk_common.py       公共构件（import 不会触发测试）
precompute.py      重型测试预计算（分片落盘，可中断续跑）
check_pairing.py   配对效应独立验证
```

```bash
python3 proto/kernel.py            # ★ 直接运行演示（3 个场景）
python3 proto/precompute.py        # 预计算（可中断续跑）
python3 proto/verify_kernel.py     # → PASS 53 / FAIL 0
```

---

## 〇、快速验证（30 秒）

```bash
$ python3 proto/kernel.py
```

```
① 干净世界（默认配置）
  真值增益        = +0.2127
  采纳/回退/重锚  = 6 / 0 / 0
  drift 检出于    = 第 None 代      ← 无漂移，正确未误报
  活跃度告警      = 0

③ 世界漂移（第 8 代重洗 35%）
  真值增益        = -0.0390
  drift 检出于    = 第 8 代          ← ★ 注入点=检出点，锚定探针精确命中
```

**drift 注入在第 8 代，锚定探针检出于第 8 代** —— 这是 E146a（100%/0%）的直接体现。

---

## 一、三层 + 锚定层结构

```
元层 Meta    —— 效用函数/任务集/探针/预算，frozen，系统无写入方法
法层 Policy  —— 检索与演化参数，系统可自由演化
行层 Entry   —— 记忆条目，系统可自由写（但需整理）
锚定层       —— 人侧判断样本，永不衰减
```

**元层隔离是能力式的**：`Meta` 是 `@dataclass(frozen=True)`，
且 `Kernel` 上不存在任何 `set_meta` / `update_meta` 方法——
系统**拿不到**修改元层的句柄，而不是"改了会被拒绝"。

---

## 二、设计依据全表（40 轮）

| 代码位置 | 机制 | 依据 | 实测效果 |
|---|---|---|---|
| `ScreenResult` | 廉价筛选**类型上无 accept** | 原则 9 / E13 | 违规代码写不出来 |
| `JudgeScore` | judge 数字不可对外 | **E85**（膨胀 349×） | `__str__` → `<judge:internal-only>` |
| `judge(blind=True)` | 盲评剥离表象 | E87/E100/E111 | 表象操纵收益 0.558→0.460 |
| `mutate(scale)` | 大幅度变异 | E104/E106 | 1.0→2.0 收益 +0.097 |
| 双门晋升 | 宽松准入 + 严格晋升 | **E7**（0/20 vs 20/20） | 逃出局部最优 |
| `pick_parent(temp)` | 温度采样 0.3 | E104 | +0.016 |
| `pareto_front` | 干净双目标 Pareto | E96/F-21 修正 | cap≥8 后平坦 |
| 停摆监控 | 检测**绝对状态** adopts=0 | E44/E96 | margin 0.15 自动放宽到 0.019 |
| `measured_importance` | 实测 = 采纳率 | E32 | 0.711 vs 自称 0.495 |
| `_prune` | 整理用**真值**不用 judge | **E122** | +0.053 vs −0.001 |
| `_audit` 判别式回退 | **按退化原因选动作** | **E133/E134** | 配置跑飞 +0.179 / 世界变了 −0.080 |
| **锚定探针** | 固定配置 × 固定集测漂移 | **E146a** | **100%/100%/0% 误报，免费** |
| **boost_on_drift** | 检出后 kids×4 | **E146b** | +0.0842 (t=3.53)，渐进下更好 |
| **boost 以 blind 为前提** | 无盲评禁止 boost | **E146c** | judge 漂移下 surf 差 +3.13 → blind 后 **+0.00** |
| **活跃度 CORE_DIMS** | 只统计核心维度 | **E150** | 核心冻结+表象乱变：采纳=3（停摆漏）→ 告警=13 |
| 预算账本 | 耗尽即停 | E64/E93 | 门槛 300 |
| 危险降档 | 危险≥3 → scale=1.0 | E115 | 复合下 v4-A > v4-B |
| 探针轮换 | 每 10 代换 seed | E84 | 防探针污染 |

---

## 三、完整配置项（含默认值与依据）

```python
@dataclass
class KernelConfig:
    scale: float = 2.0            # E106: 2.0 见顶；E115 复合危险→1.0
    temp: float = 0.3             # E104（最优 3.0/0.3 = +0.1997）
    tol: float = 0.04             # E96 宽松准入（平台区 0.04~0.25）
    margin: float = 0.02          # E96/E137 有监控时几乎不重要，默认靠 0
    cap: int = 8                  # E72（2~16 全不显著）
    kids: int = 4

    # ── 配对机制（一侧失效时另一侧会放大危害）──
    blind: bool = True            # ★ E111 盲评是大幅度安全的前提
    audit: bool = True            # ★ E110 必须与大幅度配对

    # ── 数据空间（E119–E126）──
    write_every: int = 0          # 0 = 不自写入（静态世界）
    write_n: int = 3
    prune_by: Optional[str] = None  # None / "truth"（★ E122: 不用 judge）
    prune_every: int = 2

    # ── 状态判别（E133/E134）──
    monitor: bool = True          # E44 停摆监控
    degrade_thr: float = 0.01
    diagnose_delta: float = 0.01  # ★ 判别式回退的判据阈值
    reanchor_after: int = 2       # E26/E67

    # ── 锚定探针（E146a/b/c）──
    anchor: bool = True
    anchor_n: int = 8             # 固定任务集大小
    anchor_thr: float = 0.02      # 平台区，无需标定
    boost_on_drift: Optional[int] = 4
    boost_gens: int = 6

    # ── 演化活跃度（E150）──
    activity: bool = True
    activity_win: int = 4
    activity_min: int = 1
    activity_after_drift: int = 2
```

---

## 四、关键实现细节

### 4.1 能力式红线（不是检测式）

```python
ScreenResult = Literal["reject", "unknown"]   # ★ 没有 "accept"
```

**"用廉价筛选采纳"的代码在类型上就不成立。**

### 4.2 judge 数字不可对外

```python
def __str__(self): return "<judge:internal-only>"
```

E85：**膨胀 349 倍**（自报 +8.66 / 真实 +0.025）。

### 4.3 变异必须含加性成分

```python
d[f] = d[f] * (1 + choice([...]) * scale) + choice([0, 0, 0.5, -0.5]) * scale
#                                            ^^^^ F-18：纯乘性会把 0 锁死
```

### 4.4 ⭐ 判别式回退（E133/E134）

```python
if cur_best > cur + diagnose_delta:
    # 历史最优确实更好 → 配置跑飞 → 回退
else:
    # 连历史最优也救不了 → 世界变了 → 重锚（不回退）
```

**回退的价值符号相反**：配置跑飞 **+0.179 (t=9.14)** / 世界变了 **−0.080 (t=−4.52)**。
无条件回退是在两种错误间各赌一半。

### 4.5 ⭐ 锚定探针（E146a）

```python
def _anchor_check(self, g):
    tasks = self._anchor_tasks_build()      # ★ 只建一次，绝不轮换
    cur = truth(self.entries, tasks, self._anchor_policy)   # ★ 固定配置
    if cur < mean(hist[-7:-1]) - anchor_thr:
        self._drift_detected_at = g
```

**测的是 root 的得分**（配置固定）→ 变化只反映世界。
对比 judge 跳变（测 champion，受"配置改进"混淆）：

| 信号 | abrupt | gradual | 误报 | 成本 |
|---|---|---|---|---|
| **anchor** | **100%** | **100%** | **0%** | 免费 |
| judge 跳变 | 70% | 50% | 0% | 免费 |
| 真值审计 | 55% | 35% | 0% | 付费 |

### 4.6 ⭐ boost 以 blind 为硬前提（E146c）

```python
def _cur_kids(self, g):
    if (self.cfg.boost_on_drift and self.cfg.blind    # ★ blind 是前提
            and self._drift_detected_at is not None
            and g <= self._boost_until):
        return self.cfg.kids * self.cfg.boost_on_drift
    return self.cfg.kids
```

judge 漂移下 boost 会让 surf 权重 **+3.13**；blind 就位后 **+0.00**。
**这是代码级约束，不是配置建议。**

### 4.7 ⭐ 活跃度只统计核心维度（E150）

```python
CORE_DIMS = ("w_kw", "w_content", "w_imp", "w_age", "filter_zero", "deep")
# 表象维度 w_len/w_fmt/w_den/w_cit 不计入
```

T24 构造（核心冻结 + 表象乱变）：

| 指标 | 表现 |
|---|---|
| 采纳数 | **3**（停摆监控**不触发**） |
| 任意维度变化 | 64（第一版误判"活跃"） |
| **核心维度变化** | **0** ✅ |

> 系统可以在被监控的维度上表现良好，同时在真正重要的维度上完全不动。

---

## 五、验收测试（53 项全过）

| 组 | 覆盖 | 数量 |
|---|---|---|
| T1–T16 | 基础机制：能力式红线、盲评、配对、停摆、Pareto、预算、元层隔离、判别式回退 | 16 |
| **T17–T20** | **锚定探针**：检出 6/6、误报 0/6、boost 以 blind 为前提、零副作用（开=关=+0.0888） | 4 |
| **T21–T24** | **演化活跃度**：核心维度识别、与停摆互补、drift 后告警、维度级必要性 | 4 |
| 其余 | 各轮机制的回归哨兵 | 29 |

**回归测试**（守护我自己在实验中犯过的实现错误）：
- **T7** Pareto 不得是 `arch[-cap:]`（F-20）
- **T13** 变异必须含加性成分（F-18 零乘锁死）
- **T21–T24** mutate_dead 在 drift 下从 0 变 −0.1625（E149）

### 运行方式（沙盒不稳时用）

```bash
python3 proto/precompute.py          # 预计算重活，分片落盘
python3 proto/verify_kernel.py       # 命中缓存，秒出
```

`verify_kernel.py` 是平铺脚本（import 会跑全部测试），
所以 `mk / build_world / cached` 拆到了 `vk_common.py`。

---

## 六、已知限制（诚实说明）

1. **`_prune` 用 `entry.quality`（真值）排序** —— 真实系统无真值，
   需替换为外部信号判定，但**绝不能用 judge**（E122: +0.064 vs +0.005）
2. **`judge()` 仍是人工加权函数**，不是真实 LLM
   —— **150 个实验的 judge 全是人工函数，真实 LLM-as-judge 从未测过**
3. **漂移应对只有"加预算"有效**（+0.084），五种结构性调整全废
4. **drift 下审计"正确不动作" ≡ "审计坏了"**（逐位相同，E148）
   —— 不能从结果判断审计是否工作，必须单独监测
5. 所有常量来自玩具世界（60 条目 / 6 类 query），**数字不可外推**

---

## 七、落地工单对接

| 工单 | 内容 | 依赖本内核的哪部分 |
|---|---|---|
| EV-02 | 锚定集采集与固化 | `Meta` + 锚定层（尚未实现采集） |
| EV-03 | 判断集（最大差异采样） | `Meta.probe_seed` |
| EV-04 | 效用函数拟合 | `judge()` 需替换为拟合出的效用 |
| EV-19 | 真值抽样审计 | `_audit()` 已有骨架，需接真人 |
| EV-20 | judge 通道独立性审查 | `JudgeScore` 已做类型隔离 |
| **新增** | drift 检测已在内核，`anchor=True` 默认开 | `_anchor_check()` |
| **新增** | 活跃度告警已接入 `final_report()` | `_record_activity()` |
