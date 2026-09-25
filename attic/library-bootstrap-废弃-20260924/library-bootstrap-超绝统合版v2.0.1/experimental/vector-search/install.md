# EXP-vector-search · 向量语义检索（实验）

> ⚠ L7 实验模块。稳定性 ★：依赖第三方库与模型，随上游变化可能失效。触发条件（雷达）：条目 >100 才值得。

## 做什么
给 search_knowledge.txt 补语义检索：条目嵌入 → 本地向量索引 → 关键词检索无命中时语义兜底。

## 安装步骤
1. 前置确认（必须）：`pip install scikit-learn`（TF-IDF 无模型方案）或本地 embedding 模型；探测失败则本模块不装，退回 L6。
2. 复制 exp_vector_search.txt 到目标 tools/。
3. 跑一次构建索引命令，产物 tools/.vec_index.pkl（gitignore 掉）。
4. 检索入口不变；search 无命中时自动调语义兜底。

## 已知风险（装前必须向用户明示）
- 第三方依赖破坏「纯标准库」承诺，E-manual 环境不可用。
- 中文分词无 jieba 时 TF-IDF 精度有限。
- 索引需在每次条目变更后重建（wrap-up 追加重建步骤）。

## 溯源
雷达图 C 派（HippoRAG/Zep）；本工作区 D-001 决策「条目 <500 不上向量」，本模块是触发条件命中后的先遣试验田。
