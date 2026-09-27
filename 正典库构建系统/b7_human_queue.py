# -*- coding: utf-8 -*-
"""b7_human_queue.py — B7 人工队列成军（总工单二批·波 B 收口件）。

汇聚全部终审线状态成单一人工队列，audit.suspicious_rank 最可疑优先：
  ①G16b hold 且未进 B5 面板（锚定 OK 但考官 unsure/诠释型）
  ②B5 NLI 直送（证据自相矛盾，human_nli 路由）
  ③G16c/B5b 重审后仍 hold/human
  ④B6 升级段仍 hold
  ⑤核心指代补充证据后仍未消解（unbackfillable 终态）
每件附全套引文（原+回填+核心指代）+前情提要（carry_summary 盲点先验已注明）。
产出：迷深实战-本体库/人工队列.jsonl（suspicion 升序=最可疑最后写入顶部可翻）
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "cbb-v2"))

from cbb2 import audit  # noqa: E402

STORE = ROOT / "迷深实战-本体库"
OUT = STORE / "人工队列.jsonl"


def load_last(path: Path) -> dict:
    last = {}
    if path.exists():
        for l in path.read_text(encoding="utf-8").splitlines():
            if l.strip():
                r = json.loads(l)
                last[r["record_id"]] = r
    return last


def main():
    g16b = load_last(STORE / "G16b-票面台账.jsonl")
    g16c = load_last(STORE / "G16c-重审台账.jsonl")
    esc = load_last(STORE / "G16c-升级台账.jsonl")
    pre = load_last(STORE / "补充证据-NLI预筛.jsonl")
    bf = load_last(STORE / "补充证据-回填.jsonl")
    coref_dir = ROOT / "迷深实战-工作区" / "coref_batches" / "results"
    coref = {}
    if coref_dir.exists():
        for f in coref_dir.glob("batch-*.json"):
            for r in json.loads(f.read_text(encoding="utf-8")).get("results", []):
                coref[r["record_id"]] = r

    confirmed = {rid for rid, v in {**g16b, **g16c, **esc}.items()
                 if v.get("verdict") == "promote"}
    queue = []
    for rid, verdict in g16b.items():
        if rid in confirmed or verdict != "hold" and verdict != "human":
            continue
        if verdict == "promote":
            continue
        lib = None
        rec = None
        for f in STORE.glob(f"libraries/*/*/{rid}.json"):
            rec = json.loads(f.read_text(encoding="utf-8"))
            lib = f.parent.parent.stem
            break
        if rec is None:
            continue
        supplements = (bf.get(rid) or {}).get("supplements", [])
        coref_pairs = (coref.get(rid) or {}).get("pairs", [])
        row = {
            "record_id": rid, "library": lib,
            "g16b": verdict,
            "g16c": (g16c.get(rid) or {}).get("verdict"),
            "escalated": (esc.get(rid) or {}).get("verdict"),
            "nli_route": (pre.get(rid) or {}).get("route"),
            "nli_label": (pre.get(rid) or {}).get("label"),
            "canonical": rec.get("canonical") or {},
            "evidence": rec.get("evidence") or [],
            "supplements": supplements,
            "coref_pairs": coref_pairs,
            "record": rec,
        }
        queue.append(row)

    ranked = audit.suspicious_rank(queue)  # 证据少/置信低排前=最可疑优先
    with OUT.open("w", encoding="utf-8") as f:
        for row in ranked:
            row["record"].pop("evidence", None)  # 队列行自带 evidence，避免双份
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    from collections import Counter
    c = Counter((r.get("nli_route") or "panel_line", r.get("g16b")) for r in ranked)
    print(f"人工队列: {len(ranked)} 件 → {OUT}")
    for k, v in c.most_common(8):
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
