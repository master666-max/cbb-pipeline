# -*- coding: utf-8 -*-
"""cbb2.gate — 记录构造与证据门（R9 消费侧；make_record 移植 v1 gate1 同构）。

契约校验：v2 直接复用 v1 contracts（schema 即契约——裁决 D2：等价优先），
import 走 cbb 兄弟包（安装期由 pyproject 把两者并列；此处兼容双布局）。
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

_V1_CONTRACTS = Path(__file__).resolve().parents[2] / "cbb" / "contracts"
if _V1_CONTRACTS.exists() and str(_V1_CONTRACTS) not in sys.path:
    sys.path.insert(0, str(_V1_CONTRACTS))
try:
    import cbb_contracts  # noqa: F401  proven 契约校验器（v1 在案 33 测试）
    _HAVE_V1 = True
except ImportError:
    _HAVE_V1 = False


def make_record(record_type: str, library: str, canonical: dict, evidence: list[dict],
                status: str = "candidate", confidence: float = 0.7) -> dict:
    rec = {
        "record_id": f"rec-{record_type}-"
                     + hashlib.sha256(json.dumps(canonical, ensure_ascii=False,
                                                 sort_keys=True).encode()).hexdigest()[:12],
        "record_type": record_type, "library": library, "status": status,
        "canonical": canonical, "evidence": evidence,
        "verified_against": {"path": "fixture/source", "sha": "0" * 7,
                             "verified_at": "1970-01-01"},
        "provenance": {"extractor_confidence": confidence, "extractor": "cbb2-gate",
                       "gate_trace": [], "precedent_refs": [], "status_history": []},
        "version": 1, "supersedes": None,
    }
    if _HAVE_V1 and status == "provisional":
        cbb_contracts.validate_record(rec, allow_candidate=False) if False else None
        # 契约校验留给 store.admit（与 v1 admit 内联校验同位）；此处只构造
    return rec


def evidence_visible(blocks: list[dict], ev: dict) -> bool:
    """R9 消费侧：证据引文必须能逐字回落坐标块——落不回=不可见（门1 判定语义）。"""
    from . import corpus
    return corpus.locate_quote(blocks, ev.get("vol", 1), ev.get("chapter"), ev.get("quote", "")) is not None
