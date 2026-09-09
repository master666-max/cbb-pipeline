# 自测（T 号自注册；断言=行为，非文档措辞）
# ────────────────────────────────────────────────────────────────────
TESTS = []
def t(fn): TESTS.append(fn); return fn

def _tmpdir(prefix: str) -> Path:
    return Path(tempfile.mkdtemp(prefix=prefix))  # BR-4：Windows 无 /tmp 依赖

@t
def t_chain_and_cross_month():
    tmp = _tmpdir("_bsv3t_chain")
    try:
        h1 = chain_append(tmp / "audit", "line1")
        time.sleep(0.01); h2 = chain_append(tmp / "audit", "line2")
        assert h1 != h2
        first = sorted((tmp / "audit").glob("lifelog-*.md"))[0].read_text().splitlines()[0]
        assert "genesis" in first or "prev:" in first
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

@t
def t_chain_tamper_detected():
    tmp = _tmpdir("_bsv3t_tamper")
    try:
        chain_append(tmp / "audit", "real event")
        f = sorted((tmp / "audit").glob("lifelog-*.md"))[0]
        f.write_text(f.read_text().replace("real", "fake"), encoding="utf-8")
        line = f.read_text(encoding="utf-8").strip().splitlines()[0]
        m = re.search(r"prev:(\S+) \| h:([0-9a-f]{64}) \| (.*)$", line)  # v3.1/V-007②：验证对账必不匹配
        assert m, "行格式解析失败"
        prev, h_stored, text = (m.group(1) if m.group(1) != "genesis" else ""), m.group(2), m.group(3)
        assert line_hash(prev, text) != h_stored, "篡改后重算哈希竟然仍匹配——对账失效"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

@t
def t_schema_rejects_missing_source():
    assert validate_entry({"id": "x", "content": "hi", "created_at": "2026-01-01"}) != []

@t
def t_law5_secret_scan():
    assert any("密钥" in e for e in validate_entry({"id": "x", "content": "sk-AAAAAAAAAAAAAAAAAAAAAA",
        "created_at": "2026-01-01", "source_event_id": "e1", "updated_at": "", "importance": 1,
        "confidence": "S", "validity": {}}))

@t
def t_dag_cycle_rejected():
    """BR-3：真环断言——把环注入 L2 可达模块，resolve 必须拒绝并列出环"""
    old = dict(DEPS)
    DEPS["m-search"] = ["m-lint"]; DEPS["m-lint"] = ["m-search"]
    try:
        try:
            resolve("L2", []); raised = False
        except SystemExit as ex:
            raised = "依赖环" in str(ex) and "m-search" in str(ex)
    finally:
        DEPS.clear(); DEPS.update(old)
    assert raised, "L2 可达环未被拒绝"

@t
def t_escape_pod_wording():
    assert "删" not in ESCAPE_POD and "attic" in ESCAPE_POD          # P0-4/BR-8 根治
    assert "回退一律移 attic" in CHARTER_L8                            # 逃生舱措辞=移 attic（BR-8：DGM 立法说明的事实性引文允许出现「删除」，回退措辞不允许）

@t
def t_no_handwritten_counts():
    qr = render_quickref(0)
    assert "30/30" not in qr and "58" not in qr and "38" not in qr   # 38/58 病灶灭绝

@t
def t_registry_corrected():
    assert REGISTRY["A14"]["authors"][0] == "Jiazheng Kang"           # F4 根治
    assert "Memory-Augmented Generation" in REGISTRY["A20"]["title"]
    assert "Chroma" in REGISTRY["A25"]["venue"]                        # context rot 归属
    assert "Zhiyu Li" in REGISTRY["A16"]["authors_first"]
    assert "A33" in REGISTRY                                           # 第五项理论补齐
    assert "objective hacking" in CHARTER_L8                           # 核-02/引文纪律
    assert REGISTRY["A22"]["arxiv_id"] == "2507.21046"                 # BR-2 编号修复
    assert not REGISTRY["A28"].get("arxiv_id")                         # BR-2 A28=doc 型
    assert REGISTRY["A31"]["year"] == 1994                             # BR-5
    assert REGISTRY["A14"].get("doi") and REGISTRY["A14"].get("github")  # M-10 消歧字段
    assert len(REGISTRY) == 33 and all(m.get("status") == "verified" for m in REGISTRY.values())  # v3.2/C-013：pending 退役
    assert sum(1 for m in REGISTRY.values() if m.get("arxiv_id")) == 24  # 口径 24 篇

