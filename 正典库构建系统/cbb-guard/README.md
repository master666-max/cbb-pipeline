# cbb-guard · CBB 守门插件（v0.1.3）

> 形态裁定 2026-09-24：①**项目级**安装 ②hook"二拦二警"照准（拦①冻结线覆盖②红区 Write；决策账与副本漂移不进 hook）③命令中文名。
> 安装形态＝**本地市场直接引用版本源**（`./cbb-guard`，零拷贝＝零漂移，T-8 纪律）。
> **v0.1.2 根解析跨项目通用**：不再硬编码任何实例路径——env `CBB_GUARD_ROOT` 显式指定 > cwd 向上找 CBB 项目标记（决策账.jsonl / \*-本体库 / \*-工作区）> 回落 cwd。保护面=命名惯例谓词（\*-本体库／\*-工作区／\*-工单.md／\*-发车件.md／build-state.md（带前缀与裸名两种）／决策账.jsonl／cbb/contracts/），**与根解耦、全局按名判定**——任何按惯例命名的项目自动受保护。
> **v0.1.3 两处修**（都来自一次外部审计的实测，不是读码猜）：
> ① 冻结线补**裸名 `BUILD-STATE.md`**——`init_project.py` 默认产出的文件名就是它，而旧谓词 `-(?:…|build-state)\.md$` 要求前面有连字符 ⇒ **最该护的那份恰好不拦**；旧 38 例夹具里没有这条用例，所以"38/38 全绿"与"门有洞"同时成立。
> ② **随仓附 Qoder 方言钩子**（`hooks/hooks.qoder.json` ＋ `.qoder-plugin/plugin.json`）——旧仓只给 ZCode 方言，README 把翻译工作派给安装者却不提供译好的件，直装到 Qoder 得到的是**一个不执行、也不报错的门**。见下「装到非 ZCode 宿主」。

## 它拦什么

| 规则 | 触发 | 处置 |
|---|---|---|
| A 冻结线原位保全 | Write/Edit/Bash 覆盖或清理**惯例命名的冻结面**（`*-本体库/`、`*-工作区/` 及其下文件；`工单/发车件/build-state` 三类文书，带前缀与裸名都算）的**已有文件** | **exit 2 拦截**（新建文件放行——additive 不算覆盖） |
| B 红区 Write | `cbb/contracts/*.schema.json`、在案工单、`决策账.jsonl` 的 **Write 整体覆盖**（Edit 追加放行） | **exit 2 拦截** |

拦截回执必带一行 `命中：<规则> · <触发片段>`（v0.1.1）——没有命中面的拦截无法排障，会被读成宿主故障。

**旁通（唯一合法通道）**——两种形态，都自动追加 `hook-bypass` 条目到该项目根的 `决策账.jsonl`：

| 形态 | 写法 | 作用域 |
|---|---|---|
| 绑定式（推荐） | `CBB_HOOK_BYPASS='<目标路径前缀>=<裁定引用>'` | 只放行落在该前缀下的**那一次越权**；目标不在其下 ⇒ 照拦 |
| 全局式（旧写法，兼容保留） | `CBB_HOOK_BYPASS='<裁定引用>'` | 放行一切越权；每次使用在 stderr 打一行提醒，入账记 `scope:"global(全规则)"` |

v0.1.1 起旁通的两条硬性质：**① 只在确有越权时生效**（挂着 env 做无关写不会往决策账里灌条目，也不会被记账成"越权"）；**② 无留痕不越权**（账写不进去——根路径指错、目录不存在、文件不可写——直接拒绝放行并给出原因码；v0.1.0 是静默放行＋零留痕）。
`CBB_GUARD_ROOT` 归一后不存在而旁通又设着时，会打一行"根不存在"警告（不拦无关写，但绝不静默）。

## 它不拦什么（裁定原文）

- 决策账先写后动 → **工具内断言**（自决策层 U-E02），不进 hook；
- 副本漂移 → **`/状态报告` 常设项**（＋可选每日自动任务），不进 hook；
- Bash 里的**间接写**（python 脚本内部写文件）→ 只看命令行正则，拦不到。见末节「落点自陈」。

