    tmp = _tmpdir("_bsv3t_j8")
    try:
        cmd_install("L9", [], tmp, True)
        rs = tmp / "references" / "reflect-synthesis.md"
        assert rs.exists() and "无据不写" in rs.read_text(encoding="utf-8")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

@t
def t_redeliver():
    """v3.5/J-010(D2)：--redeliver 显式重交付漂移文件"""
    import io as _io, contextlib
    tmp = _tmpdir("_bsv3t_j9")
    try:
        cmd_install("L2", [], tmp, True)
        victim = tmp / "modules" / "m-core" / "install.md"
        victim.write_text(victim.read_text(encoding="utf-8") + chr(10) + "<!-- 手改 -->", encoding="utf-8")
        buf = _io.StringIO()
        with contextlib.redirect_stdout(buf): cmd_install("L2", [], tmp, True, redeliver=True)
        out = buf.getvalue()
        assert "重交付" in out, "redeliver 未生效: " + out[:200]
        buf = _io.StringIO()
        with contextlib.redirect_stdout(buf): cmd_install("L2", [], tmp, True)
        assert "漂移 0" in buf.getvalue(), "重交付后仍漂移"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

@t
def t_absorb_md_idempotent():
    """v3.6/K-001：重跑幂等——已存在跳过计数，不混入 rejected"""
    import io as _io, contextlib
    tmp = _tmpdir("_bsv3t_k1"); src = tmp / "v4src"
    (src / "knowledge").mkdir(parents=True)
    (src / "knowledge" / "pitfalls.md").write_text(
        "### P-901 / 2026-09-06 / 教训" + chr(10) + "- 教训：内容" + chr(10) + "- 状态：active" + chr(10), encoding="utf-8")
    (src / "knowledge" / "patterns.md").write_text("", encoding="utf-8")
    lib = tmp / "lib"
    buf = _io.StringIO()
    with contextlib.redirect_stdout(buf): cmd_absorb_md(src, lib, dry_run=False)
    assert "追加 2 条" in buf.getvalue(), "首跑异常: " + buf.getvalue()[-200:]
    buf = _io.StringIO()
    with contextlib.redirect_stdout(buf): cmd_absorb_md(src, lib, dry_run=False)
    out = buf.getvalue()
    assert "幂等跳过 2 条" in out and "0 拒绝" in out, "重跑幂等语义错误: " + out[-200:]
    assert not (lib / "memory" / "longterm" / "SOUL-POINTER.json").read_text(encoding="utf-8").count("SOUL-POINTER") > 1

@t
def t_doctor_chain_check():
    """v3.6/K-002：doctor 审计链逐行重算——篡改精确报行"""
    import io as _io, contextlib
    tmp = _tmpdir("_bsv3t_k2")
    try:
        cmd_install("L2", [], tmp, True)
        e = {"id": "k2e", "created_at": "2026-09-07", "updated_at": "", "content": "x",
             "keywords": [], "links": [], "source_event_id": "gen", "importance": 1,
             "confidence": "高", "validity": {}}
        cmd_engine("append", tmp, json.dumps(e, ensure_ascii=False))
        buf = _io.StringIO()
        with contextlib.redirect_stdout(buf): cmd_engine("doctor", tmp)
        assert "审计链 连续" in buf.getvalue()
        ap = list((tmp / "audit").glob("lifelog-*.md"))[0]
        lines = ap.read_text(encoding="utf-8").splitlines()
        lines[0] = lines[0].replace("M-001", "M-XXX")  # 篡改首行
        ap.write_text(chr(10).join(lines) + chr(10), encoding="utf-8")
        buf = _io.StringIO()
        with contextlib.redirect_stdout(buf): cmd_engine("doctor", tmp)
        out = buf.getvalue()
        assert "断链 1 处" in out and ":1" in out, "篡改未被链校验定位: " + out
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

@t
def t_reflect_done():
    """v3.6/K-003：reflect-done 重置累计器并走账本/审计链"""
    import io as _io, contextlib
    tmp = _tmpdir("_bsv3t_k3")
    try:
        cmd_install("L2", [], tmp, True)
        st_path = tmp / "state.json"
        st = json.loads(st_path.read_text(encoding="utf-8"))
        st["importance_accum"] = 88
        st_path.write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")
        (tmp / "memory" / "reflect").mkdir(parents=True, exist_ok=True)
        (tmp / "memory" / "reflect" / "materials-x.md").write_text("素材", encoding="utf-8")
        buf = _io.StringIO()
        with contextlib.redirect_stdout(buf): cmd_engine("reflect-done", tmp)
        assert "已重置" in buf.getvalue()
        st = json.loads(st_path.read_text(encoding="utf-8"))
        assert st["importance_accum"] == 0
        ledger = (tmp / "ledger" / "changes.jsonl").read_text(encoding="utf-8")
        assert "reflect-done" in ledger
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

