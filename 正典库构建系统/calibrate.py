# -*- coding: utf-8 -*-
"""calibrate.py — 批次 2·V4 彩排校准夹具（R-030 仪器）。

对「新书前三章已抽取候选」按 config.types 做校准报告：
  - library 覆盖率：候选 library 落在声明桶内的比例 + 越界清单
  - canonical.entity_type 值分布（R-030：断言位可变性=语料实证属性，值供人审标定）
  - 置信度分布（低置信计数）
  - mutable_fields 使用率
报告供人审；**人审标定后的值才写入 config.types**（加载器不判值）。
"""
import argparse
import json
import statistics
from collections import Counter
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "cbb-v2"))
from cbb2 import extraction  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--config", default="extraction.config.json")
ap.add_argument("--candidates", required=True, help="候选文件 glob（如 'D:/.../extraction-ch000*.json'）")
ap.add_argument("--out", default=None)
ns = ap.parse_args()

cfg = extraction.load_config(ns.config)
declared = set(cfg.types.get("libraries") or [])
mutable = set(cfg.types.get("mutable_fields") or [])

cands = []
has_glob = any(ch in ns.candidates for ch in "*?[")
_pat = Path(ns.candidates)
files = sorted(_pat.parent.glob(_pat.name)) if has_glob else [_pat]
if not files and has_glob:
    raise SystemExit(f"glob 无匹配: {ns.candidates}")
for f in files:
    d = json.loads(f.read_text(encoding="utf-8"))
    for c in d.get("candidates") or []:
        cands.append(dict(c, _chapter=d.get("_meta", {}).get("source", {}).get("chapter")))

lib_counter = Counter(c.get("library") or "?" for c in cands)
unknown = {k: v for k, v in lib_counter.items() if declared and k not in declared}
covered = sum(v for k, v in lib_counter.items() if not declared or k in declared)
coverage = covered / len(cands) if cands else 0.0

etype = Counter()
mutable_usage = Counter()
confs = []
for c in cands:
    canon = c.get("canonical") or {}
    if isinstance(canon, dict):
        et = canon.get("entity_type")
        if et:
            etype[et] += 1
        for mf in mutable:
            if mf in canon:
                mutable_usage[mf] += 1
    if c.get("confidence") is not None:
        confs.append(float(c["confidence"]))

per_ch = Counter(c.get("_chapter") for c in cands)
report = {
    "book": cfg.book,
    "chapters": dict(per_ch),
    "候选数": len(cands),
    "library 覆盖率": f"{covered}/{len(cands)} = {coverage:.2f}",
    "library 分布": dict(lib_counter),
    "越界 library": unknown or "无",
    "canonical.entity_type 值分布（R-030 人审标定输入）": dict(etype),
    "mutable_fields 使用": dict(mutable_usage) if mutable else "config 未声明 mutable_fields",
    "置信度": ({"min": min(confs), "中位": statistics.median(confs),
               "低置信(<70)": sum(1 for x in confs if x < 70)} if confs else "无数据"),
    "判读建议": ("覆盖率 1.00 且越界为空 ⇒ 类型桶无需扩；entity_type 值分布交人审标定后写入 config.types"
             if coverage == 1.0 and not unknown else
             f"越界 library {unknown} ⇒ 类型桶需扩或候选需修"),
}
out = Path(ns.out) if ns.out else cfg.work_dir / "彩排校准报告.json"
out.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=1))
print("报告:", out)
