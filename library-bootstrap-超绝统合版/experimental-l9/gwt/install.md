# exp9-gwt · GWT 广播总线（BCA 3.3）

## 装什么
tools/broadcast.txt（仲裁脚本：显式竞争"谁写入上下文窗口"）+ state/PENDING.md（落选队列）。依赖 exp9-goalstack + exp9-dual-memory。

## install.md 步骤
1. 复制 scripts/broadcast.txt → tools/；template/PENDING.md → state/。
2. task-start 第 1 步改为：「先跑 tools/broadcast.txt --task "{任务描述}" 拿广播清单，再按清单读条目」（取代自由翻索引）。
3. 候选源 = {search 输出, PENDING 队列, reflections 摘要, 工具输出}；打分 = 任务相关性 × 情绪调制项；落选降级进 PENDING（不丢弃）。
4. 校验点：broadcast 空任务跑通输出「无候选」；PENDING 存在。

## 机理
上下文窗口就是全局工作空间——不发明，只把"谁有权写入"从隐式变显式（BCA 原话）。任务相关性来自 GOALS + 关键词；arousal 放大探索类候选，certainty 压低猜测类候选。

## 溯源
BCA 3.3 GWT 广播总线；本库 task-start 三因子检索的竞争版。
