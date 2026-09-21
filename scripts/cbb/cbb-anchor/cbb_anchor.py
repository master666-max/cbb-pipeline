# -*- coding: utf-8 -*-
"""cbb_anchor.py — CBB 锚点树+双时间轴系统（本体版 v2）

铁纪律（Step 0 结论，保留）：
1. 伪锚点 = 2000-01-01 + i 天（i=摄入序 0-based），保序不冒充真实日期；
2. 禁墙钟——本模块不调用 datetime.now/today，一切时间值由摄入序与锚点推导（单测静态+功能双检）；
3. 挂不上锚的相对时间显式标记（missing_anchor / ambiguous_reference / unresolved_time），绝不猜。

v2 双时间轴模型（U-B03 重构，第一对照项=neuro-book 双轴设计，转述自
全量构筑版-分析报告/neuro-book.md §2，零源码接触）：
  - tick   摄入序/叙事推进序（transaction time）：宿主发放全序整数，**永远单调**，
           知识边界权威，必填；
  - instant 故事时间（valid time）：自世界原点的天数偏移，由人读时间串解析；
           **可回退**——倒叙/插叙/回忆章 tick 递增而 instant 后退，这正是必须双轴的原因；可空；
  - time   人读原文：verbatim 保留，**不可比较、不参与排序**（伪锚点禁令的正面表述）。
  - as-of 双查询语义：as_of_tick=知识边界（叙事推进到这里时知道多少）/
    as_of_instant=世界状态（故事时间这一刻世界什么样）/双轴 AND/双空=全知；
  - **缺坐标判不可见**：instant 缺失的条目对 as_of_instant 查询不可见——宁可漏召回不可泄漏。
吸收：倒计时到点兑现（chinese-webnovel 伏笔台账到期提醒）；
      章号轴时序回放作 instant 缺失时的降级方案（webnovel）。
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
    """摄入序 i（0-based）→ 伪锚点日期。纯函数，无墙钟。"""
    return PSEUDO_ORIGIN + timedelta(days=i)


def story_date(day_offset: int) -> date:
    return PSEUDO_ORIGIN + timedelta(days=day_offset)


def make_anchor_record(chapter_no: int, order_index: int, vol: int = 1,
                       status: str = "provisional", verified_against: dict | None = None) -> dict:
    """伪锚点候选 → 契约 Record v2.0（record_type=anchor）。

    canonical 双时间轴字段：tick=order_index（摄入序，单调）；instant=None（伪锚点
    不自充故事时间——真故事时间由人读时间串解析另行挂接）。
    verified_against：契约 v2.0 溯源三件套（path+sha+verified_at），由调用方传入
    （值来自管线输入快照，非本模块时钟——禁墙钟纪律不破）。status 升 confirmed 由人工改判。"""
    canonical = {
        "label": f"第{chapter_no}章伪锚点",
        "kind": "pseudo",
        "tick": order_index,
        "instant": None,
        "day_offset": order_index,        # v1 兼容位：伪锚点展示用（=tick）
        "pseudo_date": story_date(order_index).isoformat(),
        "precision": "day",
        "chapter_ref": chapter_no,
        "parent_anchor": None,
    }
    rec = {
        "record_id": f"anchor-v{vol:02d}c{chapter_no:04d}",
        "record_type": "anchor",
        "library": "timeline",
        "status": status,
        "canonical": canonical,
        "evidence": [{
            "vol": vol, "chapter": chapter_no, "line": 0,
            "quote": f"<<<CHAPTER {chapter_no:04d} | …>>>",  # 伪锚点证据=章序标记（不自充故事内证据）
        }],
        "verified_against": verified_against or {
            "path": f"vol{vol:02d}/manifest", "sha": "0" * 7, "verified_at": "1970-01-01",
        },  # 调用方未提供时的占位三件套（测试/骨架场景；生产管线应传真实快照）
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


def build_pseudo_tree(chapters_in_reading_order, vol: int = 1, version: int = 1,
                      verified_against: dict | None = None) -> dict:
    """章号列表（摄入序）→ 锚点树。tick = 摄入序位置（伪锚点只保序）。"""
    anchors = [make_anchor_record(ch, i, vol=vol, verified_against=verified_against)
               for i, ch in enumerate(chapters_in_reading_order)]
    return {
        "kind": "cbb-anchor-tree",
        "version": version,
        "vol": vol,
        "axes": ["tick", "instant", "time"],
        "anchors": anchors,
        "note": "伪锚点保序不冒充真实日期；升 confirmed 由人工改判（B2 人工前置）",
    }


# ---- 相对时间归一化（挂不上显式标记，绝不猜；18 条精度抽检电池的判定面） ----

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

    context_anchor: 锚点 canonical（含 tick/day_offset/precision）或 None。
    返回 {raw, anchored, precision, day_offset|None, flags[], anchor_id|None}。
    day_offset 在 v2 语义中即 **instant**（故事时间偏移）——v1 保留面原样，v2 由
    instant_from_relative() 消费转挂。
    三种显式隔离标记：missing_anchor / ambiguous_reference / unresolved_time——
    对应 cbb-quarantine 分组入口。
    """
    expr = expr.strip()
    base = {
        "raw": expr, "anchored": False, "precision": None,
        "day_offset": None, "flags": [], "anchor_id": None,
    }
    if context_anchor is None:
        base["flags"].append("missing_anchor")
        return base
    off = context_anchor.get("day_offset", context_anchor.get("tick"))
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
        base["flags"].append("ambiguous_reference")  # 指代不明：需话语指代消解，不猜
    elif _RE_FUZZY.match(expr):
        base["flags"].append("unresolved_time")  # 模糊量词：显式隔离待人裁
    else:
        base["flags"].append("unresolved_time")
    return base


