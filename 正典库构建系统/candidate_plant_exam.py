# -*- coding: utf-8 -*-
"""candidate_plant_exam.py — QWEN 替代品候选·植物上岗考试（统一门 ≥5/6）。
候选：①百炼 ZHIPU/GLM-5.3-Flash（mt=4096，思考型）②本地 qwen3.6-35b MoE（mt=512）
计分：正植株须 support；负植株 unsure/against 均算合格（票面词汇对票面词汇）。
"""
import json
import subprocess
import sys
import time
import urllib.request
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "cbb-v2"))
from g16c_rejudge import build_plants  # noqa: E402

PROMPT = ("你是正典库独立考官。给定【证据摘录】与【记录断言】，判定证据是否支持断言。\n"
          "【记录断言】JSON 中的 claim 字段是抽取器元数据标注（true=正向，false=反推/否定性记录），"
          "**不是判定对象**。\n只输出 JSON：{\"verdict\":\"support|against|unsure\"}。禁止其他文字。")


def chat(base, model, cc, ev, order, key="", mt=512):
    evv, ccc = (ev, cc) if order == "ev" else (cc, ev)
    content_text = f"{PROMPT}\n【证据摘录】{evv}\n【记录断言】{ccc}" if order == "ev" else f"{PROMPT}\n【记录断言】{ccc}\n【证据摘录】{evv}"
    body = json.dumps({"model": model, "temperature": 0, "stream": False, "max_tokens": mt,
        "messages": [{"role": "user", "content": content_text}]}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(base.rstrip("/") + "/chat/completions", data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}" if key else ""})
    with urllib.request.urlopen(req, timeout=300) as r:
        d = json.loads(r.read().decode("utf-8"))
    msg = d["choices"][0]["message"]
    content = msg.get("content", "") or ""
    m = re.search(r"\{[^}]*\}", content, re.DOTALL)
    verdict = json.loads(m.group(0)).get("verdict") if m else f"no_json({len(content)}字)"
    return verdict, d.get("usage", {}).get("completion_tokens")


def exam(name, base, model, key="", mt=512, plants=None):
    print(f"== 候选 {name} ==")
    correct, rows, t0 = 0, [], time.time()
    for n, p in enumerate(plants, 1):
        rec, exp = p["rec"], p["expected"]
        cc = json.dumps(rec.get("canonical") or {}, ensure_ascii=False, sort_keys=True)
        ev = "；".join(e.get("quote", "") for e in (rec.get("evidence") or []))
        try:
            a, _ = chat(base, model, cc, ev, "ev", key=key, mt=mt)
            b, _ = chat(base, model, cc, ev, "concl", key=key, mt=mt)
            v = a if a == b else "unsure"
        except Exception as e:  # noqa: BLE001 — 考试面
            v = f"err:{str(e)[:50]}"
        if exp == "promote":
            ok = (v == "support")
        else:
            ok = (v in ("unsure", "against"))
        correct += ok
        rows.append({"plant": p["record_id"][:30], "expected": exp, "verdict": v, "pass": ok})
        print(f"  [{n}] {p['record_id'][:30]} 期望={exp} → {v} {'✓' if ok else '✗'}", flush=True)
    capture = correct / len(plants)
    gate = correct >= 5 and capture >= 5 / 6
    print(f"  ⇒ {name}: {correct}/{len(plants)} = {capture:.2f}  门={'PASS' if gate else 'FAIL'}  "
          f"耗时 {time.time()-t0:.0f}s\n", flush=True)
    return {"name": name, "correct": correct, "total": len(plants),
            "capture": round(capture, 3), "gate": "PASS" if gate else "FAIL", "rows": rows}


def main():
    plants = build_plants(4, 20260928)
    key = subprocess.run(["powershell", "-NoProfile", "-Command",
        "[Environment]::GetEnvironmentVariable('DASHSCOPE_API_KEY','User')"],
        capture_output=True, text=True).stdout.strip()
    out = []
    out.append(exam("百炼GLM-5.3-Flash(mt4096)",
                    "https://dashscope.aliyuncs.com/compatible-mode/v1",
                    "ZHIPU/GLM-5.3-Flash", key=key, mt=4096, plants=plants))
    out.append(exam("本地35B-MoE(mt512)",
                    "http://127.0.0.1:8080/v1",
                    "qwen3.6-35b-a3b-uncensored-hauhaucs-aggressive", mt=512, plants=plants))
    (ROOT / "迷深实战-本体库" / "QWEN替代品植物考试.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    passed = [o["name"] for o in out if o["gate"] == "PASS"]
    print("过门候选:", passed or "无")


if __name__ == "__main__":
    main()
