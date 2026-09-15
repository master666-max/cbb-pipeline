# -*- coding: utf-8 -*-
"""U-C00 端到管线：抽取源 JSON → Record v2.0 规范化 → gate1 三域 → 置信路由/隔离 → store 双轨 → 锚点树。
用法: py -X utf8 run_uc00_pipeline.py
产物: cands-ch14-excerpt1.json / gate1-ch14-excerpt1.json / logs/uc00-pipeline-summary.json / 本体库+锚点树
"""
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent            # 迷深实战-工作区/runners
WORK = HERE.parent                                 # 迷深实战-工作区
CBB = WORK.parent / "cbb"                          # 正典库构建系统/cbb（只读复用）
STORE_ROOT = WORK.parent / "迷深实战-本体库"
sys.path.insert(0, str(CBB / "contracts"))
sys.path.insert(0, str(CBB / "cbb-coordinate"))
sys.path.insert(0, str(CBB / "cbb-gate1"))
sys.path.insert(0, str(CBB / "cbb-store"))
sys.path.insert(0, str(CBB / "cbb-anchor"))
sys.path.insert(0, str(CBB / "cbb-extract"))
import cbb_contracts   # noqa: E402
import cbb_gate1       # noqa: E402
import cbb_store       # noqa: E402
import cbb_anchor      # noqa: E402

UNIT = "ch14-excerpt1"
EXTRACTION = WORK / "candidates" / f"extraction-{UNIT}.json"
CANDS_OUT = WORK / "candidates" / f"cands-{UNIT}.json"
GATE1_OUT = WORK / "gate1" / f"gate1-{UNIT}.json"
SUMMARY_OUT = WORK / "logs" / f"uc00-pipeline-summary.json"
MANIFEST = WORK / "manifest" / f"manifest-{UNIT}.json"
TREE_DIR = WORK / "anchors"
CHAPTER = 14
INGEST_INDEX = 10  # clean_full 第 11 个 <<<CHAPTER>>> 标记（0 起算摄入序）→ tick=10 → 伪锚点 2000-01-11
TAU = cbb_store.TAU_PROVISIONAL  # 0.85


def core_id(rec_type: str, canonical: dict, evidence: list[dict]) -> str:
    payload = {"c": {k: v for k, v in canonical.items() if k != "entity_refs"}, "e": evidence}
    h = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:12]
    return f"cand-{rec_type}-{h}"


def normalize(raw: dict, verified_against: dict) -> list[dict]:
    out = []
    for c in raw["candidates"]:
        canonical = dict(c["canonical"])
        rec = {
            "record_id": core_id(c["type"], canonical, c["evidence"]),
            "record_type": c["type"],
            "library": c["library"],
            "status": "candidate",
            "canonical": canonical,
            "observations": c.get("observations", []),
            "evidence": c["evidence"],
            "verified_against": verified_against,
            "provenance": {
                "extractor_confidence": c["confidence"],
                "extractor": "glm-zcode-agent-v1（工单v1.2§0亲抽路线）",
                "gate_trace": [],
                "precedent_refs": [],
                "status_history": [],
            },
            "version": 1,
            "supersedes": None,
        }
        # v2 设计（trial-v0 教训）：entity_refs(id) 不进 canonical（派生 id 随上游修正漂移→假矛盾）。
        # 关系以 subject/object 名称引用；事件/伏笔以 canonical.entities（名称数组）标注涉事者；
        # id 级 REF/死人走路检查休眠，孤悬引用改由 U-C09 R2 按名称全扫（责任转移登记 STATE）。
        if c["type"] in ("event", "foreshadow") and c.get("entities_involved"):
            rec["canonical"]["entities"] = sorted(set(c["entities_involved"]))
        cbb_contracts.validate_record(rec, allow_candidate=True)
        out.append(rec)
    return out


