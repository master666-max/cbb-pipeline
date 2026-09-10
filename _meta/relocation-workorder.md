# 工单 REL-20260911-01 — 双区架构落地：临时区回灌 + 审计区独立

> 签发：用户裁决 2026-09-11（依据：红队审计后五步勘误已闭环，零点资格维持）
> 执行：本会话（红队→勘误→搬迁执行员；管理员搬家，制图师记账，两职严禁兼任）
> 落位参数：主区=`D:\zcode专用！！！！危险！！！！！！！！！`（git 历史延续，解冻）；
> 临时区=`D:\临时工作区`（回灌源）；审计区=`D:\workspace-audit`（新建，独立 git）

## 〇、侦察结论（2026-09-11 实测，工单前提）

| 项 | 实态 |
|---|---|
| zero-point-v1 tag | **未打**（本工单第 0 步补打） |
| 主区 HEAD | `1247786`（阶段11+11.5 完成终 commit） |
| 主区未提交改动 | ①上轮红队勘误四件（workspace-audit/ 内，本工单第 0 步 commit）②**用户自有改动**（迷深清洗工作/、knowledge/trajectories/ 等）——**严禁卷入本工单任何 commit** |
| 临时区顶层 | 无 git；三个子目录：`大审查-工作包-20260909/`（338MB，118,873 文件，**自带 .git 21MB**，HEAD=`a84fd6e`）、`大审查2/`（2.2MB，16 文件，今日核验包，无 git）、`.v2c/`（1 文件工具缓存） |
| 工作包性质 | 主区 `大审查/` 的 hash 级等价可工作副本（打包时 82,878/82,878 对账一致，见其 工作包说明.md），冻结期工作全在内（混元31-34轮/LLM-judge/衔尾蛇13轮等）；内含第二个嵌套 git `zcode/.git`（HEAD=`e91bdef`） |
| 主区 `大审查` | **gitlink**（mode 160000，主区从不跟踪其内部文件）→ 工作包整目录并入**零路径冲突**（主区根无 `大审查-工作包-20260909`、无 `大审查2`） |
| 目标位 | `D:\workspace-audit` 不存在 ✓ |
| 红队产物 | 主区根 `red-team-report.csv` + `red-team-output/`（40MB，未跟踪；内含 sandbox-root 39MB 复现工作台）→ 随审计区迁出 |

## 一、操作序列（顺序不可乱）

### 第 0 步 双方证据保全（先记录后动手）
1. 主区 commit 上轮勘误（**严格限定四个路径**，禁 `git add -A`）：
   `git add workspace-audit/99-MAP.md workspace-audit/delta-baseline.csv workspace-audit/incident-log.csv workspace-audit/errata-log.md`
   → commit `AUDIT-ERRATA: 红队审计勘误五步落地（audit-log还原/S2=方法论-02/S7修正行/终审结论/errata首建）`
2. 补打 `git tag zero-point-v1`（打在勘误 commit：零点=审计修正后的完整状态；宇宙文件与 1247786 零差异，账本以 errata 登记的追加为准）
3. 工作包 git（临时区原位，只加 tag 不动工作树）：`git tag pre-backflow-20260911`；记录 HEAD=`a84fd6e`、`zcode/.git` HEAD=`e91bdef`
4. 临时区顶层无 git → 证据保全=第 1 步并入清单的全量 sha256（清单即快照）
**验收**：`git tag -l` 见 zero-point-v1；工作包 `git tag -l` 见 pre-backflow-20260911

### 第 1 步 临时区并入主区
1. 生成 `_meta/tmp-merge-manifest.csv`：临时区全部宇宙文件逐条 `{rel_path,size,sha256,disposition}`
   disposition∈{merge（新路径并入）/excluded-git（嵌套 .git 历史不并入，留临时区原位）/excluded-cache（.v2c 工具缓存留原地）/identical（主区已有同 hash 同名，跳过）}
2. 复制（robocopy /E /XD .git，排除两级嵌套 .git）：
   `大审查-工作包-20260909/` 与 `大审查2/` 整目录并入主区根（**同名不覆盖陷阱的化解方式=整目录新路径并入，主区 大审查/ 原位一字不动**；"工作包算新版本还是分支"=判断活，留给下一轮增量制图，本工单不做任何合并裁决）
