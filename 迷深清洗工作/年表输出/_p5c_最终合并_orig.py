# -*- coding: utf-8 -*-
"""P5 最终合并：全事件去重 + 按时间线分层重编 event_id + 统一排序。

流程：
1. 读取 _tmp_全/*.json 全部事件
2. 按 story_anchor 的 block_id 去重（保留 description 更长者）
3. 按 event_time 解析排序键（T0/T1/T2/T4/T3 千年序）
4. 重编 event_id: T{line}-{4位序号}
5. 输出 events_all.json + 统计
"""
import os, json, glob, re
from collections import Counter

BASE = r"D:/DeepSeek Harness专用！危险！！！！！/迷深清洗工作2/年表输出"
TMP = os.path.join(BASE, "_tmp_全")
MERGED = os.path.join(BASE, "_merged")

# 时间线排序权重
LAYER_ORDER = {"T0": 0, "T1": 1, "T2": 2, "T4": 3, "T3": 4}

def block_key(ev):
    """从 story_anchor 提取可排序的 block 数字（跨章唯一化：取最大数字段）"""
    s = ev.get("story_anchor", "") or ""
    nums = [int(m.group(1)) for m in re.finditer(r"(?:7[123]md|md)-(\d+)", s)]
    return max(nums) if nums else 0

def block_set(ev):
    s = ev.get("story_anchor", "") or ""
    return set(int(m.group(1)) for m in re.finditer(r"(?:7[123]md|md)-(\d+)", s))

def time_rank(ev):
    layer = ev.get("timeline_layer", "T3")
    return LAYER_ORDER.get(layer, 4)

def main():
    os.makedirs(MERGED, exist_ok=True)
    raw = []
    src_files = sorted(glob.glob(os.path.join(TMP, "*.json")))
    for fp in src_files:
        try:
            d = json.load(open(fp, encoding="utf-8"))
            for e in d:
                e["_src"] = os.path.basename(fp)
            raw.extend(d)
        except Exception as ex:
            print("[ERR] %s: %s" % (os.path.basename(fp), str(ex)[:60]))
    print("RAW 总事件:", len(raw))

    # ── 去重：block 重叠判定，保留 description 更长者
    dedup = []
    block_owner = {}  # block_id -> index in dedup
    for ev in raw:
        bs = block_set(ev)
        owner = None
        for b in bs:
            if b in block_owner:
                owner = block_owner[b]
                break
        if owner is None:
            for b in bs:
                block_owner[b] = len(dedup)
            dedup.append(ev)
        else:
            exist = dedup[owner]
            if len(ev.get("description", "")) > len(exist.get("description", "")):
                dedup[owner] = ev
    print("去重后:", len(dedup))

    # ── 分层重编 event_id
    buckets = {l: [] for l in LAYER_ORDER}
    for ev in dedup:
        buckets.get(ev.get("timeline_layer", "T3"), []).append(ev)
    for l, arr in buckets.items():
        arr.sort(key=lambda e: (block_key(e), e.get("event_id", "")))
    final = []
    for l in ["T0", "T1", "T2", "T4", "T3"]:
        for i, ev in enumerate(buckets[l], 1):
            ev["event_id"] = "%s-%04d" % (l, i)
            ev.pop("_src", None)
            final.append(ev)
    print("重编后:", len(final))

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
