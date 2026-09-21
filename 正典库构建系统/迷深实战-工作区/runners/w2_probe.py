# -*- coding: utf-8 -*-
"""w2_probe.py — W2 召回探针（段收口抽 2 章机械审计；重写自 U-C03 段收口口径，结果文件同构）。

门：①dangling 悬空率 ≤10%（候选 evidence.quote 逐字在切片中存在）
   ②coverage_lib_hard 库内召回 ≥0.90（切片中出现的库内实体名，本章候选应覆盖）
   ③envelope 契约封套零违规（library 枚举/category 枚举/章号一致）
   ④density 密度区间报告（只报不门）
确定性零裁量（R-018）：无网络、无模型、纯机械比对。
用法：py -X utf8 runners/w2_probe.py --chapter 132 [--out logs/w2-probe-ch0132.json]
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORK = HERE.parent
ROOT = WORK.parent
STORE = ROOT / "迷深实战-本体库"
VALID_LIB = {"event", "character", "timeline", "relation", "setting", "foreshadow"}  # cbb_store.LIBRARIES 契约库集
VALID_CAT = {"summary", "event", "tone", "technique", "quote", "significance", "foreshadowing",
             "arc", "trait", "manifestation", "evolution", "appearance", "interpretation",
             "atmosphere", "example", "status_change", "relation", "alias", "knowledge"}  # record.schema.json 契约枚举


def _chain_base(rid: str) -> str:
    while rid.endswith("-m") or re.fullmatch(r".+-m\d+", rid):
        rid = re.sub(r"-m\d*$", "", rid)
    return rid


def lib_entity_groups() -> list:
    """实体级名组：每组=一个库内实体的{正名}∪{别名}（版本链基名关联；脏行防御跳过）。"""
    groups = {}
    for sub in ("provisional", "confirmed"):
        for f in (STORE / "libraries" / "character" / sub).glob("*.json"):
            m = re.fullmatch(r"(cand-entity-[0-9a-f]+)(?:-m\d*)*\.json", f.name)
            if not m:
                continue
            base = m.group(1)
            if base not in groups:
                try:
                    rec = json.loads(f.read_text(encoding="utf-8"))
                except OSError:
                    continue
                n = (rec.get("canonical") or {}).get("name")
                if isinstance(n, str):
                    groups[base] = {n}
    for ln in (STORE / "aliases.jsonl").read_text(encoding="utf-8").splitlines():
        try:
            a = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if isinstance(a.get("alias"), str):
            groups.setdefault(_chain_base(a.get("record_id", "")), set()).add(a["alias"])
    return [g for g in groups.values() if g]


def probe(chapter_no: int) -> dict:
    unit = f"ch{chapter_no:04d}"
    slice_txt = (WORK / "slice" / f"{unit}.txt").read_text(encoding="utf-8")
    raw = json.loads((WORK / "candidates" / f"extraction-{unit}.json").read_text(encoding="utf-8"))
    cands = raw["candidates"]

    # ① dangling：quote 逐字在切片中
    bad, total = [], 0
    for c in cands:
        for ev in c.get("evidence", []):
            total += 1
            if ev.get("quote") not in slice_txt:
                bad.append({"name": (c.get("canonical") or {}).get("name"), "line": ev.get("line"),
                            "quote": (ev.get("quote") or "")[:40]})
    dangling = {"bad": len(bad), "total": total,
                "rate": round(len(bad) / total, 4) if total else 0.0,
                "pass": (len(bad) / total if total else 0.0) <= 0.10,
                "samples": bad[:5]}

    # ② coverage_lib_hard：切片中出现的库内实体（实体级名组=正名∪别名，任一名命中即覆盖）
    cand_text = json.dumps(cands, ensure_ascii=False)  # 候选全部关联面：canonical/别名/涉事者/引文/观察/fact
    in_slice = [g for g in lib_entity_groups() if any(n in slice_txt for n in g)]
    hit = [g for g in in_slice if any(n in cand_text for n in g)]
    missing = [sorted(g)[0] for g in in_slice if g not in hit]
    coverage = {"hit": len(hit), "in_slice": len(in_slice),
                "recall": round(len(hit) / len(in_slice), 4) if in_slice else 1.0,
                "pass": (len(hit) / len(in_slice) if in_slice else 1.0) >= 0.90,
                "missing": missing[:8]}

    # ③ envelope：契约枚举/章号
    viol = []
    for c in cands:
        if c.get("library") not in VALID_LIB:
            viol.append({"kind": "library", "v": c.get("library")})
        for o in c.get("observations", []):
            if o.get("category") not in VALID_CAT:
                viol.append({"kind": "category", "v": o.get("category")})
        for ev in c.get("evidence", []):
            if ev.get("chapter") != chapter_no:
                viol.append({"kind": "chapter", "v": ev.get("chapter")})
    envelope = {"violations": viol[:10], "pass": not viol}

    # ④ density
    by_type = {}
    for c in cands:
        by_type[c["type"]] = by_type.get(c["type"], 0) + 1
    density = {"total": len(cands), "by_type": by_type}

    return {"extraction": f"candidates/extraction-{unit}.json",
            "gate": "PASS" if (dangling["pass"] and coverage["pass"] and envelope["pass"]) else "FAIL",
            "dangling": dangling, "coverage_lib_hard": coverage,
            "envelope": envelope, "density": density}


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--chapter", type=int, required=True)
    ap.add_argument("--out")
    a = ap.parse_args()
    r = probe(a.chapter)
    out = Path(a.out) if a.out else WORK / "logs" / f"w2-probe-ch{a.chapter:04d}.json"
    out.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"chapter": a.chapter, "gate": r["gate"],
                      "dangling_rate": r["dangling"]["rate"], "recall": r["coverage_lib_hard"]["recall"],
                      "missing": r["coverage_lib_hard"]["missing"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