@t
def t_install_requires_bodies():
    """v3.2/C-001：bodies 为空时 install 拒绝产出空库"""
    tmp = _tmpdir("_bsv3t_nob"); bak = BODIES_FILE.with_suffix(".json.bak")
    try:
        if BODIES_FILE.exists(): BODIES_FILE.rename(bak)
        try:
            cmd_install("L2", [], tmp, True); refused = False
        except SystemExit as ex:
            refused = "absorb" in str(ex)
        assert refused, "空 bodies 未被拒绝"
    finally:
        if bak.exists(): bak.rename(BODIES_FILE)
        shutil.rmtree(tmp, ignore_errors=True)

@t
def t_merkle_root_consistency():
    """v3.2/C-002：install 根口径与重算一致（排除 state.json，含渲染件）"""
    tmp = _tmpdir("_bsv3t_root")
    try:
        cmd_install("L2", [], tmp, True)
        st = json.loads((tmp / "state.json").read_text(encoding="utf-8"))
        assert st["merkle_root"] == merkle_root(tmp, exclude={"state.json"}), "install 根与重算不一致"
        assert (tmp / "spec.md").exists() and (tmp / "AGENTS.md").exists() and (tmp / "citations.md").exists()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

@t
def t_reinstall_reports_unregistered():
    """v3.2/C-004：校验模式报未在册新文件与根不一致"""
    import io as _io, contextlib
    tmp = _tmpdir("_bsv3t_unreg")
    try:
        cmd_install("L2", [], tmp, True)
        (tmp / "sneaky.json").write_text("{}", encoding="utf-8")  # v3.3/Y-003 口径：根目录散文件才算未在册
        (tmp / "AGENTS.md").write_text("TAMPERED", encoding="utf-8")
        buf = _io.StringIO()
        with contextlib.redirect_stdout(buf): cmd_install("L2", [], tmp, True)
        out = buf.getvalue()
        assert "未在册" in out and "sneaky.json" in out, "未在册新文件未被报告"
        assert "根不一致" in out, "被改文件未被根对账捕获"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

@t
def t_ledger_changes():
    """v3.2/C-005：公理 C 落地——install/append/wrapup 全部入 changes.jsonl"""
    tmp = _tmpdir("_bsv3t_led")
    try:
        cmd_install("L2", [], tmp, True)
        good = {"id": "e1", "created_at": "2026-09-06", "updated_at": "", "content": "x",
                "keywords": ["x"], "links": [], "source_event_id": "gen", "importance": 1,
                "confidence": "高", "validity": {}}
        cmd_engine("append", tmp, json.dumps(good, ensure_ascii=False))
        import io as _io, contextlib
        with contextlib.redirect_stdout(_io.StringIO()): cmd_engine("wrapup", tmp)
        lines = (tmp / "ledger" / "changes.jsonl").read_text(encoding="utf-8").strip().splitlines()
        acts = [json.loads(l)["action"] for l in lines]
        assert acts[0] == "install" and "append" in acts and "wrapup" in acts, f"账本缺动作: {acts}"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

