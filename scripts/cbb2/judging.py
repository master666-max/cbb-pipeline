# -*- coding: utf-8 -*-
"""cbb2.judging — 判卷产线通用配置层（方法学产品化批次 1·U1）。

目标：判卷五件套（组装/考官腿/合票/上岗考试/中途修复）零书本字面量——
库根、工作目录、考官编制（base/model/key 来源）、契约文本、掺株种子、批大小、
植株捕获门限全部外置到 judging.config.json（书=配置，代码=产线）。

约定：
- 配置内相对路径以**配置文件所在目录**为基准解析（config 放仓库根即以仓库根为基准）。
- 考官 key 解析顺序：env → 注册表（ops.secret_from_registry，D-004 值不落盘）。
  槽位 key 一律排在其平台默认键之前（v1.10 教训：默认键劫持新槽位发错端点 401）。
- 契约文本走文件（contracts/*.txt），不进代码——契约是可校准的仪器参数（PT-026/R-032）。
"""
from __future__ import annotations

import glob
import json
import os
import random
import time
from dataclasses import dataclass, field
from pathlib import Path

from . import ops, audit

REQUIRED = ("version", "book", "store_root", "work_dir", "contract_file", "panel",
            "plants", "batch", "gate")


@dataclass
class Examiner:
    name: str
    base: str = ""
    model: str = ""
    channel: str = "api"
    role: str = "panel"
    key_env: str = ""
    key_registry: list = field(default_factory=list)
    max_tokens: int = 2048
    paced: bool = False

    def key(self) -> str:
        """env 优先 → 注册表逐名回读（槽位键已按优先序排列）。值不落盘不打印（D-004）。"""
        if self.key_env:
            v = os.environ.get(self.key_env)
            if v:
                return v
        for name in self.key_registry:
            v = ops.secret_from_registry(name)
            if v:
                return v
        return ""

    @property
    def audit(self) -> bool:
        return self.role == "audit"


@dataclass
class JudgeConfig:
    path: Path
    version: str
    book: str
    store_root: Path
    work_dir: Path
    contract_file: Path
    contract: str
    panel: dict
    examiners: dict
    plants: dict
    batch: dict
    gate: dict

    def examiner(self, name: str) -> Examiner:
        return self.examiners[name]


def _resolve(base: Path, p: str) -> Path:
    q = Path(p)
    return q if q.is_absolute() else (base / q)


