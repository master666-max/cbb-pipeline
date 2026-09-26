# -*- coding: utf-8 -*-
"""cbb2.runner — 章管线编排（Phase C 总装）。

prepare_chapter：派工卡=动态切分判定+场景软标签+承接摘要+三层上下文包（旗标 off=整章+空包降级）。
finalize_chapter：候选批量 write_decision（身份缓存+at 伪锚点）→投影检查点推进→LightRAG 重喂判定。
抽取本体仍由宿主 Agent 按派工卡执行（判定权在人；runner 只编排与机械判定）。
"""
from __future__ import annotations

import json
from pathlib import Path

from . import config, contract, context, splitting
from .derive import ProjectionCheckpoint
from .ledger import LedgerChain, LedgedStore
from .store import Store, identity_key


def prepare_chapter(chapter_no: int, prev_chapter_text: str = "",
                    chapter_text: str = "", blocks: list[dict] | None = None,
                    store: Path | None = None, new_entity_hint: int | None = None) -> dict:
    store = Path(store or config.store_of(Path(__file__).parents[2]))
    blocks = blocks or []
    tags = splitting.scene_tags(blocks) if blocks else {"scene_count": 1, "boundaries": [],
                                                        "dialogue_ratio": 0.0, "time_jumps": 0}
    if splitting.enabled():
        decision = splitting.split_decision(chapter_text or "", tags,
                                            new_entity_hint=new_entity_hint)
        segments = (splitting.segment_blocks(blocks, tags["boundaries"])
                    if decision["split"] and blocks else None)
    else:
        decision = {"split": False, "reasons": ["旗标 CBB_DYNAMIC_SPLIT=off"], "theta": splitting.theta()}
        segments = None
    carry = context.carry_summary(store, chapter_no - 1)
    pack = context.build_context_pack(store, chapter_no,
                                      prev_slice_tail=prev_chapter_text[-400:])
    return {"chapter": chapter_no, "动态切分": decision, "场景软标签": tags,
            "分段": segments, "承接摘要": carry, "上下文包": pack,
            "口径": "先验非事实源；抽取出候选后交 finalize_chapter"}


def finalize_chapter(store_root: Path, candidates: list[dict], at: str,
                     register_conflict: bool = True) -> dict:
    """批量 write_decision（身份缓存免全库扫描）→ lightrag 投影检查点推进。"""
    ls = LedgedStore(store_root)
    cache = {}
    inv = {e["record_id"] for e in ls._load_all("invalidations.jsonl")}
    chain = {e["old_id"]: e["new_id"] for e in ls._load_all("supersede-index.jsonl")}
    for rec in ls.iter_records():
        if rec.get("record_id") in inv:
            continue
        k = identity_key(rec)
        cur = cache.get(k)
        if cur is None or rec.get("version", 1) > cur.get("version", 1):
            cache[k] = rec
    tracks: dict[str, int] = {}
    results = []
    for cand in candidates:
        k = identity_key(cand)
        r = ls.write_decision(cand, at=at, existing=cache.get(k),
                              register_conflict=register_conflict)
        tracks[r["track"]] = tracks.get(r["track"], 0) + 1
        if r.get("new_id"):
            fresh = ls._find(r["new_id"])
            if fresh:
                cache[k] = fresh
        results.append({"record_id": cand.get("record_id"), "track": r["track"],
                        "new_id": r.get("new_id") or r.get("event_id")})
    ledger = LedgerChain(Path(store_root) / "ledger.jsonl")
    rows = len(ledger._rows_fresh())
    cp = ProjectionCheckpoint(Path(store_root), "lightrag")
    cp.commit(ledger_offset=rows, sha=at, at=at)
    return {"chapters_written_at": at, "tracks": tracks, "results": results,
            "checkpoint": rows}


def refeed_needed(store_root: Path, view: str = "lightrag") -> bool:
    """账本自上次检查点以来有任何行 ⇒ 派生视图需重喂（整批重喂语义）。"""
    ledger = LedgerChain(Path(store_root) / "ledger.jsonl")
    rows = len(ledger._rows_fresh())
    return ProjectionCheckpoint(Path(store_root), view).replay_needed(rows)


def run_chapter(chapter_no: int, store: Path | None = None, no_aux: bool = False) -> dict:
    """v2 编排骨架（aux 四件探活降级；保留兼容 Phase A 前调用面）。"""
    store = store or config.store_of(Path(__file__).parents[2])
    aux = {"embedding": None, "graph": None, "replica": None, "temporal": None}
    if not no_aux:
        aux_steps = [
            ("embedding", ["py", "-X", "utf8", "cbb/tools/embed_dedup_scan.py"]),
            ("graph", ["py", "-X", "utf8", "cbb/tools/neo4j_export.py"]),
        ]
        for key, cmd in aux_steps:
            try:
                import subprocess
                r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                                   timeout=600, cwd=str(store.parent))
                aux[key] = (json.loads(r.stdout.strip().splitlines()[-1])
                            if r.stdout.strip() else {"status": "blocked"})
            except Exception as e:
                aux[key] = {"status": "error", "stderr": str(e)[-200:]}
    return {"chapter": chapter_no, "aux": aux,
            "口径": "v2 骨架——长尾工具仍由 cbb/ 提供（D1 裁决：增量迁移）"}


if __name__ == "__main__":
    raise SystemExit(run_chapter(int(sys.argv[1]) if len(sys.argv) > 1 else 0) and 0)
