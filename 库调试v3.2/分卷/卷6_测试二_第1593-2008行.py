                "confidence": "高", "validity": {}}
        cmd_engine("append", tmp, json.dumps(good, ensure_ascii=False))
        st = json.loads((tmp / "state.json").read_text(encoding="utf-8"))
        assert st["merkle_root"] == merkle_root(tmp, exclude={"state.json"}), "append 后根未刷新"
        (tmp / "memory" / "longterm" / "r1.json").unlink()
        # 模拟 retire 生效后链变化：直接 retire 空转也刷根
        import io as _io, contextlib
        with contextlib.redirect_stdout(_io.StringIO()): cmd_engine("retire", tmp)
        st = json.loads((tmp / "state.json").read_text(encoding="utf-8"))
        assert st["merkle_root"] == merkle_root(tmp, exclude={"state.json"}), "retire 后根未刷新"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

@t
def t_reinstall_without_data():
    """v3.3/Y-002：无 bodies 的 cwd 对已装库重跑 install → 校验模式可达（不报 C-001）"""
    import io as _io, contextlib
    tmp = _tmpdir("_bsv3t_y2"); fake_cwd = _tmpdir("_bsv3t_y2cwd")
    bak = BODIES_FILE.with_suffix(".json.bak")
    real_cwd = os.getcwd()
    try:
        cmd_install("L2", [], tmp, True)
        os.chdir(fake_cwd)  # 无 bootstrap_data 的 cwd
        if BODIES_FILE.exists(): BODIES_FILE.rename(bak)
        try:
            buf = _io.StringIO()
            with contextlib.redirect_stdout(buf): cmd_install("L2", [], tmp, True)
            assert "校验模式" in buf.getvalue(), "已装库未进校验模式"
            assert "C-001" not in buf.getvalue()
        finally:
            os.chdir(real_cwd)
            if bak.exists(): bak.rename(BODIES_FILE)
    finally:
        shutil.rmtree(tmp, ignore_errors=True); shutil.rmtree(fake_cwd, ignore_errors=True)

@t
def t_reinstall_no_false_unregistered():
    """v3.3/Y-003：运行时面不报未在册；渲染件手改必报（公理 B）"""
    import io as _io, contextlib
    tmp = _tmpdir("_bsv3t_y3")
    try:
        cmd_install("L2", [], tmp, True)
        good = {"id": "m1", "created_at": "2026-09-06", "updated_at": "", "content": "x",
                "keywords": [], "links": [], "source_event_id": "gen", "importance": 1,
                "confidence": "高", "validity": {}}
        cmd_engine("append", tmp, json.dumps(good, ensure_ascii=False))  # 运行时文件：memory/intermediate/m1.json
        (tmp / "外来文件.md").write_text("sneaky", encoding="utf-8")  # 真外来：根目录散文件
        (tmp / "AGENTS.md").write_text("手改入口", encoding="utf-8")  # 渲染件手改
        buf = _io.StringIO()
        with contextlib.redirect_stdout(buf): cmd_install("L2", [], tmp, True)
        out = buf.getvalue()
        assert "m1.json" not in out, "运行时面被误报未在册"
        assert "外来文件.md" in out, "真外来文件漏报"
        assert "渲染件被改" in out and "AGENTS.md" in out, "渲染件手改未报"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

@t
def t_engine_str_path():
    """v3.3/Y-004：str 入参直调 engine 不崩"""
    tmp = _tmpdir("_bsv3t_y4")
    try:
        cmd_install("L2", [], tmp, True)
        good = {"id": "s1", "created_at": "2026-09-06", "updated_at": "", "content": "x",
                "keywords": [], "links": [], "source_event_id": "gen", "importance": 1,
                "confidence": "高", "validity": {}}
        cmd_engine("append", str(tmp), json.dumps(good, ensure_ascii=False))  # str 直调
        assert (tmp / "memory" / "intermediate" / "s1.json").exists()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

