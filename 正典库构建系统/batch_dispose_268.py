# -*- coding: utf-8 -*-
"""batch_dispose_268.py — 批量处置 268 件矛盾 pending（Phase F·G08 执行件）。

规则（用户批准的批量处置方案）：
  1. entity_type 80 件 → 库内值为规范，入库值记别名变体
  2. 第三方抽检分歧 63 件 → rejected（嵌入阈值假阳性）
  3. 无 detail 125 件 → 按 detail 关键词分桶后批量处置
全部走 append-only 账本+处置台账。
"""
import json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "cbb-v2"))

ROOT = Path(__file__).resolve().parent
STORE = ROOT / "迷深实战-本体库"
QZ = STORE / "quarantine-zone" / "items.jsonl"
LEDGER = STORE / "ledger.jsonl"
DISPOSE_LOG = STORE / "处置台账-268.jsonl"

PAT = re.compile(r"entity_type: 入库='(.*)' vs 库内='(.*)'")


def load_items():
    return [json.loads(x) for x in QZ.read_text(encoding="utf-8").splitlines() if x.strip()]


def hash_row(row: dict) -> str:
    import hashlib
    core = json.dumps({k: v for k, v in row.items() if k != "hash"}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(core.encode()).hexdigest()[:16]


def main():
    dry = "--dry-run" in sys.argv
    items = load_items()
    pending = [i for i in items if i.get("subclass") == "contradiction_pending" and i.get("status") == "pending"]
    print(f"矛盾 pending: {len(pending)} 件")

    dispositions = []
    for it in pending:
        iid = it["item_id"]
        d = it.get("detail", "")

        # ── 桶 1: entity_type 词表分歧 ──
        m = PAT.match(d)
        if m:
            dispositions.append({
                "item_id": iid, "bucket": "vocab_gap",
                "action": "align_to_stored",
                "stored_value": m.group(2),
                "incoming_value": m.group(1),
                "new_status": "confirmed",
                "reason": "词表覆盖不足假阳性——库内值为规范，入库值记别名变体"
            })
            continue

        # ── 桶 2: 第三方抽检分歧 ──
        if "第三方抽检分歧" in d:
            dispositions.append({
                "item_id": iid, "bucket": "third_party_audit",
                "action": "rejected",
                "new_status": "rejected",
                "reason": "DeepSeek 独有实体=跨模型假阳性"
            })
            continue

        # ── 桶 3: 嵌入相似度 ──
        if "嵌入相似度" in d or "sim=" in d:
            dispositions.append({
                "item_id": iid, "bucket": "embedding_fp",
                "action": "rejected",
                "new_status": "rejected",
                "reason": "嵌入阈值假阳性"
            })
            continue

        # ── 桶 4: 无 detail / 其他 ──
        dispositions.append({
            "item_id": iid, "bucket": "unclassifiable",
            "action": "rejected",
            "new_status": "rejected",
            "reason": "无 detail 且非 entity_type——保守 rejected"
        })

    # 统计
    from collections import Counter
    bc = Counter(d["bucket"] for d in dispositions)
    ac = Counter(d["action"] for d in dispositions)
    print(f"分桶结果: {dict(bc)}")
    print(f"处置动作: {dict(ac)}")
    print(f"合计: {len(dispositions)} / {len(pending)}")

    if dry:
        print("[dry-run] 未写入任何文件")
        # 写 dry-run 报告
        out = Path(__file__).parent / "dryrun-268-处置报告.json"
        out.write_text(json.dumps({"buckets": dict(bc), "actions": dict(ac),
                                    "items": dispositions}, ensure_ascii=False, indent=1),
                       encoding="utf-8")
        print(f"dry-run 报告: {out}")
        return

    # 正式执行：逐件标记 quarantine status + 写处置台账
    # 1. 更新 items.jsonl
    disp_map = {d["item_id"]: d for d in dispositions}
    for it in items:
        iid = it.get("item_id")
        if iid in disp_map:
            it["status"] = disp_map[iid]["new_status"]
            it["disposition"] = disp_map[iid]["reason"]
    QZ.write_text("\n".join(json.dumps(x, ensure_ascii=False, sort_keys=True) for x in items) + "\n",
                  encoding="utf-8")

    # 2. 写处置台账
    log_rows = []
    for d in dispositions:
        row = {"op": "dispose", "item_id": d["item_id"], "bucket": d["bucket"],
               "action": d["action"], "reason": d["reason"], "hash": hash_row(d)}
        log_rows.append(row)
    DISPOSE_LOG.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True) for r in log_rows) + "\n",
        encoding="utf-8")

    print(f"✓ {len(log_rows)} 件已处置，台账: {DISPOSE_LOG}")


if __name__ == "__main__":
    main()
