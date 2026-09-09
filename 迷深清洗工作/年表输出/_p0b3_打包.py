# -*- coding: utf-8 -*-
"""P0b3 按话切分 + 硬切打包：每包 ~140KB（行数滚动）。子代理每次读 1 包。"""
import os, re

SPLIT = r"D:/DeepSeek Harness专用！危险！！！！！/迷深清洗工作2/年表输出/_split"
DST = r"D:/DeepSeek Harness专用！危险！！！！！/迷深清洗工作2/年表输出/_packs"
TARGET = 140 * 1024

def chapter_sort_key(fn):
    m = re.search(r"(\d+)", fn)
    return (int(m.group(1)) if m else 0, fn)

def pack_chapter(cdir, cname):
    files = [f for f in os.listdir(cdir) if f.endswith(".md")]
    files.sort(key=chapter_sort_key)
    packs = []
    cur, cur_size, pack_no = [], 0, 0
    for fn in files:
        with open(os.path.join(cdir, fn), encoding="utf-8") as f:
            txt = f.read()
        # 单话文件若自己就 > 140KB，仍独立成包（由该包内首行给出话标题）
        if cur and cur_size + len(txt) > TARGET:
            packs.append((cur, cur_size)); cur, cur_size = [], 0
        cur.append(txt); cur_size += len(txt)
    if cur:
        packs.append((cur, cur_size))
    outdir = os.path.join(DST, cname)
    os.makedirs(outdir, exist_ok=True)
    for idx, (txts, size) in enumerate(packs, 1):
        header = f"## [章节] {cname} | 打包文件 {idx}/{len(packs)} (~{size//1024}KB, {len(txts)} 话)\n\n"
        body = header + "\n\n===\n\n".join(txts)
        with open(os.path.join(outdir, f"pack_{idx:02d}.md"), "w", encoding="utf-8") as f:
            f.write(body)
    return len(packs)

def main():
    total = 0
    for cname in sorted(os.listdir(SPLIT)):
        cdir = os.path.join(SPLIT, cname)
        if not os.path.isdir(cdir):
            continue
        n = pack_chapter(cdir, cname)
        total += n
        print(f"{cname}: {n} 包")
    print("TOTAL packs:", total)

if __name__ == "__main__":
    main()