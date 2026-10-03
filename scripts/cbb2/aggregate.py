# -*- coding: utf-8 -*-
"""cbb2.aggregate — 批次 6·A1/A2：保守两源聚合（精确名簇 ∪ aliases 证据面）+ 聚合页渲染。

合并边界（用户裁决·保守两源）：
  L1 精确名簇（canonical.name 相等，零风险）；
  L2 aliases.jsonl 证据面（alias→entity_id 映射，抽取期已判，低风险）；
  L3 四分类策略只做**标注**不做合并；L4 LLM 同指判定本批不做（判卷成本+循环风险）。
冲突语义：同名不同人证据 ⇒ 分裂并标存疑；错误合并代价 > 分裂（力求绝对干净）。
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict


def build_clusters(records: list[dict], alias_rows: list[dict]) -> list[dict]:
    """保守两源聚合。records: 判卷面记录（record_id/canonical.name/status…）；
    alias_rows: aliases.jsonl 行（alias/entity_id/entity_type）。
    返回簇列表：{main_name, members(按名字频次降序的 record_id), aliases, 存疑外部映射}。"""
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    rec_name: dict[str, str] = {}
    name_count: Counter = Counter()
    for r in records:
        rid = "rid:" + r["record_id"]
        nm = (r.get("canonical") or {}).get("name")
        find(rid)
        if nm:
            rec_name[rid] = nm
            name_count[nm] += 1
            union(rid, "name:" + nm)

    external_by_name: dict[str, set] = defaultdict(set)
    for a in alias_rows:
        raw_alias, eid = a.get("alias"), a.get("entity_id")
        if not raw_alias or not eid:
            continue
        if isinstance(raw_alias, dict):
            # L3 四分类真实数据行（别名台账 5/539）：title/descriptor 永不合并；nickname 须置信≥0.85
            alias_t = str(raw_alias.get("name") or "")
            kind = str(raw_alias.get("kind") or "")
            conf = float(raw_alias.get("confidence") or 0)
        else:
            alias_t, kind, conf = str(raw_alias), "", 1.0
        if not alias_t:
            continue
        known = ("rid:" + eid) in rec_name      # eid 是 record_id——比对待 prefixed 键
        merge_blocked = kind in ("title", "descriptor") or (kind == "nickname" and conf < 0.85)
        if known and not merge_blocked:
            union("name:" + alias_t, "rid:" + eid)
            union("alias:" + alias_t, "rid:" + eid)  # 2026-10-01 审计修正：alias: 节点此前从未创建，alias_texts 恒空 ⇒ 世界书别名触发键全缺
        else:
            # 保守语义：不合并的映射降级为该名簇的存疑标注
            external_by_name[alias_t].add(eid)

    comps: dict[str, list] = defaultdict(list)
    for node in list(parent):
        comps[find(node)].append(node)

    clusters = []
    for nodes in comps.values():
        rids = sorted(n[4:] for n in nodes if n.startswith("rid:"))
        if not rids:
            continue
        names = sorted(n[5:] for n in nodes if n.startswith("name:"))
        main_name = max(names, key=lambda x: (name_count.get(x, 0), len(x))) if names else rids[0]
        alias_texts = sorted(n[6:] for n in nodes if n.startswith("alias:"))
        存疑 = sorted(e for nm in names for e in external_by_name.get(nm, set()))
        clusters.append({
            "main_name": main_name,
            "members": rids,
            "names": names,
            "aliases": alias_texts,
            "存疑外部映射": 存疑,
        })
    return sorted(clusters, key=lambda c: -len(c["members"]))


def render_aggregate_page(main_name: str, aliases: list, members: list[dict],
                          anchor: dict, store_rel: str = "../../records/") -> str:
    """聚合页：实体头 + 断言时间线（按章升序，逐条源回链+三态徽章）+ 快照锚。"""
    import html as _h
    aliases_txt = "、".join(_h.escape(str(a)) for a in aliases) or "—"
    badge = {"confirmed": "confirmed ✅", "provisional": "provisional ◐",
             "quarantine": "quarantine ⚠"}.get("quarantine")
    lines = [
        "---",
        f"aggregate_of: {main_name}",
        f"members: {len(members)}",
        f"快照锚: {json.dumps(anchor, ensure_ascii=False, sort_keys=True)}",
        "---",
        "",
        f"# {main_name}（聚合页 · {len(members)} 条断言）",
        "",
        f"**别名**：{aliases_txt}",
        "",
        "## 断言时间线",
        "",
    ]
    def _key(m):
        return (m.get("chapter") if isinstance(m.get("chapter"), int) else 10**9,
                str(m.get("record_id")))
    for m in sorted(members, key=_key):
        st = m.get("status", "provisional")
        stb = {"confirmed": "confirmed ✅", "provisional": "provisional ◐",
               "quarantine": "quarantine ⚠"}.get(st, st)
        lines.append(f"### {_h.escape(str(m.get('name') or m['record_id']))} · {stb} · `{_h.escape(str(m['record_id']))}`")
        ev = m.get("evidence") or []
        if ev and isinstance(ev, list):
            for e in ev:
                if not isinstance(e, dict):
                    continue
                loc = f"[卷{e.get('vol','?')} 章{e.get('chapter','?')} 行{e.get('line','?')}]"
                lines.append(f"> {loc} {_h.escape(str(e.get('quote','')))}")
        elif m.get("quote"):
            lines.append(f"> {_h.escape(str(m['quote']))}")
    lines += ["", "---", "",
              f"<!-- 聚合源：members 按章节升序；冲突断言并列不仲裁（判卷语义留人工窗） -->"]
    return "\n".join(lines) + "\n"
