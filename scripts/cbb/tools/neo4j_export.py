# -*- coding: utf-8 -*-
"""neo4j_export.py — 本体库 → Neo4j 图层增量 MERGE 导出（工单 v1.2 §0④；U-C01 工具件2）。

设计：实体→(:Entity {name,…}) 节点、关系记录→[:REL {rel_type,…}] 边，全部 MERGE（幂等，重放零增殖）；
Cypher 走 Neo4j HTTP 端点（stdlib urllib，零驱动依赖）。探活降级链（§0④）：
  宿主 http 7695（映射容器 7474）探活 → 不在且 docker daemon 在 → docker start neo4j-step0 重探 → 仍不在 → blocked 退出码 2 不阻塞。
凭据（D-004 不落文件）：--password > 环境变量 NEO4J_PASSWORD > docker inspect 运行时读取。
纯函数核心（collect_graph/cypher 构造/export_graph）单测见 test_neo4j_export.py（零网络）。

用法：
  py -X utf8 cbb/tools/neo4j_export.py --store <本体库根> [--base http://localhost:7695] \
      [--user neo4j] [--out export-report.json] [--no-start]
"""
import argparse
import base64
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

CONTAINER = "neo4j-step0"
BATCH = 250
# A13：现役容器映射 7695→7474(HTTP)/7694→7687(Bolt)；与连续性巡检同默认（NEO4J_HTTP 可覆盖）
DEFAULT_BASE = os.environ.get("NEO4J_HTTP", "http://localhost:7695")

CONSTRAINT_CYPHER = ("CREATE CONSTRAINT entity_name_unique IF NOT EXISTS "
                     "FOR (e:Entity) REQUIRE e.name IS UNIQUE")


def edge_id_for(subject: str, rel_type: str, object: str) -> str:
    """D2：确定性边 id（三元组内容哈希）——MERGE 世界里同一 (s,r,o) 恒同 id，回填可 join。"""
    h = hashlib.sha256(f"{subject}|{rel_type}|{object}".encode("utf-8")).hexdigest()[:12]
    return f"e-{h}"


def _edge_temporals(rec: dict) -> dict:
    """D1：valid_at/invalid_at ← 证据 chapter / supersede 态映射。
    valid_at=证据最早章（无可判证据→null）；invalid_at=活版本恒 null（开放区间=仍有效；
    collect_graph 只导出活版本，superseded 旧版本的失效章由后继版本 valid_at 承担）。"""
    ev = rec.get("evidence") or []
    chapters = [e.get("chapter") for e in ev if isinstance(e.get("chapter"), int)]
    return {"valid_at": min(chapters) if chapters else None, "invalid_at": None}


def collect_graph(store_root: Path) -> dict:
    """库文件 → 图快照：实体节点（活版本）+关系边（活版本）。superseded 旧版本排除。"""
    store_root = Path(store_root)
    superseded = set()
    idx = store_root / "supersede-index.jsonl"
    if idx.exists():
        superseded = {json.loads(ln)["old_id"] for ln in idx.read_text(encoding="utf-8").splitlines() if ln.strip()}
    nodes, edges = [], []
    mentions = set()  # (chapter, name) 去重——U-F03：章节点与 MENTIONS 边
    skipped: list[str] = []
    for f in sorted(store_root.glob("libraries/*/*/*.json")):
        try:
            text = f.read_text(encoding="utf-8")
        except OSError:
            # Windows MAX_PATH：合并后缀堆出的超长文件名（-m-m-…）常规路径打不开
            # → 走扩展长度前缀重试；仍失败则跳过并计数（T-5：不静默）
            try:
                text = Path("\\\\?\\" + str(f.resolve())).read_text(encoding="utf-8")
            except Exception:
                skipped.append(f.name)
                continue
        rec = json.loads(text)
        if rec.get("record_id") in superseded:
            continue
        canon = rec.get("canonical") or {}
        chapters = [e.get("chapter") for e in (rec.get("evidence") or [])
                    if isinstance(e.get("chapter"), int)]
        if rec.get("record_type") == "entity" and canon.get("name"):
            nodes.append({"name": canon["name"], "entity_type": canon.get("entity_type", ""),
                          "lib": rec.get("library"), "status": rec.get("status"),
                          "record_id": rec.get("record_id"), "version": rec.get("version", 1)})
            for ch in chapters:
                mentions.add((ch, canon["name"]))
        elif rec.get("record_type") == "relation" and all(canon.get(k) for k in ("subject", "rel_type", "object")):
            obs = rec.get("observations") or []
            tmp = _edge_temporals(rec)
            edges.append({"subject": canon["subject"], "rel_type": canon["rel_type"],
                          "object": canon["object"], "claim": bool(canon.get("claim")),
                          "fact": (obs[0].get("text", "") if obs and obs[0].get("text") else canon["rel_type"]),
                          "record_id": rec.get("record_id"),
                          "edge_id": edge_id_for(canon["subject"], canon["rel_type"], canon["object"]),
                          "valid_at": tmp["valid_at"], "invalid_at": tmp["invalid_at"],
                          "evidence": rec.get("evidence") or []})
            for ch in chapters:  # 关系两端都算"本章提及"
                mentions.add((ch, canon["subject"]))
                mentions.add((ch, canon["object"]))
    return {"nodes": nodes, "edges": edges,
            "mentions": [{"chapter": c, "name": n} for c, n in sorted(mentions)],
            "skipped_files": skipped}


