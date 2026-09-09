# -*- coding: utf-8 -*-
"""P0b2 按话(episode)切分清洗标注版 → 年表输出/_split/<章节>/<话>.md
每个话块一个文件，体积小，供子代理直接读取（严格保真，几乎不压缩）。"""
import os, re, json, unicodedata

SRC = r"D:/DeepSeek Harness专用！危险！！！！！/迷深清洗工作2/异世界迷宫最深部_知识库/分析/清洗标注版"
DST = r"D:/DeepSeek Harness专用！危险！！！！！/迷深清洗工作2/年表输出/_split"

HEADER_RE = re.compile(r"^## block_id: (\S+)\s+episode:\s*(.*?)\s+edition:\s*(\S+)\s+timeline:\s*(\S+)")

def safe(n):
    return re.sub(r'[\\/:*?"<>|]', "_", n)

def split_chapter(fn):
    name = fn.replace("_清洗标注版.md", "")
    with open(os.path.join(SRC, fn), encoding="utf-8") as f:
        text = f.read()
    blocks = text.split("\n\n---\n\n")
    # 按 episode 分桶
    eps = {}
    order = []
    for b in blocks:
        m = HEADER_RE.match(b.strip())
        if not m:
            continue
        bid, ep, ed, tl = m.group(1), m.group(2).strip(), m.group(3), m.group(4)
        ep_key = ep if ep else "(无标题引导语)"
        if ep_key not in eps:
            eps[ep_key] = []
            order.append(ep_key)
        eps[ep_key].append(b)
    outdir = os.path.join(DST, safe(name))
    os.makedirs(outdir, exist_ok=True)
    total_chars = 0
    for ep in order:
        content = f"## [章节] {name}\n\n# 话: {ep}\n\n" + "\n\n---\n\n".join(eps[ep])
        p = os.path.join(outdir, safe(ep) + ".md")
        with open(p, "w", encoding="utf-8") as fo:
            fo.write(content)
        total_chars += len(content)
    return name, len(order), total_chars

def main():
    total_files = 0
    for fn in sorted(os.listdir(SRC)):
        if not fn.endswith(".md"):
            continue
        name, neps, chars = split_chapter(fn)
        total_files += neps
        print(f"{name}: {neps} 话块, 共 {chars/1024:.0f}KB")
    print("TOTAL 话块:", total_files)

if __name__ == "__main__":
    main()