# -*- coding: utf-8 -*-
"""g16c_rejudge.py — G16c 重审（回填后）：双外部考官对回填件重投票。

波A 质控三件内嵌：
  1. 判卷掺植物（A1）：正植株=已晋升件复判（期望 promote）；负植株=张冠李戴拼装
     （甲的断言+乙的证据，期望 hold/human）；捕获率 <5/6 ⇒ 全卷结果降级"仅参考"。
  2. Wilson 区间（A3）：晋升率等宣称全经 audit.wilson/report 出区间，点宣称禁令。
  3. 考官输入审计（C4 前身）：prompt 载荷白名单=canonical+引文串——图派生键即 abort。
支持 --sidecar 指定回填件（试点/全量）与 --plants N。
"""
import json
import random
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "cbb-v2"))

from cbb2 import promote  # noqa: E402
from cbb2 import audit  # noqa: E402

STORE = ROOT / "迷深实战-本体库"
G16B = STORE / "G16b-票面台账.jsonl"
JOURNAL_PILOT = STORE / "G16c-重审台账-试点.jsonl"
JOURNAL_FULL = STORE / "G16c-重审台账.jsonl"

ALLOWED_PAYLOAD_KEYS = {"canonical", "evidence_quotes"}


def build_payload(rec, supplements):
    """考官载荷：canonical+合并引文。白名单外一键即 abort（考官输入审计）。"""
    quotes = [e.get("quote", "") for e in (rec.get("evidence") or [])]
    quotes += [s.get("quote", "") for s in (supplements or [])]
    payload = {"canonical": rec.get("canonical") or {}, "evidence_quotes": quotes}
    bad = set(payload) - ALLOWED_PAYLOAD_KEYS
    assert not bad, f"考官输入审计 FAIL：白名单外字段 {bad}"
    return payload


def load_record(record_id, library):
    for f in STORE.glob(f"libraries/{library}/*/{record_id}.json"):
        return json.loads(f.read_text(encoding="utf-8"))
    return None


def build_plants(n_each=4, seed=20260928):
    """判卷植株：正=G16b 双 support 晋升件复判；负=断言换乙证据留甲（张冠李戴）。"""
    last = {}
    for l in G16B.read_text(encoding="utf-8").splitlines():
        if l.strip():
            r = json.loads(l)
            last[r["record_id"]] = r
    promo = [r for r in last.values()
             if r["verdict"] == "promote" and set(r.get("votes", {}).values()) == {"support"}]
    rng = random.Random(seed)
    picks = rng.sample(promo, min(n_each, len(promo)))
    others = rng.sample([r for r in last.values() if r["record_id"] not in
                         {p["record_id"] for p in picks}],
                        min(n_each, max(len(last) - len(picks), 0)))
    plants = []
    for p in picks:
        rec = load_record(p["record_id"], p.get("library") or "")
        if not rec:
            continue
        plants.append({"record_id": f"plant-pos-{len(plants):02d}-" + p["record_id"][-8:],
                       "src": p["record_id"], "library": p.get("library"),
                       "rec": rec, "supplements": [], "expected": "promote"})
    for i, o in enumerate(others):
        base = picks[i % len(picks)] if picks else None
        if not base:
            break
        donor = load_record(base["record_id"], base.get("library") or "")
        host = load_record(o["record_id"], o.get("library") or "")
        if not donor or not host:
            continue
        plants.append({"record_id": f"plant-neg-{i:02d}",
                       "src": f"{o['record_id']}×{base['record_id']}",
                       "library": host.get("library") or o.get("library"),
                       "rec": {"canonical": donor.get("canonical") or {},
                               "evidence": host.get("evidence") or []},
                       "supplements": [], "expected": "not_promote"})
    return plants


