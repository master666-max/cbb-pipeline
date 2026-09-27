# -*- coding: utf-8 -*-
"""g09_preserve_186.py — 信息保全 186 件逐条 review 处置（总工单 G09 执行件）。

对象：迷深实战-工作区/积压重分流-信息保全-20260926.json——合并时"更富的入库
entity_type"被"较瘦的库内值"顶掉的 186 件。
处置法（保守方向：拿不准就保全）：
  - 入库限定语字符集 ⊆ 库内限定语且不长于库内 → subsumed_no_loss（无信息损失，仅登记）
  - 其余（含无法解析形态）→ 转互补陈述事件保全入库富值 + 登记事件 id
产出：迷深实战-本体库/信息保全处置台账-186.jsonl（append-only，幂等）+
      complementary-statements.jsonl 追加事件（幂等键 event_id）。
判据：186 条全数有 disposition 行。
"""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STORE = ROOT / "迷深实战-本体库"
SRC = ROOT / "迷深实战-工作区" / "积压重分流-信息保全-20260926.json"
LEDGER_OUT = STORE / "信息保全处置台账-186.jsonl"
COMP = STORE / "complementary-statements.jsonl"
AT = "2026-09-27"  # 伪锚点日历取值（处置日）

TYPE_RE = re.compile(r"^(?P<base>[^(（]+)[(（](?P<q>[^)）]*)[)）]?$")


def event_id_of(about: str, field: str, at: str) -> str:
    core = json.dumps({"about": about, "field": field, "at": at},
                      ensure_ascii=False, sort_keys=True)
    return "ce-" + hashlib.sha256(core.encode("utf-8")).hexdigest()[:16]


def main():
    items = json.loads(SRC.read_text(encoding="utf-8"))
    done = set()
    if LEDGER_OUT.exists():
        for l in LEDGER_OUT.read_text(encoding="utf-8").splitlines():
            if l.strip():
                done.add(json.loads(l)["item_id"])
    comp_existing = set()
    if COMP.exists():
        for l in COMP.read_text(encoding="utf-8").splitlines():
            if l.strip():
                comp_existing.add(json.loads(l).get("event_id"))

    rows, events = [], []
    for it in items:
        iid = it["item_id"]
        if iid in done:
            continue  # 幂等：已处置跳过
        identity = it.get("identity", "")
        incoming = (it.get("entity_type") or {}).get("incoming", "")
        kept = (it.get("entity_type") or {}).get("kept", "")
        mi, mk = TYPE_RE.match(incoming or ""), TYPE_RE.match(kept or "")
        row = {"item_id": iid, "identity": identity,
               "incoming": incoming, "kept": kept, "at": AT}
        if incoming == kept or not incoming:
            row["disposition"] = "identical_no_action"
        elif mi and mk and mi.group("base") == mk.group("base") \
                and set(mi.group("q")) <= set(mk.group("q")) \
                and len(mi.group("q")) <= len(mk.group("q")):
            row["disposition"] = "subsumed_no_loss"
        else:
            about = f"info-preserve:{iid}"
            eid = event_id_of(about, "entity_type", AT)
            if eid not in comp_existing:
                events.append({
                    "about": about, "at": AT, "event_id": eid, "evidence": [],
                    "fields": {"entity_type": incoming},
                    "library": "character" if str(incoming).startswith("人物") else "setting",
                    "t_valid": AT,
                    "note": f"G09 信息保全：合并舍弃富值保全（identity={identity}；"
                            f"kept={kept}）",
                })
                comp_existing.add(eid)
            row["disposition"] = "preserved_complementary"
            row["event_id"] = eid
        rows.append(row)

    if rows:
        with LEDGER_OUT.open("a", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    if events:
        with COMP.open("a", encoding="utf-8") as f:
            for e in events:
                f.write(json.dumps(e, ensure_ascii=False, sort_keys=True) + "\n")

    from collections import Counter
    total = len([l for l in LEDGER_OUT.read_text(encoding="utf-8").splitlines() if l.strip()]) \
        if LEDGER_OUT.exists() else 0
    print(f"本轮新增处置 {len(rows)} 件（事件 {len(events)} 笔）；台账累计 {total}/186")
    print("分布:", dict(Counter(r["disposition"] for r in rows)) if rows else "（幂等重跑零新增）")


if __name__ == "__main__":
    main()
