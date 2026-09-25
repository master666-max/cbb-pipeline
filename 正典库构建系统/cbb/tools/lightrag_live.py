# -*- coding: utf-8 -*-
"""lightrag_live.py — LightRAG 副本实时同步哨（时间颗粒度拉到顶：随写随同步）。

机制（2026-09-25 用户裁定"颗粒度拉到顶"）：
  · 旁路观察哨：每 interval 秒扫描 libraries/**.json 的 mtime——只 stat 不读（扫全库 ~百毫秒级）；
  · 变更文件才读取 → 按记录生成 kg 条目 → 与 sidecar（_fed-sources.json，与章收口同步共用）差集 →
    delta 喂入（ainsert_custom_kg 增量合并）；无变更=零嵌入零写入；
  · 原子写联动：store 落盘已改 temp+os.replace（A2b），观察哨不会读到半截文件；
  · 常驻进程（PersistentWorker 模式，LightRAG 1.5.7 队列绑定事件循环——经验④）；
  · 归一：实体名集缓存随新增文件增量维护，悬挂端点同款双向子串归一（与 neo4j_export 同规则）。
用法：
  py -X utf8 lightrag_live.py --interval 10            # 常驻哨
  py -X utf8 lightrag_live.py --once                   # 单轮（测试/手动）
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "cbb-store"))
sys.path.insert(0, str(HERE.parent / "cbb-quarantine"))

import lightrag_export as le  # noqa: E402  复用嵌入/桩/常量

SEP = "<SEP>"
_IDISH = None  # 延迟编译


def _record_entries(rec: dict, names: set[str]) -> tuple[list[dict], list[dict], list[dict]]:
    """单记录 → kg 条目（与 build_kg 同构；悬挂端点就地归一，无候选如实保留）。"""
    import re
    rid = rec.get("record_id")
    canon = rec.get("canonical") or {}
    txt = "；".join(o.get("text", "") for o in (rec.get("observations") or []) if o.get("text"))
    ents, rels, chunks = [], [], []

    def norm(nm: str) -> str:
        if nm in names:
            return nm
        cands = [c for c in names if len(c) >= 2 and (c in nm or (len(nm) >= 3 and nm in c))]
        return max(cands, key=len) if cands else nm

    if rec.get("record_type") == "entity" and canon.get("name"):
        ents.append({"entity_name": canon["name"], "entity_type": canon.get("entity_type") or "unknown",
                     "description": txt or canon["name"], "source_id": rid})
    elif rec.get("record_type") == "relation" and all(canon.get(k) for k in ("subject", "rel_type", "object")):
        s2, t2 = norm(canon["subject"]), norm(canon["object"])
        if s2 != t2:  # 归一后自环（两变体名同归一）→ 跳过，审计走对账披露
            fact = ((rec.get("observations") or [{}])[0].get("text")) or canon["rel_type"]
            rels.append({"src_id": s2, "tgt_id": t2,
                         "keywords": canon["rel_type"], "description": fact,
                         "source_id": rid, "weight": 1.0})
    if txt:
        chunks.append({"content": txt, "source_id": rid})
    return ents, rels, chunks


def _canon_names(store: Path) -> set[str]:
    names = set()
    for f in store.glob("libraries/*/*/*.json"):
        try:
            rec = json.loads(f.read_text(encoding="utf-8"))
            nm = (rec.get("canonical") or {}).get("name")
            if nm:
                names.add(nm)
        except Exception:
            continue
    return names


def _sidecar(work: Path) -> dict:
    p = work / "_fed-sources.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"entities": {}, "relationships": {}, "chunks": []}


async def poll_once(store: Path, work: Path, rag_holder: dict, interval_state: dict) -> dict:
    """单轮观察：mtime 扫描 → 变更记录构建 → sidecar 差集 → 喂入。
    重试位语义：last_poll 只在**成功**后推进——喂入失败保持原位，下一轮重试同批（毒批不静默丢）。"""
    from lightrag_delta_sync import _load_sidecar, _merge_sidecar
    library = store / "libraries"
    state = interval_state
    prev_poll = state.get("last_poll", 0.0)
    max_mt = prev_poll
    changed: list[Path] = []
    for f in library.glob("*/*/*.json"):
        try:
            mt = f.stat().st_mtime
        except OSError:
            continue
        if mt > state.get("last_poll", 0.0):
            changed.append(f)
        max_mt = max(max_mt, mt)
    if not changed:
        state["last_poll"] = max_mt  # 无写入：推进到当前（空转零成本）
        return {"changed": 0, "fed": False, "口径": "无写入"}

    ents, rels, chunks = [], [], []
    names = state.setdefault("names", _canon_names(store))
    parsed = []
    for f in changed:
        try:
            rec = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue  # 极端竞态：下一轮 mtime 仍新会再处理（最终一致）
        parsed.append(rec)
        nm = (rec.get("canonical") or {}).get("name")
        if nm and nm not in names:
            names.add(nm)
    for rec in parsed:
        a, b, c = _record_entries(rec, names)
        ents.extend(a)
        rels.extend(b)
        chunks.extend(c)
    fed = _load_sidecar(work)
    delta_e = [e for e in ents if sorted(str(e["source_id"]).split(SEP)) != fed["entities"].get(e["entity_name"])]
    delta_r = [r for r in rels
               if sorted(str(r["source_id"]).split(SEP)) !=
               fed["relationships"].get(f"{r['src_id']}{r['keywords']}{r['tgt_id']}")]
    have = set(fed["chunks"])
    delta_c = [c for c in chunks if c["source_id"] not in have]
    rep = {"changed": len(changed), "delta_entities": len(delta_e),
           "delta_relationships": len(delta_r), "delta_chunks": len(delta_c)}
    if not (delta_e or delta_r or delta_c):
        state["last_poll"] = max_mt
        return {**rep, "fed": False, "口径": "变更件无新 delta（重写同内容）"}

    rag = rag_holder.get("rag")
    if rag is None:
        raise SystemExit("rag 未初始化（常驻循环内调用）")
    try:
        await rag.ainsert_custom_kg({"entities": delta_e, "relationships": delta_r,
                                     "chunks": delta_c})
    except Exception:
        state["last_poll"] = prev_poll  # 失败：重试位不前进，下一轮重试同批
        raise
    _merge_sidecar(fed, {"entities": delta_e, "relationships": delta_r, "chunks": delta_c})
    work.mkdir(parents=True, exist_ok=True)
    (work / "_fed-sources.json").write_text(json.dumps(fed, ensure_ascii=False, indent=1),
                                            encoding="utf-8")
    state["last_poll"] = max_mt  # 成功才推进
    return {**rep, "fed": True, "llm_calls": le.CNT["llm_calls"]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", default=str(le.STORE))
    ap.add_argument("--work", default=str(le.WORK))
    ap.add_argument("--interval", type=float, default=10.0)
    ap.add_argument("--once", action="store_true")
    ns = ap.parse_args(argv)
    store, work = Path(ns.store), Path(ns.work)
    work.mkdir(parents=True, exist_ok=True)

    from lightrag import LightRAG
    from lightrag.utils import EmbeddingFunc
    rag_holder: dict = {}

    async def _setup():
        rag = LightRAG(working_dir=str(work),
                       embedding_func=EmbeddingFunc(embedding_dim=4096, func=le._embed_batch),
                       llm_model_func=le._llm_stub, llm_model_name="stub-no-llm")
        await rag.initialize_storages()
        rag_holder.update({"rag": rag, "loop": asyncio.get_running_loop()})

    async def _loop():
        await _setup()
        state: dict = {}
        work.mkdir(parents=True, exist_ok=True)

        async def _hb():  # 心跳独立任务：长喂入期间也持续刷新（否则会被误判死亡→章收口并发写副本）
            hb = work / "_live-heartbeat"
            while True:
                hb.write_text(str(time.time()), encoding="utf-8")
                await asyncio.sleep(10)

        hb_task = asyncio.create_task(_hb())
        try:
            while True:
                try:
                    rep = await poll_once(store, work, rag_holder, state)
                    if rep.get("changed") or rep.get("fed"):
                        print(json.dumps(rep, ensure_ascii=False), flush=True)
                except Exception as e:
                    print(json.dumps({"error": f"{type(e).__name__}: {str(e)[:120]}"},
                                     ensure_ascii=False), flush=True)
                await asyncio.sleep(ns.interval)
        finally:
            hb_task.cancel()

    if ns.once:
        # --once 也走常驻循环（实例必须在同一 loop）；last_poll=-1 ⇒ 首轮全量比对（delta 仍由 sidecar 差集裁决）
        async def _once():
            await _setup()
            state = {"last_poll": -1.0}
            rep = await poll_once(store, work, rag_holder, state)
            print(json.dumps(rep, ensure_ascii=False))
        asyncio.run(_once())
        return 0
    print(json.dumps({"live": True, "interval": ns.interval, "store": str(store)},
                     ensure_ascii=False), flush=True)
    asyncio.run(_loop())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
