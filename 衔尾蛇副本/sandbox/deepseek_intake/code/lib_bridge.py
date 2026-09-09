# -*- coding: utf-8 -*-
"""lib_bridge.py — 真实 bootstrap_v3 落盘桥: materialize / parity 门 / P5 真实抽查

库内容与写路径 100% 走真实 b3 代码(b3.cmd_engine append/retire/doctor)。
P0 parity: 参数化检索器 retrieve_top(默认 cfg) vs b3._rank_entries 的 top-5 集合一致率。
"""
import sys, os, json, time, shutil, io, contextlib, pathlib, re

HERE = pathlib.Path(__file__).resolve().parent
BASE = HERE.parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))
import bootstrap_v3 as b3
from world_gen import strip_hidden
from engine_gate import retrieve_top, V3_DEFAULT, K_TOPK


def materialize_lib(lib_dir, entries, extra_expired=None):
    """真实落盘: state.json + b3.cmd_engine append(真实分流/审计/账本/刷根)"""
    lib_dir = pathlib.Path(lib_dir)
    if lib_dir.exists():
        shutil.rmtree(lib_dir)
    lib_dir.mkdir(parents=True)
    (lib_dir / "evals").mkdir(exist_ok=True)
    (lib_dir / "state.json").write_text(json.dumps({
        "package": "bootstrap_v3.py", "version": b3.VERSION, "level": "SANDBOX",
        "emotion": {"valence": 0.0, "arousal": 0.5, "certainty": 0.5, "stakes": 0.0},
        "importance_accum": 0, "created_at": time.strftime("%F %T"),
        "merkle_root": ""}, ensure_ascii=False), encoding="utf-8")
    import io as _io, contextlib as _ctx
    t0 = time.time()
    n = 0
    _quiet = _io.StringIO()
    with _ctx.redirect_stdout(_quiet):
        for e in entries:
            vis = strip_hidden(e)
            if vis["validity"].get("t_invalid"):
                continue
            b3.cmd_engine("append", str(lib_dir), json.dumps(vis, ensure_ascii=False), K_TOPK)
            n += 1
    if extra_expired:
        for e in extra_expired:
            vis = strip_hidden(e)
            vis["validity"] = {"t_invalid": "2020-01-01 00:00:00"}
            vis["id"] = e["id"] + "_exp"
            b3.cmd_engine("append", str(lib_dir), json.dumps(vis, ensure_ascii=False), K_TOPK)
            n += 1
    return {"entries_written": n, "append_ms": round((time.time() - t0) * 1000, 1)}


def real_doctor(lib_dir):
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            b3.cmd_engine("doctor", str(lib_dir), "", K_TOPK)
    except SystemExit as ex:
        buf.write("(exit %s)" % str(ex))
    return buf.getvalue().strip()


def real_retire(lib_dir):
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            b3.cmd_engine("retire", str(lib_dir), "", K_TOPK)
    except SystemExit as ex:
        buf.write("(exit %s)" % str(ex))
    return buf.getvalue().strip()


def real_retrieve_ids(lib_dir, qtext, k=K_TOPK):
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            b3.cmd_engine("retrieve", str(lib_dir), qtext, k)
    except SystemExit:
        pass
    ids = []
    for line in buf.getvalue().splitlines():
        m = re.search(r"[0-9.\-]+\s+([^ ]+)", line)
        if m:
            ids.append(m.group(1))
    return ids


def check_integrity(lib_dir):
    """真实路径一致性: 链逐行重算 + memory/audit 集合差 + merkle 对账(attic 计入 memory 集)"""
    lib_dir = pathlib.Path(lib_dir)
    chain_bad = n_lines = 0
    prev_tail = None
    re_line = re.compile(r"prev:(\S+) \| h:([0-9a-f]{64}) \| (.*)$")
    for ap in sorted((lib_dir / "audit").glob("lifelog-*.md")):
        for line in ap.read_text(encoding="utf-8").strip().splitlines():
            n_lines += 1
            m = re_line.search(line)
            if not m:
                chain_bad += 1
                continue
            p2, h2, text = m.group(1), m.group(2), m.group(3)
            if p2 == "genesis":
                p2 = ""
            if b3.line_hash(p2, text) != h2:
                chain_bad += 1
            if prev_tail is not None and p2 != prev_tail:
                chain_bad += 1
            prev_tail = h2
    mem = {f.stem for f in (lib_dir / "memory").rglob("*.json")}
    audit_ids = set()
    for ap in (lib_dir / "audit").glob("lifelog-*.md"):
        audit_ids |= set(re.findall(r"entry:(\S+) ", ap.read_text(encoding="utf-8")))
    mismatch = sorted(mem - audit_ids) + sorted(audit_ids - mem)
    st_path = lib_dir / "state.json"
    root_ok = False
    if st_path.exists():
        st = json.loads(st_path.read_text(encoding="utf-8"))
        root_ok = st.get("merkle_root") == b3.merkle_root(lib_dir, exclude={"state.json"})
    attic_dir = lib_dir / "memory" / "attic"
    attic = len(list(attic_dir.glob("*.json"))) if attic_dir.exists() else 0
    nbytes = sum(p.stat().st_size for p in lib_dir.rglob("*") if p.is_file())
    return {"chain_ok": chain_bad == 0, "chain_bad": chain_bad,
            "mem_audit_mismatch": len(mismatch), "merkle_ok": root_ok,
            "audit_lines": n_lines, "attic_files": attic, "lib_bytes": int(nbytes)}


def parity_check(seed_count=5, queries_per_lib=20, tmp_root=None):
    """P0: retrieve_top(默认 cfg) vs b3._rank_entries 的 top-5 集合一致率。
    边界平局(第5与第6名分差 < 1e-9)的查询跳过。"""
    from world_gen import build_world
    if tmp_root is None:
        tmp_root = HERE / "tmp_parity"
    total = ok = 0
    diffs = []
    for sd in range(1, seed_count + 1):
        w = build_world("clean", sd)
        lib = tmp_root / ("lib%d" % sd)
        materialize_lib(lib, w["entries"])
        mem_entries = []
        for p in (lib / "memory").rglob("*.json"):
            if "attic" in str(p):
                continue
            e = json.loads(p.read_text(encoding="utf-8"))
            if e.get("validity", {}).get("t_invalid"):
                continue
            mem_entries.append(e)
        topics = sorted({e["topic"] for e in w["entries"]})
        qs = []
        for t in topics:
            qs += [t] * 4
        for q in qs[:queries_per_lib]:
            sc_b3, _ = b3._rank_entries(str(lib), q)
            rb3 = sorted(sc_b3.items(), key=lambda kv: kv[1][0], reverse=True)
            ids_b3 = [fid for fid, _ in rb3[:K_TOPK]]
            mine = retrieve_top(mem_entries, q, V3_DEFAULT)
            ids_mine = [fid for fid, _s, _e in mine]
            if len(ids_b3) < K_TOPK or len(ids_mine) < K_TOPK:
                continue
            vals_b3 = [v[0] for _, v in rb3]
            if abs(vals_b3[K_TOPK - 1] - vals_b3[K_TOPK]) < 1e-9:
                continue
            total += 1
            if set(ids_b3[:K_TOPK]) == set(ids_mine[:K_TOPK]):
                ok += 1
            else:
                diffs.append({"seed": sd, "q": q, "b3": ids_b3[:5], "mine": ids_mine[:5]})
    return {"total": total, "ok": ok,
            "rate": round(ok / total, 4) if total else None, "diffs": diffs[:8]}
