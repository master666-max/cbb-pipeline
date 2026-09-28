# -*- coding: utf-8 -*-
"""wf_manifest_repair.py — 放量 manifest 中途修复（2026-09-29，P1-a/P1-b 整改）。

背景：放量判卷（dwfrun-e8af9c9b）半程中断，审计发现两缺陷——
  P1-a 掺株堆尾：8 株全部位于 manifest 末尾 idx 2184-2191，违反 B5 实证的穿插纪律
        （堆末尾=对已判卷段零监控力）；
  P1-b 期望泄漏：manifest 行携带 is_plant/expected，而 GLM 腿按 dwf 指示 Read 原始行
        ——期望答案对考官可见，植株考试盲性破缺（图05"考官不可见"仅 payload 层成立）。

修复（前缀保全式中途重排）：
  - 前 940 行（idx 0-939，对应已收线 chunk_000-091,093 的行区间）记录与顺序不变；
  - 第 941 行起 = 其余正件 + 8 株，random.Random(20260929) 统一洗牌穿插；
  - 全卷剥离 is_plant/expected 出判卷面，特权映射写 manifest_priv.jsonl（join/stats 专用）；
  - 旧 manifest 先归档进 试点轮存档/，不删不覆盖历史（铁律）。

幂等：manifest_priv.jsonl 已存在即拒绝（已修复过）；--dry-run 只验证不落盘。
"""
import json
import random
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
outdir = ROOT / "迷深实战-本体库" / "试车-工作流"
ARCH = outdir / "试点轮存档"
SEED = 20260929

dry = "--dry-run" in sys.argv

mf = outdir / "manifest.jsonl"
priv = outdir / "manifest_priv.jsonl"
if priv.exists():
    # 幂等重入（AmendWorkflow 续跑可能再次经过本相位）：校验一致后按已修复放行
    rows = [json.loads(l) for l in mf.read_text(encoding="utf-8").splitlines() if l.strip()]
    pr = [json.loads(l) for l in priv.read_text(encoding="utf-8").splitlines() if l.strip()]
    ok = (len(rows) == len(pr) == 2192
          and sum(1 for r in pr if r["is_plant"]) == 8
          and not ({"is_plant", "expected"} & set(rows[0].keys())))
    print(json.dumps({"mode": "already-repaired", "consistent": ok}, ensure_ascii=False))
    sys.exit(0 if ok else 3)

old = [json.loads(l) for l in mf.read_text(encoding="utf-8").splitlines() if l.strip()]
n = len(old)
plants_old = [(i, r["record_id"]) for i, r in enumerate(old) if r.get("is_plant")]
assert n == 2192, f"manifest 行数 {n} != 2192，与审计基准不符，拒绝执行"
assert len(plants_old) == 8, f"植株数 {len(plants_old)} != 8"

# 动态保全边界：已收线 chunk 行覆盖上界（缺号 chunk 落在前缀内时续跑会对同序行重问，无碍）
chunk_ids = [int(p.stem.split("_")[1]) for p in (outdir / "glm_chunks").glob("chunk_*.jsonl")]
max_chunk = max(chunk_ids) if chunk_ids else -1
BOUNDARY = min((max_chunk + 1) * 10, n - 8)

prefix = old[:BOUNDARY]
assert not any(r.get("is_plant") for r in prefix), "保全前缀内发现植株，与审计基准不符"
tail_real = [{k: r[k] for k in ("record_id", "file")} for r in old[BOUNDARY:] if not r.get("is_plant")]
tail_plants = [{k: r[k] for k in ("record_id", "file")} | {"is_plant": True, "expected": r.get("expected")}
               for r in old[BOUNDARY:] if r.get("is_plant")]
assert len(tail_plants) == 8, "植株不在尾段，与审计基准不符"

merged = tail_real + tail_plants
random.Random(SEED).shuffle(merged)

new_rows, priv_rows = [], []
for pos, r in enumerate(prefix):
    new_rows.append({"idx": pos, "record_id": r["record_id"], "file": r["file"]})
    priv_rows.append({"idx": pos, "record_id": r["record_id"], "is_plant": False, "expected": None})
for j, r in enumerate(merged):
    idx = BOUNDARY + j
    new_rows.append({"idx": idx, "record_id": r["record_id"], "file": r["file"]})
    priv_rows.append({"idx": idx, "record_id": r["record_id"],
                      "is_plant": bool(r.get("is_plant")), "expected": r.get("expected")})

# ---- 验证（dry-run 与实跑同口径）----
assert len(new_rows) == n and len(priv_rows) == n
assert [r["record_id"] for r in new_rows[:BOUNDARY]] == [r["record_id"] for r in prefix], "前缀被改动"
assert sorted(r["record_id"] for r in new_rows) == sorted(r["record_id"] for r in old), "全集不等"
assert len({r["record_id"] for r in new_rows}) == n, "record_id 有重复"
clean_keys = set(new_rows[0].keys())
assert not ({"is_plant", "expected"} & clean_keys), "判卷面仍带特权字段"
plants_new = [(r["idx"], r["record_id"]) for r in priv_rows if r["is_plant"]]
assert len(plants_new) == 8 and all(i >= BOUNDARY for i, _ in plants_new), "植株穿插区间错误"
missing_payload = [r["file"] for r in new_rows if not (ROOT / "迷深实战-本体库" / r["file"]).exists()]
assert not missing_payload, f"payload 缺失 {len(missing_payload)} 件"

print(json.dumps({
    "mode": "dry-run" if dry else "apply",
    "保全前缀": f"0..{BOUNDARY - 1}",
    "重排区间": f"{BOUNDARY}..{n - 1}（正件 {len(tail_real)} + 株 {len(tail_plants)}，seed={SEED}）",
    "植株新位置": plants_new,
    "判卷面键": sorted(clean_keys),
}, ensure_ascii=False, indent=1))

if dry:
    print("DRY-RUN 通过，未落盘。")
    sys.exit(0)

ts = time.strftime("%H%M%S")
ARCH.mkdir(exist_ok=True)
shutil.copy2(mf, ARCH / f"manifest.jsonl.{ts}-放量中断修复前")
mf.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in new_rows), encoding="utf-8")
priv.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in priv_rows), encoding="utf-8")
print(f"APPLIED：manifest.jsonl 重排+剥敏完成，旧件归档 试点轮存档/manifest.jsonl.{ts}-放量中断修复前；"
      f"特权映射 → manifest_priv.jsonl（{len(priv_rows)} 行）")
