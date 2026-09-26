# -*- coding: utf-8 -*-
"""test_v3_schedule.py — Phase F·G12 FSRS 重验证调度器。"""
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from cbb2.schedule import ReviewScheduler, solve_interval  # noqa: E402


def test_solve_interval_monotonic():
    assert solve_interval(1, 0.9) >= 1
    assert solve_interval(10, 0.9) > solve_interval(5, 0.9)  # S↑→N↑
    assert solve_interval(10, 0.95) < solve_interval(10, 0.90)  # r↑→N↓（更高保持率→更频繁巡检）


def test_scheduler_roundtrip():
    with tempfile.TemporaryDirectory() as td:
        sched = ReviewScheduler(Path(td))
        sched.schedule("e1", tenure_segments=5, stability=3.0)
        assert "e1" in sched.state
        e = sched.state["e1"]
        assert e["interval"] >= 1 and e["stability"] == 3.0


def test_scheduler_pass_grows_fail_resets():
    with tempfile.TemporaryDirectory() as td:
        sched = ReviewScheduler(Path(td))
        sched.schedule("e1", tenure_segments=5, stability=3.0)
        s0 = sched.state["e1"]["stability"]
        sched.record_check("e1", passed=True, segment=10)
        s_after_pass = sched.state["e1"]["stability"]
        assert s_after_pass > 3.0  # 通过→S 增长
        sched.record_check("e1", passed=False, segment=20)
        s_after_fail = sched.state["e1"]["stability"]
        assert s_after_fail < s_after_pass  # 失败→S 衰减


def test_scheduler_due_filter():
    with tempfile.TemporaryDirectory() as td:
        sched = ReviewScheduler(Path(td))
        sched.schedule("a", tenure_segments=3, stability=2.0)
        sched.schedule("b", tenure_segments=8, stability=8.0)
        due = sched.due(current_segment=50)
        assert "a" in due and "b" in due  # 初始 last_checked=0，全到期


def test_scheduler_stats():
    with tempfile.TemporaryDirectory() as td:
        sched = ReviewScheduler(Path(td))
        sched.schedule("x", tenure_segments=3, stability=2.0)
        s = sched.stats()
        assert s["total"] == 1


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"OK {fn.__name__}")
    print(f"{len(fns)} tests PASS")
