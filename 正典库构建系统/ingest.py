# -*- coding: utf-8 -*-
"""ingest.py — 批次 4·增量摄入编排器。

新增章=自动摄入（逐章驱动 run_chapter 完整管线，串行纪律）；变更章=转人工（变更清单）；
done-set=ingest-state.json（逐章原子更新，断点续跑幂等）。
用法：py -X utf8 ingest.py --config extraction.config.json [--limit N] [--dry-run]
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "cbb-v2"))
from cbb2 import extraction  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--config", default="extraction.config.json")
ap.add_argument("--state", default=None, help="默认 工作目录/ingest-state.json")
ap.add_argument("--limit", type=int, default=0, help="本轮最多摄入章数（0=不限）")
ap.add_argument("--dry-run", action="store_true")
ns = ap.parse_args()

cfg = extraction.load_config(ns.config)
state_file = Path(ns.state) if ns.state else cfg.work_dir / "ingest-state.json"
state = json.loads(state_file.read_text(encoding="utf-8")) if state_file.exists() else {}

diff = extraction.ingest_diff(cfg, state)
new = sorted(diff["new"], key=lambda x: x["chapter_no"])
changed = diff["changed"]
to_run = new[: ns.limit if ns.limit > 0 else len(new)]
print(json.dumps({"新增": len(new), "变更(转人工)": len(changed), "本轮摄入": len(to_run)},
                 ensure_ascii=False))

if changed:
    chg_file = cfg.work_dir / f"变更章清单-{time.strftime('%Y%m%d')}.json"
    chg_file.write_text(json.dumps(changed, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"变更章 {len(changed)} 件 → {chg_file.name}（转人工窗，不自动重抽）", flush=True)

if not to_run:
    print("无新增章可摄入。")
    sys.exit(0)

if ns.dry_run:
    for ch in to_run:
        print(f"[dry] ch{ch['chapter_no']:04d} {ch['title'][:30]}")
    sys.exit(0)

runner = HERE / "迷深实战-工作区" / "runners" / "run_chapter.py"
ok = fail = 0
for ch in to_run:
    no = ch["chapter_no"]
    r = subprocess.run([sys.executable, "-X", "utf8", str(runner), "--chapter", str(no)],
                       capture_output=True, text=True, timeout=7200)
    if r.returncode == 0:
        state[str(no)] = {"sha": ch["sha"], "ingested_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
        state_file.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
        ok += 1
        print(f"✓ ch{no:04d} 摄入完成（{ok}/{len(to_run)}）", flush=True)
    else:
        fail += 1
        print(f"✗ ch{no:04d} 失败：{r.stderr[-200:]}", flush=True)
print(json.dumps({"摄入完成": ok, "失败": fail, "剩余": len(to_run) - ok}, ensure_ascii=False))
sys.exit(0 if fail == 0 else 1)