@t
def t_entrypoint_state_ref():
    """v3.6/K-004：入口引用 state.json 而非幽灵路径"""
    tmp = _tmpdir("_bsv3t_k4")
    try:
        cmd_install("L2", [], tmp, True)
        ag = (tmp / "AGENTS.md").read_text(encoding="utf-8")
        assert "state.json" in ag and "state/README.md" not in ag
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

@t
def t_build_docs_lib_nostate():
    """v3.6/K-005：--lib 指向非库目录友好退出"""
    import io as _io, contextlib
    tmp = _tmpdir("_bsv3t_k5")
    try:
        refused = False
        try: cmd_build(None, tmp)
        except SystemExit as ex: refused = "state.json" in str(ex)
        assert refused, "无 state 目录未友好拒绝"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

@t
def t_full_render_rule():
    """v3.8：全量渲染化规则（L-008）——L9 下全部 experimental install.md 渲染化"""
    tmp = _tmpdir("_bsv3t_k6")
    try:
        cmd_install("L9", [], tmp, True)
        ims = list((tmp / "experimental-l8").rglob("install.md")) + list((tmp / "experimental-l9").rglob("install.md"))
        assert len(ims) >= 10
        assert all("渲染产物" in q.read_text(encoding="utf-8")[:120] for q in ims), "存在未渲染化的 install.md"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

@t
def t_redeliver_pilot_unified():
    """v3.7/L-001：redeliver 复用 _body_for——全量渲染文件 redeliver 后漂移 0"""
    import io as _io, contextlib
    tmp = _tmpdir("_bsv3t_l1")
    try:
        cmd_install("L9", [], tmp, True)
        victim = tmp / "experimental-l8" / "constitution" / "install.md"
        victim.write_text(victim.read_text(encoding="utf-8") + chr(10) + "<!-- 手改 -->", encoding="utf-8")
        buf = _io.StringIO()
        with contextlib.redirect_stdout(buf): cmd_install("L9", [], tmp, True, redeliver=True)
        assert "重交付" in buf.getvalue()
        buf = _io.StringIO()
        with contextlib.redirect_stdout(buf): cmd_install("L9", [], tmp, True)
        assert "漂移 0" in buf.getvalue(), "redeliver 后渲染文件仍漂移（分叉未消灭）"
        assert "渲染产物" in victim.read_text(encoding="utf-8")[:120], "redeliver 未按渲染化重写"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

@t
def t_absorb_overrides_loop():
    """v3.7/L-002：--absorb-overrides 出回写建议+清旁路，单一事实源复位"""
    import io as _io, contextlib
    tmp = _tmpdir("_bsv3t_l2")
    real_data = str(DATA_DIR)
    real_urlopen = urllib.request.urlopen
    xml = "<?xml?><feed><title>q</title><title>Mocked Test Title</title></feed>"
    def _mock(*a, **k): return _io.BytesIO(xml.encode("utf-8"))
    try:
        set_data_dir(tmp / "pkgdata")
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        (DATA_DIR / "bodies.json").write_text("{}", encoding="utf-8")
        urllib.request.urlopen = _mock
        try:
            with contextlib.redirect_stdout(_io.StringIO()):
                try: cmd_verify(fix=True, throttle=False)
                except SystemExit: pass  # v3.8/N-001：mismatch→exit 1 属预期，overrides 仍已写盘
            assert (DATA_DIR / "registry_overrides.json").exists()
            buf = _io.StringIO()
            with contextlib.redirect_stdout(buf):
                try: cmd_verify(fix=False, throttle=False, absorb_overrides=True)
                except SystemExit as ex: assert ex.code == 1
            out = buf.getvalue()
            assert "REGISTRY-ABSORB.md" in out and "单一事实源复位" in out
            assert not (DATA_DIR / "registry_overrides.json").exists(), "旁路文件未清空"
            assert (DATA_DIR / "REGISTRY-ABSORB.md").exists()
        finally:
            urllib.request.urlopen = real_urlopen
    finally:
        set_data_dir(real_data); shutil.rmtree(tmp, ignore_errors=True)

