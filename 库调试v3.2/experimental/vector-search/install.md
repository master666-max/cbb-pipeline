# EXP-vector-search · 向量语义检索（实验）

> ⚠ L7 实验模块。稳定性 ★：依赖第三方库与模型，随上游变化可能失效。触发条件（雷达）：条目 >100 才值得。

## 做什么
给 search_knowledge.txt 补语义检索：条目嵌入 → 本地向量索引 → 关键词检索无命中时语义兜底。

## 安装步骤
1. 前置确认（必须）：`pip install scikit-learn`（TF-IDF 无模型方案）或本地 embedding 模型；探测失败则本模块不装，退回 L6。
2. 复制 exp_vector_search.txt 到目标 tools/。
3. 跑一次构建索引命令，产物 tools/.vec_index.pkl（gitignore 掉）。空库（0 条目）时 `--build` 应输出「空库：暂无条目…」并 exit 0——若崩溃说明脚本被改坏。
4. **显式补装（勿漏）**：在目标 `knowledge/skills/wrap-up/SKILL.md` 第 5 步「更新 trajectory 轨迹文件（只追加）。」之后插入一行：
   `- 若启用 vector-search（L7）且本期有条目新增/修订：跑 {{SLOT:PY_RUNNER}} tools/exp_vector_search.txt --build 重建向量索引。`
   改完入链：`tools/lifelog_append.txt "补装 wrap-up 向量索引重建步骤"`。
5. 校验点：wrap-up SKILL 含「exp_vector_search.txt --build」字样；空库 `--build` 不崩。
6. 检索入口不变；search 无命中时自动调语义兜底。

## 已知风险（装前必须向用户明示）
- 第三方依赖破坏「纯标准库」承诺，E-manual 环境不可用。
- 中文分词无 jieba 时 TF-IDF 精度有限。
- 索引需在每次条目变更后重建（wrap-up 追加重建步骤）。

## 溯源
雷达图 C 派（HippoRAG/Zep）；本工作区 D-001 决策「条目 <500 不上向量」，本模块是触发条件命中后的先遣试验田。
