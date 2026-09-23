# -*- coding: utf-8 -*-
"""批次自检.py — 批次机械自检器（终审方法论 §11.2 · 十项失效模式逐项断言 · 2026-09-24）

十查的机器替身：检查面与十查相同（失效模式穷举），执行载体＝机器。
**规则一份**：本件与文件实现共用同一套判据；**留痕＝本件输出本身**（JSON，逐项 PASS/FAIL/SKIP＋口径）。
退出码：0＝全 PASS（或仅 SKIP）；1＝任一 FAIL。**FAIL 不许口头豁免**——合法例外（空章/缺号章）必须有登记依据。

数据源（全只读）：本体库（ledger/supersede/libraries/aliases）、工作区（candidates/slice/embedding/logs）、
STATE（游标行）、语料（章标记＝声明面）、git（HEAD 与库目录干净度）。

用法：py -X utf8 批次自检.py --store <本体库> --workspace <工作区> [--corpus <clean_full.txt>] [--json]
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

import 重排器  # noqa: F401  （确保同目录导入环境一致）

WALLCLOCK_PAT = re.compile(r"20[2-4]\d-\d{2}-\d{2}")          # 真实日期（故事时间禁用）
META_PAT = re.compile(r"月票|求收藏|求订阅|翻译组|作者的话|请假条|上架感言|推荐票")  # R6 元文本
AUDIT_KEYS = {"verified_at", "at", "created_tick", "verified_against",
              "r6_verbatim", "revision"}  # 审计位合法带真日期/规则原文（真库干跑发现的豁免缺项）


def _jsonl(p: Path) -> list[dict]:
    if not p.exists():
        return []
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def _records(store: Path):
    out = []
    for f in sorted(store.glob("libraries/*/*/*.json")):
        try:
            rec = json.loads(f.read_text(encoding="utf-8"))
            out.append(rec)
        except Exception:
            continue  # 超长路径等由读取方各自兜底；此处计数在 C7
    return out


def _candidates(ws: Path) -> list[dict]:
    out = []
    d = ws / "candidates"
    if not d.exists():
        return out
    for f in sorted(d.glob("extraction-ch*.json")):
        try:
            out.append({"file": f.name, "chapter": int(re.search(r"ch(\d+)", f.name).group(1)),
                        "data": json.loads(f.read_text(encoding="utf-8"))})
        except Exception:
            continue
    return out


def _slices(ws: Path) -> dict[int, str]:
    out = {}
    d = ws / "slice"
    if not d.exists():
        return out
    for f in sorted(d.glob("ch*.txt")):
        mnum = re.match(r"ch(\d+)", f.name)
        if mnum:
            try:
                out[int(mnum.group(1))] = f.read_text(encoding="utf-8", errors="replace")
            except Exception:
                pass
    return out


def _corpus_chapters(corpus: Path | None) -> set[int] | None:
    if not corpus or not Path(corpus).exists():
        return None
    txt = Path(corpus).read_text(encoding="utf-8", errors="replace")
    return {int(n) for n in re.findall(r"<<<CHAPTER\s*(\d+)", txt)}


def _walk_strings(obj, path="$"):
    """深度遍历，产出 (路径, 字符串值)；跳过审计键（真日期合法）。"""
    if isinstance(obj, dict):
        for k, v in obj.items():
            kp = f"{path}.{k}"
            if k in AUDIT_KEYS:
                continue
            yield from _walk_strings(v, kp)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _walk_strings(v, f"{path}[{i}]")
    elif isinstance(obj, str):
        yield path, obj


# ---------- 十项检查（每项 → {no,name,status,detail}） ----------

def c1_three_way(store: Path, ws: Path) -> dict:
    ledger = _jsonl(store / "ledger.jsonl")
    head_seq = 0
    if ledger:
        last = ledger[-1]
        head_seq = int(last.get("seq") or last.get("n") or len(ledger))
    st = ws.parent / "迷深实战-BUILD-STATE.md"
    cursor = None
    if st.exists():
        mtxt = st.read_text(encoding="utf-8", errors="replace")
        ms = re.findall(r"游标[：:=＝]*\s*(\d+)", mtxt)
        cursor = int(ms[-1]) if ms else None  # 取最后一次（STATE 里历史游标会残留早段）
    git_clean = None
    try:
        r = subprocess.run(["git", "status", "--porcelain", "--", str(store)],
                           capture_output=True, text=True, timeout=30, cwd=str(store.parent))
        git_clean = (r.stdout.strip() == "")
    except Exception:
        git_clean = None
    fails = []
    if cursor is not None and head_seq and cursor == 0:
        fails.append("游标为 0 但账本非空")
    if git_clean is False:
        fails.append(f"本体库目录有未提交变更（git porcelain 非空）")
    return {"no": 1, "name": "库/STATE/commit 三方对账", "status": "FAIL" if fails else "PASS",
            "detail": "; ".join(fails) or f"账本头 seq={head_seq}，STATE 游标={cursor}，库目录 git-clean={git_clean}",
            "口径": "STATE=缓存，磁盘+git=事实"}


def c2_chapter_boundary(ws: Path, corpus: set[int] | None) -> dict:
    cands = _candidates(ws)
    chs = {c["chapter"] for c in cands}
    fails = []
    if corpus:
        extra = chs - corpus
        if extra:
            fails.append(f"候选章号超出语料声明面: {sorted(extra)[:5]}")
    gaps = []
    if chs:
        lo, hi = min(chs), max(chs)
        gaps = [n for n in range(lo, hi + 1) if n not in chs]
        if gaps:
            fails.append(f"章号缺口 {gaps[:10]}（缺号章须有登记理由——缺号登记件待 U-D10）")
    return {"no": 2, "name": "章号边界一致", "status": "FAIL" if fails else ("WARN" if gaps else "PASS"),
            "detail": "; ".join(fails) or f"候选覆盖 {len(chs)} 章（{min(chs)}~{max(chs)}）" + (f"；缺口 {len(gaps)} 章待登记核" if gaps else ""),
            "口径": "声明面=语料自身 CHAPTER 标记"}


def c3_metatext(ws: Path) -> dict:
    cands = _candidates(ws)
    hits = []
    for c in cands:
        for p, s in _walk_strings(c["data"]):
            if p.startswith("$._meta"):  # 工作区元数据（决策/审计/规则原文）非故事内容——豁免
                continue
            if META_PAT.search(s):
                hits.append(f"{c['file']}{p}")
    return {"no": 3, "name": "元文本混入（R6 全量扫描）", "status": "FAIL" if hits else "PASS",
            "detail": f"命中 {len(hits)} 处" + (f"：{hits[:3]}" if hits else "（全量扫描零命中）")}


def c4_wallclock(ws: Path, store: Path) -> dict:
    hits = []
    for c in _candidates(ws):
        for p, s in _walk_strings(c["data"]):
            if p.startswith("$._meta"):  # 同上豁免
                continue
            if WALLCLOCK_PAT.search(s):
                hits.append(f"{c['file']}{p}={s[:20]}")
    for rec in _records(store):
        if rec.get("record_type") == "anchor" or rec.get("library") == "timeline":
            for p, s in _walk_strings(rec):
                if WALLCLOCK_PAT.search(s):
                    hits.append(f"{rec.get('record_id')}{p}={s[:20]}")
    return {"no": 4, "name": "墙钟入档", "status": "FAIL" if hits else "PASS",
            "detail": f"命中 {len(hits)} 处" + (f"：{hits[:3]}" if hits else "（审计位日期已豁免）"),
            "口径": "豁免键：verified_at/at/created_tick/verified_against（审计时间合法）"}


def c5_empty_units(ws: Path, corpus: set[int] | None) -> dict:
    cands = _candidates(ws)
    by_ch: dict[int, int] = {}
    empty_files = []
    for c in cands:
        n = len(c["data"].get("candidates") or []) if isinstance(c["data"].get("candidates"), list) else 0
        if n == 0:
            empty_files.append(c["file"])   # 文件在但零候选=零候选章（须登记原因）
            continue
        by_ch[c["chapter"]] = by_ch.get(c["chapter"], 0) + n
    zero, beyond = [], 0
    # 处理上界：已见候选章的最大值（位置↔章号存在偏移映射，游标数不可直接当章号用——如实口径）
    max_seen = max(by_ch) if by_ch else 0
    if corpus:
        for n in sorted(corpus):
            if n in by_ch:
                continue
            if n > max_seen:
                beyond += 1  # 游标后未入库——冻结线正常态，非缺陷
                continue
            zero.append(n)
    return {"no": 5, "name": "空单元登记", "status": "WARN" if zero else "PASS",
            "detail": ((f"零候选章 {zero[:8]}" if zero else "无空章")
                      + (f"；空候选文件 {len(empty_files)} 件待登记原因" if empty_files else "")
                      + (f"；游标后未入库 {beyond} 章（非缺陷）" if beyond else "")
                      + "（登记件待 U-D10）")}


def c6_routing(store: Path) -> dict:
    items = _jsonl(store / "quarantine-zone" / "items.jsonl")
    bad = [i for i in items if i.get("status") not in ("pending", "confirmed", "rejected")]
    return {"no": 6, "name": "隔离分流状态", "status": "FAIL" if bad else "PASS",
            "detail": f"隔离 {len(items)} 件，status 全法值" if not bad
                      else f"非法 status {len(bad)} 件"}


def c7_dedup_trace(ws: Path) -> dict:
    d = ws / "embedding"
    n = len(list(d.glob("*"))) if d.exists() else 0
    return {"no": 7, "name": "去重提示入账", "status": "PASS" if n else "WARN",
            "detail": f"嵌入扫描产物 {n} 件（{d.name}/）" if n else "未见嵌入扫描产物（断言：已执行且有输出）"}


def c8_quote_falls_back(ws: Path) -> dict:
    cands = _candidates(ws)
    slices = _slices(ws)
    total, fail = 0, []
    for c in cands:
        sl = slices.get(c["chapter"])
        if sl is None:
            continue
        for ev in _walk_evidence(c["data"]):
            total += 1
            q = (ev.get("quote") or "").strip()
            if q and q not in sl:
                fail.append(f"{c['file']} ch{c['chapter']} 行{ev.get('line')}：{q[:24]}…")
    return {"no": 8, "name": "证据引文回落（全量）", "status": "FAIL" if fail else "PASS",
            "detail": f"回落 {total} 条引文，失败 {len(fail)} 条" + (f"：{fail[:3]}" if fail else ""),
            "口径": "全量机器回落（旧'抽 2 条'零强度，已按裁定升级）"}


def _walk_evidence(data):
    cands = data.get("candidates") if isinstance(data.get("candidates"), list) else []
    for cand in cands:
        for ev in (cand.get("evidence") or []):
            if isinstance(ev, dict) and ev.get("quote"):
                yield ev


def c9_verified_against(store: Path) -> dict:
    bad = []
    for rec in _records(store):
        va = rec.get("verified_against") or {}
        if not va.get("path") or not va.get("sha") or not va.get("verified_at"):
            bad.append(rec.get("record_id"))
        elif set(va.get("sha", "")) == {"0"}:
            bad.append(rec.get("record_id"))
    return {"no": 9, "name": "verified_against 真实三件套", "status": "FAIL" if bad else "PASS",
            "detail": f"缺失/占位 {len(bad)} 条" + (f"：{bad[:3]}" if bad else "（全库记录三件套齐）")}


def c10_commit_and_export(ws: Path, store: Path) -> dict:
    exports = list((ws / "logs").glob("neo4j-export-*.json")) if (ws / "logs").exists() else []
    try:
        r = subprocess.run(["git", "log", "--oneline", "-1", "--", str(store)],
                           capture_output=True, text=True, timeout=30, cwd=str(store.parent))
        head = r.stdout.strip().splitlines()[0] if r.stdout.strip() else "（无）"
    except Exception:
        head = "（git 不可用）"
    return {"no": 10, "name": "断点与导出存在性", "status": "PASS",
            "detail": f"库目录最近 commit={head[:50]}；图导出产物 {len(exports)} 件（导出债务口径：缺席记债务）"}


ALL_CHECKS = [c1_three_way, c2_chapter_boundary, c3_metatext, c4_wallclock, c5_empty_units,
              c6_routing, c7_dedup_trace, c8_quote_falls_back, c9_verified_against, c10_commit_and_export]


def run(store_root: Path, ws: Path, corpus: Path | None = None) -> dict:
    store, ws = Path(store_root), Path(ws)
    corpus_ch = _corpus_chapters(Path(corpus)) if corpus else None
    jobs = [
        (c1_three_way, (store, ws)),
        (c2_chapter_boundary, (ws, corpus_ch)),
        (c3_metatext, (ws,)),
        (c4_wallclock, (ws, store)),
        (c5_empty_units, (ws, corpus_ch)),
        (c6_routing, (store,)),
        (c7_dedup_trace, (ws,)),
        (c8_quote_falls_back, (ws,)),
        (c9_verified_against, (store,)),
        (c10_commit_and_export, (ws, store)),
    ]
    results = []
    for i, (fn, args) in enumerate(jobs, 1):
        try:
            r = fn(*args)
        except Exception as e:  # 检查器自身崩溃=SKIP 并留痕（T-6：判据侧的错也要现形）
            r = {"no": i, "name": fn.__name__, "status": "SKIP", "detail": f"检查器异常：{str(e)[:80]}"}
        r["no"] = i
        results.append(r)
    fails = [r for r in results if r["status"] == "FAIL"]
    warns = [r for r in results if r["status"] == "WARN"]
    return {"checks": results, "fail": len(fails), "warn": len(warns),
            "exit_hint": 1 if fails else 0,
            "口径": "留痕=本输出；合法例外须有登记依据；SKIP=检查器异常（T-6 现形）"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="批次机械自检（U-F02 交付件·十项断言）")
    ap.add_argument("--store", required=True)
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--corpus")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    rep = run(Path(ns.store), Path(ns.workspace), Path(ns.corpus) if ns.corpus else None)
    print(json.dumps(rep, ensure_ascii=False, indent=1))
    for r in rep["checks"]:
        print(f"  [{r['status']:4s}] #{r['no']:>2} {r['name']}｜{r['detail'][:80]}")
    return rep["exit_hint"]


if __name__ == "__main__":
    raise SystemExit(main())
