# -*- coding: utf-8 -*-
"""cbb2.promote — 票数晋升制（Phase D·U-D05；流程设计 P6·G5）。

confirmed := provisional ∧ gate1 零违例(调用方核) ∧ **≥⌈2/3⌉ 异构考官隔离评审一致**
             ∧ 存续 N 区段巡检无矛盾（tenure_ok 由调用方传）。
考官通道 env 编制（裁①）：LOCAL（默认 :8080 出厂）/ DEEPSEEK / QWEN——base/model 全 env，
禁硬编码；通道不可用自动降级编制并**显式标注证据语气**。
纠偏三件（SOTA 锚）：考官间隔离（互不可见）、答案对调取均值（位置偏见）、口头置信不信（票数制）。
"""
from __future__ import annotations

import json
import math
import re

from . import ops

JUDGE_PROMPT = (
    "你是正典库独立考官。给定【证据摘录】与【记录断言】，判定证据是否支持断言。\n"
    "只输出 JSON：{\"verdict\":\"support|against|unsure\"}。支持=support；"
    "证据与断言不可同真=against；证据不足=unsure。禁止其他文字。"
)


def examiner_channel(kind: str):
    """env 编制→可调用考官；缺 base/model ⇒ None（编制缩员并显式降级）。"""
    cfg = ops.examiner_env(kind)
    if not cfg["base"] or not cfg["model"]:
        return None
    def ask(conclusion: str, evidence: str, order: str = "ev-first") -> str:
        if order == "ev-first":
            prompt = f"{JUDGE_PROMPT}\n【证据摘录】{evidence}\n【记录断言】{conclusion}"
        else:  # 答案对调：结论先行的反向序
            prompt = f"{JUDGE_PROMPT}\n【记录断言】{conclusion}\n【证据摘录】{evidence}"
        raw = ops.chat_once(cfg["base"], cfg["model"], cfg["key"], prompt)
        m = re.search(r"\{[^}]*\}", raw, re.DOTALL)
        if not m:
            raise ValueError(f"{kind} 考官输出非 JSON：{raw[:60]!r}")
        v = json.loads(m.group(0)).get("verdict")
        if v not in ("support", "against", "unsure"):
            raise ValueError(f"{kind} 考官判定非法：{v!r}")
        return v
    ask.kind = kind  # type: ignore[attr-defined]
    return ask


def build_panel(kinds: tuple[str, ...] = ("LOCAL", "DEEPSEEK", "QWEN")) -> tuple[list, list[str]]:
    """编制装配：可用通道列表 + 降级报告。"""
    panel, missing = [], []
    for k in kinds:
        ch = examiner_channel(k)
        if ch is None:
            missing.append(k)
        else:
            panel.append(ch)
    return panel, missing


def judge_isolated(examiner, conclusion: str, evidence: str) -> str:
    """单考官隔离评审：答案对调两序各判一次，一致才采纳，否则 unsure（位置偏见纠偏）。"""
    a = examiner(conclusion, evidence, order="ev-first")
    b = examiner(conclusion, evidence, order="concl-first")
    return a if a == b else "unsure"


def vote(conclusion: str, evidence: str, panel: list, full_size: int = 3) -> dict:
    """全员隔离投票：≥⌈2/3⌉ support 且 against=0 ⇒ promote；任何 against>0 ⇒ human；
    其余 hold（存续待巡检）。通道异常/编制不满员=降级（显式标注）。"""
    votes, errors = {}, []
    for ch in panel:
        try:
            votes[ch.kind] = judge_isolated(ch, conclusion, evidence)
        except Exception as e:
            errors.append({"examiner": ch.kind, "reason": str(e)[:100]})
    n = len(votes)
    if n == 0:
        return {"verdict": "blocked", "votes": {}, "errors": errors,
                "degraded": True, "口径": "无可用考官——G5 BLOCKED"}
    support = sum(1 for v in votes.values() if v == "support")
    against = sum(1 for v in votes.values() if v == "against")
    need = math.ceil(2 * n / 3)
    if against > 0:
        verdict = "human"  # 任何异构反对=真分歧信号，必须人工裁决
    elif support >= need:
        verdict = "promote"
    else:
        verdict = "hold"
    degraded = len(errors) > 0 or n < full_size
    return {"verdict": verdict, "votes": votes, "need": need, "against": against,
            "errors": errors, "degraded": degraded,
            "口径": ("降级标注：编制不满或有通道缺席" if degraded else "满编评审")}


def promotion_check(record: dict, panel: list, *, tenure_ok: bool,
                    gate_clean: bool = True) -> dict:
    """G5 总门：record 断言+证据 → 票数 + 前置条件。"""
    if not gate_clean:
        return {"verdict": "hold", "口径": "gate1 违例未清"}
    if not tenure_ok:
        return {"verdict": "hold", "口径": "存续区段不足（tenure）"}
    c = record.get("canonical") or {}
    conclusion = json.dumps(c, ensure_ascii=False, sort_keys=True)
    evidence = "；".join(e.get("quote", "") for e in (record.get("evidence") or []))
    if not evidence.strip():
        return {"verdict": "hold", "口径": "证据为空"}
    return vote(conclusion, evidence, panel)
