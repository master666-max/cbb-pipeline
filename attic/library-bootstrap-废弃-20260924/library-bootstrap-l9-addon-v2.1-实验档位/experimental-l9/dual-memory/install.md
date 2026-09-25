# exp9-dual-memory · 双速率记忆（BCA 3.2 · CLS 互补学习系统）

## 装什么
海马体侧：trajectory 结构化头规范（时间戳/情绪快照/重要性分）；皮层侧：只由睡眠管线写入的纪律。依赖 exp9-emotion（重要性分=情绪向量范数）。

## install.md 步骤
1. 复制 template/trajectory-header.md → knowledge/trajectories/FORMAT.md（新轨迹文件头规范）。
2. search_knowledge.txt 追加情绪重排说明（注释内）：「命中后按唤起度匹配（当前 arousal/certainty vs 条目快照）重排；certainty 低时强制检索」。
3. wrap-up 第 6 步追加：给本任务 trajectory 打重要性分（= 情绪向量范数 × 目标相关度）。
4. 校验点：FORMAT.md 存在；既有 trajectory 从下一条起带快照头（历史不回溯改——只增不改纪律）。

## 海马体/皮层分工
- 海马体（快）：trajectories，一次成型只追加。
- 皮层（慢）：pitfalls/patterns/reflections，只由 wrap-up（白日小固化）与睡眠管线（批量大固化）写入，人类可读。

## 溯源
BCA 3.2（杏仁核-海马通路：情绪强度决定固化优先级）；CLS 理论。
