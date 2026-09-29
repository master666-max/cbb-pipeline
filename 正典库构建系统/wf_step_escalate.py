# -*- coding: utf-8 -*-
"""wf_step_escalate.py — v1.11 升级分歧带 THIRD 补票件（阶跃官方，节奏化）。

输入：试车-工作流/升级分歧带-r2.jsonl（wf_join_dual.py --export 产出）。
只补 THIRD 缺席件（done-set=全部历史有效 third 票，银行票直接跳过）。
节奏化：v1.10 实证六进程无 pacing 冲击重置后低 RPM → 429 退避耗尽烧出 1,444 缺席；
本件单进程 + 0.4s 双序间隔 / 0.8s 件间隔 + 429 感知退避（15→60s）。
输出追加 third_votes_escalate.jsonl（P-028：独立文件不与他写共笔）。
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

BASE = "https://token-plan-cn.xiaomimimo.com/v1"
MODEL = "mimo-v2.6-flash"
MT = int(os.environ.get("EXAMINER_MAX_TOKENS") or 2048)
# v1.12：升级票考官换编 MiMo-v2.6-flash——上岗考试 8/8 满分（正株4/4 support、负株4/4 unsure），
# 非思考型输出几十 token/判（Step-3.7-Flash 思考型 4096 输出价计费致 402 超限，退役存档）。
KEY = (ops.secret_from_registry("EXAMINER_MIMO_TP_KEY")
       or ops.secret_from_registry("EXAMINER_MIMO_API_KEY")
       or ops.secret_from_registry("EXAMINER_THIRD_API_KEY"))
if not KEY:
    print("BLOCKED：EXAMINER_THIRD_API_KEY 未注入（注册表）", flush=True)
    sys.exit(2)

outdir = ROOT / "迷深实战-本体库" / "试车-工作流"
manifest = {json.loads(l)["record_id"]: json.loads(l)["file"]
            for l in (outdir / "manifest.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}
esc = [json.loads(l) for l in (outdir / "升级分歧带-r2.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]

done = set()
for df in sorted(outdir.glob("third_votes*.jsonl")):
    for l in df.read_text(encoding="utf-8").splitlines():
        s = l.strip()
        if not s:
            continue
        try:
            r = json.loads(s)
        except Exception:
            continue
        if r.get("third_vote") in ("support", "against", "unsure"):
            done.add(r["record_id"])

todo = [r["record_id"] for r in esc if r["record_id"] not in done]
print(f"升级带 {len(esc)} 件，银行票 {len(esc) - len(todo)}，需补 {len(todo)}", flush=True)


def parse(raw):
    m = re.search(r"\{[^}]*\}", raw, re.DOTALL)
    if not m:
        raise ValueError(f"考官输出非 JSON：{raw[:60]!r}")
    v = json.loads(m.group(0)).get("verdict")
    if v not in ("support", "against", "unsure"):
        raise ValueError(f"考官判定非法：{v!r}")
    return v


def ask_rl(prompt):
    delay = 15.0
    for attempt in range(6):
        raw = ops.chat_once(BASE, MODEL, KEY, prompt, timeout=90.0, max_tokens=MT)
        if not raw.strip():
            raw = ops.chat_once(BASE, MODEL, KEY, prompt, timeout=90.0, max_tokens=MT)
        try:
            return parse(raw)
        except Exception as e:  # noqa: BLE001 — 仅 429 族退避，其余原样抛出
            if "429" in str(e) and attempt < 5:
                time.sleep(delay)
                delay = min(delay * 2, 60.0)
                continue
            raise
    raise RuntimeError("429 退避重试耗尽")


outf = outdir / "third_votes_escalate.jsonl"
ok = fail = 0
for rid in todo:
    payload = json.loads((ROOT / "迷深实战-本体库" / manifest[rid]).read_text(encoding="utf-8"))
    p_ev = f"{promote.JUDGE_PROMPT}\n【证据摘录】{payload['evidence']}\n【记录断言】{payload['conclusion']}"
    p_co = f"{promote.JUDGE_PROMPT}\n【记录断言】{payload['conclusion']}\n【证据摘录】{payload['evidence']}"
    va = vb = None
    err = None
    try:
        va = parse(ops.chat_once(BASE, MODEL, KEY, p_ev, timeout=90.0, max_tokens=MT))
        time.sleep(0.4)
        vb = parse(ops.chat_once(BASE, MODEL, KEY, p_co, timeout=90.0, max_tokens=MT))
        vote = va if va == vb else "unsure"
        ok += 1
    except Exception as e:  # noqa: BLE001 — 单件异常计数不拖批
        vote, err, fail = None, str(e)[:120], fail + 1
    with outf.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"record_id": rid, "third_vote": vote, "a": va, "b": vb,
                            "model": MODEL, "err": err}, ensure_ascii=False) + "\n")
        f.flush()
    print(f"escalate {rid} -> {vote} ({err or 'ok'})", flush=True)
    time.sleep(0.8)
print(f"ESCALATE done: ok={ok} fail={fail}", flush=True)
