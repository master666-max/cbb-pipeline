# -*- coding: utf-8 -*-
"""cbb2.tei — G14 别名表 TEI schema 导出 + 亲属称谓一跳展开内核。

别名表（aliases.jsonl）→ TEI namesdates XML：人物走 listPerson/person/persName，
别名作 addName[type][nymRef][cert]，nymRef 指向规范名持有者（person 的 xml:id）；
每别名带 attestation（出处章回证据）。aliases.jsonl 现有字段（alias/entity_id/
entity_type/key，2026-09-27 实测 539 条）**无章回证据**，attestation 按工单口径
置空元素+注记；若未来记录带 evidence 字段则升级输出 bibl（首见章）。

【裁决登记·G14】relationship.js（MIT JS 库）**不引入**。理由：Python 管线内
零 JS 运行时——为导出层引入 node 进程边界，代价（跨语言运维/沙箱/版本漂移）
大于收益；本项目亲属需求仅止于"逆类型/对称回链"一跳展开，该能力 cbb-gate1 的
RELATIONSHIP_INVERSES / SYMMETRIC_RELATIONSHIPS 已单源在案（12 对 + 12 项），
本模块直接 import 复用，不复制表（与 cbb/tools/连续性巡检.py 同口径）。
【待确认】若未来要完整亲属推演（多跳/血缘合成/婚配轮），再评估 relationship.js
via node 子进程方案。

悬挂口径：nymRef 指向的 entity_id 不在实体注册表 ⇒ **只注记，不删不改**
（悬挂端点两分法：禁自动 DELETE，带边即活）。金标：65 例悬挂端点计数在案于
迷深实战-工作区/logs/graph-audit-20260925.json（节点.图外节点数=65；其全名单
仅存 20 例样例，余 45 例名单未落盘【待确认】）。

运行：py -X utf8 tei.py --store <本体库> [--workdir <迷深实战-工作区>] [--out <输出目录>]
"""
from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

TEI_NS = "http://www.tei-c.org/ns/1.0"
XML_NS = "http://www.w3.org/XML/1998/namespace"

# 原因码（schema 负对照：非法别名拒绝并给出码）
REASON_ALIAS_MISSING = "E-ALIAS-MISSING"    # 无 alias 字段
REASON_ALIAS_TYPE = "E-ALIAS-TYPE"          # alias 既非 str 也非 dict
REASON_ALIAS_EMPTY = "E-ALIAS-EMPTY"        # 名字空/纯空白（含 dict 形缺 name）
REASON_ENTITY_MISSING = "E-ENTITY-MISSING"  # entity_id 缺失或非字符串

_SAMPLE_NOTE = (
    "attestation 置空：aliases.jsonl 现有字段（alias/entity_id/entity_type/key）"
    "无章回证据【源字段所限，待补首见章】"
)
_HANGING_NOTE = "nymRef 悬挂：{eid} 不在实体注册表（两分法：只注记，不删不改）"


# ================= gate1 单源导入（不复制表） =================

_G1_CACHE: dict[str, tuple[dict, set]] = {}


def gate1_tables(base: Path | None = None) -> tuple[dict, set]:
    """从 cbb-gate1 导入逆类型/对称表（规则单一来源）。

    不可导入时显式 ValueError，不静默降级成"没有规则"
    （参照 cbb/tools/连续性巡检.py 的 fail-fast 语义，此处按工单要求抛 ValueError）。
    """
    if base is None:
        # 双布局探测：工作区（cbb-v2/cbb2 → 仓根/cbb/cbb-gate1）与
        # skill 包（scripts/cbb2 → scripts/cbb/cbb-gate1）
        base = Path(__file__).resolve().parents[2] / "cbb" / "cbb-gate1"
        if not (base / "cbb_gate1.py").exists():
            alt = Path(__file__).resolve().parents[1] / "cbb" / "cbb-gate1"
            if (alt / "cbb_gate1.py").exists():
                base = alt
    base = Path(base)
    key = str(base)
    if key in _G1_CACHE:
        return _G1_CACHE[key]
    try:
        if key not in sys.path:
            sys.path.insert(0, key)
        from cbb_gate1 import RELATIONSHIP_INVERSES, SYMMETRIC_RELATIONSHIPS  # type: ignore
    except Exception as e:  # noqa: BLE001 — 导入失败即显式报错（fail-fast）
        raise ValueError(f"无法从 cbb-gate1 导入逆类型/对称表（规则单一来源，base={base}）：{e}") from e
    # 只读快照：值本身仍唯一来源于 gate1，此处仅防调用方误改共享状态
    tables = (dict(RELATIONSHIP_INVERSES), set(SYMMETRIC_RELATIONSHIPS))
    _G1_CACHE[key] = tables
    return tables


