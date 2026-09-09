# -*- coding: utf-8 -*-
"""P5a 合并 _tmp_全/*.json → _merged/events_all.json，临时编号 EV-xxx 重编为 T0/T1/T2/T3/T4-XXXX。
并输出统计。"""
import os, json, glob
from collections import Counter

BASE = r"D:/DeepSeek Harness专用！危险！！！！！/迷深清洗工作2/年表输出"
TMP_DIR = os.path.join(BASE, "_tmp_全")
MERGED_DIR = os.path.join(BASE, "_merged")
LAYER_ORDER = ["T0", "T1", "T2", "T4", "T3"]  # 千年顺序（T4 在 T2 与 T3 之间）

def main():
    os.makedirs(MERGED_DIR, exist_ok=True)
    all_events = []
    seen = {}
    for fp in sorted(glob.glob(os.path.join(TMP_DIR, "*.json"))):
        try:
            with open(fp, encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"[ERR] {os.path.basename(fp)}: {e}")
            continue
        if not isinstance(data, list):
            print(f"[ERR] {os.path.basename(fp)}: 非数组")
            continue
        for ev in data:
            if not isinstance(ev, dict):
                continue
            all_events.append(ev)
        print(f"[OK] {os.path.basename(fp)}: {len(data)} 条")
    print(f"\nTOTAL raw: {len(all_events)}")

    # 按 timeline_layer 分组，各层重编 event_id
    by_layer = {L: [] for L in LAYER_ORDER}
    for ev in all_events:
        tl = ev.get("timeline_layer") or "T3"
        if tl not in by_layer:
            tl = "T3"
        by_layer[tl].append(ev)

    final = []
    counters = {L: 0 for L in LAYER_ORDER}
    for L in LAYER_ORDER:
        for ev in by_layer[L]:
            counters[L] += 1
            ev["event_id"] = f"{L}-{counters[L]:04d}"
            final.append(ev)

    out = os.path.join(MERGED_DIR, "events_all.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=1)

    tl = Counter(e.get("timeline_layer") for e in final)
    et = Counter(e.get("event_type") for e in final)
    cf = Counter(e.get("confidence") for e in final)
    print("timeline_layer:", dict(tl))
    print("event_type:", dict(et))
    print("confidence:", dict(cf))
    print(f"TOTAL final: {len(final)} -> {out}")

if __name__ == "__main__":
    main()
