# -*- coding: utf-8 -*-
"""g17_patrol_execute.py — 波D·G17 首圈巡检执行器（总工单二批·波 D5）。

对象：G17-首圈巡检队列.json 首圈抽样（固定种子，50 件）。
巡检动作（重推导）：
  ①锚定重推导：anchor_check.anchored（当前 evidence 是否仍锚定断言实体）
  ②NLI 复核：Erlangshen-110M（本地免费）—— 明确 CONTRADICTION ⇒ 改判候选
产报：G17-首圈巡检报告.json（重推导一致率 + 改判率 + 基线落盘供 CUSUM）
"""
import json
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STORE = ROOT / "迷深实战-本体库"
QUEUE = STORE / "G17-首圈巡检队列.json"
OUT = STORE / "G17-首圈巡检报告.json"

sys.path.insert(0, str(ROOT / "cbb-v2"))
from cbb2.anchor_check import anchored  # noqa: E402


def load_record(rid):
    """rid 可能来自隔离区 item_id 或库 record_id——两者都试。"""
    qz = STORE / "quarantine-zone" / "items.jsonl"
    if qz.exists():
        for l in qz.read_text(encoding="utf-8").splitlines():
            if rid in l:
                it = json.loads(l)
                src = it.get("record_id")
                if src:
                    rec = next((json.loads(p.read_text(encoding="utf-8"))
                                for p in STORE.glob("libraries/*/*/*.json")
                                if p.name == src + ".json"), None)
                    if rec:
                        return rec
    return next((json.loads(p.read_text(encoding="utf-8"))
                 for p in STORE.glob("libraries/*/*/*.json")
                 if p.stem == rid), None)


def main():
    import os
    os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
    from transformers import pipeline

    q = json.loads(QUEUE.read_text(encoding="utf-8"))
    sample = q.get("首圈抽样", [])
    print(f"首圈抽样 {len(sample)} 件")

    nli = pipeline("text-classification",
                   model="IDEA-CCNL/Erlangshen-RoBERTa-110M-NLI", truncation=True)
    rows, t0 = [], time.time()
    for n, rid in enumerate(sample, 1):
        rec = load_record(rid)
        if rec is None:
            rows.append({"record_id": rid, "anchor": "missing_record"})
            continue
        lib = rec.get("library", "")
        ev = rec.get("evidence") or []
        anchor_ok = bool(ev) and anchored(lib, rec.get("canonical") or {}, ev)
        premise = "；".join(e.get("quote", "") for e in ev)[:1500]
        hypo = json.dumps(rec.get("canonical") or {}, ensure_ascii=False, sort_keys=True)[:500]
        try:
            out = nli({"text": premise, "text_pair": hypo}, truncation="longest_first",
                      max_length=510)
            label = out[0]["label"] if isinstance(out, list) else out["label"]
        except Exception as e:  # noqa: BLE001 — NLI 单件失败记 err 不拖批
            label = f"err:{str(e)[:40]}"
        rows.append({"record_id": rid, "anchor_ok": anchor_ok, "nli": label})
        if n % 10 == 0 or n == len(sample):
            print(f"  {n}/{len(sample)} {time.time()-t0:.0f}s", flush=True)

    c = Counter(r.get("nli") for r in rows)
    anchor_fail = sum(1 for r in rows if r.get("anchor_ok") is False)
    contrad = sum(1 for r in rows if r.get("nli") == "CONTRADICTION")
    n_nli = sum(1 for r in rows if r.get("nli") not in (None, "missing_record")
                and not str(r.get("nli")).startswith("err"))
    report = {
        "unit": "G17-首圈", "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "抽样": len(rows), "NLI分布": dict(c),
        "锚定重推导一致率": f"{len(rows)-anchor_fail}/{len(rows)}",
        "NLI改判候选率": f"{contrad}/{n_nli}",
        "改判候选": [r["record_id"] for r in rows if r.get("nli") == "CONTRADICTION"],
        "CUSUM基线": {"n": n_nli, "contrad_cnt": contrad,
                      "p0": round(contrad / n_nli, 4) if n_nli else None,
                      "口径": "改判率序列首点；控制限需 bootstrap（D3 三前提其一已备）"},
        "耗时s": round(time.time() - t0, 1),
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"✓ 首圈巡检报告 → {OUT}（锚定一致 {len(rows)-anchor_fail}/{len(rows)}，"
          f"NLI 改判候选 {contrad}）")


if __name__ == "__main__":
    main()