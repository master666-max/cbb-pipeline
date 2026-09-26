# -*- coding: utf-8 -*-
"""cbb2.gaps — 缺口队列生成器（Phase D·U-D07；进化闭环唯一入口，流程设计 P5）。

扫描来源：契诃夫超期（foreshadow）/ 词表缺口（quarantine 自创值）/ NLI 分歧簇（人审队列）/
植物 miss / ER 缺口（悬挂引用）。产出 缺口队列.jsonl：{type, evidence, proposed_action}。
"""
from __future__ import annotations

import json
from pathlib import Path

QUEUE = "缺口队列.jsonl"


def _append(store_root: Path, row: dict):
    p = Path(store_root) / QUEUE
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists():  # B12：按 (type,evidence) 幂等——重复扫描不膨胀队列
        for x in p.read_text(encoding="utf-8").splitlines():
            if not x.strip():
                continue
            old = json.loads(x)
            if old.get("type") == row.get("type") and old.get("evidence") == row.get("evidence"):
                return
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def scan_foreshadow_overdue(store_root: Path, current_chapter: int, grace: int = 3) -> list[dict]:
    out = []
    for f in sorted(Path(store_root).glob("libraries/foreshadow/*/*.json")):
        try:
            r = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        c = r.get("canonical") or {}
        setup, payoff = c.get("setup_chapter"), c.get("payoff_chapter")
        if isinstance(setup, int) and not isinstance(payoff, int) \
                and current_chapter - setup > grace:
            out.append({"type": "契诃夫超期", "evidence": r.get("record_id"),
                        "detail": f"{c.get('name')} setup@{setup} 超 {current_chapter-setup} 章未回收",
                        "proposed_action": "下批抽取提示差量：关注该伏笔兑现"})
    for row in out:
        _append(store_root, row)
    return out


def scan_vocab_gaps(store_root: Path) -> list[dict]:
    """隔离区里 unknown/自创 entity_type 值 ⇒ 词表缺口。"""
    out = []
    q = Path(store_root) / "quarantine-zone" / "items.jsonl"
    if not q.exists():
        return out
    for x in q.read_text(encoding="utf-8").splitlines():
        if not x.strip():
            continue
        it = json.loads(x)
        d = it.get("detail", "")
        if it.get("subclass") == "contradiction_pending" and "entity_type" in d:
            out.append({"type": "词表缺口", "evidence": it.get("item_id"),
                        "detail": d[:120],
                        "proposed_action": "词表差量升级（区段边界批处理+措辞偏置审计）"})
    seen = set()
    uniq = [r for r in out if r["detail"] not in seen and not seen.add(r["detail"])]
    for row in uniq[:20]:
        _append(store_root, row)
    return uniq


def scan_plant_miss(store_root: Path, capture_report: dict) -> list[dict]:
    out = [{"type": "植物miss", "evidence": r["plant_id"], "detail": f"{r['name']} 未捕获",
            "proposed_action": "核查抽取器对该类断言的召回"} for r in capture_report.get("miss", [])]
    for row in out:
        _append(store_root, row)
    return out


def scan_nli_disagreement(store_root: Path, dual_results: list[dict]) -> list[dict]:
    out = [{"type": "NLI分歧", "evidence": json.dumps(r.get("votes"), ensure_ascii=False)[:120],
            "detail": "双通道判定不一致", "proposed_action": "人审队列（只分流不裁决）"}
           for r in dual_results if not r.get("agree") and r.get("votes")]
    for row in out:
        _append(store_root, row)
    return out


def load_queue(store_root: Path) -> list[dict]:
    p = Path(store_root) / QUEUE
    if not p.exists():
        return []
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
