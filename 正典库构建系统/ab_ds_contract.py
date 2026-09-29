# -*- coding: utf-8 -*-
"""ab_ds_contract.py — DS 弃权根源 A/B：判词契约 v1（极简）vs v2（现行长静态头）。

背景：v1.13 严格双票终裁暴露 DS 弃权画像——正件 unsure 85.9%、植株 0/8 support。
两个竞争假设：
  H1 契约致保：v2 的从严倾向条款+判例引导把 DS 压保守（G16b 时代 v1 契约下 DS 曾投 1,273 support）；
  H2 语料致保：本轮 2,184 件系 hold 存量（缺锚族），v1 下 DS 同样会弃权。
判别设计：同批 60 件=8 株(已知答案) + 40 分歧带随机 + 12 DS-support 对照，
单序(ev-first)、temperature=0、同一调用参数，只换契约文本。
读数：分层 support 率对比 + 植株捕获对比 + 逐件翻转矩阵。
判读：植株 v1-support≥5/8 而 v2=0/8 ⇒ H1 实锤（契约致保）；v1 也 0/8 ⇒ H2。
成本：~120 次 deepseek-chat ≈ 分币级。
"""
import json
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "cbb-v2"))
from cbb2 import ops, promote  # noqa: E402
from g16c_rejudge import build_plants  # noqa: E402

V1_PROMPT = (
    "你是正典库独立考官。给定【证据摘录】与【记录断言】，判定证据是否支持断言。\n"
    "只输出 JSON：{\"verdict\":\"support|against|unsure\"}。支持=support；"
    "证据与断言不可同真=against；证据不足=unsure。禁止其他文字。"
)
V2_PROMPT = promote.JUDGE_PROMPT
BASE = "https://api.deepseek.com"
MODEL = "deepseek-chat"
KEY = ops.secret_from_registry("DEEPSEEK_API_KEY")
if not KEY:
    print("BLOCKED：DEEPSEEK_API_KEY 未注入（注册表）")
    sys.exit(2)


def vote(prompt, conclusion, evidence):
    raw = ops.chat_once(BASE, MODEL, KEY, f"{prompt}\n【证据摘录】{evidence}\n【记录断言】{conclusion}",
                        timeout=90.0)
    import re
    m = re.search(r"\{[^}]*\}", raw, re.DOTALL)
    return json.loads(m.group(0)).get("verdict") if m else f"no_json({len(raw)}字)"


manifest = {json.loads(l)["record_id"]: json.loads(l)["file"]
            for l in (ROOT / "迷深实战-本体库" / "试车-工作流" / "manifest.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}

# 分层样本
plants = build_plants(4, 20260928)
flip = [json.loads(l) for l in (ROOT / "迷深实战-本体库" / "试车-工作流" / "升级分歧带-r2-full.jsonl")
        .read_text(encoding="utf-8").splitlines() if l.strip()]
random.Random(20260929).shuffle(flip)
flip40 = flip[:40]
led = [json.loads(l) for l in (ROOT / "迷深实战-本体库" / "G16c-重审台账-工作流.jsonl").read_bytes().split(b"\n") if l.strip()]
ctrl = [r["record_id"] for r in led[-2192:] if not r.get("is_plant") and r["votes"].get("DEEPSEEK") == "support"][:12]

sample = []
for p in plants:
    sample.append({"rid": p["record_id"], "stratum": "plant", "expected": p["expected"],
                   "cc": json.dumps(p["rec"].get("canonical") or {}, ensure_ascii=False, sort_keys=True),
                   "ev": "；".join(e.get("quote", "") for e in (p["rec"].get("evidence") or []))})
for r in flip40:
    payload = json.loads((ROOT / "迷深实战-本体库" / manifest[r["record_id"]]).read_text(encoding="utf-8"))
    sample.append({"rid": r["record_id"], "stratum": "flip", "expected": None,
                   "cc": payload["conclusion"], "ev": payload["evidence"]})
for rid in ctrl:
    payload = json.loads((ROOT / "迷深实战-本体库" / manifest[rid]).read_text(encoding="utf-8"))
    sample.append({"rid": rid, "stratum": "ds_support_ctrl", "expected": None,
                   "cc": payload["conclusion"], "ev": payload["evidence"]})

print(f"样本 {len(sample)} 件（plant {len(plants)} / flip {len(flip40)} / ctrl {len(ctrl)}）×2 臂", flush=True)
rows = []
for i, s in enumerate(sample, 1):
    try:
        v1 = vote(V1_PROMPT, s["cc"], s["ev"])
    except Exception as e:  # noqa: BLE001 — 考试面
        v1 = f"err:{str(e)[:40]}"
    time.sleep(0.2)
    try:
        v2 = vote(V2_PROMPT, s["cc"], s["ev"])
    except Exception as e:  # noqa: BLE001
        v2 = f"err:{str(e)[:40]}"
    time.sleep(0.2)
    rows.append({**{k: s[k] for k in ("rid", "stratum", "expected")}, "v1": v1, "v2": v2})
    print(f"[{i}/{len(sample)}] {s['stratum']} {s['rid'][:24]} v1={v1} v2={v2}", flush=True)

out = ROOT / "迷深实战-本体库" / "DS弃权根源A-B.json"
out.write_text(json.dumps({"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "rows": rows}, ensure_ascii=False, indent=1), encoding="utf-8")

# 机械复算摘要
def agg(rows, key):
    from collections import Counter
    c = Counter(r[key] for r in rows)
    return dict(c)

summary = {}
for stratum in ("plant", "flip", "ds_support_ctrl"):
    sub = [r for r in rows if r["stratum"] == stratum]
    summary[stratum] = {"n": len(sub), "v1": agg(sub, "v1"), "v2": agg(sub, "v2"),
                        "v1_support": sum(1 for r in sub if r["v1"] == "support"),
                        "v2_support": sum(1 for r in sub if r["v2"] == "support")}
flips = sum(1 for r in rows if r["v1"] == "support" and r["v2"] == "unsure")
summary["v1support_v2unsure_翻转"] = flips
summary["判读"] = ("H1 契约致保：plant 层 v1_support 显著高于 v2（v2=0/8 且 v1≥5/8 即实锤）"
           if summary["plant"]["v1_support"] >= 5 and summary["plant"]["v2_support"] == 0 else
           "H2/混合：plant 层 v1 也未恢复 support——契约非唯一因，看 flip/ctrl 层分布再判")
print(json.dumps(summary, ensure_ascii=False, indent=1))
(out.parent / "DS弃权根源A-B-摘要.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
