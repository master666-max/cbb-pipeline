# -*- coding: utf-8 -*-
"""wf_join_v21.py — 契约 v2.1 五十件验证轮合票（GLM×DS 严格双票 + 植株门）。

输入：试车-工作流/v21验证轮/{manifest.jsonl,glm_chunks/chunk_*.jsonl,ds_votes_v21.jsonl}
判词：GLM∧DS 双 support ∧ 零 against → promote；any against → human；余 → hold。
植株门：correct≥5 ∧ capture≥5/6（8 株全数计门）。输出摘要 JSON 至 stdout 与 v21验证轮/摘要-v21.json。
"""
import glob
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "cbb-v2"))
from cbb2 import audit  # noqa: E402

outdir = ROOT / "迷深实战-本体库" / "试车-工作流" / "v21验证轮"
_args = sys.argv
GLM_DIR = outdir.parent / _args[_args.index("--glm-dir") + 1] if "--glm-dir" in _args else outdir / "glm_chunks"
DS_FILE = outdir.parent / _args[_args.index("--ds") + 1] if "--ds" in _args else outdir / "ds_votes_v21.jsonl"
TAG = _args[_args.index("--tag") + 1] if "--tag" in _args else "v21"
manifest = [json.loads(l) for l in (outdir / "manifest.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
VALID = {"support", "against", "unsure"}
bad = 0


def load(paths, key):
    d = {}
    global bad
    for fp in paths:
        for l in Path(fp).read_text(encoding="utf-8").splitlines():
            s = l.strip()
            if not s:
                continue
            try:
                r = json.loads(s)
            except Exception:
                bad += 1
                continue
            if r.get(key) in VALID:
                d[r["record_id"]] = r[key]
    return d


glm = load(sorted(glob.glob(str(GLM_DIR / "chunk_*.jsonl"))), "vote")
ds = load([DS_FILE], "ds_vote")

rows = []
for it in manifest:
    rid = it["record_id"]
    g, d = glm.get(rid), ds.get(rid)
    votes, errors = {}, []
    if g:
        votes["GLM"] = g
    else:
        errors.append({"examiner": "GLM"})
    if d:
        votes["DEEPSEEK"] = d
    else:
        errors.append({"examiner": "DEEPSEEK"})
    n = len(votes)
    against = sum(1 for v in votes.values() if v == "against")
    if n == 0:
        v = "blocked"
    elif against > 0:
        v = "human"
    elif g == "support" and d == "support":
        v = "promote"
    else:
        v = "hold"
    rows.append({"record_id": rid, "verdict": v, "votes": votes, "need": 2, "against": against,
                 "errors": errors, "degraded": n < 2, "is_plant": bool(it["is_plant"]),
                 "expected": it["expected"], "口径": "编制2/3·契约v2.1验证轮（50件，不做全量）"})

plants = [r for r in rows if r["is_plant"]]
real = [r for r in rows if not r["is_plant"]]

def _correct(r):
    return (r["verdict"] == "promote") if r["expected"] == "promote" else (r["verdict"] in ("hold", "human"))

correct = sum(1 for r in plants if _correct(r))
capture = correct / len(plants) if plants else 0.0
gate = len(plants) > 0 and correct >= 5 and capture >= 5 / 6
n_pass = sum(1 for r in real if r["verdict"] == "promote")
lo, hi = audit.wilson(n_pass, len(real)) if real else (0, 0)
dist = {v: sum(1 for r in real if r["verdict"] == v) for v in ("promote", "hold", "human", "blocked")}
summary = {
    "unit": f"G16c-wf-dual-{TAG}验证轮",
    "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    "契约": "v2.1 = v2 长静态头 − 从严倾向条款 − 四判例 + claim 元数据契约行",
    "规模": f"{len(real)} 正件 + {len(plants)} 株",
    "植物捕获": f"{correct}/{len(plants)} = {capture:.2f}",
    "捕获门": "PASS" if gate else "FAIL",
    "判决分布": dist,
    "支持率对照": {
        "DS_v2.1": f"{sum(1 for r in real if r['votes'].get('DEEPSEEK') == 'support')}/{len(real)}",
        "DS_v2_量产": "308/2184 = 14.1%",
        "DS_v1_AB": "67.5%（分歧带层）",
    },
    "缺席票": sum(len(r["errors"]) for r in rows),
    "坏行跳过": bad,
    "晋升率区间": f"{n_pass}/{len(real)} = {n_pass / max(len(real), 1):.2f} [Wilson 95% {lo:.2f}, {hi:.2f}]",
}
(outdir / f"摘要-{TAG}.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False))
