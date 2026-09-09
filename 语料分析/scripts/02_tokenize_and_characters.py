# -*- coding: utf-8 -*-
"""
02_tokenize_and_characters.py — 分词 + 人物名候选识别（可重复运行）

输入: corpus/clean_full.txt
输出: analysis/tokens_pos.txt               按章节组织: 章节号<TAB>词/词性 词/词性 ...
      analysis/character_candidates.tsv     TOP50 人物名候选（名字、次数、来源、覆盖章节数）
      analysis/chapter_character_counts.tsv 每章 TOP50 人名出现次数（章节号、人名、次数）
      analysis/character_ngram_raw.json     n-gram 中间结果（便于复查）

方法:
  1) n-gram: 统计 2~5 字 CJK 高频串（带剪枝扩展），加 "XX大人/小姐..." 称谓前置串；
  2) 过滤: jieba 词典外(OOV，日系音译名的典型情况)优先；词典内词只在词性为
     nr/nrt/nrf/nz 且不在人工停用词表、或命中人工译名白名单时保留
     （jieba 会把 小姐/明白/始祖 误标 nr，把 玛利亚 标 ns，海因 标 n，需人工校正）；
  3) 碎片合并: 用候选全集构建"最长匹配"正则，对全文重新计数——只有不在更长
     人名内部的匹配才计入该候选，从而剔出 拉丝缇/娅拉/帕林库 之类碎片；
  4) TOP50 高频候选加入 jieba 自定义词典(tag=nr)后，用 jieba.posseg 全文分词。
"""
import re
import json
import os
import logging
from collections import Counter, defaultdict

import jieba
import jieba.posseg as pseg

jieba.setLogLevel(logging.ERROR)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "corpus", "clean_full.txt")
OUT_TOKENS = os.path.join(BASE, "analysis", "tokens_pos.txt")
OUT_CAND = os.path.join(BASE, "analysis", "character_candidates.tsv")
OUT_CHCOUNT = os.path.join(BASE, "analysis", "chapter_character_counts.tsv")
OUT_NGRAM = os.path.join(BASE, "analysis", "character_ngram_raw.json")

MARK_RE = re.compile(r"^<<<CHAPTER (\d+) \| (.*?)(?:\s*\[NOISE:[^\]]*\])?(?:\s*\[DUP:OF \d+\])?>>>")
CJK_RUN_RE = re.compile(r"[\u4e00-\u9fff]{2,}")
SUFFIX_RE = re.compile(r"([\u4e00-\u9fff]{2,4})(?=大人|小姐|殿下|阁下|同学|酱|陛下)")

# 人名中几乎不可能出现的虚词/常用字
BLACKLIST_CHARS = set(
    "的了是我不有他她它在也和与及或就都还又被把将从向对让使得着之其此各每么"
    "啊吧吗呢哦嗯呀嘛啦喽呗哪这那么什样子地过起来去说想看听知道会能要可以上"
    "下中里外前后左右时天年月日个只条名号些点事儿们很最太更挺非常因为所以"
)
# jieba 误标为 nr/nz 的普通词（人工停用表）
MANUAL_STOP = {
    "小姐", "明白", "始祖", "异世", "同志", "太太", "先生", "女士", "公主", "王子",
    "女王", "陛下", "大人", "魔王", "主人", "皇帝", "国王", "学生", "老师", "同学",
    "大家", "自己", "人类", "魔族", "使徒", "圣女", "女神", "少女", "孩子", "儿子",
    "女儿", "兄弟", "姐妹", "父亲", "母亲", "勇者", "冒险者", "魔法师",
    # 跨词边界产生的 OOV 垃圾 n-gram（人工复核后补充）
    "两人", "并没", "令人", "另一", "没办法", "感受到", "异世界", "次元", "合国",
    "魔石人类", "一切", "一直", "一边", "窃者", "护者", "觉到", "句话",
    "咒术", "魔人", "才行", "术式", "请你", "但却", "师傅", "史诗探索者",
    "探索者", "宣言", "魔石线", "赫尔米娜小", "大小姐", "异邦人",
    "次元魔法", "拜托", "父亲大人",
}
# 术语模式：以这些词结尾的候选按非人名处理（XX魔法/种族词XX人 等）
TERM_SUFFIX_RE = re.compile(r"(魔法|术式|结界|技能|属性|之杖|魔法阵)$|人$")
# 称谓后缀/前缀：候选若为 "人名+称谓" 且去称谓后仍是候选，则视为同一人的变体
TITLE_SUFFIX = ("大人", "先生", "小姐", "酱", "殿下", "阁下", "同学", "陛下", "家")
TITLE_PREFIX = ("始祖",)
# 已知是本作人物但 jieba 标为普通词的译名（人工白名单，依据译名习惯/正文用法）
MANUAL_NAME_WHITELIST = {"海因", "玛利亚", "海莉", "罗密斯", "勒迦希", "法芙纳"}

