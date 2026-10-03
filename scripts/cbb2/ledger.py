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
            rows: list[dict] = []
            raw = self.path.read_bytes() if self.path.exists() else b""
            # 只按 \n 切行——JSON 字符串可合法含 U+0085/U+2028 等 Unicode 行分隔符，
            # str.splitlines() 会把它们当行界撕碎 JSON（P-028）；坏行以标记占位不崩，
            # 由 verify() 判"行损坏"（审计工具对任意输入必须给判定，不许抛异常）。
            for line in raw.split(b"\n"):
                if not line.strip():
                    continue
                try:
                    rows.append(json.loads(line.decode("utf-8")))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    rows.append({"corrupt": line.decode("utf-8", "replace")[:32]})
            self._cache = rows
        return self._cache

    def _rows_fresh(self) -> list[dict]:
        self._cache = None  # 篡改检测面读盘——缓存不得掩盖账本外改动
        return self._rows()

    def has_key(self, target: str, key: str) -> bool:
        return any(r.get("op") == "append" and r.get("target") == target
                   and r.get("idempotency_key") == key for r in self._rows())

    def _append_row(self, op: str, target: str, key: str,
                    sha_before: str, sha_after: str) -> dict:
        rows = self._rows()
        prev = rows[-1] if rows else None
        if prev is not None and ("seq" not in prev or "hash" not in prev):
            # P-1：尾行损坏（corrupt 占位/残缺行）→ 重锚恢复，不再 prev["seq"] KeyError 裸崩
            # （曾使所有侧车写入永久崩溃）。重锚行本身入账留痕，verify() 识别接链。
            prev = self._reanchor("尾行损坏，重锚接链")
        payload = {"seq": (prev["seq"] + 1) if prev else 1, "op": op, "target": target,
                   "idempotency_key": key, "sha_before": sha_before, "sha_after": sha_after,
                   "prev_hash": prev["hash"] if prev else EMPTY_SHA}
        payload["hash"] = line_hash(payload)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
        if self._cache is not None:
            self._cache.append(payload)
        return payload

    def _reanchor(self, reason: str) -> dict:
        """P-1 恢复路径：尾行损坏时重锚接链（追加 reanchor 行留痕，不静默）。
        prev_hash 回锚 EMPTY_SHA；verify() 识别 reanchor 允许在损坏断点后重新接链——
        此后记账/侧车写入照常，损坏历史仍由 verify 显式披露。"""
        rows = self._rows()
        anchor = {"seq": len(rows) + 1, "op": "reanchor", "target": "",
                  "idempotency_key": "reanchor", "sha_before": EMPTY_SHA,
                  "sha_after": EMPTY_SHA, "prev_hash": EMPTY_SHA, "note": reason[:80]}
        anchor["hash"] = line_hash(anchor)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(anchor, ensure_ascii=False, sort_keys=True) + "\n")
        if self._cache is not None:
            self._cache.append(anchor)
        return anchor

    def record_append(self, target: str, key: str, sha_before: str, sha_after: str):
        return self._append_row("append", target, key, sha_before, sha_after)

    def verify(self, store_root: Path | None = None) -> dict:
        rows = self._rows_fresh()
        errors, prev_hash = [], EMPTY_SHA
        for i, r in enumerate(rows):
            if r.get("corrupt") is not None and "corrupt" in r:
                errors.append(f"line{i+1}: 行损坏无法解析（{r['corrupt']!r}…）")
                prev_hash = None  # 后续行 prev_hash 必不一致——让断链误差显式暴露
                continue
            if r.get("op") == "reanchor" and prev_hash is None:
                prev_hash = EMPTY_SHA  # P-1：重锚行在损坏断点后从 EMPTY_SHA 重新接链（恢复留痕）
            if r.get("prev_hash") != prev_hash:
                errors.append(f"seq{r.get('seq')}: prev_hash 断链")
            if r.get("hash") != line_hash(r):
                errors.append(f"seq{r.get('seq')}: 行哈希不匹配（被篡改？）")
            if r.get("seq") != i + 1:
                errors.append(f"seq{r.get('seq')}: 序号不连续")
            prev_hash = r.get("hash")
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
        self._wrap_appends()
        self._wrap_zone()

    def _sha(self, p: Path) -> str:
        import hashlib
        return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else EMPTY_SHA

    def _wrap_appends(self):
        """通用侧车入账：store._append 全部 name 走账本（幂等键跳过+sha_before/after）。
        U-A02 起 write_decision 的 complementary-statements/invalidations/拦截件全文
        经此自动入账——无需逐名注册。"""
        store = self.store
        led = self.ledger
        orig = store._append
        root = Path(store.root)

        def lappend(name, obj, _orig=orig):
            key = idempotency_key_of(obj)
            if led.has_key(name, key):
                self._skips[name] = self._skips.get(name, 0) + 1
                return
            sha_before = self._sha(root / name)
            _orig(name, obj)
            led.record_append(name, key, sha_before, self._sha(root / name))

        store._append = lappend

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

        orig_adj = zone.adjudicate

        def zadjudicate(iid, verdict, note="", by="human", _orig=orig_adj, _led=led):
            from .quarantine import adjudicate_lock
            key = f"{iid}|{verdict}"
            # G25：幂等检查+裁决内核+账本双记全程同锁——并发双写与丢更新同根除；
            # 内核直呼 _adjudicate_inner（其外层公开法自带同锁，嵌套会死锁）
            with adjudicate_lock(zone.root):
                # 检查键=记账键（key|adj）——原检查用裸 key 与记账键错位，重复裁决从未被拦（本批修复）
                if _led.has_key("quarantine-zone/adjudications.jsonl", key + "|adj"):
                    return {"item_id": iid, "repeated": True}
                sha_b_items = self._sha(zone.items_path)
                adj_path = zone.root / "adjudications.jsonl"
                sha_b_adj = self._sha(adj_path)
                out = zone._adjudicate_inner(iid, verdict, note, by)
                _led.record_append("quarantine-zone/items.jsonl", key,
                                   sha_b_items, self._sha(zone.items_path))
                _led.record_append("quarantine-zone/adjudications.jsonl", key + "|adj",
                                   sha_b_adj, self._sha(adj_path))
                return out
        zone.adjudicate = zadjudicate

    def __getattr__(self, name):
        return getattr(self.store, name)
