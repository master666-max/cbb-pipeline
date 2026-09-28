# -*- coding: utf-8 -*-
"""mp_plant_exam.py — m-prometheus 判卷上岗考试：8 株植株隔离双序，捕获率 ≥5/6 过门。
过门 → 晋升常编 DEEPSEEK+m-prometheus；不过 → 保持 DEEPSEEK 单票+人工队列现状。
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "cbb-v2"))

from g16c_rejudge import build_plant_exam_items  # noqa: E402
from g16c_escalate import chat  # noqa: E402


def main():
    items = build_plant_exam_items()
    print(f"植株 {len(items)} 株（正 {sum(1 for i in items if i['expected']=='promote')} / "
          f"负 {sum(1 for i in items if i['expected']=='not_promote')}）")
    correct = 0
    rows = []
    t0 = time.time()
    for n, it in enumerate(items, 1):
        rec, rid = it["rec"], it["record_id"]
        conclusion = json.dumps(rec.get("canonical") or {}, ensure_ascii=False, sort_keys=True)
        evidence = "；".join(e.get("quote", "") for e in (rec.get("evidence") or []))
        try:
            a = chat(conclusion, evidence, "ev")
            b = chat(conclusion, evidence, "concl")
            v = a if a == b else "unsure"
        except Exception as e:  # noqa: BLE001 — 考试面
            v = f"err:{str(e)[:60]}"
        exp = it["expected"]
        ok = (v == "support") if exp == "promote" else (v in ("unsure", "against"))  # 票面词汇对票面词汇
        correct += ok
        rows.append({"plant": rid, "expected": exp, "mp_verdict": v, "pass": ok})
        print(f"  [{n}] {rid[:32]} 期望={exp} → {v} {'✓' if ok else '✗'}")
    capture = correct / len(items) if items else 0
    gate = len(items) > 0 and correct >= 5 and capture >= 5 / 6
    out = {"exam": "m-prometheus 判卷上岗考试", "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "capture": f"{correct}/{len(items)} = {capture:.2f}",
           "gate(≥5/6)": "PASS" if gate else "FAIL", "rows": rows,
           "耗时s": round(time.time() - t0, 1)}
    (ROOT / "迷深实战-本体库" / "m-prometheus上岗考试.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("capture", "gate(≥5/6)", "耗时s")},
                     ensure_ascii=False))
    print("结论:", "m-prometheus 过门，常编 DEEPSEEK+m-prometheus" if gate
          else "m-prometheus 不过门——维持 DEEPSEEK 单票+人工队列现状")


if __name__ == "__main__":
    main()