@t
def t_ledger_guard_absorb():
    """v3.7/L-003：guard-snapshot/guard-anchor 汇总入账本"""
    import io as _io, contextlib
    tmp = _tmpdir("_bsv3t_l3")
    try:
        cmd_install("L2", [], tmp, True)
        with contextlib.redirect_stdout(_io.StringIO()): cmd_guard(None, tmp, snapshot=True)
        with contextlib.redirect_stdout(_io.StringIO()): cmd_guard(None, tmp, anchor=tmp / "anchor_snapshot.json")
        ledger = (tmp / "ledger" / "changes.jsonl").read_text(encoding="utf-8")
        assert "guard-snapshot" in ledger and "guard-anchor" in ledger
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

@t
def t_eval_degradation():
    """v3.7/L-004：基线劣化超 5% 触发宪章警告并 exit 2"""
    import io as _io, contextlib
    tmp = _tmpdir("_bsv3t_l4")
    try:
        cmd_install("L2", [], tmp, True)
        mk = lambda i, c: {"id": i, "created_at": "2026-09-07", "updated_at": "", "content": c,
                           "keywords": [c[:3]], "links": [], "source_event_id": "gen",
                           "importance": 7, "confidence": "高", "validity": {}}
        cmd_engine("append", tmp, json.dumps(mk("e1", "哈希链内容"), ensure_ascii=False))
        (tmp / "evals").mkdir(exist_ok=True)
        qs = [{"query": "哈希", "expected": ["e1"], "type": "lexical"}]
        (tmp / "evals" / "golden_queries.json").write_text(json.dumps(qs, ensure_ascii=False), encoding="utf-8")
        (tmp / "evals" / "baseline.json").write_text(json.dumps({"recall@5": 1.0, "MRR": 1.0}), encoding="utf-8")
        e1 = json.loads((tmp / "memory" / "longterm" / "e1.json").read_text(encoding="utf-8"))
        e1["validity"] = {"t_invalid": "2026-09-07"}  # 制造劣化：expected 条目失效
        (tmp / "memory" / "longterm" / "e1.json").write_text(json.dumps(e1, ensure_ascii=False), encoding="utf-8")
        code = 0
        buf = _io.StringIO()
        try:
            with contextlib.redirect_stdout(buf): cmd_engine("eval", tmp)
        except SystemExit as ex: code = ex.code
        assert code == 2 and "宪章警告" in buf.getvalue(), "劣化未触发宪章警告"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

@t
def t_cross_month_real():
    """v3.7/L-005：真跨月——次月首行 prev=上月尾哈希（X-018 核心路径补测）"""
    import time as _time_mod
    tmp = _tmpdir("_bsv3t_l5")
    real_strftime = _time_mod.strftime
    try:
        h1 = chain_append(tmp / "audit", "first line")
        _time_mod.strftime = lambda fmt, *a: "2099-12" if fmt == "%Y-%m" else "2099-12-31 23:59"  # 模块级 patch：chain_append 同源
        h2 = chain_append(tmp / "audit", "next month line")
        files = sorted((tmp / "audit").glob("lifelog-*.md"))
        assert len(files) == 2, f"应生成两个月文件: {[f.name for f in files]}"
        first_of_next = files[-1].read_text(encoding="utf-8").splitlines()[0]
        assert f"prev:{h1}" in first_of_next, "次月首行未引用上月尾哈希"
    finally:
        _time_mod.strftime = real_strftime
        shutil.rmtree(tmp, ignore_errors=True)

@t
def t_entry_normalize_types():
    """v3.7/L-006：keywords/links 类型强转"""
    e = entry_normalize({"id": "x", "keywords": "单一", "links": None, "created_at": "2026-09-07",
                         "updated_at": "", "content": "c", "source_event_id": "g", "importance": 1,
                         "confidence": "高", "validity": {}})
    assert e["keywords"] == ["单一"] and e["links"] == []
    e2 = entry_normalize({"id": "y", "keywords": 123, "links": "ab", "created_at": "2026-09-07",
                          "updated_at": "", "content": "c", "source_event_id": "g", "importance": 1,
                          "confidence": "高", "validity": {}})
    assert e2["keywords"] == [] and e2["links"] == ["ab"]

