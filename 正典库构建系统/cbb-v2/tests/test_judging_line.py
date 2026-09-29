# -*- coding: utf-8 -*-
"""test_judging_line.py — U4 判卷产线离线全链：组装穿插→注票→严格合票→植株门→中途修复。

零 API：考官票由测试注入（glm chunk + ds votes 文件），只验产线机械语义。
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from cbb2 import judging  # noqa: E402

CONTRACT = "测试契约 v2.2"


def make_cfg(tmp: Path) -> judging.JudgeConfig:
    (tmp / "contracts").mkdir(exist_ok=True)
    (tmp / "contracts" / "judge.txt").write_text(CONTRACT, encoding="utf-8")
    raw = {"version": "1.0", "book": "夹具书", "store_root": "store", "work_dir": "work",
           "contract_file": "contracts/judge.txt",
           "panel": {"GLM": {"channel": "subagent"},
                     "DS": {"base": "https://x", "model": "m", "key": {}, "role": "panel"}},
           "plants": {"pairs": 2, "seed": 20260929}, "batch": {"chunk": 10},
           "gate": {"correct_min": 3, "capture_min": 0.8334}}
    p = tmp / "judging.config.json"
    p.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    return judging.load_config(p)


def make_records(n: int) -> list[dict]:
    return [{"record_id": f"cand-{i:04d}", "conclusion": json.dumps({"assert": f"断言{i}"}, ensure_ascii=False),
             "evidence": f"证据{i}：原文直接陈述了断言{i}的要素。"} for i in range(n)]


def make_plants() -> list[dict]:
    return [{"record_id": "plant-pos-0", "expected": "promote",
             "rec": {"conclusion": json.dumps({"assert": "正株断言"}, ensure_ascii=False),
                     "evidence": "证据：原文直接陈述了正株断言的全部要素。"}},
            {"record_id": "plant-pos-1", "expected": "promote",
             "rec": {"conclusion": json.dumps({"assert": "正株断言B"}, ensure_ascii=False),
                     "evidence": "证据：原文明确陈述正株断言B成立。"}},
            {"record_id": "plant-neg-0", "expected": "not_promote",
             "rec": {"conclusion": json.dumps({"assert": "张冠李戴断言"}, ensure_ascii=False),
                     "evidence": "证据：此事与断言主体无关。"}},
            {"record_id": "plant-neg-1", "expected": "not_promote",
             "rec": {"conclusion": json.dumps({"assert": "无中生有断言"}, ensure_ascii=False),
                     "evidence": "证据：原文未提及该断言。"}}]


def test_assemble_interspersed_and_blind(tmp_path):
    cfg = make_cfg(tmp_path)
    plants = make_plants()
    r = judging.assemble(cfg, make_records(20), plants)
    assert r["n"] == 24 and r["plants"] == 4
    man = [json.loads(l) for l in (cfg.work_dir / "manifest.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(man) == 24
    assert not ({"is_plant", "expected"} & set(man[0].keys())), "判卷面泄漏特权字段"
    pidx = [r["idx"] for r in (json.loads(l) for l in (cfg.work_dir / "manifest_priv.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()) if r["is_plant"]]
    assert len(pidx) == 4 and max(pidx) - min(pidx) >= 6, "植株未穿插（堆尾）"


def test_join_gate_pass_and_distribution(tmp_path):
    cfg = make_cfg(tmp_path)
    plants = make_plants()
    judging.assemble(cfg, make_records(20), plants)
    man, priv = judging.load_manifest(cfg.work_dir)
    glm_lines, ds_lines = [], []
    for m in man:
        rid = m["record_id"]
        pinfo = priv[rid]
        if pinfo["is_plant"]:
            g, d = ("support", "support") if pinfo["expected"] == "promote" else ("unsure", "unsure")
        elif rid.endswith("0003"):
            g, d = "support", "support"     # 双票一致 → promote
        elif rid.endswith("0007"):
            g, d = "support", "against"     # against → human
        else:
            g, d = "support", "unsure"      # 弃权 → hold
        glm_lines.append(json.dumps({"record_id": rid, "a": g, "b": g, "vote": g}, ensure_ascii=False))
        ds_lines.append(json.dumps({"record_id": rid, "ds_vote": d}, ensure_ascii=False))
    (cfg.work_dir / "glm_chunks" / "chunk_000.jsonl").write_text("\n".join(glm_lines) + "\n", encoding="utf-8")
    (cfg.work_dir / "ds_votes.jsonl").write_text("\n".join(ds_lines) + "\n", encoding="utf-8")

    s = judging.join_strict(cfg, tag="test")
    assert s["捕获门"] == "PASS", s
    assert s["判决分布"]["promote"] == 3        # 2 正株 + cand-0003
    assert s["判决分布"]["human"] == 1          # cand-0007
    assert s["缺席票"] == 0 and s["坏行跳过"] == 0
    assert "8/8" in s["植物捕获"] or "4/4" in s["植物捕获"]
    ledger = (cfg.work_dir / "judging_ledger.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(ledger) == 24
    assert "is_plant" in ledger[0]              # 台账留痕含植株审计字段


def test_repair_prefix_preserving(tmp_path):
    cfg = make_cfg(tmp_path)
    plants = make_plants()
    judging.assemble(cfg, make_records(20), plants)
    # 造旧式带特权字段的 manifest（模拟中断：chunk_000 已收线=前 10 行保全）
    man = [json.loads(l) for l in (cfg.work_dir / "manifest.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    priv = [json.loads(l) for l in (cfg.work_dir / "manifest_priv.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    by_rid = {r["record_id"]: dict(r, **{k: p[k] for k in ("is_plant", "expected")}) for r, p in zip(man, priv)}
    old = [by_rid[r["record_id"]] for r in man]          # 旧式行：带 is_plant/expected
    (cfg.work_dir / "manifest.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in old), encoding="utf-8")
    (cfg.work_dir / "manifest_priv.jsonl").unlink()
    (cfg.work_dir / "glm_chunks" / "chunk_000.jsonl").write_text(
        "\n".join(json.dumps({"record_id": old[i]["record_id"], "vote": "unsure"}) for i in range(10)) + "\n",
        encoding="utf-8")
    r = judging.repair(cfg)
    assert r["mode"] == "repaired"
    man2 = [json.loads(l) for l in (cfg.work_dir / "manifest.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(man2) == 24 and not ({"is_plant", "expected"} & set(man2[0].keys()))
    # 前缀保全：前 10 行 record_id 与中断前一致
    assert [x["record_id"] for x in man2[:10]] == [x["record_id"] for x in old[:10]]
    priv2 = [json.loads(l) for l in (cfg.work_dir / "manifest_priv.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    pidx = [x["idx"] for x in priv2 if x["is_plant"]]
    assert len(pidx) == 4, "植株总数必须保全（前缀株原位保留=已银行考试证据；尾段株随重排区穿插）"
    # 幂等重入
    r2 = judging.repair(cfg)
    assert r2["mode"] == "already-repaired" and r2["consistent"]