def load_config(path: str | Path) -> JudgeConfig:
    path = Path(path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    missing = [k for k in REQUIRED if k not in raw]
    if missing:
        raise ValueError(f"判卷配置缺必填字段: {missing}（{path}）")
    base = path.resolve().parent
    store_root = _resolve(base, raw["store_root"])
    work_dir = _resolve(base, raw["work_dir"])
    contract_file = _resolve(base, raw["contract_file"])
    contract = contract_file.read_text(encoding="utf-8")
    if not contract.strip():
        raise ValueError(f"契约文件为空: {contract_file}")

    examiners = {}
    for name, spec in (raw.get("panel") or {}).items():
        key = spec.get("key") or {}
        examiners[name] = Examiner(
            name=name,
            base=spec.get("base", ""),
            model=spec.get("model", ""),
            channel=spec.get("channel", "api"),
            role=spec.get("role", "panel"),
            key_env=key.get("env", ""),
            key_registry=[k for k in (key.get("registry"), key.get("registry2")) if k],
            max_tokens=int(spec.get("max_tokens", 2048)),
            paced=bool(spec.get("paced", False)),
        )
    if not any(e.role == "panel" for e in examiners.values()):
        raise ValueError("panel 中至少需要一名 role=panel 考官")

    gate = raw["gate"]
    float(gate["capture_min"])  # 类型自检
    return JudgeConfig(path=path.resolve(), version=str(raw["version"]), book=raw["book"],
                       store_root=store_root, work_dir=work_dir, contract_file=contract_file,
                       contract=contract, panel=raw["panel"], examiners=examiners,
                       plants=raw["plants"], batch=raw["batch"], gate=gate)


# ============ U2/U3/U4：判卷产线引擎（书=配置，以下零书本字面量） ============


def payload_body(record_id: str, conclusion: str, evidence: str) -> dict:
    return {"record_id": record_id, "conclusion": conclusion, "evidence": evidence}


def _plant_concl_evi(rec: dict) -> tuple[str, str]:
    """株源兼容三种形状：{conclusion,evidence} 成品 / {canonical:dict,evidence:list[dict]} / {canonical:str,…}。"""
    if "conclusion" in rec:
        return rec["conclusion"], rec["evidence"]
    c = rec.get("canonical") or {}
    conclusion = c if isinstance(c, str) else json.dumps(c, ensure_ascii=False, sort_keys=True)
    ev = rec.get("evidence") or []

    def _q(e):
        return e.get("quote", "") if isinstance(e, dict) else str(e)

    evidence = ev if isinstance(ev, str) else "；".join(_q(e) for e in ev)
    return conclusion, evidence


def load_records_jsonl(path: str | Path) -> list[dict]:
    out = []
    for l in Path(path).read_text(encoding="utf-8").splitlines():
        s = l.strip()
        if not s:
            continue
        r = json.loads(s)
        out.append({"record_id": r["record_id"], "conclusion": r["conclusion"], "evidence": r["evidence"]})
    return out


def load_plants_jsonl(path: str | Path) -> list[dict]:
    out = []
    for l in Path(path).read_text(encoding="utf-8").splitlines():
        s = l.strip()
        if not s:
            continue
        r = json.loads(s)
        out.append({"record_id": r["record_id"], "rec": r.get("rec") or r, "expected": r["expected"]})
    return out


def assemble(cfg: JudgeConfig, records: list[dict], plants: list[dict]) -> dict:
    """判卷面组装：植株 seeded 随机穿插（非末尾堆放，B5 实证纪律）+ 判卷面零特权字段
    （expected/is_plant 走 manifest_priv.jsonl，考官盲评）。幂等：整目录重写。"""
    work = cfg.work_dir
    (work / "payload").mkdir(parents=True, exist_ok=True)
    (work / "glm_chunks").mkdir(exist_ok=True)
    items, priv = [], []

    def emit(rid, conclusion, evidence, is_plant, expected):
        fn = f"{len(items):05d}.json"
        (work / "payload" / fn).write_text(
            json.dumps(payload_body(rid, conclusion, evidence), ensure_ascii=False), encoding="utf-8")
        idx = len(items)                          # 0 基位置（首件 0；v1.14 曾误写 -1 致全体偏移）
        items.append({"idx": idx, "record_id": rid,
                      "file": str((work / "payload" / fn).resolve()),
                      "is_plant": is_plant, "expected": expected})
        priv.append({"idx": idx, "record_id": rid, "is_plant": is_plant, "expected": expected})

    allrows = [(r["record_id"], r["conclusion"], r["evidence"], False, None) for r in records]
    for p in plants:
        c, e = _plant_concl_evi(p["rec"])
        allrows.append((p["record_id"], c, e, True, p["expected"]))
    random.Random(int(cfg.plants.get("seed", 20260928))).shuffle(allrows)
    for row in allrows:
        emit(*row)

    (work / "manifest.jsonl").write_text(
        "".join(json.dumps({"idx": i["idx"], "record_id": i["record_id"], "file": i["file"]},
                           ensure_ascii=False) + "\n" for i in items), encoding="utf-8")
    (work / "manifest_priv.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in priv), encoding="utf-8")
    n_plants = sum(1 for i in items if i["is_plant"])
    return {"n": len(items), "plants": n_plants, "records": len(items) - n_plants, "dir": str(work)}


def load_manifest(work: Path) -> tuple[list[dict], dict]:
    manifest = [json.loads(l) for l in (work / "manifest.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    privf = work / "manifest_priv.jsonl"
    src = privf if privf.exists() else work / "manifest.jsonl"
    priv = {r["record_id"]: r for r in
            (json.loads(l) for l in src.read_text(encoding="utf-8").splitlines() if l.strip())}
    return manifest, priv


def load_votes(paths: list, key: str) -> dict:
    d, bad = {}, 0
    for fp in paths:
        for l in Path(fp).read_text(encoding="utf-8").splitlines():
            s = l.strip()
            if not s:
                continue
            try:
                r = json.loads(s)
            except Exception:
                bad += 1
                continue
            if r.get(key) in ("support", "against", "unsure"):
                d[r["record_id"]] = r[key]
    return d, bad


def join_strict(cfg: JudgeConfig, glm_dir: Path | None = None, ds_file: Path | None = None,
                tag: str = "round") -> dict:
    """v1.9 严格双票合票：GLM×DEEPSEEK 双 support ∧ 零 against → promote；any against → human；
    余 → hold；n=0 → blocked。植株捕获门走 cfg.gate（correct≥min ∧ capture≥capture_min）。
    判词 append 至 workdir/judging_ledger.jsonl；摘要写 workdir/摘要-{tag}.json 并返回。"""
    work = cfg.work_dir
    glm_dir = glm_dir or (work / "glm_chunks")
    ds_file = ds_file or (work / "ds_votes.jsonl")
    manifest, priv = load_manifest(work)
    glm, bad1 = load_votes(sorted(glob.glob(str(Path(glm_dir) / "chunk_*.jsonl"))), "vote")
    ds, bad2 = load_votes([Path(ds_file)], "ds_vote")
    bad = bad1 + bad2

    def _correct(verdict, expected):
        return (verdict == "promote") if expected == "promote" else (verdict in ("hold", "human"))

    rows, dist = [], {"promote": 0, "hold": 0, "human": 0, "blocked": 0}
    for it in manifest:
        rid = it["record_id"]
        g, d = glm.get(rid), ds.get(rid)
        votes, errors = {}, []
        if g:
            votes["GLM"] = g
        else:
            errors.append({"examiner": "GLM"})
        if d:
            votes["DEEPSEEK"] = d
        else:
            errors.append({"examiner": "DEEPSEEK"})
        n = len(votes)
        against = sum(1 for v in votes.values() if v == "against")
        if n == 0:
            v = "blocked"
        elif against > 0:
            v = "human"
        elif g == "support" and d == "support":
            v = "promote"
        else:
            v = "hold"
        dist[v] += 1
        rows.append({"record_id": rid, "verdict": v, "votes": votes, "need": 2, "against": against,
                     "errors": errors, "degraded": n < 2,
                     "is_plant": bool(priv[rid].get("is_plant")), "expected": priv[rid].get("expected")})
    with (work / "judging_ledger.jsonl").open("a", encoding="utf-8") as jf:
        for r in rows:
            jf.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    plants = [r for r in rows if r["is_plant"]]
    real = [r for r in rows if not r["is_plant"]]
    correct = sum(1 for r in plants if _correct(r["verdict"], r["expected"]))
    capture = correct / len(plants) if plants else 0.0
    gate = len(plants) > 0 and correct >= int(cfg.gate["correct_min"]) and capture >= float(cfg.gate["capture_min"])  # 2026-10-01 审计修正：capture_min 此前假旋钮（读而不生效）
    n_pass = dist["promote"]
    lo, hi = audit.wilson(n_pass, len(real)) if real else (0, 0)
    summary = {"unit": f"judging-dual-{tag}", "book": cfg.book, "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
               "规模": f"{len(real)} 正件 + {len(plants)} 株",
               "植物捕获": f"{correct}/{len(plants)} = {capture:.2f}",
               "捕获门": "PASS" if gate else "FAIL", "判决分布": dist,
               "缺席票": sum(len(r["errors"]) for r in rows), "坏行跳过": bad,
               "晋升率区间": f"{n_pass}/{len(real)} = {n_pass / max(len(real), 1):.2f} [Wilson 95% {lo:.2f}, {hi:.2f}]"}
    (work / f"摘要-{tag}.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    return summary


def repair(cfg: JudgeConfig) -> dict:
    """中途修复（P-031/断档后）：前缀保全（已收线 chunk 行覆盖上界）+ 尾段 seed 穿插重排 +
    判卷面剥敏 + priv 同步。幂等：已剥敏（manifest 无 is_plant）则校验放行。"""
    work = cfg.work_dir
    manifest = [json.loads(l) for l in (work / "manifest.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    if "is_plant" not in manifest[0]:
        n = len(manifest)
        privf = work / "manifest_priv.jsonl"
        pr = [json.loads(l) for l in privf.read_text(encoding="utf-8").splitlines() if l.strip()]
        np_ = sum(1 for r in pr if r["is_plant"])
        ok = len(pr) == n and not ({"is_plant", "expected"} & set(manifest[0].keys()))
        return {"mode": "already-repaired", "consistent": ok}
    privf = work / "manifest_priv.jsonl"
    if privf.exists():
        return {"mode": "already-repaired", "consistent": False}
    n = len(manifest)
    chunk_ids = [int(p.stem.split("_")[1]) for p in (work / "glm_chunks").glob("chunk_*.jsonl")]
    max_chunk = max(chunk_ids) if chunk_ids else -1
    boundary = min((max_chunk + 1) * int(cfg.batch.get("chunk", 10)), n)
    plants = [r for r in manifest if r["is_plant"]]
    # 前缀（已收线区间）原序保全：其中植株=已收线考试件，票已按 record_id 银行，原位保留即保住考试证据。
    # 尾段（重排区）= 其余正件 + 其余植株，seed 穿插重排。
    prefix_plants = sum(1 for r in manifest[:boundary] if r["is_plant"])
    tail_real = [r for r in manifest if not r["is_plant"] and r["idx"] >= boundary]
    tail_plants = [r for r in plants if r["idx"] >= boundary]
    merged = tail_real + tail_plants
    random.Random(int(cfg.plants.get("seed", 20260929))).shuffle(merged)
    priv = []
    for pos, r in enumerate(manifest[:boundary]):
        priv.append({"idx": pos, "record_id": r["record_id"],
                     "is_plant": bool(r.get("is_plant")), "expected": r.get("expected")})
    for j, r in enumerate(merged):
        priv.append({"idx": boundary + j, "record_id": r["record_id"],
                     "is_plant": bool(r.get("is_plant")), "expected": r.get("expected")})
    arch = work / "archive"
    arch.mkdir(exist_ok=True)
    ts = time.strftime("%H%M%S")
    (arch / f"manifest.jsonl.{ts}").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in manifest), encoding="utf-8")
    src_by_rid = {r["record_id"]: r for r in manifest}
    new_rows = []
    for pos, r in enumerate(priv):
        src = src_by_rid[r["record_id"]]
        new_rows.append({"idx": pos, "record_id": r["record_id"], "file": src["file"]})
    (work / "manifest.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in new_rows), encoding="utf-8")
    privf.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in priv), encoding="utf-8")
    pidx = [r["idx"] for r in priv if r["is_plant"]]
    return {"mode": "repaired", "boundary": boundary, "前缀内已有植株": prefix_plants,
            "重排区间": f"{boundary}..{n-1}", "植株新位置": pidx}


def exam(cfg: JudgeConfig, examiner_name: str, plants: list[dict]) -> dict:
    """植株上岗考试：指定考官双序评审，正株须 support、负株 unsure/against。
    门：correct≥cfg.gate.correct_min ∧ capture≥cfg.gate.capture_min。零副作用（不写库/工作区）。"""
    e = cfg.examiner(examiner_name)
    if not e.key():
        return {"gate": "BLOCKED", "examiner": examiner_name, "errors": ["key 未解析（env/注册表）"]}

    def ask(a_text, b_text):
        import re
        raw = ops.chat_once(e.base, e.model, e.key(),
                            f"{cfg.contract}\n【证据摘录】{a_text}\n【记录断言】{b_text}",
                            timeout=90.0, max_tokens=e.max_tokens)
        if e.paced:
            time.sleep(0.8)
        m = re.search(r"\{[^}]*\}", raw, re.DOTALL)
        if not m:
            raise ValueError(f"考官输出非 JSON：{raw[:60]!r}")
        v = json.loads(m.group(0)).get("verdict")
        if v not in ("support", "against", "unsure"):
            raise ValueError(f"考官判定非法：{v!r}")
        return v

    correct, rows = 0, []
    for p in plants:
        c, ev = _plant_concl_evi(p["rec"])
        try:
            va = ask(ev, c)
            vb = ask(c, ev)
            v = va if va == vb else "unsure"
        except Exception as ex:  # noqa: BLE001 — 考试面逐株容错
            v = f"err:{str(ex)[:50]}"
        ok = (v == "support") if p["expected"] == "promote" else (v in ("unsure", "against"))
        correct += ok
        rows.append({"plant": p["record_id"], "expected": p["expected"], "verdict": v, "pass": ok})
    capture = correct / len(plants) if plants else 0.0
    gate = len(plants) > 0 and correct >= int(cfg.gate["correct_min"]) and capture >= float(cfg.gate["capture_min"])  # 2026-10-01 审计修正：capture_min 此前假旋钮（读而不生效）
    return {"examiner": examiner_name, "correct": correct, "total": len(plants),
            "capture": round(capture, 3), "gate": "PASS" if gate else "FAIL", "rows": rows}
