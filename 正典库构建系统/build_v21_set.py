# -*- coding: utf-8 -*-
"""build_v21_set.py — 契约 v2.1 五十件验证集组装（8 株 + 30 分歧带 + 12 DS-support 对照）。

产线：迷深实战-本体库/试车-工作流/v21验证轮/{manifest.jsonl,payload/}。
样本与 DS 弃权根源 A/B 同源（flip 洗牌 seed=20260929；对照=本轮 DS support 件前 12）。
"""
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "cbb-v2"))
from g16c_rejudge import build_plants, build_payload  # noqa: E402

out = ROOT / "迷深实战-本体库" / "试车-工作流" / "v21验证轮"
(out / "payload").mkdir(parents=True, exist_ok=True)
(out / "glm_chunks").mkdir(exist_ok=True)

items = []


def add(rid, rec, expected, is_plant):
    fn = f"{len(items):05d}.json"
    payload = build_payload(rec, None)
    body = {"record_id": rid,
            "conclusion": json.dumps(payload["canonical"], ensure_ascii=False, sort_keys=True),
            "evidence": "；".join(payload["evidence_quotes"])}
    (out / "payload" / fn).write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
    items.append({"idx": len(items) - 1, "record_id": rid,
                  "file": f"试车-工作流/v21验证轮/payload/{fn}", "is_plant": is_plant, "expected": expected})


for p in build_plants(4, 20260928):
    add(p["record_id"], p["rec"], p["expected"], True)

rng = random.Random(20260929)
flip = [json.loads(l) for l in (out.parent / "升级分歧带-r2-full.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
rng.shuffle(flip)
led = [json.loads(l) for l in (ROOT / "迷深实战-本体库" / "G16c-重审台账-工作流.jsonl").read_bytes().split(b"\n") if l.strip()]
ctrl = [r["record_id"] for r in led[-2192:] if not r.get("is_plant") and r["votes"].get("DEEPSEEK") == "support"]
man = {json.loads(l)["record_id"]: json.loads(l)["file"]
       for l in (out.parent / "manifest.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}
def add_from_payload(rid):
    src = json.loads((ROOT / "迷深实战-本体库" / man[rid]).read_text(encoding="utf-8"))
    fn = f"{len(items):05d}.json"
    (out / "payload" / fn).write_text(json.dumps(
        {"record_id": rid, "conclusion": src["conclusion"], "evidence": src["evidence"]},
        ensure_ascii=False), encoding="utf-8")
    items.append({"idx": len(items) - 1, "record_id": rid,
                  "file": f"试车-工作流/v21验证轮/payload/{fn}", "is_plant": False, "expected": None})


for r in flip[:30]:
    add_from_payload(r["record_id"])
for rid in ctrl[:12]:
    add_from_payload(rid)

(out / "manifest.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in items), encoding="utf-8")
print(json.dumps({"件数": len(items), "株": sum(1 for i in items if i["is_plant"]),
                  "分歧带": 30, "对照": 12, "dir": str(out)}, ensure_ascii=False))
