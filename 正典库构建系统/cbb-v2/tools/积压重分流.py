# -*- coding: utf-8 -*-
"""积压重分流.py — U-A06 白名单写：604 件矛盾积压按 v3 决策树重分流（流程设计 P3）。

用法：
  py -X utf8 积压重分流.py --dry-run    # 重算分布并与 0926 报告断言一致（零写入）
  py -X utf8 积压重分流.py --execute    # 正式执行（现役全对齐→write_decision→adjudicate 入账）
  py -X utf8 积压重分流.py --sample 20  # 执行后抽样对样（库内在位+引文逐字回落）
  --store <路径>                        # 演练副本用

对齐语义（U-A06 彩排修正版）：旧章候选 vs 现役库——**现役全对齐**
（冲突断言位一律取现役值；被舍弃的更富值进「信息保全清单」留人审）。
理由：候选多为早期抽取，时序上早于已演化的现役知识；反向失效=拿旧知否新知。
rule 分桶仅用于报告：richer（一侧含另一侧）/ stored-vocab（公共子串≥2）/ manual（词根全异）。
"""
from __future__ import annotations

import argparse
import difflib
import json
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from cbb2.ledger import LedgedStore  # noqa: E402
from cbb2.store import identity_key  # noqa: E402
from cbb2 import contract  # noqa: E402

ROOT = HERE.parents[1]
STORE = ROOT / "迷深实战-本体库"
WS = ROOT / "迷深实战-工作区"
DRYREF = WS / "logs" / "积压重分流-dryrun分布-20260926.json"
PAT = re.compile(r"(entity_type|claim): 入库=(.*) vs 库内=(.*)$")


def _unq(v: str) -> str:
    return v[1:-1] if len(v) >= 2 and v[0] == v[-1] == "'" else v


def core(v: str) -> str:
    return re.sub(r"（.*?）|\(.*?\)|\s", "", v)


def rule_of(vin: str, vst: str) -> str:
    ci, cs = core(vin), core(vst)
    if ci and cs and (ci in cs or cs in ci):
        return "richer"
    m = difflib.SequenceMatcher(None, ci, cs).find_longest_match(0, len(ci), 0, len(cs))
    return "stored-vocab" if m.size >= 2 else "manual"


def load_items(store_root: Path) -> list[dict]:
    q = Path(store_root) / "quarantine-zone" / "items.jsonl"
    return [json.loads(x) for x in q.read_text(encoding="utf-8").splitlines() if x.strip()]


