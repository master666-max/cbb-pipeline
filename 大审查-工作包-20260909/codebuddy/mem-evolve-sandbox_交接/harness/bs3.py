"""真实源码适配器：一切对 v3 行为的测量都必须经过这里。

铁律（本实验的自律约束，与被测系统的铁律 1/4 同构）：
  1. 不复制粘贴 bootstrap_v3.py 的任何一行逻辑——全部通过 importlib 直接调用真实函数。
  2. 探针只做只读 + 在临时目录内写，绝不触碰用户真实库。
  3. 探针结论必须是可解析的结构化 dict，不做口头断言。
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

DEFAULT_SRC = Path(os.environ.get(
    "BS3_PATH",
    r"D:/zcode专用！！！！危险！！！！！！！！！/library-bootstrap-v3.0/bootstrap_v3.py",
))


def load(src=None):
    """按文件路径导入 bootstrap_v3.py（该文件有 __main__ 守卫，导入无副作用）。"""
    p = Path(src or DEFAULT_SRC)
    if not p.exists():
        raise SystemExit(f"[bs3] 找不到被测源码：{p}（用 BS3_PATH 环境变量或 --src 指定）")
    spec = importlib.util.spec_from_file_location("bootstrap_v3_under_test", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ─────────────────────────────────────────────────────────────
# 库构造（走真实 cmd_engine）
# ─────────────────────────────────────────────────────────────

def entry(i, importance=1, content=None, **over):
    e = {
        "id": f"e{i}", "created_at": "2026-09-01", "updated_at": "",
        "content": content if content is not None else f"条目正文{i}的关键内容",
        "keywords": [f"kw{i}"], "links": [],
        "source_event_id": f"EV-{i:04d}", "importance": importance,
        "confidence": "中", "validity": {},
    }
    e.update(over)
    return e


def build_lib(bs3, n=5, importance=1, root=None, quiet=True):
    """用真实 cmd_engine 建库；返回库路径。"""
    lib = Path(root or tempfile.mkdtemp(prefix="bs3lib_"))
    for d in ("memory/intermediate", "memory/longterm", "memory/attic",
              "audit", "ledger", "evals"):
        (lib / d).mkdir(parents=True, exist_ok=True)
    (lib / "state.json").write_text(
        json.dumps({"importance_accum": 0}), encoding="utf-8")
    for i in range(n):
        _call(bs3, quiet, "append", lib, json.dumps(entry(i, importance), ensure_ascii=False))
    return lib


def _call(bs3, quiet, op, lib, text="", k=5):
    if quiet:
        with contextlib.redirect_stdout(io.StringIO()):
            bs3.cmd_engine(op, lib, text, k)
    else:
        bs3.cmd_engine(op, lib, text, k)


def run_doctor(bs3, lib):
    """执行真实 doctor 并结构化解析五态对账结论。"""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        bs3.cmd_engine("doctor", lib)
    out = buf.getvalue()
    flags = {
        "mem_not_audit": "[memory有而audit无]" in out,
        "audit_not_mem": "[audit有而memory无]" in out,
        "ledger_not_mem": "[ledger有而memory无]" in out,
        "mem_not_ledger": "[memory有而ledger无]" in out,
        "chain_broken": "[断链]" in out,
        "state_bad": "[state]" in out,
        "all_green": "五态 全一致" in out,
    }
    return {
        "raw": out,
        "detected": any(v for k, v in flags.items() if k != "all_green"),
        "flags": flags,
    }


# ─────────────────────────────────────────────────────────────
# 一致性探针 C1–C5（对应实验报告的 P0/P1 与截断攻击）
# ─────────────────────────────────────────────────────────────

_WORKER = r'''
import importlib.util, json, sys
src, lib, i = sys.argv[1], sys.argv[2], sys.argv[3]
spec = importlib.util.spec_from_file_location("b3", src)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
import contextlib, io
with contextlib.redirect_stdout(io.StringIO()):
    m.cmd_engine("append", lib, json.dumps({
        "id": "c" + i, "created_at": "2026-09-01", "updated_at": "",
        "content": "并发写入条目" + i, "keywords": [], "links": [],
        "source_event_id": "EV-C" + i, "importance": 5,
        "confidence": "中", "validity": {}}))
'''


def probe_concurrency(bs3, src, n_proc=12, importance=5, base=150):
    """C4 并发写丢失率：n_proc 个进程并发 append，importance_accum 应为 base*1 + n_proc*importance。

    报告 §1.2 P0-4 实测 v3 = 5/60（丢 92%）。
    base 取较大值：v3 的 read-modify-write 窗口 = 一次 Merkle 全树重算（O(n)），
    库太小则窗口短于进程启动抖动，测不出竞态（这是"构造不成立"类失败的典型形态）。
    """
    lib = build_lib(bs3, base, root=tempfile.mkdtemp(prefix="bs3conc_"))
    procs = [subprocess.Popen([sys.executable, "-c", _WORKER, str(src), str(lib), str(i)],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
             for i in range(n_proc)]
    for p in procs:
        p.wait()
    st = json.loads((lib / "state.json").read_text(encoding="utf-8"))
    expect = base * 1 + n_proc * importance
    actual = int(st.get("importance_accum", 0))
    return {
        "n_proc": n_proc, "expected_accum": expect, "actual_accum": actual,
        "loss_rate": round(1 - actual / expect, 4) if expect else None,
    }


def _rewrite(path, lines):
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8", newline="\n")


def probe_truncate(bs3, variant="full", k=2, n=5):
    """C3 截断攻击检出率。

    variant=full   ：同时移除尾部 k 个事件的记忆条目 + 审计行 + 账本行（真·回滚语义）
    variant=audit  ：只删审计链尾部 k 行（留记忆）——作为"doctor 有部分覆盖"的阳性对照
    两步都重算 Merkle 根并写回 state.json（模拟持有写权限的攻击者）。
    """
    lib = build_lib(bs3, n, root=tempfile.mkdtemp(prefix="bs3trunc_"))
    root_human = bs3.merkle_root(lib, exclude={"state.json"})   # 公理 E：根抄录至人侧
    audit_files = sorted((lib / "audit").glob("lifelog-*.md"))
    lines = audit_files[-1].read_text(encoding="utf-8").strip().splitlines()
    _rewrite(audit_files[-1], lines[:-k])

    if variant == "full":
        for i in range(n - k, n):
            for p in list((lib / "memory").rglob(f"e{i}.json")):
                p.unlink()
        lp = lib / "ledger" / "changes.jsonl"
        lls = lp.read_text(encoding="utf-8").strip().splitlines()
        keep = [l for l in lls if not any(f"entry=e{i} " in (l + " ") for i in range(n - k, n))]
        _rewrite(lp, keep)

    st = json.loads((lib / "state.json").read_text(encoding="utf-8"))
    st["merkle_root"] = bs3.merkle_root(lib, exclude={"state.json"})
    (lib / "state.json").write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")

    doc = run_doctor(bs3, lib)
    root_now = bs3.merkle_root(lib, exclude={"state.json"})
    return {"variant": variant, "k": k,
            "detected_internal": doc["detected"], "flags": doc["flags"],
            "detected_by_human_anchor": root_now != root_human}


def probe_laws(bs3):
    """C5 铁律 2 / 铁律 5 在 validate_entry 层的拦截率。"""
    bad_anchor = entry(99)
    bad_anchor["source_event_id"] = ""          # 报告 §1.2 P0-2：空串可绕过
    bad_anchor.pop("evidence", None)
    ok_anchor = entry(98)
    secret = entry(97, content="api key: sk-" + "A" * 20)

    def errs(e):
        return bs3.validate_entry(e)

    return {
        "law2_empty_source_rejected": bool(errs(bad_anchor)),
        "law2_detail": errs(bad_anchor),
        "law5_secret_rejected": any("铁律5" in x for x in errs(secret)),
        "control_valid_rejected": bool(errs(ok_anchor)),
    }


def probe_merkle_scaling(bs3, sizes=(50, 100, 200, 400, 800)):
    """资源开销：Merkle 全树重算随条目数的实测斜率（v3 每次 append 都全量重算）。"""
    out = []
    for n in sizes:
        lib = build_lib(bs3, n, root=tempfile.mkdtemp(prefix="bs3scale_"))
        t0 = time.perf_counter()
        bs3.merkle_root(lib, exclude={"state.json"})
        dt = time.perf_counter() - t0
        out.append({"n": n, "merkle_seconds": round(dt, 6)})
    return out


def probe_quickref_honesty(bs3):
    """公理 G 探针：渲染件里的测试计数是否由执行结果决定（报告 §1.2 P0-1）。"""
    import re as _re
    try:
        a = bs3.render_quickref(0)
        b = bs3.render_quickref(999)
    except Exception as ex:  # 签名变更时诚实记录，不伪造结论
        return {"error": f"{type(ex).__name__}: {ex}"}
    return {
        "ratios_at_n0": _re.findall(r"\d+\s*/\s*\d+", a or "")[:5],
        "ratios_at_n999": _re.findall(r"\d+\s*/\s*\d+", b or "")[:5],
        "depends_on_n": (a != b),
    }


def consistency_suite(bs3, src, n_proc=12):
    """一次跑完 C1–C5，返回结构化结论。"""
    lib = build_lib(bs3, 6, root=tempfile.mkdtemp(prefix="bs3suite_"))
    c1 = run_doctor(bs3, lib)
    return {
        "C1_doctor_clean": {"all_green": c1["flags"]["all_green"], "flags": c1["flags"]},
        "C3_truncate_full": probe_truncate(bs3, "full"),
        "C3_truncate_audit_only": probe_truncate(bs3, "audit"),
        "C4_concurrency": probe_concurrency(bs3, src, n_proc=n_proc),
        "C5_laws": probe_laws(bs3),
        "R1_merkle_scaling": probe_merkle_scaling(bs3, sizes=(50, 100, 200, 400)),
        "G_quickref": probe_quickref_honesty(bs3),
    }
