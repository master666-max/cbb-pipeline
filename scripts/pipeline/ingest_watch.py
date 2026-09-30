# -*- coding: utf-8 -*-
"""ingest_watch.py — 批次 7·B2 增量摄入调度化（watchdog 轮询，stdlib 零依赖）。

监控语料文件 mtime：变化 ⇒ 提示增量并（--auto 时）自动触发 ingest.py。
模式：
  --once   单次检查（配 Windows 计划任务/手动）
  默认     常驻轮询（--interval 秒）
安全：默认只 dry-run 提示；--auto 才真跑全量摄入（增量摄入会写库）。
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from cbb2 import extraction  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--config", default="extraction.config.json")
ap.add_argument("--state", default=None, help="watchdog 状态文件（记上次 mtime）")
ap.add_argument("--interval", type=int, default=300, help="轮询间隔秒（默认 300）")
ap.add_argument("--once", action="store_true", help="单次检查后退出（配计划任务）")
ap.add_argument("--auto", action="store_true", help="检出增量后自动实跑摄入（默认只提示）")
ns = ap.parse_args()

cfg = extraction.load_config(ns.config)
state_file = Path(ns.state) if ns.state else cfg.work_dir / "watch-state.json"


def corpus_mtime() -> float:
    return cfg.corpus.stat().st_mtime


def check() -> dict:
    last = 0.0
    if state_file.exists():
        try:
            last = float(json.loads(state_file.read_text(encoding="utf-8")).get("mtime", 0))
        except Exception:
            last = 0.0
    cur = corpus_mtime()
    changed = cur > last
    return {"last_mtime": last, "cur_mtime": cur, "语料有更新": changed}


if ns.once:
    r = check()
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps({"mtime": r["cur_mtime"]}, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(r, ensure_ascii=False))
    sys.exit(0)

print(f"watchdog 启动：监控 {cfg.corpus}（interval={ns.interval}s，auto={ns.auto}）", flush=True)
while True:
    r = check()
    if r["语料有更新"]:
        print(f"[{time.strftime('%H:%M:%S')}] 语料有更新 → 触发增量摄入"
              f"{'（--auto 实跑）' if ns.auto else '（提示模式）'}", flush=True)
        cmd = [sys.executable, "-X", "utf8", str(HERE / "ingest.py"), "--config", ns.config]
        if not ns.auto:
            cmd.append("--dry-run")
        subprocess.run(cmd)
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(json.dumps({"mtime": corpus_mtime()}, ensure_ascii=False), encoding="utf-8")
    time.sleep(ns.interval)
