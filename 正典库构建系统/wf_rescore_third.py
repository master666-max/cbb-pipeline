# -*- coding: utf-8 -*-
"""wf_rescore_third.py — 三票满编重计分（G16c 工作流）。

读台账最近一轮编制2/3行 + third_votes.jsonl，按 B5 规则三票重算：
need=2（满编3，B13 不变）、any against → human、support≥2 ∧ n≥2 → promote、
n=0 → blocked、n<3 → degraded 显式标注。植株捕获门重算（correct≥5 ∧ ≥5/6）。
新行 append 落同一台账（append-only 审计链），摘要写 G16c-重审摘要-工作流-满编.json。
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "cbb-v2"))
from cbb2 import audit  # noqa: E402

STORE = ROOT / "迷深实战-本体库"
outdir = STORE / "试车-工作流"
manifest = {json.loads(l)["record_id"]: json.loads(l)
            for l in (outdir / "manifest.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}
third = {}
tf = outdir / "third_votes.jsonl"
if tf.exists():
    for l in tf.read_text(encoding="utf-8").splitlines():
        if l.strip():
            r = json.loads(l)
            if r.get("third_vote") in ("support", "against", "unsure"):
                third[r["record_id"]] = r["third_vote"]

VALID = {"support", "against", "unsure"}
# 只取台账中【最后一段连续】的编制2/3行——历史试点轮的 2/3 行不回填，避免混轮
blocks = []
cur = []
for l in (STORE / "G16c-重审台账-工作流.jsonl").read_text(encoding="utf-8").splitlines():
    if not l.strip():
        continue
    r = json.loads(l)
    if r.get("口径", "").startswith("编制2/3"):
        cur.append(r)
    elif cur:
        blocks.append(cur)
        cur = []
if cur:
    blocks.append(cur)
rows2 = blocks[-1] if blocks else []

rows_out = []
for r in rows2:
    rid = r["record_id"]
    t = third.get(rid)
    votes = dict(r.get("votes") or {})
    errors = []
    if t:
        votes["THIRD"] = t
    else:
        errors.append({"examiner": "THIRD", "reason": "缺席/非法票"})
    n = len(votes)
    against = sum(1 for v in votes.values() if v == "against")
    support = sum(1 for v in votes.values() if v == "support")
    need = 2
    if n == 0:
        verdict = "blocked"
    elif against > 0:
        verdict = "human"
    elif support >= need and n >= 2:
        verdict = "promote"
    else:
        verdict = "hold"
    it = manifest.get(rid, {})
    rows_out.append({"record_id": rid, "verdict": verdict, "votes": votes, "need": need,
                     "against": against, "errors": errors, "degraded": n < 3,
                     "is_plant": bool(it.get("is_plant")), "expected": it.get("expected"),
                     "口径": "编制3/3：GLM=本会话端口(工作流子代理)、DEEPSEEK=官方API、THIRD=ModelScope API-Inference(Step)"})

with (STORE / "G16c-重审台账-工作流.jsonl").open("a", encoding="utf-8") as jf:
    for r in rows_out:
        jf.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
        jf.flush()

plants = [r for r in rows_out if r["is_plant"]]
correct = 0
for r in plants:
    v, exp = r["verdict"], r.get("expected")
    ok = (v == "promote") if exp == "promote" else (v in ("hold", "human"))
    correct += bool(ok)
capture = correct / len(plants) if plants else 0.0
gate = len(plants) > 0 and correct >= 5 and capture >= 5 / 6

real = [r for r in rows_out if not r["is_plant"]]
n_pass = sum(1 for r in real if r["verdict"] == "promote")
lo, hi = audit.wilson(n_pass, len(real)) if real else (0, 0)
rep = audit.report(n_pass, len(real)) if real else {}

summary = {
    "unit": "G16c-wf-full",
    "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    "植物捕获": f"{correct}/{len(plants)} = {capture:.2f}",
    "捕获门": "PASS" if gate else "FAIL——全卷结果降级仅参考",
    "判决分布": {"promote": n_pass,
                "hold": sum(1 for r in real if r["verdict"] == "hold"),
                "human": sum(1 for r in real if r["verdict"] == "human"),
                "blocked": sum(1 for r in real if r["verdict"] == "blocked")},
    "缺席票": sum(len(r["errors"]) for r in rows_out),
    "三票一致率": (f"{sum(1 for r in real if len(set(r['votes'].values())) == 1 and len(r['votes']) == 3)}"
                  f"/{len(real)}"),
    "晋升率区间": (f"{n_pass}/{len(real)} = {n_pass / max(len(real), 1):.2f} "
                  f"[Wilson 95% {lo:.2f}, {hi:.2f}]") if real else "-",
    "audit_report": rep,
}
(STORE / "G16c-重审摘要-工作流-满编.json").write_text(
    json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False))
