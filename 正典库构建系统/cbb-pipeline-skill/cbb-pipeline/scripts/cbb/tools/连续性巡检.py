# -*- coding: utf-8 -*-
"""连续性巡检.py — 门1 连续性域的**双载体**实现（U-F02；2026-09-23）

设计（对应工单判据：①双载体一致 ②图缺席自动兜底且同形 ③规则只存一处）：
    · **一套规则、两个装载器、一个求值器**：
        file_loader(store)  → 视图
        graph_loader(neo4j) → 视图
        evaluate(视图)      → findings          ← 规则只在这一处实现
    · 逆类型/对称表**从 cbb-gate1 导入**（禁止抄第二份）：
        RELATIONSHIP_INVERSES / SYMMETRIC_RELATIONSHIPS
    · 视图带 capabilities：某载体缺某类数据时，对应规则**报"不可用"而非给出不同答案**（口径注明，T-2/T-5）
    · auto：先探图，不可用→自动落文件；输出同形（backend 字段注明载体）
规则（4 条）：
    1. orphan_ref          孤悬引用：关系两端不在实体集合（含别名）
    2. inverse_backlink    逆类型/对称回链缺失（12 对 + 12 项）
    3. dead_walking        死人走路：death_chapter 之后仍有出场（需 appearances）
    4. alias_conflict      别名冲突：同一别名指向 ≥2 个实体
用法：
    py -X utf8 连续性巡检.py --store <本体库> [--backend auto|file|graph] [--compare]
    图载体凭证走环境变量（D-004）：NEO4J_HTTP / NEO4J_USER / NEO4J_PASSWORD
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "cbb-gate1"))
try:  # 规则单一来源：门1 的表（缺失时明确报错，不静默降级成"没有规则"）
    from cbb_gate1 import RELATIONSHIP_INVERSES, SYMMETRIC_RELATIONSHIPS  # type: ignore
except Exception as e:  # pragma: no cover
    raise SystemExit(f"无法从 cbb-gate1 导入逆类型/对称表（规则单一来源）：{e}")

LIBS = ("character", "relation", "setting", "event", "foreshadow", "timeline")
ENTITY_LIBS = ("character", "setting")  # 视作实体来源的库（generic：有 canonical.name 的记录）


def _records(store: Path, lib: str):
    d = store / "libraries" / lib
    if not d.exists():
        return
    for status in ("provisional", "confirmed"):
        for f in sorted((d / status).glob("*.json")):
            try:
                yield json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue


def _jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


# ---------- 装载器 ----------

def file_loader(store_root: Path | str) -> dict:
    store = Path(store_root)
    entities, aliases, relations, deaths = set(), {}, [], {}
    for lib in LIBS:
        for rec in _records(store, lib):
            canon = rec.get("canonical") or {}
            if rec.get("record_type") == "entity" or lib in ENTITY_LIBS:
                name = canon.get("name")
                if name:
                    entities.add(name)
                    if canon.get("death_chapter") is not None:
                        deaths[name] = canon["death_chapter"]
            if rec.get("record_type") == "relation" and canon.get("subject") and canon.get("object"):
                relations.append({"subject": canon["subject"], "object": canon["object"],
                                  "rel_type": canon.get("rel_type"), "record_id": rec.get("record_id")})
    skipped = 0
    for row in _jsonl(store / "aliases.jsonl"):
        a = row.get("alias")
        if not isinstance(a, str) or not a.strip():  # 真库存在异构行（别名位为对象等）——跳过并计数（T-5 口径）
            skipped += 1
            continue
        aliases.setdefault(a, set()).add(row.get("entity_id"))
    apps = [{"entity": r["entity"], "chapter": r.get("chapter")} for r in _jsonl(store / "appearances.jsonl")]
    return {"entities": entities, "aliases": aliases, "relations": relations,
            "appearances": apps, "deaths": deaths,
            "capabilities": {"entities": True, "aliases": True, "relations": True,
                             "appearances": True, "deaths": True},
            "backend": "file", "skipped_alias_rows": skipped}


READ_ONLY_FORBIDDEN = ("create", "merge", "set ", "delete", "remove", "drop", "call {",
                       "load csv", "foreach", "import csv")


def _assert_read_only(statement: str) -> None:
    """本件自称"只读巡检"，但走的是 `/db/{db}/tx/commit`——那是**能写**的端点。
    旧版只靠注释声明只读；现在把它变成机械断言：写关键字出现即拒发，
    免得一次正则写错的 Cypher 把派生层变成改写层（图与真源从此两头不一致，还没人知道）。"""
    low = " " + statement.lower() + " "
    hit = [k for k in READ_ONLY_FORBIDDEN if k in low]
    if hit:
        raise ValueError(f"连续性巡检只允许读查询，语句含写关键字 {hit}：{statement[:90]}")


def _cypher(base: str, database: str, statement: str, user: str, password: str,
            parameters: dict | None = None) -> list[dict]:
    _assert_read_only(statement)
    stmt = {"statement": statement, "parameters": parameters or {}}
    payload = json.dumps({"statements": [stmt]}).encode("utf-8")
    req = urllib.request.Request(base.rstrip("/") + f"/db/{database}/tx/commit", data=payload,
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Basic " + base64.b64encode(
                                              f"{user}:{password}".encode()).decode()})
    with urllib.request.urlopen(req, timeout=20) as resp:
        out = json.loads(resp.read().decode("utf-8"))
    if out.get("errors"):
        raise RuntimeError(f"Cypher 错误: {out['errors'][:1]}")
    return out["results"][0]["data"]


def graph_loader(base: str | None = None, database: str = "neo4j",
                 user: str | None = None, password: str | None = None,
                 ns: str | None = None) -> dict:
    base = base or os.environ.get("NEO4J_HTTP", "http://localhost:7474")  # 7474=Neo4j 出厂默认，非某项目的映射端口
    user = user or os.environ.get("NEO4J_USER", "neo4j")
    password = password or os.environ.get("NEO4J_PASSWORD")
    if not password:
        raise RuntimeError("缺 NEO4J_PASSWORD（D-004：凭证只走环境变量）")
    # 读侧必须带命名空间过滤：不带就是"一条查询扫到别人项目的实体"，产出零孤悬零矛盾的假干净
    ns = (ns or os.environ.get("CBB_NAMESPACE") or "").strip()
    if not ns:
        raise RuntimeError("缺命名空间：graph 载体需 --namespace/env CBB_NAMESPACE；"
                           "无过滤的全库读不许当巡检依据（改用 --backend file）")
    ents = [r["row"][0] for r in _cypher(base, database,
                                         "MATCH (e:Entity) WHERE e.ns=$ns RETURN e.name",
                                         user, password, {"ns": ns})]
    rels = [{"subject": r["row"][0], "object": r["row"][1], "rel_type": r["row"][2], "record_id": None}
            for r in _cypher(base, database,
                             "MATCH (s:Entity)-[r:REL]->(o:Entity) "
                             "WHERE s.ns=$ns AND o.ns=$ns RETURN s.name, o.name, r.rel_type",
                             user, password, {"ns": ns})]
    return {"entities": set(ents), "aliases": {}, "relations": rels,
            "appearances": None, "deaths": {},
            "capabilities": {"entities": True, "aliases": False, "relations": True,
                             "appearances": False, "deaths": False,
                             # 结构性失明：导出器 MERGE 端点时自动创建 :Entity 节点 →
                             # "孤悬引用"在图上不可能出现，**不是**"查了没有"，是"查不了"
                             "orphan_detectable": False},
            "backend": "graph"}


def probe_graph(base: str | None = None, timeout: float = 4.0) -> bool:
    base = base or os.environ.get("NEO4J_HTTP", "http://localhost:7474")  # 7474=Neo4j 出厂默认，非某项目的映射端口
    try:
        with urllib.request.urlopen(base.rstrip("/") + "/", timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


# ---------- 求值器（规则只在这里） ----------

def evaluate(view: dict) -> list[dict]:
    f: list[dict] = []
    bk = view.get("backend", "?")
    ents = view["entities"]
    alias_names = set(view["aliases"].keys())

    names_ok = lambda n: (n in ents) or (n in alias_names)  # noqa: E731

    if view["capabilities"].get("orphan_detectable", True):
        for rel in view["relations"]:
            for side in ("subject", "object"):
                if not (rel.get(side) or "").strip():
                    f.append({"rule": "orphan_ref", "backend": bk, "record_id": rel.get("record_id"),
                              "detail": f"关系缺 {side}（空值）"})
                elif not names_ok(rel[side]):
                    f.append({"rule": "orphan_ref", "backend": bk, "record_id": rel.get("record_id"),
                              "detail": f"孤悬引用：{rel[side]!r} 不在实体集合（{rel.get('subject')} -[{rel.get('rel_type')}]-> {rel.get('object')}）"})
    else:
        f.append({"rule": "orphan_ref", "backend": bk, "record_id": None,
                  "detail": "不可用：本载体结构性失明——导出器自动补全关系端点（MERGE 建点），孤悬在图上不可表达"})

    triples = {(r["subject"], r["rel_type"], r["object"]) for r in view["relations"] if r.get("rel_type")}
    for rel in view["relations"]:
        t, s, o = rel.get("rel_type"), rel.get("subject"), rel.get("object")
        if not t:
            continue
        if t in SYMMETRIC_RELATIONSHIPS:
            if (o, t, s) not in triples:
                f.append({"rule": "inverse_backlink", "backend": bk, "record_id": rel.get("record_id"),
                          "detail": f"对称关系 {t} 缺反向边: {o} -[{t}]-> {s}"})
        elif t in RELATIONSHIP_INVERSES:
            inv = RELATIONSHIP_INVERSES[t]
            if (o, inv, s) not in triples:
                f.append({"rule": "inverse_backlink", "backend": bk, "record_id": rel.get("record_id"),
                          "detail": f"逆类型缺回链: {s} -[{t}]-> {o} 缺 {o} -[{inv}]-> {s}"})

    if view["capabilities"].get("appearances"):
        for a in view["appearances"] or []:
            dc = view["deaths"].get(a["entity"])
            if dc is not None and a.get("chapter") is not None and a["chapter"] > dc:
                f.append({"rule": "dead_walking", "backend": bk, "record_id": None,
                          "detail": f"死人走路：{a['entity']} 死于第 {dc} 章，但第 {a['chapter']} 章仍有出场"})
    else:
        f.append({"rule": "dead_walking", "backend": bk, "record_id": None,
                  "detail": "不可用：本载体无出场数据（口径注明，未判）"})

    if view["capabilities"].get("aliases"):
        for alias, ids in view["aliases"].items():
            if len(ids) >= 2:
                f.append({"rule": "alias_conflict", "backend": bk, "record_id": None,
                          "detail": f"别名 {alias!r} 指向 {len(ids)} 个实体: {sorted(ids)[:3]}"})
    else:
        f.append({"rule": "alias_conflict", "backend": bk, "record_id": None,
                  "detail": "不可用：本载体无别名数据（口径注明，未判）"})
    return f


def run(store_root: Path | str, backend: str = "auto", graph_base: str | None = None) -> dict:
    if backend not in ("auto", "file", "graph"):
        raise ValueError(f"非法 backend={backend!r}")
    used, note = backend, ""
    if backend == "auto":
        used = "graph" if probe_graph(graph_base) else "file"
        note = f"auto→{used}（{'图探活成功' if used == 'graph' else '图不可用，自动兜底'}）"
    try:
        view = graph_loader(graph_base) if used == "graph" else file_loader(store_root)
    except Exception as e:
        if backend == "graph":
            raise
        view, used, note = file_loader(store_root), "file", f"图装载失败({str(e)[:60]})→兜底 file"
    return {"backend": used, "note": note, "findings": evaluate(view),
            "口径": "载体见 backend；不可用项在 findings 中显式标注，不静默"}


def main(argv=None) -> int:  # pragma: no cover
    ap = argparse.ArgumentParser(description="连续性巡检（门1 双载体；U-F02）")
    ap.add_argument("--store", required=True)
    ap.add_argument("--backend", default="auto", choices=["auto", "file", "graph"])
    ap.add_argument("--compare", action="store_true", help="双载体对照（一致性断言）")
    ns = ap.parse_args(argv)
    if ns.compare:
        vf, vg = file_loader(ns.store), graph_loader()
        a, b = evaluate(vf), evaluate(vg)
        ka = {(x["rule"], x["detail"]) for x in a}
        kb = {(x["rule"], x["detail"]) for x in b}
        print(f"覆盖度口径：file 实体{len(vf['entities'])} 关系{len(vf['relations'])} 别名{len(vf['aliases'])} "
              f"| graph 实体{len(vg['entities'])} 关系{len(vg['relations'])} 别名—")
        print(f"file={len(a)} graph={len(b)} 差异={len(ka ^ kb)}")
        print("差异构成：别名/出场类＝图载体能力缺失（应显式标注不可用）；孤悬＝图结构性失明（导出自动补点）；"
              "其余差异才是需核的真分歧 —— 覆盖度差(关系 " + str(len(vf["relations"])) + " vs " + str(len(vg["relations"])) + ")会放大此表")
        for d in sorted(ka ^ kb)[:20]:
            print("  Δ", d)
        return 0
    rep = run(ns.store, ns.backend)
    print(f"载体={rep['backend']} {rep['note']}")
    for x in rep["findings"]:
        print(f"  [{x['rule']}] {x['detail']}")
    print(f"合计 {len(rep['findings'])} 条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
