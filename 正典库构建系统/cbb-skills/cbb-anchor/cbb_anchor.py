# -*- coding: utf-8 -*-
"""cbb_anchor.py — CBB P1 锚点树+时间归一化辅助（M1 骨架）

铁纪律（Step 0 结论）：
1. 伪锚点 = 2000-01-01 + i 天（i=章序 0-based），保序不冒充真实日期；
2. 禁墙钟——本模块不调用 datetime.now/today，一切时间值由章序与锚点树推导（单测静态+功能双检）；
3. 挂不上锚的相对时间显式标记（missing_anchor / ambiguous_reference / unresolved_time），绝不猜。
人工前置：锚点 status 默认 provisional，升 confirmed 必须由人改判（技能只辅助）。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "contracts"))
import cbb_contracts  # noqa: E402  契约校验（跨层唯一接口）

PSEUDO_ORIGIN = date(2000, 1, 1)  # 叙事伪锚点原点（Step 0 定案）
PRECISIONS = ("day", "month", "season", "year")
QUARANTINE_FLAGS = ("missing_anchor", "ambiguous_reference", "unresolved_time")
THREE_STATE_SINKS = ("confirmed", "provisional", "quarantine")

_CN_DIGIT = {"零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
             "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}


def cn_num(s: str):
    """中文/阿拉伯数字 → int；'半'→0.5；解析不了返回 None。支持到百位（含 零 填充）。"""
    s = s.strip()
    if s.isdigit():
        return int(s)
    if s == "半":
        return 0.5
    if s == "零":
        return 0
    if not s or any(ch not in _CN_DIGIT and ch not in "十百" for ch in s):
        return None
    core = s.replace("零", "")  # 一百零三 → 一百三
    total, num = 0, 0
    for ch in core:
        if ch in _CN_DIGIT:
            num = _CN_DIGIT[ch]
        elif ch == "十":
            total += (num or 1) * 10
            num = 0
        elif ch == "百":
            total += (num or 1) * 100
            num = 0
    return total + num


def pseudo_anchor(i: int) -> date:
    """章序 i（0-based）→ 伪锚点日期。纯函数，无墙钟。"""
    return PSEUDO_ORIGIN + timedelta(days=i)


def story_date(day_offset: int) -> date:
    return PSEUDO_ORIGIN + timedelta(days=day_offset)


def make_anchor_record(chapter_no: int, order_index: int, vol: int = 1,
                       status: str = "provisional") -> dict:
    """伪锚点候选 → 契约 Record（record_type=anchor）。status 升 confirmed 由人工改判。"""
    rec = {
        "record_id": f"anchor-v{vol:02d}c{chapter_no:04d}",
        "record_type": "anchor",
        "library": "timeline",
        "status": status,
        "canonical": {
            "label": f"第{chapter_no}章伪锚点",
            "kind": "pseudo",
            "day_offset": order_index,
            "pseudo_date": story_date(order_index).isoformat(),
            "precision": "day",
            "chapter_ref": chapter_no,
            "parent_anchor": None,
        },
        "evidence": [{
            "vol": vol, "chapter": chapter_no, "line": 0,
            "quote": f"<<<CHAPTER {chapter_no:04d} | …>>>",  # 伪锚点证据=章序标记（不自充故事内证据）
        }],
        "provenance": {
            "extractor_confidence": 1.0,
            "gate_trace": [],
            "precedent_refs": [],
            "status_history": [],
        },
        "version": 1,
        "supersedes": None,
    }
    cbb_contracts.validate_record(rec)
    return rec


def build_pseudo_tree(chapters_in_reading_order, vol: int = 1, version: int = 1) -> dict:
    """章号列表（阅读序）→ 锚点树。day_offset = 阅读序位置（伪锚点只保序）。"""
    anchors = [make_anchor_record(ch, i, vol=vol) for i, ch in enumerate(chapters_in_reading_order)]
    return {
        "kind": "cbb-anchor-tree",
        "version": version,
        "vol": vol,
        "anchors": anchors,
        "note": "伪锚点保序不冒充真实日期；升 confirmed 由人工改判（B2 人工前置）",
    }


# ---- 相对时间归一化（挂不上显式标记，绝不猜） ----

_RE_DAYS = re.compile(r"^([0-9零一二两三四五六七八九十百半]+)天后?$")
_RE_NEXTDAY = re.compile(r"^(次日|第二天|翌日)$")
_RE_SAMEDAY = re.compile(r"^(当天|当晚|今夜|当夜)$")
_RE_MONTHS = re.compile(r"^([0-9零一二两三四五六七八九十百半]+)个?月后$")
_RE_YEARS = re.compile(r"^([0-9零一二两三四五六七八九十百半]+)年后来?$")
_RE_NEXTYEAR = re.compile(r"^(次年|第二年|翌年)$")
_RE_SEASON = re.compile(r"^(那年|今年|次年)?(春|夏|秋|冬)(天|季)?$")
_RE_AMBIG = re.compile(r"^(那天|当时|此时|此刻)$")
_RE_FUZZY = re.compile(r"^(数日|几天|数个?月|几年)(之?后)$")


def normalize_relative(expr: str, context_anchor: dict | None) -> dict:
    """相对表述 + 上下文锚 → 归一化结果。

    context_anchor: 锚点 Record.canonical（含 day_offset/precision）或 None。
    返回 {raw, anchored, precision, day_offset|None, flags[], anchor_id|None}。
    三种显式隔离标记：missing_anchor（无锚可挂）/ ambiguous_reference（指代不明）/
    unresolved_time（模糊量词或不可解析）——对应 cbb-quarantine 分组入口。
    """
    expr = expr.strip()
    base = {
        "raw": expr, "anchored": False, "precision": None,
        "day_offset": None, "flags": [], "anchor_id": None,
    }
    if context_anchor is None:
        base["flags"].append("missing_anchor")
        return base
    off = context_anchor.get("day_offset")
    if not isinstance(off, int):
        base["flags"].append("missing_anchor")
        return base
    base["anchor_id"] = context_anchor.get("anchor_id") or context_anchor.get("label")

    if _RE_NEXTDAY.match(expr):
        base.update(anchored=True, precision="day", day_offset=off + 1)
    elif _RE_SAMEDAY.match(expr):
        base.update(anchored=True, precision="day", day_offset=off)
    elif (m := _RE_DAYS.match(expr)):
        n = cn_num(m.group(1))
        if n is None or not isinstance(n, int):
            base["flags"].append("unresolved_time")
        else:
            base.update(anchored=True, precision="day", day_offset=off + n)
    elif (m := _RE_MONTHS.match(expr)):
        n = cn_num(m.group(1))
        if n is None:
            base["flags"].append("unresolved_time")
        else:
            if n == 0.5:  # 半年后 = 6 个月（唯一定约换算，其余月粒度不折天）
                n = 6
            base.update(anchored=True, precision="month", month_delta=n)  # 月粒度不折天（保守）
    elif (m := _RE_YEARS.match(expr)):
        n = cn_num(m.group(1))
        if n is None or not isinstance(n, int):
            if n == 0.5:  # 半年后 = 6 个月（唯一定约换算，月粒度）
                base.update(anchored=True, precision="month", month_delta=6)
            else:
                base["flags"].append("unresolved_time")
        else:
            base.update(anchored=True, precision="year", year_delta=n)
    elif _RE_NEXTYEAR.match(expr):
        base.update(anchored=True, precision="year", year_delta=1)
    elif _RE_SEASON.match(expr):
        base.update(anchored=True, precision="season", season=_RE_SEASON.match(expr).group(2))
    elif _RE_AMBIG.match(expr):
        base["flags"].append("ambiguous_reference")  # 指代不明：需话语指代消解，M1 不猜
    elif _RE_FUZZY.match(expr):
        base["flags"].append("unresolved_time")  # 模糊量词：显式隔离待人裁
    else:
        base["flags"].append("unresolved_time")
    return base


def compare_story_time(a: dict, b: dict):
    """两个归一化时间比先后。仅当双方 day 精度可比时返回 -1/0/1；否则 None（保守不判）。
    门1 的 G1-TIME_INVERSION 只消费确定结论——粗精度宁缺毋滥（B1）。"""
    if a.get("precision") == "day" and b.get("precision") == "day":
        da, db = a.get("day_offset"), b.get("day_offset")
        if isinstance(da, int) and isinstance(db, int):
            return (da > db) - (da < db)
    return None


# ---- 树落盘/读取（版本化：修订=新版本新文件，永不覆盖） ----

def save_tree(tree: dict, tree_dir: Path):
    tree_dir = Path(tree_dir)
    tree_dir.mkdir(parents=True, exist_ok=True)
    path = tree_dir / f"anchor-tree.v{tree['version']}.json"
    if path.exists():
        return path, False  # 幂等：同版本已存在即跳过
    path.write_text(json.dumps(tree, ensure_ascii=False, sort_keys=True, indent=1),
                    encoding="utf-8")
    return path, True


def load_latest_tree(tree_dir: Path):
    tree_dir = Path(tree_dir)
    if not tree_dir.exists():
        return None
    versions = sorted(p for p in tree_dir.glob("anchor-tree.v*.json"))
    if not versions:
        return None
    return json.loads(versions[-1].read_text(encoding="utf-8"))


def three_state_write_stub(record: dict, out_root: Path, status: str):
    """三态写入桩（M1）：与 cbb-coordinate 同纪律——三池分目录、ID 命名、已存在即跳过。
    P2 由 cbb-store 接管（锚点树的 confirmed 升级也走人裁通道）。"""
    if status not in THREE_STATE_SINKS:
        raise ValueError(f"非法三态 {status!r}")
    rid = record.get("record_id") or record.get("block_id")
    if not rid:
        raise ValueError("record 缺 record_id/block_id")
    sink = Path(out_root) / status
    sink.mkdir(parents=True, exist_ok=True)
    path = sink / f"{rid}.json"
    if path.exists():
        return path, False
    path.write_text(json.dumps(record, ensure_ascii=False, sort_keys=True, indent=1),
                    encoding="utf-8")
    return path, True


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="CBB P1 锚点树辅助（M1 骨架）")
    ap.add_argument("--chapters", required=True,
                    help="章号列表（阅读序），如 14,38,114")
    ap.add_argument("--tree-dir", default=str(Path(__file__).resolve().parent / "trees"))
    ap.add_argument("--vol", type=int, default=1)
    ap.add_argument("--version", type=int, default=1)
    args = ap.parse_args(argv)
    chapters = [int(x) for x in args.chapters.split(",") if x.strip()]
    tree = build_pseudo_tree(chapters, vol=args.vol, version=args.version)
    path, created = save_tree(tree, Path(args.tree_dir))
    print(f"[anchor] anchors={len(tree['anchors'])} file={path.name} created={created} "
          f"origin={PSEUDO_ORIGIN.isoformat()}(+i天伪锚点,禁墙钟)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
