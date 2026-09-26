# -*- coding: utf-8 -*-
"""cbb2.ledger — 哈希链账本（R12；移植 v1 ledger_chain 核心，verify 读盘不信任缓存）。"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

EMPTY_SHA = "0" * 64


def line_hash(payload: dict) -> str:
    core = {k: v for k, v in payload.items() if k != "hash"}
    return hashlib.sha256(json.dumps(core, ensure_ascii=False, sort_keys=True)
                          .encode("utf-8")).hexdigest()


def idempotency_key_of(obj: dict) -> str:
    for k in ("key", "item_id", "record_id"):
        if obj.get(k):
            return str(obj[k])
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True)
                          .encode("utf-8")).hexdigest()[:16]


class LedgerChain:
    def __init__(self, path: Path):
        self.path = Path(path)
        if not self.path.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.touch()
        self._cache: list[dict] | None = None

    def _rows(self) -> list[dict]:
        if self._cache is None:
            self._cache = [json.loads(x) for x in
                           self.path.read_text(encoding="utf-8").splitlines() if x.strip()]
        return self._cache

    def _rows_fresh(self) -> list[dict]:
        self._cache = None  # 篡改检测面读盘——缓存不得掩盖账本外改动
        return self._rows()

    def has_key(self, target: str, key: str) -> bool:
        return any(r["op"] == "append" and r["target"] == target
                   and r["idempotency_key"] == key for r in self._rows())

    def _append_row(self, op: str, target: str, key: str,
                    sha_before: str, sha_after: str) -> dict:
        prev = self._rows()[-1] if self._rows() else None
        payload = {"seq": (prev["seq"] + 1) if prev else 1, "op": op, "target": target,
                   "idempotency_key": key, "sha_before": sha_before, "sha_after": sha_after,
                   "prev_hash": prev["hash"] if prev else EMPTY_SHA}
        payload["hash"] = line_hash(payload)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
        if self._cache is not None:
            self._cache.append(payload)
        return payload

    def record_append(self, target: str, key: str, sha_before: str, sha_after: str):
        return self._append_row("append", target, key, sha_before, sha_after)

    def verify(self, store_root: Path | None = None) -> dict:
        rows = self._rows_fresh()
        errors, prev_hash = [], EMPTY_SHA
        for i, r in enumerate(rows):
            if r["prev_hash"] != prev_hash:
                errors.append(f"seq{r['seq']}: prev_hash 断链")
            if r["hash"] != line_hash(r):
                errors.append(f"seq{r['seq']}: 行哈希不匹配（被篡改？）")
            if r["seq"] != i + 1:
                errors.append(f"seq{r['seq']}: 序号不连续")
            prev_hash = r["hash"]
        if store_root is not None:
            import hashlib as _h
            last = {}
            for r in rows:
                if r["op"] in ("append", "genesis", "rebaseline"):
                    last[r["target"]] = r["sha_after"]
            for target, sha in sorted(last.items()):
                actual = _h.sha256((Path(store_root) / target).read_bytes()).hexdigest() \
                    if (Path(store_root) / target).exists() else EMPTY_SHA
                if actual != sha:
                    errors.append(f"{target}: 当前 sha 与账本不符（账本外改动）")
        return {"ok": not errors, "rows": len(rows), "errors": errors}


class LedgedStore:
    """Store + 账本：侧车 _append 汇聚点自动入账（库文件写入不入账——与 v1 A3 口径一致）。"""

    def __init__(self, root: Path):
        from .store import Store
        self.store = Store(root)
        self.ledger = LedgerChain(Path(root) / "ledger.jsonl")
        self._skips: dict[str, int] = {}
        self._wrap_zone()

    def _sha(self, p: Path) -> str:
        import hashlib
        return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else EMPTY_SHA

    def _append(self, name: str, obj: dict):
        target = Path(self.store.root) / name
        key = idempotency_key_of(obj)
        if self.ledger.has_key(name, key):
            self._skips[name] = self._skips.get(name, 0) + 1
            return
        sha_before = self._sha(target)
        self.store._append(name, obj)
        self.ledger.record_append(name, key, sha_before, self._sha(target))

    def _wrap_zone(self):
        zone = self.store.zone
        orig = zone._append
        root = Path(self.store.root)
        led = self.ledger

        def zappend(item, _orig=orig, _led=led):
            rel = "quarantine-zone/items.jsonl"
            key = item.get("item_id") or idempotency_key_of(item)
            if _led.has_key(rel, key):
                return
            sha_before = self._sha(zone.items_path)
            _orig(item)
            _led.record_append(rel, key, sha_before, self._sha(zone.items_path))
        zone._append = zappend

    def __getattr__(self, name):
        return getattr(self.store, name)
