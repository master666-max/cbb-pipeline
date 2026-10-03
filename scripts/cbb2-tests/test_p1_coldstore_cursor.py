# -*- coding: utf-8 -*-
"""test_p1_coldstore_cursor.py — P-1 回归：冷段分段游标读到位 + 二次分段幂等去重。

旧码两处：① 分段后 ledger.jsonl 新增行永不读取（重建静默缺尾）；
② 账本增长后二次分段，旧尾段与新增 zst 段内容重叠（读出重复行）。
修复后：load_all_rows 按游标续读 ledger.jsonl 尾部；尾段只认最新一段。
"""
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from cbb2 import coldstore  # noqa: E402


def _append_rows(root: Path, n: int, start: int):
    with (root / "ledger.jsonl").open("a", encoding="utf-8") as f:
        for i in range(start, start + n):
            f.write(json.dumps({"seq": i, "hash": f"h{i:04d}"}) + "\n")


def test_p1_coldstore_rows_after_segmentation_are_read():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        root.mkdir(exist_ok=True)
        _append_rows(root, 100, start=1)
        assert coldstore.segment_ledger(root, segment_size=30)["status"] == "segmented"
        _append_rows(root, 5, start=101)  # 分段快照后新增账本行——旧码永不读取（静默缺尾）
        rows = coldstore.load_all_rows(root)
        assert len(rows) == 105
        assert json.loads(rows[-1])["seq"] == 105
        assert json.loads(rows[0])["seq"] == 1  # 前段不丢


def test_p1_coldstore_resegmentation_idempotent_no_duplicates():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        root.mkdir(exist_ok=True)
        _append_rows(root, 150, start=1)
        coldstore.segment_ledger(root, segment_size=50)
        _append_rows(root, 10, start=151)
        coldstore.segment_ledger(root, segment_size=50)  # 二次分段——旧码读出重复行
        rows = coldstore.load_all_rows(root)
        seqs = [json.loads(r)["seq"] for r in rows]
        assert len(rows) == 160
        assert sorted(seqs) == list(range(1, 161))  # 无重复、无缺位
        # 再来一次同总量分段：完全幂等
        coldstore.segment_ledger(root, segment_size=50)
        assert len(coldstore.load_all_rows(root)) == 160


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"OK {fn.__name__}")
    print(f"{len(fns)} tests PASS")
