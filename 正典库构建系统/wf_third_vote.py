# -*- coding: utf-8 -*-
"""wf_third_vote.py — 第三考官腿（ModelScope API-Inference，当前=StepFun Step-3.7-Flash）。

与 promote.judge_isolated 同构：JUDGE_PROMPT 同源、双序评审、一致采纳否则 unsure。
key 从 env MODELSCOPE_SDK_TOKEN 读（D-004：不落盘、不进 argv）；base/model 走 argv。
幂等：已有效出票的 record_id 跳过（可断点重跑）。空输出重试一次（思考 token
吃满 max_tokens 防线，放量 max_tokens 提至 4096）。逐行追加 third_votes.jsonl。
"""
import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "cbb-v2"))
from cbb2 import ops, promote  # noqa: E402

i_from = int(sys.argv[sys.argv.index("--from") + 1])
i_to = int(sys.argv[sys.argv.index("--to") + 1])
model = sys.argv[sys.argv.index("--model") + 1]
base = sys.argv[sys.argv.index("--base") + 1] if "--base" in sys.argv else "https://api-inference.modelscope.cn/v1"

# key 优先级：槽位 key（env→注册表）> 平台默认（MODELSCOPE）——dwfrun-62698cc8 实证：
# host env 里残留的 MODELSCOPE_TOKEN 会抢先命中被发给阶跃官方 → 401 烧票，槽位必须最先。
key = (os.environ.get("EXAMINER_THIRD_API_KEY")
       or ops.secret_from_registry("EXAMINER_THIRD_API_KEY")
       or os.environ.get("MODELSCOPE_SDK_TOKEN")
       or ops.secret_from_registry("MODELSCOPE_SDK_TOKEN") or "")
if not key:
    print("BLOCKED：MODELSCOPE_SDK_TOKEN / EXAMINER_THIRD_API_KEY 均未设置（env 与注册表）", flush=True)
    sys.exit(2)
# 官方付费端点免免费档 pacing（1.2s 双序间隔 / 2.5s 件间隔是 ModelScope 15 RPM 时代的产物）
PAID = "modelscope" not in base

outdir = ROOT / "迷深实战-本体库" / "试车-工作流"
manifest = [json.loads(l) for l in (outdir / "manifest.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
items = manifest[i_from:i_to]

# 分片独立输出（P-028 防线——并发切片共写一个文件会撕裂）；done-set 容错读全部历史
outf = outdir / f"third_votes_{i_from}_{i_to}.jsonl"
done = set()
for tf in [outdir / "third_votes.jsonl"] + list(outdir.glob("third_votes_*.jsonl")):
    if tf.exists():
        for l in tf.read_text(encoding="utf-8").splitlines():
            s = l.strip()
            if not s:
                continue
            try:
                r = json.loads(s)
            except Exception:
                continue
            if r.get("third_vote") in ("support", "against", "unsure"):
                done.add(r["record_id"])


def parse(raw):
    m = re.search(r"\{[^}]*\}", raw, re.DOTALL)
    if not m:
        raise ValueError(f"考官输出非 JSON：{raw[:60]!r}")
    v = json.loads(m.group(0)).get("verdict")
    if v not in ("support", "against", "unsure"):
        raise ValueError(f"考官判定非法：{v!r}")
    return v


def ask_once(prompt, mdl):
    raw = ops.chat_once(base, mdl, key, prompt, timeout=90.0, max_tokens=mt)
    if not raw.strip():  # 空输出重试一次（Step 3.7 思考 token 吃满时 content 为空）
        raw = ops.chat_once(base, mdl, key, prompt, timeout=90.0, max_tokens=mt)
    return raw


def ask_rl(prompt, mdl):
    """429 感知退避：免费档限流是常态而非异常，退避重试直到通过或耗尽。"""
    delay = 15.0
    for attempt in range(6):
        try:
            return ask_once(prompt, mdl)
        except Exception as e:  # noqa: BLE001 — 仅 429 族退避，其余原样抛出
            if "429" in str(e) and attempt < 5:
                time.sleep(delay)
                delay = min(delay * 2, 60.0)
                continue
            raise
    raise RuntimeError("429 退避重试耗尽")


mt = int(os.environ.get("EXAMINER_MAX_TOKENS") or 4096)
ok = fail = 0
for it in items:
    if it["record_id"] in done:
        print(f"third {it['record_id']} 已有有效票，跳过", flush=True)
        continue
    payload = json.loads((ROOT / "迷深实战-本体库" / it["file"]).read_text(encoding="utf-8"))
    p_ev = f"{promote.JUDGE_PROMPT}\n【证据摘录】{payload['evidence']}\n【记录断言】{payload['conclusion']}"
    p_co = f"{promote.JUDGE_PROMPT}\n【记录断言】{payload['conclusion']}\n【证据摘录】{payload['evidence']}"
    va = vb = None
    err = None
    try:
        va = parse(ask_rl(p_ev, model))
        if not PAID:
            time.sleep(1.2)
        vb = parse(ask_rl(p_co, model))
        vote = va if va == vb else "unsure"
        ok += 1
    except Exception as e:  # noqa: BLE001 — 单件异常计数不拖批
        vote = None
        err = str(e)[:120]
        fail += 1
    row = {"record_id": it["record_id"], "third_vote": vote, "a": va, "b": vb, "model": model, "err": err}
    with outf.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
        f.flush()
    print(f"third {it['record_id']} -> {vote} ({err or 'ok'})", flush=True)
    if not PAID:
        time.sleep(2.5)
print(f"THIRD batch [{i_from}:{i_to}] done: ok={ok} fail={fail} model={model}")
