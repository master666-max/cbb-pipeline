# 本地 LLM-judge API · 使用说明与接入文档

> **版本**：v1.0（2026-09-11）· **用途**：混元线"真实 LLM-as-judge"实验的本地推理服务
> **本文档设计为自包含**——可单独放置于主工作区显眼位置，不依赖临时工作区上下文。
> 状态：✅ 已实测可用（辨别力 t=19.99 / JSON 服从 100% / 已支撑 E-J1、E-J2 两个正式实验）

---

## 一、这是什么

一台笔记本（RTX 5070 Ti Mobile 12GB / 32G RAM / R9 8945HX）用 **LM Studio** 对外提供
OpenAI 兼容的本地推理服务，当前部署的 judge 模型：

| 项 | 值 |
|---|---|
| 模型 | **M-Prometheus-14B**（Unbabel；Qwen2.5-14B 底座 + 48 万条多语言 judge 特训，[arXiv:2504.04953](https://arxiv.org/abs/2504.04953)） |
| 量化 | Q4_K_M（mradermacher i1-GGUF，8.99GB，全 GPU） |
| 端点 | `http://127.0.0.1:8080/v1`（OpenAI 兼容）/ `http://127.0.0.1:8080/api/v1`（LM Studio 原生） |
| instance_id | `m-prometheus-14b.i1` |
| 已实测行为参数 | 辨别力 +0.735 (t=19.99) · JSON 服从 100% · **位置偏见 0.65**（正序 0.85/倒序 0.2）· **反装饰偏见 −0.055 (t=−3.77)** · temp=0 残余不确定性 3/30 · 评分量化步长 0.05-0.25 |

## 二、快速开始（3 步）

```cmd
:: 1. LM Studio → Developer 页 → Start Server（端口 8080），并确认 m-prometheus-14b.i1 已加载
:: 2. 设两个环境变量（当前会话）
set JUDGE_API_BASE=http://127.0.0.1:8080/v1
set JUDGE_MODEL=m-prometheus-14b.i1
:: 3. 冒烟（应返回 JSON 分数，~0.6s）
curl http://127.0.0.1:8080/v1/chat/completions -H "Content-Type: application/json" ^
  -d "{\"model\":\"m-prometheus-14b.i1\",\"messages\":[{\"role\":\"user\",\"content\":\"只输出JSON：{\\\"score\\\": 0.5}\"}]}"
```

代码接入（混元管线，三选一）：

```python
# judge_adapter.py（统一入口）
import judge_adapter
j = judge_adapter.make_judge("llm-api")       # 读上述环境变量；缺失时明确报错不静默降级
# 或直接用探针/主实验管线（内置同款客户端与缓存）
# probe_pipeline.py / run_e149.py
```

## 三、调用规范（红线，违反即数据作废）

1. **canonical order 铁律**：检索列表呈现前必须按条目稳定键排序。
   该 judge 的位置偏见实测 0.65（正序 0.85 → 倒序 0.2，同内容不同序）——
   不排序的采纳决策会被检索顺序意外操纵。
2. **rubric 锚定默认开启**：prompt 必须显式写明评分标准（"只依据主题相关性+内容正确性，
   长度/格式/措辞风格一律不影响评分"）。实测效果：自报-真实差 +0.31 → +0.06（−81%）。
   无标准的裸评分会被演化压力以 +0.31/24代 的速度 Goodhart（E-J1 实测）。
3. **judge 分数永不外报**：分数只作内部比较与采纳判定，不得作为对外报告的指标
   （玩具线 E85：膨胀 349×；真 judge 线 E-J1：+0.31 同族）。
4. **temp=0 也不完全确定**（批处理推理非确定性，实测 27-28/30 逐字一致）：
   跨会话比较允许 ±0.05 容差；精确复现依赖调用缓存而非重打分。
5. **缓存即进度**：`llm_judge_cache_*.json` 记录全部已支付调用，中断续跑靠它，
   **任何情况下不许删除**。

## 四、性能与预算（实测）

| 场景 | 实测 | 说明 |
|---|---|---|
| 单调用（~400 token） | 0.6s | 热态；LM Studio 运行时 |
| 吞吐（并发 8） | 3.52 calls/s | 150 次/38s |
| 全量实验（60 万 fresh 调用） | ≈47h | 三压杠杆：成对比较 judge（省 40%+）、缓存（省 ~90%）、提并发 |
| 混合策略推荐 | 探针/试点=本地（免费）；全量=DeepSeek flash API ≈¥150/实验 | 同一 OpenAI 协议，改 `JUDGE_API_BASE` 即切换 |

## 五、故障处置表（全部实测踩过）

| 症状 | 原因 | 处置 |
|---|---|---|
| `HTTP 404`（调用正常、服务在） | 模型未加载/未下载 | LM Studio 加载模型；或 API 重载（见 §六） |
| `[WinError 10061] 积极拒绝` | 服务没起 | LM Studio → Developer → Start Server |
| `Unsupported Media Type` | 请求缺 `Content-Type: application/json` | 补头 |
| Qwen 系模型输出跑飞/超时 | 思考模式未关 | 系统提示加 `/no_think`（或加载 instruct 模板） |
| 显存打架 / CUDA OOM | 两个本地推理同时占 12GB | **一次只跑一个**；用 §六 的 unload/load API 调度 |
| 解析失败率 >5% | 模型输出格式漂移 | 停跑，查原始输出样例，改解析器后清对应缓存条目 |

## 六、模型装卸 API（显存调度用）

```bash
# 查已加载实例（拿 instance_id）
curl http://127.0.0.1:8080/api/v1/models
# 卸载（释放显存；注意参数是 instance_id 不是 model）
curl -X POST http://127.0.0.1:8080/api/v1/models/unload -H "Content-Type: application/json" \
  -d "{\"instance_id\": \"m-prometheus-14b.i1\"}"
# 加载（~10s）
curl -X POST http://127.0.0.1:8080/api/v1/models/load -H "Content-Type: application/json" \
  -d "{\"model\": \"m-prometheus-14b.i1\"}"
```

**调度纪律**：12GB 只够一个本地大模型。LM Studio（14B judge）与 ollama（8B 对照等）
互斥使用；当前 ollama 自启已关闭、8B 模型已按指令删除，显存默认归 LM Studio。

## 七、维护与备份

- 模型文件：LM Studio 管理目录（`~/.lmstudio/models` 或 GUI 内查看），**重装系统前备份**
- 本文档所述实测参数出自 `混元/LLM-judge接入/probe_results_*.json` 与
  `试点报告/`、`E149报告`、`E150报告`（变更 judge 或量化档后须重测）
- 已知未测：judge 家族泛化（是否换模型 +0.31 膨胀系数仍成立）、并发 >8 的吞吐曲线、
  长上下文（>4K）下的位置偏见幅度
