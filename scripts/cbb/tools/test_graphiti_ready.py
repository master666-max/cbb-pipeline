# -*- coding: utf-8 -*-
"""test_graphiti_ready.py — 哨兵 D（隔离矛盾积压）口径回归：R4 审计 A6 修复件。

判据：pending 一律按 adjudications 差集算（与 cbb_quarantine.status_report 同口径）——
已裁件不得计入 contradiction_pending，也不得参与裁决滞后。旧实现按 items.status
静态过滤（该字段写死后永不回写）→ 积压数只增不减、RED 不可逆（信号失真）。
两侧成对：已裁件剔除（反例）＋未裁件照数（正对照）。
"""
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import graphiti_ready as gr  # noqa: E402


def _store_with(tmp: str, items: list[dict], adjudicated: list[str]) -> Path:
    store = Path(tmp) / "store"
    q = store / "quarantine-zone"
    q.mkdir(parents=True)
    (q / "items.jsonl").write_text(
        "\n".join(json.dumps(x, ensure_ascii=False) for x in items), encoding="utf-8")
    if adjudicated:
        (q / "adjudications.jsonl").write_text(
            "\n".join(json.dumps({"item_id": i}, ensure_ascii=False) for i in adjudicated),
            encoding="utf-8")
    return store


def test_trigger_d_excludes_adjudicated():
    """反例：60 件全已裁——旧实现 contradiction=60>50 → RED 且不可逆；修复后 GREEN。"""
    with tempfile.TemporaryDirectory() as tmp:
        items = [{"item_id": f"q{i}", "status": "pending", "group": "entity_unalignable",
                  "at": "2000-01-01"} for i in range(60)]
        store = _store_with(tmp, items, [f"q{i}" for i in range(60)])
        out = gr.trigger_sentinel(store, logs_dir=Path(tmp) / "logs")
        assert out["D"]["value"]["contradiction_pending"] == 0, out["D"]["value"]
        assert out["D"]["value"]["pending_total"] == 0
        assert out["D"]["state"] == "GREEN", out["D"]
        assert out["D"]["value"]["裁决滞后"]["days"] is None  # 已裁件日期不得参与滞后


def test_trigger_d_counts_true_pending():
    """正对照成对：未裁件必须照数（不得为过测试把闸门关死）。"""
    with tempfile.TemporaryDirectory() as tmp:
        items = [{"item_id": f"q{i}", "status": "pending", "group": "entity_unalignable",
                  "at": "2026-09-20"} for i in range(3)]
        items.append({"item_id": "resolved", "status": "pending",
                      "group": "entity_unalignable", "at": "2000-01-01"})
        store = _store_with(tmp, items, ["resolved"])
        out = gr.trigger_sentinel(store, logs_dir=Path(tmp) / "logs")
        assert out["D"]["value"]["contradiction_pending"] == 3
        assert out["D"]["value"]["pending_total"] == 3
        assert out["D"]["state"] == "AMBER"                    # >0 未超阈
        lag = out["D"]["value"]["裁决滞后"]
        assert lag["days"] is not None and lag["since"] == "2026-09-20"


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted({k: v for k, v in globals().items()
                            if k.startswith("test_") and callable(v)}.items()):
        try:
            fn()
            print(f"PASS {name}")
        except AssertionError as e:
            fails += 1
            print(f"FAIL {name}: {e}")
    raise SystemExit(1 if fails else 0)
