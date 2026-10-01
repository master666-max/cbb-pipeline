# -*- coding: utf-8 -*-
"""ingest_watch.py — 批次 7·B2 增量摄入调度化（watchdog 轮询，stdlib 零依赖）。

监控语料文件 mtime：变化 ⇒ 提示增量并（--auto 时）自动触发摄入脚本。
模式：
  --once   单次检查（配 Windows 计划任务/手动）
  默认     常驻轮询（--interval 秒）
安全：默认只 dry-run 提示；--auto 才真跑全量摄入（增量摄入会写库）。
**watch 状态只许在摄入实跑成功（rc=0）后推进**——2026-10-01 审计修正：
原实现不管子进程成败（甚至脚本不存在 rc=2）都把 mtime 记为已消费，
语料每次更新都会被标记"已处理"而摄入从未发生 ⇒ 增量内容永久静默丢失。
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
ap.add_argument("--ingest", default=None,
                help="摄入脚本路径（缺省 HERE/ingest.py；本仓未随附 ingest.py，"
                     "增量迁移期请用本参数指到真实摄入入口）")
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
    if r["语料有更新"]:
        r["口径"] = "本次只记录 mtime，未触发摄入——增量若还没实跑过，请先手动摄入再挂 watch"
    print(json.dumps(r, ensure_ascii=False))
    sys.exit(0)

ingest_script = Path(ns.ingest) if ns.ingest else HERE / "ingest.py"
print(f"watchdog 启动：监控 {cfg.corpus}（interval={ns.interval}s，auto={ns.auto}，ingest={ingest_script}）", flush=True)
while True:
    r = check()
    if r["语料有更新"]:
        if not ns.auto:
            # 提示模式不推进状态：增量保持未消费，提醒每轮复现，直到有人实跑摄入
            print(f"[{time.strftime('%H:%M:%S')}] 语料有更新（提示模式，不推进 watch 状态）——"
                  f"请实跑摄入（--auto 或手动）", flush=True)
        else:
            cmd = [sys.executable, "-X", "utf8", str(ingest_script), "--config", ns.config]
            pr = None
            try:
                pr = subprocess.run(cmd, capture_output=True, text=True,
                                    encoding="utf-8", errors="replace")
            except FileNotFoundError:
                print(f"[{time.strftime('%H:%M:%S')}] FATAL：摄入脚本不存在：{ingest_script}"
                      f"（用 --ingest 指到真实入口）；不推进 watch 状态", flush=True)
            if pr is not None:
                if pr.returncode == 0:
                    state_file.parent.mkdir(parents=True, exist_ok=True)
                    state_file.write_text(json.dumps({"mtime": corpus_mtime()}, ensure_ascii=False),
                                          encoding="utf-8")
                    print(f"[{time.strftime('%H:%M:%S')}] 摄入成功，watch 状态已推进", flush=True)
                else:
                    # 失败不推进 state：下轮重试；真实 stderr 带回，不许伪装成"已处理"
                    tail = (pr.stderr or "").strip()[-400:]
                    print(f"[{time.strftime('%H:%M:%S')}] 摄入失败 rc={pr.returncode}，"
                          f"不推进 watch 状态（下轮重试）\n{tail}", flush=True)
    time.sleep(ns.interval)
