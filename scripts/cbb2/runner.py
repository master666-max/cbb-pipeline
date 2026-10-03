"""cbb2.runner — 章管线编排（Phase C 总装）。

prepare_chapter：派工卡=动态切分判定+场景软标签+承接摘要+三层上下文包（旗标 off=整章+空包降级）。
finalize_chapter：候选批量 write_decision（身份缓存+at 伪锚点）→投影检查点推进→LightRAG 重喂判定。
抽取本体仍由宿主 Agent 按派工卡执行（判定权在人；runner 只编排与机械判定）。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from . import config, context, splitting
from .derive import ProjectionCheckpoint
from .ledger import LedgedStore, LedgerChain
from .store import identity_key


def prepare_chapter(chapter_no: int, prev_chapter_text: str = "",
                    chapter_text: str = "", blocks: list[dict] | None = None,
                    store: Path | None = None, new_entity_hint: int | None = None) -> dict:
    store = Path(store or config.store_of(Path(__file__).parents[2]))
    blocks = blocks or []
    tags = splitting.scene_tags(blocks) if blocks else {"scene_count": 1, "boundaries": [],
                                                        "dialogue_ratio": 0.0, "time_jumps": 0}
    if splitting.enabled():
        decision = splitting.split_decision(chapter_text or "", tags,
                                            new_entity_hint=new_entity_hint)
        segments = (splitting.segment_blocks(blocks, tags["boundaries"])
                    if decision["split"] and blocks else None)
    else:
        decision = {"split": False, "reasons": ["旗标 CBB_DYNAMIC_SPLIT=off"], "theta": splitting.theta()}
        segments = None
    carry = context.carry_summary(store, chapter_no - 1)
    pack = context.build_context_pack(store, chapter_no,
                                      prev_slice_tail=prev_chapter_text[-400:])
    return {"chapter": chapter_no, "动态切分": decision, "场景软标签": tags,
            "分段": segments, "承接摘要": carry, "上下文包": pack,
            "口径": "先验非事实源；抽取出候选后交 finalize_chapter"}


def nli_merge_gate_factory():
    """D2 NLI 合并前复核闸（改判5 第二道闸）：本地 LLM 通道可用时返回判定闭包，
    不可用返回 None（降级显式——finalize 结果口径标注 nli_merge_gate=False）。"""
    from . import nli
    ch = nli.LLMChannel()
    if not ch.available():
        return None
    def gate(incoming, existing):
        premise = json.dumps(existing.get("canonical") or {}, ensure_ascii=False, sort_keys=True)
        hypothesis = json.dumps(incoming.get("canonical") or {}, ensure_ascii=False, sort_keys=True)
        return ch.judge(premise=premise, hypothesis=hypothesis)
    return gate


def patrol_nli_check(store_root: Path, record: dict) -> dict:
    """D2 NLI 巡检闸（改判5 第三道闸）：G17 巡检重推导时的 NLI 复核。
    premise=记录全量引文，hypothesis=canonical——矛盾即改判候选（只出信号，裁决权在人工/票面）。"""
    from . import nli
    ch = nli.LLMChannel()
    if not ch.available():
        return {"channel": "unavailable", "verdict": None}
    premise = "；".join(e.get("quote", "") for e in (record.get("evidence") or []))
    hypothesis = json.dumps(record.get("canonical") or {}, ensure_ascii=False, sort_keys=True)
    return {"channel": "llm", "verdict": ch.judge(premise=premise, hypothesis=hypothesis)}


def close_out_gap_queue(store_root: Path, current_chapter: int | None = None,
                        capture_report: dict | None = None,
                        dual_results: list[dict] | None = None) -> int:
    """区段收口：四扫描器→缺口队列（wire_gap_queue 幂等追加，同 type+evidence 不重复）。
    缺输入的扫描器按缺席跳过（plant 需 capture_report / NLI 需 dual_results）——显式缩员不臆测。"""
    from . import gaps
    from .governance import wire_gap_queue
    findings: list[dict] = []
    if current_chapter is not None:
        findings += gaps.scan_foreshadow_overdue(store_root, current_chapter)
    findings += gaps.scan_vocab_gaps(store_root)
    if capture_report is not None:
        findings += gaps.scan_plant_miss(store_root, capture_report)
    if dual_results is not None:
        findings += gaps.scan_nli_disagreement(store_root, dual_results)
    return wire_gap_queue(store_root, findings)


def finalize_chapter(store_root: Path, candidates: list[dict], at: str,
                     register_conflict: bool = True) -> dict:
    """批量 write_decision（身份缓存免全库扫描）→ lightrag 投影检查点推进。"""
    ls = LedgedStore(store_root)
    cache = {}
    inv = {e["record_id"] for e in ls._load_all("invalidations.jsonl")}
    for rec in ls.iter_records():
        if rec.get("record_id") in inv:
            continue
        k = identity_key(rec)
        cur = cache.get(k)
        if cur is None or rec.get("version", 1) > cur.get("version", 1):
            cache[k] = rec
    merge_gate = nli_merge_gate_factory()  # D2：合并前复核闸（通道缺席=None=降级显式）
    tracks: dict[str, int] = {}
    results = []
    for cand in candidates:
        k = identity_key(cand)
        r = ls.write_decision(cand, at=at, existing=cache.get(k),
                              register_conflict=register_conflict,
                              nli_merge_gate=merge_gate)
        tracks[r["track"]] = tracks.get(r["track"], 0) + 1
        if r.get("new_id"):
            fresh = ls._find(r["new_id"])
            if fresh:
                cache[k] = fresh
        results.append({"record_id": cand.get("record_id"), "track": r["track"],
                        "new_id": r.get("new_id") or r.get("event_id")})
    ledger = LedgerChain(Path(store_root) / "ledger.jsonl")
    rows = len(ledger._rows_fresh())
    cp = ProjectionCheckpoint(Path(store_root), "lightrag")
    cp.commit(ledger_offset=rows, sha=at, at=at)
    try:  # G15：区段收口顺带产出缺口队列——扫描失败不拖垮收口本体，-1 显式暴露降级
        m = re.fullmatch(r"ch(\d+)", at or "")
        gap_added = close_out_gap_queue(store_root,
                                        current_chapter=int(m.group(1)) if m else None)
    except Exception:  # noqa: BLE001 — 收口辅助面宽捕获=降级语义（设计决定）
        gap_added = -1
    return {"chapters_written_at": at, "tracks": tracks, "results": results,
            "checkpoint": rows, "gap_queue_added": gap_added,
            "nli_merge_gate": merge_gate is not None}


def refeed_needed(store_root: Path, view: str = "lightrag") -> bool:
    """账本自上次检查点以来有任何行 ⇒ 派生视图需重喂（整批重喂语义）。"""
    ledger = LedgerChain(Path(store_root) / "ledger.jsonl")
    rows = len(ledger._rows_fresh())
    return ProjectionCheckpoint(Path(store_root), view).replay_needed(rows)


def _aux_tool_dir() -> Path | None:
    """aux 工具目录按模块位置推导（2026-10-03 审计修正①：旧写法相对路径 "cbb/tools/…"
    +cwd=store.parent 在当前布局下必错——脚本从未被真正执行，崩溃被伪装成 blocked）。
    双布局兼容：包 scripts/cbb2→parents[1]；工作区 cbb-v2/cbb2→parents[2]。
    找不到返回 None（缺席经 FileNotFoundError 显式入披露，不伪装）。"""
    here = Path(__file__).resolve()
    for base in (here.parents[1], here.parents[2]):
        d = base / "cbb" / "tools"
        if (d / "embed_dedup_scan.py").exists():
            return d
    return None


def run_chapter(chapter_no: int, store: Path | None = None, no_aux: bool = False) -> dict:
    """v2 编排骨架（aux 四件探活降级；保留兼容 Phase A 前调用面）。
    aux 披露口径（2026-10-03 审计修正②）：工具有 stdout 披露行（含探活失败 rc=2 的
    blocked 协议）→ 解析其末行；rc!=0 且无 stdout（裸崩/用法错）→ status=error +
    returncode + stderr 尾部——不再伪装 blocked；rc=0 无产出 → blocked（旧降级语义）。"""
    store = store or config.store_of(Path(__file__).parents[2])
    aux = {"embedding": None, "graph": None, "replica": None, "temporal": None}
    if not no_aux:
        tool_dir = _aux_tool_dir()
        aux_steps = [
            ("embedding", "embed_dedup_scan.py"),
            ("graph", "neo4j_export.py"),
        ]
        for key, script in aux_steps:
            try:
                import subprocess
                cmd = ["py", "-X", "utf8",
                       str(tool_dir / script) if tool_dir else script]
                r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                                   timeout=600, cwd=str(store.parent), check=False)  # aux 降级语义
                out = (r.stdout or "").strip()
                if r.returncode != 0 and not out:
                    aux[key] = {"status": "error", "returncode": r.returncode,
                                "stderr": (r.stderr or "")[-200:]}
                elif out:
                    aux[key] = json.loads(out.splitlines()[-1])
                else:
                    aux[key] = {"status": "blocked"}
            except Exception as e:  # noqa: BLE001 — aux 探活降级：子进程异常族全捕获不阻塞主链
                aux[key] = {"status": "error", "stderr": str(e)[-200:]}
    return {"chapter": chapter_no, "aux": aux,
            "口径": "v2 骨架——长尾工具仍由 cbb/ 提供（D1 裁决：增量迁移）"}


if __name__ == "__main__":
    import sys
    raise SystemExit(run_chapter(int(sys.argv[1]) if len(sys.argv) > 1 else 0) and 0)
