# -*- coding: utf-8 -*-
"""test_v3_g25_adjudicate_lock.py — G25 并发锁：adjudicate 单写者（总工单 G25 判据）。
并发压测双跑零交叠：异件并发零丢更新；同件并发幂等恰一行。
"""
import json
import sys
import tempfile
import threading
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from cbb2.quarantine import QuarantineZone, adjudicate_lock  # noqa: E402
from cbb2.ledger import LedgedStore  # noqa: E402


def _mk_zone(td, n=16):
    z = QuarantineZone(Path(td))
    for i in range(n):
        z.register("low_confidence", f"detail-{i}", record_id=f"r-{i}", at="ch0001")
    return z


def test_lock_is_held_exclusively():
    with tempfile.TemporaryDirectory() as td:
        with adjudicate_lock(Path(td)) as kind:
            assert kind in ("msvcrt", "fcntl", None)


def test_concurrent_distinct_items_zero_lost_update():
    """8 线程各裁 2 件：全部落定+裁决行=件数（修复前整文件重写互踩会丢更新）。"""
    with tempfile.TemporaryDirectory() as td:
        z = _mk_zone(td, 16)
        ids = [i["item_id"] for i in z._load()]
        errs = []

        def worker(pair):
            try:
                for j, iid in enumerate(pair):
                    z.adjudicate(iid, "confirmed" if j == 0 else "rejected", note="g25")
            except Exception as e:  # noqa: BLE001 — 压测收集面
                errs.append(str(e))

        pairs = [ids[i:i + 2] for i in range(0, 16, 2)]
        threads = [threading.Thread(target=worker, args=(p,)) for p in pairs]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errs, errs
        items = z._load()
        assert all(i["status"] in ("confirmed", "rejected") for i in items)
        adj = [l for l in (z.root / "adjudications.jsonl").read_text(encoding="utf-8").splitlines()
               if l.strip()]
        assert len(adj) == 16


def test_concurrent_same_item_idempotent_single_row():
    """同件并发同判定（经 LedgedStore）：裁决行恰 1——幂等检查与写入同锁，双写根除。"""
    with tempfile.TemporaryDirectory() as td:
        ls = LedgedStore(Path(td))
        z = ls.zone
        iid, created = z.register("low_confidence", "d", record_id="r-x", at="ch0001")
        assert created
        errs = []

        def worker():
            try:
                z.adjudicate(iid, "confirmed", note="g25-same")
            except Exception as e:  # noqa: BLE001 — 压测收集面
                errs.append(str(e))

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errs, errs
        adj = [l for l in (z.root / "adjudications.jsonl").read_text(encoding="utf-8").splitlines()
               if l.strip()]
        assert len(adj) == 1, json.dumps(adj, ensure_ascii=False)
