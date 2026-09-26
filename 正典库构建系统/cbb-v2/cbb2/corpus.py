# -*- coding: utf-8 -*-
"""cbb2.corpus — 坐标/引文回落（R9/R10；算法忠实移植 v1 cbb_coordinate，语义=章内物理行 1-based）。"""
from __future__ import annotations

import hashlib
import re

_MARKER = re.compile(r"^<<<CHAPTER\s+(\d+)\s*\|\s*(.*?)>>>\s*$")


def parse_chapter_marker(line: str):
    m = _MARKER.match(line.strip())
    return (int(m.group(1)), m.group(2).strip()) if m else None


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def coordinate(text: str, vol: int = 1) -> dict:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    chapters: list[dict] = []
    cur: dict | None = None
    chapter_line = 0
    para_buf: list[str] = []
    para_start = 0

    def flush():
        nonlocal para_buf, para_start
        if cur is not None and any(l.strip() for l in para_buf):
            body = "\n".join(para_buf)
            cur["paragraphs"].append({"para": len(cur["paragraphs"]) + 1,
                                      "line_start": para_start,
                                      "line_end": para_start + len(para_buf) - 1,
                                      "text": body, "sha256": sha256_text(body)})
        para_buf, para_start = [], 0

    for ln in lines:
        mk = parse_chapter_marker(ln)
        if mk:
            flush()
            cur = {"vol": vol, "chapter": mk[0], "title": mk[1], "paragraphs": []}
            chapter_line = 0
            chapters.append(cur)
            continue
        if cur is None:
            if not ln.strip():
                continue
            cur = {"vol": vol, "chapter": 0, "title": "(preamble-无章标记)", "paragraphs": []}
            chapter_line = 0
            chapters.append(cur)
        chapter_line += 1
        if ln.strip() == "":
            flush()
        else:
            if not para_buf:
                para_start = chapter_line
            para_buf.append(ln)
    flush()

    blocks = [{"block_id": f"v{ch['vol']:02d}c{ch['chapter']:04d}p{p['para']:04d}",
               "vol": ch["vol"], "chapter": ch["chapter"], "para": p["para"],
               "line_start": p["line_start"], "line_end": p["line_end"],
               "text": p["text"], "sha256": p["sha256"]}
              for ch in chapters for p in ch["paragraphs"]]
    return {"vol_default": vol, "chapter_count": len(chapters), "chapters": chapters,
            "block_count": len(blocks), "blocks": blocks}


def locate_quote(blocks: list[dict], vol: int, chapter: int, quote: str):
    for b in blocks:
        if b["vol"] == vol and b["chapter"] == chapter and quote in b["text"]:
            return b
    return None


def process_bytes(raw: bytes, vol: int = 1) -> dict:
    text = raw.decode("utf-8-sig")  # R10：剥 BOM（记事本默认带 BOM→首章失配→全库偏移）
    return coordinate(text, vol=vol)
