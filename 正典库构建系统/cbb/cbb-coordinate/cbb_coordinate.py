# -*- coding: utf-8 -*-
"""cbb_coordinate.py — CBB P0 预处理+全局坐标系统+编号注册表（本体版 v2）

v2（U-B02）在实验版（cbb-skills/，FROZEN）基础上：
  保留：全局坐标 (卷, 章, 段, 行) 与幂等分块缓存（缓存即断点协议：命中即跳过计算）；
  吸收：①事件 ID 追加序纪律（graphify-novel：ID 按分配序单调递增，乱序是预期，
        story 位置只记录不参与编号，永不重排）；②编号先查重即占位（R-015：register
        幂等于 (series,key)，分配即追加落盘 append-only JSONL）。
  移出：三态写入桩——真实三态/版本化/双轨合并由 cbb-store（U-B07）接管。
确定性纪律：输出不含任何时钟/随机字段，同输入必同输出。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

CHAPTER_RE = re.compile(r"^\s*<<<CHAPTER\s+(\d+)\s*\|\s*(.*?)\s*>>>\s*$")


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
    """幂等分块缓存：键 = sha256(全文+vol+算法版本)。命中读缓存，未命中计算落盘。
    断点协议：长篇分批处理时，已处理分块直接命中缓存跳过（graphify-novel 批处理扫章
    的『强制重读磁盘、不靠上下文累积』同思路——状态在盘不在内存）。"""
    raw = source.read_bytes()
    text = raw.decode("utf-8-sig")  # A8 修复（审计 R4）：剥 BOM（记事本默认带 BOM → 首章标记失配 → 全库坐标偏移）
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


class NumberingRegistry:
    """追加序编号注册表（U-B02 吸收项落地点）。

    纪律一（追加序，graphify-novel timeline 规则）：
      ID 按【分配序】单调递增；story_pos（故事内位置）只记录、不参与编号——
      追溯补录（乱序插入）是预期行为，ID 永不重排、永不复用。
    纪律二（先查重即占位，R-015 并发取号三方实例）：
      register(series, key) 幂等于 (series, key)——同键返回既有 ID 不重复发号；
      发号即追加落盘（append-only JSONL，一行一号），落盘即占位。
      多进程残留竞态披露：两进程在互相未见对方落盘时注册同 key 会得双号——
      单进程纪律为『取号前先重建实例重放最新账本』（reload()），跨进程互斥不在本层职责。
    确定性：账本行不含时钟/随机字段。
    """

    def __init__(self, path: Path):
        self.path = Path(path)
        self.entries: list[dict] = []
        self._by_key: dict[tuple[str, str], str] = {}
        self._counters: dict[str, int] = {}
        self._replay()

    def _replay(self) -> None:
        self.entries, self._by_key, self._counters = [], {}, {}
        if not self.path.exists():
            return
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            e = json.loads(line)
            self.entries.append(e)
            self._by_key[(e["series"], e["key"])] = e["id"]
            n = int(e["id"].rsplit("-", 1)[1])
            if n > self._counters.get(e["series"], 0):
                self._counters[e["series"]] = n

    def reload(self) -> None:
        """取号前重放最新账本（断点续跑/多实例纪律）。"""
        self._replay()

    def register(self, series: str, key: str, story_pos: int | None = None) -> str:
        """查重→占位。同 (series,key) 已占位返回原 ID（幂等）；否则发下一可用号并立即落盘。"""
        if story_pos is not None and (not isinstance(story_pos, int) or story_pos < 0):
            raise ValueError(f"story_pos 须为非负整数或 None，实为 {story_pos!r}")
        existing = self._by_key.get((series, key))
        if existing is not None:
            return existing  # 查重命中：不重复发号（幂等占位）
        n = self._counters.get(series, 0) + 1
        rid = f"{series}-{n:04d}"
        entry = {"id": rid, "series": series, "key": key, "story_pos": story_pos}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
        # 落盘即占位：写成功后才更新内存态（写失败抛异常，内存不推进——账本与内存一致）
        self.entries.append(entry)
        self._by_key[(series, key)] = rid
        self._counters[series] = n
        return rid

    def locate(self, series: str, key: str) -> str | None:
        return self._by_key.get((series, key))

    def by_story_order(self, series: str) -> list[dict]:
        """故事序视图：按 story_pos 升序（None 沉底按分配序）。
        查询可排序，编号不重排——本方法永不改 ID（追加序纪律的只读面）。"""
        picked = [e for e in self.entries if e["series"] == series]
        with_pos = sorted((e for e in picked if e["story_pos"] is not None),
                          key=lambda e: e["story_pos"])
        without = [e for e in picked if e["story_pos"] is None]
        return with_pos + without

    def snapshot(self) -> list[dict]:
        """账本快照（分配序原样，永不重排）。"""
        return list(self.entries)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="CBB P0 坐标系统+编号注册表（本体版 v2）")
    ap.add_argument("--input", default=None, help="章文本文件（UTF-8），省略则只做注册表操作")
    ap.add_argument("--cache", default=str(Path(__file__).resolve().parent / ".cache"),
                    help="幂等缓存目录")
    ap.add_argument("--vol", type=int, default=1, help="卷号（默认 1）")
    ap.add_argument("--out-json", default=None, help="manifest 另存路径（可选）")
    ap.add_argument("--registry", default=None, help="编号注册表 JSONL 路径（register 模式必填）")
    ap.add_argument("--register", nargs=3, metavar=("SERIES", "KEY", "STORY_POS"),
                    default=None, help="注册编号：SERIES KEY STORY_POS（STORY_POS 用 - 表示无）")
    args = ap.parse_args(argv)

    rc = 0
    if args.register:
        if not args.registry:
            print("FATAL: --register 需要 --registry", file=sys.stderr)
            return 2
        series, key, pos_s = args.register
        pos = None if pos_s == "-" else int(pos_s)
        reg = NumberingRegistry(Path(args.registry))
        rid = reg.register(series, key, story_pos=pos)
        print(f"[coordinate-registry] {rid}")
    if args.input:
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
    if not args.register and not args.input:
        print("FATAL: 需要 --input 或 --register", file=sys.stderr)
        rc = 2
    return rc


if __name__ == "__main__":
    sys.exit(main())