@t
def t_eval_retrieval():
    """v3.3/Y-005：golden 评测跑通并出基线"""
    import io as _io, contextlib
    tmp = _tmpdir("_bsv3t_y5")
    try:
        cmd_install("L2", [], tmp, True)
        mk = lambda i, c, kw: {"id": i, "created_at": "2026-09-06", "updated_at": "", "content": c,
                               "keywords": kw, "links": [], "source_event_id": "gen",
                               "importance": 6, "confidence": "高", "validity": {}}
        cmd_engine("append", tmp, json.dumps(mk("g1", "EPUB 清洗流水线", ["EPUB"]), ensure_ascii=False))
        cmd_engine("append", tmp, json.dumps(mk("g2", "哈希链审计", ["审计"]), ensure_ascii=False))
        qs = [{"query": "EPUB 清洗", "expected": ["g1"], "type": "lexical"},
              {"query": "哈希 审计", "expected": ["g2"], "type": "lexical"}]
        (tmp / "evals").mkdir(exist_ok=True)
        (tmp / "evals" / "golden_queries.json").write_text(json.dumps(qs, ensure_ascii=False), encoding="utf-8")
        buf = _io.StringIO()
        with contextlib.redirect_stdout(buf): cmd_engine("eval", tmp)
        out = buf.getvalue()
        assert "recall@5=1.0" in out and "MRR=1.0" in out, "评测基线异常: " + out
        base = json.loads((tmp / "evals" / "baseline.json").read_text(encoding="utf-8"))
        assert base["n"] == 2 and base["misses"] == []
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

@t
def t_guard_anchor():
    """v3.3/Y-006：锚定快照导出 + 篡改后对账必报不一致"""
    tmp = _tmpdir("_bsv3t_y6")
    try:
        cmd_install("L9", [], tmp, True)
        import io as _io, contextlib
        with contextlib.redirect_stdout(_io.StringIO()): cmd_guard(None, tmp, snapshot=True)
        snap = tmp / "anchor_snapshot.json"
        assert snap.exists(), "快照未导出"
        table = json.loads(snap.read_text(encoding="utf-8"))
        assert "__package__" in table and len(table) >= 2, "快照缺包自哈希或基准项"
        buf = _io.StringIO()
        with contextlib.redirect_stdout(buf): cmd_guard(None, tmp, anchor=snap)  # 未篡改 → 一致
        assert "不一致 0" in buf.getvalue()
        victim = [k for k in table if k != "__package__"][0]
        p = tmp / victim
        p.write_text(p.read_text(encoding="utf-8") + "\n<!-- tampered -->", encoding="utf-8")
        rejected = False
        try: cmd_guard(None, tmp, anchor=snap)
        except SystemExit as ex: rejected = True  # mismatch → exit 1
        assert rejected, "篡改后锚定对账未报警"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

@t
def t_bulk_import_note():
    """v3.3/Y-007：批量导入密度 → 反思触发提示带批量标注"""
    import io as _io, contextlib
    tmp = _tmpdir("_bsv3t_y7")
    try:
        cmd_install("L2", [], tmp, True)
        st_path = tmp / "state.json"
        st = json.loads(st_path.read_text(encoding="utf-8"))
        st["importance_accum"] = TUNABLES["reflect_importance_threshold"]["value"]
        st_path.write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        with (tmp / "ledger" / "changes.jsonl").open("a", encoding="utf-8") as fh:
            for i in range(12):
                fh.write(json.dumps({"ts": now, "action": "append", "detail": f"bulk{i}"}, ensure_ascii=False) + "\n")
        buf = _io.StringIO()
        with contextlib.redirect_stdout(buf): cmd_engine("wrapup", tmp)
        assert "批量导入累积" in buf.getvalue(), "批量标注缺失"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

@t
def t_large_entry():
    """v3.3/Y-009：大条目（>1MB）append 不崩"""
    tmp = _tmpdir("_bsv3t_big")
    try:
        cmd_install("L2", [], tmp, True)
        big = {"id": "big1", "created_at": "2026-09-06", "updated_at": "", "content": "长" * 600000,
               "keywords": [], "links": [], "source_event_id": "gen", "importance": 5,
               "confidence": "高", "validity": {}}
        cmd_engine("append", tmp, json.dumps(big, ensure_ascii=False))
        assert (tmp / "memory" / "intermediate" / "big1.json").stat().st_size > 1024 * 1024
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

@t
def t_memory_ledger_consistency():
    """v3.3/Y-009：账本 append 动作数 == memory 条目文件数（双面守恒）"""
    tmp = _tmpdir("_bsv3t_con")
    try:
        cmd_install("L2", [], tmp, True)
        for i in range(5):
            e = {"id": f"c{i}", "created_at": "2026-09-06", "updated_at": "", "content": "x",
                 "keywords": [], "links": [], "source_event_id": "gen", "importance": 1,
                 "confidence": "高", "validity": {}}
            cmd_engine("append", tmp, json.dumps(e, ensure_ascii=False))
        n_mem = len(list((tmp / "memory").rglob("*.json")))
        n_app = sum(1 for l in (tmp / "ledger" / "changes.jsonl").read_text(encoding="utf-8").splitlines()
                    if json.loads(l).get("action") == "append")
        assert n_mem == n_app == 5, f"守恒失败: memory={n_mem} ledger_append={n_app}"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

