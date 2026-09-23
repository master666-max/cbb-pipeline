# -*- coding: utf-8 -*-
"""词表.py — 受控词表三件套（2026-09-22 用户裁定 ③A+B）

裁定 ③A 三条通用规则（逐条机械执行）：
  1. **词表自举**：对存量做字段取值频次统计，逐值四选一——保留／归并到 X／降级／新增提案，
     不许漏值（本件产出提案表，四选一的裁断归人）。
  2. **粒度纪律**：枚举值之间禁包含关系——"人物"与"人物(迷宫生物)"并存=事故源
     （实例：604 件假矛盾、人工 128/129 全是返工）。`lint_vocab` 抓词表侧，`check_record` 抓记录侧。
  3. **词表外→隔离＋理由码**：不静默丢。理由码：NOT_IN_VOCAB／MISSING_REQUIRED／
     GRANULARITY_VARIANT（带建议归并目标）。

裁定 ③B：对冻结实例库跑 `bootstrap` 产出**样例词表 #1**（示范件；只读，零改动）。

归并方向约定：粒度对取**更具体**一方为建议目标（样例实证：ch14 缇达案统一为"人物(迷宫生物)"），
但**库内权威优先**——`check_record` 的建议目标是"包含它的词表值"，机械档对齐由 矛盾分流.py 按库内值执行。
"""
from __future__ import annotations

import json
import unicodedata
from collections import Counter
from pathlib import Path

LIBS = ("character", "relation", "setting", "event", "foreshadow", "timeline")


def normalize(s: str) -> str:
    """NFKC＋去空白＋去常见括号差异后的规范化形（比较用；原值永远保留）。"""
    s = unicodedata.normalize("NFKC", str(s))
    return "".join(ch for ch in s if not ch.isspace()).strip("()（）:：-—")


def iter_records(store_root: Path | str, status_dir: str = "provisional"):
    root = Path(store_root)
    for lib in LIBS:
        d = root / "libraries" / lib / status_dir
        if not d.exists():
            continue
        for f in sorted(d.glob("*.json")):
            try:
                yield json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue


def bootstrap(store_root: Path | str, fields: tuple[str, ...] = ("entity_type",)) -> dict:
    """词表自举：频次统计＋包含对探测（产出提案，不裁断）。只读。"""
    out: dict[str, dict] = {}
    for field in fields:
        cnt: Counter = Counter()
        for rec in iter_records(store_root):
            v = (rec.get("canonical") or {}).get(field)
            if isinstance(v, str) and v.strip():
                cnt[v.strip()] += 1
        vals = sorted(cnt, key=lambda x: (-cnt[x], x))
        pairs = []
        for a in vals:
            for b in vals:
                if a != b and normalize(a) and normalize(a) in normalize(b):
                    pairs.append({"short": a, "long": b, "short_n": cnt[a], "long_n": cnt[b],
                                  "proposal": f"{a!r} 归并到 {b!r}（更具体方向）",
                                  "态": "待确认（四选一：保留/归并/降级/新增）"})
        out[field] = {"values": dict(cnt.most_common()), "distinct": len(cnt),
                      "containment_pairs": pairs,
                      "口径": f"分母=provisional 库 canonical.{field} 非空字符串计数"}
    return out


def lint_vocab(vocab: dict[str, list[str]]) -> list[dict]:
    """词表侧粒度纪律：同字段枚举值之间禁包含关系。"""
    bad = []
    for field, values in vocab.items():
        ns = [(v, normalize(v)) for v in values]
        for i, (va, na) in enumerate(ns):
            for vb, nb in ns[i + 1:]:
                if na and nb and (na in nb or nb in na):
                    bad.append({"field": field, "pair": [va, vb],
                                "reason": "GRANULARITY_CONFLICT",
                                "why": "词表值存在包含关系——粒度纪律违反（裁定③A-2）"})
    return bad


def check_record(record: dict, vocab: dict[str, list[str]],
                 required_fields: dict[str, tuple[str, ...]] | None = None) -> list[dict]:
    """记录侧核查（门"词表域"的纯函数核）：返回违规清单（空=过）。
    理由码：NOT_IN_VOCAB／GRANULARITY_VARIANT（带建议目标）／MISSING_REQUIRED。"""
    lib = record.get("library")
    canon = record.get("canonical") or {}
    v: list[dict] = []
    for field, values in vocab.items():
        val = canon.get(field)
        if not isinstance(val, str) or not val.strip():
            continue
        if val in values:
            continue
        nv = normalize(val)
        cand = next((x for x in values if normalize(x) and (nv in normalize(x) or normalize(x) in nv)),
                    None)
        if cand is not None:
            v.append({"field": field, "value": val, "reason": "GRANULARITY_VARIANT",
                      "suggest": cand})
        else:
            v.append({"field": field, "value": val, "reason": "NOT_IN_VOCAB"})
    for field in (required_fields or {}).get(lib, ()):
        val = canon.get(field)
        if val is None or (isinstance(val, str) and not val.strip()):
            v.append({"field": field, "value": None, "reason": "MISSING_REQUIRED"})
    return v


def check_store(store_root: Path | str, vocab: dict[str, list[str]],
                required_fields: dict[str, tuple[str, ...]] | None = None,
                limit: int | None = None) -> dict:
    """全库干跑（只读，零改动——U-D04 纪律）：多少条会被词表域拦下、按理由码分布。"""
    by_reason: Counter = Counter()
    samples: list[dict] = []
    checked = 0
    for rec in iter_records(store_root):
        checked += 1
        for v in check_record(rec, vocab, required_fields):
            by_reason[v["reason"]] += 1
            if len(samples) < 10:
                samples.append({"record_id": rec.get("record_id"), **v})
        if limit and checked >= limit:
            break
    return {"checked": checked, "violations": sum(by_reason.values()),
            "by_reason": dict(by_reason), "samples": samples,
            "口径": "干跑只读；分母=provisional 库记录"}


def main(argv=None) -> int:  # pragma: no cover
    import argparse
    ap = argparse.ArgumentParser(description="受控词表（裁定③A+B）")
    ap.add_argument("--store", required=True)
    ap.add_argument("--fields", default="entity_type")
    ap.add_argument("--out")
    ns = ap.parse_args(argv)
    rep = bootstrap(ns.store, tuple(ns.fields.split(",")))
    for field, info in rep.items():
        print(f"== {field}：{info['distinct']} 个取值 ==")
        for v, n in list(info["values"].items())[:30]:
            print(f"  {n:5d}  {v}")
        for p in info["containment_pairs"]:
            print(f"  [包含对] {p['proposal']}")
    if ns.out:
        Path(ns.out).write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
