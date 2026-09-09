# 语料分析（完成于 2026-09-01）

> manifest 归档（D-001）：本体未搬移，位于 `语料分析/`。

## 一句话
对《迷深》web 版整本小说（迷深.epub，517 章）做提取、清洗与量化分析，产出干净全文语料与章节/人物统计。

## 复现
- 环境：Windows + `py`（依赖 BeautifulSoup）
- 运行：`py 语料分析/extract_text.py` → `py 语料分析/scripts/01_clean_normalize.py` → `py 语料分析/scripts/02_tokenize_and_characters.py`
- 最终产物：`语料分析/corpus/clean_full.txt`（约 16MB 净化全文）+ `语料分析/analysis/` 下 6 份 TSV/JSON

## 数据流
迷深.epub →（extract_text.py，含 cp437 文件名修复）→ corpus/mishen_full.txt
→（scripts/01_clean_normalize.py，规则见脚本头注释）→ corpus/clean_full.txt + analysis/clean_report.json
→（scripts/02_tokenize_and_characters.py）→ analysis/chapter_index.tsv、chapter_character_counts.tsv、character_candidates.tsv 等

## 关键决策
- 脚本头部注释即清洗规则文档，clean_report.json 与脚本一一对应，保证复现链可追溯。
- 中间产物 epub_extracted/ 保留不删（原始证据纪律）。

## 踩坑与经验
- 教训：pitfalls.md#p-002（ZIP 文件名乱码必须修复，否则章节定位失准）
- 范式：patterns.md#pt-003（语料清洗与统计分析流水线）

## 复用提示
- ★★☆ 中：换一本 EPUB，改 extract_text.py 里的文件名与输出路径即可；清洗规则（噪声章判定）需按新书调整。

## 未竟事项
- character_candidates.tsv 的人物候选尚未人工确认（clean_report.json 显示 530 万字正文已就绪）。
