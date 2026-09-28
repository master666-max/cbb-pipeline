# -*- coding: utf-8 -*-
"""wf_manifest_stats.py — 打印 manifest 规模 JSON（工作流核对相位用）。"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
rows = [json.loads(l) for l in (ROOT / "迷深实战-本体库" / "试车-工作流" / "manifest.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
print(json.dumps({"n": len(rows), "plants": sum(1 for r in rows if r["is_plant"])}, ensure_ascii=False))