def candidate_index() -> dict:
    idx = {}
    for f in sorted((WS / "candidates").glob("cands-ch*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        recs = d.get("candidates") if isinstance(d, dict) else d
        for r in recs or []:
            rid = r.get("record_id")
            if rid:
                idx[rid] = r
    return idx


def bucketize(items: list[dict], idx: dict) -> dict:
    b = {"richer": [], "stored-vocab": [], "manual_pair": [], "claim": [],
         "no_detail": [], "candidate_miss": []}
    for it in items:
        if it.get("subclass") != "contradiction_pending" or it.get("status") != "pending":
            continue
        m = PAT.search(it.get("detail", ""))
        if not m:
            b["no_detail"].append(it)
            continue
        field, vin, vst = m.group(1), _unq(m.group(2)), _unq(m.group(3))
        if field == "claim":
            b["claim"].append(it)
            continue
        rule = rule_of(vin, vst)
        if rule == "manual":
            b["manual_pair"].append(it)
        elif it.get("record_id") not in idx:
            b["candidate_miss"].append(it)
        else:
            b[rule].append(it)
    return b


def pseudo_at(record: dict) -> str:
    chs = [e.get("chapter") for e in (record.get("evidence") or [])
           if isinstance(e.get("chapter"), int)]
    return f"ch{max(chs):04d}" if chs else "ch0000"


def warm_cache(ls) -> dict:
    """身份→现役记录 全库一遍预热（write_decision 传 existing 免每件全库扫描）。"""
    inv = {e["record_id"] for e in ls._load_all("invalidations.jsonl")}
    chain = {e["old_id"]: e["new_id"] for e in ls._load_all("supersede-index.jsonl")}
    cache = {}
    for rec in ls.iter_records():
        if rec.get("record_id") in inv:
            continue
        k = identity_key(rec)
        cur = cache.get(k)
        if cur is None or rec.get("version", 1) > cur.get("version", 1):
            cache[k] = rec
    for k, rec in list(cache.items()):
        rid, seen = rec["record_id"], set()
        while rid in chain and rid not in seen:
            seen.add(rid)
            rid = chain[rid]
        if rid != rec["record_id"]:
            r2 = ls._find(rid)
            if r2:
                cache[k] = r2
    return cache


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--sample", type=int, default=0)
    ap.add_argument("--store", default=str(STORE), help="库根（演练副本用）")
    ns = ap.parse_args()

    store_root = Path(ns.store)
    items = load_items(store_root)
    cons = [i for i in items if i.get("subclass") == "contradiction_pending"
            and i.get("status") == "pending"]
    idx = candidate_index()

    if ns.dry_run:
        b = bucketize(items, idx)
        ref = json.loads(DRYREF.read_text(encoding="utf-8"))
        auto = len(b["richer"]) + len(b["stored-vocab"]) + len(b["claim"])
        assert len(cons) == ref["contradiction"] == 604, f"矛盾件数漂移 {len(cons)}"
        assert len(b["richer"]) + len(b["stored-vocab"]) + len(b["manual_pair"]) \
            + len(b["candidate_miss"]) == ref["fields_fallback"]["entity_type"] == 414, "entity_type 分布漂移"
        assert len(b["claim"]) == ref["fields_fallback"]["claim"] == 2, "claim 分布漂移"
        assert len(b["no_detail"]) == 604 - 416, "无 detail 桶漂移"
        print(json.dumps({"断言": "与 0926 dry-run 报告逐类一致", "自动可判": auto,
                          "manual_pair": len(b["manual_pair"]),
                          "candidate_miss": len(b["candidate_miss"]),
                          "no_detail": len(b["no_detail"]),
                          "候选索引": f"{len(idx)} 件"}, ensure_ascii=False, indent=1))
        return 0

    if ns.execute:
        ls = LedgedStore(store_root)
        cache = warm_cache(ls)
        before = ls.ledger.verify(store_root)
        b = bucketize(items, idx)
        done, manual, info_keep = [], [], []
        for it in b["richer"] + b["stored-vocab"]:
            m = PAT.search(it["detail"])
            _, vin, vst = m.group(1), _unq(m.group(2)), _unq(m.group(3))
            rule = rule_of(vin, vst)
            cand = idx.get(it.get("record_id"))
            if cand is None:
                manual.append({"item_id": it["item_id"], "why": "candidate_miss"})
                continue
            rec = json.loads(json.dumps(cand, ensure_ascii=False))
            k = identity_key(rec)
            existing = cache.get(k)
            if existing is None:
                manual.append({"item_id": it["item_id"], "why": "existing_not_found"})
                continue
            prof = contract.load_profile(rec.get("library") or "")
            at = pseudo_at(rec)
            keep_log = {}
            for c in contract.classify_conflicts(prof, rec, existing):
                if c["kind"] == "statement":
                    continue  # 陈述位留给 write_decision 互补分支
                if len(str(c["in"])) > len(str(c["stored"])):
                    keep_log[c["field"]] = {"incoming": c["in"], "kept": c["stored"]}
                rec["canonical"][c["field"]] = c["stored"]  # 现役全对齐
            if keep_log:
                rec.setdefault("_meta", {})["alignment"] = {"rule": "existing-wins",
                                                            "info_kept": keep_log}
                info_keep.append({"item_id": it["item_id"], "identity": k[-1],
                                  **keep_log})
            try:
                r = ls.write_decision(rec, at=at, existing=existing,
                                      register_conflict=False)
            except Exception as e:
                manual.append({"item_id": it["item_id"], "why": f"write_error:{type(e).__name__}:{e}"})
                continue
            if r["track"] not in ("consistent-duplicate", "complementary-statement"):
                manual.append({"item_id": it["item_id"], "why": f"unexpected-track:{r['track']}"})
                continue
            ls.zone.adjudicate(it["item_id"], "confirmed",
                               note=f"phaseA重分流 rule={rule} track={r['track']} at={at}",
                               by="phaseA-U-A06")
            done.append({"item_id": it["item_id"], "rule": rule, "track": r["track"],
                         "new_id": r.get("new_id") or r.get("event_id")})
        for it in b["claim"]:
            cand = idx.get(it.get("record_id"))
            if cand is None:
                manual.append({"item_id": it["item_id"], "why": "candidate_miss(claim)"})
                continue
            rec = json.loads(json.dumps(cand, ensure_ascii=False))
            r = ls.write_decision(rec, at=pseudo_at(rec),
                                  existing=cache.get(identity_key(rec)),
                                  register_conflict=False)
            if r["track"] not in ("complementary-statement", "consistent-duplicate"):
                manual.append({"item_id": it["item_id"], "why": f"claim-track:{r['track']}"})
                continue
            ls.zone.adjudicate(it["item_id"], "confirmed",
                               note=f"phaseA重分流 claim→{r['track']}", by="phaseA-U-A06")
            done.append({"item_id": it["item_id"], "rule": "claim", "track": r["track"]})
        for it in b["no_detail"] + b["manual_pair"] + b["candidate_miss"]:
            why = "no_detail" if it in b["no_detail"] else (
                "manual_pair" if it in b["manual_pair"] else "candidate_miss")
            manual.append({"item_id": it["item_id"], "why": why,
                           "detail": it.get("detail", "")[:80]})
        (WS / "积压重分流-人工桶-20260926.json").write_text(
            json.dumps(manual, ensure_ascii=False, indent=1), encoding="utf-8")
        (WS / "积压重分流-信息保全-20260926.json").write_text(
            json.dumps(info_keep, ensure_ascii=False, indent=1), encoding="utf-8")
        after = ls.ledger.verify(store_root)
        new_err = [e for e in after["errors"] if e not in before["errors"]]
        fresh_items = load_items(store_root)
        rep = {"executed": len(done), "manual": len(manual), "info_keep": len(info_keep),
               "ledger_before_errors": len(before["errors"]),
               "ledger_after_errors": len(after["errors"]),
               "ledger_new_errors": new_err,
               "remaining_pending_contradiction":
                   sum(1 for i in fresh_items
                       if i.get("subclass") == "contradiction_pending"
                       and i.get("status") == "pending")}
        (WS / "logs" / "积压重分流-执行报告-20260926.json").write_text(
            json.dumps({**rep, "done": done}, ensure_ascii=False, indent=1),
            encoding="utf-8")
        print(json.dumps(rep, ensure_ascii=False, indent=1))
        return 0 if not new_err else 1

    if ns.sample:
        rep = json.loads((WS / "logs" / "积压重分流-执行报告-20260926.json").read_text(encoding="utf-8"))
        done = rep["done"]
        idx = candidate_index()
        ls = LedgedStore(store_root)
        random.seed(20260926)
        picks = random.sample(done, min(ns.sample, len(done)))
        results = []
        for d in picks:
            item = next(i for i in load_items(store_root) if i["item_id"] == d["item_id"])
            cand = idx.get(item.get("record_id"))
            ok_lib = ok_quote = False
            if cand:
                live = ls.find_by_identity(cand)
                ok_lib = live is not None or d["track"] == "complementary-statement"
                evs = (cand.get("evidence") or []) if d["track"] != "complementary-statement" \
                    else (live.get("evidence") or [] if live else [])
                for e in evs or (cand.get("evidence") or []):
                    ch = e.get("chapter", 0)
                    sp = WS / "slice" / f"ch{ch:04d}.txt"
                    if not sp.exists():
                        sp = WS / "slice" / f"ch{ch:06d}.txt"
                    if sp.exists() and e.get("quote") and e["quote"] in sp.read_text(encoding="utf-8"):
                        ok_quote = True
                        break
            results.append({"item_id": d["item_id"], "lib_ok": ok_lib,
                            "quote_ok": ok_quote, "pass": ok_lib and ok_quote})
        n_pass = sum(1 for r in results if r["pass"])
        rate = n_pass / len(results) if results else 0
        out = {"sampled": len(results), "passed": n_pass, "rate": round(rate, 3),
               "gate": "PASS" if rate >= 0.95 else "FAIL", "results": results}
        (WS / "logs" / "积压重分流-对样-20260926.json").write_text(
            json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
        print(json.dumps({k: out[k] for k in ("sampled", "passed", "rate", "gate")},
                         ensure_ascii=False))
        return 0 if out["gate"] == "PASS" else 1
    ap.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
