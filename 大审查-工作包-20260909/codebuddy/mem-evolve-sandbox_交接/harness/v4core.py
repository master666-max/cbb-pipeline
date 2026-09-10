"""v4 事件溯源内核（对照臂 G6）。

只做三件 v3 做不到的事，用来判定"自演化引擎是否需要换底座"：
  1. importance_accum 由**事件流重放**得到，不做 read-modify-write → 并发不丢更新
  2. state 中持有 chain_tip + event_count → 截断攻击可被检出（v3 的 Merkle 根只锚定内容集合）
  3. 单一写入口 + 能力式校验（违反铁律的写入构造不出来）
约 130 行，对应实验报告 §2.5 原型 A。
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


class V4:
    def __init__(self, root):
        self.root = Path(root)
        (self.root / "events").mkdir(parents=True, exist_ok=True)
        self.events = self.root / "events" / "stream.jsonl"
        self.state_path = self.root / "state.json"
        # 人侧锚点（对应 v3 公理 E「请将 Merkle 根抄录至人侧」）：攻击者拿不到，故不随篡改更新
        self.anchor_path = self.root / ".." / (self.root.name + ".anchor.json")
        self.anchor_path = (self.root.parent / (self.root.name + ".anchor.json"))
        if not self.events.exists():
            self.events.write_text("", encoding="utf-8")
        if not self.state_path.exists():
            self._write_state({"chain_tip": "", "event_count": 0, "created_at": time.strftime("%F %T")})

    # ── 能力式写入口 ────────────────────────────────────────
    def append(self, entry: dict):
        if not (entry.get("source_event_id") or entry.get("evidence")):
            raise PermissionError("铁律2：无证据锚")
        if "sk-" in json.dumps(entry, ensure_ascii=False):
            raise PermissionError("铁律5：疑似密钥")
        prev = self._replay_tail()
        line = json.dumps({"ts": time.strftime("%F %T"), "prev": prev,
                           "op": "append", "payload": entry}, ensure_ascii=False)
        h = _sha((prev + "\x00" + line).encode())
        rec = json.loads(line)
        rec["h"] = h
        blob = (json.dumps(rec, ensure_ascii=False) + "\n").encode("utf-8")
        fd = os.open(str(self.events), os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
        try:
            os.write(fd, blob)     # 单次追加写：并发下不丢行
        finally:
            os.close(fd)
        st = json.loads(self.state_path.read_text(encoding="utf-8"))
        st["chain_tip"] = h
        st["event_count"] = self._replay_count()
        self._write_state(st)
        return h

    def _write_state(self, st):
        tmp = self.state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, self.state_path)

    def _lines(self):
        txt = self.events.read_text(encoding="utf-8")
        return [l for l in txt.splitlines() if l.strip()]

    def _replay_count(self):
        return len(self._lines())

    def _replay_tail(self):
        ls = self._lines()
        if not ls:
            return ""
        try:
            return json.loads(ls[-1]).get("h", "")
        except Exception:
            return ""

    # ── 派生量：全部由重放得到，不做 RMW ───────────────────────
    def importance_accum(self):
        tot = 0
        for l in self._lines():
            try:
                r = json.loads(l)
                if r.get("op") == "append":
                    tot += int(r["payload"].get("importance", 0))
            except Exception:
                continue
        return tot

    def replay_chain_ok(self):
        prev, ok = "", True
        for l in self._lines():
            try:
                r = json.loads(l)
            except Exception:
                return False
            if r.get("prev", "") != prev:
                ok = False
                break
            if _sha((prev + "\x00" + json.dumps({k: v for k, v in r.items() if k != "h"},
                                                ensure_ascii=False)).encode()) != r.get("h"):
                ok = False
                break
            prev = r["h"]
        return ok

    def snapshot_to_human(self):
        """把当前 tip/计数抄录至人侧（模拟公理 E 的人工抄录动作）。"""
        self._write_json(self.anchor_path, {"chain_tip": self._replay_tail(),
                                            "event_count": self._replay_count()})

    @staticmethod
    def _write_json(p, obj):
        Path(p).write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")

    # ── 对账 ──────────────────────────────────────────────
    def doctor(self):
        st = json.loads(self.state_path.read_text(encoding="utf-8"))
        tip_now, count_now = self._replay_tail(), self._replay_count()
        internal = {
            "chain_broken": not self.replay_chain_ok(),
            "tip_mismatch": tip_now != st.get("chain_tip", ""),
            "count_mismatch": count_now != st.get("event_count", -1),
        }
        anchor = {"no_anchor": True, "tip_vs_human": False, "count_vs_human": False}
        if self.anchor_path.exists():
            ha = json.loads(self.anchor_path.read_text(encoding="utf-8"))
            anchor = {"no_anchor": False,
                      "tip_vs_human": tip_now != ha.get("chain_tip", ""),
                      "count_vs_human": count_now != ha.get("event_count", -1)}
        return {"detected_internal": any(internal.values()), "flags": internal,
                "detected_by_human_anchor": (not anchor["no_anchor"])
                                            and (anchor["tip_vs_human"] or anchor["count_vs_human"]),
                "anchor_flags": anchor,
                "tip_now": tip_now[:12], "count_now": count_now,
                "count_state": st.get("event_count")}

    def truncate(self, k=2):
        """模拟截断攻击：删除尾部 k 个事件并重算 state（真·回滚）。"""
        ls = self._lines()[:-k]
        self.events.write_text("\n".join(ls) + ("\n" if ls else ""), encoding="utf-8")
        st = json.loads(self.state_path.read_text(encoding="utf-8"))
        st.pop("chain_tip", None)
        st.pop("event_count", None)
        self._write_state(st)
        # 攻击者按"诚实重算"修补 state
        st["chain_tip"] = self._replay_tail()
        st["event_count"] = self._replay_count()
        self._write_state(st)


V4_WORKER = r'''
import sys, importlib.util
root, i, harness = sys.argv[1], sys.argv[2], sys.argv[3]
spec = importlib.util.spec_from_file_location("v4c", harness + "/v4core.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
v = m.V4(root)
v.append({"id": "c" + i, "created_at": "2026-09-01", "updated_at": "",
          "content": "并发条目" + i, "keywords": [], "links": [],
          "source_event_id": "EV-C" + i, "importance": 5,
          "confidence": "中", "validity": {}})
'''