ALLOW_FLAGS = {"nr", "nr1", "nr2", "nrt", "nrf", "nz"}


def load_chapters():
    chapters = []
    cur = None
    with open(SRC, encoding="utf-8") as f:
        for ln in f:
            m = MARK_RE.match(ln)
            if m:
                cur = {"no": int(m.group(1)), "title": m.group(2).strip(), "lines": []}
                chapters.append(cur)
            elif cur is not None:
                cur["lines"].append(ln.rstrip("\n"))
    for ch in chapters:
        ch["text"] = "\n".join(ch["lines"]).strip()
    return chapters


def ngram_counts(chapters):
    """2~5 字 CJK 串频次（带剪枝扩展）"""
    big = Counter()
    spread2 = defaultdict(set)
    for ch in chapters:
        for run in CJK_RUN_RE.findall(ch["text"]):
            for i in range(len(run) - 1):
                g = run[i:i + 2]
                big[g] += 1
                spread2[g].add(ch["no"])
    results = {}
    for g, c in big.items():
        if c >= 40:
            results[g] = (c, len(spread2[g]))
    level = set(results)
    for n in range(3, 6):
        nxt = Counter()
        spread = defaultdict(set)
        for ch in chapters:
            for run in CJK_RUN_RE.findall(ch["text"]):
                for i in range(len(run) - n + 1):
                    g = run[i:i + n]
                    if g[:-1] in level and g[1:] in level:
                        nxt[g] += 1
                        spread[g].add(ch["no"])
        level = set()
        for g, c in nxt.items():
            if c >= 20:
                results[g] = (c, len(spread[g]))
                level.add(g)
    return results


def suffix_counts(chapters):
    c = Counter()
    spread = defaultdict(set)
    for ch in chapters:
        for m in SUFFIX_RE.finditer(ch["text"]):
            g = m.group(1)
            c[g] += 1
            spread[g].add(ch["no"])
    return {g: (cnt, len(spread[g])) for g, cnt in c.items() if cnt >= 20}


def word_flag(g):
    """整词在 jieba 词典中则返回其词性，否则返回 None (OOV)"""
    if g in jieba.dt.FREQ and jieba.dt.FREQ[g]:
        w = list(pseg.cut(g, HMM=False))
        if len(w) == 1:
            return w[0].flag
        return "MULTI"  # 词典路径与分词路径不一致，按 OOV 处理
    return None


def plausible_name(g, count, spread):
    if len(g) < 2 or len(g) > 5 or count < 20 or spread < 3:
        return False
    if any(c in BLACKLIST_CHARS for c in g):
        return False
    if g in MANUAL_STOP:
        return False
    if TERM_SUFFIX_RE.search(g):
        return False
    flag = word_flag(g)
    if flag is None or flag == "MULTI":
        return True                      # OOV —— 音译名典型情况
    if g in MANUAL_NAME_WHITELIST:
        return True
    return flag in ALLOW_FLAGS


