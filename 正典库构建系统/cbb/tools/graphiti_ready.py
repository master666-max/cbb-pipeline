# -*- coding: utf-8 -*-
"""graphiti_ready.py — U-C03.7 一键就绪自检 + 四触发器哨兵（工单 v1.8 §0）

自检四项 → READY/BLOCKED 清单：
  ① graphiti 包可导入？ ② Neo4j 连通（bolt 7687）？ ③ LLM 凭证在位？ ④ 嵌入端点在位？
四触发器哨兵（随段收口校准报告输出 GREEN/AMBER/RED，RED=增值层启用哨）：
  A 全局归纳型查询计数 ≥3 → RED（解锁社区检测+GraphRAG 摘要）
  B 多版本语料入库标志（库内 verified_against.path 多路径）→ RED（解锁 Resolver）
  C 按章回溯操作计数 ≥3 → RED（解锁 episode 三层）
  D 隔离矛盾积压 >50 或裁决滞后 >14 天 → RED（解锁 NLI 预筛）
  C 的阈值为就绪层建议值（工单未定），启用与否=段收口呈报审核线裁决。
用法：
  py -X utf8 graphiti_ready.py [--store 迷深实战-本体库] [--json]
  py -X utf8 graphiti_ready.py --sentinel --store 迷深实战-本体库
"""
from __future__ import annotations

import json
import re as _re
import socket
import sys
import urllib.request
from datetime import date as _date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import graphiti_bridge as gb  # noqa: E402

NEO4J_HOST, NEO4J_PORT = "127.0.0.1", 7687
LMSTUDIO_PORT = 1234


