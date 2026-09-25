# -*- coding: utf-8 -*-
"""矛盾对生成.py — U-C03.8 NLI 预筛准备件①③（工单 v1.9 §0；触发器 D=RED：矛盾积压>50）。

① pairs：从隔离区矛盾子类（contradiction_pending）导出 NLI 配对 JSONL——
   新候选 claim vs 既有记录 claim，含双方证据四元组。两族群：
   - dual_track_conflict：detail 形如 "字段: 入库='X' vs 库内='Y'"（双轨矛盾轨）；
     入库侧正文回收三层=当前 cands → git 历史 blob → 匿名重构（仅值对，evidence 置空+标记）；
     库内侧=身份键活版本。
   - embedding_notice：detail 含 "A vs B sim=…"（嵌入存疑提示件）；两侧=按名查库活版本。
   只读工具：不写库、不动隔离区（B6：预筛结果全留痕可回溯）。
③ exam：上岗小考考卷（确定性，无 RNG）——从已裁矛盾案件抽真对（预期 contradicts）+
   机械变异伪矛盾（entails_control 逐字重述→entails／entails_paraphrase 模板换词→entails／
   neutral_subject 换主体→neutral）。判定口径=操作语义（同主体同字段异值=contradicts，
   含粒度差异），非严格逻辑否定——已登记【待确认】呈报审核线。
   grade：判卷（镜像 W1 judge_exam 纪律）——分离度=真对标 contradicts 且伪对标非 contradicts
   的占比（lenient 口径，路由语义）；exact=三分全标签命中率（堵永远-neutral 退化器）；
   pass = separation≥0.70 且 exact≥0.70 且 parse_failure≤0.05。考不过→NLI 预筛不启用，
   积压继续人工消化。

用法：
  py -X utf8 矛盾对生成.py pairs  [--store <本项目>-本体库] [--out pairs.jsonl]
  py -X utf8 矛盾对生成.py exam   [--store …] [--names 名录.json] [--out-dir …]
  py -X utf8 矛盾对生成.py grade  --paper 考卷.jsonl --verdicts 判定.jsonl [--out 报告.json]
"""
import argparse
import json
import re
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent  # 正典库构建系统
sys.path.insert(0, str(HERE.parent / "contracts"))
sys.path.insert(0, str(HERE.parent / "cbb-store"))
import cbb_store  # noqa: E402

import 路径惯例 as 惯
_S = 惯.store_of(Path(os.environ.get("CBB_STORE") or ROOT))
DEFAULT_STORE = _S
DEFAULT_CANDS = 惯.workspace_of(_S) / "candidates"
DEFAULT_NLI_DIR = 惯.workspace_of(_S) / "评分" / "nli"

CONFLICT_RE = re.compile(r"^(\S+?): 入库='(.*)' vs 库内='(.*)'$")
SIM_RE = re.compile(r"([^：:]*?) vs ([^：:]*?) sim=\d")


# ---- 断言渲染（确定性；与 runners/judge_exam.assertion_of 同族，R-018 机械纪律） ----
def render_claim(rec: dict) -> str:
    rt = rec.get("record_type")
    c = rec.get("canonical") or {}
    if rt == "entity" and c.get("name"):
        return f"{c['name']}的实体类型为{c.get('entity_type')}"
    if rt == "relation":
        tag = "（声称）" if c.get("claim") else ""
        return f"{c.get('subject')}与{c.get('object')}的关系为「{c.get('rel_type')}」{tag}"
    ents = "、".join(c.get("entities") or [])
    return f"{rt}记录（涉事：{ents}）"


def evidence_quads(rec: dict) -> list[dict]:
    return [{"vol": e.get("vol"), "chapter": e.get("chapter"),
             "line": e.get("line"), "quote": e.get("quote")}
            for e in (rec.get("evidence") or [])]


