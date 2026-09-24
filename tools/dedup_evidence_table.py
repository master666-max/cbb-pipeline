# -*- coding: utf-8 -*-
"""dedup_evidence_table.py — 一次性：evidence 表去重（键=(record_id,line,quote[:40]) 唯一）。

背景：进度件曾被两次并发批写 → 118232 行中 43 个键各出现两次。
做法：流式（分批）读旧表 → 去重写入 evidence_tmp → 校验 → drop 旧表 → rename。
全程分块，峰值内存=一批；旧表在新表校验通过前不动（失败可停）。
"""
import lancedb
import pyarrow as pa

IDX = r"D:/zcode专用！！！！危险！！！！！！！！！/正典库构建系统/迷深实战-工作区/索引/lancedb"
CH = 2000


def key_of(batch):
    rid = batch.column("record_id").to_pylist()
    line = batch.column("line").to_pylist()
    quote = batch.column("quote").to_pylist()
    return [f"{r}|{l}|{q[:40]}" for r, l, q in zip(rid, line, quote)]


db = lancedb.connect(IDX)
src = db.open_table("evidence")
n_src = src.count_rows()
ds = src.to_lance()

tbl = None
seen: set[str] = set()
n_out = n_dup = 0
buf = []


def flush():
    global tbl, n_out, buf
    if not buf:
        return
    chunk = pa.Table.from_batches(buf)
    if tbl is None:
        tbl = db.create_table("evidence_tmp", chunk, mode="overwrite")
    else:
        tbl.add(chunk)
    n_out += chunk.num_rows
    buf = []


for b in ds.to_batches(batch_size=CH):
    keys = key_of(b)
    mask, keep_keys = [], []
    for k in keys:
        if k in seen:
            n_dup += 1
            mask.append(False)
        else:
            seen.add(k)
            keep_keys.append(k)
            mask.append(True)
    if all(mask):
        buf.append(b)
    else:
        idxs = [i for i, m in enumerate(mask) if m]
        if idxs:
            buf.append(b.take(pa.array(idxs, type=pa.int64())))
    if sum(x.num_rows for x in buf) >= CH:
        flush()
flush()

got = tbl.count_rows()
print(f"旧表 {n_src} 行 → 去重 {n_dup} 行 → 新表 {got} 行（唯一键 {len(seen)}）")
assert got == len(seen) == n_src - n_dup, "计数不闭合"
db.drop_table("evidence")
db.rename_table("evidence_tmp", "evidence")
t2 = db.open_table("evidence")
print(f"✓ 已切换：evidence = {t2.count_rows()} 行（唯一键）")
