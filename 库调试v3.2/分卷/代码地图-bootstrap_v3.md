# bootstrap_v3.py 结构地图（共 2416 行，v3.8.1）

> 用途：网页 AI 塞不下全文时，先发本地图 + 文件头（1-16 行），再按问题贴对应段落。

## 文件头（贴这个就够 AI 建立世界观）
- **1-16 行**：模块 docstring = 公理 A~G + 子命令清单 + 用法。全文的灵魂，必贴。
- 20 行：`VERSION = "3.8.1"`

## 第 1 区：SOURCES 唯一事实源（22-305 行）
- 26-76 `REGISTRY`：33 条题录（arXiv id / 标题 / 备注）
- 79-80 `BASELINE_BLACKLIST`：变异黑名单
- 82-95 `TUNABLES`：可调参数（衰减 0.7、反思阈值 50 等）
- 97-104 `LAWS`：六铁律
- 106-107 `SCHEMA_V3`：条目十字段
- 110-121 `MODULE_MAPPING` / 123-134 `LEVELS`（L0~L9）/ 137-140 `PACKAGE_MAPPING`
- 143-149 `SOP_GUARD` / 153-163 `REFEREE_PROMPT` / 165-178 `PACKAGES`（12 特色包）
- 180 `ESCAPE_POD`（回退=移 attic）/ 182-196 `THREAT_MODEL` + `CHARTER_L8`（L8 宪章）
- 205-210 `load_bodies/save_bodies`（bootstrap_data/bodies.json 读写）

## 第 2 区：基础设施（212-305 行）
- 215-218 哈希三件套：`sha` / `self_hash` / `line_hash`
- 220-238 `chain_append`：审计链追加（跨月连续）
- 240-247 `validate_entry`：写入前校验（铁律 2/5）
- 249-258 `entry_normalize`：八字段→十字段回填
- 260-268 `merkle_root`：Merkle 根（排除 state.json）
- 270-301 `detect_cycle` + `resolve`：依赖 DAG 与档位解析

## 第 3 区：渲染器（306-397 行）
- 309-397 `render_quickref/spec/entrypoint/skill_wrapup/skill_taskstart/readme/pkg_template/citations`

## 第 4 区：子命令实现（399-1175 行）
- 402-405 `set_data_dir`（--data 动态寻址）
- 407-456 `cmd_absorb`（v2.x 源树抽取）
- 458-538 `cmd_absorb_md`（v4 Markdown→v3 JSON 迁移）
- 540-569 `_norm_title/_urllib_read/_fetch_arxiv_title`（arXiv 对账工具）
- 571-632 `cmd_verify`（题录对账 + 静态不变式 + 退出码）
- 634-656 `cmd_build`（build-docs，--lib 刷渲染件）
- 658-693 `REFLECT_SYNTHESIS` / `render_installer_v3` / `ADAPTER_PAGE_V3`
- 695-702 `_body_for`（单文件内容唯一决策点）
- 704-751 `_deliver`（内容体落盘 + manifest + 守卫段注入）
- 753-758 `_ledger_append`
- 760-839 `cmd_install`（安装 + 幂等校验模式 + --redeliver）
- 877-915 `_all_entries/_rank_entries`（检索打分：keywords×3/content×1/links 一跳）
- 917-1100 `cmd_engine`（append/retrieve/eval/wrapup/reflect/doctor/retire/shadow 等大分支）
- 1102-1141 `cmd_guard`（变异守卫）
- 1152-1175 `cmd_migrate`

## 第 5 区：测试（1177-~2410 行，40 个用例）
- 1179 起 `TESTS` 注册表；1180 `_tmpdir` 辅助
- 覆盖：审计链防篡改/跨月、schema 拒写、密钥扫描、DAG 环、Merkle 一致性、install 幂等、guard 否决、反思触发、检索加权、eval 劣化、redeliver、overrides 闭环……
- 末尾 2372 `t_shape` / ~2410 `main` 入口

## 省流喂法
1. 先贴：1-16 行（公理）+ 本地图
2. 再按问题贴：问 install 贴 760-875；问检索贴 877-915；问 wrapup/reflect 贴 972-1100；问测试贴对应 `t_*` 函数
3. 每段 100~400 行，任何网页 AI 都装得下