# ---- 库内检索 ----
def live_by_name(store, name: str, record_type: str = "entity"):
    """按 canonical.name 取活版本（未被取代的最高版本；无活则最高版本）。"""
    matches = [r for r in store.iter_records()
               if r.get("record_type") == record_type
               and (r.get("canonical") or {}).get("name") == name]
    if not matches:
        return None
    superseded = {e["old_id"] for e in store._load_all("supersede-index.jsonl")}
    live = [m for m in matches if m["record_id"] not in superseded]
    pool = live or matches
    return max(pool, key=lambda m: m.get("version", 1))


# ---- 入库侧正文回收 ----
def index_current_cands(cands_dir: Path) -> dict:
    idx = {}
    if not cands_dir.exists():
        return idx
    for p in sorted(cands_dir.glob("cands-*.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        for rec in d.get("candidates", []):
            idx.setdefault(rec["record_id"], (rec, p.name))
    return idx


def index_git_blobs(repo_root: Path, cands_dir: Path) -> dict:
    """git 历史回收：修正循环会覆写 cands 文件，中间态只存在于历史 blob。
    任何 git 失败→空索引（层降级，不抛错）。"""
    idx = {}
    try:
        rel = cands_dir.resolve().relative_to(repo_root.resolve()).as_posix()
    except Exception:
        return idx
    try:
        out = subprocess.run(
            ["git", "-c", "core.quotepath=off", "log", "--format=%H", "--name-only",
             "--", rel + "/"],
            cwd=repo_root, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=120).stdout
    except Exception:
        return idx
    commits_by_file, commit = {}, None
    for ln in out.splitlines():
        s = ln.strip()
        if not s:
            continue
        if len(s) == 40 and all(ch in "0123456789abcdef" for ch in s):
            commit = s
        elif s.startswith("cands-") and s.endswith(".json") and commit:
            commits_by_file.setdefault(s, set()).add(commit)
    for fname, commits in sorted(commits_by_file.items()):
        for c in sorted(commits):
            try:
                r = subprocess.run(
                    ["git", "-c", "core.quotepath=off", "show", f"{c}:{rel}/{fname}"],
                    cwd=repo_root, capture_output=True, text=True, encoding="utf-8",
                    errors="replace", timeout=120)
                d = json.loads(r.stdout)
            except Exception:
                continue
            for rec in d.get("candidates", []):
                idx.setdefault(rec["record_id"], (rec, f"{fname}@{c[:8]}"))
    return idx


# ---- 配对主逻辑 ----
def build_pairs(store, cands_idx: dict, repo_root: Path | None = None) -> tuple[list[dict], dict]:
    items = store.zone.pending()  # 生效 pending=不在 adjudications 对账内（append-only，status 字段不回写）
    pairs, stats = [], {"dual_track": 0, "embedding": 0, "unparsed": 0,
                        "recovery_full": 0, "recovery_partial": 0,
                        "name_miss": 0}
    for it in items:
        if it.get("subclass") != "contradiction_pending":
            continue
        detail = it.get("detail") or ""
        segs = [s.strip() for s in detail.split("；") if s.strip()]
        conf = next((s for s in segs if CONFLICT_RE.match(s)), None)
        sim_seg = next((s for s in segs if "sim=" in s), None)
        if conf:
            m = CONFLICT_RE.match(conf)
            field, val_in, val_stored = m.group(1), m.group(2), m.group(3)
            body, src = cands_idx.get(it["record_id"], (None, None))
            if body is not None:
                existing = store.find_by_identity(body)
                if existing is None:
                    stats["dual_track"] += 1
                    stats["recovery_partial"] += 1
                    pairs.append(_pair(it, "dual_track_conflict",
                                       _side(body, "incoming", src),
                                       None, [field], "partial_existing_miss"))
                    continue
                stats["dual_track"] += 1
                stats["recovery_full"] += 1
                pairs.append(_pair(it, "dual_track_conflict",
                                   _side(body, "incoming", src),
                                   _side(existing, "existing", "store-live"),
                                   [field], "full"))
            else:
                # 匿名重构：值对来自 detail（裁决留痕在案），主体匿名令牌，evidence 空
                subject = f"案件主体{it['item_id'][2:10]}"
                stats["dual_track"] += 1
                stats["recovery_partial"] += 1
                pairs.append(_pair(it, "dual_track_conflict",
                                   {"role": "incoming", "claim": f"{subject}的{field}为{val_in}",
                                    "entity": subject, "record_id": it["record_id"],
                                    "evidence": [], "recovery": "reconstructed_from_detail"},
                                   {"role": "existing", "claim": f"{subject}的{field}为{val_stored}",
                                    "entity": subject, "record_id": None,
                                    "evidence": [], "recovery": "reconstructed_from_detail"},
                                   [field], "reconstructed"))
        elif sim_seg:
            m = SIM_RE.search(sim_seg)
            if not m:
                stats["unparsed"] += 1
                continue
            n1, n2 = m.group(1).strip(), m.group(2).strip()
            r1, r2 = live_by_name(store, n1), live_by_name(store, n2)
            # detail 惯例 "新 vs 库内"：n1=新候选（假设侧 hypothesis），n2=库内（前提侧 premise）
            if r1 is None or r2 is None:
                stats["embedding"] += 1
                stats["name_miss"] += 1
                pairs.append(_pair(it, "embedding_notice",
                                   _side(r1, "hypothesis_new", "store-live") if r1 else
                                   {"role": "hypothesis_new", "claim": None, "entity": n1,
                                    "record_id": None, "evidence": [], "recovery": "name_miss"},
                                   _side(r2, "premise_existing", "store-live") if r2 else
                                   {"role": "premise_existing", "claim": None, "entity": n2,
                                    "record_id": None, "evidence": [], "recovery": "name_miss"},
                                   ["embedding_similarity"], "name_miss"))
                continue
            stats["embedding"] += 1
            stats["recovery_full"] += 1
            pairs.append(_pair(it, "embedding_notice", _side(r1, "hypothesis_new", "store-live"),
                               _side(r2, "premise_existing", "store-live"),
                               ["embedding_similarity"], "full"))
        else:
            stats["unparsed"] += 1
    return pairs, stats


def _side(rec: dict, role: str, src: str) -> dict:
    return {"role": role, "claim": render_claim(rec),
            "entity": (rec.get("canonical") or {}).get("name"),
            "record_id": rec.get("record_id"),
            "evidence": evidence_quads(rec), "recovery": src}


def _pair(item: dict, family: str, incoming: dict, existing: dict | None,
          fields: list, recovery: str) -> dict:
    return {"pair_id": f"pair-{item['item_id']}", "family": family,
            "quarantine_item_id": item["item_id"],
            "quarantine_detail": item.get("detail"),
            "premise": existing, "hypothesis": incoming,
            "conflict_fields": fields, "recovery": recovery}


# ---- 考卷 ----
def build_exam(store, names_path: Path | None, min_real: int = 10) -> dict:
    """真对=已裁矛盾案件（item 出现在 adjudications）；名录=裁决备注中实体名的人工核定映射
    （数据件，机械工具不做裁量）。无名者用确定性匿名令牌（披露于报告）。"""
    zone_items = [json.loads(l) for l in
                  (store.root / "quarantine-zone" / "items.jsonl")
                  .read_text(encoding="utf-8").splitlines() if l.strip()]
    adj = {json.loads(l)["item_id"]: json.loads(l) for l in
           (store.root / "quarantine-zone" / "adjudications.jsonl")
           .read_text(encoding="utf-8").splitlines() if l.strip()}
    names = json.loads(names_path.read_text(encoding="utf-8")) if names_path and names_path.exists() else {}

    bases = []
    for it in zone_items:
        if it.get("subclass") != "contradiction_pending" or it["item_id"] not in adj:
            continue
        m = CONFLICT_RE.match((it.get("detail") or "").split("；")[0].strip())
        if not m:
            continue
        field, val_in, val_stored = m.group(1), m.group(2), m.group(3)
        subject = names.get(it["item_id"]) or f"案件主体{it['item_id'][2:10]}"
        bases.append({"item_id": it["item_id"], "subject": subject, "field": field,
                      "val_incoming": val_in, "val_stored": val_stored,
                      "named": it["item_id"] in names,
                      "adjudication": adj[it["item_id"]]})
    bases.sort(key=lambda b: b["item_id"])

    subjects = sorted({b["subject"] for b in bases} | {"无关参照实体"})
    rows = []
    for b in bases:
        p = f"{b['subject']}的{b['field']}为{b['val_stored']}"
        h = f"{b['subject']}的{b['field']}为{b['val_incoming']}"
        rows.append({"pair_id": f"exam-{b['item_id']}-base", "kind": "base",
                     "expected": "contradicts", "premise": p, "hypothesis": h,
                     "evidence": []})
        rows.append({"pair_id": f"exam-{b['item_id']}-control", "kind": "entails_control",
                     "expected": "entails", "premise": p, "hypothesis": p,
                     "evidence": []})
        rows.append({"pair_id": f"exam-{b['item_id']}-paraphrase", "kind": "entails_paraphrase",
                     "expected": "entails", "premise": p,
                     "hypothesis": f"{b['subject']}属于{b['val_stored']}",
                     "evidence": []})
        i = (subjects.index(b["subject"]) + 1) % len(subjects)
        other = subjects[i] if subjects[i] != b["subject"] else "无关参照实体"
        rows.append({"pair_id": f"exam-{b['item_id']}-neutral", "kind": "neutral_subject",
                     "expected": "neutral", "premise": p,
                     "hypothesis": f"{other}的{b['field']}为{b['val_incoming']}",
                     "evidence": []})
    return {"bases": bases, "rows": rows, "n_real": len(bases),
            "meets_minimum": len(bases) >= min_real,
            "named_subjects": sum(1 for b in bases if b["named"]),
            "semantics": "operational（同主体同字段异值=contradicts，含粒度差异；"
                         "非严格逻辑否定——已登记【待确认】呈报审核线）"}


# ---- 判卷 ----
LABELS = ("entails", "neutral", "contradicts")


def grade(paper_rows: list[dict], verdict_rows: list[dict]) -> dict:
    by_pid = {}
    parse_fail = []
    for v in verdict_rows:
        pid, label = v.get("pair_id"), str(v.get("label", "")).strip().lower()
        if pid in by_pid:
            parse_fail.append({"pair_id": pid, "why": "duplicate"})
            continue
        if label not in LABELS:
            parse_fail.append({"pair_id": pid, "why": f"bad_label:{label[:20]}"})
            continue
        by_pid[pid] = label
    missing = [r["pair_id"] for r in paper_rows if r["pair_id"] not in by_pid]

    sep_hits, exact_hits, by_kind = 0, 0, {}
    for r in paper_rows:
        got = by_pid.get(r["pair_id"])
        kind = r["kind"]
        d = by_kind.setdefault(kind, {"n": 0, "lenient": 0, "exact": 0})
        d["n"] += 1
        if got is None:
            continue
        ok_lenient = (got == "contradicts") if r["expected"] == "contradicts" \
            else (got != "contradicts")
        if ok_lenient:
            sep_hits += 1
            d["lenient"] += 1
        if got == r["expected"]:
            exact_hits += 1
            d["exact"] += 1
    total = len(paper_rows)
    n_judged = total - len(missing)
    separation = round(sep_hits / total, 4) if total else 0.0
    exact = round(exact_hits / total, 4) if total else 0.0
    parse_rate = round((len(parse_fail) + len(missing)) / max(1, total), 4)
    return {"separation": separation, "exact_match": exact,
            "parse_failure_rate": parse_rate, "n_paper": total, "n_judged": n_judged,
            "n_real_bases": sum(1 for r in paper_rows if r["kind"] == "base"),
            "pass": bool(total and separation >= 0.70 and exact >= 0.70
                         and parse_rate <= 0.05),
            "by_kind": {k: {"n": v["n"], "lenient": round(v["lenient"] / v["n"], 4),
                            "exact": round(v["exact"] / v["n"], 4)}
                        for k, v in sorted(by_kind.items())},
            "missing": missing, "parse_fail": parse_fail,
            "gate_definition": "separation（路由口径：真对=contradicts 且伪对=非contradicts）≥0.70 "
                               "且 exact_match（三分全标签）≥0.70（堵永远-neutral 退化器）"
                               "且 parse_failure≤0.05（W1 纪律）",
            "decision_rule": "pass→NLI 预筛可启用（contradicts→人工队列置顶/neutral→挂起第二意见/"
                             "entails→转双轨 confidence，全程留痕不静默）；fail→不启用，积压继续人工"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="U-C03.8 NLI 预筛准备件：矛盾对生成+考卷+判卷")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("pairs", help="导出矛盾配对 JSONL（生产预筛输入）")
    p1.add_argument("--store", default=str(DEFAULT_STORE))
    p1.add_argument("--cands", default=str(DEFAULT_CANDS))
    p1.add_argument("--out", default=str(DEFAULT_NLI_DIR / "nli-backlog-pairs.jsonl"))
    p1.add_argument("--no-git", action="store_true", help="跳过 git 历史回收层")

    p2 = sub.add_parser("exam", help="生成上岗小考考卷（确定性）")
    p2.add_argument("--store", default=str(DEFAULT_STORE))
    p2.add_argument("--names", default=str(DEFAULT_NLI_DIR / "exam-names.json"))
    p2.add_argument("--out-dir", default=str(DEFAULT_NLI_DIR))

    p3 = sub.add_parser("grade", help="判卷（分离度≥0.70 且 parse_failure≤0.05）")
    p3.add_argument("--paper", required=True)
    p3.add_argument("--verdicts", required=True)
    p3.add_argument("--out")

    args = ap.parse_args(argv)

    if args.cmd == "pairs":
        store = cbb_store.ThreeStateStore(Path(args.store))
        cands_dir = Path(args.cands)
        idx = index_current_cands(cands_dir)
        stats_pre = {"current_cands": len(idx)}
        if not args.no_git:
            git_idx = index_git_blobs(ROOT, cands_dir)
            for k, v in git_idx.items():
                idx.setdefault(k, v)
            stats_pre["plus_git_history"] = len(idx) - stats_pre["current_cands"]
        pairs, stats = build_pairs(store, idx)
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8") as f:
            for pr in pairs:
                f.write(json.dumps(pr, ensure_ascii=False, sort_keys=True) + "\n")
        report = {"recovery_index": stats_pre, "pair_stats": stats,
                  "n_pairs": len(pairs),
                  "dispatchable": sum(1 for p in pairs if p["premise"] and p["hypothesis"]
                                      and p["premise"].get("claim") and p["hypothesis"].get("claim")),
                  "out": str(out)}
        print(json.dumps(report, ensure_ascii=False, indent=1))
        return 0

    if args.cmd == "exam":
        store = cbb_store.ThreeStateStore(Path(args.store))
        paper = build_exam(store, Path(args.names))
        out_dir = Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        paper_path = out_dir / "nli-exam-paper.jsonl"
        with paper_path.open("w", encoding="utf-8") as f:
            for r in paper["rows"]:
                f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
        meta = {k: v for k, v in paper.items() if k != "rows"}
        (out_dir / "nli-exam-meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
        print(json.dumps({"paper": str(paper_path), "n_rows": len(paper["rows"]), **meta},
                         ensure_ascii=False, indent=1))
        return 0

    if args.cmd == "grade":
        paper_rows = [json.loads(l) for l in
                      Path(args.paper).read_text(encoding="utf-8").splitlines() if l.strip()]
        verdict_rows = [json.loads(l) for l in
                        Path(args.verdicts).read_text(encoding="utf-8").splitlines() if l.strip()]
        report = grade(paper_rows, verdict_rows)
        out = Path(args.out) if args.out else Path(args.verdicts).with_name(
            Path(args.verdicts).stem + "-report.json")
        out.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
        print(json.dumps({k: report[k] for k in
                          ("separation", "exact_match", "parse_failure_rate", "pass",
                           "n_paper", "n_judged", "by_kind")}, ensure_ascii=False, indent=1))
        return 0 if report["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
