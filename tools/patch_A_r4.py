# -*- coding: utf-8 -*-
"""patch_A.py — R4 审计修复批（A2/A4/A5/A6/A7/A8/A9/A12/C1/A13）· 每处替换带断言防静默空替"""
import pathlib

O = pathlib.Path(r"D:/zcode专用！！！！危险！！！！！！！！！/正典库构建系统")
done = []


def rep(rel, old, new, tag):
    p = O / rel
    s = p.read_text(encoding="utf-8")
    assert old in s, f"[{tag}] 锚点未找到: {rel}"
    assert s.count(old) == 1, f"[{tag}] 锚点不唯一（{s.count(old)} 处）: {rel}"
    p.write_text(s.replace(old, new), encoding="utf-8")
    done.append(tag)


# ---- A2a: iter_records 只捕 OSError → 撕裂 JSON 也披露 ----
rep("cbb/cbb-store/cbb_store.py",
    """                        except OSError:
                            self.iter_skipped.append(p.name)""",
    """                        except (OSError, json.JSONDecodeError, UnicodeDecodeError):  # A2 修复：撕裂/坏编码 JSON 也入披露（原只捕 OSError）
                            self.iter_skipped.append(p.name)""",
    "A2a-iter_records")

# ---- A2b: _write_immutable 原子写（temp+rename） ----
rep("cbb/cbb-store/cbb_store.py",
    """        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=1),
                        encoding="utf-8")
        return path, True""",
    """        path.parent.mkdir(parents=True, exist_ok=True)
        # A2 修复：temp+rename 原子写——中途崩溃不留半截 JSON（防单件撕裂阻断全链）
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=1),
                       encoding="utf-8")
        os.replace(tmp, path)
        return path, True""",
    "A2b-atomic-write")

rep("cbb/cbb-store/cbb_store.py", "import argparse\nimport json\n",
    "import argparse\nimport json\nimport os\n", "A2b-import-os")

# ---- A4: status_transition.from 记有效态 ----
rep("cbb/cbb-store/cbb_store.py",
    """        if self.effective_status(record_id) == to_status:
            return {"record_id": record_id, "from": to_status, "to": to_status,
                    "by": by, "note": note, "repeated": True}  # 幂等：目标态已达则不重复入账
        entry = {"record_id": record_id, "from": current["status"], "to": to_status,""",
    """        eff = self.effective_status(record_id)  # A4 修复：from 记有效态（原记文件态，迁移两次后轨迹失真）
        if eff == to_status:
            return {"record_id": record_id, "from": to_status, "to": to_status,
                    "by": by, "note": note, "repeated": True}  # 幂等：目标态已达则不重复入账
        entry = {"record_id": record_id, "from": eff, "to": to_status,""",
    "A4-transition-from")

# ---- A5a: 矛盾分流.propose 按 adjudications 差集 ----
rep("cbb/tools/矛盾分流.py",
    """    by_cls: dict[str, int] = {c: 0 for c in CLASSES}
    proposals: list[dict] = []
    for it in items:
        if it.get("status") != "pending" or it.get("subclass") != "contradiction_pending":
            continue""",
    """    # A5 修复（审计 R4）：pending 判定按 adjudications 差集——items.status 写死后永不回写，
    # 静态过滤会让已裁件重入机械档（违反终态不可再动）
    aq = Path(store_root) / "quarantine-zone" / "adjudications.jsonl"
    adjudicated = {json.loads(x)["item_id"] for x in aq.read_text(encoding="utf-8").splitlines() if x.strip()} \\
        if aq.exists() else set()
    by_cls: dict[str, int] = {c: 0 for c in CLASSES}
    proposals: list[dict] = []
    for it in items:
        if it.get("item_id") in adjudicated:
            continue
        if it.get("subclass") != "contradiction_pending":
            continue""",
    "A5a-propose-adjudicated")

# ---- A5b: apply 台账幂等 ----
rep("cbb/tools/矛盾分流.py",
    """    conf = set(confirmations or [])
    ledger_path = (Path(store_root) / "处置台账.jsonl") if store_root else None
    executed = skipped_cls = skipped_not_confirmed = 0
    rows: list[dict] = []
    for p in proposals:
        if not p.get("mechanical"):
            skipped_cls += 1
            continue
        if mode == "batch_confirm" and p["item_id"] not in conf:""",
    """    conf = set(confirmations or [])
    ledger_path = (Path(store_root) / "处置台账.jsonl") if store_root else None
    # A5b 修复：台账 item_id 幂等——重放不重复落账
    done_ids = set()
    if ledger_path is not None and ledger_path.exists():
        done_ids = {json.loads(x).get("item_id")
                    for x in ledger_path.read_text(encoding="utf-8").splitlines() if x.strip()}
    executed = skipped_cls = skipped_not_confirmed = skipped_dup = 0
    rows: list[dict] = []
    for p in proposals:
        if not p.get("mechanical"):
            skipped_cls += 1
            continue
        if p["item_id"] in done_ids:
            skipped_dup += 1
            continue
        if mode == "batch_confirm" and p["item_id"] not in conf:""",
    "A5b-apply-idempotent")

rep("cbb/tools/矛盾分流.py",
    """    return {"executed": executed, "skipped_direct_conflict": skipped_cls,""",
    """    return {"executed": executed, "skipped_direct_conflict": skipped_cls,
            "skipped_already_in_ledger": skipped_dup,""",
    "A5b-report")

