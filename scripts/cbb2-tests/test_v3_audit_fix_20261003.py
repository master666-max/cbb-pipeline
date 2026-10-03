# -*- coding: utf-8 -*-
"""test_v3_audit_fix_20261003.py — 2026-10-03 审计三修回归。

修1：runner.run_chapter aux 探活——rc!=0 且无 stdout 披露（裸崩）必须 error+returncode+
    stderr 尾部入披露，不再伪装 blocked；工具路径从模块位置推导绝对路径（双布局兼容）。
修2：gate1 --library-root——全库实体/known_ids 注入口，跨批死人走路/悬空引用生效；
    缺省（无注入）行为不变（本批口径，局限已在 CLI help 明示）。
运行：py -X utf8 test_v3_audit_fix_20261003.py
"""
import contextlib
import importlib.util
import io
import json
import subprocess as sp
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from cbb2 import runner  # noqa: E402


def _load_gate1():
    """双布局定位 cbb_gate1（包 scripts/cbb 与工作区根 cbb），按文件路径加载。"""
    for base in (HERE.parent, HERE.parent.parent):
        p = base / "cbb" / "cbb-gate1" / "cbb_gate1.py"
        if p.exists():
            spec = importlib.util.spec_from_file_location("cbb_gate1_reg_20261003", p)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    raise RuntimeError("cbb_gate1.py 未找到（双布局均缺席）")


g1 = _load_gate1()


def _ev(chapter, quote):
    return {"vol": 1, "chapter": chapter, "line": 1, "quote": quote}


def _dead_entity():
    return g1.make_generic_record(
        "entity", "character", {"name": "帕林", "status": "dead", "death_chapter": 14},
        [_ev(14, "帕林殒命")])


def _late_event():
    return g1.make_generic_record(
        "event", "event", {"name": "亡灵现身", "entity_refs": ["帕林"]},
        [_ev(20, "亡灵现身")])


# ---- 修1：runner aux 探活披露 ----

class _Proc:
    def __init__(self, rc, out, err):
        self.returncode, self.stdout, self.stderr = rc, out, err


def test_aux_tool_dir_dual_layout_absolute():
    """修1 路径面：工具目录按模块位置推导，双布局下均解析到真实存在的绝对路径。"""
    d = runner._aux_tool_dir()
    assert d is not None and Path(d).is_absolute()
    assert (Path(d) / "embed_dedup_scan.py").exists()


def test_aux_crash_not_masked_as_blocked():
    """修1 回归：rc!=0 且无 stdout（裸崩/用法错）→ error+returncode+stderr 尾部。
    旧实现把一切无 stdout 的子进程（含崩溃）一律伪装成 {"status":"blocked"}。"""
    seen = []

    def fake_run(cmd, **kw):
        seen.append(cmd)
        return _Proc(2, "", "usage: embed_dedup_scan.py [-h] --cands CANDS --store STORE")

    real = sp.run
    try:
        sp.run = fake_run
        out = runner.run_chapter(7, store=Path(tempfile.mkdtemp()), no_aux=False)
    finally:
        sp.run = real
    for key in ("embedding", "graph"):
        assert out["aux"][key]["status"] == "error", out["aux"][key]
        assert out["aux"][key]["returncode"] == 2
        assert "usage:" in out["aux"][key]["stderr"]
    # 路径面：脚本参数必须是模块位置推导出的绝对路径（旧仓库相对路径在当前布局必错）
    assert [Path(c[3]).name for c in seen] == ["embed_dedup_scan.py", "neo4j_export.py"]
    assert all(Path(c[3]).is_absolute() for c in seen)


