# -*- coding: utf-8 -*-
"""ledger_chain.py — U-C03.6 吸收件（工单 v1.5 §0 吸收条款 · 2026-09-18）

两件：
1) store 账本哈希链：jsonl 追加前记 sha_before / 追加后记 sha_after + 碰撞跳过计数
   （幂等键已入账即跳过追加）。语义参考 skill反向输出包-20260917/源码/append2.py
   （sha_before→碰撞跳过→追加→sha_after→复核），按 cbb 契约改写——参考实现内嵌
   他方工作区绝对路径与 CSV 载体，此处为 ThreeStateStore(_append 汇聚点) 包装，
   账本载体=store_root/ledger.jsonl，链式哈希防篡改。
2) 仪器指纹四元组（ranker/criterion/sort/params）：随每次抽检/校准报告入 STATE 的
   仪器身份标识（R-025 同精神：换配置=换仪器）。

用法：
  py -X utf8 ledger_chain.py genesis --store <本项目>-本体库   # 存量库基线登记（幂等）
  py -X utf8 ledger_chain.py verify  --store <本项目>-本体库   # 全链校验+当前文件 sha 复核
  py -X utf8 ledger_chain.py fingerprint --ranker R --criterion C --sort S --params-json '{}'
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

EMPTY_SHA = "0" * 64  # 目标文件尚不存在时的 sha_before 约定值

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "cbb-store"))
import cbb_store  # noqa: E402  ThreeStateStore（本体只读复用）


def _sha256_file(p: Path) -> str:
    if not p.exists():
        return EMPTY_SHA
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _line_hash(payload: dict) -> str:
    core = {k: v for k, v in payload.items() if k != "hash"}
    return hashlib.sha256(json.dumps(core, ensure_ascii=False, sort_keys=True)
                          .encode("utf-8")).hexdigest()


class LedgerChain:
    """append-only 哈希链账本：每行含 prev_hash + 自身 hash，verify() 重放防篡改。"""

    def __init__(self, ledger_path: Path):
        self.path = Path(ledger_path)
        if not self.path.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.touch()

    def _rows(self) -> list[dict]:
        # C1 修复（审计 R4）：实例内缓存——原实现每次追加/查键全量重读解析（O(n²)）；
        # 单写者假设（跨进程并发写见审计 B1 挂账），本实例追加后缓存内同步续行
        if getattr(self, "_cache", None) is None:
            self._cache = [json.loads(ln) for ln in
                           self.path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        return self._cache

    def _rows_fresh(self) -> list[dict]:
        """作废实例缓存后重载——篡改检测/校验等只读场景专用（缓存不得掩盖账本外改动）。"""
        self._cache = None
        return self._rows()

    def _tail(self) -> dict | None:
        rows = self._rows()
        return rows[-1] if rows else None

    def has_key(self, target: str, idempotency_key: str) -> bool:
        """碰撞检查：该 (target, key) 是否已入账（append 行才算占键；skip 不占）。"""
        return any(r["op"] == "append" and r["target"] == target
                   and r["idempotency_key"] == idempotency_key for r in self._rows())

    def _append_row(self, op: str, target: str, idempotency_key: str,
                    sha_before: str, sha_after: str, n_appended: int,
                    collision_total: int) -> dict:
        prev = self._tail()
        payload = {"seq": (prev["seq"] + 1) if prev else 1,
                   "op": op, "target": target, "idempotency_key": idempotency_key,
                   "sha_before": sha_before, "sha_after": sha_after,
                   "n_appended": n_appended, "collision_total": collision_total,
                   "prev_hash": prev["hash"] if prev else EMPTY_SHA}
        payload["hash"] = _line_hash(payload)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
        if getattr(self, "_cache", None) is not None:
            self._cache.append(payload)
        return payload

    def record_append(self, target: str, idempotency_key: str,
                      sha_before: str, sha_after: str) -> dict:
        return self._append_row("append", target, idempotency_key,
                                sha_before, sha_after, n_appended=1, collision_total=0)

    def record_skip(self, target: str, idempotency_key: str,
                    sha_before: str, collision_total: int) -> dict:
        """碰撞跳过：不追加目标文件，仅入账计数（幂等键已入账即跳过）。"""
        return self._append_row("skip", target, idempotency_key,
                                sha_before, sha_before, n_appended=0,
                                collision_total=collision_total)

    def record_genesis(self, target: str, sha: str) -> dict | None:
        """存量基线登记：每 (target) 一次性入账；重复跑幂等返回 None。"""
        if any(r["op"] == "genesis" and r["target"] == target for r in self._rows()):
            return None
        return self._append_row("genesis", target, f"__genesis__:{target}",
                                EMPTY_SHA, sha, n_appended=0, collision_total=0)

    def record_rebaseline(self, target: str, sha: str) -> dict | None:
        """基线重登记（接线修复后一次性对齐真实 sha；同 sha 幂等）。"""
        if any(r["op"] in ("rebaseline", "genesis", "append")
               and r["target"] == target and r["sha_after"] == sha for r in self._rows()):
            return None
        return self._append_row("rebaseline", target, f"__rebaseline__:{target}:{sha[:12]}",
                                EMPTY_SHA, sha, n_appended=0, collision_total=0)

    def collision_count(self, target: str | None = None) -> int:
        return sum(r.get("collision_total", 0) for r in self._rows()
                   if r["op"] == "skip" and (target is None or r["target"] == target))

    def verify(self, store_root: Path | None = None) -> dict:
        rows = self._rows_fresh()  # C1 补强：校验面读盘，不信任实例缓存
        errors = []
        prev_hash = EMPTY_SHA
        for i, r in enumerate(rows):
            if r["prev_hash"] != prev_hash:
                errors.append(f"seq{r['seq']}: prev_hash 断链")
            if r["hash"] != _line_hash(r):
                errors.append(f"seq{r['seq']}: 行哈希不匹配（被篡改？）")
            if r["seq"] != i + 1:
                errors.append(f"seq{r['seq']}: 序号不连续")
            prev_hash = r["hash"]
        # 复核：每个 target 当前磁盘 sha 应与账本中该 target 最后一条 append/genesis 的 sha_after 一致
        if store_root is not None:
            store_root = Path(store_root)
            last = {}
            for r in rows:
                if r["op"] in ("append", "genesis", "rebaseline"):
                    last[r["target"]] = r["sha_after"]
            for target, sha in sorted(last.items()):
                actual = _sha256_file(store_root / target)
                if actual != sha:
                    errors.append(f"{target}: 当前 sha 与账本不符（账本外改动）")
        return {"ok": not errors, "rows": len(rows), "errors": errors,
                "collision_total": self.collision_count()}


def idempotency_key_of(obj: dict) -> str:
    """幂等键抽取：优先用记录自带键（aliases/appearances/quarantine 的 key/item_id/
    record_id），无键对象退内容哈希——与 append2 的 claim_id=sha256(内容) 同精神。"""
    for k in ("key", "item_id", "record_id"):
        if obj.get(k):
            return str(obj[k])
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True)
                          .encode("utf-8")).hexdigest()[:16]


class LedgedStore(cbb_store.ThreeStateStore):
    """ThreeStateStore 包装：_append 汇聚点自动入账（sha_before/after+碰撞跳过）。

    行为等价性：原 _append 调用方多已自带键级去重（如 register_alias 先查 key），
    链上碰撞跳过=纵深防御第二层，不改变正常路径结果。
    """

    def __init__(self, root: Path, ledger_path: Path | None = None):
        super().__init__(root)
        self.ledger = LedgerChain(ledger_path or Path(root) / "ledger.jsonl")
        self._skip_counts: dict[str, int] = {}
        self._wrap_zone()

    def _append(self, name: str, obj: dict) -> None:
        target = Path(self.root) / name
        key = idempotency_key_of(obj)
        if self.ledger.has_key(name, key):
            self._skip_counts[name] = self._skip_counts.get(name, 0) + 1
            self.ledger.record_skip(name, key, _sha256_file(target),
                                    collision_total=self._skip_counts[name])
            return
        sha_before = _sha256_file(target)
        super()._append(name, obj)
        self.ledger.record_append(name, key, sha_before, _sha256_file(target))

    def _wrap_zone(self) -> None:
        """隔离区写入入账：QuarantineZone._append 直写 items/adjudications，
        不经 store._append 汇聚点——实例级包装补此缺口（zone.register 自带
        item_id 查重，链上碰撞跳过=第二层）。"""
        zone = self.zone
        orig = zone._append
        root = Path(self.root)
        ledger = self.ledger

        def zappend(path, obj, _orig=orig, _ledger=ledger):
            rel = str(Path(path).relative_to(root)).replace("\\", "/")
            key = idempotency_key_of(obj)
            if _ledger.has_key(rel, key):
                return  # 幂等：register/adjudicate 已在册
            sha_before = _sha256_file(path)
            _orig(path, obj)
            _ledger.record_append(rel, key, sha_before, _sha256_file(path))
        zone._append = zappend


def instrument_fingerprint(ranker: str, criterion: str, sort: str,
                           params: dict | str | None) -> dict:
    """仪器指纹四元组：抽检/校准报告的身份标识；同参同指纹、异参异指纹。"""
    if isinstance(params, str):
        params = json.loads(params) if params.strip() else {}
    quad = {"ranker": ranker, "criterion": criterion, "sort": sort,
            "params": params or {}}
    quad["fingerprint"] = hashlib.sha256(
        json.dumps(quad, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]
    return quad


JSONL_TARGETS = ["aliases.jsonl", "appearances.jsonl", "supersede-index.jsonl",
                 "evidence-graph-edges.jsonl", "transitions.jsonl", "state_changes.jsonl",
                 "quarantine-zone/items.jsonl", "quarantine-zone/adjudications.jsonl"]


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="U-C03.6 账本哈希链+仪器指纹")
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("genesis"); g.add_argument("--store", required=True)
    v = sub.add_parser("verify"); v.add_argument("--store", required=True)
    f = sub.add_parser("fingerprint")
    f.add_argument("--ranker", required=True); f.add_argument("--criterion", required=True)
    f.add_argument("--sort", required=True); f.add_argument("--params-json", default="{}")
    a = ns = ap.parse_args(argv)

    if ns.cmd == "genesis":
        store = Path(ns.store)
        led = LedgerChain(store / "ledger.jsonl")
        made = 0
        for t in JSONL_TARGETS:
            p = store / t
            if p.exists() and led.record_genesis(t, _sha256_file(p)):
                made += 1
        print(json.dumps({"cmd": "genesis", "registered": made,
                          "rows": len(led._rows())}, ensure_ascii=False))
        return 0
    if ns.cmd == "verify":
        store = Path(ns.store)
        led = LedgerChain(store / "ledger.jsonl")
        print(json.dumps(led.verify(store), ensure_ascii=False))
        return 0
    if ns.cmd == "fingerprint":
        print(json.dumps(instrument_fingerprint(ns.ranker, ns.criterion, ns.sort,
                                                ns.params_json), ensure_ascii=False))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
