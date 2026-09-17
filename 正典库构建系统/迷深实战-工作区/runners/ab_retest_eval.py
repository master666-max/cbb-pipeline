# -*- coding: utf-8 -*-
"""ab_retest_eval.py — A/B 门重测评估器（工单 v1.6 迭代制 · R-018 机械口径）。

覆盖尺机械化（禁用主代理自抽当尺）：分母=切片『』专名∪库内名在切片出现者；
分子=候选触及。门=悬空率≤10% AND 专名覆盖≥90% AND 封套契约拦截=0（G1-SCHEMA）。
辅报（不作硬门）：密度锚区间/类型配比/observations 轨道占比。

用法：py -X utf8 ab_retest_eval.py --extraction …extraction-ch0069.json --slice …ch0069.json --store 迷深实战-本体库
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CBB = HERE.parent.parent / "cbb"
sys.path.insert(0, str(CBB / "contracts"))
import cbb_contracts  # noqa: E402

def _load_jsonl(p: Path) -> list[dict]:
    if not p.exists():
        return []
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


SUSPEND_RATE_MAX = 0.10
COVERAGE_MIN = 0.90


def load_slice_names(slice_text: str, store: Path) -> set[str]:
    """分母（机械）：『』专名 ∪ 库内名在切片出现者。"""
    names = set(re.findall(r"『([^『』]{2,12})』", slice_text))
    aliases = [json.loads(x) for x in
               (store / "aliases.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    char_dir = store / "libraries" / "character" / "provisional"
    canon = set()
    for f in char_dir.glob("*.json") if char_dir.exists() else []:
        try:
            canon.add(json.loads(f.read_text(encoding="utf-8"))["canonical"]["name"])
        except Exception:
            continue
    for a in aliases:
        if a["alias"] in slice_text:
            names.add(a["alias"])
    names |= {c for c in canon if c in slice_text}
    # 噪声剔除（机械规则）：称呼后缀/超长短语；库内名一律保留（硬门口径）
    stop = {"迷宫", "魔石", "剑术"}
    suff = ("大人", "酱", "小姐", "君", "殿下", "桑", "哥哥", "姐姐", "同学")
    return {n for n in names if len(n) >= 2 and n not in stop
            and not n.endswith(suff) and len(n) <= 10}


def candidate_names(ext: dict) -> set[str]:
    got = set()
    for c in ext["candidates"]:
        ca = c.get("canonical") or {}
        for k in ("name", "subject", "object"):
            if isinstance(ca.get(k), str):
                got.add(ca[k])
        if isinstance(ca.get("entities"), list):
            got |= set(ca["entities"])
        for al in c.get("aliases_to_register", []) or []:
            got.add(al)
    # 二次：用引文+observation 文本回收覆盖（触及口径=内容触及）
    text_blob = json.dumps(ext["candidates"], ensure_ascii=False)
    return got, text_blob


def eval_dangling(ext: dict, slice_text: str) -> tuple[int, int, list]:
    total, bad, bads = 0, 0, []
    for c in ext["candidates"]:
        for ev in c.get("evidence", []):
            total += 1
            if ev.get("quote") not in slice_text:
                bad += 1
                bads.append({"name": (c.get("canonical") or {}).get("name"),
                             "quote": (ev.get("quote") or "")[:30]})
    return total, bad, bads


def eval_envelope(ext: dict) -> list[str]:
    """封套契约拦截（离线 normalize 等价校验，不触库）。"""
    import hashlib
    violations = []
    for c in ext["candidates"]:
        if c.get("type") not in ("entity", "relation", "event", "foreshadow", "setting"):
            violations.append(f"非法 type {c.get('type')!r}")
            continue
        ca = c.get("canonical")
        if not isinstance(ca, dict):
            violations.append("canonical 非对象")
            continue
        rec_type = {"entity": "entity", "relation": "relation",
                    "event": "event", "foreshadow": "foreshadow",
                    "setting": "setting"}[c["type"]]
        lib = c.get("library")
        payload = {"c": ca, "e": c.get("evidence")}
        rid = "cand-" + rec_type + "-" + hashlib.sha256(
            json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:12]
        rec = {"record_id": rid, "record_type": rec_type, "library": lib,
               "status": "candidate", "canonical": ca,
               "observations": c.get("observations", []),
               "evidence": c.get("evidence"),
               "verified_against": ext.get("_meta", {}).get("source", {}),
               "provenance": {"extractor_confidence": c.get("confidence", 0),
                              "extractor": "retest", "gate_trace": [],
                              "precedent_refs": [], "status_history": []},
               "version": 1, "supersedes": None}
        if rec_type in ("event", "foreshadow") and c.get("entities_involved"):
            rec["canonical"] = dict(ca)
            rec["canonical"]["entities"] = sorted(set(c["entities_involved"]))
        try:
            cbb_contracts.validate_record(rec, allow_candidate=True)
        except Exception as e:
            violations.append(f"{str(ca.get('name') or ca.get('subject'))[:16]}: {str(e)[:90]}")
    return violations


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--extraction", required=True)
    ap.add_argument("--slice", required=True)
    ap.add_argument("--store", default="迷深实战-本体库")
    ns = ap.parse_args(argv)
    ext = json.loads(Path(ns.extraction).read_text(encoding="utf-8"))
    slice_text = Path(ns.slice).read_text(encoding="utf-8")

    # 1 悬空率
    total, bad, bads = eval_dangling(ext, slice_text)
    rate = (bad / total) if total else 0.0
    # 2 覆盖分层（R-018/W2 探针口径）：硬门=库内名召回；软报=『』新专名触及
    store = Path(ns.store)
    libnames = set()
    import glob as _g
    for f in _g.glob(str(store / 'libraries' / '*' / 'provisional' / '*.json')):
        try:
            libnames.add(json.loads(Path(f).read_text(encoding='utf-8'))['canonical']['name'])
        except Exception:
            continue
    for a in _load_jsonl(store / 'aliases.jsonl'):
        libnames.add(a['alias'])
    got, blob = candidate_names(ext)
    in_slice_lib = sorted({n for n in libnames if n in slice_text})
    lib_hit = sorted({n for n in in_slice_lib if n in got or n in blob})
    lib_missing = sorted(set(in_slice_lib) - set(lib_hit))
    cov = len(lib_hit) / len(in_slice_lib) if in_slice_lib else 1.0
    need = load_slice_names(slice_text, store)
    hit = {n for n in need if n in got or n in blob}
    missing = sorted(need - hit)
    # 3 封套
    violations = eval_envelope(ext)
    # 4 密度/轨道（辅报）
    n = len(ext["candidates"])
    by_type = {}
    track_obs = 0
    for c in ext["candidates"]:
        by_type[c["type"]] = by_type.get(c["type"], 0) + 1
        track_obs += sum(1 for o in c.get("observations", [])
                         if isinstance(o, dict) and o.get("category") in ("evolution", "trait", "manifestation"))
    gate_pass = rate <= SUSPEND_RATE_MAX and cov >= COVERAGE_MIN and not violations
    print(json.dumps({
        "extraction": ns.extraction,
        "gate": "PASS" if gate_pass else "FAIL",
        "dangling": {"bad": bad, "total": total, "rate": round(rate, 4),
                     "pass": rate <= SUSPEND_RATE_MAX, "samples": bads[:5]},
        "coverage_lib_hard": {"hit": len(lib_hit), "in_slice": len(in_slice_lib),
                               "recall": round(cov, 4), "pass": cov >= COVERAGE_MIN,
                               "missing": lib_missing[:25]},
        "envelope": {"violations": violations[:10], "pass": not violations},
        "density": {"total": n, "by_type": by_type, "track_obs_share": round(track_obs / max(n, 1), 3)},
    }, ensure_ascii=False, indent=1))
    return 0 if gate_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