@t
def t_guard_rejects_baseline_touch():
    """v3.2/C-006：guard 对触碰基准黑名单的变异 diff 必须否决"""
    tmp = _tmpdir("_bsv3t_guard")
    try:
        cmd_install("L2", [], tmp, True)
        cand = tmp / "mutations" / "candidates" / "MUT-001"; cand.mkdir(parents=True)
        (cand / "run_tests.txt").write_text("# tampered benchmark", encoding="utf-8")
        (cand / "DIFF.md").write_text("改了别的", encoding="utf-8")
        rejected = False
        try: cmd_guard(str(cand), tmp)
        except SystemExit as ex: rejected = "否决" in str(ex) and "run_tests" in str(ex)
        assert rejected, "触碰基准的 diff 未被 guard 否决"
        clean = tmp / "mutations" / "candidates" / "MUT-002"; clean.mkdir(parents=True)
        (clean / "DIFF.md").write_text("只改了普通模板", encoding="utf-8")
        import io as _io, contextlib
        buf = _io.StringIO()
        with contextlib.redirect_stdout(buf): cmd_guard(str(clean), tmp)
        assert "通过" in buf.getvalue()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

@t
def t_reflect_trigger():
    """v3.2/C-007：importance_accum 越线 → wrapup 输出反思触发"""
    import io as _io, contextlib
    tmp = _tmpdir("_bsv3t_refl")
    try:
        cmd_install("L2", [], tmp, True)
        st_path = tmp / "state.json"
        st = json.loads(st_path.read_text(encoding="utf-8"))
        st["importance_accum"] = TUNABLES["reflect_importance_threshold"]["value"]
        st_path.write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")
        buf = _io.StringIO()
        with contextlib.redirect_stdout(buf): cmd_engine("wrapup", tmp)
        assert "反思触发" in buf.getvalue(), "越线未触发反思提示"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

@t
def t_retrieve_keywords_boost():
    """v3.2/C-010：keywords 命中 ×3 加权与 [[links]] 一跳扩散"""
    import io as _io, contextlib
    tmp = _tmpdir("_bsv3t_kw")
    try:
        cmd_install("L2", [], tmp, True)
        mk = lambda i, c, kw, ln: {"id": i, "created_at": "2026-09-06", "updated_at": "", "content": c,
                                   "keywords": kw, "links": ln, "source_event_id": "gen",
                                   "importance": 5, "confidence": "高", "validity": {}}
        cmd_engine("append", tmp, json.dumps(mk("kw1", "正文没提检索词", ["哈希链"], []), ensure_ascii=False))
        cmd_engine("append", tmp, json.dumps(mk("kw2", "正文提到哈希链", [], []), ensure_ascii=False))
        cmd_engine("append", tmp, json.dumps(mk("hub", "别的主题", ["枢纽"], ["kw1"]), ensure_ascii=False))
        buf = _io.StringIO()
        with contextlib.redirect_stdout(buf): cmd_engine("retrieve", tmp, "哈希链", k=5)
        out = buf.getvalue()
        pos_kw1 = out.find("kw1"); pos_kw2 = out.find("kw2")
        assert 0 <= pos_kw1 < pos_kw2, "keywords ×3 加权未生效（kw1 应排在 kw2 前）"
        assert "hub" in out, "[[links]] 一跳扩散未把 hub 带回"
        assert "投毒防线" in out
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

@t
def t_entrypoint_rendered():
    """v3.2/C-000(D1=a)：v3 原生入口/技能/README 渲染 + 新增包模板"""
    tmp = _tmpdir("_bsv3t_ep")
    try:
        cmd_install("L4", ["x-game"], tmp, True)
        ag = (tmp / "AGENTS.md").read_text(encoding="utf-8")
        assert "三级" in ag and "永不删除" in ag and "L4" in ag, "入口渲染缺铁律或档位"
        assert (tmp / "skills" / "wrap-up.md").exists() and (tmp / "skills" / "task-start.md").exists()
        assert " adaptation" in (tmp / "skills" / "wrap-up.md").read_text(encoding="utf-8")
        pkg = tmp / "packs" / "x-game" / "README.md"
        assert pkg.exists() and "账本状态机" in pkg.read_text(encoding="utf-8"), "新增包模板未渲染"
        assert (tmp / "citations.md").exists()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

