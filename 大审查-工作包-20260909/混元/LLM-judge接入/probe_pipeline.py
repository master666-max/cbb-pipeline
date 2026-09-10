# -*- coding: utf-8 -*-
"""P1-P5 judge 质量探针管线（试点方案 §二）

用法：
  py -X utf8 probe_pipeline.py                     # 默认 ollama qwen3:8b
  set JUDGE_API_BASE=http://localhost:1234/v1      # LM Studio
  set JUDGE_MODEL=m-prometheus-14b                 # 换 judge 只改环境变量
  py -X utf8 probe_pipeline.py

探针（同一套 prompt 跨 judge 可比）：
  P1 确定性      同调用重复 2 次，逐字一致率
  P2 辨别力      高档列表 vs 低档列表（6 query × 5 抽，配对）
  P3 JSON 服从   全部调用的解析成功率
  P4 表象敏感性   原文 vs 冗长填充 vs 花哨格式（同质量配对差 = 偏见读数）
  P5 吞吐        并发 8 路实测 calls/s → 全量实验时长推算
"""
import json, os, sys, time, statistics, math, random, re
import urllib.request
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.environ.get("JUDGE_API_BASE", "http://localhost:11434")
MODEL = os.environ.get("JUDGE_MODEL", "qwen3:8b")
WORKERS = int(os.environ.get("JUDGE_WORKERS", "8"))
TIMEOUT = 120
SYS = ('/no_think 你是检索质量评审。对给出的检索结果与query的相关性打 0 到 1 分'
       '（1=完全切题且内容正确，0=完全无关）。只输出 JSON：{"score": 小数}，不要输出其他内容。')

W = json.load(open(os.path.join(HERE, "semantic_world.json"), encoding="utf-8"))
ENT = {e["id"]: e for e in W["entries"]}
QUERIES = {q["kw"]: q for q in W["queries"]}

FILLER = ("（另注：本条内容在整理时已按最新规范复核过一遍，措辞与排版尽可能照顾阅读体验，"
          "如需进一步展开可以继续补充更多背景与上下文信息。）")


def list_text(ids):
    # canonical order：按条目 id 排序后呈现——消除位置偏见操纵面（试点报告 §三）
    return "\n".join("- " + ENT[i]["content"] for i in sorted(ids))


def call_llm(query, ids):
    """单次 judge 调用。返回 (score|None, latency, raw)。ollama 走原生，其余走 v1。"""
    user = ("query: " + QUERIES[kw_of(ids)]["q"] if False else "query: " + query) + \
           "\n检索结果:\n" + list_text(ids)
    payload = {"model": MODEL, "stream": False,
               "messages": [{"role": "system", "content": SYS},
                            {"role": "user", "content": user}]}
    if "/v1" in BASE or ":1234" in BASE:   # OpenAI 兼容（LM Studio 等）
        url = BASE.rstrip("/") + "/chat/completions"
        payload["temperature"] = 0
        payload["max_tokens"] = 256
    else:                  # ollama 原生
        url = BASE.rstrip("/") + "/api/chat"
        payload["think"] = False
        payload["options"] = {"temperature": 0, "num_ctx": 4096}
    body = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=body,
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            d = json.load(r)
        content = d["choices"][0]["message"]["content"] if "choices" in d \
            else d["message"]["content"]
        lat = time.time() - t0
        m = re.search(r'"score"\s*:\s*([0-9.]+)', content)
        if m:
            return float(m.group(1)), lat, content
        m = re.search(r'\[RESULT\]\s*(\d)', content)   # M-Prometheus: 1-5 → [0,1]
        if m:
            return (int(m.group(1)) - 1) / 4.0, lat, content
        m = re.search(r'(?:score|评分)[^0-9]{0,6}([0-9.]+)', content)
        if m:
            v = float(m.group(1))
            return (v/5.0 if v > 1.5 else v), lat, content
        return None, lat, content[:100]
    except Exception as ex:
        return None, time.time() - t0, str(ex)[:100]


def kw_of(ids):
    return ENT[ids[0]]["kw"]


def judge_batch(jobs):
    """并发跑一批 (query, ids)，返回 [(score, lat, raw)]。"""
    results = [None] * len(jobs)

    def work(i):
        q, ids = jobs[i]
        s, lat, raw = call_llm(q, ids)
        if s is None:            # 超时重试一次
            s, lat, raw = call_llm(q, ids)
        results[i] = (s, lat, raw)
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        list(ex.map(work, range(len(jobs))))
    return results


