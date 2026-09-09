# exp9-sleep-pipeline · 睡眠固化管线 + 闸门（BCA 3.4）

## 装什么
SLEEP.md 固化流程升级 + tools/sleep_gate.txt（三道闸门）。依赖 exp9-dual-memory + exp9-dmn（可选）。

## install.md 步骤
1. 复制 scripts/sleep_gate.txt → tools/。
2. SLEEP.md 追加固化管线：取高重要性 trajectory（重要性分排序）→ agent 提炼草稿 → 闸门 → 双写（皮层语义库 + state/DISTILL.md 蒸馏候选集，注记"冻结底座仅存档"）。
3. 复制 template/DISTILL.md → state/。
4. 校验点：sleep_gate 对三条坏草稿（无证据链接/措辞越界/与既有冲突）全拦截。

## 三道闸门（可执行检查）
①证据校验：实例链接 exists（复用 lint 逻辑）②措辞纪律：禁第一人称情绪断言（"让我/我高兴/感到"→打回）③去重/冲突扫描：[[关键词]] 与既有条目撞车→打回。

## 溯源
BCA 3.4（离线回放 + 审核器防污染）；DQN experience replay 工程近亲；本库月度 cron 睡眠整理升级。
