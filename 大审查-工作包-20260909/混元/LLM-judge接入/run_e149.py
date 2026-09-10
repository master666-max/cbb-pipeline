# -*- coding: utf-8 -*-
"""E149 —— LLM judge 驱动演化的最小闭环（主实验-E149-工作流程.md §2 预注册判据，勿反改）

演化采纳全部由 LLM judge 打分（M-Prometheus-14B @ LM Studio）；真值由语义化世界
构造标签离线度量（零 LLM 成本）。canonical order 铁律：检索列表按条目 id 排序。

断续设计（工作流程 §4）：
  - 调用层：llm_judge_cache.json 按 (model,query,retrieved集) 哈希缓存，跨重启命中
  - 种子层：res_e149.json 完成一个 seed 追加一条
  - 代级层：res_e149_state.json 存 (seed_idx, gen, main, arch, RNG 状态)，逐代写
用法：
  py -X utf8 run_e149.py            # 全量 n=6 × 24 代（续传自动）
  py -X utf8 run_e149.py --smoke    # 1 seed × 4 代冒烟
  py -X utf8 run_e149.py --analyze  # 判定表
"""
import sys, os, json, time, hashlib, statistics, math, random, re
import urllib.request
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.environ.get("JUDGE_API_BASE", "http://127.0.0.1:8080/v1")
MODEL = os.environ.get("JUDGE_MODEL", "m-prometheus-14b.i1")
WORKERS = 8
TIMEOUT = 120
SYS_ABS = ('/no_think 你是检索质量评审。对给出的检索结果与query的相关性打 0 到 1 分'
       '（1=完全切题且内容正确，0=完全无关）。只输出 JSON：{"score": 小数}，不要输出其他内容。')
SYS_RUBRIC = ('/no_think 你是检索质量评审。评分标准（只依据以下两条）：'
       '(1) 主题相关性：检索内容是否与 query 的主题直接相关；'
       '(2) 内容正确性：内容是否正确、具体、可执行。'
       '长度、格式、排版、措辞风格一律不影响评分。'
       '只输出 JSON：{"score": 0到1的小数}，不要输出其他内容。')
ARM = 'rubric' if '--arm-rubric' in sys.argv else 'absolute'
SYS = SYS_RUBRIC if ARM == 'rubric' else SYS_ABS
GENS, KIDS, N_SEEDS = 24, 4, 6
TOPK, NTASK = 4, 12
MARGIN, TOL, CAP = 0.02, 0.04, 8
CACHE_PATH = os.path.join(HERE, f"llm_judge_cache_{ARM}.json")
STATE_PATH = os.path.join(HERE, f"res_e150_{ARM}_state.json")
RES_PATH = os.path.join(HERE, f"res_e150_{ARM}.json")

W = json.load(open(os.path.join(HERE, "semantic_world.json"), encoding="utf-8"))
ENT = {e["id"]: e for e in W["entries"]}
ENT_IDS = sorted(ENT)
for e in ENT.values():
    e.setdefault("tf", 0.1)
QUERIES = {q["kw"]: q["q"] for q in W["queries"]}
KW_GROUPS = {}
for i in ENT_IDS:
    KW_GROUPS.setdefault(ENT[i]["kw"], []).append(i)

CACHE = json.load(open(CACHE_PATH, encoding="utf-8")) if os.path.exists(CACHE_PATH) else {}
_cache_new = 0
_parse_fail = 0

def _save_cache():
    json.dump(CACHE, open(CACHE_PATH, "w", encoding="utf-8"))

