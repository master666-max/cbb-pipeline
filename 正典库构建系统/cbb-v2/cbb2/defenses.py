# -*- coding: utf-8 -*-
"""cbb2.defenses — 抽取四面防御的读入/安全/输出三侧（R6/R7/R8/R15；移植 v1 cbb_extract）。"""
from __future__ import annotations

METATEXT_TITLE_PATTERNS = ("章末说", "本章说", "作者的话", "请假条", "插图页")
METATEXT_BODY_PATTERNS = ("翻译：", "校对：", "转载请注明", "本章说", "评论区",
                          "点赞", "收藏", "月票")
INSTRUCTION_INJECTION_PATTERNS = ("ignore previous", "disregard above", "忽略之前", "忽略以上",
                                  "请忽略上文", "system prompt", "系统提示词", "rm -rf",
                                  "<script", "```")
# 禁词八类（worldbook :373-387 框架；词表=忠实移植 v1——禁词扫描对象是**抽取产物字段值**，非原文）
import re as _re

BANNED_EIGHT = {
    "metaphor": ("transform", (r"(眸|瞳|眼|发|肤|声|嗓).{0,4}(如|似|若|像|仿佛|宛如|如同)",)),
    "universal_modifier": ("delete", (r"(精致的|美丽的|俊美的|优雅的|神秘的|冷峻的|气质出众|无可挑剔)",)),
    "default_trait": ("delete", (r"(黑发|黑眼|乌黑.{0,2}发|尖耳|年轻的|看起来.{0,3}岁)",)),
    "narrative_voice": ("delete", (r"(一丝|一缕|弧度|勾起嘴角|弯起嘴角|眸光|空气仿佛凝固)",)),
    "trait_label": ("transform", (r"^(温柔|冷酷|高冷|傲娇|腹黑|天然呆|病娇)$",)),
    "subjective": ("delete", (r"(绝美|惊艳|完美无瑕|无人能敌|天下第一)",)),
    "explanatory": ("delete", (r"(体现了|表现出他的|说明了他|暗示着|这意味|这一动作)",)),
    "tone_modifier": ("delete", (r"(似乎|好像|大概|或许|简直是|无疑)",)),
}
_BANNED_COMPILED = {k: tuple(_re.compile(p) for p in pats) for k, (_, pats) in BANNED_EIGHT.items()}


def is_metatext(title: str = "", text_sample: str = "") -> bool:
    for pat in METATEXT_TITLE_PATTERNS:
        if pat in (title or ""):
            return True
    for pat in METATEXT_BODY_PATTERNS:
        if pat in (text_sample or ""):
            return True
    return False


def has_embedded_instruction(text_sample: str) -> bool:
    low = (text_sample or "").lower()
    for pat in INSTRUCTION_INJECTION_PATTERNS:
        if pat in low or pat in (text_sample or ""):
            return True
    return False


def scan_banned(value: str) -> list[dict]:
    hits = []
    if not isinstance(value, str) or not value:
        return hits
    for cat, (_action, _desc) in BANNED_EIGHT.items():
        for rx in _BANNED_COMPILED[cat]:
            m = rx.search(value)
            if m:
                hits.append({"category": cat, "matched": m.group(0)})
                break
    return hits


def plan_batches(n: int, batch_size: int = 8) -> list[list[int]]:
    return [list(range(i + 1, min(i + batch_size, n) + 1)) for i in range(0, n, batch_size)]
