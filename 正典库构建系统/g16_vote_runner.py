# -*- coding: utf-8 -*-
"""g16_vote_runner.py — G5 票数晋升全库首跑·推断层 769 件（总工单 G16 执行件）。

对象：quarantine-zone/items.jsonl 里 subclass=extrapolation_unverified 且 status=pending
      的隔离件（置信度路由 0.8<0.85 保守隔离的推断断言）。
机制：三考官（LOCAL/DEEPSEEK/QWEN）隔离双序评审（答案对调纠位置偏见），
      ≥⌈2/3⌉ support 且 against=0 ⇒ confirmed；任何 against ⇒ 转人工；其余 hold。
纪律：append-only 裁决台账 + items.jsonl 原位状态更新（沿用 batch_dispose_268 家法）；
      幂等（已裁决 item_id 跳过，可续跑）；本体缺失/证据为空件显式登记不臆断。
env 编制：EXAMINER_{LOCAL,DEEPSEEK,QWEN}_{BASE,MODEL} + key（或公共回落）全走进程 env，
      密钥不落文件（D-004）。

用法：
  py -X utf8 g16_vote_runner.py --dry-run          # 分布盘点，零 API
  py -X utf8 g16_vote_runner.py --limit 30         # 试点批
  py -X utf8 g16_vote_runner.py                    # 全量（可续跑）
"""
import json
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "cbb-v2"))

from cbb2 import promote  # noqa: E402

STORE = ROOT / "迷深实战-本体库"
WORK = ROOT / "迷深实战-工作区"
QZ_ITEMS = STORE / "quarantine-zone" / "items.jsonl"
ADJ = STORE / "quarantine-zone" / "adjudications.jsonl"
REPORT = STORE / "G16-晋升报告.json"


