# -*- coding: utf-8 -*-
"""test_p1_ledger_reanchor.py — P-1 回归：账本尾行损坏后 _append_row 不裸崩（重锚恢复）。

旧码：prev = self._rows()[-1] 为 corrupt 占位行时 prev["seq"] 直接 KeyError——
所有侧车写入从此永久崩溃。修复后：进入恢复路径，追加 reanchor 行留痕并接链，
此后记账照常；损坏历史仍由 verify() 显式披露（不静默洗白）。
"""
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from cbb2.ledger import EMPTY_SHA, LedgerChain, LedgedStore, idempotency_key_of  # noqa: E402


def _corrupt_tail(p: Path):
    """把账本尾行替换为损坏行（模拟落盘撕裂/外力截断）。"""
    lines = p.read_text(encoding="utf-8").splitlines()
    p.write_text(lines[0] + "\n{{corrupt tail\n", encoding="utf-8")


def test_p1_ledger_chain_tail_corrupt_reanchors_instead_of_crash():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "ledger.jsonl"
        led = LedgerChain(p)
        led.record_append("a.jsonl", "k1", EMPTY_SHA, EMPTY_SHA)
        _corrupt_tail(p)
        led2 = LedgerChain(p)  # 新实例——缓存不掩盖损坏
        row = led2.record_append("a.jsonl", "k2", EMPTY_SHA, EMPTY_SHA)  # 旧码此处 KeyError
        assert row["seq"] == 4  # 1 正常行 + 1 重锚行(占断点位) + 1 新行——序号位置连续
        v = LedgerChain(p).verify()
        assert not v["ok"] and "行损坏" in v["errors"][0]  # 损坏历史显式披露
        assert len(v["errors"]) == 1  # 重锚接链后不再连环误报断链


def test_p1_ledged_store_sidecar_writes_survive_tail_corruption():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        ls = LedgedStore(root)
        ls._append("x.jsonl", {"record_id": "r1", "v": 1})
        _corrupt_tail(root / "ledger.jsonl")
        ls2 = LedgedStore(root)  # 重开——旧码此后所有侧车写入永久崩溃
        obj = {"record_id": "r2", "v": 2}
        ls2._append("x.jsonl", obj)  # 修复后：重锚恢复，不裸崩
        assert ls2.ledger.has_key("x.jsonl", idempotency_key_of(obj))
        v = ls2.ledger.verify()
        assert any("行损坏" in e for e in v["errors"])  # 损坏仍披露
        ls2._append("x.jsonl", obj)  # 幂等重放：不重复入账
        assert ls2._skips.get("x.jsonl") == 1


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"OK {fn.__name__}")
    print(f"{len(fns)} tests PASS")