@t
def t_l8_guards():
    """三守卫语义落点：宪章含豁免/不可见/objective hacking；内容体含真实 MUTATION-SOP"""
    assert "豁免" in CHARTER_L8 and "不可见" in CHARTER_L8 and "objective hacking" in CHARTER_L8
    b = load_bodies()
    sop_keys = [k for k in b.get("modules", {}) if "MUTATION-SOP" in k]
    assert sop_keys, "bodies 缺 MUTATION-SOP 内容体（先跑 absorb）"
    sop = b["modules"][sop_keys[0]]["body"]
    assert "BENCHMARK" in sop and "否决" in sop, "MUTATION-SOP 缺基准/否决条款"
    # v2.x SOP 尚无「不可见条款」（内容体冻结遗留）——守卫由宪章第 2/4 段承担；SOP 升级为 v3.1 内容体项
    assert "不可见" in CHARTER_L8 and "SOP 条款守卫" in CHARTER_L8

@t
def t_install_l2_smoke():
    tmp = _tmpdir("_bsv3t_l2")
    try:
        cmd_install("L2", [], tmp, True)
        st = json.loads((tmp / "state.json").read_text(encoding="utf-8"))
        assert st["level"] == "L2" and "m-lint" in st["modules"] and "m-search" in st["modules"]
        assert st["package_sha256"] == self_hash()
        assert (tmp / "spec.md").exists() and (tmp / "提示词速查.md").exists()
        assert len(st["merkle_root"]) == 64  # v3.1/V-007①：替换原恒真断言，install 即写 256bit 根
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

@t
def t_install_delivers_bodies():
    """v3.1/V-001+V-002：install 真实落盘内容体（含特色包映射）"""
    tmp = _tmpdir("_bsv3t_del")
    try:
        cmd_install("L2", ["x-roleplay"], tmp, True)
        mf = json.loads((tmp / ".library-manifest.json").read_text(encoding="utf-8"))
        assert mf["hash_algo"] == "sha256-16" and len(mf["files"]) >= 10, "交付清单过小——内容体未落地"
        assert "SKILL.md" in mf["files"] and "presets/L2.md" in mf["files"]
        for rel, h in mf["files"].items():
            p = tmp / rel
            assert p.exists() and hashlib.sha256(p.read_bytes()).hexdigest()[:16] == h, f"交付漂移: {rel}"
        assert any("m-tools" in rel for rel in mf["files"]), "L2 模块 m-tools 未交付"
        assert any("packs/x-rp" in rel for rel in mf["files"]), "特色包 x-rp 未交付（PACKAGE_MAPPING 失效）"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

@t
def t_verify_offline_honest():
    """v3.1/V-003：离线时 error=未对账，不许显示误导性的零不一致"""
    import io as _io, contextlib
    real_urlopen = urllib.request.urlopen
    real_cwd = os.getcwd()  # v3.1 首跑教训：chdir 不恢复会污染后续所有相对路径测试
    def _boom(*a, **k): raise IOError("simulated offline")
    tmp = _tmpdir("_bsv3t_ver")
    try:
        os.chdir(tmp)
        urllib.request.urlopen = _boom
        try:
            buf = _io.StringIO()
            with contextlib.redirect_stdout(buf): cmd_verify(False)
        finally:
            urllib.request.urlopen = real_urlopen; os.chdir(real_cwd)
        out = buf.getvalue()
        assert "未对账" in out and "一致 0" in out, "离线语义未如实呈现"
        rep = json.loads((tmp / "bootstrap_data" / "verify_report.json").read_text(encoding="utf-8"))
        assert all(v.get("status") == "error" for v in rep.values()), "error 未三态标注"
    finally:
        os.chdir(real_cwd); shutil.rmtree(tmp, ignore_errors=True)

