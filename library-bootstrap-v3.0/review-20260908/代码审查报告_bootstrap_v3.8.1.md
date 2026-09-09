# bootstrap_v3.py（v3.8.1，2415 行）严格代码审查报告

- **审查对象**：`library-bootstrap-v3.0/bootstrap_v3.py`（VERSION=3.8.1，单文件安装包）
- **审查日期**：2026-09-08
- **审查方法**：全量通读 2415 行 → 疑点清单 → **隔离动态实证**（临时目录导入模块、构造最小 bodies、逐条复现，不触碰源目录与包数据）。本报告每条 P0/P1 均标注「实证」或「静态」依据。
- **问题计数**：P0（破坏自身铁律/安全/数据完整性）5 条；P1（功能正确性/契约违背）10 条；P2（健壮性/可移植性/性能）14 条，合计 **29 条**。

---

## 一、总评

这是一份**设计纪律显著高于一般个人工具**的代码：公理（单一事实源、文档即产物、双平面、根锚定、慢车道、可证伪）→ 机器可校验不变式 → 行为测试的闭环意识贯穿始终；离线三态（match/mismatch/error）、幂等安装、redeliver、removed 镜像、CRLF 哈希漂移修复等细节说明作者踩过真实的坑并做了根治。

但当前版本存在一组**自我违背**：若干缺陷恰好破坏代码自己宣告的铁律与不变式（铁律 1、铁律 2、公理 E、公理 G），且根因高度集中——**写操作提交序列在 6 处以上手写、口径不一**，**文件分类三轨制分散**，**领域错误用 `sys.exit` 表达**。这三点是架构层面的杠杆点，修掉它们可以同时消灭大部分具体缺陷。

---

## 二、P0：严重问题（破坏铁律 / 安全 / 数据完整性）

