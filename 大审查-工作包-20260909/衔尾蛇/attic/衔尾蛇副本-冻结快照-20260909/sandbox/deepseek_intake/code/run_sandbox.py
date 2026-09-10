# -*- coding: utf-8 -*-
"""
run_sandbox.py - 记忆库自演化引擎 沙盒实验骨架 (v1)

目标: 在沙盒中论证/探讨 agent 记忆库自演化引擎的架构设计与可行性。
方法: 记忆库的存储/更新/遗忘/审计全部走 bootstrap_v3.py 的真实代码路径;
      自演化引擎(参数变异 -> 两级门控 -> Pareto 档案 -> 真值抽样审计)在其外驱动。
对照: static(静态库, v3 默认参数) / ungated(裸演化, 无门控) / gated(报告修正架构)。
场景: clean(干净世界) / spurious(伪特征: importance 名义值与真实价值错位) /
      switch(目标切换: 前段主题A 后段主题B, 检验 Pareto 档案防灾难性遗忘)。
用法: py run_sandbox.py [--scene clean|spurious|switch|all] [--seeds 3] [--gens 20] [--out out]
"""
import sys, os, json, time, random, argparse, shutil, pathlib, statistics, datetime, re

HERE = pathlib.Path(__file__).resolve().parent
BASE = HERE.parent                      # 自演化验证/
sys.path.insert(0, str(BASE))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import bootstrap_v3 as b3               # 真实记忆库代码路径

# ---------------------------------------------------------------
# 0. 常量(与报告/源码对齐)
# ---------------------------------------------------------------
V3_DEFAULT = dict(w_kw=3.0, w_content=1.0, w_imp=1.0, w_age=0.1, filter_zero=0)
TOPIC_POOL = ["t0", "t1", "t2", "t3", "t4", "t5"]
SEM_TOK    = {t: [t + "a", t + "b", t + "c", t + "d"] for t in TOPIC_POOL}
K_TOPK     = 5          # 检索 top-k(与源码 engine --k 一致)
K_GOLD     = 3          # 每查询金标条目数
SPUR_FRAC  = 0.30       # 伪特征条目占比
MARGIN0    = 0.020      # 主线晋升初始 margin
TOL_ARCH   = 0.040      # 档案宽松准入阈值
CAP_PARETO = 8          # Pareto 档案上限
STALL_GEN  = 5          # 连续零采纳代数 -> margin 减半
AUDIT_EVERY = 3         # 真值抽样审计周期
REVERT_THR = 0.03       # 审计退化回退阈值

# ---------------------------------------------------------------
# 1. 世界生成器
# ---------------------------------------------------------------
def build_world(seed, scene):
    rng = random.Random(seed)
    topics = TOPIC_POOL[:4] if scene == "switch" else TOPIC_POOL[:]
    splitA = topics[:2] if scene == "switch" else None
    splitB = topics[2:] if scene == "switch" else None
    entries = []
    eid = 0
    for t in topics:
        n_per = 10 if scene != "switch" else 12
        for j in range(n_per):
            rv = rng.random()
            spur = (scene == "spurious" and rng.random() < SPUR_FRAC)
            if scene == "spurious":
                nominal = (1.0 - rv) + 0.5 if spur else rv + 0.05 * rng.random()
            else:
                nominal = min(1.0, rv + 0.08 * rng.random())
            sem = SEM_TOK[t]
            toks = sem[:2] + [t] + [rng.choice(sem), rng.choice(["nz1", "nz2", "nz3"])]
            if spur:
                toks.append("SPUR")
            kw = [t]
            if spur:
                kw.append("spurkw")
            age_days = rng.uniform(0, 365)
            created = int(time.time()) - int(age_days * 86400)
            created_s = datetime.datetime.fromtimestamp(created).strftime("%Y-%m-%d %H:%M:%S")
            entries.append({
                "id": "e%03d" % eid, "topic": t, "rv": round(rv, 4),
                "spur": spur, "importance": round(nominal, 4), "age_days": round(age_days, 1),
                "content": " ".join(toks), "keywords": kw, "created_at": created_s,
                "source_event_id": "genesis", "confidence": 1.0,
                "validity": {}, "links": [], "updated_at": created_s,
            })
            eid += 1

    def mk_queries(rng, topics_sel, kind):
        qs = []
        for t in topics_sel:
            pool = [e for e in entries if e["topic"] == t]
            for q in range(4):
                if kind == "judge":
                    gold = sorted(pool, key=lambda e: -e["importance"])[:K_GOLD]
                else:
                    gold = sorted(pool, key=lambda e: -e["rv"])[:K_GOLD]
                qs.append({"topic": t, "q": t,
                           "gold": sorted(e["id"] for e in gold)})
        rng.shuffle(qs)
        return qs

    if scene == "switch":
        trainA = mk_queries(rng, splitA, "judge")
        trainB = mk_queries(rng, splitB, "judge")
        hold   = mk_queries(rng, splitB, "true")
        audit  = mk_queries(rng, topics, "true")[:12]
    else:
        train  = mk_queries(rng, topics, "judge")
        hold   = mk_queries(rng, topics, "true")
        audit  = mk_queries(rng, topics, "true")[:12]
    return {"entries": entries, "topics": topics,
            "trainA": trainA if scene == "switch" else None,
            "trainB": trainB if scene == "switch" else None,
            "train": train if scene != "switch" else None,
            "hold": hold, "audit": audit}

