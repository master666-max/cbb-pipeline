# -*- coding: utf-8 -*-
"""ab_gate_eval.py — A/B 双盲门机械评估（悬空率/数量偏差/分类学矛盾模拟/覆盖率辅助）。
覆盖率的语义匹配需主线人工终判，本脚本产出匹配建议表。
用法: py -X utf8 ab_gate_eval.py
"""
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORK = HERE.parent
ROOT = WORK.parent
sys.path.insert(0, str(ROOT / "cbb" / "contracts"))
sys.path.insert(0, str(ROOT / "cbb" / "cbb-coordinate"))
sys.path.insert(0, str(ROOT / "cbb" / "cbb-store"))
import cbb_coordinate as cc  # noqa: E402
import cbb_store             # noqa: E402

STORE = cbb_store.ThreeStateStore(ROOT / "迷深实战-本体库")


def load_candidates(path):
    ext = json.loads(Path(path).read_text(encoding="utf-8"))
    cands = ext["candidates"]
    for c in cands:
        c.setdefault("type", c.get("record_type"))
    return cands


def slice_full(ch):
    blocks = cc.coordinate((WORK / "slice" / f"ch{ch:04d}.txt").read_text(encoding="utf-8"), vol=1)["blocks"]
    return "\n".join(b["text"] for b in blocks)


def dangling(cands, full):
    bad = []
    for c in cands:
        for ev in c.get("evidence", []):
            if ev["quote"] not in full:
                bad.append((c.get("canonical", {}).get("name") or c.get("canonical", {}).get("subject"), ev["line"], ev["quote"][:24]))
    return bad


def counts(cands):
    out = {}
    for c in cands:
        out[c["type"]] = out.get(c["type"], 0) + 1
    return out


def taxonomy_conflict_sim(cands):
    """只读模拟 store 双轨：身份键命中且 canonical 冲突 = 分类学/字段矛盾（首过矛盾计数）。"""
    n_id, n_conf = 0, []
    for c in cands:
        rec = {"record_type": c["type"], "library": c["library"], "canonical": c["canonical"],
               "provenance": {"extractor_confidence": c.get("confidence", 0.9)}}
        try:
            existing = STORE.find_by_identity(rec)
        except Exception:
            existing = None
        if existing is None:
            continue
        n_id += 1
        conf = cbb_store.canonical_conflicts(rec, existing)
        if conf and c["type"] in ("entity", "relation"):
            n_conf.append((c["type"], c["canonical"].get("name") or c["canonical"].get("rel_type"),
                           [(x["field"], str(x["incoming"])[:20], str(x["stored"])[:20]) for x in conf]))
    return n_id, n_conf


def keyfact_match(main_cands, sub_cands):
    """主线 events/foreshadows → 子臂命中建议（实体交集+文本重叠打分）。"""
    def ents(c):
        s = set(c.get("entities_involved") or [])
        cn = c.get("canonical", {})
        for k in ("name", "subject", "object"):
            if cn.get(k):
                s.add(cn[k])
        return s

    def text(c):
        obs = " ".join(o.get("text", "") for o in c.get("observations", []))
        return c["canonical"].get("name", "") + " " + obs

    rows = []
    for m in main_cands:
        if m["type"] not in ("event", "foreshadow"):
            continue
        me, mt = ents(m), set(text(m))
        best = None
        for s in sub_cands:
            if s["type"] not in ("event", "foreshadow", "setting", "relation"):
                continue
            se = ents(s)
            inter = me & se
            ov = len(inter) / max(1, len(me))
            t2 = set(text(s))
            jac = len(mt & t2) / max(1, len(mt | t2))
            score = ov * 0.7 + jac * 0.3
            if best is None or score > best[0]:
                best = (score, s["type"], s["canonical"].get("name", ""), sorted(inter)[:4])
        rows.append({"main": m["canonical"].get("name"), "type": m["type"],
                     "best_score": round(best[0], 3) if best else 0,
                     "sub_type": best[1] if best else "-", "sub_name": best[2] if best else "-",
                     "shared_ents": best[3] if best else []})
    return rows


def main():
    report = {"chapters": {}}
    for ch, main_path, sub_path in (
            (51, WORK / "ab-gate" / "extraction-mainline-ch0051.json", WORK / "candidates" / "cands-ch0051.json"),
            (52, WORK / "ab-gate" / "extraction-mainline-ch0052.json", WORK / "candidates" / "cands-ch0052.json")):
        A = load_candidates(main_path)
        B = load_candidates(sub_path)
        full = slice_full(ch)
        dA, dB = dangling(A, full), dangling(B, full)
        nA, nB = len(A), len(B)
        id_hits, conflicts = taxonomy_conflict_sim(B)
        rows = keyfact_match(A, B)
        # 建议命中线：score>=0.5 视为机械命中候选（人工复核表）
        hits = [r for r in rows if r["best_score"] >= 0.5]
        report["chapters"][f"ch{ch}"] = {
            "counts_main": counts(A), "counts_sub": counts(B),
            "n_main": nA, "n_sub": nB,
            "count_dev": round((nB - nA) / nA, 3),
            "dangling_main": len(dA), "dangling_sub": len(dB),
            "dangle_rate_sub": round(len(dB) / max(1, nB), 4),
            "identity_hits_vs_store": id_hits,
            "first_pass_conflicts": len(conflicts), "conflict_list": conflicts,
            "keyfacts_main": len(rows),
            "keyfact_mech_hits": len(hits),
            "keyfact_mech_coverage": round(len(hits) / max(1, len(rows)), 4),
            "coverage_rows": rows,
        }
    out = WORK / "ab-gate" / "ab-eval-mech.json"
    slim = json.loads(json.dumps(report, ensure_ascii=False))
    out.write_text(json.dumps(slim, ensure_ascii=False, indent=1), encoding="utf-8")
    for k, v in report["chapters"].items():
        print(k, "| 主线", v["n_main"], "子臂", v["n_sub"], "偏差", v["count_dev"],
              "| 悬空 子", v["dangling_sub"], "率", v["dangle_rate_sub"],
              "| 库身份命中", v["identity_hits_vs_store"], "首过矛盾", v["first_pass_conflicts"],
              "| 关键事实", v["keyfacts_main"], "机械命中", v["keyfact_mech_hits"], "覆盖率", v["keyfact_mech_coverage"])
    print("artifact:", out)


if __name__ == "__main__":
    main()
