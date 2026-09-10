# -*- coding: utf-8 -*-
"""env_check.py — verify bootstrap_v3.py real code paths run in sandbox
(append routing / retrieve / eval / doctor / clock-injected retire / merkle)."""
import sys, os, json, time, shutil, pathlib, datetime
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
BASE = HERE.parent
sys.path.insert(0, str(BASE))
import bootstrap_v3 as b3

print("b3.VERSION =", b3.VERSION, "| python =", sys.version.split()[0])

work = HERE / "tmp_envcheck"
if work.exists(): shutil.rmtree(work)
work.mkdir()
lib = work / "lib"
lib.mkdir(parents=True)
(lib / "memory").mkdir(exist_ok=True)
(lib / "evals").mkdir(exist_ok=True)
(lib / "state.json").write_text(json.dumps({
    "package": "bootstrap_v3.py", "version": b3.VERSION, "level": "SANDBOX",
    "emotion": {"valence": 0.0, "arousal": 0.5, "certainty": 0.5, "stakes": 0.0},
    "importance_accum": 0, "created_at": time.strftime("%F %T"), "merkle_root": ""},
    ensure_ascii=False), encoding="utf-8")

now = time.time()

def mk(eid, toks, imp, t_invalid=None, days_old=1.0):
    created = datetime.datetime.fromtimestamp(now - days_old * 86400).strftime("%Y-%m-%d %H:%M:%S")
    return {"id": eid, "created_at": created, "updated_at": created,
            "content": " ".join(toks), "keywords": [toks[0]], "links": [],
            "source_event_id": "genesis", "importance": imp, "confidence": 1.0,
            "validity": {"t_invalid": t_invalid} if t_invalid else {}}

entries = [
    mk("e_a1", ["alpha", "vector", "query", "aa"], 8.0),
    mk("e_a2", ["alpha", "schema", "entry", "ab"], 5.0),
    mk("e_b1", ["beta", "retrieve", "rank", "ba"], 6.0),
    mk("e_old", ["alpha", "obsolete", "zz"], 9.0, t_invalid="2020-01-01"),
]
for e in entries:
    b3.cmd_engine("append", str(lib), json.dumps(e), 5)

files = {}
for p in (lib / "memory").rglob("*.json"):
    files.setdefault(p.parent.name, []).append(p.stem)
print("routing:", {k: sorted(v) for k, v in files.items()})

print("--- retrieve 'alpha' ---")
b3.cmd_engine("retrieve", str(lib), "alpha", 5)

gold2 = [{"query": "alpha", "expected": ["e_a1", "e_a2"]},
         {"query": "beta", "expected": ["e_b1"]}]
(lib / "evals" / "golden_queries.json").write_text(json.dumps(gold2, ensure_ascii=False), encoding="utf-8")
b3.cmd_engine("eval", str(lib), "", 5)
b3.cmd_engine("doctor", str(lib), "", 5)

b3.cmd_engine("retire", str(lib), "", 5)
attic = sorted(p.name for p in (lib / "memory" / "attic").rglob("*.json"))
print("attic after retire:", attic)
b3.cmd_engine("doctor", str(lib), "", 5)

print("--- retrieve 'obsolete' (e_old must NOT return) ---")
b3.cmd_engine("retrieve", str(lib), "obsolete", 5)

def size(p): return sum(x.stat().st_size for x in p.rglob("*") if x.is_file())
print("lib_bytes:", size(lib), "| audit files:", [p.name for p in (lib / "audit").glob("*.md")])
print("env_check OK")