def call_llm_raw(query, texts):
    user = "query: " + query + "\n检索结果:\n" + "\n".join("- " + t for t in texts)
    payload = {"model": MODEL, "stream": False, "temperature": 0, "max_tokens": 512,
               "messages": [{"role": "system", "content": SYS},
                            {"role": "user", "content": user}]}
    req = urllib.request.Request(BASE.rstrip("/") + "/chat/completions",
                                 data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        d = json.load(r)
    c = d["choices"][0]["message"]["content"]
    m = re.search(r'"score"\s*:\s*([0-9.]+)', c)
    if m:
        return float(m.group(1)), c
    m = re.search(r'\[RESULT\]\s*(\d)', c)
    if m:
        return (int(m.group(1)) - 1) / 4.0, c
    m = re.search(r'(?:score|评分)[^0-9]{0,6}([0-9.]+)', c)
    if m:
        v = float(m.group(1))
        return (v / 5.0 if v > 1.5 else v), c
    return None, c

def judge_score(query, ids):
    """带缓存与 canonical order 的 judge 调用。失败重试 1 次；仍失败记 0.5+raw 标记（分析时计数）。"""
    global _cache_new, _parse_fail
    canon = sorted(ids)
    texts = [ENT[i]["content"] for i in canon]
    key = hashlib.sha256(json.dumps([MODEL, SYS, query, texts], ensure_ascii=False)
                         .encode()).hexdigest()[:20]
    if key in CACHE:
        return CACHE[key]
    s, raw = None, ""
    for _ in range(2):
        try:
            s, raw = call_llm_raw(query, texts)
            if s is not None:
                break
        except Exception as ex:
            raw = str(ex)[:200]
            time.sleep(2)
    if s is None:
        _parse_fail += 1
        CACHE[key] = 0.5        # 如实记中位值并留 raw 标记；analyze 里按 |raw 键计数
        CACHE[key + "|raw"] = raw
    else:
        CACHE[key] = s
    _cache_new += 1
    if _cache_new % 50 == 0:
        _save_cache()
    return CACHE[key]

def jsc(c, tasks, ex):
    """配置 c 在任务列表上的 LLM 均分。任务并发评分（canonical order 内建于 judge_score）。"""
    def one(t):
        ids = retrieve(c, t["q"])
        return judge_score(t["q"], ids)
    vals = list(ex.map(one, tasks))
    return statistics.mean(vals)

def retrieve(c, query):
    qw = re.findall(r'[A-Za-z0-9\u4e00-\u9fff]+', query)
    scored = []
    for i in ENT_IDS:
        e = ENT[i]
        kh = sum(1 for w in qw if w in (e["kw"], e["topic"]))
        ch = sum(1 for w in qw if w in e["content"])
        if c.filter_zero and kh == 0 and ch == 0:
            continue
        s = (c.w_kw * kh + c.w_content * ch + c.w_imp * e["tf"]
             - c.w_age * (e["age_days"] / 400.0)
             + c.w_len * e["length"] + c.w_fmt * e["formatting"]
             + c.w_den * e["kw_density"] + c.w_cit * e["has_citation"])
        scored.append((s, i))
    scored.sort(key=lambda x: (-x[0], x[1]))     # 分数降序，id 升序破并列（确定性）
    return [i for _, i in scored[:TOPK]]

def tscore_true(c, tasks):
    """真值：构造标签均值，离线零 LLM。"""
    out = []
    for t in tasks:
        ids = retrieve(c, t["q"])
        out.append(statistics.mean(ENT[i]["true_quality"] for i in ids) if ids else 0.0)
    return statistics.mean(out)

def make_tasks(rnd, n):
    kws = list(QUERIES)
    out = []
    for _ in range(n):
        kw = rnd.choice(kws)
        grp = KW_GROUPS[kw]
        out.append({"q": QUERIES[kw], "kw": kw, "golden": rnd.choice(grp)})
    return out

def cfg_dict(c):
    return {k: getattr(c, k) for k in ("w_kw","w_content","w_imp","w_age",
            "w_len","w_fmt","w_den","w_cit","filter_zero","deep")}

def run_seed(seed, gens=GENS, smoke=False):
    from evolve20_shim import Cfg2     # 见文件尾说明：轻量 Cfg2 复制
    rnd = random.Random(seed)
    rj_state = None
    audit_set = make_tasks(rnd, 40)
    root = Cfg2()
    base_true = tscore_true(root, audit_set)
    ex = ThreadPoolExecutor(max_workers=WORKERS)
    eff_arch, main = [root], root
    m, tol, cap = MARGIN, TOL, CAP

    def mut(c):
        d = cfg_dict(c)
        r = rnd.random()
        if r < 0.08:
            d["deep"] = 1 - d["deep"]
        elif r < 0.16:
            d["filter_zero"] = 1 - d["filter_zero"]
        else:
            pk = rnd.choice(["w_kw","w_content","w_imp","w_age","w_len","w_fmt","w_den","w_cit"])
            d[pk] = round(max(-5.0, min(20.0,
                d[pk] * (1 + rnd.choice([-0.4, -0.15, 0.2, 0.6]) * 2.0)
                + rnd.choice([0, 0, 0.5, -0.5]) * 2.0)), 4)
        return Cfg2(**d)

    def pareto(a, tr, he):
        pts = [((jsc(c, tr, ex), jsc(c, he, ex)), c) for c in a]
        front = []
        for (A, ca) in pts:
            if not any(B[0] >= A[0] and B[1] >= A[1] and (B[0] > A[0] or B[1] > A[1])
                       for (B, _cb) in pts):
                front.append(ca)
        return front or a[-1:]

    # ── 断点恢复 ──
    start_gen = 1
    state = json.load(open(STATE_PATH, encoding="utf-8")) if os.path.exists(STATE_PATH) else None
    smoke_tag = f"{ARM}_smoke" if smoke else f"{ARM}_full"
    if state and state.get("tag") == smoke_tag and state.get("seed") == seed:
        start_gen = state["gen"] + 1
        main = Cfg2(**state["main"])
        eff_arch = [Cfg2(**d) for d in state["arch"]]
        rs = state["rnd"]
        rnd.setstate((rs[0], tuple(rs[1]), rs[2]))
        print(f"  [续传] seed={seed} 从 gen={start_gen} 恢复")

    jgain_series = []
    for g in range(start_gen, gens + 1):
        tr = make_tasks(rnd, NTASK)
        he = make_tasks(rnd, NTASK)
        for _ in range(2 if smoke else KIDS):
            cand = rnd.choice(eff_arch[-3:])
            ch = mut(cand)
            d_tr = jsc(ch, tr, ex) - jsc(cand, tr, ex) + rnd.gauss(0, 0.05)
            d_he = jsc(ch, he, ex) - jsc(cand, he, ex) + rnd.gauss(0, 0.05)
            if d_tr > -tol:
                eff_arch.append(ch)
            eff_arch = pareto(eff_arch, tr, he)
            if len(eff_arch) > cap:
                eff_arch = rnd.sample(eff_arch, cap)
            if d_tr > m and d_he > m and jsc(ch, tr, ex) > jsc(main, tr, ex):
                main = ch
        # 逐代断点
        json.dump({"tag": smoke_tag, "seed": seed, "gen": g,
                   "main": cfg_dict(main), "arch": [cfg_dict(c) for c in eff_arch],
                   "rnd": list(rnd.getstate())},
                  open(STATE_PATH, "w", encoding="utf-8"))
        jgain_series.append(jsc(main, audit_set[:8], ex))
        print(f"  seed={seed} gen={g}/{gens} done (cache={len(CACHE)})")

    true_final = tscore_true(main, audit_set)
    true_root = base_true
    j_final = jsc(main, audit_set, ex)
    j_root = jsc(root, audit_set, ex)
    ex.shutdown()
    final_retrieval = {q: retrieve(main, q) for q in QUERIES.values()}
    root_retrieval = {q: retrieve(root, q) for q in QUERIES.values()}
    return {"gain_true": round(true_final - true_root, 6),
            "gain_judge": round(j_final - j_root, 6),
            "judge_series_last": round(jgain_series[-1], 6) if jgain_series else None,
            "final_main": cfg_dict(main),
            "final_retrieval": final_retrieval,
            "root_retrieval": root_retrieval}


def analyze():
    res = json.load(open(RES_PATH, encoding="utf-8"))
    runs = res.get("full", [])
    print("=" * 76)
    print(f"E149 · LLM judge 驱动演化（n={len(runs)}）")
    print("%-8s %12s %12s" % ("seed", "真值增益", "judge增益"))
    for r in runs:
        print("seed-%d  %+12.4f %+12.4f" % (r["seed"], r["gain_true"], r["gain_judge"]))
    gt = [r["gain_true"] for r in runs]
    gj = [r["gain_judge"] for r in runs]
    pos = sum(1 for v in gt if v > 0)
    mt = statistics.mean(gt); set_ = statistics.pstdev(gt)/math.sqrt(len(gt)) if len(gt) > 1 else 0
    print("-" * 76)
    print("H1 真值增益: 均值=%+.4f ± %.4f (t=%+.2f, n=%d)  正种子 %d/%d"
          % (mt, set_, mt/set_ if set_ else 0, len(gt), pos, len(gt)))
    mj = statistics.mean(gj)
    print("H2 自报-真实差: judge增益均值 %+.4f − 真值增益均值 %+.4f = %+0.4f" % (mj, mt, mj - mt))
    nf = sum(1 for k in CACHE if k.endswith("|raw"))
    print("H3 缓存: %d 条（本次解析失败 %d 条，命中率与断点演练见运行日志）" % (len(CACHE), nf))
    print("=" * 76)


def main():
    global _cache_new
    argv = sys.argv
    if "--analyze" in argv:
        analyze(); return
    smoke = "--smoke" in argv
    seeds = [1] if smoke else list(range(1, N_SEEDS + 1))
    gens = 4 if smoke else GENS
    res = json.load(open(RES_PATH, encoding="utf-8")) if os.path.exists(RES_PATH) else {}
    res.setdefault("full", [])
    done_seeds = {r["seed"] for r in res["full"]}
    for seed in seeds:
        if not smoke and seed in done_seeds:
            print(f"  seed={seed} 已完成，跳过")
            continue
        t0 = time.time()
        r = run_seed(seed, gens=gens, smoke=smoke)
        r["seed"] = seed
        if not smoke:
            res["full"] = [x for x in res["full"] if x["seed"] != seed]
            res["full"].append(r)
            json.dump(res, open(RES_PATH, "w", encoding="utf-8"))
            if os.path.exists(STATE_PATH):
                os.remove(STATE_PATH)     # 该 seed 闭合，清 gen 级断点
        print(f"seed={seed} 完成: {r}  耗时 {time.time()-t0:.0f}s")
    _save_cache()
    n_new = _cache_new
    print(f"缓存: {len(CACHE)} 条（本次新增 {n_new}）")
    if not smoke:
        analyze()


if __name__ == "__main__":
    main()
