# X-Corpus · 语料分析库特色包

## 定位
长文本/整本书的量化分析：清洗规则库 + 统计范式库 + 三层数据流目录约定。机制层复用双库。

## 装什么（叠加在 L≥2 上）
| 模板 | 目标 | 说明 |
|---|---|---|
| template/knowledge/清洗规则库.md | knowledge/清洗规则库.md | 规则条目（R 系，注意与反思 R 系区分——检索时带「清洗」词） |
| template/knowledge/统计范式库.md | knowledge/统计范式库.md | 分析脚本范式（A 系） |
| template/data-layout.md | data/ 目录约定 | raw → interim → processed 单向流 |

## install.md 步骤
1. 复制两知识库模板。
2. 建 data/{raw,interim,processed}/ 三目录（raw 只读纪律写入 README）。
3. wrap-up 复盘特化：清洗规则改动是否记条目？clean_report 与脚本头注释一致吗？
4. 校验点：data 三目录存在；raw/README 含「只读」。

## 溯源
本工作区语料分析项目实战（517 章清洗 + clean_report.json 全量化；PT-003）。