@t
def t_build_docs_refreshes_render():
    """v3.4/H-001：build-docs --lib 刷新 AGENTS/README，校验模式渲染件清零"""
    import io as _io, contextlib
    tmp = _tmpdir("_bsv3t_h1")
    try:
        cmd_install("L2", [], tmp, True)
        ag = tmp / "AGENTS.md"; ag.write_text(ag.read_text(encoding="utf-8") + "\n<!-- 旧版本残留 -->", encoding="utf-8")
        buf = _io.StringIO()
        with contextlib.redirect_stdout(buf): cmd_build(tmp, tmp)  # --lib 刷新
        assert "AGENTS.md" in buf.getvalue(), "build-docs --lib 未刷渲染件"
        buf = _io.StringIO()
        with contextlib.redirect_stdout(buf): cmd_install("L2", [], tmp, True)
        assert "渲染件被改 0" in buf.getvalue(), "刷新后仍报渲染件被改"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

@t
def t_host_trace_env_line():
    """v3.4/H-002(D1=a)：宿主目录 .v2c 报环境痕迹、不进未在册"""
    import io as _io, contextlib
    tmp = _tmpdir("_bsv3t_h2")
    try:
        cmd_install("L2", [], tmp, True)
        (tmp / ".v2c").mkdir(); (tmp / ".v2c" / "plugin_root").write_text("x", encoding="utf-8")
        buf = _io.StringIO()
        with contextlib.redirect_stdout(buf): cmd_install("L2", [], tmp, True)
        out = buf.getvalue()
        assert "环境痕迹" in out and "plugin_root" in out, "宿主痕迹未被报告"
        assert "未在册 0" in out, "宿主痕迹泄漏进未在册计数"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

@t
def t_reflect_materials():
    """v3.4/H-003：reflect 取材打包器产出素材文件"""
    import io as _io, contextlib
    tmp = _tmpdir("_bsv3t_h3")
    try:
        cmd_install("L2", [], tmp, True)
        st_path = tmp / "state.json"
        st = json.loads(st_path.read_text(encoding="utf-8"))
        st["importance_accum"] = TUNABLES["reflect_importance_threshold"]["value"]
        st_path.write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")
        e = {"id": "m1", "created_at": "2026-09-06", "updated_at": "", "content": "高重要度经验",
             "keywords": [], "links": [], "source_event_id": "gen", "importance": 9,
             "confidence": "高", "validity": {}}
        cmd_engine("append", tmp, json.dumps(e, ensure_ascii=False))
        buf = _io.StringIO()
        with contextlib.redirect_stdout(buf): cmd_engine("reflect", tmp)
        assert "素材已打包" in buf.getvalue()
        mat = list((tmp / "memory" / "reflect").glob("materials-*.md"))[0].read_text(encoding="utf-8")
        assert "触发原因" in mat and "m1" in mat and "无据不写" in mat
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

@t
def t_absorb_md_dryrun():
    """v3.4/H-004：absorb-md 收编——mini v4 源树 dry-run 解析对账"""
    import io as _io, contextlib
    tmp = _tmpdir("_bsv3t_h4"); src = tmp / "v4src"
    (src / "knowledge").mkdir(parents=True)
    (src / "knowledge" / "pitfalls.md").write_text(
        "# P\n\n### P-901 / 2026-09-06 / 测试教训\n- 教训：测试性教训内容\n- 关键词：测试、迁移\n- 状态：active\n", encoding="utf-8")
    (src / "knowledge" / "patterns.md").write_text(
        "# PT\n\n### PT-901 / 2026-09-06 / 测试范式\n- 核心步骤：测试范式内容\n- 状态：active\n\n### PT-001 / {日期} / {模式名}\n", encoding="utf-8")
    buf = _io.StringIO()
    with contextlib.redirect_stdout(buf): cmd_absorb_md(src, tmp / "lib", dry_run=True)
    out = buf.getvalue()
    assert "解析 2 条" in out and "模板跳过 1" in out and "dry-run" in out, "dry-run 对账异常: " + out
    assert not (tmp / "lib" / "memory").exists(), "dry-run 不应写入"
    with contextlib.redirect_stdout(_io.StringIO()): cmd_absorb_md(src, tmp / "lib", dry_run=False)
    assert (tmp / "lib" / "memory" / "longterm" / "P-901.json").exists()
    assert (tmp / "lib" / "memory" / "intermediate" / "TRAJ-001.json").exists() is False  # 无轨迹目录则无索引条目
    assert (tmp / "lib" / "memory" / "longterm" / "SOUL-POINTER.json").exists()

