# -*- coding: utf-8 -*-
"""wf_twd_shadow.py — G5 门 TWD 影子回放（补充工单 20260928 第五节：影子模式只记分不判票）。

读台账最后一段连续的编制3/3行（不足则退编制2/3行），DS-EM 拟合考官发射矩阵，
逐件算 p(θ+|votes)，按占位损失 (α,β) 出三支建议；对比现行 B5 判词 + 双票提前收线测算。
输出：迷深实战-本体库/G5-TWD影子报告.json；stdout 打印摘要。
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "cbb-v2"))
from cbb2 import twd  # noqa: E402

STORE = ROOT / "迷深实战-本体库"

# 占位损失（影子演示，未标定）：错晋升 λ_PN=10（正典污染最贵）＞误隔离 λ_NP=4＞人工 λ_B*=2＞正确 0。
# → α=0.8, β=0.5。上线替换前必须由 G10 判例窗口重标（工单四.1）。
LOSS_PLACEHOLDER = {"PP": 0.0, "PN": 10.0, "BP": 2.0, "BN": 2.0, "NP": 4.0, "NN": 0.0}

rows = [json.loads(l) for l in (STORE / "G16c-重审台账-工作流.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]


def last_block(prefix: str) -> list:
    blocks, cur = [], []
    for r in rows:
        if r.get("口径", "").startswith(prefix):
            cur.append(r)
        elif cur:
            blocks.append(cur)
            cur = []
    if cur:
        blocks.append(cur)
    return blocks[-1] if blocks else []


block = last_block("编制3/3") or last_block("编制2/3")
if not block:
    print("BLOCKED：台账无可用轮次")
    sys.exit(2)
# 块内按 record_id 去重（rescore 连跑会拼接出连续同件行），保留最后一次判词
_dedup = {}
for r in block:
    _dedup[r["record_id"]] = r
block = list(_dedup.values())
recs = [{"record_id": r["record_id"], "votes": r.get("votes") or {}, "b5": r.get("verdict"),
         "is_plant": bool(r.get("is_plant"))} for r in block]

model = twd.dawid_skene_fit([r for r in recs if r["votes"]])
alpha, beta = twd.alpha_beta(LOSS_PLACEHOLDER)

out = []
agree = 0
early_total = early_decided = early_ok = 0
for r in recs:
    votes = r["votes"]
    p = twd.posterior(votes, model) if votes else None
    # against=0 硬门（工单 §2.1）：一票反对=真分歧信号，必进 human，后验不可越过
    if any(v == "against" for v in votes.values()):
        dec, mapped = "abstain-gate", "human"
    else:
        dec = twd.decide(p, alpha, beta) if p is not None else "abstain"
        mapped = {"positive": "promote", "boundary": "hold", "negative": "quarantine",
                  "abstain": "abstain", "abstain-gate": "human"}[dec]
    agree += bool(mapped == r["b5"])
    v2 = {k: votes[k] for k in ("GLM", "DEEPSEEK") if k in votes}
    if len(v2) == 2:
        early_total += 1
        d2 = twd.decide(twd.posterior(v2, model), alpha, beta)
        if d2 in ("positive", "negative"):
            early_decided += 1
            final = r["b5"]
            consistent = ((d2 == "positive" and final == "promote")
                          or (d2 == "negative" and final in ("hold", "human"))
                          or d2 == "boundary")
            early_ok += bool(consistent)
    out.append({"record_id": r["record_id"], "b5": r["b5"],
                "p": round(p, 4) if p is not None else None,
                "twd": dec, "mapped": mapped, "is_plant": r["is_plant"]})

summary = {
    "unit": "G5-TWD-shadow",
    "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    "样本": len(recs),
    "损失": {**LOSS_PLACEHOLDER, "口径": "占位未标定——上线前必须 G10 判例窗口重标（工单四.1）"},
    "alpha": round(alpha, 3),
    "beta": round(beta, 3),
    "prior_P(θ+)": round(model["prior"], 3),
    "考官发射": {e: {"P(support|θ+)": round(model["emit"][e][1]["support"], 3),
                    "P(support|θ−)": round(model["emit"][e][0]["support"], 3),
                    "P(unsure|θ+)": round(model["emit"][e][1]["unsure"], 3),
                    "P(unsure|θ−)": round(model["emit"][e][0]["unsure"], 3)}
                for e in model["emit"]},
    "与B5一致率": f"{agree}/{len(recs)}",
    "提前收线": f"{early_decided}/{early_total} 件双票即可三支定夺，其中与三票终判一致 {early_ok}",
    "建议隔离件": [o["record_id"] for o in out if o["mapped"] == "quarantine"],
    "口径": "影子模式：只记分不判票，线上 ⌈2/3⌉ 继续服役（工单第五节）",
}
(STORE / "G5-TWD影子报告.json").write_text(
    json.dumps({"summary": summary, "rows": out}, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False, indent=1))
