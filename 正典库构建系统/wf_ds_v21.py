# -*- coding: utf-8 -*-
"""wf_ds_v21.py — 契约 v2.1 验证轮 DS 腿（50 件双序，独立文件不与量产票共笔）。

契约 v2.1 = v2 长静态头 − 从严倾向条款 − 四判例 ＋ claim 元数据契约行。
v1.13 A/B 实证 v2 的从严诱导把 DS 支持率压掉 2/3（植株 0/8）——本验证轮测 v2.1 是否恢复校准。
判词规则不变：双序一致采纳，否则 unsure。
"""
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "cbb-v2"))
from cbb2 import ops  # noqa: E402

JUDGE_PROMPT_V21 = (
    "你是正典库独立考官。给定【证据摘录】与【记录断言】，判定证据是否支持断言。\n"
    "【记录断言】JSON 中的 claim 字段是抽取器元数据标注（true=正向，false=反推/否定性记录），"
    "不是判定对象。\n"
    "只输出 JSON：{\"verdict\":\"support|against|unsure\"}。支持=support；"
    "证据与断言不可同真=against；证据不足=unsure。禁止其他文字。"
)

BASE = "https://api.deepseek.com"
MODEL = "deepseek-chat"
KEY = ops.secret_from_registry("DEEPSEEK_API_KEY")
if not KEY:
    print("BLOCKED：DEEPSEEK_API_KEY 未注入（注册表）")
    sys.exit(2)

outdir = ROOT / "迷深实战-本体库" / "试车-工作流" / "v21验证轮"
items = [json.loads(l) for l in (outdir / "manifest.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
done = set()
outf = outdir / "ds_votes_v22.jsonl"
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
for it in items:
    if it["record_id"] in done:
        continue
    payload = json.loads((ROOT / "迷深实战-本体库" / it["file"]).read_text(encoding="utf-8"))
    p_ev = f"{JUDGE_PROMPT_V21}\n【证据摘录】{payload['evidence']}\n【记录断言】{payload['conclusion']}"
    p_co = f"{JUDGE_PROMPT_V21}\n【记录断言】{payload['conclusion']}\n【证据摘录】{payload['evidence']}"
    va = vb = None
    err = None
    try:
        va = parse(ops.chat_once(BASE, MODEL, KEY, p_ev, timeout=90.0))
        vb = parse(ops.chat_once(BASE, MODEL, KEY, p_co, timeout=90.0))
        vote = va if va == vb else "unsure"
        ok += 1
    except Exception as e:  # noqa: BLE001 — 单件异常计数不拖批
        vote, err = None, str(e)[:120]
    with outf.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"record_id": it["record_id"], "ds_vote": vote, "a": va, "b": vb,
                            "model": MODEL, "contract": "v2.2", "err": err}, ensure_ascii=False) + "\n")
        f.flush()
    print(f"ds_v21 {it['record_id']} -> {vote} ({err or 'ok'})", flush=True)
print(f"DS v2.1 验证轮 done: ok={ok}", flush=True)
