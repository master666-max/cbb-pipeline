# -*- coding: utf-8 -*-
"""judge_ds.py — 判卷产线·DEEPSEEK 考官腿（通用 runner，U2）。

读 config 的 DS 编制（base/model/key 链）与契约文本，对工作目录 manifest 逐件双序评审。
幂等：done-set（有效票跳过）；单件异常计数不拖批；逐行 append ds_votes.jsonl。
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cbb2 import judging, ops  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--config", default="judging.config.json")
ap.add_argument("--examiner", default="DEEPSEEK")
ns = ap.parse_args()

cfg = judging.load_config(ns.config)
e = cfg.examiner(ns.examiner)
key = e.key()
if not key:
    print(f"BLOCKED：{ns.examiner} key 未解析（env/注册表）")
    sys.exit(2)

manifest, _ = judging.load_manifest(cfg.work_dir)
done = set()
outf = cfg.work_dir / "ds_votes.jsonl"
if outf.exists():
    for l in outf.read_text(encoding="utf-8").splitlines():
        s = l.strip()
        if not s:
            continue
        try:
            r = json.loads(s)
        except Exception:
            continue
        if r.get("ds_vote") in ("support", "against", "unsure"):
            done.add(r["record_id"])


def parse(raw):
    m = re.search(r"\{[^}]*\}", raw, re.DOTALL)
    if not m:
        raise ValueError(f"考官输出非 JSON：{raw[:60]!r}")
    v = json.loads(m.group(0)).get("verdict")
    if v not in ("support", "against", "unsure"):
        raise ValueError(f"考官判定非法：{v!r}")
    return v


ok = 0
for it in manifest:
    if it["record_id"] in done:
        continue
    payload = json.loads(Path(it["file"]).read_text(encoding="utf-8"))
    try:
        va = parse(ops.chat_once(e.base, e.model, key,
                                 f"{cfg.contract}\n【证据摘录】{payload['evidence']}\n【记录断言】{payload['conclusion']}",
                                 timeout=90.0, max_tokens=e.max_tokens))
        if e.paced:
            time.sleep(0.4)
        vb = parse(ops.chat_once(e.base, e.model, key,
                                 f"{cfg.contract}\n【记录断言】{payload['conclusion']}\n【证据摘录】{payload['evidence']}",
                                 timeout=90.0, max_tokens=e.max_tokens))
        vote = va if va == vb else "unsure"
        err = None
        ok += 1
    except Exception as ex:  # noqa: BLE001 — 单件异常计数不拖批
        va = vb = None
        vote = None
        err = str(ex)[:120]
    with outf.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"record_id": it["record_id"], "ds_vote": vote, "a": va, "b": vb,
                            "model": e.model, "err": err}, ensure_ascii=False) + "\n")
        f.flush()
    print(f"ds {it['record_id']} -> {vote} ({err or 'ok'})", flush=True)
print(f"judge_ds done: ok={ok}", flush=True)
