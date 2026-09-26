# -*- coding: utf-8 -*-
"""cbb2.store — 三态存储 + 双轨合并（R1-R5/R13；算法忠实移植 v1，数据布局逐字节兼容）。

v1 兼容面：libraries/<lib>/<status>/<rid>.json 布局、supersede-index.jsonl、
transitions.jsonl、quarantine-zone/、-m{N} 版本链（Windows MAX_PATH 修复语义）、
CORROBORATION_BUMP=2.0、P-017 幂等守卫（证据子集→repeated）。
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from .quarantine import QuarantineZone

CORROBORATION_BUMP = 2.0
TRANSITION_BYS = ("human", "shadow", "promotion")
ADMIT_DECISIONS = ("confirmed", "provisional", "quarantine")


def identity_key(record: dict) -> tuple:
    rt = record.get("record_type")
    c = record.get("canonical") or {}
    if rt == "entity" and c.get("name"):
        return ("entity", record.get("library"), c["name"])
    if rt == "relation" and all(c.get(k) for k in ("subject", "rel_type", "object")):
        return ("relation", c["subject"], c["rel_type"], c["object"])
    return ("id", record.get("record_id"))


def canonical_conflicts(a: dict, b: dict) -> list[dict]:
    ca, cb = a.get("canonical") or {}, b.get("canonical") or {}
    return [{"field": k, "incoming": ca[k], "stored": cb[k]}
            for k in sorted(set(ca) & set(cb)) if ca[k] != cb[k]]


def _chain_base(record_id: str) -> str:
    rid = record_id
    while True:
        if rid.endswith("-m"):
            rid = rid[:-2]
            continue
        i = rid.rfind("-m")
        if i != -1 and rid[i + 2:].isdigit():
            rid = rid[:i]
            continue
        return rid


class Store:
    """三态库：confirmed / provisional 在 libraries，quarantine 在隔离区（B1：库里只有两态）。"""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.zone = QuarantineZone(self.root / "quarantine-zone")
        self.iter_skipped: list[str] = []

    # ---- 底层 IO ----

    def _lib_path(self, library: str, status: str, rid: str) -> Path:
        return self.root / "libraries" / library / status / f"{rid}.json"

    def _write_immutable(self, path: Path, obj: dict):
        if path.exists():
            return path, False
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=1),
                       encoding="utf-8")
        try:
            os.replace(tmp, path)  # R4：原子写
        except OSError:
            tmp.unlink(missing_ok=True)
            raise
        return path, True

    def _append(self, name: str, obj: dict):
        p = self.root / name
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False, sort_keys=True) + "\n")

    def _load_all(self, name: str) -> list[dict]:
        p = self.root / name
        if not p.exists():
            return []
        return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]

    # ---- 遍历（R5：撕裂披露不崩） ----

    def iter_records(self):
        for p in sorted(self.root.glob("libraries/*/*/*.json")):
            try:
                yield json.loads(p.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError, UnicodeDecodeError):
                self.iter_skipped.append(p.name)

    def _find(self, rid: str):
        for p in sorted(self.root.glob(f"libraries/*/*/{rid}.json")):
            return json.loads(p.read_text(encoding="utf-8"))
        return None

    def find_by_identity(self, record: dict) -> dict | None:
        key = identity_key(record)
        matches = [r for r in self.iter_records() if identity_key(r) == key]
        if not matches:
            return None
        superseded = {e["old_id"] for e in self._load_all("supersede-index.jsonl")}
        live = [m for m in matches if m["record_id"] not in superseded]
        return max(live or matches, key=lambda m: m.get("version", 1))

    # ---- 三态写入（R1） ----

    def admit(self, record: dict, decision: str):
        if decision not in ADMIT_DECISIONS:
            raise ValueError(f"非法入库决定 {decision!r}")
        rid = record.get("record_id")
        if not rid:
            raise ValueError("record 缺 record_id")
        if decision == "quarantine":
            raise ValueError("quarantine 走 register_quarantine（显式分组语义）")
        rec = dict(record)
        rec["status"] = decision
        rec.setdefault("provenance", {}).setdefault("status_history", []).append(
            {"to": decision, "by": "cbb2-admit"})
        return self._write_immutable(self._lib_path(rec["library"], decision, rid), rec)

    def register_quarantine(self, record: dict, group: str, detail: str):
        return self.zone.register(group=group, detail=detail,
                                  record_id=record.get("record_id"), source="cbb2-store")

    # ---- 双轨合并（R2/R3 + P-017 幂等 + -m{N} 版本链） ----

    def supersede(self, old_id: str, new_record: dict):
        old = self._find(old_id)
        if old is None:
            raise KeyError(old_id)
        if new_record["record_id"] == old_id:
            raise ValueError("supersede 不得同 id")
        new_record["version"] = old.get("version", 1) + 1
        new_record["supersedes"] = old_id
        path, created = self._write_immutable(
            self._lib_path(new_record["library"], new_record.get("status", old["status"]),
                           new_record["record_id"]), new_record)
        self._append("supersede-index.jsonl",
                     {"old_id": old_id, "new_id": new_record["record_id"],
                      "version": new_record["version"]})
        return path, created

    def resolve_latest(self, rid: str):
        chain = {e["old_id"]: e["new_id"] for e in self._load_all("supersede-index.jsonl")}
        cur, seen = rid, set()
        while cur in chain and cur not in seen:
            seen.add(cur)
            cur = chain[cur]
        return self._find(cur)

    def admit_or_merge(self, incoming: dict) -> dict:
        existing = self.find_by_identity(incoming)
        if existing is None:
            path, created = self.admit(incoming, "provisional")
            return {"track": "on-create", "path": str(path), "created": created}

        conflicts = canonical_conflicts(incoming, existing)
        if not conflicts:
            def _ev_set(rec):
                return {(e.get("vol"), e.get("chapter"), e.get("line"), e.get("quote"))
                        for e in (rec.get("evidence") or [])}
            if _ev_set(incoming) <= _ev_set(existing):  # P-017 幂等守卫
                return {"track": "consistent-duplicate", "new_id": existing["record_id"],
                        "confidence": (existing.get("provenance") or {}).get(
                            "extractor_confidence"), "created": False, "repeated": True}
            merged = dict(existing)
            old_conf = (existing.get("provenance") or {}).get("extractor_confidence", 0) or 0
            new_conf = (incoming.get("provenance") or {}).get("extractor_confidence", 0) or 0
            merged.setdefault("provenance", {})["extractor_confidence"] = min(
                100.0, max(old_conf, new_conf) + CORROBORATION_BUMP)
            seen_q, ev = set(), list(existing.get("evidence") or [])
            for e in incoming.get("evidence") or []:
                k = (e.get("vol"), e.get("chapter"), e.get("line"), e.get("quote"))
                if k not in seen_q:
                    seen_q.add(k)
                    ev.append(e)
            merged["evidence"] = ev
            new_ver = existing.get("version", 1) + 1
            merged["record_id"] = f"{_chain_base(existing['record_id'])}-m{new_ver}"
            path, created = self.supersede(existing["record_id"], merged)
            return {"track": "consistent-duplicate", "new_id": merged["record_id"],
                    "confidence": merged["provenance"]["extractor_confidence"],
                    "path": str(path), "created": created}

        detail = "；".join(f"{c['field']}: 入库={c['incoming']!r} vs 库内={c['stored']!r}"
                          for c in conflicts)
        iid, created = self.zone.register(
            group="entity_unalignable", detail=detail,
            record_id=incoming.get("record_id"), source="cbb2-store-dual-track",
            subclass="contradiction_pending")
        return {"track": "contradiction", "quarantine_item": iid, "created": created}

    # ---- 状态迁移（R13：旁车日志，文件不动） ----

    def status_transition(self, rid: str, to_status: str, by: str = "human", note: str = ""):
        if by not in TRANSITION_BYS:
            raise ValueError(f"非法 by {by!r}")
        if to_status not in ("confirmed", "provisional"):
            raise ValueError("迁移仅限库内两态")
        if self._find(rid) is None:
            raise KeyError(f"记录不在库: {rid}")
        eff = self.effective_status(rid)
        if eff == to_status:
            return {"record_id": rid, "from": to_status, "to": to_status,
                    "by": by, "note": note, "repeated": True}
        entry = {"record_id": rid, "from": eff, "to": to_status, "by": by, "note": note}
        self._append("transitions.jsonl", entry)
        return entry

    def effective_status(self, rid: str) -> str | None:
        rec = self._find(rid)
        if rec is None:
            return None
        status = rec["status"]
        for t in self._load_all("transitions.jsonl"):
            if t["record_id"] == rid:
                status = t["to"]
        return status
