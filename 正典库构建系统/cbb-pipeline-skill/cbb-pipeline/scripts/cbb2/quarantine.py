# -*- coding: utf-8 -*-
"""cbb2.quarantine — 隔离区（R14；数据格式与 v1 逐字节兼容——同 items.jsonl 可互操作）。"""
from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

GROUPS = ("unresolved_time", "missing_anchor", "ambiguous_reference",
          "entity_unalignable", "low_confidence", "out_of_scope")
SUBCLASSES = ("contradiction_pending", "extrapolation_unverified", "overdue_omission")
GROUP_TO_SUBCLASS = {
    "unresolved_time": "overdue_omission",
    "entity_unalignable": "contradiction_pending",
    "low_confidence": "extrapolation_unverified",
}


def _today() -> str:
    return date.today().isoformat()


def item_id(group: str, record_id: str, detail: str) -> str:
    h = hashlib.sha256(f"{group}|{record_id}|{detail}".encode("utf-8")).hexdigest()[:12]
    return f"q-{h}"


class QuarantineZone:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.items_path = self.root / "items.jsonl"

    def _load(self) -> list[dict]:
        if not self.items_path.exists():
            return []
        return [json.loads(x) for x in
                self.items_path.read_text(encoding="utf-8").splitlines() if x.strip()]

    def _append(self, item: dict):
        with self.items_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")

    def register(self, group: str, detail: str, record_id: str = None,
                 source: str = None, blocks: list | None = None,
                 subclass: str = None, at: str = None):
        if group not in GROUPS:
            raise ValueError(f"非法隔离分组 {group!r}，合法={GROUPS}")
        sub = subclass or GROUP_TO_SUBCLASS.get(group, "extrapolation_unverified")
        if sub not in SUBCLASSES:
            raise ValueError(f"非法子类 {sub!r}，合法={SUBCLASSES}")
        iid = item_id(group, record_id or "", detail)
        if any(it["item_id"] == iid for it in self._load()):
            return iid, False
        self._append({"item_id": iid, "group": group, "subclass": sub,
                      "source": source, "record_id": record_id, "detail": detail,
                      "blocks_downstream": sorted(set(blocks or [])),
                      "status": "pending", "at": at or _today()})
        return iid, True

    def adjudicate(self, iid: str, verdict: str, note: str = "", by: str = "human"):
        if verdict not in ("confirmed", "rejected"):
            raise ValueError("verdict 合法=confirmed|rejected")
        items = self._load()
        hit = next((i for i in items if i["item_id"] == iid), None)
        if hit is None:
            raise KeyError(iid)
        hit["status"] = verdict
        self.items_path.write_text(
            "\n".join(json.dumps(i, ensure_ascii=False, sort_keys=True) for i in items) + "\n",
            encoding="utf-8")
        with (self.root / "adjudications.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps({"item_id": iid, "verdict": verdict, "note": note,
                                "by": by, "at": _today()}, ensure_ascii=False) + "\n")

    def pending(self) -> list[dict]:
        adj = {json.loads(x)["item_id"] for x in
               (self.root / "adjudications.jsonl").read_text(encoding="utf-8").splitlines()
               if x.strip()} if (self.root / "adjudications.jsonl").exists() else set()
        return [i for i in self._load() if i["item_id"] not in adj]
