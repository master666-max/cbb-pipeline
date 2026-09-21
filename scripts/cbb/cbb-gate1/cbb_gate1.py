# -*- coding: utf-8 -*-
"""cbb_gate1.py — CBB 门1：确定性硬校验（本体版 v2 · 三域重构）

三域（story-skills 三域分离架构）：
  validate   结构/schema 域：G1-SCHEMA（契约 v2.0）+ G1-EVIDENCE（证据四元组+坐标回落）；
  links      引用完整性域：G1-REF（引用悬空）+ G1-REL-BACKLINK（关系逆类型 12 对+
             对称 12 项双向回链——"parent"必须被"child"回指，sibling 类要求对称）；
  continuity 连续性域：G1-DEAD-WALK（死人走路）/G1-FORESHADOW-ORDER（伏笔时序倒置）/
             G1-CHEKHOV-OVERDUE（契诃夫枪≥3 章超期）/G1-CONTRADICTION（同字段矛盾）+
             G1-TIME_INVERSION（因果前驱时间倒置，v1 保留）。
吸收（U-A17 §3）：Issue v2.0 落地（每违规→带 fix_action P0-P3+精确命令、
  confidence_caliber=deterministic、cites 强制列的契约合规 Issue）；
  EXPLAIN 拒写（检索层永不写库——check/to_issue 纯函数零落盘，Issue 只产不写，
  路由权在裁决通道）；可执行反例测试纪律（每域≥1 反例，见 test）。
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

REASON_CODES = (
    "G1-SCHEMA", "G1-EVIDENCE", "G1-REF", "G1-REL-BACKLINK",
    "G1-TIME_INVERSION", "G1-DEAD-WALK", "G1-FORESHADOW-ORDER",
    "G1-CHEKHOV-OVERDUE", "G1-CONTRADICTION",
)

# 拦截 → 隔离区三子类（U-A17 采纳的 quarantine 三子类；v1 暂定映射就此收敛）
REASON_TO_QUARANTINE_SUBCLASS = {
    "G1-SCHEMA": "extrapolation_unverified",       # 外推待证：结构不合规不可证
    "G1-EVIDENCE": "extrapolation_unverified",     # 外推待证：无证据/证据悬空
    "G1-REF": "extrapolation_unverified",          # 外推待证：引用悬空
    "G1-REL-BACKLINK": "contradiction_pending",    # 矛盾待裁决：关系单向缺回链
    "G1-TIME_INVERSION": "contradiction_pending",  # 矛盾待裁决：时间倒置
    "G1-DEAD-WALK": "contradiction_pending",       # 矛盾待裁决：死人走路
    "G1-FORESHADOW-ORDER": "contradiction_pending",  # 矛盾待裁决：伏笔时序倒置
    "G1-CONTRADICTION": "contradiction_pending",   # 矛盾待裁决：同字段矛盾
    "G1-CHEKHOV-OVERDUE": "overdue_omission",      # 超期遗漏：契诃夫枪超期
}

# 修复动作模板（story-skills P0-P3+精确命令；{rid} 占位）
FIX_ACTIONS = {
    "G1-SCHEMA": ("P0", "修复记录 {rid} 契约违规后重过门1：py -X utf8 cbb/cbb-gate1/cbb_gate1.py --candidates <file>"),
    "G1-EVIDENCE": ("P0", "补齐或改正 {rid} 的证据四元组（原文引+坐标），无证据不入库（B4）"),
    "G1-CONTRADICTION": ("P0", "人工裁决 {rid} 冲突字段：supersede 旧记录并记 status_history"),
    "G1-DEAD-WALK": ("P0", "核查 {rid}：死亡实体后续事件——复活须经人裁 supersede 死亡记录"),
    "G1-REF": ("P1", "修复 {rid} 悬空引用：补目标记录或删除引用字段"),
    "G1-REL-BACKLINK": ("P1", "补 {rid} 的反向边（逆类型/对称回链）后重跑 links 域"),
    "G1-TIME_INVERSION": ("P1", "核查 {rid} 时间倒置：修正 story_time 或 causal_predecessors"),
    "G1-FORESHADOW-ORDER": ("P1", "修正 {rid} 伏笔时序：payoff_chapter 不得早于 setup_chapter"),
    "G1-CHEKHOV-OVERDUE": ("P2", "复核 {rid}：契诃夫枪超期未兑现——安排 payoff 或转 abandoned（人裁）"),
}

# ---- 关系逆类型 12 对 + 对称 12 项（story-skills src/story.js:60-88 设计转译，MIT） ----
RELATIONSHIP_INVERSES = {
    "parent": "child", "child": "parent",
    "grandparent": "grandchild", "grandchild": "grandparent",
    "uncle": "nephew", "aunt": "niece",
    "nephew": "uncle", "niece": "aunt",
    "mentor": "student", "student": "mentor",
    "employer": "subordinate", "subordinate": "employer",
}
SYMMETRIC_RELATIONSHIPS = {
    "sibling", "spouse", "partner", "friend", "ally", "rival", "enemy",
    "cousin", "colleague", "foil", "confidant", "love-interest",
}

CHEKHOV_OVERDUE_CHAPTERS = 3  # 契诃夫枪：≥3 章未兑现即超期（story-skills 算法）


def _vid(record_id: str, codes: list[str]) -> str:
    h = hashlib.sha256(f"{record_id}|{'|'.join(sorted(codes))}".encode("utf-8")).hexdigest()[:12]
    return f"g1-{h}"


# ================= 域一 validate：结构/schema =================

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


# ================= 域二 links：引用完整性+关系回链 =================

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


def _relation_edges(records: list[dict]) -> set:
    """收集关系边 (subject, rel_type, object)——relation 记录 canonical 三元组。"""
    edges = set()
    for r in records:
        if r.get("record_type") != "relation":
            continue
        c = r.get("canonical") or {}
        s, o, t = c.get("subject"), c.get("object"), c.get("rel_type")
        if s and o and t:
            edges.add((s, t, o))
    return edges


def _check_relation_backlinks(rec: dict, all_records: list[dict]) -> list[dict]:
    """关系双向回链：逆类型表（parent↔child 等 12 对）要求反向边存在；
    对称表（sibling/spouse 等 12 项）要求同型反向边存在。缺回链=拦截。"""
    if rec.get("record_type") != "relation":
        return []
    c = rec.get("canonical") or {}
    s, o, t = c.get("subject"), c.get("object"), c.get("rel_type")
    if not (s and o and t):
        return []
    edges = _relation_edges(all_records)
    if (s, t, o) not in edges:
        return []  # 自身不完整交给 schema/其他检查
    if t in SYMMETRIC_RELATIONSHIPS:
        if (o, t, s) not in edges:
            return [{"code": "G1-REL-BACKLINK",
                     "detail": f"对称关系 {t} 缺反向边: {o} -[{t}]-> {s}（symmetric 12 项）"}]
    elif t in RELATIONSHIP_INVERSES:
        inv = RELATIONSHIP_INVERSES[t]
        if (o, inv, s) not in edges:
            return [{"code": "G1-REL-BACKLINK",
                     "detail": f"关系 {t} 缺逆类型回链: {o} -[{inv}]-> {s}（逆类型 12 对）"}]
    return []


# ================= 域三 continuity：连续性 =================

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


def _resolve_day(rec, records_by_id: dict) -> dict | None:
    """取记录的 day 精度故事时间（canonical.story_time），否则 None。"""
    st = (rec or {}).get("canonical", {}).get("story_time")
    if isinstance(st, dict) and st.get("precision") == "day" and isinstance(st.get("day_offset"), int):
        return st
    return None


def _chapter_of(rec: dict):
    ev = (rec.get("evidence") or [{}])[0]
    return ev.get("chapter")


def _check_dead_walk(rec: dict, entities_by_name: dict) -> list[dict]:
    """死人走路：事件（entity_refs 引用死亡实体）且事件章 > 死亡章。
    实体死亡约定：entity 记录 canonical {name, status:"dead", death_chapter:N}。"""
    if rec.get("record_type") not in ("event", "relation"):
        return []
    canon = rec.get("canonical") or {}
    ch = _chapter_of(rec)
    for ref in canon.get("entity_refs") or []:
        ent = entities_by_name.get(ref)
        if not ent:
            continue
        ec = ent.get("canonical") or {}
        if ec.get("status") == "dead" and isinstance(ec.get("death_chapter"), int) \
                and isinstance(ch, int) and ch > ec["death_chapter"]:
            return [{"code": "G1-DEAD-WALK",
                     "detail": f"{ref} 于第{ec['death_chapter']}章死亡，但被第{ch}章事件引用（死人走路）"}]
    return []


def _check_foreshadow(rec: dict, current_chapter) -> list[dict]:
    """伏笔三查：时序倒置（payoff 早于 setup）/契诃夫枪超期（开环且≥3 章未兑现）。"""
    if rec.get("record_type") != "foreshadow":
        return []
    c = rec.get("canonical") or {}
    setup, payoff = c.get("setup_chapter"), c.get("payoff_chapter")
    if isinstance(setup, int) and isinstance(payoff, int) and payoff < setup:
        return [{"code": "G1-FORESHADOW-ORDER",
                 "detail": f"伏笔兑现早于埋设：setup=第{setup}章 payoff=第{payoff}章"}]
    if payoff is None and isinstance(setup, int) and isinstance(current_chapter, int) \
            and current_chapter - setup >= CHEKHOV_OVERDUE_CHAPTERS:
        return [{"code": "G1-CHEKHOV-OVERDUE",
                 "detail": f"契诃夫枪超期：第{setup}章埋设，至第{current_chapter}章 "
                           f"已 {current_chapter - setup} 章未兑现（≥{CHEKHOV_OVERDUE_CHAPTERS}）"}]
    return []


def _check_contradiction(rec: dict, seen_statuses: dict) -> list[dict]:
    """矛盾检测：同一实体名在同批出现互斥 status（alive/dead 等）且无 supersedes 链。"""
    if rec.get("record_type") != "entity":
        return []
    c = rec.get("canonical") or {}
    name, status = c.get("name"), c.get("status")
    if not name or not isinstance(status, str):
        return []
    if rec.get("supersedes"):
        return []  # 已走版本化通道的不算同批矛盾
    prev = seen_statuses.get(name)
    if prev is not None and prev != status:
        return [{"code": "G1-CONTRADICTION",
                 "detail": f"实体 {name} 同批双状态: {prev!r} vs {status!r}（应走 supersedes 版本化）"}]
    return []


# ================= 门1 主流程 =================

def check_record(rec: dict, ctx: dict) -> dict:
    """单记录门1（三域并跑）。ctx: {blocks, known_ids, records_by_id,
    all_records, entities_by_name, seen_statuses, current_chapter}"""
    violations = (
        _check_schema(rec) + _check_evidence(rec, ctx.get("blocks"))          # validate 域
        + _check_refs(rec, ctx.get("known_ids"))                              # links 域
        + _check_relation_backlinks(rec, ctx.get("all_records") or [])        # links 域
        + _check_time_inversion(rec, ctx.get("records_by_id") or {})          # continuity 域
        + _check_dead_walk(rec, ctx.get("entities_by_name") or {})            # continuity 域
        + _check_foreshadow(rec, ctx.get("current_chapter"))                  # continuity 域
        + _check_contradiction(rec, ctx.get("seen_statuses") or {})           # continuity 域
    )
    codes = [v["code"] for v in violations]
    return {
        "record_id": rec.get("record_id", "?"),
        "verdict": "intercept" if violations else "pass",
        "violations": violations,
        "quarantine_subclass": REASON_TO_QUARANTINE_SUBCLASS.get(codes[0]) if codes else None,
        "gate_trace_entry": {"gate": "1", "verdict_id": _vid(rec.get("record_id", "?"), codes)},
    }


def to_issue(check: dict, record: dict) -> dict:
    """违规检查结果 → 契约合规 Issue v2.0（EXPLAIN 拒写：只构造返回，绝不落盘——
    路由权在裁决通道/quarantine）。fix_action=P0-P3+精确命令；caliber=deterministic。"""
    code = check["violations"][0]["code"] if check["violations"] else None
    if code is None:
        raise ValueError("pass 的检查不产 Issue")
    rid = record.get("record_id", "?")
    priority, command = FIX_ACTIONS[code]
    issue = {
        "issue_id": f"{check['gate_trace_entry']['verdict_id']}-issue",
        "skill": "cbb-gate1",
        "error_type": code,
        "claim": check["violations"][0]["detail"],
        "evidence_span": dict(record.get("evidence", [{}])[0]) if record.get("evidence") else {},
        "graph_context": {"record_id": rid, "quarantine_subclass": check["quarantine_subclass"]},
        "severity": priority,
        "extraction_confidence": 100,
        "fix_action": {"priority": priority, "command": command.format(rid=rid)},
        "confidence_caliber": "deterministic",
        "cites": [rid],
    }
    cbb_contracts.validate_issue(issue)  # 构造期即合规
    return issue


def check_batch(candidates: list[dict], ctx: dict | None = None) -> dict:
    """批量过门。返回 {passed, intercepted(含 issues), summary}。幂等：纯函数零落盘，
    重跑同结果；不改写输入候选（EXPLAIN 拒写纪律的功能面）。"""
    ctx = dict(ctx or {})
    own_ids = {c.get("record_id") for c in candidates if c.get("record_id")}
    known = ctx.get("known_ids")
    if known is not None:
        ctx["known_ids"] = set(known) | own_ids  # 候选间互引合法（同批沉淀）
    records_by_id = dict(ctx.get("records_by_id") or {})
    for c in candidates:
        records_by_id.setdefault(c.get("record_id"), c)
    ctx["records_by_id"] = records_by_id
    ctx.setdefault("all_records", list(records_by_id.values()))
    entities_by_name = {r["canonical"]["name"]: r for r in candidates
                        if r.get("record_type") == "entity" and isinstance(r.get("canonical"), dict)
                        and r["canonical"].get("name")}
    ctx.setdefault("entities_by_name", entities_by_name)
    seen_statuses: dict[str, str] = {}

    passed, intercepted = [], []
    for rec in candidates:
        ctx2 = {**ctx, "seen_statuses": dict(seen_statuses)}
        chk = check_record(rec, ctx2)
        if chk["verdict"] == "pass":
            passed.append(chk)
            if rec.get("record_type") == "entity" and isinstance(rec.get("canonical"), dict):
                n, s = rec["canonical"].get("name"), rec["canonical"].get("status")
                if isinstance(n, str) and isinstance(s, str):
                    seen_statuses.setdefault(n, s)
        else:
            intercepted.append({"check": chk, "record": rec,
                                "issues": [to_issue(chk, rec)]})
    return {
        "passed": passed,
        "intercepted": intercepted,
        "summary": {"total": len(candidates), "pass": len(passed),
                    "intercept": len(intercepted),
                    "by_code": {c: sum(1 for it in intercepted
                                       if any(v["code"] == c for v in it["check"]["violations"]))
                                for c in REASON_CODES}},
    }


def make_generic_record(record_type: str, library: str, canonical: dict,
                        evidence: list[dict], status: str = "candidate",
                        confidence: float = 0.7) -> dict:
    """构造任意类型契约合规记录（fixture/冒烟用；生产抽取走 cbb-extract）。"""
    rec = {
        "record_id": f"rec-{record_type}-{hashlib.sha256(json.dumps(canonical, ensure_ascii=False, sort_keys=True).encode('utf-8')).hexdigest()[:12]}",
        "record_type": record_type,
        "library": library,
        "status": status,
        "canonical": canonical,
        "evidence": evidence,
        "verified_against": {"path": "fixture/source", "sha": "0" * 7, "verified_at": "1970-01-01"},
        "provenance": {"extractor_confidence": confidence, "extractor": "gate1-fixture",
                       "gate_trace": [], "precedent_refs": [], "status_history": []},
        "version": 1,
        "supersedes": None,
    }
    cbb_contracts.validate_record(rec, allow_candidate=(status == "candidate"))
    return rec


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="CBB 门1 确定性硬校验（本体版 v2 · 三域）")
    ap.add_argument("--candidates", required=True, help="cbb-extract 候选 JSON（{candidates:[…]}）")
    ap.add_argument("--manifest", default=None, help="坐标 manifest JSON（供证据回落校验）")
    ap.add_argument("--known-ids", default=None, help="已知记录 ID 清单 JSON 数组（可选）")
    ap.add_argument("--current-chapter", type=int, default=None,
                    help="当前推进章号（契诃夫枪超期判定的时钟位，缺省则跳过该检查）")
    args = ap.parse_args(argv)

    payload = json.loads(Path(args.candidates).read_text(encoding="utf-8"))
    cands = payload["candidates"] if isinstance(payload, dict) else payload
    ctx = {"blocks": None, "known_ids": None, "current_chapter": args.current_chapter}
    if args.manifest:
        ctx["blocks"] = json.loads(Path(args.manifest).read_text(encoding="utf-8"))["blocks"]
    if args.known_ids:
        ctx["known_ids"] = set(json.loads(Path(args.known_ids).read_text(encoding="utf-8")))
    result = check_batch(cands, ctx)
    print(f"[gate1] total={result['summary']['total']} "
          f"pass={result['summary']['pass']} intercept={result['summary']['intercept']} "
          f"by_code={ {k: v for k, v in result['summary']['by_code'].items() if v} } "
          f"(三域=validate/links/continuity；Issue=契约v2.0只产不写)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
