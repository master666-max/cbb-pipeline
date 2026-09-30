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
import os
import re

from . import ops

# 判卷契约 v2（缓存前缀改造，2026-09-28）：长静态头（契约+判定标准+判例 few-shot）
# + 短动态尾（载荷由调用方拼接在头之后）——全部请求共享同一前缀，吃满考官端前缀缓存。
# A/B 验收（工单 20260928-B）：20 条前后票型分布一致 + DS usage 命中实测，未过不得放量。
JUDGE_PROMPT = (
    "你是正典库独立考官。给定【证据摘录】与【记录断言】，判定证据是否支持断言。\n"
    "判定标准：\n"
    "一、support：证据摘录直接陈述或无可争议地蕴含断言的全部要素（主体、动作/关系、对象、条件）。\n"
    "二、against：证据与断言不可同真——证据明确否定断言的某一要素，或与断言在同一要素上直接冲突。\n"
    "三、unsure：证据与断言相关但缺少至少一个要素的直接陈述；或存在歧义、指代不明、仅暗示、"
    "需要外部知识补足才能成立。\n"
    "从严倾向：证据不足以支持时选 unsure，不得靠猜测弥补。\n"
    "判例一：证据「他把玉佩递给了沈青梧，说是母亲的遗物」，断言「沈青梧获得玉佩」→ support"
    "（获得与来源两要素均被直接陈述）。\n"
    "判例二：证据「他递给她一件东西」，断言「沈青梧获得玉佩」→ unsure（对象与物品均未指明）。\n"
    "判例三：证据「那枚玉佩早已不知所踪」，断言「沈青梧获得玉佩」→ against（持有状态直接冲突）。\n"
    "判例四：证据「沈青梧玉佩不离身」，断言「沈青梧继承家产」→ unsure（玉佩只是家产的可能旁证，"
    "断言主体要素未被陈述）。\n"
    "输出契约：只输出 JSON：{\"verdict\":\"support|against|unsure\"}。支持=support；"
    "证据与断言不可同真=against；证据不足=unsure。禁止任何其他文字。\n"
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
        mt_env = os.environ.get("EXAMINER_MAX_TOKENS")
        raw = ops.chat_once(cfg["base"], cfg["model"], cfg["key"], prompt,
                            max_tokens=int(mt_env) if mt_env else None)
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


def vote(conclusion: str, evidence: str, panel: list, full_size: int = 3,
         weights: dict | None = None) -> dict:
    """全员隔离投票：≥⌈2/3⌉ support 且 against=0 ⇒ promote；任何 against>0 ⇒ human；
    其余 hold（存续待巡检）。通道异常/编制不满员=降级（显式标注）。
    weights（G13 可选）：{考官kind: 权重}——加权路径下需票=满编权重和×2/3，
    against=0 与 n≥2 硬门不变；None=等权旧行为逐位保持。"""
    votes, errors = {}, []
    for ch in panel:
        try:
            votes[ch.kind] = judge_isolated(ch, conclusion, evidence)
        except Exception as e:  # noqa: BLE001 — LLM 端点异常族宽捕获=缩员降级语义（设计决定）
            errors.append({"examiner": ch.kind, "reason": str(e)[:100]})
    n = len(votes)
    if n == 0:
        return {"verdict": "blocked", "votes": {}, "errors": errors,
                "degraded": True, "口径": "无可用考官——G5 BLOCKED"}
    against = sum(1 for v in votes.values() if v == "against")
    if weights:
        full_w = sum(float(weights.get(ch.kind, 1.0)) for ch in panel) or float(full_size)
        support = sum(float(weights.get(k, 1.0)) for k, v in votes.items() if v == "support")
        need = math.ceil(2 * full_w / 3 * 100) / 100  # 加权需票按满编权重算——缩员不降门槛
        promote_ok = support >= need
        口径 = f"加权评审：support_w={round(support, 2)}/{round(need, 2)}（满编权重 {round(full_w, 2)}）"
    else:
        support = sum(1 for v in votes.values() if v == "support")
        need = math.ceil(2 * full_size / 3)  # B13：需票按满编制算——缩员不得自动降门槛
        promote_ok = support >= need
        口径 = None
    if against > 0:
        verdict = "human"  # 任何异构反对=真分歧信号，必须人工裁决
    elif promote_ok and n >= 2:
        verdict = "promote"  # B13：单考官无异构性可言，不得单独晋升
    else:
        verdict = "hold"
    degraded = len(errors) > 0 or n < full_size
    out = {"verdict": verdict, "votes": votes, "need": need, "against": against,
           "errors": errors, "degraded": degraded,
           "口径": ("降级标注：编制不满或有通道缺席" if degraded else "满编评审")}
    if 口径:
        out["加权口径"] = 口径
    return out


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