### P0-1　条目 id 路径穿越，可写出库目录（安全）
- **位置**：`cmd_engine` append 分支，L927–933；`validate_entry` L240–247。
- **现象（实证）**：id 不做任何字符集校验，直接 `dest / f"{e['id']}.json"`。传入 `"../../../pwned"` 时，文件被写到**库目录之外**（探针实测 `ROOT/pwned.json` 落盘），且审计链/账本照常记录一次"合法 append"。
- **影响**：任何能调用 engine append 的 agent/输入都可向库外任意路径写文件（受进程权限约束）；id 含 `/`、`\`、`:` 还会制造嵌套目录与 doctor 正则永远对不上的账本记录。
- **修复**：`validate_entry` 增加 id 白名单 `^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$`，禁止路径分隔符与 `..` 段；落盘前断言 `epath.resolve().is_relative_to(dest.resolve())`。

### P0-2　retire 在 attic 存在同名文件时覆盖旧文件——直接违反铁律 1
- **位置**：L1083–1086（`shutil.move(str(f), str(dest))`）。
- **现象（实证）**：预先在 `memory/attic/old.json` 放置旧版本，再 retire 同名条目，探针实测 attic 旧文件内容被新文件替换（Windows 11 / Python 3.14 实测为覆盖；部分平台为 `FileExistsError` 裸崩——两种结果都不正确）。
- **根因**：出仓只算 TTL，不检查目标点是否已存在；铁律 1「永不删除/覆盖已有记录」在自己的实现里被击穿。
- **修复**：`dest.exists()` 时改用不冲突名（如 `old__<t_invalid 或时间戳>.json`）并在审计文本记录改名原因；禁止任何形式的覆盖。

### P0-3　同一 id 可在 intermediate / longterm 双写，唯一性失效
- **位置**：L927–932（只检查**目标目录**内 `epath.exists()`）。
- **现象（实证）**：先 append importance=1 的 `dup`（落 intermediate），再 append importance=9 的同 id（落 longterm）——第二次未触发"已存在"拒绝，两个 `dup.json` 同时存在。此后 `_rank_entries` 以 `f.stem` 为键，两条记录在检索结果里静默互相覆盖；doctor 的 memory↔audit 对账也出现二义性。
- **修复**：唯一性检查面为整个 `memory/` 树（`list((lib/'memory').rglob(f'{id}.json'))`，attic 一并纳入决策）；重复即按 J-001 同路径拒绝。

### P0-4　eval 劣化门限"棘轮失效"：被劣化结果反向覆盖
- **位置**：L962–971，基线写盘 L968 在 `sys.exit(2)`（L971）之前无条件执行。
- **现象（实证）**：旧基线 recall@5=1.0；制造劣化（expected 条目失效）后 eval 计算出 0.0、打印宪章警告并 exit 2，**但 0.0 已被写为新 baseline**。下一次运行只需要相对 0.0 不再跌 5% 即可过门——门限被自己逐步拉低，累计漂移无下界。
- **修复**：劣化分支**不覆盖** baseline（保留历史最佳/已签收基线），劣化结果另写 `evals/last_run.json`；MRR 也应纳入同口径门限（当前只守 recall）。

### P0-5　写后刷根纪律不一致，doctor 第五态必然误报
- **位置（实证）**：合规路径 append/wrapup/retire/reflect-done/install/build/redeliver 都在写 audit/ledger 后重算 `state.merkle_root`；但 **shadow（L1095–1098）、reflect（L1009–1022）、guard --snapshot（L1112）、guard --anchor（L1124）** 同样写了 audit/ledger（二者都在 Merkle 根口径内），却不刷根。
- **现象（实证）**：install 后执行一次 `engine shadow`，state 根 `e3e90527…` 与重算根 `23c7fc8f…` 立即不一致；随后 install 校验模式与 doctor 都报"根不一致/最近写操作未刷根或被篡改"。
- **危害**：这是**安全机制信噪比问题**——正常操作持续制造"根不一致"告警，真正的篡改信号会被狼来了淹没，人侧锚定对账失去意义。
- **修复（最高杠杆）**：抽出唯一提交原语 `commit(lib, action, audit_text, state_mutator)`，内部固定"audit → ledger → 改 state → 重算根 → 原子落盘"序列，所有写操作（含 shadow/reflect/guard）必须经过它；或者把 shadow 类纯日志移出根口径，二选一，不能维持现状。

---

## 三、P1：功能正确性 / 契约违背

### P1-6　已装库上请求更高档位被静默忽略，且无升级路径
- **位置**：L773–839，state 存在即进入校验模式并 `return`，**全程不比较请求档位与 `state.level`**。
- **实证**：对 L2 已装库执行 `install L9`，输出"L2 已安装"，state.level 仍为 L2，L9 内容不交付，无任何告警。用户会以为升级成功。
- **修复**：校验模式先比对 `requested_level != st.level`（或 packages 差异），显式报"档位变更未生效"；另提供 `--upgrade` 走差异解析（L8/L9 仍受慢车道令牌约束）→增量交付→账本记 level-change。

### P1-7　铁律 2「证据非空」可被空字符串绕过
- **位置**：L244 `if "evidence" not in e and "source_event_id" not in e`——只查**键存在**。
- **实证**：`source_event_id: ""` 通过校验，errs=[]。SCHEMA_V3 十字段同理：值为 `null`/空串全部通过。
- **修复**：改为真值校验 `not e.get("source_event_id") and not e.get("evidence")`；字段值类型/非空按 schema 逐字段判。

### P1-8　schema 类型不校验，脏数据后置崩溃
- **位置**：L240–258、L906/L927/L939。
- **现象（静态）**：`importance` 传字符串会在 `>= 7` / 累加处抛 `Type: 'str' >= 'int'` 裸崩；`confidence` 无枚举（测试里同时出现"高"和"S"）；`validity.t_valid/t_invalid` 不校验日期形态；keywords/links 有强转兜底（L249–258，做得对）但其余字段没有。
- **修复**：写一个零依赖的类型化校验器（importance∈0..10 int、confidence 枚举、日期正则、content 非空 str），拒绝信息可机读。

### P1-9　absorb-md 产出"半身库"，后续命令连环崩；坏日期被伪造为固定时间
- **位置**：L530–538（只调 append，不建 state）；wrapup L973、reflect L997、reflect-done L1025 均直接 `state.json.read_text` 无存在性保护。
- **实证**：对一个未 install 的目录跑 absorb-md 后执行 wrapup，`FileNotFoundError: state.json`。对照：migrate 反而会建最小 state（L1166–1171）——两个迁移入口契约不一致。
- **附带问题**：L475 无法解析的日期被静默替换为硬编码 `"2026-09-06"`，等于给条目**伪造 created_at**，只在计数里登记 no_date，条目本身无标记。
- **修复**：absorb-md 要么要求目标为已装库，要么像 migrate 一样建最小 state；未知日期写 `null` 并在条目留 `_date_inferred` 标记，禁止填具体假日期。

### P1-10　"渲染件手改检测"存在执法盲区，公理 B 未全覆盖
- **位置**：render_check 只含根目录 5 个文件（L793–794）；`skills/wrap-up.md`、`skills/task-start.md`、`packs/<新包>/README.md` 同为渲染产物，却因落在 `RUNTIME_PREFIX`（L780，"skills/""packs/"）而被豁免。
- **实证**：改写 skills/wrap-up.md 后重装校验，输出"渲染件被改 0"。
- **修复**：见 P1-11 的统一分类函数——渲染产物清单由"渲染函数 × 输出路径"注册表生成，全部纳入重渲染 diff。

### P1-11　工具自产文件被自己报"未在册"
- **位置**：快照落库 L1110；未在册判定 L789–791。
- **实证**：`guard --snapshot` 生成的 `anchor_snapshot.json` 落在库根，下一次 install 校验即报 `[未在册] anchor_snapshot.json`。同类：`memory/reflect/materials-*.md` 靠 runtime 前缀侥幸豁免。
- **根因**：文件身份有三套并行口径——manifest（交付面）、RENDER_NAMES（渲染面）、RUNTIME_PREFIX（运行面），新增输出时必须同时改三处，必然漏。
- **修复**：定义唯一 `classify(rel) -> delivered | rendered | runtime | tool_output | env_trace | foreign`，校验/doctor/快照全部消费它。

### P1-12　engine eval 空评测集 ZeroDivisionError
- **位置**：L960–961 `hits/n`。
- **实证**：golden 为 `[]` 时除零裸崩。修复：n==0 友好退出并提示，不写 baseline。

### P1-13　guard 不带任何模式参数时 TypeError 裸崩
- **位置**：L1128–1129，`Path(None)`。
- **实证**：`guard --lib .`（无 --diff/--snapshot/--anchor）抛 TypeError 栈。修复：参数互斥/缺失校验放 argparse 层，友好退出码 2。

### P1-14　resolve 依赖判定含恒真死逻辑，且缺依赖仍入安装清单
- **位置**：L285–301，死条件在 L294。
- **实证/静态**：`if dep not in got and dep not in order` 中 `order` 是档位名（"L0"…），`dep` 是模块名（"m-schema3"），二者永不相等，`dep not in order` **恒真**；且缺依赖时 `got.add(name)` 照样执行（实证注入未知依赖后模块仍进清单，只靠 cmd_install L769 事后 exit 兜底）。当前 DEPS 之所以不出事，是因为 LEVELS.adds 列表顺序"恰好"把被依赖者排在前面——顺序一改即漏依赖。
- **修复**：删除恒真子句；缺依赖即不加入 got 并向上抛结构化错误；最好做一次真正的拓扑排序输出安装序（替代 `sorted(got)` 的字母序）。

### P1-15　测试运行器兜不住 SystemExit，单个用例可杀掉整个套件
- **位置**：L2381 `except Exception`——`SystemExit` 继承 `BaseException`。
- **实证**：被测路径里一次意外 `sys.exit` 会穿透 runner，68 个测试中断在第一个。修复：`except (Exception, SystemExit) as ex`，并把意外退出码计入 FAIL。

---

## 四、P2：健壮性 / 可移植性 / 性能（14 条，简表）

| # | 位置 | 问题 | 建议 |
|---|---|---|---|
| 16 | L845–849 等 74 处 write_text；L262 | **跨平台根不可复现（实证）**：渲染件用 write_text 在 Windows 落 CRLF（_deliver 只给 2 个文件特判 write_bytes）；Merkle 叶子路径用 `str(relative_to)` 带 OS 分隔符。人侧跨 OS 抄录的根对不上，动摇公理 E | 全部落盘统一 `encode('utf-8')+write_bytes`（newline='\n'）；叶子键统一 `.replace('\\','/')` |
| 17 | L260–268，全文件 16 处 merkle_root | 每次写操作全量 O(n) 重算并通读全库字节；absorb-md 每条 append 重算一次 = **O(n²)**；`merkle_refresh_trigger=500` 登记后从不读取 | 批量导入走"挂根、末尾一次重算"；中期改子树哈希/增量树 |
| 18 | L82–95 | **12 个 TUNABLES 中 7 个是死参数**（grep 实证无消费方）：broadcast_weights、reflect_trigger、index_hot_budget、eval_n、review_intervals、merkle_refresh_trigger、governance_budget。宣称的三路融合/热度分层在代码里不存在——按公理 G 这正是"测不出差异"的表演性配置；中文无空格，`q.split()` 检索退化 | 要么实现要么标注「未实现/规划值」；检索补中文分词或字符 n-gram |
| 19 | L936–941、L236 等 | **state.json 非原子写、无并发锁**：写一半崩溃即全库命令连环崩；两 agent 并发 append 会让哈希链分叉（chain_append 无锁） | tmp 文件 + `os.replace`；库级锁文件（msvcrt/portalocker 思路） |
| 20 | L1911–1922、L1849–1867 等 | **测试污染全局**：t_deliver_skips_removed 直接改写真实 bodies.json 不还原；t_golden_shipped 把 data dir 硬还原到 `cwd/bootstrap_data` 而非原值；chdir/urlopen/strftime/DEPS monkeypatch 依赖顺序；t_absorb_mapping、t_l8_guards 要求 cwd 先 absorb，全新检出 run-tests 不自洽 | 测试 fixture 在 tmp 合成最小 bodies；set_data_dir 用 try/finally 还原原值；不碰真实包数据 |
| 21 | L15 vs L20 | **版本漂移**：头注释写「v3.8.2 中性化修正」，`VERSION="3.8.1"` | 注释引用版本号处改由 VERSION 渲染，或同步 |
| 22 | L600–603 | verify 标题对账用双向子串 + 冒号首段匹配，短首段（如 "Mem0:"）易**假阳性**通过 | token 集合相似度 + 长度比阈值；match 方式（exact/substr/first-seg）落 report 供复核 |
| 23 | L436–437 | absorb 对同一文件 read_text(errors='replace') 与 read_bytes 读两次；非 UTF-8 被静默替换字符；存入的 sha256 是原始字节、交付的是有损重编码内容，且该字段**全局无消费**（死字段） | 一次 read_bytes → 严格 decode（失败显式登记）；要么校验 bodies.sha256 要么删字段 |
| 24 | L636–643、L850+L864 | `out == Path("./dist")` 脆弱（`Path("./dist") != Path("dist")`，J-004 分支基本不可达）；install 时 citations 连写两次 | 路径比较统一 resolve；install 只保留一次渲染 |
| 25 | L1155 | `(lib/"audit").glob(...) and any(glob(...))`：生成器对象恒真，前半段死代码且遍历两次 | 只保留 `any(...)` |
| 26 | L285 | `tuple[list, list]` 下标泛型在 Py3.9 前定义期即 TypeError，无 `from __future__ import annotations`，README 未声明最低版本 | 加 future 注解或改 `Tuple[list, list]`，声明 requires-python |
| 27 | L2404+ | 中文 print 在 cp936 控制台可能 UnicodeEncodeError（文档让用户自己加 -X utf8） | 启动时 `sys.stdout.reconfigure(encoding='utf-8', errors='replace')` 代码自保 |
| 28 | L1108/L1134、L1109 | guard 黑名单按**子串**匹配文件名，"anchor" 会误伤任何含 anchor 的候选；快照/锚定截 16hex（64bit）而库根用全长 256bit，截断策略不统一 | 改文件名段精确/glob 匹配；人侧锚定件一律全长哈希 |
| 29 | L1487 等 | t_retire_ttl 等用例依赖墙钟与硬编码 2026 日期，改系统时间可能失败 | 时钟注入（Context.now），测试用固定时钟 |

---

## 五、架构层面的优化探讨

### 5.1 现状的结构性矛盾

```
bootstrap_v3.py（2415 行 / 119 def / 68 测试 / 单一 sha256 信任锚）
├─ SOURCES 纯数据（REGISTRY/TUNABLES/LAWS/LEVELS/PACKAGES …）
├─ 完整性基件（hash / Merkle / hash-chain / schema / DAG）
├─ 渲染器（7 个 render_*）
├─ 9 个子命令域（absorb×2 / verify / build / install / engine×10 ops / guard×3 / migrate）
├─ 68 个内联自测（占全文约一半篇幅）
└─ argparse CLI
```

矛盾点在于：**公理 E（文件自哈希）只约束"交付物是单文件"，并不要求"开发态是单文件"**。当前把数据、领域逻辑、网络对账、渲染、迁移、测试全部塞进同一个信任锚，导致：测试噪声进入自哈希基；全局 DATA_DIR 让所有函数隐式耦合；任何改动都在 2400 行里寻找口径。

### 5.2 目标形态（保持单文件交付，开发态分层 + 构建期 bundle）

1. **开发态分包**：`sources.py`（纯数据，唯一事实源）/ `integrity.py`（chain、merkle、原子写、锁）/ `schema.py`（类型化校验）/ `engine.py`（条目语义与检索）/ `installer.py`（交付与校验）/ `render.py` / `registry_verify.py`（网络）/ `migrate.py` / `tests/`。
2. **构建期 bundle**：一个 30 行的打包器把上述模块按固定顺序拼接成单文件 `bootstrap_v3.py` 并计算自哈希——对外仍然是一个可抄录锚点的单文件，对内可独立测试、独立 review。测试留在 bundle 外（或 bundle 时可剥离的尾段），信任锚只锚运行代码。
3. **Commit 原语（最高优先级重构，同时消灭 P0-5/P2-19 与大量重复）**：

   ```python
   def commit(lib, action, audit_text="", state_mutator=None):
       with lib_lock(lib):                       # 库级锁，防链分叉
           if audit_text: chain_append(lib/"audit", audit_text)
           ledger_append(lib, action, ...)       # 账本
           st = load_state(lib)                  # 统一 state 读写
           if state_mutator: state_mutator(st)
           st["merkle_root"] = merkle_root(lib, exclude={"state.json"})
           atomic_write_json(lib/"state.json", st)  # tmp + os.replace
   ```
   所有写操作只声明"改什么 state"，不再手写四步序列；shadow/reflect/guard 的口径问题随之消失。
4. **领域异常替代 sys.exit**：24 处 `sys.exit` 埋在领域函数里，使 engine 无法被 harness 作为库嵌入（而 referee/reflect-synthesis 的设计恰恰要求 harness 调用），测试只能 catch SystemExit。定义 `BootstrapError(code, msg)`，CLI 层统一映射退出码（0/1/2 的语义顺便写进 --help）。
5. **显式 Context 替代模块全局态**：`Context(data_dir, lib, now, net)` 贯穿命令；时钟可注入（顺带解决 P2-29）、多库并行、测试零 monkeypatch。
6. **单一文件分类器**：`classify(rel)` 一处定义 delivered/rendered/runtime/tool_output/env_trace/foreign，校验模式、doctor、guard 快照共用，消灭 P1-10/P1-11 类盲区。渲染产物用"渲染函数→输出路径"注册表自动枚举，不再维护 RENDER_NAMES 名单。
7. **检索层诚实化**：现状是 rglob 全扫 + 子串计数。短期：中文 n-gram/分词、统一打分口径、删掉或实现死参数；中期：倒排索引（让 index_hot_budget 名副其实），eval 基线改"只升不降的最佳签收线"。
8. **升级语义产品化**：install 校验模式识别档位/包差异 → `--upgrade` 增量交付（L8/L9 过令牌）→ 账本 level-change，补掉 P1-6。

### 5.3 修复路线图建议

| 阶段 | 内容 | 对应条目 |
|---|---|---|
| 立即（小改动、守铁律） | id 白名单与落盘路径断言；retire 不覆盖；全库 id 唯一；证据真值校验；shadow/reflect/guard 补刷根 | P0-1/2/3、P1-7、P0-5 临时版 |
| 短期 | eval 基线不回写；档位差异提示；absorb-md 建最小 state、禁假日期；classify 统一；LF/路径分隔统一；state 原子写+锁；空集/空参数友好退出；runner 兜 BaseException | P0-4、P1-6/9/10/11/12/13/15、P2-16/19 |
| 中期 | Commit 原语重构；领域异常分层；增量 Merkle/批量挂根；死参数清理或实现；测试 fixture 自洽 | P0-5 根治、P1-8/14、P2-17/18/20 |
| 长期 | 开发态分包 + bundle 单文件交付；检索层实现；升级通道产品化 | 5.2 全部 |

---

## 六、值得肯定、应当保留的设计

- 公理 → 机器不变式 → `assert`/测试的闭环（如 LAWS 数量、A14 纠错纪念碑、objective hacking 措辞守卫），把"曾经犯过的错"固化成不可回退的测试，这是工业级做法。
- verify 的 match/mismatch/error 三态分离与"离线不计入通过"，在个人工具里很少见这种诚实性设计。
- 幂等安装校验（漂移/未在册/渲染件/根对账四视图）、redeliver 显式授权、bodies removed 镜像，方向正确——问题只在分类口径分散，不是思路问题。
- write_bytes 修 CRLF 漂移、bytes 落盘与 manifest 哈希对账，说明对"哈希口径"有实战级敏感（本次 P2-16 只是没推广到全部落盘点）。
- 测试以行为断言为主（68 个、大量负向用例），且函数自注册 registry，避免了手写测试清单的漂移。

---

## 附录：动态实证记录（2026-09-08，Python 3.14.7 / Windows，临时目录隔离）

15 项探针全部复现（断言描述的是"正确代码应有行为"，REFUTED 即现版本缺陷确认）：

```
[CONFIRMED] A 空 source_event_id 通过校验（errs=[]）           → P1-7
[CONFIRMED] B id="../../../pwned" 文件写出库外                       → P0-1
[CONFIRMED] C shadow 后 state 根 ≠ 重算根（e3e9… vs 23c7…）     → P0-5
[CONFIRMED] D L2 库请求 install L9 被静默忽略，仍报 L2          → P1-6
[CONFIRMED] E eval 空集 ZeroDivisionError                      → P1-12
[CONFIRMED] F 同 id 在 intermediate+longterm 双写成功           → P0-3
[CONFIRMED] G guard 无模式参数 TypeError                        → P1-13
[CONFIRMED] H anchor_snapshot.json 被报未在册                  → P1-11
[CONFIRMED] I skills/wrap-up.md 手改检测不到                    → P1-10
[CONFIRMED] J eval exit2 同时用 0.0 覆盖了 1.0 基线             → P0-4
[CONFIRMED] K 无 state 的 absorb-md 库 wrapup 崩溃              → P1-9
[CONFIRMED] L retire 覆盖 attic 同名旧文件（违反铁律1）         → P0-2
[CONFIRMED] M AGENTS.md 落盘为 CRLF                            → P2-16
[CONFIRMED] N except Exception 兜不住 SystemExit               → P1-15
[CONFIRMED] O resolve 缺依赖模块仍进 got                       → P1-14
```

> 探针脚本与本报告、架构可视化同目录留存，可复跑：`python -X utf8 probe.py`。