def node_statement(n: dict) -> dict:
    return {"statement": ("MERGE (e:Entity {name:$name}) "
                          "ON CREATE SET e.created_tick = timestamp() "
                          "SET e.entity_type=$entity_type, e.lib=$lib, e.status=$status, e.version=$version"),
            "parameters": {"name": n["name"], "entity_type": n["entity_type"], "lib": n["lib"],
                           "status": n["status"], "version": n["version"]}}


def edge_statement(e: dict) -> dict:
    edge_id = e.get("edge_id") or edge_id_for(e["subject"], e["rel_type"], e["object"])
    return {"statement": ("MERGE (s:Entity {name:$subject}) "
                          "MERGE (o:Entity {name:$object}) "
                          "MERGE (s)-[r:REL {rel_type:$rel_type}]->(o) "
                          "SET r.claim=$claim, r.fact=$fact, r.edge_id=$edge_id, "
                          "r.valid_at=$valid_at, r.invalid_at=$invalid_at"),
            "parameters": {"subject": e["subject"], "object": e["object"], "rel_type": e["rel_type"],
                           "claim": e["claim"], "fact": e["fact"],
                           "edge_id": edge_id,
                           "valid_at": e.get("valid_at"), "invalid_at": e.get("invalid_at")}}


def evidence_edge_backfill(graph: dict) -> list[dict]:
    """D2：证据链→图边回填（导出后调用）。每条关系记录的每条证据挂
    graph_edge{edge_id, valid_at, invalid_at}，形如 evidence[].graph_edge 契约位。
    侧车输出（jsonl，键级去重），不改库内记录文件——旧件字节不动。"""
    out = []
    for e in graph.get("edges", []):
        if not e.get("evidence"):
            continue
        edge_id = e.get("edge_id") or edge_id_for(e["subject"], e["rel_type"], e["object"])
        ev_out = []
        for i, ev in enumerate(e["evidence"]):
            ev_out.append({"idx": i, "vol": ev.get("vol"), "chapter": ev.get("chapter"),
                           "line": ev.get("line"), "quote": ev.get("quote"),
                           "graph_edge": {"edge_id": edge_id,
                                          "valid_at": e.get("valid_at"),
                                          "invalid_at": e.get("invalid_at")}})
        out.append({"record_id": e.get("record_id"),
                    "triple": {"subject": e["subject"], "rel_type": e["rel_type"],
                               "object": e["object"]},
                    "edge_id": edge_id,
                    "valid_at": e.get("valid_at"), "invalid_at": e.get("invalid_at"),
                    "evidence": ev_out})
    return out


