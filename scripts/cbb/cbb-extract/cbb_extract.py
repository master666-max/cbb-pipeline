# -*- coding: utf-8 -*-
"""cbb_extract.py — CBB P2 抽取器（本体版 v2 · 四面防御）

四面防御（U-B04，R6 独有性经 16 仓复核确认——四层并配是 CBB 独有组合）：
  ①读入侧 R6 元文本规则（逐字照抄 Step0 Tier2 已验证文本，勿改动措辞）+ stub 元文本启发闸；
  ②输出侧禁词八类（worldbook 禁词剔除八类表：比喻转白描/万能修饰删/叙事禁词删/解释性描写删等，
    每类带确定性触发词表与处置动作）；
  ③模型侧防先验（"AI 已知信息不入档"：默认特征（黑发黑眼/尖耳/年轻）无原文证据即判先验补全，
    处置=以 // 原文未提及 占位，绝不默认填充）；
  ④安全侧注入防御（untrusted narrative text 条款：正文内嵌指令样模式检测→整块拒抽）。
吸收（U-A17 §3）：证据式抽取条款（每断言须原文引+章号）//原文未提及+反推标注；
  别名四分类（oh-story：proper_name 可合/nickname 须同指证据且置信≥0.85/descriptor·title 永不；
  存疑分开建——宁可分裂不可误合）；长篇施工参数（5-8 章/批新上下文+15KB/章→≤8K 回传→√N 合并+
  章节边界表单一切片真值）；机械硬检查（grep 计数不依赖自报）；编写前重读纪律（SKILL 条款）。
保留（v1.0）：stub 离线确定性抽取、record_id 内容哈希幂等、build_episode_kwargs
  （伪锚点 reference_time + R6 注入，Step0 Tier2 已验证形态）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "contracts"))
import cbb_contracts  # noqa: E402

# ---- ①读入侧：R6 元文本规则（生产标配，逐字照抄 Step0 Tier2 run_tier2_pipeline.py，勿改动措辞） ----
R6_CUSTOM_EXTRACTION_INSTRUCTIONS = """领域规则（中文小说《迷深》正典库构建）：
1) 元文本（作者杂谈/翻译组公告/论坛吐槽/现实日期/话数卷数/平台与作品名）一律不得抽取任何实体或关系；
2) 无专名但固定出场且有关键行为的职务称呼（如店长）应抽取为实体；
3) 专有名词（人名/地名/魔法名/道具名）保留原文写法，不翻译不改写；
4) 信件/传闻/指控中的声称按文本事实抽取，并在 fact 中标注'据某某声称'。"""

# stub 模式元文本启发式（真实路径防线=R6 指令注入，已由 Tier2 验证；stub 闸为同义确定性防线）
METATEXT_TITLE_PATTERNS = (
    "推荐事先阅读", "新人观众", "公告", "作者的话", "杂谈", "后记", "悬赏", "加更说明",
    "请假", "上架感言", "完本感言",
)
METATEXT_BODY_PATTERNS = (
    "翻译：", "校对：", "转载请注明", "本章说", "评论区", "点赞", "收藏", "月票",
)

# ---- ④安全侧：注入防御（untrusted narrative text——正文内嵌指令样模式→整块拒抽） ----
INSTRUCTION_INJECTION_PATTERNS = (
    "ignore previous", "ignore all previous", "disregard above", "忽略之前", "忽略以上",
    "请忽略上文", "system prompt", "系统提示词", "rm -rf", "<script", "```",
)

DEFAULT_TRAIT_NOT_MENTIONED = "// 原文未提及"  # ③模型侧占位（worldbook 四规则之一）
INFERENCE_MARK = "（反推）"                    # 行为反推性格标注（区分原文直接陈述）

# ---- ②输出侧：禁词八类（worldbook :373-387 框架；触发词表为本技能自建确定性词典） ----
# 处置动作：delete=删/不入档；transform=转写（白描/行为依据）；flag=标记待人工。
BANNED_EIGHT = {
    "metaphor": {"action": "transform", "desc": "意象比喻→特征白描",
                 "patterns": (r"(眸|瞳|眼|发|肤|声|嗓).{0,4}(如|似|若|像|仿佛|宛如|如同)",)},
    "universal_modifier": {"action": "delete", "desc": "万能修饰直接删（放任何角色都成立）",
                           "patterns": (r"(精致的|美丽的|俊美的|优雅的|神秘的|冷峻的|气质出众|无可挑剔)",)},
    "default_trait": {"action": "delete", "desc": "默认特征删（AI 数据库已有：黑发黑眼/尖耳/年轻）",
                      "patterns": (r"(黑发|黑眼|乌黑.{0,2}发|尖耳|年轻的|看起来.{0,3}岁)",)},
    "narrative_voice": {"action": "delete", "desc": "叙事禁词删（小说腔）",
                        "patterns": (r"(一丝|一缕|弧度|勾起嘴角|弯起嘴角|眸光|空气仿佛凝固)",)},
    "trait_label": {"action": "transform", "desc": "性格标签→原文具体行为依据",
                    "patterns": (r"^(温柔|冷酷|高冷|傲娇|腹黑|天然呆|病娇)$",)},
    "subjective": {"action": "delete", "desc": "主观评价删",
                   "patterns": (r"(绝美|惊艳|完美无瑕|无人能敌|天下第一)",)},
    "explanatory": {"action": "delete", "desc": "解释性描写删（只留动作）",
                    "patterns": (r"(体现了|表现出他的|说明了他|暗示着|这意味|这一动作)",)},
    "tone_modifier": {"action": "delete", "desc": "语气修饰删",
                      "patterns": (r"(似乎|好像|大概|或许|简直是|无疑)",)},
}
_BANNED_COMPILED = {k: tuple(re.compile(p) for p in v["patterns"])
                    for k, v in BANNED_EIGHT.items()}

# ---- 别名四分类（oh-story material-decomposition 规则层：定"能不能合"） ----
ALIAS_KINDS = ("proper_name", "nickname", "descriptor", "title")
ALIAS_MERGE_CONFIDENCE_GATE = 0.85

# ---- 长篇施工参数（oh-story 降维聚合——迷深 517 章直接可用） ----
CONSTRUCTION_PARAMS = {
    "batch_chapters": (5, 8),        # 每批 5-8 章（clamp）
    "batch_context": "fresh-subagent",  # 每批新上下文子代理（no accumulation）
    "chapter_budget_kb": 15,          # 章切片预算
    "return_budget_kb": 8,            # 回传预算（≤8K）
    "merge_rule": "sqrt(N)",          # √N 合并
    "chapter_boundary": "manifest-slice-truth",  # 章节边界以 cbb-coordinate manifest 切片为准（真值）
    "reread_before_write": True,      # 编写前重读对应章节（worldbook 纪律）
}

LIBRARY_OF_TYPE = {"event": "event", "entity": "character"}


# ---- ①读入侧 + ④安全侧：双闸 ----

def is_metatext(title: str = "", text_sample: str = "") -> bool:
    """确定性启发式：标题或正文抽样命中元文本特征 → 整章跳过（stub 第一道闸）。"""
    for pat in METATEXT_TITLE_PATTERNS:
        if pat in (title or ""):
            return True
    for pat in METATEXT_BODY_PATTERNS:
        if pat in (text_sample or ""):
            return True
    return False


def has_embedded_instruction(text_sample: str) -> bool:
    """④安全侧：正文内嵌指令样模式检测（untrusted narrative text 条款的 stub 实现）。
    命中 → 该块视为被注入污染，整块拒抽（宁可漏抽不可执行）。"""
    low = (text_sample or "").lower()
    for pat in INSTRUCTION_INJECTION_PATTERNS:
        if pat in low or pat in (text_sample or ""):
            return True
    return False


# ---- ②输出侧：禁词八类扫描 ----

def scan_banned(value: str) -> list[dict]:
    """输出侧扫描：对【抽取产物字段值】（非原文！）逐类匹配禁词八类。
    返回 [{category, matched, action}]；空列表=干净。"""
    hits = []
    if not isinstance(value, str) or not value:
        return hits
    for cat, rule in BANNED_EIGHT.items():
        for rx in _BANNED_COMPILED[cat]:
            m = rx.search(value)
            if m:
                hits.append({"category": cat, "matched": m.group(0),
                             "action": rule["action"], "desc": rule["desc"]})
                break
    return hits


def no_prior_fill(canonical: dict, evidence_quotes: list[str]) -> list[dict]:
    """③模型侧防先验："AI 已知信息不入档"。
    默认特征词出现在 canonical 值中、且【证据引文中无该词的原文出处】→ 判先验补全，
    处置=改为 // 原文未提及 占位（绝不默认填充）。返回违规清单。"""
    joined_quotes = " ".join(evidence_quotes or [])
    violations = []
    rx = _BANNED_COMPILED["default_trait"][0]
    for key, val in canonical.items():
        if not isinstance(val, str):
            continue
        m = rx.search(val)
        if m and m.group(0) not in joined_quotes:
            violations.append({"field": key, "term": m.group(0),
                               "remedy": DEFAULT_TRAIT_NOT_MENTIONED})
    return violations


