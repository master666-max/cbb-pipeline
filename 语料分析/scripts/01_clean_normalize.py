# -*- coding: utf-8 -*-
"""
01_clean_normalize.py — 《异世界迷宫最深处为目标》语料清洗规范化（可重复运行）

输入: corpus/mishen_full.txt
输出: corpus/clean_full.txt           清洗后全文（保留 CHAPTER 标记，噪声章节加标记）
      analysis/chapter_index.tsv      章节索引（章节号、章节名、字数、位置）
      analysis/clean_report.json      清洗统计（供 corpus_meta.md 使用）

清洗规则（保守，只动格式与明确噪声，不改写正文内容）:
  A. 行尾统一 \n；BOM、零宽字符去除；NBSP/全角空格 → 半角空格
  B. 全角英文字母/数字 → 半角；中文标点（，。！？：；（）等）保持全角原样
  C. 行内多余空白折叠为单空格；去行首行尾空白；3 个以上连续空行压缩为 1 个
  D. 删除明确噪声行:
     - 论坛附件块: "下载附件" / "(xx KB,下载次数:n)" / "20xx-x-xx xx:xx上传"
     - URL 行、原帖地址行
     - 译者署名行: 翻译君:/图源：/翻译：/校对：/网译版转自 等
     - 插图占位行: 插图N
     - 纯装饰行: ◆◆◆、****、———— 等连续符号行
     - 每章开头的重复书名头 "异世界迷宫最深处为目标"（dedupe，仅当为章首第一行时删）
  E. 噪声章节不删除，仅在 CHAPTER 标记后追加 [NOISE:<类型>] 标记
  F. 章节级 dedupe: 正文内容完全相同的重复章仅保留第一份，其余替换为 [DUP:OF 0001] 标记
"""
import re
import json
import hashlib
import os
from collections import Counter

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "corpus", "mishen_full.txt")
OUT_CLEAN = os.path.join(BASE, "corpus", "clean_full.txt")
OUT_INDEX = os.path.join(BASE, "analysis", "chapter_index.tsv")
OUT_REPORT = os.path.join(BASE, "analysis", "clean_report.json")

MARK_RE = re.compile(r"<<<CHAPTER (\d+) \| (.*?)>>>")

NOISE_PATTERNS = [
    (r"插图|插画|彩页|封面说明|特典|后记|设定|图片", "插图页/后记/封面说明/特典/设定"),
]
NOISE_TITLE_RE = re.compile(r"(后记|封面说明|特典|插图|插画|彩页|部分设定|的设定)")

# 行级噪声
ATTACH_RE = re.compile(r"^\(.{1,20}KB,下载次数:\d+\)$")
UPLOAD_RE = re.compile(r"^20\d{2}-\d{1,2}-\d{1,2}\d{1,2}:\d{1,2}上传$")
URL_RE = re.compile(r"https?://|www\.|\.moe|tieba\.baidu")
CREDIT_RE = re.compile(
    r"^(翻译君[:：]|翻译君的话[:：]|图源[:：]|翻译[:：]|校对[:：]|扫描[:：]|录入[:：]|"
    r"网译版转自|原帖地址|转载自|搬运自|PS[:：]|译者[:：])"
)
ILLUS_RE = re.compile(r"^插图\d*$")
DECOR_RE = re.compile(r"^[\s＊*\-—~＝=·.。…◆◇★☆_─━ー]{3,}$")
TITLE_HEADER = "异世界迷宫最深处为目标"

# 只转全角字母/数字/空格；中文标点（，。！？：；（）等）保持全角原样
FW_MAP = {chr(c): chr(c - 0xFEE0) for c in range(0xFF10, 0xFF1A)}   # ０-９ → 0-9
FW_MAP.update({chr(c): chr(c - 0xFEE0) for c in range(0xFF21, 0xFF3B)})  # Ａ-Ｚ
FW_MAP.update({chr(c): chr(c - 0xFEE0) for c in range(0xFF41, 0xFF5B)})  # ａ-ｚ
FW_MAP.update({"　": " ", "\u00a0": " ", "\u200b": "", "\u200c": "", "\u200d": "",
               "\ufeff": "", "\u2028": "\n", "\u2029": "\n"})
