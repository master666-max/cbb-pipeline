# -*- coding: utf-8 -*-
"""test_重排器.py — 统一客户端测试（传输层注入，零网络；正负对照成对）"""
import importlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
rr = importlib.import_module("重排器")


def _stub_transport(responses):
    """按调用次序返回罐头响应体；多余调用抛错（防意外网络）。"""
    calls = {"n": 0}
    def t(endpoint, payload, timeout):
        i = calls["n"]; calls["n"] += 1
        if i >= len(responses):
            raise AssertionError("意外的外呼")
        return responses[i]
    t.calls = calls
    return t


def test_score_parses_standard_shape():
    body = json.dumps({"results": [{"index": 1, "relevance_score": 0.9},
                                   {"index": 0, "relevance_score": 0.1}]}).encode("utf-8")
    s = rr.score("q", ["甲", "乙"], transport=lambda e, p, t: body.decode("utf-8"))
    assert s == [0.1, 0.9]  # 对齐 documents 下标


def test_score_none_on_mismatch_and_error():
    body = json.dumps({"results": [{"index": 0, "relevance_score": 0.5}]}).encode("utf-8")
    assert rr.score("q", ["甲", "乙"], transport=lambda e, p, t: body.decode("utf-8")) is None
    assert rr.score("q", ["甲"], transport=lambda e, p, t: (_ for _ in ()).throw(OSError("挂了"))) is None


def test_order_stable_desc():
    body = json.dumps({"results": [{"index": 0, "relevance_score": 0.5},
                                   {"index": 1, "relevance_score": 0.5},
                                   {"index": 2, "relevance_score": 0.9}]}).encode("utf-8")
    o = rr.order("q", ["a", "b", "c"], transport=lambda e, p, t: body.decode("utf-8"))
    assert o == [2, 0, 1]  # 0.9 第一；并列 0.5/0.5 稳定序


def test_rerank_or_mechanical_both_paths():
    ok = json.dumps({"results": [{"index": 0, "relevance_score": 0.8}]}).encode("utf-8")
    o1, bk1 = rr.rerank_order_or_mechanical("q", ["a"], [0], transport=lambda e, p, t: ok.decode("utf-8"))
    assert bk1 == "rerank" and o1 == [0]
    o2, bk2 = rr.rerank_order_or_mechanical("q", ["a"], [0, 1],
                                            transport=lambda e, p, t: (_ for _ in ()).throw(OSError("x")))
    assert bk2 == "mechanical" and o2 == [0, 1]  # 降级=机械序原样


def test_payload_is_utf8_and_carry_query():
    seen = {}
    def t(endpoint, payload, timeout):
        seen["body"] = payload
        return json.dumps({"results": [{"index": 0, "relevance_score": 0.5}]}).encode("utf-8")
    rr.score("谁在传递情报", ["斯诺用眼神交流"], transport=t)
    body = seen["body"].decode("utf-8")
    d = json.loads(body)
    assert d["query"] == "谁在传递情报" and d["documents"] == ["斯诺用眼神交流"]  # UTF-8 无 mojibake


if __name__ == "__main__":
    import tempfile
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"OK {fn.__name__}")
    print(f"{len(fns)} tests PASS")