def screen_candidate(canonical: dict, evidence_quotes: list[str]) -> dict:
    """输出侧+模型侧联合筛：clean=无禁词无先验；否则带 findings（quarantine 入口之一）。"""
    banned = []
    for key, val in canonical.items():
        if isinstance(val, str):
            for h in scan_banned(val):
                banned.append({**h, "field": key})
    prior = no_prior_fill(canonical, evidence_quotes)
    return {"clean": not banned and not prior,
            "banned_findings": banned, "prior_fill_findings": prior}


# ---- 别名四分类策略（规则层） ----

def alias_merge_policy(kind: str, same_referent_evidence: bool = False,
                       confidence: float = 0.0) -> dict:
    """别名合并策略：proper_name=可合并；nickname=须同指证据且置信≥0.85；
    descriptor/title=永不合并（描述性称谓与头衔不同人可共用）；存疑（无证据/低置信/未知类）
    =分开建——宁可分裂不可误合。"""
    if kind == "proper_name":
        return {"decision": "merge", "reason": "专名：同一写法可合并"}
    if kind == "nickname":
        if same_referent_evidence and confidence >= ALIAS_MERGE_CONFIDENCE_GATE:
            return {"decision": "merge", "reason": f"绰号：同指证据在案且置信 {confidence}≥{ALIAS_MERGE_CONFIDENCE_GATE}"}
        return {"decision": "separate", "reason": "绰号：缺同指证据或置信不足门槛——存疑分开建"}
    if kind in ("descriptor", "title"):
        return {"decision": "never", "reason": "描述性称谓/头衔：不同人物可共用，永不合并"}
    return {"decision": "separate", "reason": f"未知别名类 {kind!r}：存疑分开建（保守缺省）"}


