# -*- coding: utf-8 -*-
"""cbb_coordinate.py — CBB P0 预处理+全局坐标系统（M1 骨架）

清洗 + 全局坐标 (卷, 章, 段, 行) + 幂等分块缓存。
确定性纪律：输出不含任何时钟/随机字段，同输入必同输出；缓存命中即跳过计算。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

CHAPTER_RE = re.compile(r"^\s*<<<CHAPTER\s+(\d+)\s*\|\s*(.*?)\s*>>>\s*$")

# 三态写入桩的目标池（与 cbb-skills/contracts/cbb_contracts.THREE_STATE_SINKS 对齐；
# 本文件自带桩实现以保持技能独立性，P2 由 cbb-store 接管）
THREE_STATE_SINKS = ("confirmed", "provisional", "quarantine")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parse_chapter_marker(line: str):
    m = CHAPTER_RE.match(line)
    if not m:
        return None
    return int(m.group(1)), m.group(2)


def clean_lines(text: str) -> list[str]:
    """最小清洗：统一换行、去行尾空白。不动正文内容（P-003：过度清洗制造误报）。"""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return [ln.rstrip() for ln in text.split("\n")]


def coordinate(text: str, vol: int = 1) -> dict:
    """全文 → 章清单 + 扁平块清单。行号 = 章内物理行 1-based（空行占号）。"""
    lines = clean_lines(text)
    chapters: list[dict] = []
    cur: dict | None = None
    chapter_line = 0
    para_buf: list[str] = []
    para_start = 0

    def flush():
        nonlocal para_buf, para_start
        if cur is not None and any(l.strip() for l in para_buf):
            body = "\n".join(para_buf)
            cur["paragraphs"].append({
                "para": len(cur["paragraphs"]) + 1,
                "line_start": para_start,
                "line_end": para_start + len(para_buf) - 1,
                "text": body,
                "sha256": sha256_text(body),
            })
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
                continue  # 首章标记前的空行不建伪章
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

    blocks = []
    for ch in chapters:
        for p in ch["paragraphs"]:
            blocks.append({
                "block_id": f"v{ch['vol']:02d}c{ch['chapter']:04d}p{p['para']:04d}",
                "vol": ch["vol"], "chapter": ch["chapter"], "para": p["para"],
                "line_start": p["line_start"], "line_end": p["line_end"],
                "text": p["text"], "sha256": p["sha256"],
            })
    return {
        "vol_default": vol,
        "chapter_count": len(chapters),
        "chapters": chapters,
        "block_count": len(blocks),
        "blocks": blocks,
    }


def locate_quote(blocks: list[dict], vol: int, chapter: int, quote: str):
    """按坐标+引文定位块：返回首个 vol/chapter 匹配且 text 含 quote 的块；找不到返回 None。
    门1 的 G1-EVIDENCE/G1-DANGLING 校验以此为坐标事实源。"""
    for b in blocks:
        if b["vol"] == vol and b["chapter"] == chapter and quote in b["text"]:
            return b
    return None


def process_file(source: Path, cache_dir: Path, vol: int = 1) -> dict:
    """幂等分块缓存：键 = sha256(全文+vol+算法版本)。命中读缓存，未命中计算落盘。"""
    raw = source.read_bytes()
    text = raw.decode("utf-8")
    key = sha256_text(f"{sha256_text(text)}|vol={vol}|algo=coord-v1")
    cache_dir.mkdir(parents=True, exist_ok=True)
    cpath = cache_dir / f"{key}.json"
    if cpath.exists():
        data = json.loads(cpath.read_text(encoding="utf-8"))
        data["cache_hit"] = True
        return data
    manifest = coordinate(text, vol=vol)
    manifest["source"] = {
        "name": source.name,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "size": len(raw),
    }
    manifest["cache_key"] = key
    cpath.write_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=1),
                     encoding="utf-8")
    out = json.loads(cpath.read_text(encoding="utf-8"))
    out["cache_hit"] = False
    return out


def three_state_write_stub(record: dict, out_root: Path, status: str):
    """三态写入桩（M1）：confirmed/provisional/quarantine 三池互不混文件。
    纪律：文件名=记录 ID（record_id 或 block_id），已存在即跳过——幂等且永不覆盖（铁律2）。
    P2 起 cbb-store 接管真实入库（版本化 supersedes + status_history），本桩保证三态分离可独立演示。"""
    if status not in THREE_STATE_SINKS:
        raise ValueError(f"非法三态 {status!r}，合法={THREE_STATE_SINKS}")
    rid = record.get("record_id") or record.get("block_id")
    if not rid:
        raise ValueError("record 缺 record_id/block_id，无法入三态桩")
    sink = Path(out_root) / status
    sink.mkdir(parents=True, exist_ok=True)
    path = sink / f"{rid}.json"
    if path.exists():
        return path, False
    path.write_text(json.dumps(record, ensure_ascii=False, sort_keys=True, indent=1),
                    encoding="utf-8")
    return path, True


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="CBB P0 坐标系统（M1 骨架）")
    ap.add_argument("--input", required=True, help="章文本文件（UTF-8）")
    ap.add_argument("--cache", default=str(Path(__file__).resolve().parent / ".cache"),
                    help="幂等缓存目录")
    ap.add_argument("--vol", type=int, default=1, help="卷号（默认 1）")
    ap.add_argument("--out-json", default=None, help="manifest 另存路径（可选）")
    args = ap.parse_args(argv)

    src = Path(args.input)
    if not src.exists():
        print(f"FATAL: 输入不存在 {src}", file=sys.stderr)
        return 2
    manifest = process_file(src, Path(args.cache), vol=args.vol)
    if args.out_json:
        Path(args.out_json).write_text(
            json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=1), encoding="utf-8")
    print(f"[coordinate] chapters={manifest['chapter_count']} blocks={manifest['block_count']} "
          f"cache_hit={manifest['cache_hit']} key={manifest['cache_key'][:16]}…")
    return 0


if __name__ == "__main__":
    sys.exit(main())
