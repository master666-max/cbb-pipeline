# -*- coding: utf-8 -*-
"""g_backfill.py — 证据回填件（三件落地工单 U1）。

缺锚记录回章补引文：evidence.line=章内相对行（±1 偏差，ch112 实测）→
边界表换算绝对行 → ±10 行窗口容错匹配缺失实体变体 → 命中句摘为补充引文。
窗口零命中 → 全章兜底一次 → 仍零命中 = unbackfillable（真缺证据，直送人工）。

模式：
  --dry-run                  全量缺锚统计，零写入
  --pilot N [--libs a,b,c]   试点回填 N 件（分层抽样），写试点 sidecar+MD 报告
  --all                      全量回填（写正式 sidecar；试点件按幂等键去重）

写面纪律：只写 sidecar（append-only），库件一行不动。
"""
import json
import re
import sys
import hashlib
import random
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STORE = ROOT / "迷深实战-本体库"
CORPUS = ROOT.parent / "语料分析" / "corpus" / "clean_full.txt"
BOUNDARY = ROOT / "迷深实战-工作区" / "manifest" / "boundary-table-v1.json"
SIDECAR_PILOT = STORE / "补充证据-回填-试点.jsonl"
REPORT = STORE / "U1-回填试点报告"

WORST = ("relation", "event", "foreshadow")
DEFAULT_LIBS = ("relation", "event", "foreshadow", "setting", "character")
PER_LIB = {"relation": 10, "event": 10, "foreshadow": 10, "setting": 6, "character": 4}


def norm(s):
    return re.sub(r"[『』「」\[\]（）()………\.\.\—─\-、，。？！?!：:；;\s\"\"''~～·　]", "", str(s))


def variants(k):
    vs = {k}
    if len(k) >= 4:
        vs.add(k[:-2])
    if len(k) >= 3:
        vs.add(k[-2:])
    if len(k) >= 4:
        vs.add(k[-3:])
    return {v for v in vs if len(v) >= 2}


def anchor_keys(lib, c):
    """库分形锚定谓词（研讨报告同款；U3 时迁入单一来源）。
    返回 (表面名 keys, 实体 keys)——labels 豁免名锚，只锚实体。"""
    if lib == "relation":
        return [], [norm(c.get(k, "")) for k in ("subject", "object")]
    if lib in ("event", "foreshadow"):
        return [], [norm(e) for e in (c.get("entities") or [])]
    return [], [norm(c.get("name", ""))]


def missing_keys(lib, c, quotes_normed):
    keys = [k for k in anchor_keys(lib, c)[1] if k]
    return [k for k in keys if not any(v in quotes_normed for v in variants(k))]


def split_sentences(text):
    parts = re.split(r"(?<=[。！？!?])", text)
    return [p for p in parts if p.strip()]


