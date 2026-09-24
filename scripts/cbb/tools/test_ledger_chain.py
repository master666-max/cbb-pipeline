# -*- coding: utf-8 -*-
"""test_ledger_chain.py — U-C03.6 吸收件单测（账本哈希链+仪器指纹）。
离线：临时目录全链路，不碰真库。"""
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import ledger_chain as lc  # noqa: E402


def _fresh(tmp: str):
    store = Path(tmp) / "store"
    store.mkdir(exist_ok=True)
    ls = lc.LedgedStore(store)
    return ls


def test_append_records_sha_before_after():
    with tempfile.TemporaryDirectory() as tmp:
        ls = _fresh(tmp)
        ls.register_alias("基督", "cand-entity-x1", "人物")
        rows = ls.ledger._rows()
        assert rows and rows[-1]["op"] == "append"
        assert rows[-1]["target"] == "aliases.jsonl"
        assert rows[-1]["sha_before"] == lc.EMPTY_SHA  # 首次：文件不存在
        assert rows[-1]["sha_after"] != lc.EMPTY_SHA
        ls.register_alias("基督君", "cand-entity-x1", "人物")
        rows = ls.ledger._rows()
        assert rows[-1]["sha_before"] == rows[-2]["sha_after"]  # 链式衔接
        r = ls.ledger.verify(Path(tmp) / "store")
        assert r["ok"], r


def test_collision_skip_no_target_growth():
    with tempfile.TemporaryDirectory() as tmp:
        ls = _fresh(tmp)
        ls.register_alias("基督", "cand-entity-x1", "人物")
        n_before = len((Path(tmp) / "store" / "aliases.jsonl").read_text().splitlines())
        # 直接调 _append 同 key 对象——绕过 register_alias 自带去重，模拟纵深防御场景
        ls._append("aliases.jsonl", {"key": "基督|cand-entity-x1|人物",
                                     "alias": "基督", "entity_id": "cand-entity-x1",
                                     "entity_type": "人物"})
        n_after = len((Path(tmp) / "store" / "aliases.jsonl").read_text().splitlines())
        assert n_after == n_before, "碰撞跳过后目标文件不得增长"
        rows = ls.ledger._rows()
        assert rows[-1]["op"] == "skip" and rows[-1]["collision_total"] == 1
        assert ls.ledger.collision_count("aliases.jsonl") == 1
        assert ls.ledger.verify(Path(tmp) / "store")["ok"]


def test_store_semantics_equivalent():
    """LedgedStore 与裸 ThreeStateStore 行为等价：同操作同库内容。"""
    with tempfile.TemporaryDirectory() as tmp:
        plain = _fresh(tmp)
        rec = {"record_id": "cand-entity-abcd", "record_type": "entity",
               "library": "character", "status": "candidate",
               "canonical": {"name": "测试者", "entity_type": "人物"},
               "observations": [{"category": "summary", "chapter": 1, "text": "测试"}],
               "evidence": [{"vol": 1, "chapter": 1, "line": 1, "quote": "测试者登场"}],
               "verified_against": {"path": "t.txt", "sha": "a" * 40,
                                    "verified_at": "2026-09-18"},
               "provenance": {"extractor_confidence": 0.9, "extractor": "t",
                              "gate_trace": [], "precedent_refs": [],
                              "status_history": []},
               "version": 1, "supersedes": None}
        import copy
        import cbb_store
        (Path(tmp) / "plain").mkdir()
        plain2 = cbb_store.ThreeStateStore(Path(tmp) / "plain")
        plain2.admit(copy.deepcopy(rec), "provisional")
        ls = _fresh(tmp)
        ls.admit(copy.deepcopy(rec), "provisional")
        # 双库同一实体文件内容一致（除 record 内部无差异）
        a = json.loads((Path(tmp) / "plain" / "libraries" / "character" /
                        "provisional" / "cand-entity-abcd.json").read_text(encoding="utf-8"))
        b = json.loads((Path(tmp) / "store" / "libraries" / "character" /
                        "provisional" / "cand-entity-abcd.json").read_text(encoding="utf-8"))
        assert a == b


def test_tamper_detected():
    with tempfile.TemporaryDirectory() as tmp:
        ls = _fresh(tmp)
        ls.register_alias("基督", "cand-entity-x1", "人物")
        p = Path(tmp) / "store" / "ledger.jsonl"
        rows = [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines()]
        rows[-1]["target"] = "tampered.jsonl"  # 篡改末行
        p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
                     encoding="utf-8")
        r = ls.ledger.verify()
        assert not r["ok"] and any("行哈希" in e for e in r["errors"])


