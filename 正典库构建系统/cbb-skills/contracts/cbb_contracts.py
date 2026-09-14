# -*- coding: utf-8 -*-
"""cbb_contracts.py — 四契约加载与最小校验（Record / Issue / Verdict / Case）

契约是全系统唯一跨层接口（CBB v1.0 Part XVII 不变量 1：新组件接入必先实现契约）。
schema JSON 照抄基线 Part IV；本模块用 stdlib 实现最小校验器，覆盖四 schema 实际用到的
关键字（type/enum/required/properties/items/minItems/minimum），不引第三方依赖（P1 骨架纪律）。
"""
from __future__ import annotations

import json
from pathlib import Path

SCHEMA_DIR = Path(__file__).resolve().parent

# B1：库中记录只有 confirmed / provisional；candidate 是 Part V 状态机的入库前状态，
# 不在 Record.status 枚举内（见 record.schema.json $comment）。
LIBRARY_STATUSES = ("confirmed", "provisional")
CANDIDATE_STATUS = "candidate"
QUARANTINE_STATUS = "quarantine"  # 不入库（B1），走隔离区（cbb-quarantine）
THREE_STATE_SINKS = ("confirmed", "provisional", "quarantine")

_EVIDENCE_KEYS = ("vol", "chapter", "line", "quote")  # B4 证据四元组


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
    if isinstance(inst, str) and "minLength" in schema and len(inst) < schema["minLength"]:
        raise ContractViolation(path, f"字符串长度 {len(inst)} < minLength {schema['minLength']}")


def validate(instance, schema_name: str) -> None:
    """按契约名校验；违规抛 ContractViolation。"""
    _check(instance, load_schema(schema_name), "$")


def validate_record(record: dict, allow_candidate: bool = False) -> None:
    """校验 Record。allow_candidate=True 时接受 status=candidate（P2 抽取候选态）：
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
    validate(verdict, "verdict")


def validate_case(case: dict) -> None:
    validate(case, "case")


def evidence_ok(entry: dict) -> bool:
    """证据四元组完整性（B4）：vol/chapter/line 为非负整数、quote 非空字符串。"""
    return (
        isinstance(entry, dict)
        and all(isinstance(entry.get(k), int) and not isinstance(entry.get(k), bool) and entry.get(k) >= 0
                for k in ("vol", "chapter", "line"))
        and isinstance(entry.get("quote"), str)
        and entry.get("quote", "") != ""
    )
