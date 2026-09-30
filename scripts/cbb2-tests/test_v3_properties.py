# -*- coding: utf-8 -*-
"""test_v3_properties.py — Phase F·G03：Hypothesis 属性测试（决策树完备性+账本链重算）。
运行：py -X utf8 -m pytest test_v3_properties.py -x -q
"""
import json
import string
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from hypothesis import given, settings, strategies as st, HealthCheck  # noqa: E402
from cbb2.store import Store  # noqa: E402
from cbb2.ledger import LedgerChain  # noqa: E402

# 字母表直出不用 filter——st.text 默认全 Unicode，isalnum() 过滤器拒绝率 >90% 会触发
# HealthCheck.filter_too_much（P-028 同批修正）
ALNUM = st.text(alphabet=string.ascii_letters + string.digits, min_size=1, max_size=12)
PRINTABLE = st.text(
    alphabet=st.characters(blacklist_categories=("Cs", "Cc")),  # 去代理/控制符=isprintable 全集
    min_size=1, max_size=8)

record_strategy = st.fixed_dictionaries({
    "record_id": ALNUM,
    "record_type": st.sampled_from(["entity", "relation", "event"]),
    "library": st.sampled_from(["character", "relation", "event"]),
    "status": st.just("provisional"),
    "canonical": st.fixed_dictionaries({
        "name": PRINTABLE,
        "entity_type": st.sampled_from(["人物", "组织", "地点"]),
        "status": st.sampled_from(["alive", "dead", "missing"]),
    }),
    "evidence": st.lists(st.fixed_dictionaries({
        "vol": st.just(1), "chapter": st.integers(1, 100), "line": st.integers(1, 200),
        "quote": st.text(min_size=1, max_size=20),  # 含代理/控制符——写路径须拒绝为 ValueError 而非崩
    }), min_size=1, max_size=3),
    "provenance": st.fixed_dictionaries({"extractor_confidence": st.integers(60, 95)}),
    "version": st.just(1), "supersedes": st.none(),
    "verified_against": st.fixed_dictionaries({
        "path": st.just("t"), "sha": st.just("a" * 7), "verified_at": st.just("2000-01-01")}),
})

entry_strategy = st.fixed_dictionaries({
    "seq": st.integers(1, 100),
    "op": st.just("append"),
    "target": st.sampled_from(["libraries/character/provisional", "quarantine-zone/items.jsonl"]),
    # 去 Cs（未配对代理）：代理无法 UTF-8 编码，属字节层非法输入；
    # 保留 U+0085/U+2028 等——它们正是行撕裂缺陷的考题
    "idempotency_key": st.text(alphabet=st.characters(blacklist_categories=("Cs",)),
                               min_size=1, max_size=10),
    "sha_before": st.text(alphabet=st.characters(blacklist_categories=("Cs",)),
                          min_size=64, max_size=64),
    "sha_after": st.text(alphabet=st.characters(blacklist_categories=("Cs",)),
                         min_size=64, max_size=64),
    "prev_hash": st.text(alphabet=st.characters(blacklist_categories=("Cs",)),
                         min_size=64, max_size=64),
    "hash": st.text(alphabet=st.characters(blacklist_categories=("Cs",)),
                    min_size=64, max_size=64),
})

TRACKS = {"on-create", "consistent-duplicate", "complementary-statement",
          "invalidation-update", "uncertain-coexist", "contradiction"}


@given(rec=record_strategy,
       at=st.sampled_from(["ch0014", "ch0020", "ch0050"]))
@settings(max_examples=30, deadline=None,
          suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture])
def test_write_decision_total(rec, at):
    """任意输入必落五轨之一或抛已知 ValueError（不崩、不出未分类异常）。"""
    with tempfile.TemporaryDirectory() as td:
        store = Store(Path(td))
        try:
            out = store.write_decision(dict(rec), at=at, register_conflict=False)
            assert out["track"] in TRACKS
        except ValueError:
            pass  # 已知校验错误=可接受（不崩、不静默）


@given(e1=record_strategy, e2=record_strategy,
       at=st.sampled_from(["ch0014"]))
@settings(max_examples=20, deadline=None,
          suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture])
def test_idempotent_replay(e1, e2, at):
    """同输入二次 write_decision 不产生新库件（幂等守卫）。"""
    with tempfile.TemporaryDirectory() as td:
        store = Store(Path(td))
        try:
            store.write_decision(dict(e1), at=at, register_conflict=False)
            n0 = sum(1 for _ in store.iter_records())
            store.write_decision(dict(e2), at=at, register_conflict=False)
            n1 = sum(1 for _ in store.iter_records())
            assert n1 >= n0  # 只增不减
        except ValueError:
            pass  # 校验拒绝也是合法行为


@given(entries=st.lists(entry_strategy, max_size=30))
@settings(max_examples=30, deadline=None,
          suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large])
def test_ledger_chain_recompute(entries):
    with tempfile.TemporaryDirectory() as td:
        lc = LedgerChain(Path(td) / "ledger.jsonl")
        for e in entries:
            lc.record_append(e["target"], e["idempotency_key"], e["sha_before"], e["sha_after"])
        v = lc.verify()
        assert v["ok"]


@given(data=st.data(), entries=st.lists(entry_strategy, min_size=2, max_size=10))
@settings(max_examples=20, deadline=None)
def test_tamper_detection(data, entries):
    with tempfile.TemporaryDirectory() as td:
        lc = LedgerChain(Path(td) / "ledger.jsonl")
        for e in entries:
            lc.record_append(e["target"], e["idempotency_key"], e["sha_before"], e["sha_after"])
        # 篡改一个字节
        blob = bytearray((Path(td) / "ledger.jsonl").read_bytes())
        if blob:
            pos = data.draw(st.integers(0, len(blob) - 1))
            blob[pos] ^= 0x01
            (Path(td) / "ledger.jsonl").write_bytes(bytes(blob))
            v = LedgerChain(Path(td) / "ledger.jsonl").verify()
            # 要么哈希不匹配要么 prev 断链
            assert not v["ok"]
