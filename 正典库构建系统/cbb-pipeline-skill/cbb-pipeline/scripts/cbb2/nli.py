# -*- coding: utf-8 -*-
"""cbb2.nli — NLI 双通道矛盾预筛（U-A04）：只分流不裁决（R-019），两通道不一致才人审。

通道：
  LLMChannel   —— OpenAI 兼容本地端点（env NLI_LLM_BASE/NLI_LLM_MODEL；三分判定 JSON）；
  TransformersChannel —— Erlangshen-RoBERTa-110M-NLI 本地小模型（惰性加载；缺 transformers/模型
                          ⇒ ChannelUnavailable ⇒ 降级单通道并显式标注）。
上岗小考 exam()：分离度 ≥0.70 才启用（judge 补考 0.5455 停用先例）；附分桶校准。
"""
from __future__ import annotations

import json
import os
import re
import urllib.request

VERDICTS = ("entails", "neutral", "contradicts")
_PROMPT = (
    "你是中文自然语言推理判定器。给定【前提】与【假设】，只输出一个 JSON 对象："
    '{"verdict":"entails|neutral|contradicts"}。'
    "前提能推出假设=entails；前提与假设不可同真=contradicts；其余=neutral。"
    "禁止输出任何其他文字。"
)


class ChannelUnavailable(RuntimeError):
    """通道不可用（缺依赖/缺 env/端点不在位）——降级单通道并标注，不崩。"""


class LLMChannel:
    name = "llm"

    def __init__(self, base: str | None = None, model: str | None = None, api_key: str = ""):
        self.base = base or os.environ.get("NLI_LLM_BASE", "http://127.0.0.1:8080/v1")
        self.model = model or os.environ.get("NLI_LLM_MODEL", "")
        self.api_key = api_key or os.environ.get("NLI_LLM_API_KEY", "")

    def available(self) -> bool:
        return bool(self.base and self.model)

    def judge(self, premise: str, hypothesis: str) -> str:
        if not self.available():
            raise ChannelUnavailable("NLI_LLM_BASE/NLI_LLM_MODEL 未配置")
        from .ops import chat_once
        raw = chat_once(self.base, self.model, self.api_key,
                        f"{_PROMPT}\n【前提】{premise}\n【假设】{hypothesis}")
        m = re.search(r"\{[^}]*\}", raw, re.DOTALL)
        if not m:
            raise ValueError(f"LLM 判定非 JSON：{raw[:80]!r}")
        verdict = json.loads(m.group(0)).get("verdict")
        if verdict not in VERDICTS:
            raise ValueError(f"LLM 判定非法：{verdict!r}")
        return verdict


class TransformersChannel:
    name = "roberta-nli"

    def __init__(self, model_id: str | None = None):
        self.model_id = model_id or os.environ.get(
            "NLI_LOCAL_MODEL", "IDEA-CCNL/Erlangshen-RoBERTa-110M-NLI")
        self._pipe = None

    def available(self) -> bool:
        try:
            import transformers  # noqa: F401
            return True
        except ImportError:
            return False

    def _load(self):
        if self._pipe is None:
            try:
                from transformers import pipeline
                self._pipe = pipeline("text-classification", model=self.model_id)
            except Exception as e:  # 模型下载失败/不兼容 ⇒ 通道降级
                raise ChannelUnavailable(f"本地 NLI 通道不可用: {type(e).__name__}: {str(e)[:120]}")
        return self._pipe

    def judge(self, premise: str, hypothesis: str) -> str:
        pipe = self._load()
        out = pipe({"text": premise, "text_pair": hypothesis}, top_k=None)
        scores = {x["label"].lower(): float(x["score"]) for x in out}
        label_map = {"entailment": "entails", "neutral": "neutral",
                     "contradiction": "contradicts"}
        best = max(scores, key=scores.get)
        return label_map.get(best, best)


def dual_judge(premise: str, hypothesis: str,
               channels: list) -> dict:
    """两通道独立判定：一致→采纳；不一致→verdict=None（人审队列）；单通道可用→降级标注。
    计票键=序号:通道名（同名通道不互相覆盖）。"""
    votes, unavailable = {}, []
    for i, ch in enumerate(channels):
        try:
            votes[f"{i}:{ch.name}"] = ch.judge(premise, hypothesis)
        except ChannelUnavailable as e:
            unavailable.append({"channel": ch.name, "reason": str(e)[:120]})
    if not votes:
        return {"verdict": None, "agree": False, "votes": {}, "degraded": True,
                "unavailable": unavailable, "human_queue": True}
    if len(votes) >= 2:
        agree = len(set(votes.values())) == 1
        verdict = next(iter(votes.values())) if agree else None
        return {"verdict": verdict, "agree": agree, "votes": votes,
                "degraded": False, "unavailable": unavailable, "human_queue": not agree}
    only = next(iter(votes.values()))  # 单通道降级：出票但标注（分流可用，非裁决）
    return {"verdict": only, "agree": False, "votes": votes,
            "degraded": True, "unavailable": unavailable, "human_queue": False}


def exam(judge_fn, cases: list[dict]) -> dict:
    """上岗小考：cases=[{premise,hypothesis,label(entails|contradicts)}+]（neutral 不计分离度）。
    分离度=与标签一致率；<0.70 ⇒ {"pass": False}（停用保守路由）。附置信分桶校准
    （judge_fn 返回 (verdict, confidence|None)；confidence=None 记 uncalibrated 桶）。"""
    total = hit = 0
    buckets: dict[str, dict] = {}
    for c in cases:
        out = judge_fn(c["premise"], c["hypothesis"])
        verdict, conf = out if isinstance(out, tuple) else (out, None)
        total += 1
        ok = verdict == c["label"]
        hit += ok
        key = "uncalibrated" if conf is None else f"{min(0.99, max(0.0, conf)):.1f}"
        b = buckets.setdefault(key, {"n": 0, "hit": 0})
        b["n"] += 1
        b["hit"] += ok
    separation = hit / total if total else 0.0
    calib = {k: {"n": v["n"], "accuracy": round(v["hit"] / v["n"], 3)}
             for k, v in sorted(buckets.items())}
    return {"separation": round(separation, 4), "pass": separation >= 0.70,
            "total": total, "calibration": calib}
