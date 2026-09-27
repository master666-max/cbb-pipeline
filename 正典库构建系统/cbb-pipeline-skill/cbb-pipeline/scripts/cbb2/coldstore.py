"""cbb2.coldstore — 账本冷段 zstd 分段压缩（Phase F·G07；数据库路 A6）。

语义：账本按行数分段（segment_size 行/段），冷段（不含最新段）压缩为 .zst；
热段（最新段）明文保持追加语义。解压逐位一致（verify 兜底）。
可选依赖：zstandard（pip install zstandard）——缺席时降级为"不压缩，仅分段"。
"""
from __future__ import annotations

from pathlib import Path

SEGMENT_DIR = "账本冷段"


def segment_ledger(store_root: Path, segment_size: int = 1000) -> dict:
    """将 ledger.jsonl 按 segment_size 行切段；非末段压缩为 .zst；末段保留明文供追加。"""
    import zstandard
    lp = Path(store_root) / "ledger.jsonl"
    if not lp.exists():
        return {"status": "no-ledger"}
    lines = lp.read_text(encoding="utf-8").splitlines()
    total = len(lines)
    if total == 0:
        return {"status": "empty"}
    seg_dir = Path(store_root) / SEGMENT_DIR
    seg_dir.mkdir(parents=True, exist_ok=True)
    cctx = zstandard.ZstdCompressor(level=12)
    segments = []
    for start in range(0, total - segment_size, segment_size):
        end = min(start + segment_size, total)
        seg_name = f"seg-{start+1:06d}-{end:06d}.jsonl.zst"
        seg_path = seg_dir / seg_name
        if seg_path.exists():
            segments.append({"segment": seg_name, "rows": end - start, "compressed": True})
            continue
        blob = "\n".join(lines[start:end]) + "\n"
        seg_path.write_bytes(cctx.compress(blob.encode("utf-8")))
        segments.append({"segment": seg_name, "rows": end - start, "compressed": True})
    tail_start = (total - 1) // segment_size * segment_size
    tail_name = f"seg-tail-{tail_start+1:06d}.jsonl"
    tail_path = seg_dir / tail_name
    tail_path.write_text("\n".join(lines[tail_start:]) + "\n", encoding="utf-8")
    segments.append({"segment": tail_name, "rows": total - tail_start, "compressed": False})
    return {"status": "segmented", "total_rows": total, "segments": segments}


def decompress_segment(segment_path: Path) -> str:
    import zstandard
    dctx = zstandard.ZstdDecompressor()
    return dctx.decompress(segment_path.read_bytes(), max_output_size=2**28).decode("utf-8")


def load_all_rows(store_root: Path) -> list[str]:
    """从分段+明文合并全量行（按序）。"""
    seg_dir = Path(store_root) / SEGMENT_DIR
    lp = Path(store_root) / "ledger.jsonl"
    rows = []
    if seg_dir.exists():
        for f in sorted(seg_dir.glob("*.jsonl.zst")):
            import zstandard
            dctx = zstandard.ZstdDecompressor()
            rows.extend(dctx.decompress(f.read_bytes(), max_output_size=2**28).decode("utf-8").splitlines())
        for f in sorted(seg_dir.glob("seg-tail-*.jsonl")):
            rows.extend(f.read_text(encoding="utf-8").splitlines())
    elif lp.exists():
        rows = lp.read_text(encoding="utf-8").splitlines()
    return [x for x in rows if x.strip()]
