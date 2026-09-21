# -*- coding: utf-8 -*-
"""cbb_contracts.py — 四契约 v2.0 加载与校验（Record / Issue / Verdict / Case）

契约是全系统唯一跨层接口（CBB v1.0 Part XVII 不变量 1：新组件接入必先实现契约）。
v2.0（本体构筑 U-B01，源自 U-A17 §3 契约层修订）在 v1.0 最小校验器上扩展：
  - schema 关键字新增 maximum / pattern；
  - Verdict 三项语义强制：critique 键序先于 label（evals-skills 次序强制）、
    confidence_band 与 confidence(0-100) 分带一致（>90=high/80-90=medium/<80=low）、
    label=conflict 时 rule_applied 必填（两派并陈裁决文书化）；
  - Case 配对强制：retrieval_hints.counter_example_of 非空 → counter_example 三段式必填。
仍用 stdlib 实现，不引第三方依赖（P1 骨架纪律沿用）。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

SCHEMA_DIR = Path(__file__).resolve().parent

# B1：库中记录只有 confirmed / provisional；candidate 是入库前状态，quarantine 走隔离区。
# 用户裁决 2026-09-15：不增设第四态（cut 以 supersedes+归档覆盖）。
LIBRARY_STATUSES = ("confirmed", "provisional")
CANDIDATE_STATUS = "candidate"
QUARANTINE_STATUS = "quarantine"
THREE_STATE_SINKS = ("confirmed", "provisional", "quarantine")

_EVIDENCE_KEYS = ("vol", "chapter", "line", "quote")  # B4 证据四元组

# basic-memory 观察分类词表 15 类照录 + CBB 自增 4 类（status_change/relation/alias/knowledge）
OBSERVATION_CATEGORIES = (
    "summary", "event", "tone", "technique", "quote", "significance", "foreshadowing",
    "arc", "trait", "manifestation", "evolution", "appearance", "interpretation",
    "atmosphere", "example",
    "status_change", "relation", "alias", "knowledge",
)

# Verdict 裁决规则表学派（claude-book 冲突解决表 + worldbook 首次出场基准，两派并陈）
VERDICT_SCHOOLS = ("first_appearance", "later_books", "documented_variance",
                   "show_over_tell", "most_common")

# 可信度分带（evals-skills 校准三带）：>90=high / 80-90=medium / <80=low
def confidence_band(confidence: float) -> str:
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
        raise ContractViolation("$.confidence", f"非数值置信 {confidence!r}")
    if confidence > 90:
        return "high"
    if confidence >= 80:
        return "medium"
    return "low"


class ContractViolation(Exception):
    """契约违规。message 携带 JSON 路径，供门1原因码 G1-SCHEMA 消费。"""

    def __init__(self, path: str, message: str):
        self.path = path
        self.message = message
        super().__init__(f"{path}: {message}")


def load_schema(name: str) -> dict:
    path = SCHEMA_DIR / f"{name}.schema.json"
    if not path.exists():
        raise FileNotFoundError(f"契约 schema 不存在: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _type_ok(inst, t: str) -> bool:
    if t == "object":
        return isinstance(inst, dict)
    if t == "array":
        return isinstance(inst, list)
    if t == "string":
        return isinstance(inst, str)
    if t == "integer":
        return isinstance(inst, int) and not isinstance(inst, bool)
    if t == "number":
        return isinstance(inst, (int, float)) and not isinstance(inst, bool)
    if t == "boolean":
        return isinstance(inst, bool)
    if t == "null":
        return inst is None
    raise ContractViolation("$schema", f"未知类型 {t!r}")


def _check(inst, schema: dict, path: str = "$") -> None:
    if "enum" in schema and inst not in schema["enum"]:
        raise ContractViolation(path, f"值 {inst!r} 不在枚举 {schema['enum']}")
    t = schema.get("type")
    if t is not None:
        types = t if isinstance(t, list) else [t]
        if not any(_type_ok(inst, x) for x in types):
            raise ContractViolation(path, f"类型应为 {t}，实为 {type(inst).__name__}")
    if isinstance(inst, dict):
        for key in schema.get("required", []):
            if key not in inst:
                raise ContractViolation(path, f"缺必填字段 {key!r}")
        for key, sub in schema.get("properties", {}).items():
            if key in inst:
                _check(inst[key], sub, f"{path}.{key}")
    if isinstance(inst, list):
        if "minItems" in schema and len(inst) < schema["minItems"]:
            raise ContractViolation(path, f"元素数 {len(inst)} < minItems {schema['minItems']}")
        item_schema = schema.get("items")
        if item_schema:
            for i, el in enumerate(inst):
                _check(el, item_schema, f"{path}[{i}]")
    if isinstance(inst, (int, float)) and not isinstance(inst, bool):
        if "minimum" in schema and inst < schema["minimum"]:
            raise ContractViolation(path, f"{inst} < minimum {schema['minimum']}")
        if "maximum" in schema and inst > schema["maximum"]:
            raise ContractViolation(path, f"{inst} > maximum {schema['maximum']}")
    if isinstance(inst, str):
        if "minLength" in schema and len(inst) < schema["minLength"]:
            raise ContractViolation(path, f"字符串长度 {len(inst)} < minLength {schema['minLength']}")
        if "pattern" in schema and re.search(schema["pattern"], inst) is None:
            raise ContractViolation(path, f"字符串 {inst!r} 不匹配 pattern {schema['pattern']!r}")


def validate(instance, schema_name: str) -> None:
    """按契约名校验；违规抛 ContractViolation。"""
    _check(instance, load_schema(schema_name), "$")


def validate_record(record: dict, allow_candidate: bool = False) -> None:
    """校验 Record v2.0。allow_candidate=True 时接受 status=candidate（P2 抽取候选态）：
    其余字段仍按契约全量校验（实现：以 provisional 代位走完 schema，再断言原值为 candidate）。"""
    status = record.get("status")
    if status == CANDIDATE_STATUS and allow_candidate:
        proxy = dict(record, status="provisional")
        validate(proxy, "record")
        return
    validate(record, "record")


def validate_issue(issue: dict) -> None:
    validate(issue, "issue")


def validate_verdict(verdict: dict) -> None:
    """校验 Verdict v2.0：schema 全量 + 三项语义强制。"""
    validate(verdict, "verdict")
    # ① 次序强制（evals-skills）：critique 键必须先于 label 键出现（dict 保持插入序=原文键序）
    keys = list(verdict)
    if keys.index("critique") > keys.index("label"):
        raise ContractViolation("$", "次序违规：critique 必须先于 label（先陈述评估再下结论）")
    # ② 分带一致：confidence(0-100) 与 confidence_band 必须匹配
    expected = confidence_band(verdict["confidence"])
    if verdict["confidence_band"] != expected:
        raise ContractViolation(
            "$.confidence_band",
            f"分带不一致：confidence={verdict['confidence']} 应为 {expected!r}，实为 {verdict['confidence_band']!r}")
    # ③ 冲突必附裁决规则：label=conflict 时 rule_applied 必填（两派并陈文书化）
    if verdict["label"] == "conflict" and "rule_applied" not in verdict:
        raise ContractViolation("$.rule_applied", "label=conflict 的 Verdict 必填 rule_applied（裁决规则表）")


def validate_case(case: dict) -> None:
    """校验 Case v2.0：schema 全量 + counter_example 配对强制。"""
    validate(case, "case")
    hints = case.get("retrieval_hints", {})
    if isinstance(hints, dict) and hints.get("counter_example_of") is not None:
        if "counter_example" not in case:
            raise ContractViolation(
                "$.counter_example",
                "counter_example_of 非空时必须提供 counter_example 三段式（原文/错误/正确）")


def evidence_ok(entry: dict) -> bool:
    """证据四元组完整性（B4）：vol/chapter/line 为非负整数、quote 非空字符串。"""
    return (
        isinstance(entry, dict)
        and all(isinstance(entry.get(k), int) and not isinstance(entry.get(k), bool) and entry.get(k) >= 0
                for k in ("vol", "chapter", "line"))
        and isinstance(entry.get("quote"), str)
        and entry.get("quote", "") != ""
    )