def instant_from_relative(expr: str, context_anchor: dict | None) -> dict:
    """人读时间串 → instant（自研核心入口，16 仓无现成）。

    消费 normalize_relative（18 条电池判定面不变）：day 精度 anchored → instant=day_offset；
    其余精度/标记 → instant=None（粗精度不折天不冒充 instant，宁缺毋滥）。
    返回 {instant, precision, flags, time}——time=原文 verbatim（不可比较不参与排序）。
    """
    got = normalize_relative(expr, context_anchor)
    instant = got["day_offset"] if (got["anchored"] and got.get("precision") == "day") else None
    return {"instant": instant, "precision": got["precision"], "flags": got["flags"],
            "time": expr.strip()}


def compare_story_time(a: dict, b: dict):
    """两个归一化时间比先后。仅当双方 day 精度可比时返回 -1/0/1；否则 None（保守不判）。
    门1 的 G1-TIME_INVERSION 只消费确定结论——粗精度宁缺毋滥（B1）。"""
    if a.get("precision") == "day" and b.get("precision") == "day":
        da, db = a.get("day_offset"), b.get("day_offset")
        if isinstance(da, int) and isinstance(db, int):
            return (da > db) - (da < db)
    return None


# ---- 双时间轴（tick / instant / time） ----

def make_entry(entry_id: str, tick: int, instant: int | None = None,
               time: str | None = None, **extra) -> dict:
    """时间线条目：tick 必填（摄入序）；instant 可空（故事时间可回退）；
    time 人读原文（不可比较不参与排序，仅 verbatim 保留）。"""
    if not isinstance(tick, int) or isinstance(tick, bool) or tick < 0:
        raise ValueError(f"tick 须为非负整数，实为 {tick!r}")
    if instant is not None and (not isinstance(instant, int) or isinstance(instant, bool)):
        raise ValueError(f"instant 须为整数或 None，实为 {instant!r}")
    e = {"entry_id": entry_id, "tick": tick, "instant": instant, "time": time}
    e.update(extra)
    return e


