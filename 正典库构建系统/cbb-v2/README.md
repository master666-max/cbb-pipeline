# cbb-v2 · 包化重建版（reimagine 产物）

> 判决：**PROVEN** —— `tests/acceptance.py` 对 v1 特征基线（`analysis/characterization-baseline.json`，指纹 `aafe38042b28f0c2`）五面逐位相等；金丝雀对 v2 有效（改坏=1/还原=0）。

## 这是什么

CBB 核心管线的**包化重建**：算法忠实移植 v1（proven），架构全新——

| v1 债务 | v2 解法 |
|---|---|
| 46 模块各自 sys.path.insert 手术 | **可安装包 `cbb2`**，绝对导入（`from cbb2.store import Store`） |
| 19 处实例名默认 + 7 处写死端口 | **`config.py` 单一配置源**（env-first，推不出报错，吸收 路径惯例） |
| 无统一入口 | `runner.py` 编排骨架（aux 探活降级） |
| 契约/账本/隔离散装 | `contracts/gate/ledger/quarantine` 各就各位 |

## 模块

- `config.py` — env-first 配置 + 惯例推导（store_of/workspace_of/neo4j_http/namespace）
- `corpus.py` — 坐标/引文回落/BOM 剥离（R9/R10）
- `defenses.py` — 元文本/注入闸 + 禁词八类（忠实词表）（R6/R7/R8/R15）
- `gate.py` — 记录构造 + 证据可见性判定（复用 v1 contracts 校验器）
- `store.py` — 三态 + 双轨 + 原子写 + 撕裂披露 + -m{N} 版本链 + P-017 幂等（R1-R5/R13）
- `ledger.py` — 哈希链账本（verify 读盘不信任缓存）（R12）
- `quarantine.py` — 隔离区（数据格式与 v1 逐字节兼容）（R14）
- `search.py` — 机械检索面：别名/关键词/RRF/引文核验（R11）
- `runner.py` — 章管线编排骨架

## 数据兼容

**同一库双向可操作**：v2 读写 v1 的 `迷深实战-本体库/`（同布局同 schema），切换零迁移。
验收以临时夹具证明；对生产库的切换需先跑 `analysis/characterization.py`（对 v1 库）留基线。

## 使用

```python
import sys; sys.path.insert(0, "cbb-v2")   # 或 pip install -e cbb-v2
from cbb2.store import Store
from cbb2 import config
store = Store(config.store_of(Path("正典库构建系统")))
```

## 边界（裁决 D1）

长尾工具（cbb/tools 66 件）**保留 v1 原地**，cbb2.runner 以适配层调用——增量迁移，按需进行。
