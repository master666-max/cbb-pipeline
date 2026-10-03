"""cbb2.quarantine — 隔离区（R14；数据格式与 v1 逐字节兼容——同 items.jsonl 可互操作）。"""
from __future__ import annotations

import contextlib
import hashlib
import json
from datetime import date
from pathlib import Path

from . import jsonl_io  # P-028：共享 JSONL 读面（撕裂安全+坏行披露）

GROUPS = ("unresolved_time", "missing_anchor", "ambiguous_reference",
          "entity_unalignable", "low_confidence", "out_of_scope")
SUBCLASSES = ("contradiction_pending", "extrapolation_unverified", "overdue_omission")
# 2026-10-03 审计口径收敛：unresolved_time 对齐 v1 GROUP_TO_SUBCLASS 映射
# （extrapolation_unverified=时间锚挂不上属外推待证；旧 overdue_omission 是映射漂移——
#  overdue_omission 语义=契诃夫枪超期遗漏，与时间不可解析无关）。
GROUP_TO_SUBCLASS = {
    "unresolved_time": "extrapolation_unverified",
    "entity_unalignable": "contradiction_pending",
    "low_confidence": "extrapolation_unverified",
}


@contextlib.contextmanager
def adjudicate_lock(root: Path):
    """G25：adjudicate 读-改-写全程文件锁（单写者语义）。
    Windows=msvcrt.locking 阻塞锁；POSIX=fcntl.flock；两者皆缺→无锁直行
    （显式降级语义，调用面经 exceptions 面知晓——当前无双缺平台在役）。
    锁文件=同目录 adjudicate.lock，随库落盘（幂等 touch）。"""
    lock_path = Path(root) / "adjudicate.lock"
    lock_path.touch(exist_ok=True)
    f = open(lock_path, "r+", encoding="utf-8")  # noqa: SIM115 — 锁生命周期=with 体
    locked = False
    try:
        try:
            import msvcrt
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)  # 阻塞至获取
            locked = "msvcrt"
        except ImportError:
            try:
                import fcntl
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                locked = "fcntl"
            except ImportError:
                locked = None  # 双缺：无锁直行（显式降级）
        yield locked
    finally:
        if locked == "msvcrt":
            try:
                f.seek(0)
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            except OSError:
                pass
        f.close()


def _today() -> str:
    return date.today().isoformat()  # noqa: DTZ011 — v1 兼容锚：墙钟仅作回退默认，主路径显式 at 透传


def item_id(group: str, record_id: str, detail: str) -> str:
    h = hashlib.sha256(f"{group}|{record_id}|{detail}".encode()).hexdigest()[:12]
    return f"q-{h}"


class QuarantineZone:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.items_path = self.root / "items.jsonl"
        self.skipped: list[dict] = []  # 坏行披露（iter_skipped 式，P-028：不静默丢弃）

    def _load(self) -> list[dict]:
        if not self.items_path.exists():
            return []
        rows, skipped = jsonl_io.parse_jsonl(
            self.items_path.read_text(encoding="utf-8"), source="quarantine/items.jsonl")
        self.skipped.extend(skipped)
        return rows

    def _append(self, item: dict):
        with self.items_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")

    def register(self, group: str, detail: str, record_id: str | None = None,
                 source: str | None = None, blocks: list | None = None,
                 subclass: str | None = None, at: str | None = None):
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
        """公开裁决入口：读-改-写全程单写者锁（G25）。账本面请走 LedgedStore（其 zadjudicate
        自持同一把锁直呼 _adjudicate_inner——幂等检查与账本追加同锁，双写根除且不嵌套死锁）。"""
        with adjudicate_lock(self.root):
            self._adjudicate_inner(iid, verdict, note, by)

    def _adjudicate_inner(self, iid: str, verdict: str, note: str, by: str):
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
        adj_path = self.root / "adjudications.jsonl"
        adj: set = set()
        if adj_path.exists():
            rows, skipped = jsonl_io.parse_jsonl(
                adj_path.read_text(encoding="utf-8"), source="quarantine/adjudications.jsonl")
            self.skipped.extend(skipped)
            adj = {r.get("item_id") for r in rows}
        return [i for i in self._load() if i["item_id"] not in adj]