# ---- 长篇施工参数（规划函数） ----

def plan_batches(n_chapters: int, batch_size: int = 8) -> list[list[int]]:
    """分批规划：每批 5-8 章（batch_size clamp 进 [5,8]）；最后一批允许 <5（尾批不摊薄）。
    返回 1-based 章号批列表。"""
    if n_chapters < 1:
        return []
    size = max(CONSTRUCTION_PARAMS["batch_chapters"][0],
               min(CONSTRUCTION_PARAMS["batch_chapters"][1], batch_size))
    return [list(range(s, min(s + size, n_chapters + 1)))
            for s in range(1, n_chapters + 1, size)]


def merge_plan(n_units: int) -> list[dict]:
    """降维聚合规划（√N 合并）：15KB/章 → ≤8K 回传 → 按 √N 分组合并，直至单组。
    返回逐层 [{level, units, group_size, groups}]。"""
    levels = []
    units, level = n_units, 0
    while units > 1:
        group_size = max(2, int(math.sqrt(units)))
        groups = math.ceil(units / group_size)
        levels.append({"level": level, "units": units,
                       "group_size": group_size, "groups": groups})
        units, level = groups, level + 1
    if not levels:
        levels.append({"level": 0, "units": 1, "group_size": 1, "groups": 1})
    return levels


# ---- 机械硬检查（grep 计数不依赖自报） ----

def verify_evidence(candidates: list[dict], blocks: list[dict]) -> dict:
    """落盘后硬检查：每条候选的证据引文【回原文坐标复核】——引文在声称的
    vol/chapter 坐标内 grep 不到即判失败（不依赖抽取器自报，oh-story 机械硬检查）。
    计数核对：candidate_count == 复核通过数 + 失败数（总数不许缩水）。"""
    by_chapter: dict[int, list[dict]] = {}
    for b in blocks:
        by_chapter.setdefault(b["chapter"], []).append(b)
    passed, failed = [], []
    for cand in candidates:
        ok = True
        for ev in cand.get("evidence", []):
            hit = None
            for b in by_chapter.get(ev["chapter"], []):
                if b["vol"] == ev["vol"] and ev["quote"] in b["text"]:
                    hit = b
                    break
            if hit is None:
                ok = False
                break
        (passed if ok else failed).append(cand["record_id"])
    return {"total": len(candidates), "passed": len(passed), "failed": len(failed),
            "failed_ids": failed}


