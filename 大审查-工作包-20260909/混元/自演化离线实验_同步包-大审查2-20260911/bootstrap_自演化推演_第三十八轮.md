# 自演化 · 第三十八轮：E147 —— 锚定探针接入内核

> 任务：把 E146a 的锚定探针落进 `kernel.py`，并补验收测试。
>
> **结果：验收从 27 项 → 43 项，全过。**
> 过程中修了一个陈旧断言和一个测试 bug，两者都值得记录。

---

## 一、内核改动

```
KernelConfig 新增：
  anchor           = True       # 锚定探针开关
  anchor_n         = 8          # 锚定任务集大小
  anchor_thr       = 0.02       # 漂移判据
  boost_on_drift   = 4          # 检出后 kids 临时倍数
  boost_gens       = 6          # boost 持续代数

Kernel 新增：
  _anchor_policy   固定不参与演化的 Policy（"世界温度计"）
  _anchor_tasks    固定任务集，只建一次（★ 轮换就无法区分漂移）
  _anchor_hist     历史读数
  _anchor_check(g) 每代一次，免费
  _cur_kids(g)     检出后返回 kids × boost_on_drift
```

调用点：`_step()` 中数据空间操作之后、真值审计之前。

---

## 二、⭐ 关键设计：boost 以 blind 为前提

```python
def _cur_kids(self, g):
    if (self.cfg.boost_on_drift and self.cfg.blind     # ★ blind 是前提
            and self._drift_detected_at is not None
            and g <= self._boost_until):
        return self.cfg.kids * self.cfg.boost_on_drift
    return self.cfg.kids
```

依据 E146c：judge 漂移下 boost 会让 surf 权重从 2.56 飙到 5.69（+3.13），
而 blind 就位后 surf 差为 **+0.00**。所以**没有盲评就不允许 boost**。

---

## 三、修掉的两个问题

### 3.1 陈旧断言（T15）

原断言：`drift 世界下有审计 > 无审计`
实测：**有审计 −0.0174，无审计 −0.0102（审计略差）**。

这不是回归，是 **E145b 已证明的事实**：drift 下重锚完全无效（+0.0000, t=0.00）。

> **用一条错误的断言守护代码，只会掩盖真正该守的性质。**

改为守护三条真正该守的：
1. 判别式回退 > naive 无条件回退
2. drift 危害被压到 <0.03（E133 naive 为 −0.0795）
3. 残余危害未恶化 > −0.05（已知未解问题的回归哨兵）

实测通过：判别式 +0.0034 / naive +0.0026 / 残余 +0.0034。

### 3.2 测试 bug（T17）

缓存里"未检出"存的是 `-1`，而断言写 `det is not None`：
`−1 is not None` 恒为真 → **检出 6/6、误报 6/6 同时成立**（自相矛盾）。

> 识别信号：**两个互斥的指标同时满分** → 一定是判定条件错了，不是被测对象错了。

修正为 `det >= 0`：检出 6/6，误报 **0/6**。

---

## 四、新增验收测试（T17–T20）

| # | 守护什么 | 实测 |
|---|---|---|
| T17a | drift 下锚定探针检出 | **6/6** |
| T17b | 无 drift 零误报 | **0/6** |
| T17c | 锚定任务集固定不轮换 | n=8 ✓ |
| T17d | 锚定配置不参与演化 | ✓ |
| T18 | drift 下 boost > 不 boost | −0.0559 vs −0.0657（+0.0097）|
| T19a | **无盲评 → 禁止 boost** | kids=4 ✓ |
| T19b | 有盲评 → boost 生效 | kids=16 ✓ |
| T19c | boost 窗口过期回落 | kids=4 ✓ |
| T20 | 锚定探针零副作用 | 开=关=+0.0888（差 0.0000）|

**T20 差值为 0.0000** —— 锚定探针在无 drift 时完全不改变行为，纯增量。

---

## 五、工程改进：分片落盘缓存

沙盒频繁 500 导致长测试无法跑完。解决：

```
proto/vk_common.py   拆出 build_world / mk / cached（import 不执行测试）
proto/precompute.py  重型测试预计算，只补缺失项
res_verify_cache.json  57 项缓存
```

**关键**：`verify_kernel.py` 是平铺脚本，import 它就会跑全部测试，
所以必须把 `mk` 拆到独立模块才能"只预计算重活"。

```bash
python3 proto/precompute.py t15    # 分片预计算
python3 proto/verify_kernel.py     # 命中缓存，秒出
```

---

## 六、复现

```bash
python3 proto/precompute.py          # 全量预计算（可中断续跑）
python3 proto/verify_kernel.py       # → PASS 43 / FAIL 0
```
