# -*- coding: utf-8 -*-
"""P5 增强合并：_tmp_全/*.json → 全事件表
- 按 story_anchor 中的 block_id 去重（保留信息更全者）
- 归一化别名（化名主名双保留，检索层归一）
- 输出 merged 全表 + 统计
"""
import os, json, glob, re
from collections import Counter

BASE = r"D:/DeepSeek Harness专用！危险！！！！！/迷深清洗工作2/年表输出"
TMP = os.path.join(BASE, "_tmp_全")
MERGED = os.path.join(BASE, "_merged")

def block_ids_of(ev):
    s = ev.get("story_anchor", "") or ""
    return set(m.group(1) for m in re.finditer(r"(md-\d+)", s))

def main():
    os.makedirs(MERGED, exist_ok=True)
    raw = []
    for fp in sorted(glob.glob(os.path.join(TMP, "*.json"))):
        try:
            d = json.load(open(fp, encoding="utf-8"))
            raw.extend(d)
        except Exception as e:
            print(f"[ERR] {os.path.basename(fp)}: {e}")
    print(f"RAW total: {len(raw)}")

    # 去重：按 block_id 集合重叠 判定
    # 策略：块重叠>=1 视为重复候选，保留 description 更长者
    dedup = []
    used_blocks = {}  # block_id -> idx in dedup
    for ev in raw:
        bset = block_ids_of(ev)
        # 找已存在且重叠
        merged_into = None
        for bid in bset:
            if bid in used_blocks:
                merged_into = used_blocks[bid]
                break
        if merged_into is None:
            used_blocks.clear()  # 仅对当前批次
            for bid in bset:
                used_blocks[bid] = len(dedup)
            dedup.append(ev)
        else:
            # 比较长度，保留更长者
            exist = dedup[merged_into]
            if len(ev.get("description","")) > len(exist.get("description","")):
                dedup[merged_into] = ev
    print(f"DEDUP total: {len(dedup)}")

    out = os.path.join(MERGED, "events_all.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(dedup, f, ensure_ascii=False, indent=1)

    tl = Counter(e.get("timeline_layer") for e in dedup)
    et = Counter(e.get("event_type") for e in dedup)
    cf = Counter(e.get("confidence") for e in dedup)
    print("timeline_layer:", dict(tl))
    print("event_type:", dict(et))
    print("confidence:", dict(cf))
    print(f"-> {out} ({len(dedup)} 条)")

if __name__ == "__main__":
    main()
