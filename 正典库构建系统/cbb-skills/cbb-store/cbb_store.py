# -*- coding: utf-8 -*-
"""cbb_store.py — CBB B1/B5 三态写入纪律+版本化存储（M1 骨架，jsonl-file 后端）

纪律：文件即记录写后不改；状态迁移走旁车 transitions.jsonl（append-only）；
supersede 新版本新文件+索引旁车；quarantine 不进 library 目录（B1）。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "contracts"))
sys.path.insert(0, str(HERE.parent / "cbb-quarantine"))
import cbb_contracts  # noqa: E402
from cbb_quarantine import QuarantineZone  # noqa: E402

# Part XI 名义阈值（M1 无校准器；P2 由置信度校准器标定取代）
TAU_CONFIRMED = 0.97
TAU_PROVISIONAL = 0.85

LIBRARIES = ("event", "character", "timeline", "relation", "setting", "foreshadow")
ADMIT_DECISIONS = ("confirmed", "provisional", "quarantine")
TRANSITION_BYS = ("human", "shadow", "promotion")  # Record.provenance.status_history.by 枚举


def route_by_confidence(confidence: float) -> str:
    """置信度路由：confirmed 永不因置信度单独达成（门2b/人工通道缺席时的 B1 保守纪律）。"""
    if confidence >= TAU_PROVISIONAL:
        return "provisional"
    return "quarantine"


class ThreeStateStore:
    def __init__(self, root: Path, backend: str = "jsonl-file"):
        if backend != "jsonl-file":
            raise NotImplementedError(
                "M1 仅实现 jsonl-file 后端。P2 接入 Neo4j/Graphiti（Step0 Tier2 已验证配置："
                "bolt://localhost:7687 + DeepSeek + LM Studio 嵌入），凭证走环境变量（D-004）。")
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.zone = QuarantineZone(self.root / "quarantine-zone")

    # ---- 基元 ----
    def _append(self, name: str, obj: dict) -> None:
        p = self.root / name
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False, sort_keys=True) + "\n")

    def _load_all(self, name: str) -> list[dict]:
        p = self.root / name
        if not p.exists():
            return []
        return [json.loads(ln) for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]

    def _lib_path(self, library: str, status: str, record_id: str) -> Path:
        return self.root / "libraries" / library / status / f"{record_id}.json"

    def _write_immutable(self, path: Path, obj: dict):
        if path.exists():
            return path, False
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=1),
                        encoding="utf-8")
        return path, True

    # ---- 三态入库 ----
    def admit(self, record: dict, decision: str, gate_trace_entry: dict | None = None,
              quarantine_group: str | None = None, quarantine_detail: str = ""):
        """candidate → confirmed/provisional/quarantine。
        confirmed/provisional：严格契约校验（status 置为目标态）+ status_history 初始条目；
        quarantine：不进 library，登记隔离区（B1：库中只有 confirmed/provisional）。"""
        if decision not in ADMIT_DECISIONS:
            raise ValueError(f"非法入库决定 {decision!r}，合法={ADMIT_DECISIONS}")
        rid = record.get("record_id")
        if not rid:
            raise ValueError("record 缺 record_id")

        if decision == "quarantine":
            iid, created = self.zone.register(
                group=quarantine_group or "low_confidence",
                detail=quarantine_detail or "门1 拦截件",
                record_id=rid, source="cbb-store",
                blocks=[],
            )
            return iid, created

        stored = dict(record)
        stored["status"] = decision
        hist_entry = {"from": "candidate", "to": decision, "by": "promotion"}
        stored.setdefault("provenance", {})
        stored["provenance"].setdefault("status_history", []).append(hist_entry)
        if gate_trace_entry:
            stored["provenance"].setdefault("gate_trace", []).append(gate_trace_entry)
        cbb_contracts.validate_record(stored)  # 严格：库内态必须全契约合规
        path = self._lib_path(stored["library"], decision, rid)
        return self._write_immutable(path, stored)

    # ---- 状态迁移（旁车日志，文件不动） ----
    def status_transition(self, record_id: str, to_status: str, by: str = "human",
                          note: str = "") -> dict:
        """provisional→confirmed（人工/交叉印证/门2b）或 confirmed→provisional（影子审计降级）。
        迁移落 transitions.jsonl；record 文件字节不动（文件后端的 status_history 等价物）。"""
        if by not in TRANSITION_BYS:
            raise ValueError(f"非法 by {by!r}")
        if to_status not in ("confirmed", "provisional"):
            raise ValueError("文件后端迁移仅限库内两态；quarantine/rejected 走隔离区裁决通道")
        current = self._find(record_id)
        if current is None:
            raise KeyError(f"记录不在库: {record_id}")
        entry = {"record_id": record_id, "from": current["status"], "to": to_status,
                 "by": by, "note": note}
        self._append("transitions.jsonl", entry)
        return entry

    def effective_status(self, record_id: str) -> str | None:
        """文件态 + 旁车迁移的最终态。"""
        rec = self._find(record_id)
        if rec is None:
            return None
        status = rec["status"]
        for t in self._load_all("transitions.jsonl"):
            if t["record_id"] == record_id:
                status = t["to"]
        return status

    # ---- 版本化 supersedes（B5） ----
    def supersede(self, old_id: str, new_record: dict):
        """以 new_record 取代 old_id：新文件 version=old.version+1、supersedes=old_id；
        旧件字节不动；supersede-index.jsonl 登记链。返回 (new_path, created)。"""
        old = self._find(old_id)
        if old is None:
            raise KeyError(f"被取代记录不在库: {old_id}")
        if new_record.get("record_id") == old_id:
            raise ValueError("新版本必须换 record_id（旧件不可覆盖）")
        new = dict(new_record)
        if new.get("status") not in ("confirmed", "provisional"):
            new["status"] = "provisional"  # 修订版默认 provisional 待重过门（B1 保守）
        new["version"] = old["version"] + 1
        new["supersedes"] = old_id
        new.setdefault("provenance", {}).setdefault("status_history", []).append(
            {"from": "superseded:" + old_id, "to": new.get("status", "provisional"),
             "by": "promotion"})
        cbb_contracts.validate_record(new)
        path = self._lib_path(new["library"], new["status"], new["record_id"])
        result = self._write_immutable(path, new)
        if result[1]:
            self._append("supersede-index.jsonl",
                         {"old_id": old_id, "new_id": new["record_id"],
                          "version": new["version"]})
        return result

    def resolve_latest(self, record_id: str) -> dict | None:
        """沿 supersedes 链取最新版本。"""
        chain = {e["old_id"]: e["new_id"] for e in self._load_all("supersede-index.jsonl")}
        cur = record_id
        seen = set()
        while cur in chain and cur not in seen:
            seen.add(cur)
            cur = chain[cur]
        return self._find(cur)

    # ---- 查询 ----
    def _find(self, record_id: str):
        for lib in LIBRARIES:
            for status in ("confirmed", "provisional"):
                p = self._lib_path(lib, status, record_id)
                if p.exists():
                    return json.loads(p.read_text(encoding="utf-8"))
        return None

    def stats(self) -> dict:
        out = {"libraries": {}, "quarantine_pending": len(self.zone.pending())}
        for lib in LIBRARIES:
            counts = {}
            for status in ("confirmed", "provisional"):
                d = self.root / "libraries" / lib / status
                counts[status] = len(list(d.glob("*.json"))) if d.exists() else 0
            if any(counts.values()):
                out["libraries"][lib] = counts
        return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="CBB B1/B5 三态入库（M1 骨架）")
    ap.add_argument("--root", required=True, help="库根目录")
    ap.add_argument("--stats", action="store_true", help="打印库统计")
    args = ap.parse_args(argv)
    store = ThreeStateStore(Path(args.root))
    if args.stats:
        print(json.dumps(store.stats(), ensure_ascii=False, indent=1))
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
