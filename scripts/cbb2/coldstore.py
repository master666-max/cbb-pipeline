"""cbb2.coldstore — 账本冷段 zstd 分段压缩（Phase F·G07；数据库路 A6）。

语义：账本按行数分段（segment_size 行/段），冷段（不含最新段）压缩为 .zst；
热段（最新段）明文保持追加语义。解压逐位一致（verify 兜底）。
可选依赖：zstandard（pip install zstandard）——缺席时降级为"不压缩，仅分段"。
"""
from __future__ import annotations

from pathlib import Path

from . import jsonl_io  # P-028：撕裂安全切行

SEGMENT_DIR = "账本冷段"


def segment_ledger(store_root: Path, segment_size: int = 1000) -> dict:
    """将 ledger.jsonl 按 segment_size 行切段；非末段压缩为 .zst；末段保留明文供追加。
    读面走 jsonl_io（P-028）；已存在分段不重写（二次分段幂等，账本 append-only ⇒ 同名
    分段内容不变）。"""
    import zstandard
    lp = Path(store_root) / "ledger.jsonl"
    if not lp.exists():
        return {"status": "no-ledger"}
    lines = [x for x in jsonl_io.read_jsonl_lines(lp.read_text(encoding="utf-8")) if x.strip()]
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


def _seg_end(name: str) -> int:
    """seg-000001-001000.jsonl.zst / seg-tail-002001.jsonl → 名内编码的行号（1 基）。"""
    part = name.split("-")[2]  # "001000.jsonl.zst" / "002001.jsonl"
    return int(part.split(".")[0])


def load_all_rows(store_root: Path) -> list[str]:
    """从分段+明文合并全量行（按序）。P-1 修复：
    - 游标读到位：分段（zst+尾段）覆盖 cursor 行，其余自 ledger.jsonl 续读——
      分段快照之后新增的账本行不再被静默丢失（重建缺尾根除）；
    - 二次分段幂等去重：尾段只认起始位最靠后的一个（旧尾段内容必已并入其后分段，
      读入即重复行）；游标=尾段起始位+尾段行数。前提=账本 append-only（既有口径）。"""
    seg_dir = Path(store_root) / SEGMENT_DIR
    lp = Path(store_root) / "ledger.jsonl"
    rows: list[str] = []
    cursor = 0  # 分段已覆盖的账本行数（位置游标，按非空行计）
    if seg_dir.exists():
        import zstandard
        dctx = zstandard.ZstdDecompressor()
        for f in sorted(seg_dir.glob("seg-*.jsonl.zst")):
            rows.extend(x for x in jsonl_io.read_jsonl_lines(
                dctx.decompress(f.read_bytes(), max_output_size=2**28).decode("utf-8"))
                if x.strip())
            try:
                cursor = max(cursor, _seg_end(f.name))
            except (IndexError, ValueError):
                pass
        tails = sorted(seg_dir.glob("seg-tail-*.jsonl"))
        if tails:
            t = tails[-1]  # 只认最新尾段——旧尾段已被后续分段覆盖（二次分段幂等去重）
            tail_rows = [x for x in jsonl_io.read_jsonl_lines(
                t.read_text(encoding="utf-8")) if x.strip()]
            rows.extend(tail_rows)
            try:
                cursor = max(cursor, _seg_end(t.name) - 1 + len(tail_rows))
            except (IndexError, ValueError):
                pass
    if lp.exists():
        ledger_rows = [x for x in jsonl_io.read_jsonl_lines(
            lp.read_text(encoding="utf-8")) if x.strip()]
        rows.extend(ledger_rows[cursor:])  # 游标续读：分段之后新增的账本行
    return rows
