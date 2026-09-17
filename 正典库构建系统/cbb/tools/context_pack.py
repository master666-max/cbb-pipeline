# -*- coding: utf-8 -*-
"""context_pack.py — 上下文包生成器（工单 v1.6 §0 编排 · 确定性脚本 R-018 · 2026-09-18）

库喂抽取的闭环：主代理派工前机械生成上下文包（≤2K tokens≈1300 字封顶），子代理视为
**先验而非事实源**（与原文冲突以原文为准+存疑分开建，防先验污染）。

四节（工单 §0 v1.6 原文）：
  ① 主要人物册（canonical+别名，出场频次排序）
  ② 活跃伏笔/开环清单（payoff 未回收；核心 tier 优先，setup_chapter 新→旧）
  ③ 最近 N 章一行提要（rolling-summary.md 尾部 30 章；文件不存在则占位）
  ④ 判例指针

种子双源：jsonl 库（aliases.jsonl/appearances.jsonl/foreshadow 库）+ 迷深清洗工作
《_alias25.json》（异名统合表——canonical 匹配合并，库内优先）。
生成全程机械规则零裁量；超预算截断顺序=②尾部→①尾部（确定性）。

用法：py -X utf8 context_pack.py --store 迷深实战-本体库 \
        --alias-seed "…/_alias25.json" --out 迷深实战-工作区/context-pack.md
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

TOP_ENTITIES = 25
TOP_FORESHADOWS = 12
ROLLING_KEEP = 30
BUDGET_CHARS = 1300

HEADER = ("# 上下文包（机械生成 · 先验而非事实源：与原文冲突以原文为准+存疑分开建）\n"
          "> 生成器=cbb/tools/context_pack.py（确定性脚本 R-018）；子代理必读但不得当作事实源。\n")


def _load_jsonl(p: Path) -> list[dict]:
    if not p.exists():
        return []
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def _load_records(lib: str, store: Path) -> list[dict]:
    out = []
    d = store / "libraries" / lib / "provisional"
    for f in sorted(d.glob("*.json")) if d.exists() else []:
        try:
            out.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
            continue
    return out


def entity_roster(store: Path, alias_seed: Path | None) -> list[str]:
    """① 人物册行：出场频次 desc，名(频次)=别名1/别名2…（库内别名∪种子统合表）。"""
    freq = Counter(r["entity"] for r in _load_jsonl(store / "appearances.jsonl"))
    # 库内别名：aliases.jsonl(entity_id) → character 库 record_id→canonical.name 映射到名字级
    id2name = {r["record_id"]: r["canonical"]["name"] for r in _load_records("character", store)}
    lib_alias: dict[str, set[str]] = {}
    for a in _load_jsonl(store / "aliases.jsonl"):
        nm = id2name.get(a.get("entity_id"))
        if nm:
            lib_alias.setdefault(nm, set()).add(a["alias"])
    seed: dict[str, list[str]] = {}
    if alias_seed and Path(alias_seed).exists():
        raw = json.loads(Path(alias_seed).read_text(encoding="utf-8"))
        seed = {k: [x for x in v if x != k] for k, v in raw.items()}
    # 类型（从 character 库取 entity_type）
    types = {r["canonical"]["name"]: r["canonical"].get("entity_type", "")
             for r in _load_records("character", store)}
    lines = []
    for name, n in freq.most_common(TOP_ENTITIES):
        al = sorted((lib_alias.get(name, set()) | set(seed.get(name, []))) - {name})[:4]
        t = types.get(name, "")
        lines.append(f"- {name}{'(' + t + ')' if t else ''}×{n}"
                     + (f"＝{'/'.join(al)}" if al else ""))
    return lines


def active_foreshadows(store: Path) -> list[str]:
    """② 活跃伏笔/开环：payoff_chapter 为空；核心 tier 优先，setup_chapter 新→旧。"""
    recs = [r for r in _load_records("foreshadow", store)
            if r.get("canonical", {}).get("payoff_chapter") is None]
    recs.sort(key=lambda r: (0 if r["canonical"].get("tier") == "核心" else 1,
                             -(r["canonical"].get("setup_chapter") or 0)))
    lines = []
    for r in recs[:TOP_FORESHADOWS]:
        c = r["canonical"]
        note = re.sub(r"\s+", " ", str(c.get("note", "")))[:38]
        lines.append(f"- [{c.get('tier', '')}] {c['name']}（ch{c.get('setup_chapter')}）{note}")
    return lines


def rolling_digest(rolling: Path) -> list[str]:
    """③ 最近 30 章一行提要：文件格式=每行 'chNNNN｜提要'；取尾部 30。"""
    if not Path(rolling).exists():
        return ["（滚动摘要未建——首班主代理种子化，见 rolling-summary.md）"]
    rows = [x.strip() for x in Path(rolling).read_text(encoding="utf-8").splitlines()
            if re.match(r"^ch\d{4}[｜|]", x.strip())]
    return rows[-ROLLING_KEEP:]


def build(store: Path, alias_seed: Path | None, rolling: Path | None) -> str:
    sec1 = entity_roster(store, alias_seed)
    sec2 = active_foreshadows(store)
    sec3 = rolling_digest(rolling or store.parent / "迷深实战-工作区" / "rolling-summary.md")
    prec = Path(__file__).resolve().parent / "判例.md"
    n_prec = len(re.findall(r"^\d+\. ", prec.read_text(encoding="utf-8"), re.M)) if prec.exists() else 0
    sec4 = [f"- cbb/tools/判例.md（当前 {n_prec} 条，连读《抽取规范.md》）"]

    def render(s2, s1):
        parts = [HEADER, "## ① 主要人物册（频次排序）\n" + ("\n".join(s1) if s1 else "（空）")]
        parts.append("## ② 活跃伏笔/开环\n" + ("\n".join(s2) if s2 else "（空）"))
        parts.append("## ③ 最近章提要\n" + "\n".join(sec3))
        parts.append("## ④ 判例指针\n" + "\n".join(sec4))
        return "\n\n".join(parts) + "\n"

    text = render(sec2, sec1)
    # 预算裁剪（确定性顺序：②尾部→①尾部）
    while len(text) > BUDGET_CHARS and len(sec2) > 0:
        sec2.pop(); text = render(sec2, sec1)
    while len(text) > BUDGET_CHARS and len(sec1) > 0:
        sec1.pop(); text = render(sec2, sec1)
    return text


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="上下文包生成器（确定性）")
    ap.add_argument("--store", default="迷深实战-本体库")
    ap.add_argument("--alias-seed",
                    default=r"..\..\迷深清洗工作\异世界迷宫最深部_知识库\分析\_角色语料库\_alias25.json")
    ap.add_argument("--rolling", default=r"迷深实战-工作区\rolling-summary.md")
    ap.add_argument("--out", default=r"迷深实战-工作区\context-pack.md")
    ns = ap.parse_args(argv)
    text = build(Path(ns.store), Path(ns.alias_seed) if ns.alias_seed else None,
                 Path(ns.rolling) if ns.rolling else None)
    Path(ns.out).write_text(text, encoding="utf-8")
    print(json.dumps({"out": ns.out, "chars": len(text)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
