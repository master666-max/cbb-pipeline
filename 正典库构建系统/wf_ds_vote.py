# -*- coding: utf-8 -*-
"""wf_ds_vote.py — DeepSeek 官方 API 考官腿（工作流版）。

与 promote.judge_isolated 完全同构：JUDGE_PROMPT 同源（cbb2.promote）、双序评审、
一致采纳否则 unsure。base/model/key 全 env 优先（EXAMINER_DEEPSEEK_*），缺省回落
官方端点 https://api.deepseek.com + DEEPSEEK_API_KEY；模型名带降级链
（deepseek-chat → deepseek-v4-flash，官方已宣布旧名映射）。按 manifest 切片
[--from, --to) 判卷，逐行追加 ds_votes.jsonl。
"""
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "cbb-v2"))
from cbb2 import ops, promote  # noqa: E402

i_from = int(sys.argv[sys.argv.index("--from") + 1])
i_to = int(sys.argv[sys.argv.index("--to") + 1])

outdir = ROOT / "迷深实战-本体库" / "试车-工作流"
manifest = [json.loads(l) for l in (outdir / "manifest.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
items = manifest[i_from:i_to]

base = os.environ.get("EXAMINER_DEEPSEEK_BASE") or "https://api.deepseek.com"
key = (os.environ.get("EXAMINER_DEEPSEEK_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
       or ops.secret_from_registry("DEEPSEEK_API_KEY") or "")
models = [m for m in [os.environ.get("EXAMINER_DEEPSEEK_MODEL") or "", "deepseek-chat", "deepseek-v4-flash"] if m]
mt = int(os.environ.get("EXAMINER_MAX_TOKENS") or 4096)
# 分片独立输出文件：多批次并发时不再共写一个文件（撕裂防线）；兼容读取旧 ds_votes.jsonl
outf = outdir / f"ds_votes_{i_from}_{i_to}.jsonl"
done = set()
for df in [outdir / "ds_votes.jsonl"] + list(outdir.glob("ds_votes_*.jsonl")):
    if df.exists():
        for l in df.read_text(encoding="utf-8").splitlines():
            if l.strip():
                try:
                    r = json.loads(l)
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


model_ok = None
for it in items:
    if it["record_id"] in done:
        print(f"ds {it['record_id']} 已有有效票，跳过", flush=True)
        continue
    payload = json.loads((ROOT / "迷深实战-本体库" / it["file"]).read_text(encoding="utf-8"))
    p_ev = f"{promote.JUDGE_PROMPT}\n【证据摘录】{payload['evidence']}\n【记录断言】{payload['conclusion']}"
    p_co = f"{promote.JUDGE_PROMPT}\n【记录断言】{payload['conclusion']}\n【证据摘录】{payload['evidence']}"
    va = vb = None
    err = None
    try:
        for mdl in ([model_ok] if model_ok else models):
            try:
                va = parse(ops.chat_once(base, mdl, key, p_ev, timeout=120.0, max_tokens=mt))
                vb = parse(ops.chat_once(base, mdl, key, p_co, timeout=120.0, max_tokens=mt))
                model_ok = mdl
                break
            except Exception as e:  # noqa: BLE001 — 模型名/网络逐个降级，model_ok 后不再降
                if model_ok:
                    raise
                va = vb = None
                err = str(e)[:120]
        vote = va if (va is not None and va == vb) else "unsure"
        if va is None:
            vote = None
        row = {"record_id": it["record_id"], "ds_vote": vote, "a": va, "b": vb,
               "model": model_ok, "err": err}
    except Exception as e:  # noqa: BLE001 — 单件异常计数不拖批
        row = {"record_id": it["record_id"], "ds_vote": None, "a": va, "b": vb,
               "model": model_ok, "err": str(e)[:120]}
    with outf.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
        f.flush()
    print(f"ds [{i_from}:{i_to}] {it['record_id']} -> {row['ds_vote']} ({row['err'] or 'ok'})", flush=True)
print(f"DS batch [{i_from}:{i_to}] done, model={model_ok}")
