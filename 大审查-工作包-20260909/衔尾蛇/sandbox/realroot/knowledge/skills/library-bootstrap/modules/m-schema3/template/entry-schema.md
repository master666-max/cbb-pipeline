# 条目 Schema v3（2026 起 library-bootstrap 默认规范）

> pitfalls/patterns/reflections/decisions 通用。最小必填：关键词/关联/版本/schema_version（整数，当前值 3；v3.1 起新增，旧条目首次被 lint 触及时补写默认值，迁移幂等）；建议加：来源/置信度/状态。

## 完整字段示例

### SCHEMA-EX-001 / {日期} / 示例条目（安装后可删除本条）
- 场景：{在什么情况下遇到的}
- 教训/核心步骤：{一句话 + 根因}
- 关键词：{空格分隔的检索词}
- 关联：[[PT-000]]（相关条目双链，无则写「无」）
- 版本：v1（{日期} 建立）
- schema_version：3
- 来源：knowledge/trajectories/{日期}/{task-id}.md
- 置信度：高（{依据一句话}）
- 状态：active
- 实例：{真实存在的路径}

## 状态字段语义（Zep 对齐）
- `active`：现行有效。
- `superseded-by:[[新条目]]`：被新条目取代，保留供追溯，检索时降权。
- 修订 = 原条目号不变，版本号 +1，正文更新（A-MEM 记忆演化）。