def hash_row(row: dict) -> str:
    import hashlib
    core = json.dumps(row, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(core.encode()).hexdigest()[:16]


def load_jsonl(p: Path) -> list:
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def build_body_index() -> dict:
    """record_id → (文件名, 候选体)，递归扫工作区全部候选件。"""
    idx = {}
    for f in WORK.glob("**/cands-*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001 — 坏件跳过并在报告中显式计数
            continue
        recs = data if isinstance(data, list) else data.get("candidates", data.get("records", []))
        for r in recs:
            rid = r.get("record_id") or r.get("id")
            if rid and rid not in idx:
                idx[rid] = (f.name, r)
    return idx


def already_adjudicated() -> set:
    if not ADJ.exists():
        return set()
    return {r["item_id"] for r in load_jsonl(ADJ) if r.get("note", "").startswith("G16")}


def review_one(rid: str, body: dict, panel: list, full_size: int) -> dict:
    """单记录三考官隔离评审（票面逐项落报告）。"""
    canonical = body.get("canonical") or {}
    conclusion = json.dumps(canonical, ensure_ascii=False, sort_keys=True)
    evidence = "；".join(e.get("quote", "") for e in (body.get("evidence") or []))
    gate_dirty = bool((body.get("provenance") or {}).get("gate_trace"))
    res = promote.promotion_check({"canonical": canonical, "evidence": body.get("evidence") or []},
                                  panel, tenure_ok=True, gate_clean=not gate_dirty)
    res["record_id"] = rid
    return res


def main():
    dry = "--dry-run" in sys.argv
    limit = None
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])

    items = load_jsonl(QZ_ITEMS)
    targets = [i for i in items
               if i.get("subclass") == "extrapolation_unverified" and i.get("status") == "pending"]
    done_items = already_adjudicated()
    todo_items = [i for i in targets if i["item_id"] not in done_items]

    idx = build_body_index()
    # 同一 record_id 多个隔离指针：评审一次，结果回写全部指针；无指针件显式计数
    rid_group: dict = {}
    no_rid = 0
    for i in todo_items:
        if not i.get("record_id"):
            no_rid += 1
            continue
        rid_group.setdefault(i["record_id"], []).append(i)

    bodies = {rid: idx[rid] for rid in rid_group if rid in idx}
    missing = sorted(set(rid_group) - set(bodies))
    empty_ev = [rid for rid, (_, b) in bodies.items()
                if not "；".join(e.get("quote", "") for e in (b.get("evidence") or [])).strip()]
    gate_dirty = [rid for rid, (_, b) in bodies.items()
                  if (b.get("provenance") or {}).get("gate_trace")]

    print(f"推断层 pending 指针: {len(targets)}（已裁决跳过 {len(targets)-len(todo_items)}，无 record_id {no_rid}）")
    print(f"唯一 record_id: {len(rid_group)}  本体在库: {len(bodies)}  本体缺失: {len(missing)}")
    print(f"证据为空: {len(empty_ev)}  gate_trace 非空: {len(gate_dirty)}")

    if dry:
        sample = [bodies[r][1] for r in list(bodies)[:3]]
        Path(ROOT / "dryrun-G16-盘点.json").write_text(json.dumps(
            {"pending指针": len(targets), "唯一rid": len(rid_group), "本体在库": len(bodies),
             "本体缺失": missing, "证据为空": empty_ev, "gate脏": gate_dirty,
             "样例": sample}, ensure_ascii=False, indent=1), encoding="utf-8")
        print("[dry-run] 零 API；盘点 → dryrun-G16-盘点.json")
        return

    panel, missing_kinds = promote.build_panel()
    print(f"考官编制: {[c.kind for c in panel]}（缺席: {missing_kinds or '无'}）")
    if not panel:
        print("G16 BLOCKED：无可用考官")
        return

    full_size = 3
    runnable = [rid for rid in bodies
                if rid not in empty_ev]
    if limit:
        runnable = runnable[:limit]
    print(f"本轮评审: {len(runnable)} 件")

    t0 = time.time()
    results = {}
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(review_one, rid, bodies[rid][1], panel, full_size): rid
                for rid in runnable}
        for n, fu in enumerate(as_completed(futs), 1):
            rid = futs[fu]
            try:
                results[rid] = fu.result()
            except Exception as e:  # noqa: BLE001 — 单件异常不拖垮整批，报告显式计数
                results[rid] = {"verdict": "error", "errors": [{"examiner": "runner", "reason": str(e)[:120]}],
                                "votes": {}, "degraded": True, "record_id": rid}
            if n % 10 == 0 or n == len(runnable):
                cc = Counter(r["verdict"] for r in results.values())
                print(f"  进度 {n}/{len(runnable)}  {dict(cc)}  {time.time()-t0:.0f}s")

    # ── 写裁决台账 + 更新 items.jsonl ──
    adj_rows, item_patch = [], {}
    for rid, r in results.items():
        v = r["verdict"]
        votes = r.get("votes", {})
        by = "panel:" + ";".join(f"{k}={v2}" for k, v2 in votes.items()) or "panel:无票"
        if v == "promote":
            decision, new_status = "confirmed", "confirmed"
        elif v == "human":
            decision, new_status = "human_review", "pending"
        else:
            decision, new_status = v, "pending"
        note = f"G16票面 verdict={v} need={r.get('need')} degraded={r.get('degraded')}"
        if r.get("errors"):
            note += " errors=" + json.dumps(r["errors"], ensure_ascii=False)
        for it in rid_group[rid]:
            adj_rows.append({"by": by, "decision": decision, "item_id": it["item_id"],
                             "note": note, "hash": hash_row({"item_id": it["item_id"], "verdict": v})})
            item_patch[it["item_id"]] = (new_status,
                                         f"G16: {decision}（{by}）" if v != "promote"
                                         else f"G16: 三考官票面晋升（{by}）")

    with ADJ.open("a", encoding="utf-8") as f:
        for row in adj_rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    for it in items:
        if it["item_id"] in item_patch:
            it["status"], it["disposition"] = item_patch[it["item_id"]]
    QZ_ITEMS.write_text(
        "\n".join(json.dumps(x, ensure_ascii=False, sort_keys=True) for x in items) + "\n",
        encoding="utf-8")

    for rid in missing:
        pass  # 本体缺失件保持 pending 原状——不写台账（无票面可记），仅在报告登记

    cc = Counter(r["verdict"] for r in results.values())
    report = {
        "unit": "G16", "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "panel": [c.kind for c in panel], "panel_missing": missing_kinds,
        "full_size": full_size,
        "pending指针总数": len(targets), "本轮评审": len(runnable),
        "判定分布": dict(cc),
        "本体缺失": missing, "证据为空": empty_ev, "gate脏": gate_dirty,
        "票面": {rid: {"verdict": r["verdict"], "votes": r.get("votes", {}),
                      "degraded": r.get("degraded"), "errors": r.get("errors", [])}
                for rid, r in results.items()},
        "耗时s": round(time.time() - t0, 1),
        "tenure口径": "首晋升批——tenure 自确认日起算，G17 首圈巡检承接存续核证",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"✓ 台账 +{len(adj_rows)} 行；报告 → {REPORT}")
    print(f"判定分布: {dict(cc)}  耗时 {report['耗时s']}s")


if __name__ == "__main__":
    main()
