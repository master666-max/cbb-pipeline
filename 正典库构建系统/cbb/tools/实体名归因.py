# -*- coding: utf-8 -*-
"""实体名归因.py — 把图谱产物里"名字在原文找不到"拆成四类，各给处置，不许一刀切

为什么需要它（2026-09-25 本机实测，GraphRAG 卷1 冒烟 102 个实体）：
  派生层（GraphRAG/LightRAG/社区报告）产出的实体名有 16 个在原文里**字面找不到**。
  整句"图抽得不准"没法处置——四种成因的修法完全不同，而默认动作（要么全删要么全收）都错：
    全删 ⇒ 把最有价值的归纳标签（事件名、主题名）一起扔了；
    全收 ⇒ 模型自造的词进库当事实，L2 证据门当场失效（引文必须逐字子串这条守的是这个）。

四类与归属（实测数＝86 命中／A 2／B 1／C 0／D 13）：
  命中      原文逐字能找到
  A 写法变体  归一化（去间隔号/空白/全半角）后能找到 ⇒ 锅在模型少写或多写了标点，机械可救
  B 括注修饰  剥掉（代称）这类括注后能找到 ⇒ 括注内容转别名，名字本体仍可用
  C 转换吃字符 模型**原始回执里有**正确写法且能精确命中，终值却命中不了 ⇒ 锅在流水线清洗，
             该开上游缺陷单，不许改数据。判 C 靠 --raw-dir，缺该参数时 C 类只能记 UNKNOWN，
             不许默认判成模型的锅（实测 graphrag 的 clean_str 只删控制字符，C 类＝0）
  D 真自造词  都不中。再分两小类，价值与处置完全不同：
    D1 可合成  拆得出 ≥1 个原文成词片段（`梅芙莉莎的手枪`←梅芙莉莎+手枪；`天空都市·…的苍之学园`
               是层级路径被压成专名）⇒ 当 proposed 标签，必须记 grounded_to（成素＋支撑块）
    D2 纯命名  拆不出（`终末对抗`/`接吻行为`/`轻小说情节`）⇒ interpretation：**永不进 confirmed**，
               只当检索别名与主题候选；它给"一段动作/一簇现象"起名，正是人读三遍才会做的动作

三条纪律写进代码，不靠自觉：
  1. **零支撑不许立词**：D 类若无支撑块计数（--in 里的 support 字段），判 reject 不判 proposed；
  2. **匹配键只认命中类与 A/B 归一后的名字**，D 类一律不得进受控词表与去重键；
  3. **口径上界自己印出来**：字面命中只证"这词出处有"，不证"这实体含义对"；
     未命中也不等于幻觉（可能跨章全称、译名差异）——两端都不许被读成结论。

用法：
  py -X utf8 实体名归因.py --in entities.jsonl --corpus <语料文件或目录> \
      [--raw-dir cache/extract_graph] [--strict] [--out 归因.json]
  输入 --in 支持：每行一名 .txt / .jsonl / .json（对象数组）/ .csv，字段名兼容 name|title|entity。
退出码：0 正常；1 = --strict 且存在 reject 项（零支撑的自造词）。
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

# 归一口径：空白／各类间隔号／连字符全去掉，再做 NFKC（全角→半角），最后小写。
SEP_RE = re.compile(r"[\s\u3000·・‧⋅•.。_－—–\-/、,，:：;；]")
PAREN_RE = re.compile(r"[（(][^（()）]*[)）]")
SPLIT_RE = re.compile(r"的|之|与|和")
NAME_KEYS = ("name", "title", "entity", "canonical_name")
SUPPORT_KEYS = ("support", "frequency", "n_sources", "text_unit_count")


def canon(s: str) -> str:
    """归一化：去分隔符 + NFKC + 小写。用于区分"写法变体"与"真造词"。"""
    return SEP_RE.sub("", unicodedata.normalize("NFKC", str(s))).lower()


def load_rows(path: Path) -> list[dict]:
    """读名单。自动认 .txt/.json/.jsonl/.csv；纯文本按每行一名。"""
    txt = path.read_text(encoding="utf-8")
    if path.suffix == ".txt":
        return [{"name": ln.strip()} for ln in txt.splitlines() if ln.strip()]
    if path.suffix == ".csv":
        return list(csv.DictReader(txt.splitlines()))
    if path.suffix == ".jsonl":
        return [json.loads(l) for l in txt.splitlines() if l.strip()]
    data = json.loads(txt)
    if isinstance(data, dict):                       # graphrag 风格 {"entities": [...]}
        for k in ("entities", "items", "rows", "data"):
            if isinstance(data.get(k), list):
                return data[k]
        return [data]
    return list(data)


def pick(row: dict, keys: tuple[str, ...]) -> str | None:
    for k in keys:
        if k in row and row[k] not in (None, ""):
            return str(row[k])
    return None


def support_of(row: dict) -> int | None:
    v = pick(row, SUPPORT_KEYS)
    if v is None:
        # text_unit_ids 这类列表字段也算支撑计数
        for k in ("text_unit_ids", "source_ids", "chunk_ids"):
            if isinstance(row.get(k), list):
                return len(row[k])
        return None
    try:
        return int(float(v))
    except ValueError:
        return None


def _names_in(text: str) -> list[str]:
    r"""从一段（已解码的）回执文本里抓候选名字。

    注意必须先解码再抓：graphrag 的 cache 是 JSON，正文里的引号在文件里是转义形态，
    直接对整个文件文本跑引号正则会把 `"弗恩·西蒙"` 拆成 `他提到\"` 与 `一次` 两段假命中
    （本函数就是这么被抓出来的——实测教训）。
    """
    out: list[str] = []
    for chunk in re.split(r"\|[<>#*（）()【】\[\]{}]+|\n+", text):
        c = chunk.strip(" \"',;:、。「」『』")
        if 1 <= len(c) <= 60:
            out.append(c)
    out += re.findall(r'"([^"\n]{1,60})"', text)
    out += re.findall(r"[「『]([^」』\n]{1,60})[」』]", text)
    return out


def walk_strings(obj) -> list[str]:
    if isinstance(obj, str):
        return [obj]
    if isinstance(obj, dict):
        return [s for v in obj.values() for s in walk_strings(v)]
    if isinstance(obj, list):
        return [s for v in obj for s in walk_strings(v)]
    return []


def raw_spellings(d: Path | None) -> dict[str, list[str]]:
    """从模型原始回执目录里建「归一名 → 原始写法列表」索引，用来判 C 类。

    JSON（graphrag cache）先解析再取字符串；纯文本直接扫。抓不到就不记——宁缺不错。
    """
    idx: dict[str, list[str]] = {}
    if not d or not d.exists():
        return idx
    for f in sorted(d.rglob("*")):
        if not f.is_file() or f.suffix.lower() in {".parquet", ".lock", ".arrow"}:
            continue
        try:
            t = f.read_text(encoding="utf-8")
        except Exception:
            continue
        strings: list[str] = []
        if t.lstrip().startswith(("{", "[")):
            try:
                strings = walk_strings(json.loads(t))
            except Exception:
                strings = [t]
        else:
            strings = [t]
        for s in strings:
            for nm in _names_in(s):
                if nm.startswith("$") or "\\n" in nm:
                    continue
                idx.setdefault(canon(nm), []).append(nm)
    return idx


def classify(name: str, corpus_low: str, corpus_norm: str, raws: dict,
             has_raw_index: bool) -> tuple[str, str]:
    """返回 (类, 依据)。类的划分见模块 docstring。

    顺序很要紧：**C 必须排在 A 前面**。终值少写间隔号而原文有——看着像模型的锅（A），
    可如果模型原始回执里写的是对的，那就是流水线清洗吃掉了字符（C）。有原始回执就先判 C，
    没有就诚实标"无法区分"，不许默认把责任推给模型。
    """
    n = canon(name)
    if not n:
        return "D2 纯命名", "归一后为空"
    if str(name).lower() in corpus_low:
        return "命中", "原文逐字（忽略大小写）可定位"
    if has_raw_index:
        for raw in raws.get(n, []):
            if raw.lower() in corpus_low:
                return "C 转换吃字符", f"原始写法「{raw}」本可命中，终值不可"
    if n in corpus_norm:
        return "A 写法变体", ("去分隔符后可定位" if has_raw_index
                          else "去分隔符后可定位（无原始回执，不能排除是清洗吃的字）")
    stripped = PAREN_RE.sub("", str(name))
    if canon(stripped) and canon(stripped) in corpus_norm:
        return "B 括注修饰", "剥括注后可定位"
    parts = [p for p in SPLIT_RE.split(str(name)) if p and canon(p) in corpus_norm]
    if parts:
        return "D1 可合成", f"成素 {parts} 在原文"
    return "D2 纯命名", "无任何原文成素"


DISPOSE = {
    "命中": "可进 canon_name；仍须过引文逐字门",
    "A 写法变体": "归一后作 canon_name，原写法进 aliases",
    "B 括注修饰": "剥括注后作 canon_name，括注内容进 aliases",
    "C 转换吃字符": "开上游清洗缺陷单；数据不改，等上游修好重跑",
    "D1 可合成": "proposed 标签：记 grounded_to（成素＋支撑块），禁入受控词表与去重键",
    "D2 纯命名": "interpretation：永不进 confirmed；只当检索别名/主题候选，须标『非原文逐字』",
}


def main() -> int:
    ap = argparse.ArgumentParser(description="图谱派生层实体名归因（四分类＋处置）")
    ap.add_argument("--in", dest="inp", required=True, type=Path)
    ap.add_argument("--corpus", required=True, type=Path, help="真源语料：文件或目录")
    ap.add_argument("--raw-dir", type=Path, default=None, help="模型原始回执目录（判 C 类用）")
    ap.add_argument("--strict", action="store_true", help="有 reject ⇒ 退出码 1")
    ap.add_argument("--out", type=Path, default=None)
    ns = ap.parse_args()

    if ns.corpus.is_dir():
        texts = [p.read_text(encoding="utf-8", errors="replace")
                 for p in sorted(ns.corpus.rglob("*"))
                 if p.is_file() and p.suffix.lower() in {".txt", ".md", ".csv", ".json"}]
    else:
        texts = [ns.corpus.read_text(encoding="utf-8", errors="replace")]
    blob = "\n".join(texts)
    corpus_low, corpus_norm = blob.lower(), canon(blob)
    raws = raw_spellings(ns.raw_dir)
    has_raw = bool(raws)

    rows = load_rows(ns.inp)
    buckets: dict[str, list] = {}
    for row in rows:
        name = pick(row, NAME_KEYS)
        if not name:
            continue
        cls, why = classify(name, corpus_low, corpus_norm, raws, has_raw)
        sup = support_of(row)
        rec = {"name": name, "why": why, "dispose": DISPOSE[cls], "support": sup}
        if cls.startswith(("D1", "D2")) and sup == 0:
            cls = "reject 零支撑自造"
            rec["dispose"] = "不许立词：无支撑块的 D 类直接退回，不进任何一层"
        buckets.setdefault(cls, []).append(rec)

    order = ["命中", "A 写法变体", "B 括注修饰", "C 转换吃字符",
             "D1 可合成", "D2 纯命名", "reject 零支撑自造"]
    counts = {k: len(buckets.get(k, [])) for k in order if k in buckets}
    out = {
        "口径": {
            "语料": str(ns.corpus), "语料字符数": len(blob), "名单条数": len(rows),
            "原始回执索引": ("有（可判 C）" if has_raw else "无 ⇒ C 类记 UNKNOWN"),
            "归一口径": "去空白与间隔号/连句读 + NFKC + 小写",
        },
        "计数": dict(Counter({k: v for k, v in counts.items()}).items()),
        "明细": {k: buckets[k] for k in order if k in buckets},
        "处置映射": DISPOSE,
    }
    hit = counts.get("命中", 0)
    out["结论"] = (f"字面命中率 {hit}/{len(rows)}；"
                   f"自造标签 {counts.get('D1 可合成', 0) + counts.get('D2 纯命名', 0)} 个"
                   f"（其中零支撑应退回 {counts.get('reject 零支撑自造', 0)} 个）")
    out["口径上界"] = ("字面命中只证『该词出处存在』，不证『该实体含义正确』——子串可能跨语境巧合；"
                       "未命中也不等于幻觉，可能是译名差异或复合全称。两端都不许被读成结论，"
                       "仍需按 references/审查与收口.md 的分层抽样人工对原文。")

    s = json.dumps(out, ensure_ascii=False, indent=1)
    if ns.out:
        ns.out.write_text(s, encoding="utf-8")
    print(s)
    if ns.strict and counts.get("reject 零支撑自造", 0) > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
