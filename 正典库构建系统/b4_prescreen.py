# -*- coding: utf-8 -*-
"""b4_prescreen.py — B4 NLI 预筛：Erlangshen-110M 对回填件分流（只分流不裁决）。

premise=合并引文（原+回填），hypothesis=canonical。
路由（G5 门完整保留——预筛只省 API，不代替考官）：
  CONTRADICTION（证据与自己矛盾=疑似误抽取）→ route=human_nli（直送人工，不烧 API）
  ENTAILMENT/NEUTRAL                        → route=panel（走 G16c 双考官全门）
产出：补充证据-NLI预筛.jsonl {record_id, label, score, route}
"""
import json
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "cbb-v2"))
os_ok = True
try:
    os_env = None
except Exception:  # pragma: no cover
    pass

STORE = ROOT / "迷深实战-本体库"
SIDECAR = STORE / "补充证据-回填.jsonl"
OUT = STORE / "补充证据-NLI预筛.jsonl"
MAX_CHARS = 1500


def main():
    import os
    os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
    from transformers import pipeline

    rows = [json.loads(l) for l in SIDECAR.read_text(encoding="utf-8").splitlines() if l.strip()]
    done = {}
    if OUT.exists():
        for l in OUT.read_text(encoding="utf-8").splitlines():
            if l.strip():
                r = json.loads(l)
                done[r["record_id"]] = r
    todo = [r for r in rows if r["record_id"] not in done and r["status"] in ("full", "partial")]
    print(f"待预筛 {len(todo)}/{len(rows)}（已筛 {len(done)}）", flush=True)
    if not todo:
        return

    nli = pipeline("text-classification",
                   model="IDEA-CCNL/Erlangshen-RoBERTa-110M-NLI", truncation=True)
    t0 = time.time()
    with OUT.open("a", encoding="utf-8") as f:
        for n, row in enumerate(todo, 1):
            rec_path = next(STORE.glob(f"libraries/{row['library']}/*/{row['record_id']}.json"), None)
            if rec_path is None:
                continue
            rec = json.loads(rec_path.read_text(encoding="utf-8"))
            quotes = "；".join(e.get("quote", "") for e in (rec.get("evidence") or []))
            quotes += "；" + "；".join(s.get("quote", "") for s in row["supplements"])
            hypo = json.dumps(rec.get("canonical") or {}, ensure_ascii=False, sort_keys=True)
            out = nli({"text": quotes[:MAX_CHARS], "text_pair": hypo[:MAX_CHARS]},
                      truncation="longest_first", max_length=510)
            if isinstance(out, list):
                out = out[0]
            label = out["label"]
            route = "human_nli" if label == "CONTRADICTION" else "panel"
            f.write(json.dumps({"record_id": row["record_id"], "label": label,
                                "score": round(out["score"], 4), "route": route},
                               ensure_ascii=False, sort_keys=True) + "\n")
            f.flush()
            if n % 200 == 0 or n == len(todo):
                el = time.time() - t0
                print(f"  {n}/{len(todo)}  {el:.0f}s（ETA {el/n*(len(todo)-n)/60:.0f}min）", flush=True)

    dist = Counter()
    for l in OUT.read_text(encoding="utf-8").splitlines():
        if l.strip():
            dist[json.loads(l)["route"]] += 1
    print("路由分布:", dict(dist), f"耗时 {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