FW_TRANS = str.maketrans(FW_MAP)


def is_noise_title(title: str):
    m = NOISE_TITLE_RE.search(title)
    return m.group(0) if m else None


def clean_line(ln: str):
    """返回 (cleaned_line, removed_bool)"""
    s = ln.translate(FW_TRANS).strip()
    if not s:
        return "", False
    if s == TITLE_HEADER:
        return "", True
    if (ATTACH_RE.match(s) or UPLOAD_RE.match(s) or ILLUS_RE.match(s)
            or s == "下载附件" or URL_RE.search(s) or CREDIT_RE.match(s)
            or DECOR_RE.match(s)):
        return "", True
    s = re.sub(r"[ \t]{2,}", " ", s)
    return s, False


def main():
    with open(SRC, encoding="utf-8") as f:
        raw = f.read()
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")

    parts = MARK_RE.split(raw)
    # parts: [pre, num1, title1, body1, num2, title2, body2, ...]
    header = parts[0]
    chapters = []
    for i in range(1, len(parts), 3):
        chapters.append((int(parts[i]), parts[i + 1].strip(), parts[i + 2]))

    stats = Counter()
    index_rows = []
    out_blocks = []
    body_hashes = {}
    pos = 0

    if header.strip():
        out_blocks.append(header.strip() + "\n\n")
        pos += len(header) + 1

    for num, title, body in chapters:
        stats["chapters"] += 1
        lines = body.split("\n")
        cleaned = []
        for j, ln in enumerate(lines):
            s, removed = clean_line(ln)
            if removed:
                stats["removed_lines:" + ("title_header" if s == "" else "noise")] += 1
                stats["removed_lines"] += 1
                continue
            if not s:
                stats["blank"] += 1
            cleaned.append(s)
        # 压缩连续空行
        compact = []
        blank_run = 0
        for s in cleaned:
            if s == "":
                blank_run += 1
                if blank_run > 1:
                    stats["collapsed_blank"] += 1
                    continue
            else:
                blank_run = 0
            compact.append(s)
        while compact and compact[0] == "":
            compact.pop(0)
        while compact and compact[-1] == "":
            compact.pop()

        body_text = "\n".join(compact)
        nchars = len(re.sub(r"\s", "", body_text))

        # 章节级 dedupe（内容哈希，忽略空白差异）
        h = hashlib.md5(re.sub(r"\s", "", body_text).encode("utf-8")).hexdigest()
        noise_tag = is_noise_title(title)
        dup_of = None
        if h in body_hashes:
            dup_of = body_hashes[h]
            stats["dup_chapters"] += 1
        elif noise_tag is None:  # 噪声章（后记/特典等常为短文）不参与正文哈希登记
            body_hashes[h] = num

        marker = f"<<<CHAPTER {num:04d} | {title}>>>"
        if noise_tag:
            marker += f" [NOISE:{noise_tag}]"
            stats["noise_chapters"] += 1
        if dup_of is not None:
            marker += f" [DUP:OF {dup_of:04d}]"
            block = marker + "\n\n"
        else:
            block = marker + "\n\n" + (body_text + "\n" if body_text else "")

        index_rows.append((num, title, nchars, pos))
        out_blocks.append(block)
        pos += len(block)
        stats["total_chars"] += nchars

    with open(OUT_CLEAN, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out_blocks))

    with open(OUT_INDEX, "w", encoding="utf-8", newline="\n") as f:
        f.write("chapter_no\ttitle\tchar_count\tfile_offset\n")
        for num, title, nchars, off in index_rows:
            f.write(f"{num:04d}\t{title}\t{nchars}\t{off}\n")

    report = {
        "source_file": "corpus/mishen_full.txt",
        "clean_file": "corpus/clean_full.txt",
        "total_chapters": stats["chapters"],
        "noise_chapters": stats["noise_chapters"],
        "dup_chapters": stats["dup_chapters"],
        "removed_noise_lines": stats["removed_lines"],
        "collapsed_blank_lines": stats["collapsed_blank"],
        "total_body_chars_nospace": stats["total_chars"],
        "rules": "见脚本头部注释 scripts/01_clean_normalize.py",
    }
    with open(OUT_REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