# ---------------------------------------------------------------
# 2. 检索器: v3 _rank_entries 的参数化复刻
# ---------------------------------------------------------------
def retrieve_top(entries, q, cfg, k=K_TOPK):
    scored = []
    for e in entries:
        kw_hit = sum(1 for w in q.split() if w in " ".join(e["keywords"]))
        c_hit  = sum(1 for w in q.split() if w in e["content"])
        if kw_hit:
            c_hit = max(c_hit, 1)
        s = (kw_hit * cfg["w_kw"] + c_hit * cfg["w_content"]
             + e["importance"] * cfg["w_imp"] - e["age_days"] * cfg["w_age"])
        if cfg.get("filter_zero") and kw_hit == 0 and c_hit == 0:
            s = float("-inf")
        scored.append((s, e))
    scored.sort(key=lambda x: -x[0])
    return [e for _, e in scored[:k]]

def util(queries, entries, cfg):
    if not queries:
        return 0.0
    tot = 0.0
    for q in queries:
        top = retrieve_top(entries, q["q"], cfg)
        hit = sum(1 for e in top if e["id"] in q["gold"])
        tot += hit / min(K_GOLD, K_TOPK)
    return tot / len(queries)

# ---------------------------------------------------------------
# 3. 真实记忆库落地 + 一致性检查(全走 bootstrap_v3 代码路径)
# ---------------------------------------------------------------
def materialize_lib(lib_dir, world, seed):
    lib_dir.mkdir(parents=True, exist_ok=True)
    (lib_dir / "state.json").write_text(json.dumps({
        "package": "bootstrap_v3.py", "version": b3.VERSION, "level": "SANDBOX",
        "emotion": {"valence": 0.0, "arousal": 0.5, "certainty": 0.5, "stakes": 0.0},
        "importance_accum": 0, "created_at": time.strftime("%F %T"),
        "merkle_root": ""}, ensure_ascii=False), encoding="utf-8")
    t0 = time.time()
    n_written = 0
    for e in world["entries"]:
        b3.cmd_engine("append", str(lib_dir), json.dumps(e), K_TOPK)
        n_written += 1
    write_ms = (time.time() - t0) * 1000
    integ = check_integrity(lib_dir)
    integ["write_ms"] = round(write_ms, 1)
    integ["entries"] = n_written
    return integ

def check_integrity(lib_dir):
    chain_bad = 0
    n_lines = 0
    prev_tail = None
    re_line = re.compile(r"prev:(\S+) \| h:([0-9a-f]{64}) \| (.*)$")
    for ap in sorted((lib_dir / "audit").glob("lifelog-*.md")):
        for line in ap.read_text(encoding="utf-8").strip().splitlines():
            n_lines += 1
            m = re_line.match(line)
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
    mem_ids = {f.stem for f in (lib_dir / "memory").rglob("*.json") if "attic" not in str(f)}
    audit_ids = set()
    for ap in (lib_dir / "audit").glob("lifelog-*.md"):
        audit_ids |= set(re.findall(r"entry:(\S+) ", ap.read_text(encoding="utf-8")))
    set_mismatch = sorted(mem_ids - audit_ids) + sorted(audit_ids - mem_ids)
    st = json.loads((lib_dir / "state.json").read_text(encoding="utf-8"))
    root_ok = st.get("merkle_root") == b3.merkle_root(lib_dir, exclude={"state.json"})
    nbytes = sum(p.stat().st_size for p in lib_dir.rglob("*") if p.is_file())
    return {"chain_ok": chain_bad == 0, "chain_bad": chain_bad,
            "set_mismatch": set_mismatch[:5],
            "merkle_ok": root_ok, "audit_lines": n_lines, "lib_bytes": int(nbytes)}

