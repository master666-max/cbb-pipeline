# -*- coding: utf-8 -*-
"""cbb_gate1.py — CBB P4 门1：确定性规则硬校验（M1 骨架）

四校验（G1-SCHEMA / G1-EVIDENCE / G1-REF / G1-TIME_INVERSION）→ 拦截附原因码。
纯函数：无 LLM、无网络、无时钟；同输入必同判定（verdict_id 内容哈希）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "contracts"))
sys.path.insert(0, str(HERE.parent / "cbb-coordinate"))
sys.path.insert(0, str(HERE.parent / "cbb-anchor"))
import cbb_contracts  # noqa: E402
import cbb_coordinate  # noqa: E402
import cbb_anchor  # noqa: E402

REASON_CODES = ("G1-SCHEMA", "G1-EVIDENCE", "G1-REF", "G1-TIME_INVERSION")

# 拦截 → 隔离区分组（M1 暂定映射，SKILL.md 已标【待确认】，issues/ 在案）
REASON_TO_QUARANTINE_GROUP = {
    "G1-TIME_INVERSION": "unresolved_time",
    "G1-REF": "ambiguous_reference",
    "G1-SCHEMA": "low_confidence",
    "G1-EVIDENCE": "low_confidence",
}

THREE_STATE_SINKS = ("confirmed", "provisional", "quarantine")


def _vid(record_id: str, codes: list[str]) -> str:
    h = hashlib.sha256(f"{record_id}|{'|'.join(sorted(codes))}".encode("utf-8")).hexdigest()[:12]
    return f"g1-{h}"


def _check_schema(rec: dict) -> list[dict]:
    try:
        cbb_contracts.validate_record(rec, allow_candidate=True)
        return []
    except cbb_contracts.ContractViolation as e:
        return [{"code": "G1-SCHEMA", "detail": f"{e.path}: {e.message}"}]


def _check_evidence(rec: dict, blocks: list[dict]) -> list[dict]:
    out = []
    evs = rec.get("evidence") or []
    if not evs:
        return [{"code": "G1-EVIDENCE", "detail": "evidence 为空（B4 无证据不入库）"}]
    for i, ev in enumerate(evs):
        if not cbb_contracts.evidence_ok(ev):
            out.append({"code": "G1-EVIDENCE", "detail": f"证据[{i}] 四元组不完整: {ev!r}"})
            continue
        if blocks is not None and cbb_coordinate.locate_quote(
                blocks, ev["vol"], ev["chapter"], ev["quote"]) is None:
            out.append({"code": "G1-EVIDENCE",
                        "detail": f"证据[{i}] quote 悬空（坐标块内不可回落）: "
                                  f"v{ev['vol']}c{ev['chapter']} {ev['quote'][:20]}…"})
    return out


def _check_refs(rec: dict, known_ids) -> list[dict]:
    if known_ids is None:
        return []
    out = []
    canon = rec.get("canonical") or {}
    for field in ("causal_predecessors", "entity_refs"):
        for rid in canon.get(field) or []:
            if rid not in known_ids:
                out.append({"code": "G1-REF", "detail": f"canonical.{field} 引用悬空: {rid}"})
    sup = rec.get("supersedes")
    if sup is not None and sup not in known_ids:
        out.append({"code": "G1-REF", "detail": f"supersedes 引用悬空: {sup}"})
    return out


def _resolve_day(rec, records_by_id: dict) -> dict | None:
    """取记录的 day 精度故事时间（canonical.story_time），否则 None。"""
    st = (rec or {}).get("canonical", {}).get("story_time")
    if isinstance(st, dict) and st.get("precision") == "day" and isinstance(st.get("day_offset"), int):
        return st
    return None


def _check_time_inversion(rec: dict, records_by_id: dict) -> list[dict]:
    canon = rec.get("canonical") or {}
    preds = canon.get("causal_predecessors") or []
    own = _resolve_day(rec, records_by_id)
    if own is None or not preds:
        return []
    max_pred_day = None
    unresolvable = False
    for pid in preds:
        pst = _resolve_day(records_by_id.get(pid), records_by_id)
        if pst is None:
            unresolvable = True  # 有前驱时间不可比 → 保守放行给门2/人工，不硬判
            continue
        d = pst["day_offset"]
        max_pred_day = d if max_pred_day is None else max(max_pred_day, d)
    if unresolvable or max_pred_day is None:
        return []
    if own["day_offset"] < max_pred_day:
        cmp = {"precision": "day", "day_offset": max_pred_day}
        assert cbb_anchor.compare_story_time(own, cmp) == -1  # 语义自证：早于前驱
        return [{"code": "G1-TIME_INVERSION",
                 "detail": f"事件 day_offset={own['day_offset']} 早于前驱最大 "
                           f"day_offset={max_pred_day}"}]
    return []


def check_record(rec: dict, ctx: dict) -> dict:
    """单记录门1。ctx: {blocks: list|None, known_ids: set|None, records_by_id: dict|None}"""
    blocks = ctx.get("blocks")
    known = ctx.get("known_ids")
    records_by_id = ctx.get("records_by_id") or {}
    violations = (_check_schema(rec) + _check_evidence(rec, blocks)
                  + _check_refs(rec, known) + _check_time_inversion(rec, records_by_id))
    codes = [v["code"] for v in violations]
    return {
        "record_id": rec.get("record_id", "?"),
        "verdict": "intercept" if violations else "pass",
        "violations": violations,
        "quarantine_group": REASON_TO_QUARANTINE_GROUP.get(codes[0]) if codes else None,
        "gate_trace_entry": {"gate": "1", "verdict_id": _vid(rec.get("record_id", "?"), codes)},
    }


def check_batch(candidates: list[dict], ctx: dict | None = None) -> dict:
    """批量过门。返回 {passed:[检查结果], intercepted:[{check, record}], summary}。
    幂等：纯函数，重跑同结果。"""
    ctx = ctx or {}
    own_ids = {c.get("record_id") for c in candidates if c.get("record_id")}
    known = ctx.get("known_ids")
    if known is not None:
        known = set(known) | own_ids  # 候选间互引合法（同批沉淀）
    records_by_id = dict(ctx.get("records_by_id") or {})
    for c in candidates:
        records_by_id.setdefault(c.get("record_id"), c)
    ctx2 = {**ctx, "known_ids": known, "records_by_id": records_by_id}

    passed, intercepted = [], []
    for rec in candidates:
        chk = check_record(rec, ctx2)
        if chk["verdict"] == "pass":
            passed.append(chk)
        else:
            intercepted.append({"check": chk, "record": rec})
    return {
        "passed": passed,
        "intercepted": intercepted,
        "summary": {"total": len(candidates), "pass": len(passed),
                    "intercept": len(intercepted),
                    "by_code": {c: sum(1 for it in intercepted
                                       if any(v["code"] == c for v in it["check"]["violations"]))
                                for c in REASON_CODES}},
    }


def three_state_write_stub(record: dict, out_root: Path, status: str):
    """三态写入桩（M1）：与其他 cbb-* 同纪律——三池分目录、ID 命名、已存在即跳过。"""
    if status not in THREE_STATE_SINKS:
        raise ValueError(f"非法三态 {status!r}")
    rid = record.get("record_id") or record.get("block_id")
    if not rid:
        raise ValueError("record 缺 record_id/block_id")
    sink = Path(out_root) / status
    sink.mkdir(parents=True, exist_ok=True)
    path = sink / f"{rid}.json"
    if path.exists():
        return path, False
    path.write_text(json.dumps(record, ensure_ascii=False, sort_keys=True, indent=1),
                    encoding="utf-8")
    return path, True


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="CBB P4 门1 确定性硬校验（M1 骨架）")
    ap.add_argument("--candidates", required=True, help="cbb-extract 候选 JSON（{candidates:[…]}）")
    ap.add_argument("--manifest", default=None, help="坐标 manifest JSON（供证据回落校验）")
    ap.add_argument("--known-ids", default=None, help="已知记录 ID 清单 JSON 数组（可选）")
    args = ap.parse_args(argv)

    payload = json.loads(Path(args.candidates).read_text(encoding="utf-8"))
    cands = payload["candidates"] if isinstance(payload, dict) else payload
    ctx = {"blocks": None, "known_ids": None}
    if args.manifest:
        ctx["blocks"] = json.loads(Path(args.manifest).read_text(encoding="utf-8"))["blocks"]
    if args.known_ids:
        ctx["known_ids"] = set(json.loads(Path(args.known_ids).read_text(encoding="utf-8")))
    result = check_batch(cands, ctx)
    print(f"[gate1] total={result['summary']['total']} "
          f"pass={result['summary']['pass']} intercept={result['summary']['intercept']} "
          f"by_code={ {k: v for k, v in result['summary']['by_code'].items() if v} }")
    return 0


if __name__ == "__main__":
    sys.exit(main())