# ================= 别名校验（schema 正负对照的"负"侧） =================

def validate_alias(raw: dict) -> tuple[dict, str | None]:
    """校验单条别名记录，返回 (规范化视图, 原因码)；合法时原因码为 None。

    支持两种真实在库形态（aliases.jsonl 2026-09-27 实测：534 条 str 形 + 5 条 dict 形）：
      a) alias 为 str；
      b) alias 为 {"name", "kind", "confidence"} dict（遗留抽取形态，kind→addName
         的 type、confidence→cert）。
    """
    alias = raw.get("alias")
    if alias is None:
        return {}, REASON_ALIAS_MISSING
    kind: str | None = None
    cert: str | None = None
    if isinstance(alias, dict):
        name = alias.get("name")
        k = alias.get("kind")
        kind = k if isinstance(k, str) and k else None
        conf = alias.get("confidence")
        if isinstance(conf, (int, float)) and 0 < conf <= 1:
            cert = str(conf)
    elif isinstance(alias, str):
        name = alias
    else:
        return {}, REASON_ALIAS_TYPE
    if not isinstance(name, str) or not name.strip():
        return {}, REASON_ALIAS_EMPTY
    eid = raw.get("entity_id")
    if not isinstance(eid, str) or not eid.strip():
        return {}, REASON_ENTITY_MISSING
    etype = raw.get("entity_type")
    view = {
        "name": name.strip(),
        "kind": kind,
        "cert": cert,
        "entity_id": eid.strip(),
        "entity_type": etype if isinstance(etype, str) and etype else "未分类",
        "evidence": raw.get("evidence") if isinstance(raw.get("evidence"), list) else [],
    }
    return view, None


# ================= TEI 导出 =================

def _q(tag: str) -> str:
    return f"{{{TEI_NS}}}{tag}"


def _sub(parent, tag: str, text: str | None = None, **attrib):
    el = ET.SubElement(parent, _q(tag), {k: v for k, v in attrib.items() if v is not None})
    if text is not None:
        el.text = text
    return el


def _entity_registry_id(eid: str) -> str:
    return f"nym-{eid}"


def build_tei(aliases: list[dict], registry: dict[str, str] | None = None,
              title: str = "《迷深》别名表 TEI 导出（G14）") -> dict:
    """别名表 → TEI DOM。返回 {"root": Element, "rejected": [...], "stats": {...}}。

    registry：entity_id → 规范名（来自库内实体 canonical.name，见 load_registry）。
    未提供/查无此 id ⇒ nymRef 悬挂，输出注记不崩（两分法：只注记，不删不改）。
    """
    registry = registry or {}
    # 分组（保持首见顺序）+ 拒绝件
    groups: dict[str, dict] = {}
    order: list[str] = []
    rejected: list[dict] = []
    for i, raw in enumerate(aliases):
        view, reason = validate_alias(raw if isinstance(raw, dict) else {})
        if reason:
            rejected.append({"index": i, "reason": reason, "record": raw})
            continue
        eid = view["entity_id"]
        if eid not in groups:
            groups[eid] = []
            order.append(eid)
        groups[eid].append(view)

    ET.register_namespace("", TEI_NS)
    root = ET.Element(_q("TEI"))
    header = _sub(root, "teiHeader")
    fd = _sub(header, "fileDesc")
    _sub(_sub(fd, "titleStmt"), "title", title)
    _sub(_sub(fd, "publicationStmt"), "p", "正典库构建系统 · cbb2.tei 导出（差异披露不改写）")
    _sub(_sub(fd, "sourceDesc"), "p",
         f"来源：迷深实战-本体库/aliases.jsonl（输入 {len(aliases)} 条，"
         f"合法 {len(aliases) - len(rejected)} 条，拒绝 {len(rejected)} 条）")

    stand_off = _sub(root, "standOff")
    list_person = _sub(stand_off, "listPerson")
    list_other = _sub(stand_off, "list", type="非人物实体")
    hanging = 0
    persons = 0
    for eid in order:
        canonical = registry.get(eid)
        is_hanging = canonical is None
        if is_hanging:
            hanging += 1
        views = groups[eid]
        is_person = any(v["entity_type"].startswith("人物") for v in views)
        if is_person:
            persons += 1
            holder = _sub(list_person, "person", **{f"{{{XML_NS}}}id": _entity_registry_id(eid)})
            _sub(holder, "persName", canonical if canonical else eid)
            alias_tag = "addName"
        else:
            holder = _sub(list_other, "item")
            _sub(holder, "name", canonical if canonical else eid,
                 type="规范名", **{f"{{{XML_NS}}}id": _entity_registry_id(eid)})
            alias_tag = "name"
        if is_hanging:
            _sub(holder, "note", _HANGING_NOTE.format(eid=eid), type="hanging")
        for v in views:
            attr_type = v["kind"] if v["kind"] else "unknown"
            el = _sub(holder, alias_tag, v["name"], type=attr_type,
                      nymRef=f"#{_entity_registry_id(eid)}", cert=v["cert"])
            att = _sub(el, "attestation")
            evs = v["evidence"]
            if evs:
                for ev in evs:
                    if isinstance(ev, dict) and ev.get("chapter") is not None:
                        _sub(att, "bibl", f"第{ev['chapter']}章")
                if not len(att):
                    _sub(att, "note", _SAMPLE_NOTE)
            else:
                # 缺章回证据 ⇒ 空元素 + 注记（工单 G14 口径）
                _sub(el, "note", _SAMPLE_NOTE, type="attestation-missing")

    stats = {
        "input": len(aliases),
        "valid": len(aliases) - len(rejected),
        "rejected": len(rejected),
        "entities": len(order),
        "persons": persons,
        "hanging": hanging,
    }
    return {"root": root, "rejected": rejected, "stats": stats}


