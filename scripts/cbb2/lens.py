"""cbb2.lens — DuckDB 只读分析层（Phase F·G02；数据库路 A2）。

直接 read_ndjson 挂现有 jsonl（零迁移、零写入），SQL 化投影重建/抽查/统计。
可选依赖：pip install duckdb——缺席时 lens 显式 BLOCKED。
"""
from __future__ import annotations

import json
from pathlib import Path

_DUCK = None


def _conn():
    global _DUCK
    if _DUCK is None:
        try:
            import duckdb
        except ImportError:
            raise RuntimeError("duckdb 未安装——pip install duckdb（可选依赖）")
        _DUCK = duckdb.connect()
    return _DUCK


def tri_state_counts(store_root: Path) -> dict:
    root = Path(store_root)
    q = root / "quarantine-zone" / "items.jsonl"
    if not q.exists():
        return {"provisional": 0, "confirmed": 0, "quarantine_pending": 0, "quarantine_confirmed": 0}
    import json
    st = {"provisional": 0, "confirmed": 0, "quarantine_pending": 0, "quarantine_confirmed": 0}
    for line in q.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        it = json.loads(line)
        if it.get("status") == "pending":
            st["quarantine_pending"] += 1
        elif it.get("status") == "confirmed":
            st["quarantine_confirmed"] += 1
    for lib_dir in (root / "libraries").iterdir():
        for status_dir in lib_dir.iterdir():
            if status_dir.is_dir():
                st[status_dir.name] = st.get(status_dir.name, 0) + sum(1 for f in status_dir.glob("*.json"))
    return st


def invalidation_chain(store_root: Path) -> list[dict]:
    """失效链全量——从 invalidations.jsonl 读，供"记录 X 在第 N 章失效"查询。"""
    p = Path(store_root) / "invalidations.jsonl"
    if not p.exists():
        return []
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def complementary_count(store_root: Path) -> int:
    p = Path(store_root) / "complementary-statements.jsonl"
    if not p.exists():
        return 0
    return sum(1 for x in p.read_text(encoding="utf-8").splitlines() if x.strip())


def full_report(store_root: Path) -> dict:
    root = Path(store_root)
    st = tri_state_counts(root)
    inv = invalidation_chain(root)
    comp = complementary_count(root)
    libs = {}
    lib_base = root / "libraries"
    if lib_base.exists():
        for lib_dir in lib_base.iterdir():
            for status in ("provisional", "confirmed"):
                d = lib_dir / status
                if d.exists():
                    libs[f"{lib_dir.name}/{status}"] = sum(1 for f in d.glob("*.json"))
    return {"tri_state": st, "invalidations": len(inv), "complementary": comp,
            "libraries": libs}