## 三条命令

`/cbb-guard:批次自检` ／ `/cbb-guard:状态报告` ／ `/cbb-guard:覆盖复算` ——薄壳，只编排既有脚本与手工配方；脚本缺席时报明确错误。

## 安装（项目级 · 本地市场 · ZCode）

注册表已登记：`known_marketplaces.json`（cbb-local → `cbb-marketplace/`）＋ `installed_plugins.json`（cbb-guard@cbb-local，installPath=版本源本体）。**新会话生效**（当前会话的插件加载是启动时快照）。
卸载＝删两条注册表项＋删 `.bak` 前缀的备份恢复。

## 装到非 ZCode 宿主（Qoder／Claude Code）——**必做，否则门是哑的**

钩子条目是**宿主方言**，不通用。仓里两份都在，别再手抄翻译：

| 宿主 | 清单目录 | 钩子文件 | 关键字段差异 |
|---|---|---|---|
| ZCode | `.zcode-plugin/` | `hooks/hooks.json` | `type:"process"`、`timeoutMs`（毫秒）、`${ZCODE_PLUGIN_ROOT}` |
| Qoder | `.qoder-plugin/` | **`hooks/hooks.qoder.json`** | `type:"command"`、`timeout`（**秒**）、`${QODER_PLUGIN_ROOT}`、**`async:false`**（同步返回才拦得住） |
| Claude Code | `.claude-plugin/` | `hooks/hooks.qoder.json` 同形态，但根变量是 `${CLAUDE_PLUGIN_ROOT}`，需改一处 |

Qoder 直装步骤：① 把插件放进 `<宿主配置目录>/plugins/cache/<source>/cbb-guard/<version>/`（**目录末段必须等于 version**）；② 清单用 `.qoder-plugin/plugin.json`；③ **把 `hooks/hooks.qoder.json` 复制成该安装位里的 `hooks/hooks.json`**（宿主按这个文件名读）；④ `settings.json#enabledPlugins` 里 `"cbb-guard@<source>": true`；⑤ 重启宿主后**新会话**生效。

### 装完必验（这一步不是可选的）

**本机 `node guard.mjs` 跑绿，不代表宿主会执行它**——方言不匹配时宿主根本不派发，门静默不存在。
装完在新会话里做一次真越权写，必须拿到拦截：

1. 拿一个**已存在**的 `*-本体库/` 下文件路径，用工具的 Write 覆盖一次 → **期望被拦**（exit 2，回执带命中面）；
2. 裸名 `BUILD-STATE.md` 覆盖一次 → **期望被拦**（v0.1.3 起；0.1.2 及以前会放过，可用来验自己装的是哪版）；
3. 无关新文件 Write → 期望放行；
4. 三发里第 1、2 发没拦 ⇒ 钩子没被派发，回去核对字段与 `enabledPlugins`，**不要接着干活**。

## 自检（命令行直打，与宿主无关）

```bash
# <根> 换成你的项目根；下面三发只需替换路径，不含任何机器专属值
printf '%s' '{"tool_name":"Write","tool_input":{"file_path":"<根>/X-本体库/ledger.jsonl"}}' | node hooks/guard.mjs   # → exit 2（拦：冻结线覆盖）
printf '%s' '{"tool_name":"Write","tool_input":{"file_path":"<根>/BUILD-STATE.md"}}'          | node hooks/guard.mjs   # → exit 2（拦：v0.1.3 补的裸名）
printf '%s' '{"tool_name":"Write","tool_input":{"file_path":"<根>/新建件.md"}}'                | node hooks/guard.mjs   # → exit 0（放）
```

七发验证（2026-09-24）：冻结覆盖拦✓／新建放✓／红区 Write 拦✓／冻结件 Edit 拦✓／旁通入账✓／Bash 清理拦✓／红区 Edit 放✓。
v0.1.3 追加两发（2026-09-25）：裸名 `BUILD-STATE.md` 覆盖拦✓／其首次新建放✓。

## 回归夹具（随仓发布，改这道门必跑）