def to_tei(aliases: list[dict], registry: dict[str, str] | None = None) -> str:
    """别名表 → TEI XML 字符串（带声明）。悬挂 nymRef 只注记不崩。"""
    built = build_tei(aliases, registry)
    return ET.tostring(built["root"], encoding="unicode", xml_declaration=True)


def load_registry(store_root: Path) -> dict[str, str]:
    """实体注册表：record_id → canonical.name（character/setting 两库，
    provisional+confirmed；与 cbb/tools/连续性巡检.py 的 ENTITY_LIBS 同口径）。"""
    store_root = Path(store_root)
    reg: dict[str, str] = {}
    for lib in ("character", "setting"):
        for status in ("provisional", "confirmed"):
            d = store_root / "libraries" / lib / status
            if not d.exists():
                continue
            for f in sorted(d.glob("*.json")):
                try:
                    rec = json.loads(f.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):  # 坏件跳过，导出口径披露不改写
                    continue
                name = (rec.get("canonical") or {}).get("name")
                rid = rec.get("record_id")
                if isinstance(name, str) and name and isinstance(rid, str):
                    reg[rid] = name
    return reg


# ================= 亲属称谓内核（一跳展开；gate1 表单源） =================

def expand_kinship(relations: list[dict], base: Path | None = None) -> dict:
    """用 cbb-gate1 的逆类型/对称表做一跳展开。

    输入关系三元组列表，兼容两种键形：
      - 内核形 {"source", "type", "target"}；
      - 在库形 {"subject", "rel_type", "object"}（libraries/relation 的 canonical
        实测形态；库内 rel_type 为自由中文词表，命中 gate1 表者极少，
        未命中类型原样保留 known=False，不静默丢弃）。
    对称（spouse/sibling…）补反向边；逆类型（parent→child…）翻转补边；
    重复边（输入已含反向）去重。返回 {"edges", "counts", "tables"}。
    """
    inv, sym = gate1_tables(base)

    def _trip(r: dict) -> tuple:
        if "source" in r or "target" in r or "type" in r:
            return r.get("source"), r.get("type"), r.get("target")
        return r.get("subject"), r.get("rel_type"), r.get("object")

    edges: list[dict] = []
    seen: set[tuple] = set()
    counts = {"input": 0, "skipped": 0, "original": 0, "inverse": 0, "symmetric": 0,
              "unknown_type": 0}
    for r in relations or []:
        if not isinstance(r, dict):
            counts["skipped"] += 1
            continue
        s, t, o = _trip(r)
        if not t or s is None or o is None:
            counts["skipped"] += 1
            continue
        counts["input"] += 1
        expands: list[tuple[str, str, str]] = []
        if t in sym:
            expands.append((o, t, s))
        elif t in inv:
            expands.append((o, inv[t], s))
        else:
            counts["unknown_type"] += 1
        for src, ty, dst in [(s, t, o)] + expands:
            k = (src, ty, dst)
            if k in seen:
                continue
            seen.add(k)
            origin = "original" if (src, ty, dst) == (s, t, o) else (
                "symmetric" if ty == t else "inverse")
            edges.append({"source": src, "type": ty, "target": dst, "origin": origin})
            counts[origin] += 1
    counts["output"] = len(edges)
    return {
        "edges": edges,
        "counts": counts,
        "tables": {"inverse_pairs": len(inv), "symmetric_items": len(sym)},
    }


# ================= 库级导出（报告 + 样件；永不覆盖已有文件） =================

