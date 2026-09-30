# -*- coding: utf-8 -*-
"""judge_assemble.py — 判卷产线·组装（通用 runner，U2）。

用法：py -X utf8 judge_assemble.py [--config judging.config.json]
        --records records.jsonl（每行 {record_id,conclusion,evidence}）
        [--plants plants.jsonl]（每行 {record_id,expected[,rec|conclusion+evidence]}）
植株按 config.seed 随机穿插全卷；判卷面零特权字段（expected/is_plant → manifest_priv.jsonl）。
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cbb2 import judging  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--config", default="judging.config.json")
ap.add_argument("--records", required=True)
ap.add_argument("--plants", default=None)
ns = ap.parse_args()

cfg = judging.load_config(ns.config)
records = judging.load_records_jsonl(ns.records)
plants = judging.load_plants_jsonl(ns.plants) if ns.plants else []
r = judging.assemble(cfg, records, plants)
print(json.dumps(r, ensure_ascii=False))