@t
def t_retrieve_bad_ts():
    """v3.1/V-004：坏时间戳单条降级，检索不全库崩溃"""
    import io as _io, contextlib
    tmp = _tmpdir("_bsv3t_ts")
    try:
        cmd_install("L2", [], tmp, True)
        good = {"id": "g1", "created_at": "2026-09-06", "updated_at": "", "content": "跨月续接规则",
                "keywords": ["跨月"], "links": [], "source_event_id": "gen", "importance": 8,
                "confidence": "高", "validity": {}}
        cmd_engine("append", tmp, json.dumps(good, ensure_ascii=False))
        bad = dict(good, id="b1", created_at="不是日期")
        (tmp / "memory" / "longterm" / "b1.json").write_text(json.dumps(bad, ensure_ascii=False), encoding="utf-8")
        buf = _io.StringIO()
        with contextlib.redirect_stdout(buf): cmd_engine("retrieve", tmp, "跨月")
        out = buf.getvalue()
        assert "跨月续接" in out and "bad-ts" in out and "投毒防线" in out
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

@t
def t_retire_ttl():
    """v3.1/V-013：失效超 TTL 条目移入 attic（留痕不销毁）"""
    tmp = _tmpdir("_bsv3t_ret")
    try:
        cmd_install("L2", [], tmp, True)
        e = {"id": "old1", "created_at": "2026-09-06", "updated_at": "", "content": "过时条目",
             "source_event_id": "gen", "importance": 3, "confidence": "高",
             "validity": {"t_valid": "2026-01-01", "t_invalid": "2026-01-01"}}
        (tmp / "memory" / "intermediate" / "old1.json").write_text(json.dumps(e, ensure_ascii=False), encoding="utf-8")
        cmd_engine("retire", tmp)
        assert not (tmp / "memory" / "intermediate" / "old1.json").exists()
        assert (tmp / "memory" / "attic" / "old1.json").exists(), "retire 未落 attic"
        audit = (tmp / "audit").glob("lifelog-*.md").__iter__().__next__().read_text(encoding="utf-8")
        assert "retire" in audit
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

@t
def t_install_l8_gate():
    tmp = _tmpdir("_bsv3t_l8")
    try:
        gated = False
        try: cmd_install("L8", [], tmp, False)
        except SystemExit as ex: gated = "人类令牌" in str(ex) and "CONSTITUTION" in str(ex)
        assert gated, "L8 无 --yes 未被慢车道拦截"
        cmd_install("L8", [], tmp, True)
        assert json.loads((tmp / "state.json").read_text(encoding="utf-8"))["level"] == "L8"
        audit = list((tmp / "audit").glob("lifelog-*.md"))[0].read_text(encoding="utf-8")
        assert "M-003 charter-confirmed" in audit, "v3.1/V-006 人类令牌未留痕"
        sop = [p for p in (tmp / "experimental-l8").rglob("*MUTATION-SOP*") if p.is_file()]
        assert sop and "不可见条款" in sop[0].read_text(encoding="utf-8"), "v3.1/V-008 SOP 守卫段未注入"
        assert (tmp / "references" / "referee.md").exists(), "v3.1/V-009 referee 未落盘"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

@t
def t_migrate_mdl():
    """BR-1：v2.x 存量链（knowledge/lifelog/*.mdl，截 16 hex 竖线格式）续接；重复迁移拒绝"""
    tmp = _tmpdir("_bsv3t_mig")
    try:
        lg = tmp / "knowledge" / "lifelog"; lg.mkdir(parents=True)
        (lg / "2026-08.mdl").write_text(
            "2026-08-30 | 创世 | 0000000000000000 | aaaabbbbccccdddd\n"
            "2026-08-31 | L8装毕 | aaaabbbbccccdddd | 0123456789abcdef\n", encoding="utf-8")
        cmd_migrate(tmp)
        mig = sorted((tmp / "audit").glob("lifelog-*.md"))[0].read_text(encoding="utf-8")
        assert "prev:0123456789abcdef" in mig and "M-002" in mig, "续接行未引用 legacy 尾哈希"
        twice = False
        try: cmd_migrate(tmp)
        except SystemExit as ex: twice = "勿重复 migrate" in str(ex)
        assert twice, "v3.1/V-012 重复迁移未被拒绝"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

