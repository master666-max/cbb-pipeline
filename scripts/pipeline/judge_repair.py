# -*- coding: utf-8 -*-
"""judge_repair.py — 判卷产线·中途修复（通用 runner，U2）。

断档/中断后：前缀保全（已收线 chunk 行覆盖上界）+ 尾段 seed 穿插重排 + 判卷面剥敏 + priv 同步。
幂等：已剥敏则校验放行。
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cbb2 import judging  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--config", default="judging.config.json")
ns = ap.parse_args()

r = judging.repair(judging.load_config(ns.config))
print(json.dumps(r, ensure_ascii=False))
sys.exit(0 if r.get("mode") in ("repaired", "already-repaired") else 3)