3. 逐文件 sha256 对账：manifest vs 主区落位，**118,495/118,495 全等** 才许 commit
4. `git add "大审查-工作包-20260909" "大审查2" "_meta"` → commit `MERGE: 临时工作区并入 [工作包HEAD=a84fd6e pre-backflow-20260911]`
**验收**：对账零差异；commit 后 `git status` 中用户自有改动（迷深清洗等）保持原样未被卷入

### 第 2 步 审计区迁出（内容逐字节不变）
1. `robocopy workspace-audit → D:\workspace-audit /E`；红队产物 → `D:\workspace-audit\red-team\`（含 sandbox-root 实体，gitignore 排除其跟踪）
2. 逐文件 sha256 对账 → 生成新家 `出生证明.md`（迁出源 commit/tag + 全量 sha256 清单）
3. 新家 `git init` → 写入 `ANCHOR-PROTOCOL.md`（第 3 步）+ `HANDOVER.md`（第 4 步）→ `git add -A && git commit -m "BORN: 迁出自主区 <tag后hash>，文件清单+sha256 见出生证明.md"`
4. 主区：`git rm -r workspace-audit/`（git 记录删除=它从这里离开；历史与 tag 里它永远在——审计区是仪器，仪器搬家不违反"永不删除"，被保护的是实验宇宙与账本行）；未跟踪的 `red-team-report.csv`/`red-team-output/` 复制核对后删源（移动语义）
5. 主区根写存根 `workspace-audit-MOVED.md`（去向+迁出时点+锚点验证命令）
6. 主区 `HANDOVER.md` 末尾追加搬迁段（append-only）
7. commit `AUDIT-EXIT: 审计区迁出，留存根`（add 限定：删除记录+存根+HANDOVER）
**验收**：新家 `git log` 首条 BORN；逐文件 hash 新家=迁出时点；主区工作区无 workspace-audit/ 残留

### 第 3 步 锚点解析协议 v2（写入新家 ANCHOR-PROTOCOL.md）
- 冻结纪元断言（zero-point-v1 之前入账）：一律 `git show zero-point-v1:<路径>` 解析——tag 兜底，主区随便改
- 实验纪元新断言（增量制图起）：锚点升级 `file@commit:line`，钉死生成时 commit；**禁止对可写文件使用裸路径锚点**（S1 移动目标快照教训的制度化封堵）
- 跨区引用：审计区→主区按上述协议；主区→审计区只读参照

### 第 4 步 时序纪律（并入 ≠ 入账）
- 临时区成果进主区后账本一个字不动：不手工补断言、不翻转 status、不顺手写结论
- 语义入账=下一轮增量制图：扫描范围 `zero-point-v1..HEAD`，工作包/大审查2 作为新宇宙成员机械提取、带锚点入账，被翻转的旧断言走 supersede
- 增量制图扫描**跳过一切元文件**：主区 `_meta/`、`workspace-audit-MOVED.md`、`HANDOVER.md`、`.v2c/`、审计区整体

### 第 5 步 主实验点火（不在本工单范围，交接文件给入口）
10-branch-proposals.md 排序表第一条（P-A1 总法则七验），七字段预注册 → 执行 → 每步 commit。

## 二、陷阱清单（执行时逐条打钩）
- [ ] 任何主区 commit 禁 `git add -A`（用户迷深改动在树上，绝不卷入）
- [ ] robocopy /XD .git 必须生效（嵌套 git 进主区会变 gitlink 噪音）；工作包 .git 历史靠 tag+清单保全，不迁移
- [ ] `.v2c/` 工具缓存不并入（主区已有同名目录）
- [ ] 复制必须先于删除（迁出侧同一纪律：先对账后 rm）
- [ ] 新家 sandbox-root 加 .gitignore（39MB 工作台不入库，实体保留防证据丢失）
- [ ] 长路径兜底 `git config core.longpaths true`
- [ ] 出生证明里的 hash 清单在 git init **之前**生成亦可，但 BORN commit 必须包含出生证明自身

## 三、回滚
每步一个 commit，`git revert/reset --hard <上一步>` 可逐步回退；临时区与工作包 .git 全程原位不动=终极回滚点。
