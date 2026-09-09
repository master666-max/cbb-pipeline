# CONTRACT · 多 Agent 协作契约（{{SLOT:DATE}} 建立）

> ⚠ 装包时必须与用户逐条确认后才生效。

## 分工
- {agent-A}：{负责域}
- {agent-B}：{负责域}

## 写权限
- agents/{name}/：各自全权。
- knowledge/ 共享层：可写，但条目必须带 agent 署名行。
- archive/：只追加。

## 冲突处理（核心规则）
- 后写让先写：新条目与已有条目冲突时，**修订旧条目（升版本）**而非新建对抗条目。
- 无法自行裁决的冲突 → 列入 knowledge/协作教训库.md 并标【待确认】等用户。

## 会话纪律
- 每 agent 会话开始读 CONTRACT.md + knowledge/_index.md；结束时各自跑 wrap-up（只动自己分区+共享层署名条目）。