def main():
    sidecar = SIDECAR_PILOT = STORE / "补充证据-回填-试点.jsonl"
    if "--sidecar" in sys.argv:
        sidecar = Path(sys.argv[sys.argv.index("--sidecar") + 1])
        if not sidecar.is_absolute():
            sidecar = STORE / sidecar.name  # 相对名锚到库根（防 cwd 漂移）
    journal = JOURNAL_PILOT if "试点" in sidecar.name else JOURNAL_FULL  # 非试点 sidecar 一律全量台账
    n_plants = 4
    if "--plants" in sys.argv:
        n_plants = int(sys.argv[sys.argv.index("--plants") + 1])

    rows = [json.loads(l) for l in sidecar.read_text(encoding="utf-8").splitlines() if l.strip()]
    full = [r for r in rows if r["status"] in ("full", "partial")]
    # B4 NLI 预筛路由：CONTRADICTION 件直送人工（不烧 API）——路由文件在则遵从
    prescreen = {}
    ps = STORE / "补充证据-NLI预筛.jsonl"
    if ps.exists():
        for l in ps.read_text(encoding="utf-8").splitlines():
            if l.strip():
                r = json.loads(l)
                prescreen[r["record_id"]] = r["route"]
    routed = [r for r in full if prescreen.get(r["record_id"]) == "human_nli"]
    full = [r for r in full if prescreen.get(r["record_id"]) != "human_nli"]
    if "--revote-qwen-against" in sys.argv:
        # B5c：重判被 claim 字段契约缺陷污染的 QWEN=against 件（判词 v2 下重跑）
        last = {}
        if JOURNAL_FULL.exists():
            for l in JOURNAL_FULL.read_text(encoding="utf-8").splitlines():
                if l.strip():
                    r = json.loads(l)
                    last[r["record_id"]] = r
        before = len(full)
        full = [r for r in full
                if r["record_id"] in last
                and last[r["record_id"]].get("votes", {}).get("QWEN") == "against"
                and last[r["record_id"]].get("verdict") == "human"]
        print(f"B5c 契约缺陷重判模式: {len(full)}/{before} 件（JUDGE_PROMPT v2）")

    if "--revote-incomplete" in sys.argv:
        # B5b 补判模式：只重判 QWEN 缺席的持票不完整件（末行 hold 且票数<2）
        last = {}
        if JOURNAL_FULL.exists():
            for l in JOURNAL_FULL.read_text(encoding="utf-8").splitlines():
                if l.strip():
                    r = json.loads(l)
                    last[r["record_id"]] = r
        before = len(full)
        full = [r for r in full
                if r["record_id"] in last
                and last[r["record_id"]].get("verdict") in ("hold", "blocked")
                and len(last[r["record_id"]].get("votes", {})) < 2]
        print(f"B5b 补判模式: 只重判票面不完整件 {len(full)}/{before}")
    print(f"回填可审件: {len(full)}（NLI 预筛转人工 {len(routed)}，其路由见补充证据-NLI预筛.jsonl）")

    plants = build_plants(n_plants)
    print(f"判卷植株: {len(plants)}（正 {sum(1 for p in plants if p['expected']=='promote')} / "
          f"负 {sum(1 for p in plants if p['expected']=='not_promote')}）")

    panel, missing = promote.build_panel(("DEEPSEEK", "QWEN"))
    print(f"编制: {[c.kind for c in panel]}（缺席 {missing or '无'}）；full_size=3 → promote=双 support")
    if not panel or not full:
        print("BLOCKED 或无可评件")
        return

    def review_one(item):
        row, is_plant = item
        if is_plant:
            rec, sup = row["rec"], row["supplements"]
            rid = row["record_id"]
        else:
            rec_path = next(STORE.glob(f"libraries/{row['library']}/*/{row['record_id']}.json"), None)
            if rec_path is None:
                return {"verdict": "error", "record_id": row["record_id"],
                        "errors": [{"reason": "库件未找到"}]}
            rec = json.loads(rec_path.read_text(encoding="utf-8"))
            sup = row["supplements"]
            rid = row["record_id"]
        payload = build_payload(rec, sup)
        conclusion = json.dumps(payload["canonical"], ensure_ascii=False, sort_keys=True)
        evidence = "；".join(payload["evidence_quotes"])
        res = promote.vote(conclusion, evidence, panel, full_size=3)
        res["record_id"] = rid
        if is_plant:
            res["expected"] = row["expected"]
            res["is_plant"] = True
        else:
            res["g16b_verdict"] = None
        return res

    items = [(r, False) for r in full]
    step = max(1, len(items) // (len(plants) or 1))  # 植株穿插全卷——末尾堆放会让末段故障漏检（B5 实证）
    for off, p in enumerate(plants):
        items.insert(min(off * step, len(items)), (p, True))
    t0 = time.time()
    results = []
    with journal.open("a", encoding="utf-8") as jf, \
            ThreadPoolExecutor(max_workers=8) as ex:
        futs = [ex.submit(review_one, it) for it in items]
        for n, fu in enumerate(as_completed(futs), 1):
            try:
                res = fu.result()
            except Exception as e:  # noqa: BLE001 — 单件异常计数不拖批（含输入审计 abort）
                res = {"verdict": "error", "errors": [{"reason": str(e)[:120]}]}
            results.append(res)
            jf.write(json.dumps(res, ensure_ascii=False, sort_keys=True) + "\n")
            jf.flush()
            if n % 20 == 0 or n == len(items):
                print(f"  {n}/{len(items)}  {time.time()-t0:.0f}s")

    # ── 植物捕获门（A1）──
    plant_res = [r for r in results if r.get("is_plant")]
    correct = 0
    for r in plant_res:
        v, exp = r.get("verdict"), r.get("expected")
        ok = (v == "promote") if exp == "promote" else (v in ("hold", "human"))
        correct += ok
    capture = correct / len(plant_res) if plant_res else 0
    gate_pass = len(plant_res) > 0 and correct >= 5 and capture >= 5 / 6

    # ── 正件翻转 + Wilson 区间（A3）──
    real = [r for r in results if not r.get("is_plant")]
    flips = Counter(f"{r.get('g16b_verdict') or '?'} → {r.get('verdict')}" for r in real)
    n_pass = sum(1 for r in real if r.get("verdict") == "promote")
    lo, hi = audit.wilson(n_pass, len(real)) if real else (0, 0)
    rep = audit.report(n_pass, len(real)) if real else {}

    summary = {
        "unit": "G16c", "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "sidecar": sidecar.name,
        "植物捕获": f"{correct}/{len(plant_res)} = {capture:.2f}",
        "捕获门": "PASS" if gate_pass else "FAIL——全卷结果降级仅参考",
        "正件翻转分布": dict(flips),
        "晋升率区间": f"{n_pass}/{len(real)} = {n_pass/len(real):.2f} "
                     f"[Wilson 95% {lo:.2f}, {hi:.2f}]" if real else "-",
        "audit_report": rep,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    (STORE / f"G16c-重审摘要-{'全量' if journal==JOURNAL_FULL else '试点'}.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()


def build_plant_exam_items():
    """判卷上岗考试条目（m-prometheus 上岗考试用）——与掺植物同源同构。"""
    return build_plants(4, 20260928)
