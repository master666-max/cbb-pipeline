# -*- coding: utf-8 -*-
"""U-C01：解析 clean_full.txt 517 章边界表（单一切片真值）+ 全量伪锚点树 v1。
产物：manifest/boundary-table-v1.json（含每章行区间/摄入序/噪音标记）
      anchors/anchor-tree.v1.json（517 锚点，tick=摄入序 0 起算）
抽 5 章核对证据：logs/uc01-boundary-check.json
"""
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORK = HERE.parent
CBB = WORK.parent / "cbb"
sys.path.insert(0, str(CBB / "cbb-anchor"))
sys.path.insert(0, str(CBB / "contracts"))
import cbb_anchor  # noqa: E402

CORPUS = WORK.parent.parent / "语料分析" / "corpus" / "clean_full.txt"
VA = {"path": "语料分析/corpus/clean_full.txt",
      "sha": "e1a96061d25b0016094dd8daec82769ee80fc3bb",
      "verified_at": "2026-09-16"}
MARKER_RE = re.compile(r"^<<<CHAPTER (\d{4}) \| (.*?)>>>(?:\s*\[([A-Z]+:[^\]]+)\])?\s*$")


def main() -> int:
    raw = CORPUS.read_bytes()
    text = raw.decode("utf-8")
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    chapters = []
    for lineno, ln in enumerate(lines, 1):
        m = MARKER_RE.match(ln)
        if m:
            tag = m.group(3)
            chapters.append({"chapter_no": int(m.group(1)), "title": m.group(2),
                             "noise": tag if (tag and tag.startswith("NOISE")) else None,
                             "dup_of": int(tag.split("OF")[1]) if (tag and tag.startswith("DUP")) else None,
                             "marker_line": lineno})
    assert len(chapters) == 517, f"章数 {len(chapters)} ≠ 517"
    for i, ch in enumerate(chapters):
        ch["ingestion_index"] = i                      # 0 起算摄入序=伪锚点 i
        end = chapters[i + 1]["marker_line"] - 1 if i + 1 < len(chapters) else len(lines)
        ch["line_start"] = ch["marker_line"]
        ch["line_end"] = end
        ch["body_lines"] = end - ch["marker_line"]
    table = {
        "kind": "boundary-table", "version": 1, "source": dict(VA, name=CORPUS.name,
                                                               size=len(raw),
                                                               sha256=hashlib.sha256(raw).hexdigest()),
        "chapter_count": len(chapters),
        "coordinate_note": "evidence.line=章内物理行=marker_line 起算的行号-1（marker 行不计）",
        "chapters": chapters,
    }
    out = WORK / "manifest" / "boundary-table-v1.json"
    out.write_text(json.dumps(table, ensure_ascii=False, sort_keys=True, indent=1), encoding="utf-8")

    # 全量伪锚点树 v1（trial 单章树已移档 anchors/trial-v0-anchor-tree.ch14only.json）
    tree = cbb_anchor.build_pseudo_tree([c["chapter_no"] for c in chapters], vol=1, version=1,
                                        verified_against=VA)
    p, created = cbb_anchor.save_tree(tree, WORK / "anchors")
    assert created, "anchor-tree.v1.json 已存在（应先移档 trial 树）"

    # 抽 5 章核对：marker 行原文/首行正文/边界衔接（下一章 marker 恰在 line_end+1）
    import random
    rng = random.Random(20260916)
    samples = rng.sample(range(517), 5)
    checks = []
    for i in samples:
        ch = chapters[i]
        marker_txt = lines[ch["marker_line"] - 1]
        nxt = lines[ch["line_end"]] if ch["line_end"] < len(lines) else "(EOF)"
        checks.append({
            "ingestion_index": i, "chapter": ch["chapter_no"],
            "marker_line": ch["marker_line"], "marker_text": marker_txt[:60],
            "body_lines": ch["body_lines"],
            "next_line_after_end": nxt[:60],
            "ok_marker": marker_txt.startswith(f"<<<CHAPTER {ch['chapter_no']:04d} |"),
            "ok_boundary": (ch["line_end"] + 1 == chapters[i + 1]["marker_line"]) if i + 1 < 517 else True,
        })
    ev = {"sampled": samples, "checks": checks,
          "all_ok": all(c["ok_marker"] and c["ok_boundary"] for c in checks),
          "noise_chapters": sum(1 for c in chapters if c["noise"]),
          "first_three": [{k: c[k] for k in ("ingestion_index", "chapter_no", "title")} for c in chapters[:3]],
          "last_one": {k: chapters[-1][k] for k in ("ingestion_index", "chapter_no", "title", "line_end")}}
    (WORK / "logs" / "uc01-boundary-check.json").write_text(
        json.dumps(ev, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"chapters": len(chapters), "tree": str(p),
                      "check_all_ok": ev["all_ok"], "noise": ev["noise_chapters"],
                      "last_chapter": ev["last_one"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
