# -*- coding: utf-8 -*-
"""g17_circle.py — 批次 7·B1 G17 巡检圈一键编排（队列→执行→CUSUM 读数）。

用法：py -X utf8 g17_circle.py --seed 20260930 --unit G17-二圈
流程：①g17_patrol_queue（新种子出新样本，种子入档可复算）
      ②g17_patrol_execute（锚定重推导+Erlangshen NLI 复核，本地免费）
      ③CUSUM 上偏累计：改判率相对首圈基线 p0，h=0.05，k=0.002
产出：二圈报告 + G17-CUSUM序列.json（逐圈追加，生命周期条款 3 圈无告警降频）。
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from cbb2 import cusum  # noqa: E402

STORE = HERE / "迷深实战-本体库"
SERIES = STORE / "G17-CUSUM序列.json"

ap = argparse.ArgumentParser()
ap.add_argument("--seed", type=int, required=True, help="本圈抽样种子（入档可复算）")
ap.add_argument("--unit", default="G17-二圈")
ap.add_argument("--p0", type=float, default=None, help="基线改判率（缺省读首圈报告）")
ns = ap.parse_args()

p0 = ns.p0
if p0 is None:
    first = STORE / "G17-首圈巡检报告.json"
    if first.exists():
        p0 = json.loads(first.read_text(encoding="utf-8")).get("CUSUM基线", {}).get("p0")
    if not p0:
        print("BLOCKED：首圈报告无 p0 基线，且未传 --p0")
        sys.exit(2)

queue_out = STORE / f"G17-{ns.unit}-队列.json"
report_out = STORE / f"G17-{ns.unit}-巡检报告.json"

print(f"[1/3] 队列生成（seed={ns.seed}）", flush=True)
r = subprocess.run([sys.executable, "-X", "utf8", str(HERE / "g17_patrol_queue.py"),
                    "--seed", str(ns.seed), "--out", str(queue_out)],
                   capture_output=True, text=True)
print(r.stdout.strip() or r.stderr.strip()[-200:], flush=True)
if r.returncode != 0:
    sys.exit(r.returncode)

print(f"[2/3] 巡检执行（{ns.unit}）", flush=True)
r = subprocess.run([sys.executable, "-X", "utf8", str(HERE / "g17_patrol_execute.py"),
                    "--queue", str(queue_out), "--out", str(report_out), "--unit", ns.unit],
                   capture_output=True, text=True, timeout=3600)
print((r.stdout.strip()[-300:] or r.stderr.strip()[-200:]), flush=True)
if r.returncode != 0:
    sys.exit(r.returncode)

print("[3/3] CUSUM 读数", flush=True)
report = json.loads(report_out.read_text(encoding="utf-8"))
n_nli = int(report.get("CUSUM基线", {}).get("n") or 0)
contrad = int(report.get("CUSUM基线", {}).get("contrad_cnt") or 0)
rate = contrad / n_nli if n_nli else 0.0
读 = cusum.feed_circle(rate=rate, p0=p0, k=0.002, h=0.05)
series_file = STORE / "G17-CUSUM序列.json"
series_doc = json.loads(series_file.read_text(encoding="utf-8")) if series_file.exists() else {
    "p0 基线": p0, "k 松弛": 0.002, "h 告警阈": 0.05, "圈读数": []}
series_doc["圈读数"].append({"unit": ns.unit, "改判率": round(rate, 4),
                             "累计偏移": 读["累计偏移"], "告警": 读["告警"],
                             "at": time.strftime("%Y-%m-%dT%H:%M:%S")})
series_file.write_text(json.dumps(series_doc, ensure_ascii=False, indent=1), encoding="utf-8")
peak = max((c["累计偏移"] for c in series_doc["圈读数"]), default=0.0)
print(json.dumps({"unit": ns.unit, "改判率": round(rate, 4), "累计偏移": 读["累计偏移"],
                  "告警": 读["告警"], "序列峰值": round(peak, 4), "h": 0.05}, ensure_ascii=False))
sys.exit(0 if not 读["告警"] else 1)
