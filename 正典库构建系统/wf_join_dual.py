# -*- coding: utf-8 -*-
"""wf_join_dual.py — v1.9/v1.11 编制合票器（GLM×DS 常编双票 + THIRD 升级票）。

背景：v1.9 裁决 Step 降级抽检/重点失锚区域后，满编 3/3 口径退役；但纯"双票一致"
会使植株考试死锁（DS 两轮实证 8 株全弃权，正株永远凑不齐双 support → 门限 7/8
永不可达 → 每轮参考值）。故按二批工单 B6 升级段设计：

  晋升 = GLM∧DS 双 support（满编一致）
       ∨ 单 support 分歧带（恰一票 support、零 against、另一票 unsure/缺席）
         ∧ THIRD(阶跃官方)=support —— 分歧带=重点失锚区域本体，Step 判别力最强处
  any against → human；双 unsure → hold；n=0 → blocked

两相：
  --export  导出升级分歧带清单（升级分歧带-r2.jsonl，含植株）——给补票件
  --final   终裁：append-only 台账追加一轮（口径=编制2/3+升级票）+ 摘要 + 植株捕获门
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
KOUJING = "编制2/3(v1.9严格执行)：GLM=会话端口、DEEPSEEK=官方API 双票一致，THIRD 不进主链(仅抽检审计)"
VALID = {"support", "against", "unsure"}


def load(pattern, key):
    d = {}
    bad = 0
    for fp in sorted(glob.glob(str(outdir / pattern))):
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
    return d, bad


manifest = [json.loads(l) for l in (outdir / "manifest.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
_privf = outdir / "manifest_priv.jsonl"
priv = {r["record_id"]: r for r in
        (json.loads(l) for l in (_privf if _privf.exists() else outdir / "manifest.jsonl")
         .read_text(encoding="utf-8").splitlines() if l.strip())}
glm, bad1 = load("glm_chunks/chunk_*.jsonl", "vote")
ds, bad2 = load("ds_votes*.jsonl", "ds_vote")
th, bad3 = load("third_votes*.jsonl", "third_vote")
bad_lines = bad1 + bad2 + bad3


def verdict_for(rid):
    # v1.9 严格执行（v1.13）：THIRD 不进主链——判词只由 GLM×DS 构成，双票一致方晋升。
    # 已银行的第三方票全部转为抽检审计数据（对账报告另出），不参与任何 verdict。
    g, d = glm.get(rid), ds.get(rid)
    votes, errors = {}, []
    if g:
        votes["GLM"] = g
    else:
        errors.append({"examiner": "GLM", "reason": "缺席/非法票"})
    if d:
        votes["DEEPSEEK"] = d
    else:
        errors.append({"examiner": "DEEPSEEK", "reason": "缺席/非法票"})
    n = len(votes)
    against = sum(1 for v in votes.values() if v == "against")
    if n == 0:
        return votes, errors, "blocked"
    if against > 0:
        return votes, errors, "human"
    if g == "support" and d == "support":
        return votes, errors, "promote"
    return votes, errors, "hold"


if "--export" in sys.argv:
    rows = []
    for it in manifest:
        rid = it["record_id"]
        g, d = glm.get(rid), ds.get(rid)
        if g is None and d is None:
            continue
        against = sum(1 for v in (g, d) if v == "against")
        support = sum(1 for v in (g, d) if v == "support")
        if against == 0 and support == 1:
            rows.append({"record_id": rid, "gl": g, "ds": d, "third_banked": th.get(rid),
                         "is_plant": bool(priv.get(rid, {}).get("is_plant"))})
    (outdir / "升级分歧带-r2.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    missing = sum(1 for r in rows if not r["third_banked"])
    print(json.dumps({"分歧带": len(rows), "GLM侧": sum(1 for r in rows if r["gl"] == "support"),
                      "DS侧": sum(1 for r in rows if r["ds"] == "support"),
                      "植株": sum(1 for r in rows if r["is_plant"]),
                      "THIRD已银行": len(rows) - missing, "需补票": missing}, ensure_ascii=False))
    sys.exit(0)

if "--final" in sys.argv:
    rows_out = []
    stuck = 0
    for it in manifest:
        rid = it["record_id"]
        votes, errors, v = verdict_for(rid)
        if any(e.get("reason") == "升级票缺席" for e in errors):
            stuck += 1
        rows_out.append({"record_id": rid, "verdict": v, "votes": votes, "need": 2,
                         "against": sum(1 for x in votes.values() if x == "against"),
                         "errors": errors, "degraded": len(votes) < 2,
                         "is_plant": bool(priv[rid].get("is_plant")), "expected": priv[rid].get("expected"),
                         "口径": KOUJING})
    with (STORE / "G16c-重审台账-工作流.jsonl").open("a", encoding="utf-8") as jf:
        for r in rows_out:
            jf.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
            jf.flush()
    real = [r for r in rows_out if not r["is_plant"]]
    plants = [r for r in rows_out if r["is_plant"]]

    def _correct(r):
        return (r["verdict"] == "promote") if r["expected"] == "promote" else (r["verdict"] in ("hold", "human"))

    correct = sum(1 for r in plants if _correct(r))
    capture = correct / len(plants) if plants else 0.0
    gate = len(plants) > 0 and correct >= 5 and capture >= 5 / 6
    n_pass = sum(1 for r in real if r["verdict"] == "promote")
    lo, hi = audit.wilson(n_pass, len(real)) if real else (0, 0)
    dist = {v: sum(1 for r in real if r["verdict"] == v) for v in ("promote", "hold", "human", "blocked")}
    summary = {
        "unit": "G16c-wf-dual-v11",
        "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "口径": KOUJING,
        "规模": f"{len(real)} 正件 + {len(plants)} 株",
        "植物捕获": f"{correct}/{len(plants)} = {capture:.2f}",
        "捕获门": "PASS" if gate else "FAIL——全卷结果降级仅参考",
        "判决分布": dist,
        "双票一致直晋": sum(1 for r in real if r["verdict"] == "promote"),
        "单票弃权挂hold": sum(1 for r in real if r["verdict"] == "hold"
                          and r["votes"].get("GLM") in ("unsure", None) and r["votes"].get("DEEPSEEK") in ("unsure", None)),
        "缺席票": sum(len(r["errors"]) for r in rows_out),
        "坏行跳过": bad_lines,
        "晋升率区间": f"{n_pass}/{len(real)} = {n_pass / max(len(real), 1):.2f} [Wilson 95% {lo:.2f}, {hi:.2f}]",
    }
    (STORE / "G16c-重审摘要-工作流-双票.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    sys.exit(0)

print("用法：wf_join_dual.py --export | --final")
sys.exit(2)
