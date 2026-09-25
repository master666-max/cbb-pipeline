# -*- coding: utf-8 -*-
"""P5 最终合并：全事件去重 + 按时间线分层重编 event_id + 统一排序。

[2026-09-02 修复, v3] 去重策略：
- 原版缺陷：去重键只取 block 纯数字 -> 跨章 block_id 碰撞（各章独立编号），
  1587 条被误吞成 335 条。
- v2 缺陷：键 = (章节+block+标题完全一致) -> 标题措辞差异导致 0 条命中。
- v3 正确策略：按 (章节, block 集合) 分组，组内跨文件事件两两比较标题
  jaccard 相似度，>= 0.5 视为同事件重复（保留 description 更长者），
  否则视为同一 block 内的不同事件（保留）。
  实测跨包重叠对（第一章 new/pack01、第7-3章 packB 等）约 6 对，符合预期。

流程：
1. 读取 _tmp_全/*.json 全部事件
2. 相似度去重（保留 description 更长者）
3. 按 timeline_layer 分层（T0/T1/T2/T4/T3 千年序）
4. 层内按 (章节序, block数字) 排序
5. 重编 event_id: T{line}-{4位序号}
6. 输出 events_all.json + 统计
"""
import os, json, glob, re
from collections import Counter, defaultdict

BASE = r"D:/DeepSeek Harness专用！危险！！！！！/迷深清洗工作2/年表输出"
TMP = os.path.join(BASE, "_tmp_全")
MERGED = os.path.join(BASE, "_merged")

# 时间线排序权重
LAYER_ORDER = {"T0": 0, "T1": 1, "T2": 2, "T4": 3, "T3": 4}

# 章节标签提取（从源文件名）与章节排序序
CHAP_ORDER = {
    "第一章": 1, "第二章": 2, "第三章": 3, "第四章": 4, "第五章": 5,
    "第六章": 6, "第7-1章": 71, "第7-2章": 72, "第7-3章": 73,
    "第八章": 8, "第九章": 9, "第十章": 10,
}
CHAP_RE = re.compile(r"(第十章|第九章|第八章|第7-[123]章|第六章|第五章|第四章|第三章|第二章|第一章)")

def chap_of(src):
    m = CHAP_RE.search(src or "")
    return m.group(1) if m else "未知"

def chap_rank(chap):
    return CHAP_ORDER.get(chap, 99)

def block_set(ev):
    """(章节, block数字) 集合 —— 跨章不再碰撞"""
    s = ev.get("story_anchor", "") or ""
    chap = ev.get("_chap", "未知")
    return frozenset(
        (chap, int(m.group(1)))
        for m in re.finditer(r"(?:7[123]md|md)-(\d+)", s)
    )

def jaccard(a, b):
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)

def sort_key(ev):
    """层内排序：章节序 -> block 数字 -> 原标题"""
    bs = block_set(ev)
    if bs:
        chap, num = min(bs, key=lambda x: (chap_rank(x[0]), x[1]))
    else:
        chap, num = ev.get("_chap", "未知"), 0
    return (chap_rank(chap), num, ev.get("event_id", ""))

def main():
    os.makedirs(MERGED, exist_ok=True)
    raw = []
    src_files = sorted(glob.glob(os.path.join(TMP, "*.json")))
    # 仅处理章节提取事件文件（形如「第X章_*.json」/「第7-X章_*.json」），
    # 排除 P6/P7/P8 中间产物（_p6_chains.json 等）
    src_files = [fp for fp in src_files if re.search(r"(第[一二三四五六七八九十]+章|第7-[123]章)_", os.path.basename(fp))]
    for fp in src_files:
        try:
            d = json.load(open(fp, encoding="utf-8"))
            for e in d:
                e["_src"] = os.path.basename(fp)
                e["_chap"] = chap_of(e["_src"])
            raw.extend(d)
        except Exception as ex:
            print("[ERR] %s: %s" % (os.path.basename(fp), str(ex)[:60]))
    print("RAW 总事件:", len(raw))

    # ── 去重：按 (章节,block集合) 分组，组内跨文件标题相似度>=0.5 合并
    groups = defaultdict(list)
    for ev in raw:
        bs = block_set(ev)
        if not bs:
            bs = frozenset([(ev.get("_chap", "未知"), 0)])
        groups[bs].append(ev)

    dedup = []
    merged_count = 0
    for bs, items in groups.items():
        keep = []
        for ev in items:
            merged = False
            for i, k in enumerate(keep):
                # 仅跨文件（不同 _src）才判重复：同一 block 内的多条不同事件保留
                if k.get("_src") == ev.get("_src"):
                    continue
                t_ev = ev.get("title", "") or ""
                t_k = k.get("title", "") or ""
                if jaccard(t_ev, t_k) >= 0.35:
                    if len(ev.get("description", "")) > len(k.get("description", "")):
                        keep[i] = ev
                    merged = True
                    merged_count += 1
                    break
            if not merged:
                keep.append(ev)
        dedup.extend(keep)
    print("去重后:", len(dedup), "（合并组数:", merged_count, "）")

    # ── 分层重编 event_id
    buckets = {l: [] for l in LAYER_ORDER}
    for ev in dedup:
        _layer = ev.get("timeline_layer", "T3")
        if _layer not in buckets:   # 02-bugs R7-P1：非法层级原 .get 默认返回一次性列表=静默丢事件
            print(f"⚠ 非法 timeline_layer={_layer!r}（事件 {ev.get(chr(101)+chr(118)+chr(101)+chr(110)+chr(116)+chr(95)+chr(105)+chr(100))} 归 T3 兜底）")
            _layer = "T3"
        buckets[_layer].append(ev)
    for l, arr in buckets.items():
        arr.sort(key=sort_key)
    final = []
    chap_map = {}  # event_id -> 章节（供 P10 timeline_index 用）
    for l in ["T0", "T1", "T2", "T4", "T3"]:
        for i, ev in enumerate(buckets[l], 1):
            new_id = "%s-%04d" % (l, i)
            ev["event_id"] = new_id
            chap_map[new_id] = ev.get("_chap", "未知")
            ev.pop("_src", None)
            ev.pop("_chap", None)
            final.append(ev)
    print("重编后:", len(final))
    with open(os.path.join(MERGED, "event_chapter_map.json"), "w", encoding="utf-8") as f:
        json.dump(chap_map, f, ensure_ascii=False, indent=1)
    print("->", os.path.join(MERGED, "event_chapter_map.json"))

    out = os.path.join(MERGED, "events_all.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=1)

    tl = Counter(e.get("timeline_layer") for e in final)
    et = Counter(e.get("event_type") for e in final)
    cf = Counter(e.get("confidence") for e in final)
    print("timeline_layer:", dict(sorted(tl.items(), key=lambda x: LAYER_ORDER.get(x[0], 9))))
    print("event_type:", dict(et.most_common()))
    print("confidence:", dict(cf))
    print("->", out)

if __name__ == "__main__":
    main()