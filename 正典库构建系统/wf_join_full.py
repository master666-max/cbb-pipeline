# -*- coding: utf-8 -*-
"""wf_join_full.py — 三票满编合票（GLM chunks + DS votes + THIRD votes → 编制3/3 判词）。

输入：试车-工作流/glm_chunks/chunk_*.jsonl（GLM 票，文件是唯一真源）
     + ds_votes.jsonl 与 ds_votes_*.jsonl（DS 票，每 record 取最后一条有效票）
     + third_votes.jsonl（THIRD=ModelScope Step 票，每 record 取最后一条有效票）。
容错：任何一行 JSON 解析失败即跳过并计数（并发追加撕裂防线），坏行数进摘要。
B5 规则：need=2（满编 3，B13 不变）、any against → human、support≥2 ∧ n≥2 → promote、
n=0 → blocked、n<3 → degraded 显式标注。
植株捕获门走 audit.report 正确口径（0.95 门槛用在捕获率上——工单 B2 修正）。
台账 append-only；摘要写 G16c-重审摘要-工作流-放量.json；stdout 打印摘要 JSON。
"""
import glob
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "cbb-v2"))
from cbb2 import audit  # noqa: E402

STORE = ROOT / "迷深实战-本体库"
outdir = STORE / "试车-工作流"
manifest = [json.loads(l) for l in (outdir / "manifest.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]

VALID = {"support", "against", "unsure"}
bad_lines = 0


def load_votes(lines, vote_key):
    global bad_lines
    out = {}
    for l in lines:
        s = l.strip()
        if not s:
            continue
        try:
            r = json.loads(s)
        except Exception:
            bad_lines += 1
            continue
        if r.get(vote_key) in VALID:
            out[r["record_id"]] = r[vote_key]
    return out


glm = {}
for fp in sorted(glob.glob(str(outdir / "glm_chunks" / "chunk_*.jsonl"))):
    glm.update(load_votes(Path(fp).read_text(encoding="utf-8").splitlines(), "vote"))
ds = {}
ds_files = [outdir / "ds_votes.jsonl"] + [Path(p) for p in sorted(glob.glob(str(outdir / "ds_votes_*.jsonl")))]
for fp in ds_files:
    if fp.exists():
        ds.update(load_votes(fp.read_text(encoding="utf-8").splitlines(), "ds_vote"))
third = {}
tf = outdir / "third_votes.jsonl"
if tf.exists():
    third = load_votes(tf.read_text(encoding="utf-8").splitlines(), "third_vote")

rows_out = []
for it in manifest:
    rid = it["record_id"]
    votes, errors = {}, []
    g, d, t = glm.get(rid), ds.get(rid), third.get(rid)
    if g:
        votes["GLM"] = g
    else:
        errors.append({"examiner": "GLM", "reason": "缺席/非法票"})
    if d:
        votes["DEEPSEEK"] = d
    else:
        errors.append({"examiner": "DEEPSEEK", "reason": "缺席/非法票"})
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
    rows_out.append({"record_id": rid, "verdict": verdict, "votes": votes, "need": need,
                     "against": against, "errors": errors, "degraded": n < 3,
                     "is_plant": bool(it.get("is_plant")), "expected": it.get("expected"),
                     "口径": "编制3/3：GLM=本会话端口(工作流子代理)、DEEPSEEK=官方API、THIRD=ModelScope API-Inference(Step-3.7-Flash)"})

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
rep_plant = audit.report(correct, len(plants)) if plants else {}

summary = {
    "unit": "G16c-wf-fullrun3",
    "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    "规模": f"{len(real)} 正件 + {len(plants)} 株",
    "植物捕获": f"{correct}/{len(plants)} = {capture:.2f}",
    "捕获门": "PASS" if gate else "FAIL——全卷结果降级仅参考",
    "植株audit_report": rep_plant,
    "判决分布": {"promote": n_pass,
                "hold": sum(1 for r in real if r["verdict"] == "hold"),
                "human": sum(1 for r in real if r["verdict"] == "human"),
                "blocked": sum(1 for r in real if r["verdict"] == "blocked")},
    "三票齐全": sum(1 for r in real if len(r["votes"]) == 3),
    "缺席票": sum(len(r["errors"]) for r in rows_out),
    "坏行跳过": bad_lines,
    "晋升率区间": (f"{n_pass}/{len(real)} = {n_pass / max(len(real), 1):.2f} "
                  f"[Wilson 95% {lo:.2f}, {hi:.2f}]") if real else "-",
}
(STORE / "G16c-重审摘要-工作流-放量.json").write_text(
    json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False))