# ---------------------------------------------------------------
# 4. 变异算子(固定混合算子, E73)
# ---------------------------------------------------------------
def mutate(rng, cfg, step_scale=0.3):
    c = dict(cfg)
    coin = rng.random()
    keys = ["w_kw", "w_content", "w_imp", "w_age"]
    if coin < 0.10:
        c["filter_zero"] = 1 - c["filter_zero"]
    elif coin < 0.90:
        k = rng.choice(keys)
        c[k] = max(0.0, c[k] * (1 + rng.uniform(-step_scale, step_scale)))
    else:
        for k in keys:
            c[k] = max(0.0, c[k] * (1 + rng.uniform(-0.1, 0.1)))
    return c

# ---------------------------------------------------------------
# 5. 演化引擎(报告 5.1 修正架构的沙盒实现)
# ---------------------------------------------------------------
def evolve(world, mode, seed, gens, quick=False):
    entries = world["entries"]
    rng = random.Random(seed * 7919 + 17)
    train_phaseA = world["trainA"] if world["trainA"] is not None else world["train"]
    train_phaseB = world["trainB"]

    if mode == "static":
        cfg = dict(V3_DEFAULT)
        return {"mode": mode, "final_cfg": cfg,
                "u_trainA": round(util(train_phaseA, entries, cfg), 4),
                "u_hold": round(util(world["hold"], entries, cfg), 4),
                "u_audit": round(util(world["audit"], entries, cfg), 4),
                "adopts": 0, "audit_dips": 0, "rollbacks": 0,
                "traj": [{"gen": 0, "u_audit": round(util(world["audit"], entries, cfg), 4)}]}

    mainline = dict(V3_DEFAULT)
    margin = MARGIN0
    archive = [dict(mainline)]
    adopts = 0
    stall = 0
    audit_dips = 0
    rollbacks = 0
    last_check = None
    traj = []
    gens_eff = gens if not quick else max(4, gens // 4)
    ga = max(2, int(gens_eff * 2 / 3))

    for g in range(gens_eff):
        if train_phaseB is not None:
            train_now = train_phaseA if g < ga else train_phaseB
        else:
            train_now = train_phaseA
        u_main_hold = util(world["hold"], entries, mainline)
        cands = [mutate(rng, mainline) for _ in range(3)]
        for c in cands:
            u_tr = util(train_now, entries, c)
            u_ho = util(world["hold"], entries, c)
            u_mn = util(train_now, entries, mainline)
            if u_tr >= u_mn - TOL_ARCH or u_ho >= u_main_hold - TOL_ARCH:
                archive.append(dict(c))
        archive = _pareto(archive, entries, train_now, world["hold"])
        if len(archive) > CAP_PARETO:
            rng.shuffle(archive)
            archive = archive[:CAP_PARETO]
        best, best_du = None, 0.0
        u_main_tr = util(train_now, entries, mainline)
        for c in archive:
            du_tr = util(train_now, entries, c) - u_main_tr
            du_ho = util(world["hold"], entries, c) - u_main_hold
            if du_tr > margin and du_ho > margin and du_ho > best_du:
                best, best_du = c, du_ho
        if best is not None:
            mainline = dict(best)
            adopts += 1
            stall = 0
        else:
            stall += 1
            if stall >= STALL_GEN:
                margin = max(0.005, margin * 0.5)
                stall = 0
        if mode == "gated" and (g % AUDIT_EVERY == 0 or g == gens_eff - 1):
            u_aud = util(world["audit"], entries, mainline)
            if last_check is not None and u_aud < last_check[1] - REVERT_THR:
                audit_dips += 1
                if last_check[0] is not None:
                    mainline = dict(last_check[0])
                    rollbacks += 1
                margin = max(0.005, margin * 0.7)
            last_check = (dict(mainline), u_aud)
        traj.append({"gen": g,
                     "u_audit": round(util(world["audit"], entries, mainline), 4),
                     "u_train": round(util(train_now, entries, mainline), 4),
                     "adopts": adopts, "margin": round(margin, 4),
                     "arch_size": len(archive)})

    return {"mode": mode, "final_cfg": mainline,
            "u_trainA": round(util(train_phaseA, entries, mainline), 4),
            "u_trainB": round(util(train_phaseB, entries, mainline), 4) if train_phaseB is not None else None,
            "u_hold": round(util(world["hold"], entries, mainline), 4),
            "u_audit": round(util(world["audit"], entries, mainline), 4),
            "adopts": adopts, "audit_dips": audit_dips, "rollbacks": rollbacks,
            "arch_final": len(archive), "traj": traj}

def _pareto(cfgs, entries, train_q, hold_q):
    pts = [(c, util(train_q, entries, c), util(hold_q, entries, c)) for c in cfgs]
    keep = []
    for i in range(len(pts)):
        dominated = False
        for j in range(len(pts)):
            if i == j:
                continue
            if pts[j][1] > pts[i][1] and pts[j][2] > pts[i][2]:
                dominated = True
                break
        if not dominated:
            keep.append(cfgs[i])
    return keep or [cfgs[0]]

# ---------------------------------------------------------------
# 6. 场景 x 对照矩阵 + 汇总
# ---------------------------------------------------------------
SCENES = ["clean", "spurious", "switch"]
MODES  = ["static", "ungated", "gated"]

def run_scene(scene, seeds, gens, quick=False):
    rows = []
    for s in seeds:
        world = build_world(s, scene)
        for mode in MODES:
            t0 = time.time()
            r = evolve(world, mode, s, gens, quick)
            r["seed"] = s
            r["scene"] = scene
            r["sec"] = round(time.time() - t0, 2)
            rows.append(r)
    agg = {}
    for m in MODES:
        rs = [r for r in rows if r["mode"] == m]
        agg[m] = {"u_audit_mean": round(statistics.mean(x["u_audit"] for x in rs), 4),
                  "u_audit_std": round(statistics.pstdev(x["u_audit"] for x in rs), 4),
                  "u_trainA_mean": round(statistics.mean(x["u_trainA"] for x in rs), 4),
                  "u_hold_mean": round(statistics.mean(x["u_hold"] for x in rs), 4),
                  "adopts_mean": round(statistics.mean(x["adopts"] for x in rs), 1),
                  "audit_dips_mean": round(statistics.mean(x["audit_dips"] for x in rs), 1),
                  "rollbacks_mean": round(statistics.mean(x["rollbacks"] for x in rs), 1),
                  "seeds": len(rs)}
    return {"scene": scene, "seeds": seeds, "gens": gens, "by_mode": agg, "rows": rows}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="all", choices=SCENES + ["all"])
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--gens", type=int, default=20)
    ap.add_argument("--out", default="out")
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    out_dir = pathlib.Path(HERE) / a.out
    out_dir.mkdir(exist_ok=True)
    scenes = SCENES if a.scene == "all" else [a.scene]
    manifest = {"script": "run_sandbox.py",
                "python": sys.version.split()[0],
                "bootstrap_v3": b3.VERSION,
                "seeds": a.seeds, "gens": a.gens, "scenes": {}}
    for sc in scenes:
        res = run_scene(sc, list(range(1, a.seeds + 1)), a.gens, a.quick)
        manifest["scenes"][sc] = {"by_mode": res["by_mode"]}
        world = build_world(1, sc)
        lib_dir = out_dir / "libs" / (sc + "_seed1")
        if lib_dir.exists():
            shutil.rmtree(lib_dir)
        integ = materialize_lib(lib_dir, world, 1)
        manifest["scenes"][sc]["integrity"] = integ
        (out_dir / ("rows_" + sc + ".json")).write_text(
            json.dumps(res["rows"], ensure_ascii=False, indent=1), encoding="utf-8")
        print_table(sc, res, integ)
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    print()
    print("[manifest] ->", out_dir / "manifest.json")

def print_table(scene, res, integ):
    print()
    print("===== scene", scene, "| seeds=", res["seeds"], "gens=", res["gens"], "=====")
    hdr = "%-9s %10s %7s %8s %7s %6s %8s %6s" % (
        "mode", "auditU", "std", "trainA", "hold", "adopt", "dips", "rbk")
    print(hdr)
    for m in MODES:
        v = res["by_mode"][m]
        print("%-9s %10.4f %7.4f %8.4f %7.4f %6.1f %8.1f %6.1f" % (
            m, v["u_audit_mean"], v["u_audit_std"], v["u_trainA_mean"],
            v["u_hold_mean"], v["adopts_mean"], v["audit_dips_mean"], v["rollbacks_mean"]))
    print("[integrity] chain_ok=", integ["chain_ok"], "chain_bad=", integ.get("chain_bad", 0),
          "merkle_ok=", integ["merkle_ok"],
          "set_mismatch=", integ["set_mismatch"],
          "audit_lines=", integ["audit_lines"],
          "lib_bytes=", integ["lib_bytes"])

if __name__ == "__main__":
    main()
