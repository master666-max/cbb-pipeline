# task-073 · research-hub 建线迁入：衔尾蛇-自演化内核

- 日期：2026-09-21/22
- 线：衔尾蛇线（ZCode 责任田）
- 依据：用户令「research-hub 建自己的目录，迁入研究内容，写到隔离 agent 读到即能开工」
- 产出：https://github.com/master666-max/research-hub 新目录 `衔尾蛇-自演化内核/`（233 件 56.6K 行，commit e4cde06）

## 做了什么

1. **目录结构**（照仓规：一线一目录、START-HERE 入口、线内自足、被测件锚哈希）：
   - `START-HERE.md`（§0 三十秒现场→§9 交接附言；含复核三路线/硬边界/复算五步/哈希锚/未闭合清单）
   - `纪律与协议/`（SOP v1.2 原样副本 74f251ca + 工作流与双仓结构 + 哈希表）
   - `引擎_正典发布/`（bootstrap_v3.9.py 47b762c7 + RELEASE.md）
   - `运行件-原始proto布局/`（全量 proto 原样布局，路径逻辑不变）
   - `结果报告/`（94 份全量）+ `实测台_库调试工作区/`（45 条目+33 金标+序列+ledger+state）+ 相关材料
2. **仓级索引**：README+AGENTS 各追加本线一行（只加本线行，未改他线）。
3. **推送**：gh 凭据 https 推送成功（99673ed..e4cde06）；**不加 --force**。

## 踩坑与经验（三件）

1. **`git add -A` 在共享克隆里卷进他线未跟踪件**（F1 线 54 件）：初次提交误含他线文件——因未推送，`reset --soft` + 退栈 + 重建提交修复（F1 文件原样未动）；教训=**共享工作区只做精确 add，永不用 -A**。
2. **git show 的中文路径八进制转义骗过 grep**：核对提交构成时 `grep 中文` 得零命中（路径显示为 `\350\241...`）——核对"提交里有没有 X"必须用 `git ls-files`/awk 或 `-c core.quotepath=false`。
3. **临时克隆是共享的**（%TEMP%/research-hub 被多会话共用：CBB/ps-mcp/F1 的提交与未跟踪件同场）：推送前必 fetch，本地历史改动（reset）仅限未推提交。

## 复用提示

- research-hub 的线模板（START-HERE 九节骨架）可直接复用于后续任何研究线迁入。
- 推送通道：`gh auth setup-git` + `git remote set-url --push origin https://...`（SSH 不可用时的正解）。

## 关联

- [[bootstrap-v39-release]]（正典 47b762c7 随迁）
- 远端：master666-max/research-hub @ e4cde06
