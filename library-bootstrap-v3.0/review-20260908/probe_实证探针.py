# -*- coding: utf-8 -*-
"""bootstrap_v3.py 审查探针：全部在 temp 目录内完成，不碰源目录/源数据。"""
import sys, os, io, json, contextlib, tempfile, importlib.util, traceback
from pathlib import Path

SRC = r"D:\zcode专用！！！！危险！！！！！！！！！\library-bootstrap-v3.0\bootstrap_v3.py"
spec = importlib.util.spec_from_file_location("bsv3", SRC)
bs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bs)

results = []
def check(name, fn):
    try:
        detail = fn()
        results.append((name, True, detail or ""))
    except AssertionError as e:
        results.append((name, False, f"REFUTED: {e}"))
    except Exception as e:
        results.append((name, None, f"{type(e).__name__}: {e}"))

ROOT = Path(tempfile.mkdtemp(prefix="_bs3review_"))
PKG = ROOT / "pkgdata"; PKG.mkdir()
bs.set_data_dir(PKG)
(PKG / "bodies.json").write_text(json.dumps(
    {"docs": {"SKILL.md": {"body": "# skill\n", "src": "SKILL.md", "sha256": "x"}}},
    ensure_ascii=False), encoding="utf-8")
LIB = ROOT / "lib"

def silent(fn, *a, **k):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        r = fn(*a, **k)
    return buf.getvalue(), r

def good_entry(eid, imp=1, **kw):
    e = {"id": eid, "created_at": "2026-09-06", "updated_at": "", "content": "内容x",
         "keywords": [], "links": [], "source_event_id": "gen", "importance": imp,
         "confidence": "高", "validity": {}}
    e.update(kw); return e

# 基线安装
silent(bs.cmd_install, "L2", [], LIB, True)

# A. 空证据锚通过校验
def c_a():
    errs = bs.validate_entry(good_entry("a", source_event_id=""))
    assert any("证据" in x for x in errs), f"空证据锚应被拒，实际 errs={errs}"
check("A 空 source_event_id 被铁律2拦截", c_a)

# B. id 路径穿越
def c_b():
    eid = "../../../pwned"
    try:
        silent(bs.cmd_engine, "append", LIB, json.dumps(good_entry(eid), ensure_ascii=False))
    except SystemExit:
        pass
    escaped = ROOT / "pwned.json"
    inside = list((LIB / "memory").rglob("pwned.json"))
    assert not escaped.exists() and not inside, f"穿越写入: escaped={escaped.exists()} inside={inside}"
check("B id 含 ../ 的路径穿越被拒", c_b)

# C. shadow 后 state 根变陈旧
def c_c():
    st0 = json.loads((LIB / "state.json").read_text(encoding="utf-8"))["merkle_root"]
    silent(bs.cmd_engine, "shadow", LIB, "试变更")
    st1 = json.loads((LIB / "state.json").read_text(encoding="utf-8"))["merkle_root"]
    now = bs.merkle_root(LIB, exclude={"state.json"})
    assert st0 == st1 == now, f"shadow 后 state 根陈旧: state={st1[:12]} now={now[:12]}"
check("C shadow 后 state.merkle_root 仍与重算一致", c_c)

# D. 已装 L2 库请求 install L9 —— 档位被静默忽略
def c_d():
    out, _ = silent(bs.cmd_install, "L9", [], LIB, True)
    lvl = json.loads((LIB / "state.json").read_text(encoding="utf-8"))["level"]
    assert lvl == "L9" and "L9" in out, f"请求 L9 被静默忽略，实际 level={lvl}, 输出={out[:80]}"
check("D 对已装库请求更高档位 L9 不被忽略", c_d)

# E. eval 空评测集
LIB2 = ROOT / "lib2"; silent(bs.cmd_install, "L2", [], LIB2, True)
def c_e():
    (LIB2 / "evals").mkdir(exist_ok=True)
    (LIB2 / "evals" / "golden_queries.json").write_text("[]", encoding="utf-8")
    try:
        silent(bs.cmd_engine, "eval", LIB2)
    except ZeroDivisionError:
        raise AssertionError("空评测集触发 ZeroDivisionError")
check("E eval 空 golden 集不崩溃", c_e)

# F. 同 id 跨目录（intermediate/longterm）重复
def c_f():
    silent(bs.cmd_engine, "append", LIB2, json.dumps(good_entry("dup", imp=1), ensure_ascii=False))
    try:
        silent(bs.cmd_engine, "append", LIB2, json.dumps(good_entry("dup", imp=9), ensure_ascii=False))
        rejected = False
    except SystemExit as ex:
        rejected = "已存在" in str(ex)
    files = list((LIB2 / "memory").rglob("dup.json"))
    assert rejected and len(files) == 1, f"跨目录重复未拦截: rejected={rejected}, files={files}"
check("F 同 id 跨 intermediate/longterm 重复写入被拦截", c_f)

# G. guard 三参数全空
def c_g():
    try:
        silent(bs.cmd_guard, None, LIB2)
    except TypeError as e:
        raise AssertionError(f"无 --diff/--snapshot/--anchor 时 TypeError: {e}")
    except SystemExit:
        return "友好退出"
check("G guard 无任何模式参数时友好报错", c_g)

# H. 工具自产 anchor_snapshot.json 被报未在册
def c_h():
    silent(bs.cmd_guard, None, LIB2, snapshot=True)
    out, _ = silent(bs.cmd_install, "L2", [], LIB2, True)
    assert "anchor_snapshot.json" not in out, f"自产快照被当外来文件:\n{[l for l in out.splitlines() if 'anchor' in l]}"
