# -*- coding: utf-8 -*-
"""wf_pilot_dump.py — 判卷件组装（工作流版；试点/全量两用）。

复用 g16c_rejudge 同源函数：同一 NLI 预筛路由、同一晋升排除（按台账最后一轮）、
同一 build_payload 白名单、同一 build_plants 植株（seed 同源）。
默认全量放量；--limit N 可切试点。
旧轮产物移入 试点轮存档/（不删除——append-only 纪律）。
产出：payload/NNN.json（judge-facing，无 expected）+ manifest.jsonl（特权清单）。
"""
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "cbb-v2"))
import g16c_rejudge as G  # noqa: E402

N = None
if "--limit" in sys.argv:
    N = int(sys.argv[sys.argv.index("--limit") + 1])

rows = [json.loads(l) for l in (G.STORE / "补充证据-回填.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
full = [r for r in rows if r["status"] in ("full", "partial")]

prescreen = {}
ps = G.STORE / "补充证据-NLI预筛.jsonl"
if ps.exists():
    for l in ps.read_text(encoding="utf-8").splitlines():
        if l.strip():
            r = json.loads(l)
            prescreen[r["record_id"]] = r.get("route")
full = [r for r in full if prescreen.get(r["record_id"]) != "human_nli"]

last = {}
if G.JOURNAL_FULL.exists():
    for l in G.JOURNAL_FULL.read_text(encoding="utf-8").splitlines():
        if l.strip():
            r = json.loads(l)
            last[r["record_id"]] = r
full = [r for r in full if last.get(r["record_id"]) is None or last[r["record_id"]].get("verdict") != "promote"]
if N:
    full = full[:N]

outdir = G.STORE / "试车-工作流"
arch = outdir / "试点轮存档"
arch.mkdir(parents=True, exist_ok=True)
ts = time.strftime("%H%M%S")
for nm in ("manifest.jsonl", "ds_votes.jsonl", "third_votes.jsonl"):
    src = outdir / nm
    if src.exists():
        os.replace(src, arch / f"{nm}.{ts}")
paydir = outdir / "payload"
if paydir.exists():
    os.replace(paydir, arch / f"payload.{ts}")
paydir.mkdir(parents=True, exist_ok=True)
(outdir / "glm_chunks").mkdir(exist_ok=True)

items = []


def add(rid, rec, sup, is_plant, expected):
    payload = G.build_payload(rec, sup)
    conclusion = json.dumps(payload["canonical"], ensure_ascii=False, sort_keys=True)
    evidence = "；".join(payload["evidence_quotes"])
    fn = f"{len(items):05d}.json"
    (paydir / fn).write_text(
        json.dumps({"record_id": rid, "conclusion": conclusion, "evidence": evidence}, ensure_ascii=False),
        encoding="utf-8")
    items.append({"idx": len(items), "record_id": rid, "file": f"试车-工作流/payload/{fn}",
                  "is_plant": is_plant, "expected": expected})


skipped = 0
for r in full:
    rec_path = next(G.STORE.glob(f"libraries/{r['library']}/*/{r['record_id']}.json"), None)
    if rec_path is None:
        skipped += 1
        continue
    rec = json.loads(rec_path.read_text(encoding="utf-8"))
    add(r["record_id"], rec, r.get("supplements"), False, None)

for p in G.build_plants(4):
    add(p["record_id"], p["rec"], p["supplements"], True, p["expected"])

(outdir / "manifest.jsonl").write_text(
    "".join(json.dumps(it, ensure_ascii=False) + "\n" for it in items), encoding="utf-8")
print(json.dumps({"n": len(items), "plants": sum(1 for i in items if i["is_plant"]),
                  "skipped_no_libfile": skipped, "dir": "试车-工作流"}, ensure_ascii=False))