def main():
    dry = "--dry-run" in sys.argv
    pilot_n = None
    if "--pilot" in sys.argv:
        pilot_n = int(sys.argv[sys.argv.index("--pilot") + 1])

    boundary = json.loads(BOUNDARY.read_text(encoding="utf-8"))
    chap_of = {c["chapter_no"]: c for c in boundary["chapters"]}
    lines = CORPUS.read_text(encoding="utf-8").splitlines()
    print(f"语料 {len(lines)} 行载入")

    # ── 收集缺锚件 ──
    misses = []
    seen_lib = Counter()
    for f in sorted(STORE.glob("libraries/*/*/*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        lib = f.parent.parent.stem
        c = d.get("canonical") or {}
        evs = d.get("evidence") or []
        quotes = norm("；".join(e.get("quote", "") for e in evs))
        mk = missing_keys(lib, c, quotes)
        if not mk or not evs:
            continue
        rec = {"record_id": d.get("record_id"), "library": lib, "path": str(f),
               "missing": mk, "canonical": c, "evidence": evs}
        if dry:
            seen_lib[lib] += 1
            misses.append(rec)
            continue
        per = PER_LIB.get(lib, 0)
        if pilot_n is not None and seen_lib[lib] >= per:
            continue
        seen_lib[lib] += 1
        misses.append(rec)

    if dry:
        print(f"全量缺锚 {len(misses)} 件:", dict(seen_lib))
        return

    if pilot_n is not None:
        # 分层抽样（固定种子可复算）
        rng = random.Random(20260928)
        sampled = []
        for lib in DEFAULT_LIBS:
            pool = [m for m in misses if m["library"] == lib]
            rng.shuffle(pool)
            sampled += pool[:PER_LIB[lib]]
        misses = sampled
        print(f"试点 {len(misses)} 件（{dict(Counter(m['library'] for m in misses))}）")

    # ── 回填 ──
    out_rows, stats = [], Counter()
    for rec in misses:
        cands = []  # (距离, 绝对行, 句, key)
        for ev in rec["evidence"]:
            ch = chap_of.get(ev.get("chapter"))
            if not ch or not ev.get("line"):
                continue
            base = ch["line_start"] - 1 + ev["line"]
            for key in rec["missing"]:
                hit = None
                # 窗口 ±10
                for dist in range(0, 11):
                    for ln in ({base - dist, base + dist} if dist else {base}):
                        if not (ch["line_start"] <= ln <= min(ch["line_end"], len(lines))):
                            continue
                        if any(v in norm(lines[ln - 1]) for v in variants(key)):
                            hit = (dist, ln)
                            break
                    if hit:
                        break
                # 全章兜底
                strat = "window"
                if not hit:
                    for ln in range(ch["line_start"], min(ch["line_end"], len(lines)) + 1):
                        if any(v in norm(lines[ln - 1]) for v in variants(key)):
                            hit = (None, ln)
                            strat = "chapter_fallback"
                            break
                if hit:
                    dist, ln = hit
                    text = lines[ln - 1]
                    sent = next((s for s in split_sentences(text)
                                 if any(v in norm(s) for v in variants(key))), text)
                    cands.append({"key": key, "strategy": strat, "distance": dist,
                                  "chapter": ev["chapter"], "line_rel": ln - ch["line_start"] + 1,
                                  "quote": sent.strip()})
        # 每 key 取最优（window 优先、距离近优先）
        best = {}
        for cd in sorted(cands, key=lambda x: (x["strategy"] != "window", x["distance"] or 99)):
            best.setdefault(cd["key"], cd)
        supplements = [{"vol": 1, "chapter": v["chapter"], "line": v["line_rel"],
                        "quote": v["quote"], "backfill": True,
                        "for_key": v["key"], "strategy": v["strategy"],
                        "distance": v["distance"]}
                       for v in best.values()]
        covered = {s["for_key"] for s in supplements}
        status = "full" if covered >= set(rec["missing"]) else \
            ("partial" if covered else "unbackfillable")
        stats[(rec["library"], status)] += 1
        out_rows.append({
            "record_id": rec["record_id"], "library": rec["library"],
            "missing_keys": rec["missing"], "status": status,
            "supplements": supplements, "at": "2026-09-28",
            "idem": hashlib.sha256(json.dumps(
                {"rid": rec["record_id"], "q": [s["quote"] for s in supplements]},
                ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16],
        })

    sidecar = SIDECAR_PILOT if pilot_n is not None else STORE / "补充证据-回填.jsonl"
    have = set()
    if sidecar.exists():
        for l in sidecar.read_text(encoding="utf-8").splitlines():
            if l.strip():
                have.add(json.loads(l)["idem"])
    with sidecar.open("a", encoding="utf-8") as f:
        for r in out_rows:
            if r["idem"] not in have:
                f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")

    print(f"回填状态: {dict(Counter((k[0], k[1]) for k in stats.elements()))}")
    print(f"→ {sidecar}（+{len(out_rows)} 行）")

    # ── 人读报告（人工抽看闸的耗材）──
    report_dir = REPORT
    report_dir.mkdir(exist_ok=True)
    md = ["# U1 回填试点抽看单（2026-09-28）", ""]
    for r in out_rows:
        md.append(f"## {r['record_id']}（{r['library']}，{r['status']}）")
        md.append(f"- 断言: {json.dumps(r.get('canonical') or {}, ensure_ascii=False)[:160]}")
        md.append(f"- 缺失 key: {r['missing_keys']}")
        for s in r["supplements"]:
            md.append(f"- 回填[{s['strategy']} d={s['distance']}] {s['quote'][:120]}")
        if not r["supplements"]:
            md.append("- （零命中——真缺证据候选）")
        md.append("")
    (report_dir / ("试点抽看单.md" if pilot_n is not None else "全量回填清单.md")).write_text(
        "\n".join(md), encoding="utf-8")
    print(f"抽看单 → {report_dir}")


if __name__ == "__main__":
    main()
