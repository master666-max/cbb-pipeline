# -*- coding: utf-8 -*-
"""cbb2.er — 实体归一三段流水线 + 可撤销合并日志（Phase D·U-D08；路⑤ B1-B5）。

规则归一（NFKC/括注剥离/零宽）→ blocking（首字+字符集键）→ [可选 LLM 判决回调]。
合并可撤销：union-find + 合并日志（谁/何时/依据），split 回滚是一等公民。
0.85~0.95 绝对相似带废弃 → margin（best/second 差）+ 分歧信号。
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

BRACKET_RE = re.compile(r"[（(].*?[)）]")
ZERO_RE = re.compile(r"[\u200b\u200c\u200d\ufeff]")


def normalize_name(name: str) -> str:
    """确定性归一层：NFKC 全半角、剥括注、去零宽与空白。无风险消化大部分写法变体。"""
    s = unicodedata.normalize("NFKC", name or "")
    s = BRACKET_RE.sub("", s)
    s = ZERO_RE.sub("", s)
    return s.strip()


def blocking_key(name: str) -> tuple:
    n = normalize_name(name)
    return (n[:1], "".join(sorted(set(n))[:6]), len(n))


def margin_decision(scores: dict[str, float], min_margin: float = 0.05) -> dict:
    """margin+分歧信号：best 与 second 差 < min_margin ⇒ 存疑人审；否则归 best。"""
    ranked = sorted(scores.items(), key=lambda x: -x[1])
    if not ranked:
        return {"target": None, "certain": False}
    best, s_best = ranked[0]
    s_second = ranked[1][1] if len(ranked) > 1 else -1.0
    certain = (s_best - s_second) >= min_margin
    return {"target": best if certain else None, "certain": certain,
            "margin": round(s_best - s_second, 4)}


class MergeLog:
    """可撤销合并：union-find + 操作日志（linked 分组按日志重放）。"""

    def __init__(self, store_root: Path):
        self.path = Path(store_root) / "合并日志.jsonl"

    def _rows(self) -> list[dict]:
        if not self.path.exists():
            return []
        return [json.loads(x) for x in self.path.read_text(encoding="utf-8").splitlines()
                if x.strip()]

    def merge(self, canonical: str, variant: str, *, rule: str, confidence: float, at: str) -> dict:
        row = {"op": "merge", "canonical": canonical, "variant": variant,
               "rule": rule, "confidence": confidence, "at": at,
               "id": f"m-{hashlib_sha(canonical, variant, at)}"}
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        return row

    def split(self, variant: str, *, at: str, note: str = "") -> dict:
        row = {"op": "split", "variant": variant, "at": at, "note": note,
               "id": f"s-{hashlib_sha(variant, at, note)}"}
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        return row

    def resolve(self, name: str) -> str:
        """重放日志求规范名：merge 归并、split 拆出（split 后该 variant 回到自身）。"""
        parent: dict[str, str] = {}

        def find(x: str) -> str:
            parent.setdefault(x, x)
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        for r in self._rows():
            if r["op"] == "merge":
                a, b = find(r["canonical"]), find(r["variant"])
                if a != b:
                    parent[b] = a
            elif r["op"] == "split":
                root = find(r["variant"])  # B10：拆根=解散整组合并（回滚语义完备）
                for k in list(parent):
                    if find(k) == root:
                        parent[k] = k
        return find(name)

    def groups(self) -> dict[str, list[str]]:
        g: dict[str, list[str]] = {}
        names: set[str] = set()
        for r in self._rows():
            if r["op"] == "merge":
                names.add(r["canonical"])
                names.add(r["variant"])
        for n in names:
            g.setdefault(self.resolve(n), []).append(n)
        return g


def hashlib_sha(*parts: str) -> str:
    import hashlib
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:12]
