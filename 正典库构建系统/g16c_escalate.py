# -*- coding: utf-8 -*-
"""g16c_escalate.py — B6 升级段：单 support 件 → m-prometheus 第三票（串行 GPU）。

对象：G16c-重审台账.jsonl 末行 verdict=hold 且恰好一票 support 的件。
机制：m-prometheus-14b 隔离双序（max_tokens 截断 CoT 提速）→ 三票重算
      （B13：≥2/3 support 且 against=0 ⇒ promote；任何 against ⇒ human）。
台账：G16c-升级台账.jsonl（append-only，幂等续跑——已升级 rid 跳过）。
"""
import json
import os
import re
import sys
import time
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STORE = ROOT / "迷深实战-本体库"
G16C = STORE / "G16c-重审台账.jsonl"
BACKFILL = STORE / "补充证据-回填.jsonl"
JOURNAL = STORE / "G16c-升级台账.jsonl"

BASE = os.environ.get("EXAMINER_LOCAL_BASE", "")
MODEL = os.environ.get("EXAMINER_LOCAL_MODEL", "")
KEY = os.environ.get("EXAMINER_LOCAL_API_KEY", "")
PROMPT = ("你是正典库独立考官。给定【证据摘录】与【记录断言】，判定证据是否支持断言。\n"
          "只输出 JSON：{\"verdict\":\"support|against|unsure\"}。支持=support；"
          "证据与断言不可同真=against；证据不足=unsure。禁止其他文字。")


def chat(conclusion, evidence, order):
    ev, cc = (evidence, conclusion) if order == "ev" else (conclusion, evidence)
    body = json.dumps({"model": MODEL, "temperature": 0, "stream": False,
                       "max_tokens": 64,
                       "messages": [{"role": "user",
                                     "content": f"{PROMPT}\n【证据摘录】{ev}\n【记录断言】{cc}"
                                     if order == "ev" else
                                     f"{PROMPT}\n【记录断言】{cc}\n【证据摘录】{ev}"}]}).encode()
    req = urllib.request.Request(BASE.rstrip("/") + "/chat/completions", data=body,
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {KEY}" if KEY else ""})
    with urllib.request.urlopen(req, timeout=120) as r:
        raw = json.loads(r.read().decode("utf-8"))["choices"][0]["message"]["content"]
    m = re.search(r"\{[^}]*\}", raw, re.DOTALL)
    if not m:
        raise ValueError(f"非 JSON 输出：{raw[:60]!r}")
    return json.loads(m.group(0)).get("verdict")


def main():
    last = {}
    for l in G16C.read_text(encoding="utf-8").splitlines():
        if l.strip():
            r = json.loads(l)
            last[r["record_id"]] = r
    done = set()
    if JOURNAL.exists():
        for l in JOURNAL.read_text(encoding="utf-8").splitlines():
            if l.strip():
                done.add(json.loads(l)["record_id"])

    targets = []
    for rid, r in last.items():
        if rid in done or r.get("verdict") != "hold":
            continue
        votes = r.get("votes", {})
        if sorted(votes.values()) == ["support", "unsure"]:  # 恰一票 support——第三票可翻
            targets.append((rid, r))
    print(f"升级目标: {len(targets)} 件（单 support hold）")
    if not targets:
        return

    bf = {}
    for l in BACKFILL.read_text(encoding="utf-8").splitlines():
        if l.strip():
            r = json.loads(l)
            bf[r["record_id"]] = r

    t0 = time.time()
    with JOURNAL.open("a", encoding="utf-8") as jf:
        for n, (rid, r) in enumerate(targets, 1):
            row = bf.get(rid)
            rec = None
            if row:
                rec_path = next(STORE.glob(f"libraries/{row['library']}/*/{rid}.json"), None)
                if rec_path:
                    rec = json.loads(rec_path.read_text(encoding="utf-8"))
            if not rec:
                continue
            conclusion = json.dumps(rec.get("canonical") or {}, ensure_ascii=False, sort_keys=True)
            evidence = "；".join([e.get("quote", "") for e in (rec.get("evidence") or [])] +
                                 [s.get("quote", "") for s in row.get("supplements", [])])
            try:
                a = chat(conclusion, evidence, "ev")
                b = chat(conclusion, evidence, "concl")
                v3 = a if a == b else "unsure"
            except Exception as e:  # noqa: BLE001 — 升级失败=保持 hold，票面记因
                v3 = None
                jf.write(json.dumps({"record_id": rid, "verdict": "hold", "escalation_error":
                                     str(e)[:120], "at": time.strftime("%Y-%m-%dT%H:%M:%S")},
                                    ensure_ascii=False, sort_keys=True) + "\n")
                jf.flush()
                continue
            votes = dict(r.get("votes", {}))
            votes["LOCAL3"] = v3
            support = sum(1 for v in votes.values() if v == "support")
            against = sum(1 for v in votes.values() if v == "against")
            verdict = "promote" if (support >= 2 and against == 0) else \
                      ("human" if against > 0 else "hold")
            jf.write(json.dumps({"record_id": rid, "verdict": verdict,
                                 "votes": votes, "escalated": True,
                                 "at": time.strftime("%Y-%m-%dT%H:%M:%S")},
                                ensure_ascii=False, sort_keys=True) + "\n")
            jf.flush()
            if n % 25 == 0 or n == len(targets):
                el = time.time() - t0
                print(f"  {n}/{len(targets)}  {el:.0f}s（ETA {el/n*(len(targets)-n)/3600:.1f}h）",
                      flush=True)
    print(f"✓ 升级段收口 → {JOURNAL}")


if __name__ == "__main__":
    main()
