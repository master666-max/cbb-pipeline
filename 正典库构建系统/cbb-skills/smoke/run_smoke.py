# -*- coding: utf-8 -*-
"""run_smoke.py — CBB P1-M1 六技能集成冒烟（U7）

链路：coordinate → anchor → extract(stub,R6) → gate1 → quarantine → store。
样本 = fixtures/mini-corpus.txt（2 故事章 + 1 元文本章）+ 1 条植入坏件（悬空 quote）。
纪律：全程离线确定性（无 LLM/网络/墙钟）；所有落盘 skip-if-exists → 重跑幂等，
二次运行不产生新文件（幂等性本身是断言项之一）。
退出码 0 = 全部检查通过。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILLS = HERE.parent
for mod in ("contracts", "cbb-coordinate", "cbb-anchor", "cbb-extract",
            "cbb-gate1", "cbb-quarantine", "cbb-store"):
    sys.path.insert(0, str(SKILLS / mod))

import cbb_coordinate  # noqa: E402
import cbb_anchor  # noqa: E402
import cbb_extract  # noqa: E402
import cbb_gate1  # noqa: E402
from cbb_quarantine import QuarantineZone  # noqa: E402
from cbb_store import ThreeStateStore, route_by_confidence  # noqa: E402

OUT = HERE / "out"
FAILURES: list[str] = []
TOTAL = 0


def check(label: str, cond: bool, detail: str = "") -> None:
    global TOTAL
    TOTAL += 1
    mark = "PASS" if cond else "FAIL"
    print(f"  [{mark}] {label}" + (f"  {detail}" if detail and not cond else ""))
    if not cond:
        FAILURES.append(f"{label}: {detail}")


def main() -> int:
    print("== CBB P1-M1 六技能集成冒烟 ==")
    fixture = HERE / "fixtures" / "mini-corpus.txt"
    OUT.mkdir(parents=True, exist_ok=True)

    # ---- ① cbb-coordinate：坐标+幂等缓存 ----
    print("[1/6] cbb-coordinate")
    m1 = cbb_coordinate.process_file(fixture, OUT / "cache")
    m2 = cbb_coordinate.process_file(fixture, OUT / "cache")
    check("三章解析", m1["chapter_count"] == 3, f"got {m1['chapter_count']}")
    check("二次运行缓存命中（幂等）", m2["cache_hit"] is True)
    check("块数=3（每章一非空段簇）", m1["block_count"] == 3, f"got {m1['block_count']}")
    blocks, titles = m1["blocks"], {c["chapter"]: c["title"] for c in m1["chapters"]}

    # ---- ② cbb-anchor：伪锚点树+相对时间 ----
    print("[2/6] cbb-anchor")
    reading_order = [c["chapter"] for c in m1["chapters"]]  # 文件序=阅读序 [14,38,1]
    tree = cbb_anchor.build_pseudo_tree(reading_order)
    tree_path, _ = cbb_anchor.save_tree(tree, OUT / "trees")
    offsets = [a["canonical"]["day_offset"] for a in tree["anchors"]]
    check("锚点树阅读序保序", offsets == [0, 1, 2], f"got {offsets}")
    anchor_38 = tree["anchors"][1]["canonical"]
    norm_ok = cbb_anchor.normalize_relative("三天后", anchor_38)
    norm_no_ctx = cbb_anchor.normalize_relative("次日", None)
    norm_ambig = cbb_anchor.normalize_relative("那天", anchor_38)
    check("「三天后」挂锚 day=4", norm_ok["anchored"] and norm_ok["day_offset"] == 4,
          f"got {norm_ok}")
    check("无锚显式标记 missing_anchor", "missing_anchor" in norm_no_ctx["flags"])
    check("指代不明显式标记 ambiguous_reference", "ambiguous_reference" in norm_ambig["flags"])

    # ---- ③ cbb-extract（stub 模式，R6 标配） ----
    print("[3/6] cbb-extract (stub, R6 builtin)")
    cands = cbb_extract.extract_stub(blocks, lexicon=["缇达", "迷宫"],
                                     event_patterns=["拔出了剑", "踏入迷宫"],
                                     chapter_titles=titles)
    from_story = [c for c in cands if c["evidence"][0]["chapter"] in (14, 38)]
    from_meta = [c for c in cands if c["evidence"][0]["chapter"] == 1]
    check("故事章候选产出", len(from_story) == 6, f"got {len(from_story)}")
    check("元文本章零抽取（R6 stub 闸）", len(from_meta) == 0, f"got {len(from_meta)}")
    check("候选全部契约合规(candidate 态)",
          all(c["status"] == "candidate" for c in cands))
    # 植入坏件：悬空 quote
    planted = cbb_extract.make_candidate(
        "entity", {"name": "幽灵"},
        evidence=[{"vol": 1, "chapter": 14, "line": 99, "quote": "根本不存在的引文"}],
        confidence=0.9)
    batch = cands + [planted]

    # ---- ④ cbb-gate1：确定性四校验 ----
    print("[4/6] cbb-gate1")
    g = cbb_gate1.check_batch(batch, {"blocks": blocks, "known_ids": set()})
    check("好件全放行", g["summary"]["pass"] == len(cands),
          f"pass={g['summary']['pass']} want={len(cands)}")
    check("植入坏件被拦", g["summary"]["intercept"] == 1
          and g["summary"]["by_code"]["G1-EVIDENCE"] == 1,
          f"summary={g['summary']}")

    # ---- ⑤ cbb-quarantine：登记（门1拦截件+锚定失败件）+报告 ----
    print("[5/6] cbb-quarantine")
    zone = QuarantineZone(OUT / "quarantine-zone")
    for it in g["intercepted"]:
        zone.register(it["check"]["quarantine_group"],
                      detail="; ".join(v["detail"] for v in it["check"]["violations"]),
                      record_id=it["record"].get("record_id"),
                      source="cbb-gate1",
                      blocks=[c["record_id"] for c in cands[:2]])
    cand_ids = [c["record_id"] for c in cands]
    zone.register("missing_anchor", detail="「次日」无锚可挂（mini 冒烟）",
                  source="cbb-anchor", blocks=cand_ids)
    zone.register("ambiguous_reference", detail="「那天」指代不明（mini 冒烟）",
                  source="cbb-anchor", blocks=cand_ids[:1])
    report = zone.report_markdown()
    (OUT / "quarantine-report.md").write_text(report, encoding="utf-8")
    check("报告含「请你确认」（第一产出）", "请你确认" in report)
    check("阻塞计数降序（缺锚 6 阻塞居首）",
          report.index("阻塞下游 6 项") < report.index("阻塞下游 2 项"),
          report[:200])

    # ---- ⑥ cbb-store：三态路由+人工晋升+版本化 ----
    print("[6/6] cbb-store")
    store = ThreeStateStore(OUT / "kb")
    entity0 = next(c for c in cands if c["record_type"] == "entity")
    # 置信度路由纪律展示：stub 置信度 0.8/0.6 < τ_provisional → 全部只配 quarantine
    routes = {route_by_confidence(c["provenance"]["extractor_confidence"]) for c in cands}
    check("置信度路由：低置信只配隔离", routes == {"quarantine"}, f"got {routes}")
    # 人工通道演示：确认一条实体入 provisional → 人工晋升 confirmed → 修订 supersede v2
    # （幂等口径：created 仅首次为 True，断言看落盘与内容，不看首次标志）
    p1, c1 = store.admit(entity0, "provisional",
                         gate_trace_entry={"gate": "1", "verdict_id": "g1-smoke"})
    stored1 = json.loads(p1.read_text(encoding="utf-8")) if p1.exists() else {}
    check("人工确认入 provisional（在库且态正确）",
          p1.exists() and stored1.get("status") == "provisional"
          and stored1.get("provenance", {}).get("gate_trace"), f"created={c1}")
    entry = store.status_transition(entity0["record_id"], "confirmed",
                                    by="human", note="冒烟人工复核")
    check("人工晋升 confirmed（旁车）", entry["to"] == "confirmed"
          and store.effective_status(entity0["record_id"]) == "confirmed")
    v2 = dict(entity0, record_id=entity0["record_id"] + "-v2",
              canonical={"name": "缇达", "mention_kind": "lexicon-hit", "rev": "修订"})
    p2, c2 = store.supersede(entity0["record_id"], v2)
    latest = store.resolve_latest(entity0["record_id"])
    check("supersede 版本化 v2+链可追", p2.exists() and latest is not None
          and latest["version"] == 2 and latest["supersedes"] == entity0["record_id"],
          f"created={c2}")
    stats = store.stats()
    check("库统计 character/provisional=2（实体原件+修订件）",
          stats["libraries"].get("character", {}).get("provisional") == 2, f"got {stats}")
    check("隔离区待裁决 ≥3", len(zone.pending()) >= 3, f"got {len(zone.pending())}")

    # ---- 汇总 ----
    print(f"\n== SMOKE {'PASS' if not FAILURES else 'FAIL'} "
          f"({len(FAILURES)} 失败 / {TOTAL} 项) ==")
    if FAILURES:
        for f in FAILURES:
            print(f"  ✗ {f}")
        return 1
    (OUT / "smoke-summary.json").write_text(json.dumps({
        "status": "PASS", "chapters": m1["chapter_count"],
        "candidates": len(cands), "gate_pass": g["summary"]["pass"],
        "gate_intercept": g["summary"]["intercept"],
        "quarantine_pending": len(zone.pending()),
        "store_stats": stats,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