def _tcp_ok(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def check_graphiti_import() -> dict:
    try:
        import graphiti_core  # noqa: F401
        return {"item": "graphiti 包", "state": "READY", "note": "graphiti_core 可导入"}
    except ImportError:
        return {"item": "graphiti 包", "state": "BLOCKED",
                "note": "未安装：py -m pip install graphiti-core"}


def check_neo4j() -> dict:
    import os
    if not (os.environ.get("NEO4J_PASSWORD") or os.environ.get("NEO4J_AUTH")):
        return {"item": "Neo4j 连通", "state": "BLOCKED", "note": "缺 NEO4J_PASSWORD 环境变量"}
    if not _tcp_ok(NEO4J_HOST, NEO4J_PORT):
        return {"item": "Neo4j 连通", "state": "BLOCKED",
                "note": f"bolt {NEO4J_HOST}:{NEO4J_PORT} 不通（容器未拉起？docker start neo4j-step0）"}
    return {"item": "Neo4j 连通", "state": "READY", "note": "bolt 端口在听"}


def check_llm(preset: str) -> dict:
    if preset == "deepseek":
        import os
        if not os.environ.get("DEEPSEEK_API_KEY"):
            return {"item": f"LLM 凭证[{preset}]", "state": "BLOCKED",
                    "note": "缺 DEEPSEEK_API_KEY"}
        return {"item": f"LLM 凭证[{preset}]", "state": "READY", "note": "凭证在位（值不读出）"}
    if _tcp_ok("127.0.0.1", LMSTUDIO_PORT):
        return {"item": f"LLM 端点[{preset}]", "state": "READY", "note": "LM Studio :1234 在听"}
    return {"item": f"LLM 端点[{preset}]", "state": "BLOCKED", "note": "LM Studio :1234 不通"}


def check_embedding() -> dict:
    url = gb.EMBEDDING_PROFILE["base_url"].replace("http://127.0.0.1:8080/v1/embeddings",
                                                   "http://127.0.0.1:8080/v1/models")
    try:
        with urllib.request.urlopen(url, timeout=2):
            return {"item": "嵌入端点", "state": "READY", "note": f"{gb.EMBEDDING_PROFILE['model']} @8080 在位"}
    except Exception:
        return {"item": "嵌入端点", "state": "BLOCKED",
                "note": f"{gb.EMBEDDING_PROFILE['model']} @8080 不通"}


def ready_report(preset: str = "deepseek") -> dict:
    checks = [check_graphiti_import(), check_neo4j(), check_llm(preset), check_embedding()]
    overall = "READY" if all(c["state"] == "READY" for c in checks) else "BLOCKED"
    return {"overall": overall, "preset": preset, "checks": checks}


def trigger_sentinel(store_root: Path | str, logs_dir: Path | str | None = None,
                     logical_corpus: list[tuple[str, str]] | None = None) -> dict:
    """四触发器哨兵：只读扫描，输出 GREEN/AMBER/RED 状态表（并入段收口校准报告）。
    logical_corpus=[(path,sha),…]：显式声明逻辑语料版本（裁决④A 首选）；缺省走排除切片的启发式。"""
    store = Path(store_root)
    logs = Path(logs_dir) if logs_dir else store.parent / "迷深实战-工作区" / "logs"

    # A 全局归纳型查询计数（数据源=计数文件；无文件=0）
    cnt_file = logs / "global-query-count.txt"
    a_count = int(cnt_file.read_text(encoding="utf-8").strip() or 0) if cnt_file.exists() else 0
    a = {"trigger": "A 全局归纳型查询", "value": a_count, "state": "RED" if a_count >= 3 else "GREEN",
         "unlock": "社区检测+GraphRAG 摘要"}

    # B 多版本语料入库（2026-09-22 裁决 ④A：按"逻辑语料版本"判断——内容哈希不同＋有版本标识。
    # 切片/分区文件是同一版本的局部视图，**不算**多版本——修复实测误报
    # （旧口径按 verified_against.path 去重，把 ch0092~ch0131 切片全计成了"多版本"）。
    # 启发式口径（无显式 logical_corpus 时）：排除路径含 slice 段或 basename 形如 ch<数字> 的条目；
    # 排除明细入 excluded 留痕（T-5：每个数带口径）。显式传 logical_corpus=[(path,sha),…] 时以它为准。）
    _slice = _re.compile(r"[/\\]slice[/\\]|(?:^|[/\\])ch\d+", _re.IGNORECASE)
    versions: dict[str, str] = {}
    excluded: list[str] = []
    if logical_corpus:
        for p, sha in logical_corpus:
            if sha:
                versions.setdefault(sha, p)
        b_note = "口径=显式 logical_corpus 的不同内容哈希数"
    else:
        for lib in ("character", "relation", "setting", "event", "foreshadow", "timeline"):
            d = store / "libraries" / lib
            if not d.exists():
                continue
            for f in d.rglob("*.json"):
                try:
                    rec = json.loads(f.read_text(encoding="utf-8"))
                    va = rec.get("verified_against") or {}
                    p, sha = va.get("path"), va.get("sha")
                    if not p or not sha:
                        continue
                    if _slice.search(p) or _slice.search(Path(p).name):
                        excluded.append(p)
                        continue
                    versions.setdefault(sha, p)
                except Exception:
                    continue
        b_note = "口径=排除切片/分区局部视图后的不同内容哈希数；切片明细见 excluded（截断 20 条）"
    b_multi = len(versions) > 1
    b = {"trigger": "B 多版本语料入库",
         "value": {"logical_versions": len(versions),
                   "versions": [{"sha": k[:12], "path": v} for k, v in sorted(versions.items())[:10]],
                   "excluded_local_views": sorted(set(excluded))[:20]},
         "state": "RED" if b_multi else "GREEN",
         "unlock": "Resolver", "note": b_note}

    # C 按章回溯操作计数（数据源=计数文件；无文件=0；阈值=就绪层建议值）
    c_file = logs / "chapter-backtrack-count.txt"
    c_count = int(c_file.read_text(encoding="utf-8").strip() or 0) if c_file.exists() else 0
    c = {"trigger": "C 按章回溯操作", "value": c_count,
         "state": "RED" if c_count >= 3 else ("AMBER" if c_count > 0 else "GREEN"),
         "unlock": "episode 三层", "note": "阈值 3=就绪层建议值（工单未定，启用与否=审核线裁决）"}

    # D 隔离矛盾积压>50 或裁决滞后>14 天（2026-09-22 裁决②附带落地：
    # items/adjudications 带日期位（at）后滞后可算；历史件无日期 → UNKNOWN 如实披露）
    items = []
    iq = store / "quarantine-zone" / "items.jsonl"
    if iq.exists():
        items = [json.loads(x) for x in iq.read_text(encoding="utf-8").splitlines() if x.strip()]
    # A6 修复（审计 R4）：口径与 cbb_quarantine.status_report 对齐——按 adjudications 差集取 pending；
    # 原静态 status 过滤含已裁件 → RED 随时间必然触发且不可逆（信号失真）
    aq = store / "quarantine-zone" / "adjudications.jsonl"
    adj_ids = {json.loads(x)["item_id"] for x in aq.read_text(encoding="utf-8").splitlines() if x.strip()} \
        if aq.exists() else set()
    pend = [r for r in items if r.get("item_id") not in adj_ids]
    contradiction = sum(1 for r in pend if r.get("group") == "entity_unalignable")
    dated = sorted(it["at"] for it in pend if it.get("at"))
    today = _date.today()
    if dated:
        lag = (today - _date.fromisoformat(dated[0])).days
        lag_out = {"days": lag, "since": dated[0],
                   "口径": f"最早未裁登记日（带日期位 {len(dated)}/{len(items)} 条）"}
    else:
        lag_out = {"days": None, "since": None,
                   "口径": "UNKNOWN（在库条目均无日期位——历史件，不得编造）"}
    d = {"trigger": "D 隔离矛盾积压",
         "value": {"contradiction_pending": contradiction, "pending_total": len(pend),
                   "裁决滞后": lag_out},
         "state": "RED" if contradiction > 50 or (lag_out["days"] or 0) > 14 else
                  ("AMBER" if contradiction > 0 else "GREEN"),
         "unlock": "NLI 预筛",
         "note": "contradiction_pending 口径=group=entity_unalignable 的 pending（含默认分流噪音），"
                 "真矛盾另见 矛盾分流.py 四分类"}

    return {"A": a, "B": b, "C": c, "D": d,
            "summary": "RED=增值层启用哨；启用动作=段收口呈报审核线，本哨兵只报告不动作"}


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="graphiti 就绪自检+四触发器哨兵（U-C03.7）")
    ap.add_argument("--store", default="迷深实战-本体库")
    ap.add_argument("--preset", default="deepseek", choices=["deepseek", "lmstudio-flash"])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--sentinel", action="store_true")
    ns = ap.parse_args(argv)
    if ns.sentinel:
        rep = trigger_sentinel(ns.store)
        print(json.dumps(rep, ensure_ascii=False, indent=1 if not ns.json else None))
        return 0
    rep = ready_report(ns.preset)
    print(json.dumps(rep, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