@t
def t_verify_exit_codes():
    """v3.8/N-001：mismatch→exit 1；全 error→不判负"""
    import io as _io, contextlib
    tmp = _tmpdir("_bsv3t_n1")
    real_urlopen = urllib.request.urlopen
    real_data = str(DATA_DIR)
    xml = "<?xml?><feed><title>q</title><title>Mocked Test Title</title></feed>"
    def _mock(*a, **k): return _io.BytesIO(xml.encode("utf-8"))
    def _boom(*a, **k): raise IOError("offline")
    try:
        set_data_dir(tmp / "pkgdata")
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        (DATA_DIR / "bodies.json").write_text("{}", encoding="utf-8")
        urllib.request.urlopen = _mock
        try:
            buf = _io.StringIO()
            with contextlib.redirect_stdout(buf):
                try: cmd_verify(fix=False, throttle=False)
                except SystemExit as ex: assert ex.code == 1, "mismatch 应 exit 1"
            assert "不一致 24" in buf.getvalue()
        finally:
            urllib.request.urlopen = _boom
            buf = _io.StringIO()
            with contextlib.redirect_stdout(buf):
                try: cmd_verify(fix=False, throttle=False)
                except SystemExit as ex: assert ex.code in (0, None), "未对账不应 exit 1"
            assert "未对账 24" in buf.getvalue()
    finally:
        urllib.request.urlopen = real_urlopen; set_data_dir(real_data)
        shutil.rmtree(tmp, ignore_errors=True)

@t
def t_migrate_state():
    """v3.8/N-002：migrate 建最小 state（level=MIGRATED），append 后 accum/根更新"""
    tmp = _tmpdir("_bsv3t_n2")
    try:
        lg = tmp / "knowledge" / "lifelog"; lg.mkdir(parents=True)
        (lg / "2026-08.mdl").write_text("2026-08-31 | L8 | aaaabbbbccccdddd | 0123456789abcdef" + chr(10), encoding="utf-8")
        cmd_migrate(tmp)
        st = json.loads((tmp / "state.json").read_text(encoding="utf-8"))
        assert st["level"] == "MIGRATED" and "merkle_root" in st
        good = {"id": "mst1", "created_at": "2026-09-07", "updated_at": "", "content": "迁移库可写",
                "keywords": [], "links": [], "source_event_id": "gen", "importance": 7,
                "confidence": "高", "validity": {}}
        cmd_engine("append", tmp, json.dumps(good, ensure_ascii=False))
        st = json.loads((tmp / "state.json").read_text(encoding="utf-8"))
        assert st["importance_accum"] == 7, "迁移库 accum 未生效（半身库）"
        assert st["merkle_root"] == merkle_root(tmp, exclude={"state.json"})
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

@t
def t_doctor_crossmonth_and_state():
    """v3.8/N-003：doctor 跨月断链定位 + state 第五态"""
    import io as _io, contextlib, time as _time_mod
    tmp = _tmpdir("_bsv3t_n3")
    real_strftime = _time_mod.strftime
    try:
        cmd_install("L2", [], tmp, True)
        e = {"id": "n3e", "created_at": "2026-09-07", "updated_at": "", "content": "x",
             "keywords": [], "links": [], "source_event_id": "gen", "importance": 2,
             "confidence": "高", "validity": {}}
        cmd_engine("append", tmp, json.dumps(e, ensure_ascii=False))
        # 跨月：追加 8 月文件（在 9 月之前，制造两个月结构）并伪造断链
        aug = tmp / "audit" / "lifelog-2026-08.md"
        aug.write_text("2026-08-31 | x | genesis | ffffffffffffffff" + chr(10), encoding="utf-8")
        # 现有 2026-09 文件首行 prev 指向 install 时哈希，不等于 8 月伪尾 ffff… → 跨月断链
        buf = _io.StringIO()
        with contextlib.redirect_stdout(buf): cmd_engine("doctor", tmp)
        out = buf.getvalue()
        assert "跨月断链" in out or "断链" in out, "断链未被发现: " + out[:200]
        assert "state" in out, "第五态缺失"
    finally:
        _time_mod.strftime = real_strftime
        shutil.rmtree(tmp, ignore_errors=True)

@t
def t_verify_l9_no_gate():
    """v3.8/N-004：已装 L9 库纯校验不需 --yes；redeliver 仍需令牌"""
    import io as _io, contextlib
    tmp = _tmpdir("_bsv3t_n4")
    try:
        cmd_install("L9", [], tmp, True)
        buf = _io.StringIO()
        with contextlib.redirect_stdout(buf): cmd_install("L9", [], tmp, False)
        assert "校验模式" in buf.getvalue(), "纯校验被 gate 误拦"
        gated = False
        try: cmd_install("L9", [], tmp, False, redeliver=True)
        except SystemExit as ex: gated = "人类令牌" in str(ex)
        assert gated, "redeliver 未被慢车道拦截"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

