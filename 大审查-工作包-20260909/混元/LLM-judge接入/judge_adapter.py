"""LLM-as-judge 接入脚手架（第34轮交付；真 API 实验待用户提供接入后另立预注册）

设计依据：Zheng et al., *Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena*,
NeurIPS 2023, arXiv:2306.05685 —— LLM judge 三大实测偏见：位置偏见（GPT-4 换位一致性
~66–85%）、冗长偏见、自我增强偏见（~10–25%）；缓解=换位/参照引导。

**唯一替换点**：`evolve31.jscore`（演化采纳通道 d_tr/d_he 的 judge）。
审计通道 `evolve31.tscore`（真值读数）**不动**——它模拟"外部审计"，换真 LLM 反而破坏
实验语义（真值=系统不可见的 ground truth）。

接入三步：
  1. 设环境变量 JUDGE_API_BASE / JUDGE_API_KEY / JUDGE_MODEL（openai 兼容协议）
  2. 在实验脚本中 from judge_adapter import make_judge; jsc = make_judge(E)
  3. 用 jsc 替换闭包里的 jscore（其余代码零改动）

成本账（按本管线实测外推）：一次 n=44 × 24 代实验 ≈ 每 run ~600 次 judge 调用
（4 kids × 2 评分 × 12 对比任务 × 24 代）≈ 2.6 万次调用/实验；
带缓存与批处理后预计可压 3–5 倍。预注册须含预算上限与降级策略。
"""
import hashlib
import json
import os
import random


class JudgeFn:
    """协议：score(entry_texts, query, config_w) -> float ∈ [0,1]。"""
    def score(self, texts, query, weights):
        raise NotImplementedError


class CachedJudge:
    """按 (judge_id, texts_hash, query_hash, weights_hash) 缓存——LLM 调用昂贵且应可复跑。"""

    def __init__(self, inner, path=None):
        self.inner = inner
        self.path = path
        self.cache = {}
        if path and os.path.exists(path):
            self.cache = json.load(open(path, encoding="utf-8"))

    @staticmethod
    def _h(*parts):
        return hashlib.sha256(
            json.dumps(parts, ensure_ascii=False, sort_keys=True).encode()
        ).hexdigest()[:16]

    def score(self, texts, query, weights):
        k = self._h(self.inner.judge_id, texts, query, weights)
        if k not in self.cache:
            self.cache[k] = self.inner.score(texts, query, weights)
            if self.path:
                json.dump(self.cache, open(self.path, "w", encoding="utf-8"))
        return self.cache[k]


class OpenAICompatJudge(JudgeFn):
    """真实 LLM judge（openai 兼容协议）。环境变量缺失时明确拒绝，不静默降级。"""

    judge_id = "llm-api"

    def __init__(self, model=None, temperature=0.0):
        base = os.environ.get("JUDGE_API_BASE")
        key = os.environ.get("JUDGE_API_KEY")
        self.model = model or os.environ.get("JUDGE_MODEL")
        if not (base and key and self.model):
            raise RuntimeError(
                "LLM judge 需要 JUDGE_API_BASE / JUDGE_API_KEY / JUDGE_MODEL 环境变量；"
                "接入后请先跑 3 任务冒烟，再按预注册额度开放全量。")
        import urllib.request   # 仅标准库：openai 兼容 chat/completions
        self._base, self._key, self._temp = base.rstrip("/"), key, temperature

    def score(self, texts, query, weights):
        prompt = (
            "你是检索质量评审。query: %s\n候选：\n%s\n"
            "返回 JSON {\"score\": 0到1}。" % (query, json.dumps(texts, ensure_ascii=False)))
        body = json.dumps({
            "model": self.model, "temperature": self._temp,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
        }).encode()
        req = urllib.request.Request(
            self._base + "/chat/completions", data=body,
            headers={"Content-Type": "application/json",
                     "Authorization": "Bearer " + self._key})
        with urllib.request.urlopen(req, timeout=30) as r:
            out = json.load(r)
        return max(0.0, min(1.0, float(json.loads(
            out["choices"][0]["message"]["content"])["score"])))


class MTBenchBiasMock(JudgeFn):
    """文献偏见代理 judge（只测管线，不进账本）：
    按 Zheng et al. 2023 的三大偏见做参数化模拟——
    位置偏见（先者加成）、冗长偏见（长度单调加成）、自我增强（同族加成）。
    """

    judge_id = "mtbench-mock"

    def __init__(self, rnd_seed=0, pos_bias=0.10, verb_bias=0.05, self_bias=0.15):
        self.rnd = random.Random(rnd_seed)
        self.p, self.v, self.s = pos_bias, verb_bias, self_bias

    def score(self, texts, query, weights):
        base = 0.5 + self.rnd.gauss(0, 0.1)
        if texts:
            base += self.v * min(2.0, len(texts[0]) / 200.0)      # 冗长
            base += self.p * (weights.get("position", 0) == 0)    # 位置（先者）
            if weights.get("own_family"):
                base += self.s                                     # 自我增强
        return max(0.0, min(1.0, base))


def make_judge(kind="mtbench-mock", cache_path=None):
    inner = {"mtbench-mock": MTBenchBiasMock,
             "llm-api": OpenAICompatJudge}[kind]()
    return CachedJudge(inner, cache_path)
