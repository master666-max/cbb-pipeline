# CONVENTIONS.md — 正典库构建系统命名与编码规范

> 屎山治理周期 5（superpowers 轮）产出；从 326 件清理实例中提炼。

## 命名

- **Python 模块/函数/变量**：snake_case；**工具件文件名**：中文动词短语（`批次自检.py`/`检索层.py`——管线工序名，历史约定，不改为拼音）
- **常量**：UPPER_SNAKE（`CORROBORATION_BUMP`/`DEFAULT_THETA`）；**魔法数字禁散落**——超过两处使用的数值必须提为模块常量
- **测试文件**：`test_<被测件名>.py`；测试内解包占位用 `_` 前缀（`_rc, rep = ...`）
- **记录/字段**：契约 v3 字段名不动（`record_id`/`canonical`/`t_valid`）；sidecar 文件=中文或语义英文名（`complementary-statements.jsonl`/`缺口队列.jsonl`）

## 异常处理

- **文件读循环**：`except (OSError, json.JSONDecodeError): continue`——禁裸 `except Exception`
- **网络/子进程/LLM 调用**：宽捕获合法但必须带 `# noqa: BLE001 — <降级语义说明>` 注记
- **探活**：`subprocess.run(..., check=False)` + 返回码判定（退出码≠异常）
- **导入失败**：fail-fast `SystemExit`（`连续性巡检.py` 模式）

## 布局

- 模块头：docstring（职责+来源 Phase）→ `from __future__ import annotations` → stdlib → 本包相对导入
- `# -*- coding: utf-8 -*-`：保留（中文项目惯例，防旧工具误判——UP009 豁免裁定）
- 单文件≤400 行为软限（6 个超限件=工序边界裁定保留，新增超限需 DECISIONS 登记）

## 测试

- 每个新模块配 `test_v3_*.py`；判据全断言化（禁零断言 describe）
- 修 bug 先写红测试（PT-020）；红队攻击固化为回归（P0-1/P1-1 模式）
- PROVEN 等价锚（acceptance.py）**任何改动后必跑**

## 工具链

- ruff：`py -X utf8 -m ruff check <dir>`——两域当前 All checks passed（继续保持）
- bandit：`-ll` 级别——测试件 B101 误报已知，探活 B310 合法
- 发布包：改生产件后必跑 `tools/build_release.py`（manifest 逐位一致）