check("H guard 自产 anchor_snapshot.json 不被报未在册", c_h)

# I. skills/wrap-up.md 手改检测
def c_i():
    f = LIB2 / "skills" / "wrap-up.md"
    f.write_text(f.read_text(encoding="utf-8") + "\n手改", encoding="utf-8")
    out, _ = silent(bs.cmd_install, "L2", [], LIB2, True)
    assert "wrap-up" in out and "渲染件被改" in out, f"渲染产物 skills/wrap-up.md 被手改却未报告"
check("I skills/*.md 渲染件手改能被检测", c_i)

# J. eval 劣化后旧基线被覆盖（棘轮失效）
LIB3 = ROOT / "lib3"; silent(bs.cmd_install, "L2", [], LIB3, True)
def c_j():
    silent(bs.cmd_engine, "append", LIB3, json.dumps(good_entry("e1", imp=7, content="哈希链", keywords=["哈希"]), ensure_ascii=False))
    (LIB3 / "evals").mkdir(exist_ok=True)
    (LIB3 / "evals" / "golden_queries.json").write_text(
        json.dumps([{"query": "哈希", "expected": ["e1"]}]), encoding="utf-8")
    (LIB3 / "evals" / "baseline.json").write_text(json.dumps({"recall@5": 1.0, "MRR": 1.0}), encoding="utf-8")
    p = LIB3 / "memory" / "longterm" / "e1.json"
    e = json.loads(p.read_text(encoding="utf-8")); e["validity"] = {"t_invalid": "2026-09-06"}
    p.write_text(json.dumps(e, ensure_ascii=False), encoding="utf-8")
    code = 0
    try:
        silent(bs.cmd_engine, "eval", LIB3)
    except SystemExit as ex:
        code = ex.code
    new_base = json.loads((LIB3 / "evals" / "baseline.json").read_text(encoding="utf-8"))
    assert code == 2 and new_base.get("recall@5") == 1.0, f"劣化基线覆盖了旧门限: code={code}, new={new_base}"
check("J eval 劣化(exit2)时保留旧基线作门限", c_j)

# K. absorb-md 产出半身库后 wrapup 崩溃
LIB4 = ROOT / "lib4"; SRC4 = ROOT / "v4src" / "knowledge"; SRC4.mkdir(parents=True)
(SRC4 / "pitfalls.md").write_text(
    "### P-1 / 2026-09-06 / 教训\n- 教训：内容\n- 状态：active\n", encoding="utf-8")
(SRC4.parent / "patterns.md").write_text("", encoding="utf-8")
def c_k():
    silent(bs.cmd_absorb_md, ROOT / "v4src", LIB4, False)
    try:
        silent(bs.cmd_engine, "wrapup", LIB4)
    except FileNotFoundError as e:
        raise AssertionError(f"半身库（无 state.json）wrapup 崩溃: {e}")
check("K absorb-md 产出的无 state 库执行 wrapup 不崩溃", c_k)

# L. retire 时 attic 已有同名文件
LIB5 = ROOT / "lib5"; silent(bs.cmd_install, "L2", [], LIB5, True)
def c_l():
    e = good_entry("old", validity={"t_invalid": "2026-01-01"})
    inter = LIB5 / "memory" / "intermediate"; inter.mkdir(parents=True, exist_ok=True)
    (inter / "old.json").write_text(json.dumps(e, ensure_ascii=False), encoding="utf-8")
    attic = LIB5 / "memory" / "attic"; attic.mkdir(parents=True, exist_ok=True)
    (attic / "old.json").write_text('{"旧版本": true}', encoding="utf-8")
    try:
        silent(bs.cmd_engine, "retire", LIB5)
    except Exception as ex:
        raise AssertionError(f"attic 同名时 retire 未处理: {type(ex).__name__}: {ex}")
    kept = json.loads((attic / "old.json").read_text(encoding="utf-8"))
    assert "旧版本" in kept, "attic 原有文件被覆盖（违反铁律1）"
check("L retire 不覆盖 attic 已有同名文件（铁律1）", c_l)

# M. Windows 渲染件换行
def c_m():
    raw = (LIB / "AGENTS.md").read_bytes()
    assert b"\r\n" not in raw, "AGENTS.md 含 CRLF（跨平台根不可复现）"
check("M 渲染件落盘为 LF（跨 OS 根一致）", c_m)

# N. 测试 runner 能否兜住 SystemExit
def c_n():
    def boom(): raise SystemExit(2)
    caught = True
    try:
        try: boom()
        except Exception: caught = True
        else: caught = False
    except SystemExit:
        caught = False
    assert caught, "cmd_run_tests 的 except Exception 兜不住 SystemExit，单测异常会中断整个套件"
check("N run-tests 能兜住测试内意外 SystemExit", c_n)

# O. resolve 依赖缺失时仍把模块加入 got
def c_o():
    old = dict(bs.DEPS); bs.DEPS["m-core"] = ["m-nonexistent"]
    try:
        got, missing = bs.resolve("L1", [])
    finally:
        bs.DEPS.clear(); bs.DEPS.update(old)
    assert not missing and "m-core" not in got, f"缺依赖模块仍入清单: missing={missing}"
check("O resolve 缺依赖时模块不进入安装清单", c_o)

print("ROOT:", ROOT)
for name, ok, detail in results:
    tag = {True: "PASS(断言成立=代码无此缺陷)", False: "CONFIRMED-BUG", None: "ERROR"}[ok]
    print(f"[{tag}] {name}  {detail if ok is not True else ''}")