@t
def t_golden_shipped():
    """v3.4/H-005：golden 评测集随包落 evals/ 且 eval 直接跑通"""
    import io as _io, contextlib
    tmp = _tmpdir("_bsv3t_h5")
    try:
        set_data_dir(tmp / "pkgdata")  # 造包数据：bodies.json（最小）+ evals/golden_queries.json
        (DATA_DIR / "evals").mkdir(parents=True, exist_ok=True)
        (DATA_DIR / "bodies.json").write_text(json.dumps({"docs": {"SKILL.md": {"body": "# skill", "src": "SKILL.md", "sha256": "x"}}}), encoding="utf-8")
        qs = [{"query": "哈希", "expected": ["gg1"], "type": "lexical"}]
        (DATA_DIR / "evals" / "golden_queries.json").write_text(json.dumps(qs, ensure_ascii=False), encoding="utf-8")
        cmd_install("L2", [], tmp, True)
        set_data_dir(Path.cwd() / "bootstrap_data")  # 还原
        assert (tmp / "evals" / "golden_queries.json").exists(), "golden 集未随包落盘"
        good = {"id": "gg1", "created_at": "2026-09-06", "updated_at": "", "content": "哈希链",
                "keywords": ["哈希"], "links": [], "source_event_id": "gen", "importance": 7,
                "confidence": "高", "validity": {}}
        cmd_engine("append", tmp, json.dumps(good, ensure_ascii=False))
        buf = _io.StringIO()
        with contextlib.redirect_stdout(buf): cmd_engine("eval", tmp)
        out = buf.getvalue()
        assert "recall@5=1.0" in out and "参照线" in out, "eval 增强缺失: " + out
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        set_data_dir(Path.cwd() / "bootstrap_data")

@t
def t_doctor():
    """v3.4/H-006：doctor 三方对账——孤儿条目精确报告"""
    import io as _io, contextlib
    tmp = _tmpdir("_bsv3t_h6")
    try:
        cmd_install("L2", [], tmp, True)
        good = {"id": "d1", "created_at": "2026-09-06", "updated_at": "", "content": "x",
                "keywords": [], "links": [], "source_event_id": "gen", "importance": 1,
                "confidence": "高", "validity": {}}
        cmd_engine("append", tmp, json.dumps(good, ensure_ascii=False))
        # 模拟中断：删 audit 中的 entry 行（篡改审计面后 doctor 应报 memory 有而 audit 无）
        ap = list((tmp / "audit").glob("lifelog-*.md"))[0]
        lines = [l for l in ap.read_text(encoding="utf-8").splitlines() if "entry:d1" not in l]
        ap.write_text("\n".join(lines) + "\n", encoding="utf-8")
        buf = _io.StringIO()
        with contextlib.redirect_stdout(buf): cmd_engine("doctor", tmp)
        out = buf.getvalue()
        assert "memory有而audit无" in out and "d1" in out, "doctor 未报孤儿条目: " + out
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

@t
def t_append_rejects_dup_id():
    """v3.5/J-001：同 id 二次 append 必须拒绝（写入路径不覆盖）"""
    tmp = _tmpdir("_bsv3t_j1")
    try:
        cmd_install("L2", [], tmp, True)
        e = {"id": "dup1", "created_at": "2026-09-07", "updated_at": "", "content": "第一版",
             "keywords": [], "links": [], "source_event_id": "gen", "importance": 1,
             "confidence": "高", "validity": {}}
        cmd_engine("append", tmp, json.dumps(e, ensure_ascii=False))
        rejected = False
        try: cmd_engine("append", tmp, json.dumps(dict(e, content="第二版"), ensure_ascii=False))
        except SystemExit as ex: rejected = "已存在" in str(ex)
        assert rejected, "同 id 覆盖未被拒绝"
        body = json.loads((tmp / "memory" / "intermediate" / "dup1.json").read_text(encoding="utf-8"))
        assert body["content"] == "第一版", "原条目被覆盖"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