def build_timeline(entries: list[dict]) -> list[dict]:
    """时间线构建：tick 永远单调（摄入序纪律）——非递增 tick 直接拒绝；
    instant 无单调约束（倒叙/插叙/回忆：tick 递增而 instant 后退是合法且预期的）。"""
    out = []
    last_tick = None
    for raw in entries:
        e = dict(raw)
        if "tick" not in e or not isinstance(e["tick"], int):
            raise ValueError(f"条目缺合法 tick：{e.get('entry_id')!r}")
        if last_tick is not None and e["tick"] <= last_tick:
            raise ValueError(f"tick 必须严格递增（摄入序单调）：{e['entry_id']} tick={e['tick']} ≤ 前值 {last_tick}")
        out.append(e)
        last_tick = e["tick"]
    return out


def asof(entries: list[dict], as_of_tick: int | None = None,
         as_of_instant: int | None = None) -> list[dict]:
    """as-of 双查询语义（双时间轴的核心查询面）。

    - as_of_tick：知识边界——叙事推进到该 tick 时已摄入的条目（tick <= as_of_tick）；
    - as_of_instant：世界状态——故事时间该刻已发生的条目（instant <= as_of_instant）；
      **缺坐标判不可见**：instant 为 None 的条目不返回（宁可漏召回不可泄漏）；
    - 双给：AND；双空：全知（全部条目）。
    """
    out = []
    for e in entries:
        if as_of_tick is not None and not (e["tick"] <= as_of_tick):
            continue
        if as_of_instant is not None:
            if e.get("instant") is None or not (e["instant"] <= as_of_instant):
                continue  # 缺坐标不可见
        out.append(e)
    return out


def story_order(entries: list[dict]) -> list[dict]:
    """故事序视图：按 instant 升序重组（倒叙还原）；instant 缺失条目沉底保持 tick 序。
    只读视图——永不改写条目 tick/instant（tick 单调纪律的查询侧镜像）。"""
    with_i = [e for e in entries if e.get("instant") is not None]
    without = [e for e in entries if e.get("instant") is None]
    return sorted(with_i, key=lambda e: (e["instant"], e["tick"])) + without


def replay(entries: list[dict], upto_tick: int | None = None) -> list[dict]:
    """章号轴时序回放（webnovel 吸收：instant 缺失时的降级方案）。

    按摄入序（tick）回放叙事——无论 instant 是否齐全，章号轴永远可用；
    条目自带 instant 时作为注记展示，缺失不影响回放次序。"""
    seq = [e for e in entries if upto_tick is None or e["tick"] <= upto_tick]
    return sorted(seq, key=lambda e: e["tick"])


# ---- 倒计时到点兑现（chinese-webnovel 伏笔台账到期提醒的判定原语） ----

def countdowns_due(countdowns: list[dict], at_tick: int) -> list[dict]:
    """到期判定：{key, due_tick, resolved_tick|None} 列表 × 当前 tick →
    未兑现且 due_tick <= at_tick 的项（到点必须兑现——超期即浮出，供 quarantine 🔴 消费）。"""
    return [c for c in countdowns
            if c.get("resolved_tick") is None and c.get("due_tick") is not None
            and c["due_tick"] <= at_tick]


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


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="CBB 锚点树+双时间轴（本体版 v2）")
    ap.add_argument("--chapters", default=None, help="章号列表（摄入序），如 14,38,114")
    ap.add_argument("--tree-dir", default=str(Path(__file__).resolve().parent / "trees"))
    ap.add_argument("--vol", type=int, default=1)
    ap.add_argument("--version", type=int, default=1)
    args = ap.parse_args(argv)
    if not args.chapters:
        print("FATAL: 需要 --chapters", file=sys.stderr)
        return 2
    chapters = [int(x) for x in args.chapters.split(",") if x.strip()]
    tree = build_pseudo_tree(chapters, vol=args.vol, version=args.version)
    path, created = save_tree(tree, Path(args.tree_dir))
    print(f"[anchor] axes=tick/instant/time anchors={len(tree['anchors'])} "
          f"file={path.name} created={created} origin={PSEUDO_ORIGIN.isoformat()}(+i天伪锚点,禁墙钟)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
