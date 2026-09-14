# -*- coding: utf-8 -*-
"""cbb_extract.py — CBB P2 最小版抽取器（M1 骨架）

只抽 event/entity 两类；每条候选强制带证据四元组（B4）。
R6 元文本规则内置为生产标配常量（逐字照抄 Step 0 Tier2 已验证文本）。
stub 模式 = 离线确定性规则抽取（词典/关键词驱动，供单测与冒烟）；
graphiti 模式 = 参数组装器（伪锚点 reference_time + R6 注入），完整管道复用 Tier2 脚本。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "contracts"))
import cbb_contracts  # noqa: E402

# ---- R6 元文本规则（生产标配，逐字照抄 Step0 Tier2 run_tier2_pipeline.py，勿改动措辞） ----
R6_CUSTOM_EXTRACTION_INSTRUCTIONS = """领域规则（中文小说《迷深》正典库构建）：
1) 元文本（作者杂谈/翻译组公告/论坛吐槽/现实日期/话数卷数/平台与作品名）一律不得抽取任何实体或关系；
2) 无专名但固定出场且有关键行为的职务称呼（如店长）应抽取为实体；
3) 专有名词（人名/地名/魔法名/道具名）保留原文写法，不翻译不改写；
4) 信件/传闻/指控中的声称按文本事实抽取，并在 fact 中标注'据某某声称'。"""

# stub 模式元文本启发式（M1 简版词表；真实路径防线=R6 指令注入，已由 Tier2 验证）
METATEXT_TITLE_PATTERNS = (
    "推荐事先阅读", "新人观众", "公告", "作者的话", "杂谈", "后记", "悬赏", "加更说明",
    "请假", "上架感言", "完本感言",
)
METATEXT_BODY_PATTERNS = (
    "翻译：", "校对：", "转载请注明", "本章说", "评论区", "点赞", "收藏", "月票",
)

LIBRARY_OF_TYPE = {"event": "event", "entity": "character"}  # P1 只承诺两库
THREE_STATE_SINKS = ("confirmed", "provisional", "quarantine")


def is_metatext(title: str = "", text_sample: str = "") -> bool:
    """确定性启发式：标题或正文抽样命中元文本特征 → 整章跳过（stub 第一道闸）。"""
    for pat in METATEXT_TITLE_PATTERNS:
        if pat in (title or ""):
            return True
    for pat in METATEXT_BODY_PATTERNS:
        if pat in (text_sample or ""):
            return True
    return False


def _short_hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True)
                          .encode("utf-8")).hexdigest()[:12]


def make_candidate(record_type: str, canonical: dict, evidence: list[dict],
                   confidence: float, extractor: str = "stub-v1") -> dict:
    """构造契约合规的 candidate 记录（入库前态）。record_id 由内容哈希决定→重跑幂等。"""
    if record_type not in ("event", "entity"):
        raise ValueError(f"M1 只抽 event/entity，拒绝 {record_type!r}")
    for ev in evidence:
        if not cbb_contracts.evidence_ok(ev):
            raise ValueError(f"证据四元组不完整: {ev!r}")  # B4：无证据不入库
    rec = {
        "record_id": f"cand-{record_type}-{_short_hash({'c': canonical, 'e': evidence})}",
        "record_type": record_type,
        "library": LIBRARY_OF_TYPE[record_type],
        "status": "candidate",
        "canonical": canonical,
        "evidence": evidence,
        "provenance": {
            "extractor_confidence": confidence,
            "extractor": extractor,
            "gate_trace": [],
            "precedent_refs": [],
            "status_history": [],
        },
        "version": 1,
        "supersedes": None,
    }
    cbb_contracts.validate_record(rec, allow_candidate=True)
    return rec


def _find_line(block: dict, term: str):
    """块内定位 term 首次出现的物理行号（章内 1-based）。"""
    for k, ln in enumerate(block["text"].split("\n")):
        if term in ln:
            return block["line_start"] + k, ln.strip()
    return None, None


def extract_stub(blocks: list[dict], lexicon=None, event_patterns=None,
                 chapter_titles: dict | None = None) -> list[dict]:
    """stub 确定性抽取：词典实体 + 关键词事件。元文本章整章跳过（is_metatext）。

    blocks: cbb_coordinate.coordinate()['blocks']（或 manifest 同字段）
    lexicon: 实体词典（如角色清单）——命中即候选，evidence=实际物理行
    event_patterns: 事件关键词——命中行即事件候选
    返回 candidate 列表（每提及一条，实体消歧归 P3 Canonicalizer）。
    """
    lexicon = lexicon or []
    event_patterns = event_patterns or []
    chapter_titles = chapter_titles or {}
    out: list[dict] = []
    for block in blocks:
        title = chapter_titles.get(block.get("chapter"), "")
        if is_metatext(title=title, text_sample=block["text"]):
            continue  # R6 对应的 stub 闸：元文本零抽取
        for name in lexicon:
            line_no, _ = _find_line(block, name)
            if line_no is None:
                continue
            out.append(make_candidate(
                "entity",
                canonical={"name": name, "mention_kind": "lexicon-hit"},
                evidence=[{"vol": block["vol"], "chapter": block["chapter"],
                           "line": line_no, "quote": name}],
                confidence=0.80,
            ))
        for kw in event_patterns:
            line_no, quote = _find_line(block, kw)
            if line_no is None:
                continue
            out.append(make_candidate(
                "event",
                canonical={"name": quote[:30], "trigger": kw, "story_time": None},
                evidence=[{"vol": block["vol"], "chapter": block["chapter"],
                           "line": line_no, "quote": quote}],
                confidence=0.60,
            ))
    # 去重：同一 record_id 只留一条（内容哈希幂等）
    seen, uniq = set(), []
    for rec in out:
        if rec["record_id"] not in seen:
            seen.add(rec["record_id"])
            uniq.append(rec)
    return uniq


# ---- graphiti 真实路径（P2 实装；M1 只提供已验证参数形态） ----

def build_episode_kwargs(order_index: int, episode_body: str, episode_name: str,
                         group_id: str, source_description: str) -> dict:
    """组装 graphiti add_episode 关键参数（Step0 Tier2 已验证形态）：
    reference_time = 伪锚点（2000-01-01+order_index 天，禁墙钟）；
    custom_extraction_instructions = R6 标配（元文本防御）。
    纯函数无副作用、不依赖 graphiti 安装；完整管道接线见
    P1执行区/step0-抽取精度实验/脚本/run_tier2_pipeline.py。
    """
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "cbb-anchor"))
    import cbb_anchor  # 延迟导入：伪锚点纪律单一事实源

    return {
        "name": episode_name,
        "episode_body": episode_body,
        "source_description": source_description,
        "reference_time": cbb_anchor.pseudo_anchor(order_index),
        "source": "text",  # graphiti EpisodeType.text（P2 接线时以枚举替换字面量）
        "group_id": group_id,
        "custom_extraction_instructions": R6_CUSTOM_EXTRACTION_INSTRUCTIONS,
    }


def run_graphiti_extraction(*_args, **_kwargs):  # pragma: no cover（P2 实装）
    raise NotImplementedError(
        "M1 骨架不含 graphiti 运行时。P2 接线复用 Step0 Tier2 已验证管道"
        "（venv312 + DeepSeek + LM Studio 嵌入 + Neo4j），参数经 build_episode_kwargs 组装。")


def env_probe() -> dict:
    """云 API/图库凭证探活（⑧纪律）：只探存在性布尔，绝不读值输出值（D-004）。"""
    import os
    return {"DEEPSEEK_API_KEY": bool(os.environ.get("DEEPSEEK_API_KEY")),
            "NEO4J_PASSWORD": bool(os.environ.get("NEO4J_PASSWORD"))}


def three_state_write_stub(record: dict, out_root: Path, status: str):
    """三态写入桩（M1）：三池分目录、ID 命名、已存在即跳过（与其他 cbb-* 同纪律）。"""
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
    ap = argparse.ArgumentParser(description="CBB P2 抽取器 stub 模式（M1 骨架）")
    ap.add_argument("--manifest", required=True, help="cbb-coordinate 产出的 manifest JSON")
    ap.add_argument("--lexicon", default="", help="实体词典，逗号分隔")
    ap.add_argument("--events", default="", help="事件关键词，逗号分隔")
    ap.add_argument("--out", default=None, help="候选记录 JSON 输出路径（可选）")
    ap.add_argument("--r6-check", action="store_true", help="只打印 R6 标配摘要并退出")
    args = ap.parse_args(argv)

    if args.r6_check:
        print(f"[extract] R6 标配已内置，{len(R6_CUSTOM_EXTRACTION_INSTRUCTIONS)} 字，"
              f"含元文本零抽取条款：{'一律不得抽取任何实体或关系' in R6_CUSTOM_EXTRACTION_INSTRUCTIONS}")
        return 0

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    titles = {c["chapter"]: c["title"] for c in manifest.get("chapters", [])}
    cands = extract_stub(
        manifest["blocks"],
        lexicon=[x for x in args.lexicon.split(",") if x.strip()],
        event_patterns=[x for x in args.events.split(",") if x.strip()],
        chapter_titles=titles,
    )
    payload = {"candidate_count": len(cands), "candidates": cands}
    if args.out:
        Path(args.out).write_text(json.dumps(payload, ensure_ascii=False, indent=1),
                                  encoding="utf-8")
    print(f"[extract] candidates={len(cands)} "
          f"(entities={sum(1 for c in cands if c['record_type'] == 'entity')}, "
          f"events={sum(1 for c in cands if c['record_type'] == 'event')}) "
          f"R6=内置标配")
    return 0


if __name__ == "__main__":
    sys.exit(main())