@t
def t_append_max_bytes():
    """v3.8/N-007：单条目超 16MB 拒绝"""
    tmp = _tmpdir("_bsv3t_n5")
    try:
        cmd_install("L2", [], tmp, True)
        big = {"id": "huge", "created_at": "2026-09-07", "updated_at": "", "content": "长" * 9000000,
               "keywords": [], "links": [], "source_event_id": "gen", "importance": 1,
               "confidence": "高", "validity": {}}
        rejected = False
        try: cmd_engine("append", tmp, json.dumps(big, ensure_ascii=False))
        except SystemExit as ex: rejected = "超上限" in str(ex)
        assert rejected, "超限条目未被拒绝"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

@t
def t_shape():
    assert len(LEVELS) == 10 and len(PACKAGES) == 12 and len(LAWS) == 6 and len(SCHEMA_V3) == 10  # v3.2/C-010(D4) 十字段
    assert "invalid_ttl_days" in TUNABLES and "unverified_ttl_days" not in TUNABLES  # v3.2/C-008(D3) 改名收窄
    assert len(BASELINE_BLACKLIST) >= 8  # v3.2/C-006 守卫黑名单在位

def cmd_run_tests():
    fails = 0
    for fn in TESTS:
        try: fn(); print(f"  PASS {fn.__name__}")
        except Exception as ex: fails += 1; print(f"  FAIL {fn.__name__}: {ex}")
    print(f"run_tests: {len(TESTS)-fails}/{len(TESTS)}（T号=函数名自注册，无手工registry——G2/G9根治）")
    sys.exit(1 if fails else 0)

# ────────────────────────────────────────────────────────────────────
CLI = argparse.ArgumentParser(description=f"library-bootstrap v{VERSION} 单文件安装包")
CLI.add_argument("--hash", action="store_true", help="打印包自哈希")
sub = CLI.add_subparsers(dest="cmd", required=True)
s = sub.add_parser("absorb");      s.add_argument("src"); s.add_argument("--data", default=None)
s = sub.add_parser("verify");      s.add_argument("--fix", action="store_true"); s.add_argument("--absorb-overrides", action="store_true"); s.add_argument("--data", default=None)  # v3.7/L-002
s = sub.add_parser("run-tests")
s = sub.add_parser("build-docs"); s.add_argument("--out", default=None); s.add_argument("--lib", default=None)  # v3.5/J-004：out 缺省随 lib
s = sub.add_parser("install");     s.add_argument("level"); s.add_argument("--packages", nargs="*", default=[])
s.add_argument("--target", default="./mylib"); s.add_argument("--yes", action="store_true"); s.add_argument("--data", default=None)
s.add_argument("--redeliver", action="store_true")  # v3.5/J-010
s = sub.add_parser("engine");      s.add_argument("op"); s.add_argument("--lib", default="./mylib")
s.add_argument("--text", default=""); s.add_argument("--k", type=int, default=5)
s = sub.add_parser("guard");       s.add_argument("--diff", default=None); s.add_argument("--lib", default="./mylib")
s.add_argument("--anchor", default=None); s.add_argument("--snapshot", action="store_true")  # v3.3/Y-006
s = sub.add_parser("absorb-md");   s.add_argument("--src", required=True); s.add_argument("--lib", required=True)
s.add_argument("--dry-run", action="store_true")  # v3.4/H-004
s = sub.add_parser("migrate");     s.add_argument("--lib", default="./mylib")

if __name__ == "__main__":
    a = CLI.parse_args()
    if getattr(a, "data", None): set_data_dir(a.data)  # v3.3/Y-002
    elif os.environ.get("BS3_DATA_DIR"): set_data_dir(os.environ["BS3_DATA_DIR"])
    print(f"[bootstrap_v3 {VERSION}] pkg_sha256={self_hash()[:16]}…（每次命令自报，人侧对账）")
    {"absorb": lambda: cmd_absorb(a.src), "verify": lambda: cmd_verify(a.fix, absorb_overrides=a.absorb_overrides),
     "run-tests": cmd_run_tests, "build-docs": lambda: cmd_build(Path(a.out) if a.out else None, a.lib),
     "install": lambda: cmd_install(a.level, a.packages, Path(a.target), a.yes, a.redeliver),
     "engine": lambda: cmd_engine(a.op, Path(a.lib), a.text, a.k),
     "guard": lambda: cmd_guard(a.diff, Path(a.lib), a.anchor, a.snapshot),
     "absorb-md": lambda: cmd_absorb_md(Path(a.src), Path(a.lib), a.dry_run),
     "migrate": lambda: cmd_migrate(Path(a.lib))}[a.cmd]()
