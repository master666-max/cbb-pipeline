# -*- coding: utf-8 -*-
"""重排器.py — 本地重排模型统一客户端（U-F04~F06 共用；2026-09-23）

职责（能力落地-工单 深融条款）：给四个岗位提供"分数/排序"能力，**只影响先看谁，不影响算不算对**。
端点：llama.cpp `/v1/rerank`（U-F01 已打通，CUDA 常驻 8081）；响应 `results[{index, relevance_score}]`。

纪律：
  · **缺席即降级**：端点不可用/格式异常 → 返回 None，调用方落机械排序（产出同形）——绝不抛异常打断主链
  · **可注入传输层**：测试零网络（transport 注入）；真调用走 urllib，请求体强制 UTF-8
  · **确定性**：同输入同分数（评分模型无采样）；并列名次用稳定排序
"""
from __future__ import annotations

import json
import os
import urllib.request

DEFAULT_ENDPOINT = os.environ.get("RERANK_HTTP", "http://127.0.0.1:8081/v1/rerank")
DEFAULT_MODEL = "qwen3-reranker-4b"


def _http(endpoint: str, payload: bytes, timeout: float) -> str:
    req = urllib.request.Request(endpoint, data=payload,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8")


def score(query: str, documents: list[str], endpoint: str | None = None,
          timeout: float = 120.0, transport=None) -> list[float] | None:
    """批量打分：返回与 documents 对齐的相关分列表；**任何异常→None**（调用方降级）。"""
    if not documents:
        return []
    payload = json.dumps({"model": DEFAULT_MODEL, "query": query,
                          "documents": documents}, ensure_ascii=False).encode("utf-8")
    try:
        raw = (transport or _http)(endpoint or DEFAULT_ENDPOINT, payload, timeout)
        data = json.loads(raw)
        results = data.get("results") or []
        if len(results) != len(documents):
            return None
        out = [0.0] * len(documents)
        for r in results:
            out[int(r["index"])] = float(r.get("relevance_score") or 0.0)
        return out
    except Exception:
        return None


def order(query: str, documents: list[str], endpoint: str | None = None,
          timeout: float = 120.0, transport=None) -> list[int] | None:
    """返回按相关分降序的**下标序列**（稳定排序）；不可用→None。"""
    scores = score(query, documents, endpoint, timeout, transport)
    if scores is None:
        return None
    return sorted(range(len(documents)), key=lambda i: -scores[i])


def available(endpoint: str | None = None, timeout: float = 8.0) -> bool:
    """探活：一次真实单对打分是否成功。"""
    return score("探活", ["测试文档"], endpoint, timeout) is not None


def rerank_order_or_mechanical(query: str, docs: list[str], mechanical_order: list[int],
                               endpoint: str | None = None, transport=None) -> tuple[list[int], str]:
    """岗位共用入口：重排可用→重排序；不可用→机械序。**返回 (顺序, backend)**——两载体同形由调用方保证。"""
    o = order(query, docs, endpoint, transport=transport)
    return (o, "rerank") if o is not None else (mechanical_order, "mechanical")