# ---- A6: 哨兵 D 口径对齐（pending 差集） ----
rep("cbb/tools/graphiti_ready.py",
    """    contradiction = sum(1 for r in items
                        if r.get("status") == "pending" and r.get("group") == "entity_unalignable")
    dated = sorted(it["at"] for it in items if it.get("at"))""",
    """    # A6 修复（审计 R4）：口径与 cbb_quarantine.status_report 对齐——按 adjudications 差集取 pending；
    # 原静态 status 过滤含已裁件 → RED 随时间必然触发且不可逆（信号失真）
    aq = store / "quarantine-zone" / "adjudications.jsonl"
    adj_ids = {json.loads(x)["item_id"] for x in aq.read_text(encoding="utf-8").splitlines() if x.strip()} \\
        if aq.exists() else set()
    pend = [r for r in items if r.get("item_id") not in adj_ids]
    contradiction = sum(1 for r in pend if r.get("group") == "entity_unalignable")
    dated = sorted(it["at"] for it in pend if it.get("at"))""",
    "A6-triggerD")

rep("cbb/tools/graphiti_ready.py",
    """         "value": {"contradiction_pending": contradiction, "pending_total": len(items),""",
    """         "value": {"contradiction_pending": contradiction, "pending_total": len(pend),""",
    "A6-pending-total")

# ---- A7: anchor 版本数值排序 ----
rep("cbb/cbb-anchor/cbb_anchor.py",
    """    versions = sorted(p for p in tree_dir.glob("anchor-tree.v*.json"))""",
    """    # A7 修复（审计 R4）：数值排序——原字典序在 v10+ 时 versions[-1] 取到 v9
    versions = sorted(tree_dir.glob("anchor-tree.v*.json"),
                      key=lambda p: int(re.search(r"v(\\d+)", p.stem).group(1)))""",
    "A7-version-sort")

# ---- A8: 语料 BOM 剥离 ----
rep("cbb/cbb-coordinate/cbb_coordinate.py",
    """    text = raw.decode("utf-8")""",
    """    text = raw.decode("utf-8-sig")  # A8 修复（审计 R4）：剥 BOM（记事本默认带 BOM → 首章标记失配 → 全库坐标偏移）""",
    "A8-bom")

# ---- A9: extract 跳过块登记（B6 显式隔离） ----
rep("cbb/cbb-extract/cbb_extract.py",
    """def extract_stub(blocks: list[dict], lexicon=None, event_patterns=None,
                 chapter_titles: dict | None = None) -> list[dict]:""",
    """def extract_stub(blocks: list[dict], lexicon=None, event_patterns=None,
                 chapter_titles: dict | None = None,
                 skipped_out: list[dict] | None = None) -> list[dict]:""",
    "A9-signature")

rep("cbb/cbb-extract/cbb_extract.py",
    """    for block in blocks:
        title = chapter_titles.get(block.get("chapter"), "")
        if is_metatext(title=title, text_sample=block["text"]):
            continue  # ①R6 对应 stub 闸：元文本零抽取
        if has_embedded_instruction(block["text"]):
            continue  # ④安全侧：注入污染块整块拒抽""",
    """    for block in blocks:
        title = chapter_titles.get(block.get("chapter"), "")
        if is_metatext(title=title, text_sample=block["text"]):
            # A9 修复（审计 R4）：B6「绝不静默丢弃」——跳过块登记（skipped_out 或调用方入 quarantine）
            if skipped_out is not None:
                skipped_out.append({"chapter": block.get("chapter"),
                                    "line_start": block.get("line_start"),
                                    "reason": "metatext"})
            continue  # ①R6 对应 stub 闸：元文本零抽取
        if has_embedded_instruction(block["text"]):
            if skipped_out is not None:
                skipped_out.append({"chapter": block.get("chapter"),
                                    "line_start": block.get("line_start"),
                                    "reason": "embedded_instruction"})
            continue  # ④安全侧：注入污染块整块拒抽""",
    "A9-skip-log")

# ---- A12: 恒真断言 ----
rep("cbb/smoke/run_smoke.py",
    """    check("漂移钩子（SHA 变更→stale）", any(s["record_id"].startswith("rec-entity")
                                          for s in stale) or len(stale) >= 0)""",
    """    # A12 修复（审计 R4）：删恒真子句 `or len(stale) >= 0`（该项原为空转）
    check("漂移钩子（SHA 变更→stale）", any(s["record_id"].startswith("rec-entity")
                                          for s in stale))""",
    "A12-vacuous")

# ---- C1: 账本行缓存 ----
rep("cbb/tools/ledger_chain.py",
    """    def _rows(self) -> list[dict]:
        return [json.loads(ln) for ln in
                self.path.read_text(encoding="utf-8").splitlines() if ln.strip()]""",
    """    def _rows(self) -> list[dict]:
        # C1 修复（审计 R4）：实例内缓存——原实现每次追加/查键全量重读解析（O(n²)）；
        # 单写者假设（跨进程并发写见审计 B1 挂账），本实例追加后缓存内同步续行
        if getattr(self, "_cache", None) is None:
            self._cache = [json.loads(ln) for ln in
                           self.path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        return self._cache""",
    "C1-cache")

rep("cbb/tools/ledger_chain.py",
    """        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\\n")
        return payload""",
    """        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\\n")
        if getattr(self, "_cache", None) is not None:
            self._cache.append(payload)
        return payload""",
    "C1-cache-append")

# ---- A13: 导出器端口默认对齐 ----
rep("cbb/tools/neo4j_export.py",
    """    ap.add_argument("--base", default=os.environ.get("NEO4J_HTTP", "http://localhost:7474"))""",
    """    # A13 修复（审计 R4）：与连续性巡检对齐——端口漂移记录（工单 §0④）现役 http=7695；
    # 原 7474 默认与巡检的 7695 同名变量两默认值，其一必错
    ap.add_argument("--base", default=os.environ.get("NEO4J_HTTP", "http://localhost:7695"))""",
    "A13-port")

print(f"✓ 全部 {len(done)} 处补丁落地：")
for t in done:
    print("  -", t)
