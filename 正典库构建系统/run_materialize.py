# -*- coding: utf-8 -*-
"""run_materialize.py — 批次 5·物料化 CLI（store 正门 status_transition 通道）。

用法：py -X utf8 run_materialize.py --store 迷深实战-本体库 --round-ledger <判词台账>
        --tag <轮次名> [--require-pass-snapshot <摘要.json>] [--dry-run]
安全链：轮摘要植株捕获门 PASS（提供时强校验）→ load_round 滤 promote → 引擎防御票门
（双票一致∧零against）→ status provisional → gate1 零违例 → status_transition(by=promotion)。
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "cbb-v2"))
from cbb2 import materialize  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--store", required=True)
ap.add_argument("--round-ledger", required=True)
ap.add_argument("--tag", default="round")
ap.add_argument("--require-pass-snapshot", default=None)
ap.add_argument("--dry-run", action="store_true")
ns = ap.parse_args()

rows = materialize.load_round(Path(ns.round_ledger))
snap_arg = Path(ns.require_pass_snapshot) if ns.require_pass_snapshot else None
r = materialize.materialize_round(store_root=Path(ns.store), rows=rows, tag=ns.tag,
                                  dry_run=ns.dry_run, require_pass_snapshot=snap_arg)
print(json.dumps(r, ensure_ascii=False, indent=1))
sys.exit(0 if r.get("物料化", 0) > 0 or r.get("dry_run") else 1)
