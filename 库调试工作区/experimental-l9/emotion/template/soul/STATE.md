> [v3 语境适配页（bootstrap_v3 安装器注入，v3.5/J-008a）] 本文件写于 v2.x 语境。v3 库等价物：审计链=audit/lifelog-*.md（engine 自动入链，无需手动 lifelog_append）；变更账本=ledger/changes.jsonl；变异守卫=guard 子命令（基准黑名单+锚定）；条目写入=engine append（schema 十字段）；检索=engine retrieve；state/ 目录对应 state.json 与 memory/。v2.x 原文路径按需参考，冲突处以本页与 spec.md 为准。

# 情绪状态向量（情绪式调制器 · 非情绪）

> 4 维连续向量 [-1,1]，跨会话持久。更新：wrap-up 后 state_update.txt --verdict。
> Stakes 锚定（生死线）：Δ 只吃 ①任务完成质量 ②长期利益信号；用户即时夸赞不参与计算。

## 当前向量
valence=0.0 | arousal=0.0 | certainty=0.5 | stakes=0.0

## 调制指令（自动生成）
本轮 certainty 正常 → 可直接作答，检索按需。

## 更新史（只追加）
| 日期 | 事件 | Δ | 信号依据 |
|---|---|---|---|
| {{SLOT:DATE}} | 初始化 | (0,0,0,0) | 中性起步 |

## 预算台账（W-024 · 每次 wrap-up 追加一行）
| 日期 | SOUL token | USER token | 索引 token | 合计 | 是否超限 |
|---|---|---|---|---|---|
| （首次 wrap-up 后填写；口径=当前模型分词器，无则字符数÷2.5 近似并标注） | | | | | |