def append_backfill_sidecar(path: Path, entries: list[dict]) -> dict:
    """回填侧车落盘：jsonl 追加，键级去重（record_id+edge_id+quote+line 重复不追加）。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    seen = set()
    if path.exists():
        for ln in path.read_text(encoding="utf-8").splitlines():
            if ln.strip():
                r = json.loads(ln)
                seen.add((r.get("record_id"), r.get("edge_id"),
                          tuple((e.get("quote"), e.get("line")) for e in r.get("evidence", []))))
    added = 0
    with path.open("a", encoding="utf-8") as f:
        for r in entries:
            k = (r.get("record_id"), r.get("edge_id"),
                 tuple((e.get("quote"), e.get("line")) for e in r.get("evidence", [])))
            if k in seen:
                continue
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
            seen.add(k)
            added += 1
    return {"sidecar": str(path), "total_lines": len(seen), "added": added}


def chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def chapter_statement(m: dict) -> dict:
    """U-F03：章节点 + (章)-[:MENTIONS]->(实体) 边（MERGE 全幂等，重放零增殖）。
    "某一章出现了什么"＝一条查询；章节点的编号与锚点章的 chapter 同轴。"""
    return {"statement": ("MERGE (c:Chapter {no:$no}) "
                          "MERGE (e:Entity {name:$name}) "
                          "MERGE (c)-[:MENTIONS]->(e)"),
            "parameters": {"no": m["chapter"], "name": m["name"]}}


def export_graph(graph: dict, commit) -> dict:
    """commit(statements:list[dict])->None（抛异常即失败）。约束→节点分批→边分批→章提及分批；返回执行报告。"""
    commit([{"statement": CONSTRAINT_CYPHER}])
    for batch in chunks([node_statement(n) for n in graph["nodes"]], BATCH):
        commit(batch)
    for batch in chunks([edge_statement(e) for e in graph["edges"]], BATCH):
        commit(batch)
    mentions = graph.get("mentions", [])
    for batch in chunks([chapter_statement(m) for m in mentions], BATCH):
        commit(batch)
    return {"nodes": len(graph["nodes"]), "edges": len(graph["edges"]),
            "mentions": len(mentions),
            "batches": (1 + (len(graph["nodes"]) + BATCH - 1) // BATCH
                        + (len(graph["edges"]) + BATCH - 1) // BATCH
                        + (len(mentions) + BATCH - 1) // BATCH)}


# ---- 运输层（Neo4j HTTP /db/neo4j/tx/commit） ----

def http_commit(base: str, user: str, password: str, statements: list[dict], timeout: int = 60) -> None:
    body = json.dumps({"statements": statements}).encode("utf-8")
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    req = urllib.request.Request(f"{base.rstrip('/')}/db/neo4j/tx/commit", data=body,
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Basic {token}"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode("utf-8"))
    errs = [e for res in data.get("results", []) for e in res.get("errors", [])] or data.get("errors", [])
    if errs:
        raise RuntimeError(f"Neo4j 执行错误: {errs}")


def probe(base: str, timeout: int = 4) -> bool:
    try:
        with urllib.request.urlopen(base, timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


def docker_daemon_up() -> bool:
    return subprocess.run(["docker", "info"], capture_output=True, timeout=15).returncode == 0


def docker_start() -> bool:
    return subprocess.run(["docker", "start", CONTAINER], capture_output=True, timeout=60).returncode == 0


def derive_password(cli_pw: str) -> str | None:
    if cli_pw:
        return cli_pw
    import os
    if os.environ.get("NEO4J_PASSWORD"):
        return os.environ["NEO4J_PASSWORD"]
    try:  # 运行时读容器 env（NEO4J_AUTH=neo4j/<pw>）；凭据不落任何文件（D-004）
        out = subprocess.run(["docker", "inspect", "-f", "{{range .Config.Env}}{{println .}}{{end}}", CONTAINER],
                             capture_output=True, timeout=30)
        for ln in out.stdout.decode("utf-8", "ignore").splitlines():
            if ln.startswith("NEO4J_AUTH="):
                return ln.split("=", 1)[1].split("/", 1)[1]
    except Exception:
        pass
    return None


def ensure_server(base: str, allow_start: bool) -> bool:
    if probe(base):
        return True
    if not allow_start:
        return False
    if docker_daemon_up() and docker_start():
        for _ in range(10):  # Neo4j 启动最长等 ~50s
            time.sleep(5)
            if probe(base):
                return True
    return probe(base)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="本体库→Neo4j 增量 MERGE 导出（探活失败 blocked 不阻塞主链）")
    ap.add_argument("--store", required=True)
    # A13 修复（审计 R4）：与连续性巡检对齐——端口漂移记录（工单 §0④）现役 http=7695；
    # 原 7474 默认与巡检的 7695 同名变量两默认值，其一必错
    ap.add_argument("--base", default=DEFAULT_BASE)
    ap.add_argument("--user", default="neo4j")
    ap.add_argument("--password", default="")
    ap.add_argument("--out")
    ap.add_argument("--backfill-out", help="D2：证据→图边回填侧车 jsonl 路径（导出成功后回填，键级去重追加）")
    ap.add_argument("--no-start", action="store_true")
    args = ap.parse_args(argv)
    if not ensure_server(args.base, allow_start=not args.no_start):
        print(json.dumps({"status": "blocked", "reason": "Neo4j 探活失败且拉起无果（§0④：跳过导出，不阻塞主链）"},
                         ensure_ascii=False))
        return 2
    pw = derive_password(args.password)
    if pw is None:
        print(json.dumps({"status": "blocked", "reason": "凭据不可得（--password/NEO4J_PASSWORD/docker inspect 均无）"},
                         ensure_ascii=False))
        return 2
    graph = collect_graph(Path(args.store))

    def commit(statements):
        try:
            http_commit(args.base, args.user, pw, statements)
        except RuntimeError as e:
            # step0 期已建同名索引（非约束）：约束创建撞 IndexAlreadyExists → 容错继续
            # （索引已在即 MERGE {name} 定位有效；MERGE 幂等不依赖唯一约束）
            if "IndexAlreadyExists" in str(e):
                return
            raise

    report = export_graph(graph, commit)
    # 导出后对账：图上实点/实边数
    counts = {}
    for label, cyq in (("nodes", "MATCH (e:Entity) RETURN count(e) AS c"),
                       ("edges", "MATCH ()-[r:REL]->() RETURN count(r) AS c")):
        body = json.dumps({"statements": [{"statement": cyq}]}).encode()
        token = base64.b64encode(f"{args.user}:{pw}".encode()).decode()
        req = urllib.request.Request(f"{args.base.rstrip('/')}/db/neo4j/tx/commit", data=body,
                                     headers={"Content-Type": "application/json", "Authorization": f"Basic {token}"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode("utf-8"))
        counts[label] = data["results"][0]["data"][0]["row"][0]
    report.update({"status": "ok", "graph_counts_after": counts})
    if args.backfill_out:  # D2：导出成功后回填证据链→图边（侧车，键级去重追加）
        bf = append_backfill_sidecar(Path(args.backfill_out), evidence_edge_backfill(graph))
        report["backfill"] = bf
    if args.out:
        Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
