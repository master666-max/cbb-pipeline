# -*- coding: utf-8 -*-
"""ab_contract.py — 判卷产线·契约刻度 A/B（通用 runner，U3）。

两份契约文本 × 同批分层样本（植株全数 + 分歧带抽样）单序对跑，定位行为漂移源。
用法：py -X utf8 ab_contract.py --config judging.config.json --examiner DEEPSEEK
        --contract-a contracts/judge-v1.txt --contract-b contracts/judge-v2.2.txt
        --plants plants.jsonl --flip flip.jsonl [--flip-n 40] [--out 摘要.json]
输出：分层 support 率 + 翻转矩阵 + 判读建议（植株层一锤定音）。
"""
import argparse
import json
import random
import re
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "cbb-v2"))
from cbb2 import judging, ops  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--config", default="judging.config.json")
ap.add_argument("--examiner", default="DEEPSEEK")
ap.add_argument("--contract-a", required=True)
ap.add_argument("--contract-b", required=True)
ap.add_argument("--plants", required=True)
ap.add_argument("--flip", required=True, help="分歧带清单 jsonl（record_id+conclusion+evidence 或 record_id+file）")
ap.add_argument("--flip-n", type=int, default=40)
ap.add_argument("--seed", type=int, default=20260929)
ap.add_argument("--out", default=None)
ns = ap.parse_args()

cfg = judging.load_config(ns.config)
e = cfg.examiner(ns.examiner)
key = e.key()
if not key:
    print("BLOCKED：考官 key 未解析")
    sys.exit(2)
ca = Path(ns.contract_a).read_text(encoding="utf-8")
cb = Path(ns.contract_b).read_text(encoding="utf-8")

plants = judging.load_plants_jsonl(ns.plants)
flip = [json.loads(l) for l in Path(ns.flip).read_text(encoding="utf-8").splitlines() if l.strip()]
random.Random(ns.seed).shuffle(flip)
flip = flip[:ns.flip_n]

work = cfg.work_dir
sample = []
for p in plants:
    c, ev = judging._plant_concl_evi(p["rec"])
    sample.append({"rid": p["record_id"], "stratum": "plant", "expected": p["expected"],
                   "conclusion": c, "evidence": ev})
man = judging.load_manifest(work)[0]
src_by_rid = {r["record_id"]: r for r in man}
for r in flip:
    rid = r["record_id"]
    f = Path(src_by_rid[rid]["file"]) if rid in src_by_rid else Path(r["file"])
    payload = json.loads(f.read_text(encoding="utf-8"))
    sample.append({"rid": rid, "stratum": "flip", "expected": None,
                   "conclusion": payload["conclusion"], "evidence": payload["evidence"]})


def vote(contract, conclusion, evidence):
    raw = ops.chat_once(e.base, e.model, key,
                        f"{contract}\n【证据摘录】{evidence}\n【记录断言】{conclusion}",
                        timeout=90.0, max_tokens=e.max_tokens)
    if e.paced:
        time.sleep(0.4)
    m = re.search(r"\{[^}]*\}", raw, re.DOTALL)
    if not m:
        raise ValueError(f"考官输出非 JSON：{raw[:60]!r}")
    v = json.loads(m.group(0)).get("verdict")
    if v not in ("support", "against", "unsure"):
        raise ValueError(f"考官判定非法：{v!r}")
    return v


rows = []
for i, s in enumerate(sample, 1):
    va = vote(ca, s["conclusion"], s["evidence"])
    vb = vote(cb, s["conclusion"], s["evidence"])
    rows.append({k: s[k] for k in ("rid", "stratum", "expected")} | {"va": va, "vb": vb})
    print(f"[{i}/{len(sample)}] {s['stratum']} {s['rid'][:24]} A={va} B={vb}", flush=True)

summary = {}
for stratum in ("plant", "flip"):
    sub = [r for r in rows if r["stratum"] == stratum]

    def _sup(rs, k):
        return sum(1 for r in rs if r[k] == "support")

    summary[stratum] = {"n": len(sub), "A_support": _sup(sub, "va"), "B_support": _sup(sub, "vb"),
                        "A": dict(Counter(r["va"] for r in sub)), "B": dict(Counter(r["vb"] for r in sub))}
flips = sum(1 for r in rows if r["va"] == "support" and r["vb"] != "support")
summary["A_support_B丢失"] = flips
summary["判读"] = ("plant 层 A 支持率显著高于 B 且 B 接近 0 ⇒ B 契约含抑制性条款（对照 PT-026 削峰）"
           if summary["plant"]["A_support"] >= 3 and summary["plant"]["B_support"] <= 1 else
           "plant 层两版接近 ⇒ 契约非主要漂移源，看 flip 层分布再判")
out = ns.out or str(cfg.work_dir / f"契约A-B-{Path(ns.contract_a).stem}-{Path(ns.contract_b).stem}.json")
Path(out).write_text(json.dumps({"rows": rows, "summary": summary}, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False, indent=1))
print("明细:", out)
