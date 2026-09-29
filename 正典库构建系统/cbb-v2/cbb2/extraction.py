# -*- coding: utf-8 -*-
"""cbb2.extraction — 抽取线通用配置层（方法学产品化批次 2·V1）。

目标：抽取上游（语料→切片→边界表→抽取→锚定）零书本字面量——语料路径、切片标记、
边界表、类型词表、抽取契约、判例 few-shot、上下文包、库根、工作目录、并发全部外置。

R-030 硬约束（写入 config 的 types 字段语义）：实体类型体系与断言位可变声明是**语料实证
属性**——config 结构可跨书复制，**值必须经真数据彩排校准**（批次 2·V4 彩排校准夹具），
禁止盲抄他书 config 的值。

约定：配置内相对路径以配置文件所在目录为基准；词表/判例/上下文包为 per-book 演化资产，
加载器只解析不强制存在（存在性由 runner 在使用点校验）。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

REQUIRED = ("version", "book", "corpus", "store_root", "work_dir", "panel_concurrency")


@dataclass
class ExtractionConfig:
    path: Path
    version: str
    book: str
    corpus: Path
    boundary_file: Path | None
    vocab_file: Path | None
    contract_file: Path | None
    precedent_file: Path | None
    context_pack_dir: Path | None
    context_auto_update: bool
    store_root: Path
    work_dir: Path
    concurrency: int
    anchor_check: bool
    types: dict
    raw: dict = field(default_factory=dict)


def _resolve(base: Path, p: str | None) -> Path | None:
    if p is None:
        return None
    q = Path(p)
    return q if q.is_absolute() else (base / q)


def load_config(path: str | Path) -> ExtractionConfig:
    path = Path(path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    missing = [k for k in REQUIRED if k not in raw]
    if missing:
        raise ValueError(f"抽取配置缺必填字段: {missing}（{path}）")
    base = path.resolve().parent
    corpus = raw.get("corpus") or {}
    corpus_path = _resolve(base, corpus.get("path") if isinstance(corpus, dict) else corpus)
    if corpus_path is None:
        raise ValueError("corpus.path 必填")
    conc = int(raw.get("panel_concurrency", raw.get("concurrency", 3)))
    if conc < 1:
        raise ValueError(f"并发须 ≥1，得到 {conc}")
    cfg = ExtractionConfig(
        path=path.resolve(),
        version=str(raw["version"]),
        book=raw["book"],
        corpus=corpus_path,
        boundary_file=_resolve(base, raw.get("boundary_file")),
        vocab_file=_resolve(base, raw.get("vocab_file")),
        contract_file=_resolve(base, raw.get("contract_file")),
        precedent_file=_resolve(base, raw.get("precedent_file")),
        context_pack_dir=_resolve(base, (raw.get("context_pack") or {}).get("dir")),
        context_auto_update=bool((raw.get("context_pack") or {}).get("auto_update", True)),
        store_root=_resolve(base, raw["store_root"]),
        work_dir=_resolve(base, raw["work_dir"]),
        concurrency=conc,
        anchor_check=bool(raw.get("anchor_check", True)),
        types=raw.get("types") or {},
        raw=raw,
    )
    return cfg


def build_boundary(cfg) -> dict:
    """V2 边界表生成器（通用）：按 config 的语料与章节标记正则扫描全文，
    产出 {kind,version,source,chapter_count,coordinate_note,chapters[]} 至 cfg.boundary_file。
    expected_chapter_count 提供时强校验（迷深=517）；不提供则跳过断言。"""
    import hashlib
    import re
    raw = cfg.corpus.read_bytes()
    text = raw.decode("utf-8")
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    rex = re.compile(cfg.raw.get("chapter_marker_regex")
                     or r"^<<<CHAPTER (\d{4}) \| (.*?)>>>(?:\s*\[([A-Z]+:[^\]]+)\])?\s*$")
    chapters = []
    for lineno, ln in enumerate(lines, 1):
        m = rex.match(ln)
        if m:
            tag = m.group(3)
            chapters.append({"chapter_no": int(m.group(1)), "title": m.group(2),
                             "noise": tag if (tag and tag.startswith("NOISE")) else None,
                             "dup_of": int(tag.split("OF")[1]) if (tag and tag.startswith("DUP")) else None,
                             "marker_line": lineno})
    expected = cfg.raw.get("expected_chapter_count")
    if expected:
        assert len(chapters) == int(expected), f"章数 {len(chapters)} ≠ {expected}"
    for i, ch in enumerate(chapters):
        ch["ingestion_index"] = i
        end = chapters[i + 1]["marker_line"] - 1 if i + 1 < len(chapters) else len(lines)
        ch["line_start"] = ch["marker_line"]
        ch["line_end"] = end
        ch["body_lines"] = end - ch["marker_line"]
    table = {"kind": "boundary-table", "version": 1,
             "source": {"path": str(cfg.corpus), "name": cfg.corpus.name, "size": len(raw),
                        "sha256": hashlib.sha256(raw).hexdigest()},
             "chapter_count": len(chapters),
             "coordinate_note": "evidence.line=章内物理行=marker_line 起算的行号-1（marker 行不计）",
             "chapters": chapters}
    if not cfg.boundary_file:
        raise ValueError("config 缺 boundary_file——构建结果无处落盘")
    cfg.boundary_file.parent.mkdir(parents=True, exist_ok=True)
    cfg.boundary_file.write_text(json.dumps(table, ensure_ascii=False, sort_keys=True, indent=1),
                                 encoding="utf-8")
    return {"chapter_count": len(chapters), "out": str(cfg.boundary_file)}
