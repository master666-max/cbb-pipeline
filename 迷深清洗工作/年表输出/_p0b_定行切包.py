# -*- coding: utf-8 -*-
"""P0b 直接按固定行数把清洗标注版切包（~900 行/包），无视话边界。
子代理每次读 1 包。块头前 ensure 完整块不被切开（在块边界处切）。"""
import os, re

SRC = r"D:/DeepSeek Harness专用！危险！！！！！/迷深清洗工作2/异世界迷宫最深部_知识库/分析/清洗标注版"
DST = r"D:/DeepSeek Harness专用！危险！！！！！/迷深清洗工作2/年表输出/_packs"
LINES_PER = 1700

def chunk_by_blocks(lines):
    """按 '## block_id:' 块边界，把 lines 切成每 ~LINES_PER 行一包，不在块中间断开。"""
    # 先收集块起止
    starts = [i for i, l in enumerate(lines) if l.startswith("## block_id:")]
    bounds = starts + [len(lines)]
    blocks = []
    for idx in range(len(starts)):
        blocks.append((starts[idx], bounds[idx+1]))
    chunks = []
    cur, curlines = [], 0
    for s, e in blocks:
        seg = lines[s:e]
        if cur and curlines + len(seg) > LINES_PER:
            chunks.append(cur); cur, curlines = [], 0
        cur += seg; curlines += len(seg)
    if cur:
        chunks.append(cur)
    return chunks

def main():
    os.makedirs(DST, exist_ok=True)
    total = 0
    for fn in sorted(os.listdir(SRC)):
        if not fn.endswith(".md"):
            continue
        cname = fn.replace("_清洗标注版.md", "")
        with open(os.path.join(SRC, fn), encoding="utf-8") as f:
            lines = f.read().split("\n")
        chunks = chunk_by_blocks(lines)
        outdir = os.path.join(DST, cname)
        os.makedirs(outdir, exist_ok=True)
        for idx, ch in enumerate(chunks, 1):
            header = f"## [章节] {cname} | 包 {idx}/{len(chunks)} (~{sum(len(l) for l in ch)//1024}KB, {len(ch)} 行)\n\n"
            with open(os.path.join(outdir, f"pack_{idx:02d}.md"), "w", encoding="utf-8") as fo:
                fo.write(header + "\n".join(ch))
        total += len(chunks)
        print(f"{cname}: {len(chunks)} 包")
    print("TOTAL packs:", total)

if __name__ == "__main__":
    main()