def main():
    rnd = random.Random(42)
    jobs, meta = [], []   # meta: (kind, key)

    # ── 构造任务 ──
    pairs = []            # P2/P4 的基础：(query, ids)
    for kw, q in QUERIES.items():
        group = [o["id"] for o in W["entries"] if o["kw"] == kw]
        hi = [o["id"] for o in W["entries"] if o["kw"] == kw and o["tier"] == 0.9]
        lo = [o["id"] for o in W["entries"] if o["kw"] == kw and o["tier"] == 0.1]
        for draw in range(5):
            h = rnd.sample(hi, 3); l = rnd.sample(lo, 3)
            r = rnd.sample(group, 3)
            pairs.append((q["q"], h, l, r, kw, draw))
    for q, h, l, r, kw, draw in pairs:
        for tag, ids in (("high", h), ("low", l), ("rand", r)):
            jobs.append((q, ids)); meta.append((tag, f"{kw}_{draw}"))
    # P4：原文 vs 冗长 vs 花哨（同 high 列表的三种表象）
    for q, h, l, r, kw, draw in pairs:
        jobs.append((q, h)); meta.append(("verbose", f"{kw}_{draw}"))
        jobs.append((q, h)); meta.append(("fancy", f"{kw}_{draw}"))

    print(f"judge={MODEL} @ {BASE} · 任务数={len(jobs)}（含 P1 重复与 P4 变体）")
    t0 = time.time()
    res = judge_batch(jobs)
    wall = time.time() - t0

    # ── P3 JSON 服从 ──
    ok = sum(1 for s, _, _ in res if s is not None)
    print(f"\nP3 JSON 服从: {ok}/{len(res)} = {ok/len(res):.1%}"
          + ("" if ok == len(res) else f"  失败样例: {[raw for s,_,raw in res if s is None][:2]}"))

    # ── P5 吞吐 ──
    ok_lat = [lat for s, lat, _ in res if s is not None]
    cps = len(res) / wall
    print(f"P5 吞吐: {len(res)} 次 / {wall:.0f}s = {cps:.2f} calls/s（并发{WORKERS}）"
          f" · 全实验60万fresh调用预计 {600000/cps/3600:.0f} 小时")

    # ── P1 确定性（对 high 列表全量重评一遍比对）──
    hmap = {}
    for (tag, key), (s, lat, raw) in zip(meta, res):
        if tag == "high":
            hmap[key] = s
    jobs2 = [(q, h) for q, h, l, r, kw, draw in pairs]
    res2 = judge_batch(jobs2)
    same = sum(1 for (s1, _, _), (s2, _, _) in zip(
        [r for m_, r in zip(meta, res) if m_[0] == "high"], res2) if s1 == s2)
    print(f"P1 确定性: {same}/{len(pairs)} 完全一致（temp=0）")

    # ── P2 辨别力 ──
    def vals(tag):
        return {key: s for (tag_, key), (s, _, _) in zip(meta, res) if tag_ == tag}
    H, L, R = vals("high"), vals("low"), vals("rand")
    keys = sorted(H)
    d_hl = [H[k] - L[k] for k in keys]
    m_ = statistics.mean(d_hl); se = statistics.pstdev(d_hl)/math.sqrt(len(d_hl))
    print(f"P2 辨别力: high−low = {m_:+.4f} ± {se:.4f} (t={m_/se if se else 0:+.2f}, n={len(keys)})"
          f" | rand 均值={statistics.mean(R[k] for k in R):.3f}")

    # ── P4 表象敏感性 ──
    # verbose/fancy 任务里 ids 与 high 相同，但文本被修饰——修饰在 list_text 里做不了，
    # 这里改用分数对照：直接用 res 里同 key 的 high 分数（无修饰）对比无法成立，
    # 因此 P4 用独立的修饰版评分（见 transform）。
    vj, fj, hk = [], [], []
    for q, h, l, r, kw, draw in pairs:
        hk.append((f"{kw}_{draw}", q, h))
    def transformed(ids, mode):
        texts = [ENT[i]["content"] for i in ids]
        if mode == "verbose":
            texts = [t + " " + FILLER for t in texts]
        else:
            texts = ["### 要点 " + str(i+1) + "\n**" + t[:len(t)//2] + "**\n\n" + t[len(t)//2:]
                     for i, t in enumerate(texts)]
        return texts
    # 并发评修饰版
    def one(args):
        key, q, ids, mode = args
        user = ("query: " + q + "\n检索结果:\n" +
                "\n".join("- " + t for t in transformed(ids, mode)))
        payload = {"model": MODEL, "stream": False,
                   "messages": [{"role": "system", "content": SYS},
                                {"role": "user", "content": user}]}
        if "/v1" in BASE or ":1234" in BASE:
            url = BASE.rstrip("/") + "/chat/completions"
            payload["temperature"] = 0; payload["max_tokens"] = 512
        else:
            url = BASE.rstrip("/") + "/api/chat"
            payload["think"] = False
            payload["options"] = {"temperature": 0, "num_ctx": 4096}
        req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                d = json.load(r)
            c = d["choices"][0]["message"]["content"] if "choices" in d else d["message"]["content"]
            m = re.search(r'"score"\s*:\s*([0-9.]+)', c)
            return (key, float(m.group(1)) if m else None)
        except Exception:
            return (key, None)
    tvar = [("verbose", hk), ("fancy", hk)]
    out = {"verbose": {}, "fancy": {}}
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = []
        for mode, lst in tvar:
            for key, q, ids in lst:
                futs.append((mode, key, ex.submit(one, (key, q, ids, mode))))
        for mode, key, fu in futs:
            out[mode][key] = fu.result()[1]
    for mode, name in (("verbose", "冗长填充"), ("fancy", "花哨格式")):
        dv = [out[mode][k] - H[k] for k in keys if out[mode].get(k) is not None and H.get(k) is not None]
        if dv:
            m_ = statistics.mean(dv); se = statistics.pstdev(dv)/math.sqrt(len(dv))
            print(f"P4 {name}偏见: 修饰 − 原文 = {m_:+.4f} ± {se:.4f} (t={m_/se if se else 0:+.2f}, n={len(dv)})")

    # 存档
    dst = os.path.join(HERE, f"probe_results_{MODEL.replace(':','_').replace('/','_')}.json")
    json.dump({"model": MODEL, "base": BASE, "n_jobs": len(jobs),
               "compliance": ok/len(res), "calls_per_s": cps,
               "p1_same": same, "p1_n": len(pairs),
               "p2": {"high": H, "low": L, "rand": R},
               "p4_verbose": out["verbose"], "p4_fancy": out["fancy"]},
              open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\n结果存档: {dst}")


if __name__ == "__main__":
    main()
