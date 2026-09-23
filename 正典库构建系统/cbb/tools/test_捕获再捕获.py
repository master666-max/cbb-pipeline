# -*- coding: utf-8 -*-
"""test_捕获再捕获.py — Chapman 估计量的数学正确性（手算对账）"""
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
cc = importlib.import_module("捕获再捕获")


def test_chapman_known_values():
    """手算对账：n1=n2=40, m=10 → N̂=(41×41)/11−1≈151.8；m=16 → (41×41)/17−1≈97.9。"""
    r10 = cc.chapman(40, 40, 10)
    assert abs(r10["N_hat"] - 151.8) < 0.1, r10
    r16 = cc.chapman(40, 40, 16)
    assert abs(r16["N_hat"] - 97.9) < 0.1, r16
    assert r16["residual"] == round(max(97.9 - 40, 0), 1)


def test_chapman_edge_cases():
    try:
        cc.chapman(40, 40, 50)
        raise AssertionError("m 超界应拒")
    except ValueError as e:
        assert "不能超过" in str(e)
    try:
        cc.chapman(0, 40, 0)
        raise AssertionError("n1=0 应拒")
    except ValueError:
        pass


def test_agreement_independence_check():
    a = {"r1", "r2", "r3"}
    b = {"r1", "r2", "r4"}
    agg = cc.agreement(a, b)
    assert agg["共同"] == 2 and agg["jaccard"] == 0.5  # 低重叠=独立性可


def test_batch_report():
    rep = cc.batch_report([{"n1": 40, "n2": 40, "m": 10}, {"n1": 40, "n2": 40, "m": 16}],
                          sample_size=40)
    assert rep["avg_N_hat"] == round((151.8 + 97.9) / 2, 1)


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"OK {fn.__name__}")
    print(f"{len(fns)} tests PASS")
