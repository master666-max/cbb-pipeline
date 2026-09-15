# -*- coding: utf-8 -*-
"""adapt_record_to_tier1.py — Record v2.0 候选 → Step0 Tier1 评分形态适配器（R-018）。

背景：score_tier1.py（P1执行区/step0-抽取精度实验/脚本/）消费 Tier1 形态
{"entities":[…],"edges":[…],"time_expressions":[…]}，且按文件名中的 excerptN 触发
金标映射。本脚本把 cbb 亲抽候选（cands-*.json，{candidates:[Record…], meta:…}）转为该形态。

映射规则（留痕于 U-C00 STATE；评分器与金标本体一律不改）：
  entity 记录   → entities[]：name=canonical.name；type=canonical.entity_type；
                  summary=observations 文本按序并接（供 FP 展示与时间可用率 blob）
  relation 记录 → edges[]：source=canonical.subject；target=canonical.object；
                  fact=observations(relation) 文本，claim=true 时前缀"【声称】"
  event/foreshadow/anchor → 不映射（Tier1 无对应槽位；门槛只看实体 P）
  time_expressions → 恒为 []（R-018：无对应字段置空数组，本门槛只看实体 P）

用法：py -X utf8 cbb/tools/adapt_record_to_tier1.py --cands <cands.json> --out <tier1-…excerptN.json>
"""
import argparse
import json
import sys
from pathlib import Path


def adapt(cands_path: Path) -> dict:
    data = json.loads(cands_path.read_text(encoding="utf-8"))
    entities, edges = [], []
    for rec in data["candidates"]:
        rt, canon = rec.get("record_type"), rec.get("canonical") or {}
        obs = rec.get("observations") or []
        if rt == "entity" and canon.get("name"):
            entities.append({
                "name": canon["name"],
                "type": canon.get("entity_type", ""),
                "summary": "；".join(o.get("text", "") for o in obs if o.get("text")),
            })
        elif rt == "relation" and canon.get("subject") and canon.get("object"):
            fact = "；".join(o.get("text", "") for o in obs if o.get("text"))
            if canon.get("claim"):
                fact = f"【声称】{fact}"
            edges.append({"source": canon["subject"], "target": canon["object"], "fact": fact})
    return {"entities": entities, "edges": edges, "time_expressions": []}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Record 候选 → Tier1 评分形态适配器（R-018，评分器/金标不改）")
    ap.add_argument("--cands", required=True, help="cbb 规范化候选 JSON（{candidates:[Record…]}）")
    ap.add_argument("--out", required=True, help="输出 Tier1 JSON 路径（文件名须含 excerptN 以触发金标映射）")
    args = ap.parse_args(argv)
    out = adapt(Path(args.cands))
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"entities": len(out["entities"]), "edges": len(out["edges"]),
                      "time_expressions": 0, "out": str(args.out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
