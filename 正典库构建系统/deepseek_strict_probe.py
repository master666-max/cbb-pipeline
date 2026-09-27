# -*- coding: utf-8 -*-
"""deepseek_strict_probe.py — 同批 hold 件对 DEEPSEEK 做旧/严提示词 A/B。
回答：DEEPSEEK 的 support 是"读出了原文说了"还是"把不矛盾当支持"——
      若严格规则下 DEEPSEEK 也翻转成 unsure ⇒ 它此前把 plausibility 当 entailment；
      若仍 support ⇒ 它判断的依据与 QWEN 不同（异构性本身，非宽松）。
"""
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent

sys.path.insert(0, str(ROOT))
from qwen_prompt_ab import OLD, NEW, judge  # noqa: E402


def _ds_channel():
    return (os.environ["EXAMINER_DEEPSEEK_BASE"],
            os.environ["DEEPSEEK_API_KEY"],
            os.environ["EXAMINER_DEEPSEEK_MODEL"])


def main():
    rows = [json.loads(l) for l in
            (ROOT / "迷深实战-本体库" / "G16b-票面台账.jsonl").read_text(encoding="utf-8").splitlines()
            if l.strip()]
    last = {}
    for r in rows:
        last[r["record_id"]] = r
    holds = [r for r in last.values() if r["verdict"] == "hold"][:6]
    bodies = {}
    for f in ROOT.glob("迷深实战-本体库/libraries/*/*/*.json"):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        rid = d.get("record_id")
        if rid in {h["record_id"] for h in holds} and rid not in bodies:
            bodies[rid] = d
    c = {"old_support": 0, "old_other": 0, "new_support": 0, "new_unsure": 0,
         "new_against": 0, "new_other": 0}
    for h in holds:
        d = bodies.get(h["record_id"])
        if not d:
            continue
        cc = json.dumps(d.get("canonical") or {}, ensure_ascii=False, sort_keys=True)
        ev = "；".join(e.get("quote", "") for e in (d.get("evidence") or []))
        vo = judge(OLD, cc, ev, "ev", channel=_ds_channel())
        vn = judge(NEW, cc, ev, "ev", channel=_ds_channel())
        if vo == "support":
            c["old_support"] += 1
        else:
            c["old_other"] += 1
        if vn == "support":
            c["new_support"] += 1
        elif vn == "unsure":
            c["new_unsure"] += 1
        elif vn == "against":
            c["new_against"] += 1
        else:
            c["new_other"] += 1
        print(f"{h['record_id']}: DS旧={vo} → DS严={vn}")
    print("\n汇总:", c)


if __name__ == "__main__":
    main()
