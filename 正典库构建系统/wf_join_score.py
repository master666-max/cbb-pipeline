# -*- coding: utf-8 -*-
"""wf_join_score.py — 工作流判卷合票（G16c 工作流版收口）。

B5 规则与 promote.vote 同构（full_size=3 → need=2；any against → human；
support≥2 ∧ n≥2 → promote；其余 hold；n=0 → blocked；编制不满=degraded 显式标注）。
植株捕获门与 g16c 同一门：correct≥5 ∧ capture≥5/6，否则全卷降级仅参考。
Wilson 区间走 cbb2.audit（点宣称禁令）。台账 append-only 落
G16c-重审台账-工作流.jsonl；stdout 打印摘要 JSON。
用法：py -X utf8 wf_join_score.py --glm '<json 数组>'
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "cbb-v2"))
from cbb2 import audit  # noqa: E402

glm_raw = sys.argv[sys.argv.index("--glm") + 1]
glm_list = json.loads(glm_raw)
glm = {}
for v in glm_list:
    if isinstance(v, dict) and v.get("record_id"):
        glm[v["record_id"]] = v

outdir = ROOT / "迷深实战-本体库" / "试车-工作流"
manifest = [json.loads(l) for l in (outdir / "manifest.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
ds = {}
dsf = outdir / "ds_votes.jsonl"
if dsf.exists():
    for l in dsf.read_text(encoding="utf-8").splitlines():
        if l.strip():
            r = json.loads(l)
            ds[r["record_id"]] = r

VALID = {"support", "against", "unsure"}
rows_out = []
for it in manifest:
    rid = it["record_id"]
    g = glm.get(rid, {}).get("vote")
    if g not in VALID:
        g = None
    d = ds.get(rid, {}).get("ds_vote")
    if d not in VALID:
        d = None
    votes, errors = {}, []
    if g:
        votes["GLM"] = g
    else:
        errors.append({"examiner": "GLM", "reason": str(glm.get(rid, {}).get("err") or "缺席/非法票")[:100]})
    if d:
        votes["DEEPSEEK"] = d
    else:
        errors.append({"examiner": "DEEPSEEK", "reason": str(ds.get(rid, {}).get("err") or "缺席/非法票")[:100]})
    n = len(votes)
    against = sum(1 for v in votes.values() if v == "against")
    support = sum(1 for v in votes.values() if v == "support")
    need = 2  # full_size=3（B13：需票按满编算，缩员不降门槛）
    if n == 0:
        verdict = "blocked"
    elif against > 0:
        verdict = "human"
    elif support >= need and n >= 2:
        verdict = "promote"
    else:
        verdict = "hold"
    rows_out.append({"record_id": rid, "verdict": verdict, "votes": votes, "need": need,
                     "against": against, "errors": errors, "degraded": n < 3,
                     "is_plant": bool(it.get("is_plant")), "expected": it.get("expected"),
                     "口径": "编制2/3：GLM=本会话端口(工作流子代理)、DEEPSEEK=官方API；第三票待定"})

journal = ROOT / "迷深实战-本体库" / "G16c-重审台账-工作流.jsonl"
with journal.open("a", encoding="utf-8") as jf:
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
    "unit": "G16c-wf",
    "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    "植物捕获": f"{correct}/{len(plants)} = {capture:.2f}",
    "捕获门": "PASS" if gate else "FAIL——全卷结果降级仅参考",
    "判决分布": {"promote": n_pass,
                "hold": sum(1 for r in real if r["verdict"] == "hold"),
                "human": sum(1 for r in real if r["verdict"] == "human"),
                "blocked": sum(1 for r in real if r["verdict"] == "blocked")},
    "缺席票": sum(len(r["errors"]) for r in rows_out),
    "晋升率区间": (f"{n_pass}/{len(real)} = {n_pass / max(len(real), 1):.2f} "
                  f"[Wilson 95% {lo:.2f}, {hi:.2f}]") if real else "-",
    "audit_report": rep,
}
(ROOT / "迷深实战-本体库" / "G16c-重审摘要-工作流.json").write_text(
    json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False))
