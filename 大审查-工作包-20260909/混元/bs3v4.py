"""v4 事件溯源内核原型 —— 仅为验证架构可行性，非生产代码。
验证目标：
  V1 事件流为唯一真相源，state/memory 均为 fold 产物
  V2 并发 append 不再 lost update（append+fold 取代 read-modify-write）
  V3 chain_tip 能检出截断攻击
  V4 增量 fold（只读新增事件）
"""
from __future__ import annotations
import json, hashlib, os, time, fcntl, tempfile
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable

# ── 事件 ────────────────────────────────────────────────────────────
def canon(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def sha(b) -> str:
    return hashlib.sha256(b if isinstance(b, bytes) else b.encode()).hexdigest()

@dataclass(frozen=True)
class Event:
    seq: int
    ts: str
    type: str
    payload: dict
    prev: str = ""
    @property
    def body(self) -> str:
        return canon({"seq": self.seq, "ts": self.ts, "type": self.type, "payload": self.payload})
    @property
    def h(self) -> str:
        return sha(self.prev + "\x00" + self.body)
    def line(self) -> str:
        return canon({"seq": self.seq, "ts": self.ts, "type": self.type,
                      "payload": self.payload, "prev": self.prev, "h": self.h})
    @staticmethod
    def parse(line: str) -> "Event":
        d = json.loads(line)
        return Event(seq=d["seq"], ts=d["ts"], type=d["type"], payload=d["payload"], prev=d["prev"])

# ── 事件存储（append-only + 锁 + 跨月分片）────────────────────────
class EventStore:
    def __init__(self, root: Path):
        self.root = Path(root); self.dir = self.root / "audit"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.lock = self.root / ".lock"
    def _shard(self, ts: str) -> Path:
        return self.dir / f"events-{ts[:7]}.jsonl"
    def tail(self) -> tuple[int, str]:
        files = sorted(self.dir.glob("events-*.jsonl"))
        if not files: return 0, ""
        last = files[-1].read_text(encoding="utf-8").strip().splitlines()
        if not last: return 0, ""
        ev = Event.parse(last[-1]); return ev.seq, ev.h
    def read_all(self) -> list[Event]:
        out = []
        for f in sorted(self.dir.glob("events-*.jsonl")):
            for line in f.read_text(encoding="utf-8").strip().splitlines():
                if line.strip(): out.append(Event.parse(line))
        return out
    def read_since(self, seq: int) -> list[Event]:
        return [e for e in self.read_all() if e.seq > seq]
    def append(self, type: str, payload: dict) -> Event:
        with open(self.lock, "w") as lf:
            fcntl.flock(lf, fcntl.LOCK_EX)
            try:
                seq, prev = self.tail()
                ev = Event(seq=seq + 1, ts=time.strftime("%Y-%m-%dT%H:%M:%S"),
                           type=type, payload=payload, prev=prev)
                with self._shard(ev.ts).open("a", encoding="utf-8") as fh:
                    fh.write(ev.line() + "\n"); fh.flush(); os.fsync(fh.fileno())
                return ev
            finally:
                fcntl.flock(lf, fcntl.LOCK_UN)

# ── 状态与 fold（纯函数）────────────────────────────────────────────
@dataclass
class State:
    seq: int = 0
    chain_tip: str = ""
    level: str = "L0"
    entries: dict = field(default_factory=dict)      # id -> entry dict
    importance_accum: int = 0
    emotion: dict = field(default_factory=lambda: {"valence":0.0,"arousal":0.5,"certainty":0.5,"stakes":0.0})
    reflect_since: int = 0

def apply(state: State, e: Event) -> None:            # 就地单事件推进（可增量）
    p = e.payload
    if e.type == "LIB_CREATED":
        state.level = p["level"]
    elif e.type == "ENTRY_APPENDED":
        if p["id"] in state.entries: raise ValueError(f"条目 id 重复: {p['id']}")
        state.entries[p["id"]] = p
        state.importance_accum += int(p.get("importance", 0))
        state.reflect_since += int(p.get("importance", 0))
    elif e.type == "ENTRY_INVALIDATED":
        state.entries[p["id"]]["validity"]["t_invalid"] = p["t_invalid"]
    elif e.type == "ENTRY_RETIRED":
        state.entries.pop(p["id"], None)
    elif e.type == "EMOTION_DECAYED":
        state.emotion = {k: round(v * p["decay"], 3) for k, v in state.emotion.items()}
    elif e.type == "REFLECT_DONE":
        state.importance_accum = 0; state.reflect_since = 0
    elif e.type == "LEVEL_CHANGED":
        state.level = p["to"]
    state.seq = e.seq; state.chain_tip = e.h

def fold(events: list[Event]) -> State:
    st = State()
    for e in events: apply(st, e)
    return st

# ── 提交（事件 → 状态快照 → 视图物化）────────────────────────────
class Library:
    def __init__(self, root: Path):
        self.root = Path(root); self.store = EventStore(self.root)
        (self.root / "memory").mkdir(parents=True, exist_ok=True)
    def commit(self, type: str, payload: dict) -> State:
        ev = self.store.append(type, payload)
        st = fold(self.store.read_all())          # 生产环境用增量 fold
        self.materialize(st)
        (self.root / "state.json").write_text(
            json.dumps({"seq": st.seq, "chain_tip": st.chain_tip, "level": st.level,
                        "importance_accum": st.importance_accum, "emotion": st.emotion},
                       ensure_ascii=False, indent=1), encoding="utf-8")
        return st
    def materialize(self, st: State) -> None:
        md = self.root / "memory"
        for f in md.glob("*.json"):
            if f.stem not in st.entries: f.rename(md / "attic" / f.name) if (md/"attic").exists() else f.unlink()
        for eid, e in st.entries.items():
            (md / f"{eid}.json").write_text(canon(e), encoding="utf-8")
    def state(self) -> State:
        return fold(self.store.read_all())
    def verify(self) -> dict:
        """V3：截断/篡改检出 —— 真值为 fold，state.json 仅为快照"""
        st = self.state()
        snap = json.loads((self.root / "state.json").read_text(encoding="utf-8"))
        return {"chain_continuous": self._chain_ok(),
                "truncated": snap.get("chain_tip") != st.chain_tip,
                "snapshot_tip": (snap.get("chain_tip") or "")[:12],
                "recomputed_tip": st.chain_tip[:12],
                "entries": len(st.entries), "accum": st.importance_accum}
    def _chain_ok(self) -> bool:
        prev = ""
        for e in self.store.read_all():
            if e.prev != prev or e.h != sha(e.prev + "\x00" + e.body): return False
            prev = e.h
        return True