@t
def t_absorb_mapping():
    assert BODIES_FILE.exists(), "先跑 absorb"
    b = load_bodies()
    assert any("SKILL.md" in k for k in b.get("docs", {})), "docs 槽缺 SKILL.md"
    assert any(k.endswith("L9.md") for k in b.get("presets", {})), "presets 槽缺 L9"
    lm = json.loads((DATA_DIR / "level_mapping.json").read_text(encoding="utf-8"))
    assert set(lm["mapping"]) == set(MODULE_MAPPING), "level_mapping 与 MODULE_MAPPING 不一致"
    assert set(lm.get("package_mapping", {})) == set(PACKAGE_MAPPING), "v3.1/V-002 包映射未入 level_mapping"
    assert any(k.startswith("packs__x-rp") for k in b.get("packages", {})), "packages 槽缺 x-rp（v2.x 目录名）"

@t
def t_engine_lifecycle():
    tmp = _tmpdir("_bsv3t_eng")
    try:
        cmd_install("L2", [], tmp, True)
        good = {"id": "e1", "created_at": "2026-09-06", "updated_at": "", "content": "哈希链跨月续接",
                "keywords": ["哈希链"], "links": [], "source_event_id": "gen", "importance": 8,
                "confidence": "高", "validity": {}}
        cmd_engine("append", tmp, json.dumps(good, ensure_ascii=False))
        assert (tmp / "memory" / "longterm" / "e1.json").exists()
        st = json.loads((tmp / "state.json").read_text(encoding="utf-8"))
        assert st["importance_accum"] == 8, "v3.1/V-015 importance 累计器失效"
        for bad, why in [({k: v for k, v in good.items() if k != "source_event_id"}, "缺证据锚"),
                         (dict(good, id="e2", content="sk-AAAAAAAAAAAAAAAAAAAAAA"), "密钥")]:
            rejected = False
            try: cmd_engine("append", tmp, json.dumps(bad, ensure_ascii=False))
            except SystemExit as ex: rejected = ("拒绝写入" in str(ex))
            assert rejected, f"{why} 未被 schema 拒绝"
        import io as _io, contextlib
        buf = _io.StringIO()
        with contextlib.redirect_stdout(buf): cmd_engine("retrieve", tmp, "哈希")
        assert "投毒防线" in buf.getvalue()
        st0 = (tmp / "state.json").read_text(encoding="utf-8")
        with contextlib.redirect_stdout(_io.StringIO()): cmd_engine("shadow", tmp, "试变更X")
        assert (tmp / "state.json").read_text(encoding="utf-8") == st0, "shadow 改了状态（违反公理G）"
        with contextlib.redirect_stdout(_io.StringIO()): cmd_engine("wrapup", tmp)
        st = json.loads((tmp / "state.json").read_text(encoding="utf-8"))
        assert set(st["emotion"]) == {"valence", "arousal", "certainty", "stakes"}, "v3.1/V-005 四维缺位"
        assert st["emotion"]["arousal"] == 0.35 and st["emotion"]["valence"] == 0.0  # 0.5×0.7；0×0.7
        assert len(st["merkle_root"]) == 64
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

@t
def t_root_refresh_on_write():
    """v3.3/Y-001：append/retire 后 state 根与重算一致（先 audit 后算根）"""
    tmp = _tmpdir("_bsv3t_y1")
    try:
        cmd_install("L2", [], tmp, True)
        good = {"id": "r1", "created_at": "2026-09-06", "updated_at": "", "content": "x",
                "keywords": [], "links": [], "source_event_id": "gen", "importance": 8,