def main():
    jieba.initialize()  # 关键：FREQ 为懒加载，必须先显式初始化，否则词典判断全部失效
    chapters = load_chapters()
    print(f"loaded {len(chapters)} chapters", flush=True)

    ng = ngram_counts(chapters)
    sf = suffix_counts(chapters)
    print(f"raw ngram: {len(ng)}, suffix: {len(sf)}", flush=True)

    pool = {}
    for src, dic in (("ngram", ng), ("suffix", sf)):
        for g, (c, sp) in dic.items():
            if g in pool or not plausible_name(g, c, sp):
                continue
            pool[g] = (c, sp, src)
    print(f"pool after filter: {len(pool)}", flush=True)

    # ---- 最长匹配重计数（碎片合并核心）----
    # blocker = 候选全集 + 所有高频 n-gram（含被过滤掉的词典词如 盗窃者/感觉到/守护者），
    # 词典词同样参与"占位"，避免 盗窃者 的尾巴 窃者 被误计为独立候选
    blockers = set(pool) | {g for g, (c, _) in ng.items() if c >= 40}
    b_sorted = sorted(blockers, key=lambda g: (-len(g), -pool.get(g, (0, 0, ""))[0]))
    alt = re.compile("(" + "|".join(re.escape(g) for g in b_sorted) + ")")
    max_cnt = Counter()
    max_spread = defaultdict(set)
    for ch in chapters:
        for m in alt.finditer(ch["text"]):
            g = m.group(1)
            if g in pool:
                max_cnt[g] += 1
                max_spread[g].add(ch["no"])

    # ---- 称谓变体合并：涡波大人/始祖涡波 → 涡波 ----
    merged = {g: [c, len(max_spread[g])] for g, c in max_cnt.items()
              if c >= 30 and len(max_spread[g]) >= 3}
    drop = set()
    for g in list(merged):
        base = None
        for t in TITLE_SUFFIX:
            if g.endswith(t) and g[:-len(t)] in merged:
                base = g[:-len(t)]
        for t in TITLE_PREFIX:
            if g.startswith(t) and g[len(t):] in merged:
                base = g[len(t):]
        if base:
            merged[base][0] += merged[g][0]
            merged[base][1] = max(merged[base][1], merged[g][1])
            drop.add(g)
    for g in drop:
        merged.pop(g)

    ranked = [(g, v[0], v[1], pool[g][2], pool[g][0]) for g, v in merged.items()]
    ranked.sort(key=lambda t: -t[1])
    top50 = ranked[:50]

    with open(OUT_CAND, "w", encoding="utf-8", newline="\n") as f:
        f.write("名字\t次数\t来源\t覆盖章节数\tngram原始频次\n")
        for g, c, sp, src, rawc in top50:
            f.write(f"{g}\t{c}\t{src}\t{sp}\t{rawc}\n")

    # ---- TOP 候选加入词典后全文 posseg 分词 ----
    for g, c, _, _, _ in ranked[:300]:
        jieba.add_word(g, freq=max(c, 100), tag="nr")
    total_tokens = 0
    with open(OUT_TOKENS, "w", encoding="utf-8", newline="\n") as tok:
        for ch in chapters:
            words = pseg.lcut(ch["text"], HMM=True)
            toks = [f"{w}/{f}" for w, f in words]
            tok.write(f"{ch['no']:04d}\t" + " ".join(toks) + "\n")
            total_tokens += len(toks)
    print(f"tokens: {total_tokens}", flush=True)

    # ---- 每章 TOP50 人名子串计数 ----
    names = [g for g, _, _, _, _ in top50]
    with open(OUT_CHCOUNT, "w", encoding="utf-8", newline="\n") as f:
        f.write("章节号\t人名\t次数\n")
        for ch in chapters:
            t = ch["text"]
            for g in names:
                c = t.count(g)
                if c:
                    f.write(f"{ch['no']:04d}\t{g}\t{c}\n")

    with open(OUT_NGRAM, "w", encoding="utf-8") as f:
        json.dump({"ngram": {g: list(v) for g, v in ng.items()},
                   "suffix": {g: list(v) for g, v in sf.items()}},
                  f, ensure_ascii=False)

    print("TOP50 (maximal-match count):")
    for row in top50:
        print(f"  {row[0]}\t{row[1]}\t{row[2]}\t{row[3]}")
    json.dump({"total_tokens": total_tokens}, open(
        os.path.join(BASE, "analysis", "token_count.json"), "w", encoding="utf-8"),
        ensure_ascii=True)


if __name__ == "__main__":
    main()
