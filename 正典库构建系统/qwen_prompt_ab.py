# -*- coding: utf-8 -*-
"""qwen_prompt_ab.py — 提示词 A/B：旧 JUDGE_PROMPT vs 明确判定规则版，真实 hold 件翻转率。
判读：明确规则版把"真清晰"件从 unsure 拉回 support ⇒ 现提示词有缺陷，采纳；
      仍 unsure ⇒ 这些 hold 本就模糊，强制投票只会生产假自信，维持升级段设计。
"""
import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _env():
    return (os.environ["EXAMINER_QWEN_BASE"],
            os.environ.get("EXAMINER_QWEN_API_KEY") or os.environ.get("DASHSCOPE_API_KEY", ""),
            os.environ["EXAMINER_QWEN_MODEL"])

OLD = ("你是正典库独立考官。给定【证据摘录】与【记录断言】，判定证据是否支持断言。\n"
       "只输出 JSON：{\"verdict\":\"support|against|unsure\"}。支持=support；"
       "证据与断言不可同真=against；证据不足=unsure。禁止其他文字。")
NEW = ("你是正典库独立考官。给定【证据摘录】与【记录断言】，按下列规则判定：\n"
       "1) 证据摘录的原文**明确陈述**了断言内容（人名/地名/事件/关系可直接从原文指出）→ support\n"
       "2) 证据原文与断言**明确矛盾**（不可同真）→ against\n"
       "3) 证据与断言相关但原文**没有明说**（需要推测、反推、脑补才能得出）→ unsure\n"
       "只输出 JSON：{\"verdict\":\"support|against|unsure\"}。禁止其他文字。")


def judge(prompt, conclusion, evidence, order, channel=None):
    base, key, model = channel or _env()
    ev, cc = (evidence, conclusion) if order == "ev" else (conclusion, evidence)
    body = json.dumps({"model": model, "temperature": 0, "stream": False,
                       "messages": [{"role": "user",
                                     "content": f"{prompt}\n【证据摘录】{ev}\n【记录断言】{cc}"
                                     if order == "ev" else
                                     f"{prompt}\n【记录断言】{cc}\n【证据摘录】{ev}"}]}).encode()
    req = urllib.request.Request(base + "/chat/completions", data=body,
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + key})
    import re
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = json.loads(r.read().decode("utf-8"))["choices"][0]["message"]["content"]
    m = re.search(r"\{[^}]*\}", raw, re.DOTALL)
    return json.loads(m.group(0)).get("verdict") if m else "parse_err"


def main():
    rows = [json.loads(l) for l in
            (ROOT / "迷深实战-本体库" / "G16b-票面台账.jsonl").read_text(encoding="utf-8").splitlines()
            if l.strip()]
    last = {}
    for r in rows:
        last[r["record_id"]] = r
    holds = [r for r in last.values() if r["verdict"] == "hold"][:10]
    bodies = {}
    for f in ROOT.glob("迷深实战-本体库/libraries/*/*/*.json"):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        rid = d.get("record_id")
        if rid in {h["record_id"] for h in holds} and rid not in bodies:
            bodies[rid] = d
    flips = {"A_unsure->B_support": 0, "A_unsure->B_against": 0, "stay_unsure": 0, "other": 0}
    for h in holds:
        d = bodies.get(h["record_id"])
        if not d:
            continue
        cc = json.dumps(d.get("canonical") or {}, ensure_ascii=False, sort_keys=True)
        ev = "；".join(e.get("quote", "") for e in (d.get("evidence") or []))
        try:
            b = judge(NEW, cc, ev, "ev")
            b2 = judge(NEW, cc, ev, "concl")
            vb = b if b == b2 else "unsure"
        except Exception as e:  # noqa: BLE001 — 探针面
            vb = f"err:{str(e)[:40]}"
        key = (f"A_unsure->B_{vb}" if vb in ("support", "against")
               else "stay_unsure" if vb == "unsure" else f"other:{vb}")
        flips[key] = flips.get(key, 0) + 1
        print(f"{h['record_id']}: A=unsure → B={vb}")
    print("\n汇总:", flips)


if __name__ == "__main__":
    main()
