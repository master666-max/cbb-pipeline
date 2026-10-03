# -*- coding: utf-8 -*-
"""test_wiki_export.py — X2 导出器端到端（夹具 store，离线）：页数对账/隔离专区/图谱/快照锚。
附带批次 6 runner（batch6_export.py）回归：--status confirmed 真过滤（审计修复）。
"""
import json
import subprocess
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
    # 失效链一行（审计修复：渲染必须读 old_id/new_id/version 真实字段）
    (store / "supersede-index.jsonl").write_text(json.dumps(
        {"old_id": "cand-b", "new_id": "cand-b2", "version": 2}, ensure_ascii=False) + "\n",
        encoding="utf-8")


def test_wiki_export_end_to_end(tmp_path, monkeypatch):
    store = tmp_path / "store"
    _seed_store(store)
    out = tmp_path / "快照"

    # notary.ledger_head 正常可读（夹具账本自洽）；runner 以子进程实跑（端到端）
    runner = HERE.parent / "pipeline" / "wiki_export.py"  # 包内布局：运行件在 scripts/pipeline/
    r = subprocess.run([sys.executable, "-X", "utf8", str(runner),
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
    # 失效链索引用真实字段渲染（审计修复：不得再出 seqNone None → None 垃圾行）
    sup_md = (out / "wiki" / "indexes" / "superseded.md").read_text(encoding="utf-8")
    assert "`cand-b` → `cand-b2`" in sup_md and "version 2" in sup_md
    assert "seqNone" not in sup_md


# ---- 批次 6 runner 回归（审计修复：--status confirmed 假开关） ----

def _seed_batch6_store(store: Path, only_provisional: bool = False):
    conf_dir = store / "libraries" / "character" / "confirmed"
    conf_dir.mkdir(parents=True, exist_ok=True)
    if not only_provisional:
        (conf_dir / "cand-ok.json").write_text(json.dumps({
            "record_id": "cand-ok", "library": "character", "status": "confirmed",
            "canonical": {"name": "沈青梧", "entity_type": "人物"},
            "evidence": [{"vol": 1, "chapter": 3, "line": 10, "quote": "沈青梧的引文。"}],
            "_aliases": []}, ensure_ascii=False), encoding="utf-8")
    prov_dir = store / "libraries" / "character" / "provisional"
    prov_dir.mkdir(parents=True, exist_ok=True)
    (prov_dir / "cand-no.json").write_text(json.dumps({
        "record_id": "cand-no", "library": "character", "status": "provisional",
        "canonical": {"name": "玉佩", "entity_type": "物品"},
        "evidence": [{"vol": 1, "chapter": 3, "line": 11, "quote": "玉佩的引文。"}],
        "_aliases": []}, ensure_ascii=False), encoding="utf-8")
    (store / "aliases.jsonl").write_text("", encoding="utf-8")
    (store / "snapshot.json").write_text(json.dumps(
        {"检查点": {"rows": 0, "chain_head": "ut"}, "store_root": str(store)},
        ensure_ascii=False), encoding="utf-8")


def _run_batch6(runner: Path, store: Path, out: Path, *extra):
    return subprocess.run([sys.executable, "-X", "utf8", str(runner),
                           "--store", str(store), "--aliases", str(store / "aliases.jsonl"),
                           "--snapshot", str(store / "snapshot.json"), "--out", str(out), *extra],
                          capture_output=True, text=True, timeout=120)


def test_batch6_status_confirmed_real_filter(tmp_path):
    """审计修复：--status confirmed 必须按 effective status 真过滤——
    未定（provisional）记录不得以已确认名义外流；--status all 缺省不受影响。"""
    runner = HERE.parent / "pipeline" / "batch6_export.py"  # 包内布局（工作区副本指向仓根运行件）
    store = tmp_path / "store"
    _seed_batch6_store(store)

    out_cf = tmp_path / "导出-confirmed"
    r = _run_batch6(runner, store, out_cf, "--status", "confirmed")
    assert r.returncode == 0, r.stdout[-500:] + r.stderr[-500:]
    st = json.loads((out_cf / "lorebook" / "sillytavern-v1.json").read_text(encoding="utf-8"))
    blob = json.dumps(st, ensure_ascii=False)
    assert st["entries"], "确认件必须仍在流"
    assert "沈青梧" in blob
    assert "玉佩" not in blob, "未定记录以已确认名义外流（--status 假开关回归）"

    out_all = tmp_path / "导出-all"
    r2 = _run_batch6(runner, store, out_all)  # 缺省 all：不过滤
    assert r2.returncode == 0, r2.stdout[-500:] + r2.stderr[-500:]
    blob_all = (out_all / "lorebook" / "sillytavern-v1.json").read_text(encoding="utf-8")
    assert "沈青梧" in blob_all and "玉佩" in blob_all


def test_batch6_status_confirmed_zero_hit_outputs_zero(tmp_path):
    """审计修复：全库无 confirmed ⇒ 零命中如实输出 0（不回落 all、不外流未定记录）。"""
    runner = HERE.parent / "pipeline" / "batch6_export.py"
    store = tmp_path / "store"
    _seed_batch6_store(store, only_provisional=True)
    out = tmp_path / "导出-zero"
    r = _run_batch6(runner, store, out, "--status", "confirmed")
    assert r.returncode == 0, r.stdout[-500:] + r.stderr[-500:]
    summary = json.loads((out / "批次6摘要.json").read_text(encoding="utf-8"))
    assert summary["cluster 总数"] == 0
    assert summary["lorebook 条目"] == 0
    assert summary["rag 块"] == 0
    st = json.loads((out / "lorebook" / "sillytavern-v1.json").read_text(encoding="utf-8"))
    assert st["entries"] == {}
    assert "玉佩" not in json.dumps(st, ensure_ascii=False)