# ---- 候选构造（证据式抽取条款：每断言须原文引+章号，B4 无证据不入库） ----

def _short_hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True)
                          .encode("utf-8")).hexdigest()[:12]


def make_candidate(record_type: str, canonical: dict, evidence: list[dict],
                   confidence: float, extractor: str = "stub-v2",
                   verified_against: dict | None = None) -> dict:
    """构造契约合规的 candidate 记录（入库前态）。record_id 由内容哈希决定→重跑幂等。
    Bad 例：make_candidate("entity", {"name": "绝美的少女"}, [])  → 无证据，拒（B4）。
    Good 例：make_candidate("entity", {"name": "缇达"},
               [{"vol":1,"chapter":14,"line":3,"quote":"缇达拔出了剑"}]) → 过。"""
    if record_type not in ("event", "entity"):
        raise ValueError(f"只抽 event/entity，拒绝 {record_type!r}")
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
        "verified_against": verified_against or {
            "path": "stub/source", "sha": "0" * 7, "verified_at": "1970-01-01",
        },  # 生产管线应传真实源快照三件套
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
                 chapter_titles: dict | None = None,
                 skipped_out: list[dict] | None = None) -> list[dict]:
    """stub 确定性抽取：词典实体 + 关键词事件。
    防御并配：元文本章整章跳过（①读入侧）+ 内嵌指令块拒抽（④安全侧）。
    返回 candidate 列表（每提及一条；实体消歧归 P3 Canonicalizer）。"""
    lexicon = lexicon or []
    event_patterns = event_patterns or []
    chapter_titles = chapter_titles or {}
    out: list[dict] = []
    for block in blocks:
        title = chapter_titles.get(block.get("chapter"), "")
        if is_metatext(title=title, text_sample=block["text"]):
            # A9 修复（审计 R4）：B6「绝不静默丢弃」——跳过块登记（skipped_out 或调用方入 quarantine）
            if skipped_out is not None:
                skipped_out.append({"chapter": block.get("chapter"),
                                    "line_start": block.get("line_start"),
                                    "reason": "metatext"})
            continue  # ①R6 对应 stub 闸：元文本零抽取
        if has_embedded_instruction(block["text"]):
            if skipped_out is not None:
                skipped_out.append({"chapter": block.get("chapter"),
                                    "line_start": block.get("line_start"),
                                    "reason": "embedded_instruction"})
            continue  # ④安全侧：注入污染块整块拒抽
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


# ---- graphiti 真实路径（P2 实装；本体版只提供已验证参数形态） ----

def build_episode_kwargs(order_index: int, episode_body: str, episode_name: str,
                         group_id: str, source_description: str) -> dict:
    """组装 graphiti add_episode 关键参数（Step0 Tier2 已验证形态）：
    reference_time = 伪锚点（2000-01-01+order_index 天，禁墙钟）；
    custom_extraction_instructions = R6 标配（元文本防御，逐字照抄已验证文本）。
    纯函数无副作用、不依赖 graphiti 安装；完整管道接线见
    P1执行区/step0-抽取精度实验/脚本/run_tier2_pipeline.py。"""
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
        "本体版不含 graphiti 运行时。P2 接线复用 Step0 Tier2 已验证管道"
        "（venv312 + DeepSeek + LM Studio 嵌入 + Neo4j），参数经 build_episode_kwargs 组装。")


def env_probe() -> dict:
    """云 API/图库凭证探活（⑧纪律）：只探存在性布尔，绝不读值输出值（D-004）。"""
    import os
    return {"DEEPSEEK_API_KEY": bool(os.environ.get("DEEPSEEK_API_KEY")),
            "NEO4J_PASSWORD": bool(os.environ.get("NEO4J_PASSWORD"))}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="CBB P2 抽取器 stub（本体版 v2 · 四面防御）")
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
    hard = verify_evidence(cands, manifest["blocks"])  # 机械硬检查随跑
    payload = {"candidate_count": len(cands), "candidates": cands, "hard_check": hard}
    if args.out:
        Path(args.out).write_text(json.dumps(payload, ensure_ascii=False, indent=1),
                                  encoding="utf-8")
    print(f"[extract] candidates={len(cands)} hard_check={hard['passed']}/{hard['total']} "
          f"R6=内置标配 四面防御=并配")
    return 0


if __name__ == "__main__":
    sys.exit(main())
