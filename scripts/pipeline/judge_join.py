# -*- coding: utf-8 -*-
"""judge_join.py — 判卷产线·严格双票合票+植株捕获门（通用 runner，U2）。

用法：py -X utf8 judge_join.py [--tag round] [--glm-dir 子目录] [--ds 文件名]
GLM 票=workdir/glm_chunks/chunk_*.jsonl；DS 票=workdir/ds_votes.jsonl（可覆盖）。
判词 append workdir/judging_ledger.jsonl；摘要 workdir/摘要-{tag}.json。
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cbb2 import judging  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--config", default="judging.config.json")
ap.add_argument("--tag", default="round")
ap.add_argument("--glm-dir", default=None)
ap.add_argument("--ds", default=None)
ns = ap.parse_args()

cfg = judging.load_config(ns.config)
glm_dir = cfg.work_dir / ns.glm_dir if ns.glm_dir else None
ds_file = cfg.work_dir / ns.ds if ns.ds else None
s = judging.join_strict(cfg, glm_dir=glm_dir, ds_file=ds_file, tag=ns.tag)
print(json.dumps(s, ensure_ascii=False, indent=1))
sys.exit(0 if s["捕获门"] == "PASS" else 1)