def export_store(store_root: Path, workdir: Path | None = None,
                 out_dir: Path | None = None, sample_limit: int = 50) -> dict:
    """全流程：aliases.jsonl → TEI 样件（前 N 条）+ G14 报告 JSON。

    金标口径：65 例悬挂端点 = 迷深实战-工作区/logs/graph-audit-20260925.json
    节点.图外节点数；该日志全名单仅存 20 例样例（节点.图外节点列表），
    别名覆盖率按此 20 例计算（余 45 例名单未落盘【待确认】）。
    铁律 D-001：目标文件已存在则抛 FileExistsError，永不覆盖。
    """
    store_root = Path(store_root)
    out_dir = Path(out_dir) if out_dir else store_root
    xml_path = out_dir / "G14-TEI样件.xml"
    report_path = out_dir / "G14-TEI别名报告.json"
    for p in (xml_path, report_path):
        if p.exists():
            raise FileExistsError(f"目标已存在，永不覆盖（铁律 D-001）：{p}")

    aliases_raw = store_root / "aliases.jsonl"
    aliases: list[dict] = []
    if aliases_raw.exists():
        for line in aliases_raw.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                aliases.append(json.loads(line))
            except json.JSONDecodeError:
                aliases.append({"alias": 123})  # 坏行按非法件走拒绝通道（E-ALIAS-TYPE）

    registry = load_registry(store_root)
    built = build_tei(aliases[:sample_limit], registry)
    xml_str = ET.tostring(built["root"], encoding="unicode", xml_declaration=True)
    xml_bytes = len(xml_str.encode("utf-8"))

    inv, sym = gate1_tables()

    # 金标侦察
    gold_status = "缺源【待确认】"
    gold_detail: dict = {"日志": "迷深实战-工作区/logs/graph-audit-20260925.json（未找到）"}
    hit = miss = None
    if workdir:
        audit_path = Path(workdir) / "logs" / "graph-audit-20260925.json"
        if audit_path.exists():
            try:
                audit = json.loads(audit_path.read_text(encoding="utf-8"))
                node = audit.get("节点", {})
                total = node.get("图外节点数")
                names = [n for n in node.get("图外节点", []) if isinstance(n, str)]
                alias_names = set()
                for a in aliases:
                    v, reason = validate_alias(a)
                    if not reason:
                        alias_names.add(v["name"])
                hit = sorted(n for n in names if n in alias_names)
                miss = sorted(n for n in names if n not in alias_names)
                if total == 65:
                    gold_status = "65例金标在案"
                gold_detail = {
                    "日志": "迷深实战-工作区/logs/graph-audit-20260925.json",
                    "计数": total,
                    "名单样例数": len(names),
                    "名单样例命中": len(hit),
                    "名单样例未命中": len(miss),
                    "未命中样例": miss,
                    "注记": "全名单仅存 20 例样例，余 45 例未落盘【待确认】；命中=别名表精确同名",
                }
            except (json.JSONDecodeError, OSError) as e:
                gold_detail["读取失败"] = str(e)

    report = {
        "aliases总数": len(aliases),
        "TEI导出样件字节数": xml_bytes,
        "亲属表条目数": len(inv) + len(sym),
        "亲属表明细": {"逆类型对": len(inv), "对称项": len(sym), "单一来源": "cbb/cbb-gate1/cbb_gate1.py"},
        "金标状态": gold_status,
        "金标明细": gold_detail,
        "样件口径": f"前 {sample_limit} 条别名记录（文件序）",
        "样件统计": built["stats"],
        "relationship.js裁决": "不引入（Python 管线内零 JS 运行时；gate1 表单源替代）【待确认：未来完整亲属推演再评估】",
        "生成时间": datetime.now().isoformat(timespec="seconds"),
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    xml_path.write_text(xml_str, encoding="utf-8")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"xml_path": xml_path, "report_path": report_path, "report": report,
            "xml_bytes": xml_bytes, "hit": hit, "miss": miss}


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="G14：别名表 TEI 导出 + 报告")
    ap.add_argument("--store", default="迷深实战-本体库")
    ap.add_argument("--workdir", default="迷深实战-工作区")
    ap.add_argument("--out", default=None, help="默认写入 --store 同目录")
    ap.add_argument("--sample-limit", type=int, default=50)
    args = ap.parse_args()
    root = Path(__file__).resolve().parents[2]
    r = export_store(root / args.store, root / args.workdir,
                     root / args.out if args.out else None, args.sample_limit)
    print(f"样件：{r['xml_path']}（{r['xml_bytes']} 字节）")
    print(f"报告：{r['report_path']}")
    print(f"金标：{r['report']['金标状态']}；名单样例命中 {len(r['hit'] or [])} 例")
