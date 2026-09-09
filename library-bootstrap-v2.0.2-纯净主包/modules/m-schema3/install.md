# m-schema3 · 条目结构化元数据（MemCube/Zep/A-MEM 对齐）

## 装什么
条目字段规范文档（knowledge/entry-schema.md）+ pitfalls/patterns 模板头升级（含示例条目 SCHEMA-EX-001，可删）。

## install.md 步骤
1. 复制 template/entry-schema.md → knowledge/entry-schema.md。
2. 在 knowledge/pitfalls.md 与 patterns.md 的格式模板注释里追加 v3 字段行（模板注释在文件尾，追加不覆盖）。
3. 校验点：grep「关键词：」与「版本：」出现在两个文件的模板注释中。

## 新字段（每条目三行起步）
```
- 关键词：{检索用，空格分隔}
- 关联：[[PT-xxx]]（[[条目号]] 双链）
- 版本：v1（{日期} 建立）
- 来源：{trajectory 链接}（可选）
- 置信度：高/中/低（可选）
- 状态：active / superseded-by:[[X]]（可选，默认 active）
```

## 溯源
MemOS MemCube（来源/版本元数据）、Zep 双时态（状态生命周期）、A-MEM（结构化属性）、MemInsight（属性标注）；本工作区 v4 实装 7 条。