```bash
node cbb-guard/tests/guard-suites.mjs                          # 默认打 ../hooks/guard.mjs
git show fccc5c6:cbb-guard/hooks/guard.mjs > g012.mjs          # 上一版基线（本地文件，跨平台）
node cbb-guard/tests/guard-suites.mjs g012.mjs                 # → 41/42，唯一不符项＝裸名 BUILD-STATE.md
```

| 组 | 覆盖面 | 例数 | v0.1.0 基线 | v0.1.1／v0.1.2 | v0.1.3 |
|---|---|---|---|---|---|
| ① 主套 | 真危险 15（含 `&&` 后 rm、`sudo rm`、`xargs rm`、`os.remove`、`shutil.rmtree`、`Remove-Item`、**BUILD-STATE 两种形态**）＋设计放行 15（含**近似词不误伤**、**子目录首次新建**）＋附检 2 | 32 | 不符 9 | 不符 1（漏拦裸名 BUILD-STATE） | 不符 0 |
| ② 旁通路数 | 账可写／账不可写／根不存在／不凭空建目录／无旁通不漏账 | 5 | 不符 2 | 不符 0 | 不符 0 |
| ③ 旁通作用域 | 绑定式覆盖与不覆盖／无关写不入账／全局式入账与提醒 | 5 | 不符 5 | 不符 0 | 不符 0 |
| 合计 | | **42** | **22/38** | **38/38；对 0.1.2 跑 42 例＝41/42** | **42/42** |

夹具全部写在临时夹具根里（跑完自删），不碰真实项目根。误伤样本（v0.1.0 拦、v0.1.1 放）：命令里出现
`cbb-guard`、`third`、`record`、`platform`、`warm`、`standard`、`confirm` 这类以 `rm`/`rd`/`del` 收尾的普通词，
且同条命令提到冻结名。写夹具时注意：临时目录名也别带这类词，否则"该拦"例会靠误伤假通过。
另一条自证式教训：夹具**必须包含被测门自己产出的默认文件名**——38 例全绿却漏掉 `BUILD-STATE.md`，
是因为用例路径全是手写的带前缀形态。

## 版本

- **0.1.3（2026-09-25）**：G-5 冻结线补裸名 `BUILD-STATE.md`（`init_project.py` 默认产出名，旧谓词要求连字符前缀 ⇒ 恰好不拦；夹具 38→42 例，含"近似词不误伤"与"首次新建放行"两条反面护栏）；G-6 随仓附 Qoder 方言钩子（`hooks/hooks.qoder.json`＋`.qoder-plugin/plugin.json`）与"装完必验"步；三份清单与 `marketplace.json` 版本对齐（此前 marketplace.json 停在 0.1.1 而 plugin.json 已是 0.1.2）。规则范围：冻结面**扩大**一种形态（裸名 build-state），其余不变。
- **0.1.2（2026-09-25）**：根解析四级（env > cwd 向上找 CBB 标记 > cwd 子目录 > 回落 cwd），废除硬编码迷深默认路径；保护面与根解耦、全局按名判定；拦截回执带命中面；旁通绑定式＋无留痕不越权（承 0.1.1 四修）。
- **0.1.1（2026-09-24）**：G-1 清理动词改独立词匹配＋补真删除 API（误伤 7／漏拦 1 → 0）；G-2 旁通留痕写不进即拒绝放行（原为静默放行且零留痕）；G-3 旁通改为**先判越权再谈放行**＋绑定式作用域＋无关写不灌账；拦截回执加命中面；根路径不存在时显式警告；回归夹具 `tests/guard-suites.mjs` 入仓。规则范围未扩大也未缩小。
- 0.1.0（2026-09-24）：首版，二拦二警裁定落地。

## 落点自陈

本插件的强制力＝**进程退出码**（L4：能拦）；但它拦不到 Bash 里的间接写（如 python 脚本写文件）——只看 Write/Edit/MultiEdit 的 file_path 与 Bash 命令行正则。删掉本插件目录＝守门消失（这也是它自己的落点）。
再加一条 v0.1.3 才补上的落点：**"装了"不等于"在拦"**。钩子方言不合宿主时，门既不执行也不报错，与从来没装过完全同形——所以「装完必验」是安装的一部分，不是排障手段。
