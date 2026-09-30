# -*- coding: utf-8 -*-
"""judge_exam.py — 判卷产线·植株上岗考试（通用 runner，U2）。

用法：py -X utf8 judge_exam.py --examiner THIRD --plants plants.jsonl [--config ...]
门：correct≥config.gate.correct_min ∧ capture≥5/6。零副作用。
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cbb2 import judging  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--config", default="judging.config.json")
ap.add_argument("--examiner", required=True)
ap.add_argument("--plants", required=True)
ns = ap.parse_args()

cfg = judging.load_config(ns.config)
plants = judging.load_plants_jsonl(ns.plants)
r = judging.exam(cfg, ns.examiner, plants)
print(json.dumps(r, ensure_ascii=False, indent=1))
sys.exit(0 if r["gate"] == "PASS" else 1)