@t
def t_deliver_skips_removed():
    """v3.5/J-002：bodies removed 槽不参与交付"""
    tmp = _tmpdir("_bsv3t_j2")
    try:
        b = load_bodies()
        b["removed"] = {"modules__m-core__template__GHOST.md":
                        {"body": "# ghost", "src": "modules/m-core/template/GHOST.md", "sha256": "x"}}
        save_bodies(b)
        cmd_install("L2", [], tmp, True)
        assert not (tmp / "modules" / "m-core" / "template" / "GHOST.md").exists(), "已删除文件复活"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

@t
def t_verify_overrides_applied():
    """v3.5/J-003：--fix 写 overrides → 二次 verify 应用并 match（对账裁决闭环）"""
    import io as _io, contextlib
    tmp = _tmpdir("_bsv3t_j3")
    real_urlopen = urllib.request.urlopen
    real_data = str(DATA_DIR)
    xml = "<?xml?><feed><title>q</title><title>Mocked Test Title</title></feed>"
    def _mock(*a, **k): return _io.BytesIO(xml.encode("utf-8"))
    try:
        set_data_dir(tmp / "pkgdata")  # 隔离：overrides 写入测试目录
        (DATA_DIR / "evals").mkdir(parents=True, exist_ok=True)
        (DATA_DIR / "bodies.json").write_text("{}", encoding="utf-8")
        urllib.request.urlopen = _mock
        try:
            buf = _io.StringIO()
            with contextlib.redirect_stdout(buf):
                try: cmd_verify(fix=True, throttle=False)
                except SystemExit as ex: assert ex.code == 1, "N-001：mismatch 应 exit 1"
            assert "不一致 24" in buf.getvalue()
            buf = _io.StringIO()
            with contextlib.redirect_stdout(buf): cmd_verify(fix=False, throttle=False)
            out = buf.getvalue()
            assert "一致 24" in out and "overrides" in out, "overrides 未进账: " + out[:200]
            rep = json.loads((tmp / "pkgdata" / "verify_report.json").read_text(encoding="utf-8"))
            assert all(v.get("via") == "override" for v in rep.values())
        finally:
            urllib.request.urlopen = real_urlopen
    finally:
        set_data_dir(real_data); shutil.rmtree(tmp, ignore_errors=True)

@t
def t_build_docs_lib_default_out():
    """v3.5/J-004+005：--lib 模式渲染产物默认落库 + state 随包升级"""
    tmp = _tmpdir("_bsv3t_j4")
    try:
        cmd_install("L2", [], tmp, True)
        cmd_build(None, tmp)  # out=None + lib → 全部渲染件落库
        assert (tmp / "spec.md").exists() and (tmp / "citations.md").exists()
        st = json.loads((tmp / "state.json").read_text(encoding="utf-8"))
        assert st["version"] == VERSION and st["package_sha256"] == self_hash(), "state 未随包升级"
        assert st["merkle_root"] == merkle_root(tmp, exclude={"state.json"})
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

@t
def t_entrypoint_lists_new_commands():
    """v3.5/J-006：入口命令清单覆盖 v3 全命令面"""
    tmp = _tmpdir("_bsv3t_j5")
    try:
        cmd_install("L2", [], tmp, True)
        ag = (tmp / "AGENTS.md").read_text(encoding="utf-8")
        for kw in ("engine eval", "engine reflect", "engine doctor", "guard --diff"):
            assert kw in ag, f"入口缺命令 {kw}"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

@t
def t_migrate_hints_eval():
    """v3.5/J-007：migrate 输出含 engine eval 下一步"""
    import io as _io, contextlib
    tmp = _tmpdir("_bsv3t_j6")
    try:
        lg = tmp / "knowledge" / "lifelog"; lg.mkdir(parents=True)
        (lg / "2026-08.mdl").write_text("2026-08-31 | L8 | aaaabbbbccccdddd | 0123456789abcdef" + chr(10), encoding="utf-8")
        buf = _io.StringIO()
        with contextlib.redirect_stdout(buf): cmd_migrate(tmp)
        assert "engine eval" in buf.getvalue()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

@t
def t_experimental_adapter_page():
    """v3.5/J-008a(D1=a)：experimental install.md 注入 v3 语境适配页"""
    tmp = _tmpdir("_bsv3t_j7")
    try:
        cmd_install("L9", [], tmp, True)
        ims = list((tmp / "experimental-l8").rglob("install.md"))  # v3.7/L-008：全量渲染化后 install.md 一律渲染
        assert ims and all("渲染产物" in q.read_text(encoding="utf-8")[:120] for q in ims), "install.md 未全量渲染化"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

@t
def t_reflect_synthesis_shipped():
    """v3.5/J-009：reflect 合成提示词随包（L5+）"""