def test_aux_blocked_protocol_rc2_with_stdout_still_parsed():
    """修1 兼容：工具自带披露协议（embed 探活失败 rc=2 + stdout JSON）仍解析其披露行，
    不误升 error——只有 rc!=0 且无 stdout 才判裸崩。"""
    def fake_run(cmd, **kw):
        return _Proc(2, json.dumps({"status": "blocked", "reason": "LM Studio 探活失败"},
                                   ensure_ascii=False) + "\n", "")

    real = sp.run
    try:
        sp.run = fake_run
        out = runner.run_chapter(7, store=Path(tempfile.mkdtemp()), no_aux=False)
    finally:
        sp.run = real
    assert out["aux"]["embedding"]["status"] == "blocked"
    assert "探活失败" in out["aux"]["embedding"]["reason"]


def test_aux_rc0_empty_stdout_keeps_blocked_semantics():
    """rc=0 且无 stdout：保留旧 blocked 降级语义不变。"""
    def fake_run(cmd, **kw):
        return _Proc(0, "", "")

    real = sp.run
    try:
        sp.run = fake_run
        out = runner.run_chapter(7, store=Path(tempfile.mkdtemp()), no_aux=False)
    finally:
        sp.run = real
    assert out["aux"]["embedding"] == {"status": "blocked"}


# ---- 修2：gate1 --library-root 跨批注入口 ----

def test_gate1_cross_batch_dead_walk_needs_injection():
    """修2 回归：他批沉淀的死亡实体+本批引用事件——注入 entities_by_name 后跨批
    死人走路拦截；缺省（无注入）不误报（局限=本批口径，CLI help 已明示）。"""
    late = _late_event()
    assert g1.check_batch([late], {})["summary"]["intercept"] == 0  # 缺省行为不变
    dead = _dead_entity()
    res = g1.check_batch([late], {"entities_by_name": {"帕林": dead},
                                  "known_ids": {dead["record_id"]}})
    assert res["summary"]["intercept"] == 1
    v = res["intercepted"][0]["check"]["violations"][0]
    assert v["code"] == "G1-DEAD-WALK" and "死人走路" in v["detail"]


def test_gate1_batch_entities_override_injected_library():
    """注入合并语义：本批同名实体=最新观察覆盖库内基线（注入不丢本批实体——
    旧 setdefault 语义下注入即丢本批实体，同批死人走路反而失效）。"""
    lib_dead = _dead_entity()
    batch_alive = g1.make_generic_record(
        "entity", "character", {"name": "帕林", "status": "alive"}, [_ev(15, "帕林仍在")])
    late = _late_event()
    res = g1.check_batch(
        [batch_alive, late],
        {"entities_by_name": {"帕林": lib_dead},
         "known_ids": {lib_dead["record_id"], batch_alive["record_id"]}})
    assert res["summary"]["intercept"] == 0  # 本批 alive 覆盖库内 dead 基线


def test_gate1_load_library_view_and_cli_end_to_end():
    """_load_library_view：全库实体/known_ids/不可读披露；CLI --library-root 端到端：
    跨批死人走路在真库根上拦截并披露注入统计。"""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        dead = _dead_entity()
        d = root / "libraries" / "character" / "provisional"
        d.mkdir(parents=True)
        (d / f"{dead['record_id']}.json").write_text(
            json.dumps(dead, ensure_ascii=False), encoding="utf-8")
        (root / "libraries" / "character" / "confirmed").mkdir(parents=True)
        (root / "libraries" / "character" / "confirmed" / "broken.json").write_text(
            "{oops", encoding="utf-8")  # 撕裂件：计数披露不静默
        ents, known, unreadable = g1._load_library_view(root)
        assert "帕林" in ents and dead["record_id"] in known and unreadable == 1
        cand = root / "cands.json"
        cand.write_text(json.dumps({"candidates": [_late_event()]}, ensure_ascii=False),
                        encoding="utf-8")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = g1.main(["--candidates", str(cand), "--library-root", str(root)])
        assert rc == 0
        outp = buf.getvalue()
        assert "intercept=1" in outp
        assert "G1-DEAD-WALK" in outp  # by_code 披露
        assert "library-root=" in outp and "不可读=1" in outp


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items())
           if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"OK {fn.__name__}")
    print(f"{len(fns)} tests PASS")
