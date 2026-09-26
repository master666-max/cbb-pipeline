# -*- coding: utf-8 -*-
"""test_v3_notary.py — Phase F·U-F01 检查点外部发布（独立复算原则）。
运行：py -X utf8 test_v3_notary.py"""
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from cbb2 import notary  # noqa: E402


def seed_ledger(root: Path, n: int):
    """种子账本：行哈希公式与 cbb2.ledger.line_hash 同源（保证 verify 重放可用）。"""
    import hashlib
    from cbb2.ledger import line_hash
    root.mkdir(parents=True, exist_ok=True)
    prev = "genesis"
    lines = []
    for i in range(1, n + 1):
        payload = {"seq": i, "op": "append", "target": "libraries/x/provisional", "i": i,
                   "idempotency_key": f"k{i}", "sha_before": "0" * 64, "sha_after": "1" * 64,
                   "prev_hash": prev}
        h = line_hash({**payload, "hash": None}) if False else hashlib.sha256(
            json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
        row = {**payload, "hash": h}
        lines.append(json.dumps(row, ensure_ascii=False, sort_keys=True))
        prev = h
    (root / "ledger.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return prev


def test_publish_and_verify_roundtrip():
    with tempfile.TemporaryDirectory() as td:
        store = Path(td) / "store"
        channel = Path(td) / "channel"
        seed_ledger(store, 100)
        r = notary.publish(store, channel, "迷深实战", at="ch0020")
        assert r["rows"] == 100 and r["chain_head"] != "genesis"
        v = notary.verify(channel, store, "迷深实战")
        assert v["ok"], v


def test_verify_detects_append_after_publish():
    """发布后账本前进 ⇒ 检查点过期（须重发，不是通过）。"""
    with tempfile.TemporaryDirectory() as td:
        store = Path(td) / "store"
        channel = Path(td) / "channel"
        store.mkdir(parents=True)
        seed_ledger(store, 50)
        notary.publish(store, channel, "demo", at="ch0050")
        # 账本追加 50 行
        with (store / "ledger.jsonl").open("a", encoding="utf-8") as f:
            for i in range(51, 101):
                prev = ""
                f.write(json.dumps({"seq": i, "hash": f"h{i}", "prev_hash": ""}) + "\n")
        v = notary.verify(channel, store, "demo")
        assert not v["ok"] and any(("断链" in e) or ("size" in e) or ("漂移" in e) for e in v["errors"])


def test_verify_detects_tamper():
    """账本中途行被改 ⇒ 链尾哈希变 ⇒ 检查点对不上。"""
    with tempfile.TemporaryDirectory() as td:
        store = Path(td) / "store"
        channel = Path(td) / "channel"
        store.mkdir(parents=True)
        seed_ledger(store, 30)
        notary.publish(store, channel, "demo", at="ch0030")
        # 篡改第 10 行 payload（不改末行）
        p = store / "ledger.jsonl"
        lines = p.read_text(encoding="utf-8").splitlines()
        row = json.loads(lines[9])
        row["tampered"] = True
        lines[9] = json.dumps(row, ensure_ascii=False, sort_keys=True)
        p.write_text("\n".join(lines) + "\n", encoding="utf-8")
        v = notary.verify(channel, store, "demo")
        assert not v["ok"]


def test_torn_ledger_rejected_at_publish():
    """撕裂账本不许发检查点（先修账本）。"""
    with tempfile.TemporaryDirectory() as td:
        store = Path(td) / "store"
        store.mkdir(parents=True)
        (store / "ledger.jsonl").write_text(
            json.dumps({"seq": 1, "hash": "h"}) + "\n" + '{"seq": 2, " torn":',
            encoding="utf-8")
        try:
            notary.ledger_head(store)
            raise AssertionError("撕裂账本未报错")
        except ValueError as e:
            assert "撕裂" in str(e)


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"OK {fn.__name__}")
    print(f"{len(fns)} tests PASS")
