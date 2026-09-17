# -*- coding: utf-8 -*-
"""slice_batch.py — 切批脚本（工单 §0 编排：子代理只读自己的包）。
从边界表把章切成 迷深实战-工作区/slice/chNNNN.txt（含 CHAPTER 标记行起，至 line_end 止）。
切片行号约定：evidence.line=章内物理行（cbb-coordinate：标记行为第 0 块，正文行号=文件行号-1）。

用法：py -X utf8 slice_batch.py --from 66 --to 71 [--force]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORK = HERE.parent
BT = WORK / "manifest" / "boundary-table-v1.json"
SLICE = WORK / "slice"
CORPUS = WORK.parent.parent / "语料分析" / "corpus" / "clean_full.txt"


def slice_range(ch_from: int, ch_to: int, force: bool = False) -> list[dict]:
    bt = json.loads(BT.read_text(encoding="utf-8"))
    by_no = {c["chapter_no"]: c for c in bt["chapters"]}
    lines = CORPUS.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    SLICE.mkdir(exist_ok=True)
    made = []
    for no in range(ch_from, ch_to + 1):
        ch = by_no.get(no)
        if not ch:
            continue
        out = SLICE / f"ch{no:04d}.txt"
        if out.exists() and not force:
            continue
        body = "\n".join(lines[ch["marker_line"] - 1:ch["line_end"]]) + "\n"
        out.write_text(body, encoding="utf-8")
        made.append({"chapter": no, "slice": str(out), "lines": ch["line_end"] - ch["marker_line"] + 1,
                     "ingestion_index": ch["ingestion_index"], "noise": ch["noise"],
                     "title": ch["title"]})
    return made


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="ch_from", type=int, required=True)
    ap.add_argument("--to", dest="ch_to", type=int, required=True)
    ap.add_argument("--force", action="store_true")
    ns = ap.parse_args(argv)
    made = slice_range(ns.ch_from, ns.ch_to, ns.force)
    print(json.dumps(made, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
