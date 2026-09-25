# -*- coding: utf-8 -*-
"""run_chapter.py — 通用章节管线（U-C02+ 主力；每章即读即抽即落盘的落盘侧）。
流程：边界表切片 → coordinate 清单 → 规范化候选（v2 设计）→ gate1（current_chapter=本章）→
置信路由/隔离 → store 双轨 → 别名/出场登记 → 锚点记录（tick=摄入序）→ 嵌入扫描+Neo4j 导出（探活降级）。
用法：py -X utf8 run_chapter.py --chapter 0003 [--no-aux]
  输入：candidates/extraction-ch0003.json（代理亲抽源件）
  产物：manifest/manifest-ch0003.json、candidates/cands-ch0003.json、gate1/gate1-ch0003.json、
        logs/ch0003-pipeline-summary.json
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORK = HERE.parent
CBB = WORK.parent / "cbb"
ROOT = WORK.parent
CORPUS = ROOT.parent / "语料分析" / "corpus" / "clean_full.txt"
STORE_ROOT = ROOT / "迷深实战-本体库"
sys.path.insert(0, str(CBB / "contracts"))
sys.path.insert(0, str(CBB / "cbb-coordinate"))
sys.path.insert(0, str(CBB / "cbb-gate1"))
sys.path.insert(0, str(CBB / "cbb-store"))
sys.path.insert(0, str(CBB / "cbb-anchor"))
sys.path.insert(0, str(CBB / "cbb-extract"))
sys.path.insert(0, str(CBB / "tools"))
import cbb_contracts   # noqa: E402
import cbb_coordinate  # noqa: E402
import cbb_gate1       # noqa: E402
import cbb_store       # noqa: E402
import cbb_anchor      # noqa: E402
import cbb_extract     # noqa: E402

TAU = cbb_store.TAU_PROVISIONAL
SUBCLASS_GROUP = {"contradiction_pending": "entity_unalignable",
                  "extrapolation_unverified": "low_confidence",
                  "overdue_omission": "low_confidence"}
# 调度层机械归一（2026-09-19，先例=批9-10 ch0079/ch0121 手工修正；确定性零裁量，每次改写计入 summary 留痕）
LIBRARY_NORMALIZE = {"organization": "character", "location": "setting",
                     "item": "setting", "magic": "setting", "skill": "setting",
                     "title": "setting"}  # 2026-09-21 ch0191『支配之王』称号首例：称号类实体库内惯例入 setting
# observations.category 枚举外值→契约枚举（2026-09-20 ch0136 'behavior' 首例；确定性零裁量）
OBS_CATEGORY_NORMALIZE = {"behavior": "manifestation",
                          "setting": "knowledge"}  # 2026-09-21 ch0199 沃尔斯家庭院首例：场景设定事实观察→knowledge


def boundary(chapter_no: int) -> dict:
    bt = json.loads((WORK / "manifest" / "boundary-table-v1.json").read_text(encoding="utf-8"))
    ch = next(c for c in bt["chapters"] if c["chapter_no"] == chapter_no)
    return ch


def slice_text(ch: dict) -> str:
    lines = CORPUS.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    return "\n".join(lines[ch["marker_line"] - 1:ch["line_end"]])


def core_id(rec_type, canonical, evidence):
    payload = {"c": canonical, "e": evidence}
    h = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:12]
    return f"cand-{rec_type}-{h}"


def normalize(raw: dict, verified: dict) -> list[dict]:
    out, remaps = [], []
    for c in raw["candidates"]:
        canonical = dict(c["canonical"])
        lib = c["library"]
        lib = c["library"]
        if lib not in cbb_store.LIBRARIES and lib in LIBRARY_NORMALIZE:
            remaps.append((c["type"], c["canonical"].get("name") or c["canonical"].get("subject"), lib, LIBRARY_NORMALIZE[lib]))
            lib = LIBRARY_NORMALIZE[lib]
        obs_norm = False
        for o in c.get("observations", []):
            if o.get("category") in OBS_CATEGORY_NORMALIZE:
                o["category"] = OBS_CATEGORY_NORMALIZE[o["category"]]
                obs_norm = True
        if obs_norm:
            remaps.append((c["type"], c["canonical"].get("name") or c["canonical"].get("subject"),
                           "obs_category", "枚举归一"))
        # vol 归一（2026-09-20 ch0138 首例：137/137 条 vol=0 → 规范口径恒 1；确定性零裁量）
        vol_fixed = sum(1 for ev in c["evidence"] if ev.get("vol") != 1)
        if vol_fixed:
            for ev in c["evidence"]:
                ev["vol"] = 1
            remaps.append((c["type"], c["canonical"].get("name") or c["canonical"].get("subject"),
                           "vol", f"1（{vol_fixed}条）"))
        rec = {
            "record_id": core_id(c["type"], canonical, c["evidence"]),
            "record_type": c["type"], "library": lib, "status": "candidate",
            "canonical": canonical, "observations": c.get("observations", []),
            "evidence": c["evidence"], "verified_against": verified,
            "provenance": {"extractor_confidence": c["confidence"],
                           "extractor": "glm-zcode-agent-v1（工单v1.2§0亲抽路线）",
                           "gate_trace": [], "precedent_refs": [], "status_history": []},
            "version": 1, "supersedes": None,
        }
        if c["type"] in ("event", "foreshadow") and c.get("entities_involved"):
            rec["canonical"]["entities"] = sorted(set(c["entities_involved"]))
        cbb_contracts.validate_record(rec, allow_candidate=True)
        out.append(rec)
    if remaps:
        print(json.dumps({"library_normalized": [list(r) for r in remaps]}, ensure_ascii=False))
    return out


def run(chapter_no: int, no_aux: bool = False) -> dict:
    ch = boundary(chapter_no)
    unit = f"ch{chapter_no:04d}"
    ext_src = WORK / "candidates" / f"extraction-{unit}.json"
    raw = json.loads(ext_src.read_text(encoding="utf-8"))
    va_src = raw["_meta"]["source"]
    verified = {"path": va_src["path"], "sha": va_src["sha"], "verified_at": va_src["verified_at"]}

    manifest_path = WORK / "manifest" / f"manifest-{unit}.json"
    if not manifest_path.exists():
        man = cbb_coordinate.coordinate(slice_text(ch), vol=1)
        man["source"] = {"name": va_src["path"], "sha": va_src["sha"],
                         "slice": f"行{ch['marker_line']}-{ch['line_end']}（CHAPTER {chapter_no:04d}）"}
        manifest_path.write_text(json.dumps(man, ensure_ascii=False, sort_keys=True, indent=1), encoding="utf-8")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    cands = normalize(raw, verified)
    result = cbb_gate1.check_batch(cands, ctx={"blocks": manifest["blocks"],
                                               "current_chapter": chapter_no})
    (WORK / "gate1" / f"gate1-{unit}.json").write_text(json.dumps(
        {"unit": unit, "summary": result["summary"],
         "intercepted": [{"record_id": it["check"]["record_id"],
                          "violations": it["check"]["violations"]} for it in result["intercepted"]]},
        ensure_ascii=False, indent=1), encoding="utf-8")

    # U-C03.6：账本哈希链包装（_append 汇聚点自动入账，行为等价——test_ledger_chain 绿）
    sys.path.insert(0, str(CBB / "tools"))
    import ledger_chain as _lc
    store = _lc.LedgedStore(STORE_ROOT)
    admits, quarantined = [], []
    for chk in result["passed"]:
        rec = next(r for r in cands if r["record_id"] == chk["record_id"])
        conf = rec["provenance"]["extractor_confidence"]
        if conf >= TAU:
            r = store.admit_or_merge(rec)
            admits.append({"record_id": rec["record_id"], "type": rec["record_type"],
                           "name": rec["canonical"].get("name") or rec["canonical"].get("subject"),
                           "track": r["track"],
                           "detail": {k: v for k, v in r.items() if k in ("new_id", "quarantine_item", "repeated")}})
        else:
            iid, _ = store.admit(rec, "quarantine", quarantine_group="low_confidence",
                                 quarantine_detail=f"置信度路由：{conf}<{TAU}")
            quarantined.append({"record_id": rec["record_id"], "type": rec["record_type"],
                                "name": rec["canonical"].get("name") or rec["canonical"].get("subject"),
                                "item_id": iid, "reason": "confidence_route"})
    for it in result["intercepted"]:
        rec = next(r for r in cands if r["record_id"] == it["check"]["record_id"])
        sub = it["check"]["quarantine_subclass"] or "extrapolation_unverified"
        codes = ";".join(v["code"] for v in it["check"]["violations"])
        iid, _ = store.admit(rec, "quarantine", quarantine_group=SUBCLASS_GROUP.get(sub, "low_confidence"),
                             quarantine_detail=f"门1拦截[{codes}] {it['check']['violations'][0]['detail'][:80]}")
        quarantined.append({"record_id": rec["record_id"], "type": rec["record_type"],
                            "name": rec["canonical"].get("name") or rec["canonical"].get("subject"),
                            "item_id": iid, "reason": f"gate1:{codes}"})

    for idx, c in enumerate(raw["candidates"]):
        for alias in c.get("aliases_to_register", []):
            # 结构化别名防御（2026-09-19 ch0121 勘误：子代理交 dict{name,kind,confidence}→取 name 串）
            if isinstance(alias, dict):
                alias = alias.get("name") or alias.get("alias")
                if not isinstance(alias, str):
                    continue
            # 2026-09-20 ch0132 勘误：别名登记按序号直取候选自身规范化记录（normalize 与 raw 严格 1:1 同序），
            # 替代旧名+硬编码 entity 匹配——setting 类候选带别名（ch0132『Impulse』）旧法 StopIteration；
            # entity_type 缺省回退 library（entity 候选行为不变）。
            ent = cands[idx]
            store.register_alias(alias, ent["record_id"],
                                 c["canonical"].get("entity_type") or c["library"])
        if c["type"] == "entity":
            store.record_appearance(c["canonical"]["name"], chapter_no)

    anchor_rec = cbb_anchor.make_anchor_record(chapter_no, ch["ingestion_index"], vol=1,
                                               verified_against=verified)
    chk_a = cbb_gate1.check_record(anchor_rec, ctx={"blocks": None, "current_chapter": chapter_no})
    anchor_admit = store.admit_or_merge(anchor_rec) if chk_a["verdict"] == "pass" else None

    (WORK / "candidates" / f"cands-{unit}.json").write_text(
        json.dumps({"candidates": cands, "meta": raw["_meta"]}, ensure_ascii=False, sort_keys=True, indent=1),
        encoding="utf-8")

    aux = {"embedding": None, "neo4j": None, "lightrag": None, "graphiti": None}
    if not no_aux:
        # 嵌入扫描（探活降级：blocked 不阻塞）
        r = subprocess.run([sys.executable, "-X", "utf8", str(CBB / "tools" / "embed_dedup_scan.py"),
                            "--cands", str(WORK / "candidates" / f"cands-{unit}.json"),
                            "--store", str(STORE_ROOT),
                            "--out", str(WORK / "embedding" / f"scan-{unit}.json")],
                           capture_output=True, text=True, timeout=600)
        try:
            aux["embedding"] = json.loads(r.stdout.strip().splitlines()[-1])
        except Exception:
            aux["embedding"] = {"status": "error", "stderr": r.stderr[-200:]}
        # Neo4j 增量导出（探活降级：blocked 不阻塞）
        r2 = subprocess.run([sys.executable, "-X", "utf8", str(CBB / "tools" / "neo4j_export.py"),
                             "--store", str(STORE_ROOT),
                             "--out", str(WORK / "logs" / f"neo4j-export-{unit}.json")],
                            capture_output=True, text=True, timeout=600)
        try:
            aux["neo4j"] = json.loads(r2.stdout.strip().splitlines()[-1])
        except Exception:
            aux["neo4j"] = {"status": "error", "stderr": r2.stderr[-200:]}
        # LightRAG 副本增量同步（探活降级：blocked 不阻塞；2026-09-25 并轨新增——
        # delta 由 sidecar 记账判定，无新增=零嵌入调用；副作用仅派生副本，正典库只读）
        try:
            r3 = subprocess.run([sys.executable, "-X", "utf8", str(CBB / "tools" / "lightrag_delta_sync.py"),
                                 "--store", str(STORE_ROOT), "--work", str(WORK / "索引" / "lightrag-exp")],
                                capture_output=True, text=True, encoding="utf-8", timeout=900)
            aux["lightrag"] = (json.loads(r3.stdout.strip().splitlines()[-1])
                               if r3.stdout.strip() else {"status": "blocked"})
        except Exception as e:
            aux["lightrag"] = {"status": "error", "stderr": str(e)[-200:]}
        # Graphiti 双时序抽取（对样 19✓/1✗ 过门后铺开；探活降级不阻塞；
        # 抽取自管=DeepSeek 裸调用，存储=fact_triple 模式，只写 7693 隔离实例）
        try:
            r4 = subprocess.run([sys.executable, "-X", "utf8", str(CBB / "tools" / "graphiti_ingest.py"),
                                 "--chapter", str(chapter_no), "--group", f"ch{chapter_no:04d}-gt"],
                                capture_output=True, text=True, encoding="utf-8", timeout=1500)
            aux["graphiti"] = (json.loads(r4.stdout.strip().splitlines()[-1])
                               if r4.stdout.strip() else {"status": "blocked"})
        except Exception as e:
            aux["graphiti"] = {"status": "error", "stderr": str(e)[-200:]}

    summary = {"unit": unit, "chapter": chapter_no,
               "ingestion_index": ch["ingestion_index"], "title": ch["title"],
               "noise": ch["noise"], "dup_of": ch.get("dup_of"),
               "counts": {"authored": len(cands), "pass": result["summary"]["pass"],
                          "intercept": result["summary"]["intercept"],
                          "admitted": len(admits), "quarantined": len(quarantined)},
               "tracks": {t: sum(1 for a in admits if a["track"] == t) for t in {a["track"] for a in admits}},
               "admitted": admits, "quarantined": quarantined,
               "anchor": {"tick": ch["ingestion_index"],
                          "pseudo_date": anchor_rec["canonical"]["pseudo_date"],
                          "track": (anchor_admit or {}).get("track", "intercepted")},
               "aux": aux, "lightrag_live": live_state}
    (WORK / "logs" / f"{unit}-pipeline-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"unit": unit, "counts": summary["counts"], "tracks": summary["tracks"],
                      "anchor_tick": ch["ingestion_index"],
                      "aux": {k: (v or {}).get("status", "?") for k, v in aux.items()},
                      "lightrag_live": live_state},
                     ensure_ascii=False))
    return summary


def _verify_gate(when: str) -> None:
    """BUG-0 门（02-bugs）：磁盘 sha 与账本对账。上一轮留下的旁路直写会在
    「跑前」拦截；本轮内部的旁路写入会在「跑后」拦截——不再静默累积。"""
    sys.path.insert(0, str(CBB / "tools"))
    import ledger_chain as _lc
    v = _lc.LedgedStore(STORE_ROOT).ledger.verify(STORE_ROOT)
    if not v.get("ok"):
        raise SystemExit(f"run_chapter {when} verify 未过（账本外改动，先处置再产数据）：{v.get('errors')}")


def _ensure_live_sentinel() -> str:
    """自唤起 LightRAG 实时同步哨（单例）：心跳 120s 内=在岗不重复拉起；陈旧/缺席=拉起新哨。
    DETACHED 分离进程——不随 runner 退出而死；哨日志=logs/lightrag-live.log。"""
    import time as _t
    work_lt = WORK / "索引" / "lightrag-exp"
    hb = work_lt / "_live-heartbeat"
    if hb.exists():
        try:
            if _t.time() - hb.stat().st_mtime < 120:
                return "already-running"
        except OSError:
            pass
    work_lt.mkdir(parents=True, exist_ok=True)
    pidf = work_lt / "_live.pid"
    if pidf.exists():
        try:
            pidf.unlink()  # 心跳已陈旧=旧哨已死，清 pid 位
        except OSError:
            pass
    logf = open(WORK / "logs" / "lightrag-live.log", "ab")
    flags = 0
    for f_name in ("DETACHED_PROCESS", "CREATE_NEW_PROCESS_GROUP"):
        flags |= getattr(subprocess, f_name, 0)
    subprocess.Popen([sys.executable, "-X", "utf8", str(CBB / "tools" / "lightrag_live.py"),
                      "--store", str(STORE_ROOT), "--work", str(work_lt), "--interval", "10"],
                     stdout=logf, stderr=logf, creationflags=flags, close_fds=True)
    _t.sleep(1.5)  # 给哨起心跳
    return "spawned"


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--chapter", type=int, required=True)
    ap.add_argument("--no-aux", action="store_true")
    args = ap.parse_args()
    _verify_gate("前置")
    try:
        live_state = _ensure_live_sentinel()  # 自唤起实时哨（失败不阻塞主链）
    except Exception as e:
        live_state = f"error: {str(e)[:80]}"
    run(args.chapter, no_aux=args.no_aux)
    _verify_gate("后置")
    return 0


if __name__ == "__main__":
    sys.exit(main())
