# -*- coding: utf-8 -*-
"""test_wiki_export.py — X2 导出器端到端（夹具 store，离线）：页数对账/隔离专区/图谱/快照锚。"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from cbb2 import notary  # noqa: E402
from cbb2.ledger import line_hash, EMPTY_SHA  # noqa: E402


def _seed_store(store: Path):
    lib = store / "libraries" / "character" / "provisional"
    lib.mkdir(parents=True, exist_ok=True)
    for i, (rid, name) in enumerate([("cand-a", "沈青梧"), ("cand-b", "玉佩")]):
        (lib / f"{rid}.json").write_text(json.dumps({
            "record_id": rid, "library": "character", "status": "provisional",
            "canonical": {"name": name, "entity_type": "人物"},
            "evidence": [{"vol": 1, "chapter": 3, "line": 10 + i, "quote": f"{name}的引文。"}],
            "_aliases": []}, ensure_ascii=False), encoding="utf-8")
    rel = store / "libraries" / "relation" / "provisional"
    rel.mkdir(parents=True, exist_ok=True)
    (rel / "cand-r.json").write_text(json.dumps({
        "record_id": "cand-r", "library": "relation", "status": "provisional",
        "canonical": {"subject": "沈青梧", "predicate": "持有", "object": "玉佩"},
        "evidence": [{"vol": 1, "chapter": 3, "line": 12, "quote": "她握紧了玉佩。"}],
        "_aliases": []}, ensure_ascii=False), encoding="utf-8")
    q = store / "quarantine-zone"
    q.mkdir(exist_ok=True)
    (q / "items.jsonl").write_text(json.dumps(
        {"item_id": "q-1", "record_id": "cand-a", "status": "pending",
         "group": "low_confidence", "disposition": "hold"}, ensure_ascii=False) + "\n", encoding="utf-8")
    # 2 行有效链（ledger_head 可读）
    rows = []
    prev = EMPTY_SHA
    for i in (1, 2):
        payload = {"seq": i, "op": "append", "target": "libraries/x", "prev_hash": prev}
        import hashlib
        h = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        rows.append(json.dumps({**payload, "hash": h}, ensure_ascii=False))
        prev = h
    (store / "ledger.jsonl").write_text("\n".join(rows) + "\n", encoding="utf-8")


def test_wiki_export_end_to_end(tmp_path, monkeypatch):
    store = tmp_path / "store"
    _seed_store(store)
    out = tmp_path / "快照"

    # notary.ledger_head 正常可读（夹具账本自洽）；runner 以子进程实跑（端到端）
    import subprocess
    r = subprocess.run([sys.executable, "-X", "utf8", str(HERE.parent.parent / "wiki_export.py"),
                        "--store", str(store), "--out", str(out)],
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stdout[-500:] + r.stderr[-500:]

    snap = json.loads((out / "SNAPSHOT.json").read_text(encoding="utf-8"))
    assert snap["对账结果"]["页数对账"] is True
    assert snap["对账结果"]["引文抽查"]["ok"] is True
    assert snap["状态"] == "PASS" and snap["隔离页数"] == 1
    # 页面逐件存在（2 记录页 + 1 relation 页 + 1 隔离页）
    assert (out / "wiki" / "records" / "character" / "cand-a.md").exists()
    assert (out / "wiki" / "records" / "relation" / "cand-r.md").exists()
    assert (out / "wiki" / "quarantine" / "q-1.md").exists()
    # 图谱投影：2 节点（沈青梧/玉佩）+ 1 边
    edges = [json.loads(l) for l in (out / "graph" / "edges.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(edges) == 1 and edges[0]["predicate"] == "持有"
    # 记录页引文逐字回链
    md = (out / "wiki" / "records" / "character" / "cand-a.md").read_text(encoding="utf-8")
    assert "沈青梧的引文。" in md
    # 索引页存在
    assert (out / "wiki" / "indexes" / "by-type" / "character.md").exists()
    assert (out / "wiki" / "_index.md").exists()
