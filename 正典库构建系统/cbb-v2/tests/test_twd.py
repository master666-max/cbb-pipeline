# -*- coding: utf-8 -*-
"""cbb2.twd 属性测试：阈值推导单调性、DS-EM 收敛方向、三支判定边界。"""
import math

import pytest

from cbb2 import twd

LOSS_OK = {"PP": 0.0, "PN": 10.0, "BP": 2.0, "BN": 2.0, "NP": 4.0, "NN": 0.0}


def test_alpha_beta_values_and_monotonicity():
    a, b = twd.alpha_beta(LOSS_OK)
    assert (a, b) == (0.8, 0.5)
    # 错晋升代价升高 ⇒ α 单调升（宁可挂起，不可污染正典）
    for pn in (10.0, 20.0, 40.0):
        loss = dict(LOSS_OK, PN=pn)
        a2, _ = twd.alpha_beta(loss)
        assert a2 >= 0.8 - 1e-9


def test_alpha_beta_rejects_bad_matrices():
    with pytest.raises(ValueError):
        twd.alpha_beta(dict(LOSS_OK, BP=5.0, NP=4.0))  # 违反 λ_BP ≤ λ_NP
    with pytest.raises(ValueError):
        twd.alpha_beta(dict(LOSS_OK, PN=2.0, BN=2.0, BP=2.0, PP=2.0))  # 阈值退化/1-单调破坏


def test_posterior_direction_and_extremes():
    # 理想考官：support 只在 θ+ 出现，against 只在 θ− 出现
    model = {"prior": 0.5, "emit": {"A": {1: {"support": 0.9, "against": 0.0, "unsure": 0.1},
                                           0: {"support": 0.0, "against": 0.9, "unsure": 0.1}}}}
    assert twd.posterior({"A": "support"}, model) > 0.99
    assert twd.posterior({"A": "against"}, model) < 0.01
    # 噪声考官的 support 证据会被对抗票拉回
    model2 = {"prior": 0.5, "emit": {
        "N": {1: {"support": 0.6, "against": 0.0, "unsure": 0.4},
              0: {"support": 0.4, "against": 0.0, "unsure": 0.6}},
        "S": {1: {"support": 0.9, "against": 0.0, "unsure": 0.1},
              0: {"support": 0.1, "against": 0.2, "unsure": 0.7}}}}
    p_noisy_alone = twd.posterior({"N": "support"}, model2)
    p_with_strong = twd.posterior({"N": "support", "S": "support"}, model2)
    assert 0.5 < p_noisy_alone < 0.8
    assert p_with_strong > p_noisy_alone


def test_decide_boundaries():
    assert twd.decide(0.9, 0.8, 0.5) == "positive"
    assert twd.decide(0.5, 0.8, 0.5) == "negative"
    assert twd.decide(0.65, 0.8, 0.5) == "boundary"
    with pytest.raises(ValueError):
        twd.decide(0.6, 0.4, 0.6)


def test_dawid_skene_recovers_strong_signal():
    # 两个干净考官 + 一个噪声考官：全 support 票型应得到高后验，含噪声反对票的后验应显著下降
    records = []
    for i in range(60):
        records.append({"votes": {"A": "support", "B": "support", "N": "support" if i % 2 else "unsure"}})
    for i in range(30):
        records.append({"votes": {"A": "against", "B": "unsure", "N": "support" if i % 2 else "unsure"}})
    model = twd.dawid_skene_fit(records)
    p_all_in = twd.posterior({"A": "support", "B": "support", "N": "support"}, model)
    p_mixed = twd.posterior({"A": "unsure", "B": "unsure", "N": "support"}, model)
    assert p_all_in > p_mixed
    assert p_all_in > 0.8
    assert math.isfinite(p_mixed)
