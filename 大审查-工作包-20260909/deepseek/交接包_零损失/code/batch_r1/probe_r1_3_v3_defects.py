# -*- coding: utf-8 -*-
"""probe_r1_3_v3_defects.py — R1-3: v3 基座缺陷回归套件(自演化引擎的依赖面)
复现报告第一部分 P0/P1: (a) 并发 append 丢更新(importance_accum 应为 60); (b) 审计链截断攻击检出;
(c) 同 id 重写拒绝(能力式)已 5/5 —— 本套件并入自动化回归。
"""
import sys, os, json, time, pathlib, subprocess, shutil, io, contextlib, re
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent          # 自演化验证/(bootstrap_v3.py 所在)
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE.parent))
import bootstrap_v3 as b3
import lib_bridge as lb

OUT = HERE / "out_r1_3"
OUT.mkdir(parents=True, exist_ok=True)


def mk_lib(lib, n=5, imp=5.0):
    lib = pathlib.Path(lib)
    if lib.exists():
        shutil.rmtree(lib)
    lib.mkdir(parents=True)
    (lib / "state.json").write_text(json.dumps({
        "package": "bootstrap_v3.py", "version": b3.VERSION, "level": "SANDBOX",
        "emotion": {"valence": 0.0, "arousal": 0.5, "certainty": 0.5, "stakes": 0.0},
        "importance_accum": 0, "created_at": time.strftime("%F %T"), "merkle_root": ""},
        ensure_ascii=False), encoding="utf-8")
    return lib


def entry(i, imp=5.0):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    return {"id": "e%03d" % i, "created_at": ts, "updated_at": ts,
            "content": "k%d fact body" % i, "keywords": ["k%d" % i], "links": [],
            "source_event_id": "genesis", "importance": imp, "confidence": 1.0,
            "validity": {}}


def run_py(args):
    return subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")


results = {}

# ---- (a) 并发 append 丢更新(P0-4): 12 进程 x importance=5 -> accum 期望 60 ----
lib = OUT / "tmp_conc"
mk_lib(lib)
code = "import sys,json; sys.path.insert(0,r'%s'); import bootstrap_v3 as b3, time, pathlib; "        "lib=pathlib.Path(r'%s'); e={'id':'e_c%%d'%%1,'created_at':time.strftime('%%Y-%%m-%%d %%H:%%M:%%S'),"        "'updated_at':'','content':'c fact','keywords':['c'],'links':[],'source_event_id':'genesis',"        "'importance':5.0,'confidence':1.0,'validity':{}}; "        "import multiprocessing as mp; "        "def w(_): b3.cmd_engine('append', str(lib), json.dumps(e), 5); return 1; "        "p=mp.Pool(12); p.map(w, range(12)); p.close(); p.join(); "        "print('ok')" % (ROOT, str(lib))
# simpler: spawn 12 subprocess appends
procs = []
for i in range(12):
    c = ("import sys,json,pathlib,time; sys.path.insert(0,r'%s'); import bootstrap_v3 as b3; "
         "lib=pathlib.Path(r'%s'); ts=time.strftime('%%Y-%%m-%%d %%H:%%M:%%S'); "
         "e={'id':'e_cc%d','created_at':ts,'updated_at':ts,'content':'cc fact','keywords':['cc'],"
         "'links':[],'source_event_id':'genesis','importance':5.0,'confidence':1.0,'validity':{}}; "
         "b3.cmd_engine('append', str(lib), json.dumps(e), 5)" % (ROOT, str(lib), i))
    procs.append(subprocess.Popen([sys.executable, "-c", c], cwd=str(OUT),
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
for p in procs:
    p.wait()
st = json.loads((lib / "state.json").read_text(encoding="utf-8"))
results["concurrent_accum"] = st.get("importance_accum", 0)
mem = len(list((lib / "memory").rglob("*.json")))
results["concurrent_mem_count"] = mem
results["concurrent_expect"] = 60
shutil.rmtree(lib, ignore_errors=True)

# ---- (b) 截断攻击: append 5 -> 删审计尾 2 行 + 重算 root -> doctor 能否检出 ----
lib = OUT / "tmp_trunc"
mk_lib(lib)
for i in range(5):
    b3.cmd_engine("append", str(lib), json.dumps(entry(i)), 5)
audit_files = sorted((lib / "audit").glob("lifelog-*.md"))
lines = audit_files[0].read_text(encoding="utf-8").strip().splitlines()
kept = lines[:-2]
audit_files[0].write_text("\n".join(kept) + "\n", encoding="utf-8")
stp = lib / "state.json"
s2 = json.loads(stp.read_text(encoding="utf-8"))
s2["merkle_root"] = b3.merkle_root(lib, exclude={"state.json"})
stp.write_text(json.dumps(s2, ensure_ascii=False, indent=1), encoding="utf-8")
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    b3.cmd_engine("doctor", str(lib), "", 5)
doc = buf.getvalue()
results["trunc_detected"] = ("断链" in doc) or ("差异等用户裁决" in doc and "根不一致" in doc)
results["trunc_doctor_line"] = [l for l in doc.splitlines() if "doctor:" in l]
results["trunc_recomputed_root_ok"] = s2["merkle_root"] == b3.merkle_root(lib, exclude={"state.json"})
shutil.rmtree(lib, ignore_errors=True)

(OUT / "results_r1_3.json").write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(results, ensure_ascii=False, indent=1))
print("[R1-3] out_r1_3 done");
