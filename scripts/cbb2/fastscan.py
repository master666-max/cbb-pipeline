"""cbb2/fastscan.py — 多模式字面匹配粗筛（Phase F·G04；物理算法路 Q2）。

双实现：ahocorasick_rs（Rust，LeftmostLongest 适配中文）> pyahocorasick > 正则回落。
用法：粗筛命中的小窗口才跑正则——大词表场景比逐条正则快 1-2 个量级。
缺席降级：AC 库不可用 → 纯正则（行为等价，性能回落）。
"""
from __future__ import annotations

_ENGINE = None
_engine_checked = False


def _try_ac():
    global _ENGINE, _engine_checked
    if _engine_checked:
        return _ENGINE
    _engine_checked = True
    for mod in ("ahocorasick_rs", "ahocorasick"):
        try:
            _ENGINE = __import__(mod)
            _ENGINE._name = mod
            return _ENGINE
        except ImportError:
            continue
    _ENGINE = None
    return None


def ac_available() -> bool:
    return _try_ac() is not None


def ac_scan(text: str, patterns: list[str]) -> list[dict]:
    """AC 多模式匹配；命中返回 [{pattern, start, end}]。"""
    ac = _try_ac()
    if ac is None or not patterns:
        return _regex_scan(text, patterns)
    if hasattr(ac, "AhoCorasick"):
        # ahocorasick_rs
        acm = ac.AhoCorasick(patterns, matchkind=ac.MatchKind.LeftmostLongest if hasattr(ac, "MatchKind") else None)
        return [{"pattern": patterns[p], "start": s, "end": e}
                for p, s, e in acm.find_matches_as_tuples(text)]
    # pyahocorasick
    auto = ac.automaton()
    for p in patterns:
        auto.add_word(p, (p,))
    auto.make_automaton()
    out = []
    for end, (p,) in auto.iter(text):
        out.append({"pattern": p, "start": end - len(p) + 1, "end": end + 1})
    return out


def _regex_scan(text: str, patterns: list[str]) -> list[dict]:
    out = []
    for p in patterns:
        start = 0
        while True:
            idx = text.find(p, start)
            if idx == -1:
                break
            out.append({"pattern": p, "start": idx, "end": idx + len(p)})
            start = idx + 1
    return out


def scan_patterns(text: str, patterns: list[str]) -> list[dict]:
    """统一入口：AC 可用→AC；不可用→字符串查找（纯 Python，零依赖回落）。"""
    if not patterns or not text:
        return []
    ac = _try_ac()
    if ac is not None and hasattr(ac, "AhoCorasick"):
        try:
            return ac_scan(text, patterns)
        except (ImportError, AttributeError, RuntimeError):
            pass  # AC 引擎不可用或参数不兼容→回落纯 Python 扫描
    return _regex_scan(text, patterns)