def test_genesis_idempotent_and_offledger_change_detected():
    with tempfile.TemporaryDirectory() as tmp:
        store = Path(tmp) / "store"
        store.mkdir(exist_ok=True)
        (store / "aliases.jsonl").write_text('{"key": "a|1|人物"}\n', encoding="utf-8")
        led = lc.LedgerChain(store / "ledger.jsonl")
        assert led.record_genesis("aliases.jsonl", lc._sha256_file(store / "aliases.jsonl"))
        assert led.record_genesis("aliases.jsonl", lc._sha256_file(store / "aliases.jsonl")) is None
        assert led.verify(store)["ok"]
        (store / "aliases.jsonl").write_text('{"key": "b|2|人物"}\n', encoding="utf-8")
        r = led.verify(store)
        assert not r["ok"] and any("账本外改动" in e for e in r["errors"])


def test_instrument_fingerprint():
    f1 = lc.instrument_fingerprint("random", "coverage", "desc", {"n": 30, "seed": 7})
    f2 = lc.instrument_fingerprint("random", "coverage", "desc", {"n": 30, "seed": 7})
    f3 = lc.instrument_fingerprint("random", "coverage", "desc", {"n": 30, "seed": 8})
    assert f1["fingerprint"] == f2["fingerprint"] and f1["fingerprint"] != f3["fingerprint"]
    assert set(f1) == {"ranker", "criterion", "sort", "params", "fingerprint"}
    # params 字符串形态等价
    f4 = lc.instrument_fingerprint("random", "coverage", "desc", '{"n": 30, "seed": 7}')
    assert f4["fingerprint"] == f1["fingerprint"]




def test_zone_writes_ledgered():
    """隔离区写入入账：admit(quarantine) 走 zone.register → items.jsonl 入链。"""
    with tempfile.TemporaryDirectory() as tmp:
        ls = _fresh(tmp)
        rec = {"record_id": "cand-relation-zz01", "record_type": "relation",
               "library": "relation", "status": "candidate",
               "canonical": {"subject": "A", "rel_type": "敌对", "object": "B"},
               "observations": [], "evidence": [{"vol": 1, "chapter": 9, "line": 1, "quote": "q"}],
               "verified_against": {"path": "t.txt", "sha": "a" * 40, "verified_at": "2026-09-18"},
               "provenance": {"extractor_confidence": 0.9, "extractor": "t", "gate_trace": [],
                              "precedent_refs": [], "status_history": []},
               "version": 1, "supersedes": None}
        ls.admit(rec, "quarantine", quarantine_group="low_confidence", quarantine_detail="测试")
        rows = [r for r in ls.ledger._rows()
                if r["target"] == "quarantine-zone/items.jsonl" and r["op"] == "append"]
        assert rows, "zone 写入必须入账"
        r = ls.ledger.verify(Path(tmp) / "store")
        assert r["ok"], r


def test_rebaseline_idempotent():
    with tempfile.TemporaryDirectory() as tmp:
        store = Path(tmp) / "store"
        store.mkdir()
        (store / "quarantine-zone").mkdir()
        (store / "quarantine-zone" / "items.jsonl").write_text('{"item_id": "q-1"}' + chr(10), encoding="utf-8")
        led = lc.LedgerChain(store / "ledger.jsonl")
        led.record_genesis("quarantine-zone/items.jsonl", "b" * 64)  # 过时基线
        assert led.record_rebaseline("quarantine-zone/items.jsonl", lc._sha256_file(store / "quarantine-zone" / "items.jsonl"))
        assert led.record_rebaseline("quarantine-zone/items.jsonl", lc._sha256_file(store / "quarantine-zone" / "items.jsonl")) is None
        assert led.verify(store)["ok"]


def test_c1_rows_cached_and_consistent():
    """C1 反例：原实现每次 _rows/_tail/has_key 全量重读解析（O(n²)）。
    契约=实例内缓存复用（同一对象）＋追加在缓存内续行＋缓存与盘逐字一致。"""
    with tempfile.TemporaryDirectory() as tmp:
        led = lc.LedgerChain(Path(tmp) / "ledger.jsonl")
        for i in range(5):
            led.record_append("libraries/x.jsonl", f"k{i}", lc.EMPTY_SHA, "a" * 64)
        rows = led._rows()
        assert led._rows() is rows                        # 旧实现：每次新列表（恒 False）
        assert [r["seq"] for r in rows] == [1, 2, 3, 4, 5]
        assert led._tail()["seq"] == 5                    # 追加后缓存内同步看得见
        assert led.has_key("libraries/x.jsonl", "k4")
        disk = [json.loads(x) for x in
                (Path(tmp) / "ledger.jsonl").read_text(encoding="utf-8").splitlines()
                if x.strip()]
        assert disk == rows                               # 缓存 == 盘（无漂移）
        assert lc._line_hash(disk[-1]) == disk[-1]["hash"]  # 链自洽


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