def main() -> int:
    raw = json.loads(EXTRACTION.read_text(encoding="utf-8"))
    va = raw["_meta"]["source"]
    verified = {"path": va["path"], "sha": va["sha"], "verified_at": va["verified_at"]}
    cands = normalize(raw, verified)

    # 幂等守卫说明：本脚本首跑建库；重跑时 store 双轨按身份键吸收（consistent-duplicate 幂等，
    # P-017 证据包含即不增殖）——断点续跑安全。
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    result = cbb_gate1.check_batch(cands, ctx={"blocks": manifest["blocks"], "current_chapter": CHAPTER})
    GATE1_OUT.write_text(json.dumps(
        {"unit": UNIT, "summary": result["summary"],
         "intercepted": [{"record_id": it["check"]["record_id"],
                          "violations": it["check"]["violations"],
                          "subclass": it["check"]["quarantine_subclass"]} for it in result["intercepted"]]},
        ensure_ascii=False, sort_keys=True, indent=1), encoding="utf-8")

    store = cbb_store.ThreeStateStore(STORE_ROOT)
    SUBCLASS_GROUP = {"contradiction_pending": "entity_unalignable",
                      "extrapolation_unverified": "low_confidence",
                      "overdue_omission": "low_confidence"}
    admits, quarantined = [], []
    for chk in result["passed"]:
        rec = next(r for r in cands if r["record_id"] == chk["record_id"])
        conf = rec["provenance"]["extractor_confidence"]
        if conf >= TAU:
            r = store.admit_or_merge(rec)
            admits.append({"record_id": rec["record_id"], "type": rec["record_type"],
                           "name": rec["canonical"].get("name") or rec["canonical"].get("subject"),
                           "track": r["track"], "detail": {k: v for k, v in r.items() if k in ("new_id", "quarantine_item", "repeated")}})
        else:
            iid, created = store.admit(rec, "quarantine", quarantine_group="low_confidence",
                                       quarantine_detail=f"置信度路由：{conf}<{TAU}（含反推成分，保守隔离待人工/后证）")
            quarantined.append({"record_id": rec["record_id"], "type": rec["record_type"],
                                "name": rec["canonical"].get("name") or rec["canonical"].get("subject"),
                                "item_id": iid, "reason": "confidence_route"})
    for it in result["intercepted"]:
        rec = next(r for r in cands if r["record_id"] == it["check"]["record_id"])
        sub = it["check"]["quarantine_subclass"] or "extrapolation_unverified"
        codes = ";".join(v["code"] for v in it["check"]["violations"])
        iid, _ = store.admit(rec, "quarantine",
                             quarantine_group=SUBCLASS_GROUP.get(sub, "low_confidence"),
                             quarantine_detail=f"门1拦截[{codes}] {it['check']['violations'][0]['detail'][:80]}")
        quarantined.append({"record_id": rec["record_id"], "type": rec["record_type"],
                            "name": rec["canonical"].get("name") or rec["canonical"].get("subject"),
                            "item_id": iid, "reason": f"gate1:{codes}"})

    # 别名复合 PK 登记（UNIQUE 约束族；别名不进 canonical，防跨章双轨误判）
    by_id = {r["record_id"]: r for r in cands}
    alias_regs = []
    for c in raw["candidates"]:
        for alias in c.get("aliases_to_register", []):
            ent = next(r for r in cands if r["record_type"] == "entity"
                       and r["canonical"]["name"] == c["canonical"]["name"])
            key, created = store.register_alias(alias, ent["record_id"], c["canonical"]["entity_type"])
            alias_regs.append({"alias": alias, "entity": c["canonical"]["name"], "created": created})

    # 出场唯一（entity,chapter）
    for c in raw["candidates"]:
        if c["type"] == "entity":
            ent = next(r for r in cands if r["record_type"] == "entity"
                       and r["canonical"]["name"] == c["canonical"]["name"])
            store.record_appearance(c["canonical"]["name"], CHAPTER)

    # 锚点：单章试车树（摄入序 10）+ anchor 记录入库（timeline 库）
    anchor_rec = cbb_anchor.make_anchor_record(CHAPTER, INGEST_INDEX, vol=1, verified_against=verified)
    chk_a = cbb_gate1.check_record(anchor_rec, ctx={"blocks": None, "current_chapter": CHAPTER})
    # anchor 证据=章序标记模板（make_anchor_record 设计），非正文块引文 → blocks=None 回落豁免，留痕
    tree = {"kind": "cbb-anchor-tree", "version": 1, "vol": 1,
            "axes": ["tick", "instant", "time"], "anchors": [anchor_rec],
            "note": "U-C00 单章试车树（仅 ch14，摄入序=10）；全量树 v1 在 U-C01 落盘；伪锚点保序不冒充真实日期"}
    TREE_DIR.mkdir(parents=True, exist_ok=True)
    cbb_anchor.save_tree(tree, TREE_DIR)
    anchor_admit = store.admit_or_merge(anchor_rec) if chk_a["verdict"] == "pass" else \
        store.admit(anchor_rec, "quarantine", quarantine_group="low_confidence",
                    quarantine_detail=f"anchor 门1异常:{chk_a['violations'][:1]}")

    CANDS_OUT.write_text(json.dumps({"candidates": cands, "meta": raw["_meta"]},
                                    ensure_ascii=False, sort_keys=True, indent=1), encoding="utf-8")
    summary = {
        "unit": UNIT, "generated_by": "run_uc00_pipeline.py",
        "counts": {"authored": len(cands),
                   "gate1_pass": result["summary"]["pass"], "gate1_intercept": result["summary"]["intercept"],
                   "admitted": len(admits), "quarantined": len(quarantined)},
        "gate1_by_code": result["summary"]["by_code"],
        "tracks": {t: sum(1 for a in admits if a["track"] == t) for t in {a["track"] for a in admits}},
        "admitted": admits, "quarantined": quarantined,
        "aliases_registered": alias_regs,
        "anchor": {"tick": INGEST_INDEX, "pseudo_date": anchor_rec["canonical"]["pseudo_date"],
                   "gate1": chk_a["verdict"], "admit_track": anchor_admit.get("track", str(anchor_admit))},
        "store_stats": store.stats() if hasattr(store, "stats") else None,
    }
    SUMMARY_OUT.write_text(json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=1), encoding="utf-8")
    print(json.dumps({"counts": summary["counts"], "tracks": summary["tracks"],
                      "gate1_by_code": {k: v for k, v in result["summary"]["by_code"].items() if v},
                      "anchor": summary["anchor"]}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
