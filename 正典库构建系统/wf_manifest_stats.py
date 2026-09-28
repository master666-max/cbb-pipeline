# -*- coding: utf-8 -*-
"""wf_manifest_stats.py — 打印 manifest 规模 JSON（工作流核对相位用）。

植株计数走 manifest_priv.jsonl（判卷面剥敏后 manifest 不再携带 is_plant），
无 priv 的旧轮回落 manifest 自带字段。
"""
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent / "迷深实战-本体库" / "试车-工作流"
rows = [json.loads(l) for l in (BASE / "manifest.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
privf = BASE / "manifest_priv.jsonl"
src = privf if privf.exists() else BASE / "manifest.jsonl"
priv = [json.loads(l) for l in src.read_text(encoding="utf-8").splitlines() if l.strip()]
print(json.dumps({"n": len(rows), "plants": sum(1 for r in priv if r["is_plant"])}, ensure_ascii=False))
