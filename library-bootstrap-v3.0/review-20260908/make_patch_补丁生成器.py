# -*- coding: utf-8 -*-
"""生成 L9 交付映射补丁：在临时副本上应用，输出 unified diff，并跑测试验证。"""
import difflib, io, re, shutil, subprocess, sys, os
from pathlib import Path

SRC = Path(r"D:\zcode专用！！！！危险！！！！！！！！！\library-bootstrap-v3.0\bootstrap_v3.py")
orig = SRC.read_text(encoding="utf-8")
new = orig
changes = []

def sub(old, repl, tag):
    global new
    assert new.count(old) == 1, f"[{tag}] 锚点命中 {new.count(old)} 次（应为 1）"
    new = new.replace(old, repl, 1)
    changes.append(tag)

# 1) VERSION 3.8.1 -> 3.8.2（对齐文件头已写的 v3.8.2 与总表数据源标注；不想要可单独回退此 hunk）
sub('VERSION = "3.8.1"', 'VERSION = "3.8.2"  # v3.8.2/L9-DELIVER：L9 交付映射补全', "version")

# 2) MODULE_MAPPING 补 5 个 L9 语义模块（instrumentation 同时映射 scripts 的 .txt 工具）
sub(''' "l9:emotion": ["experimental-l9/emotion"], "l9:gwt": ["experimental-l9/gwt"],
 "l9:sleepgate": ["experimental-l9/sleep-pipeline"],
}''',
''' "l9:emotion": ["experimental-l9/emotion"], "l9:gwt": ["experimental-l9/gwt"],
 "l9:sleepgate": ["experimental-l9/sleep-pipeline"],
 # v3.8.2/L9-DELIVER：补全 L9 已吸收但漏交付的内容体（论文核对 T4：A24/A29/A32/A33）
 "l9:instrumentation": ["experimental-l9/instrumentation", "experimental-l9/scripts"],
 "l9:bca": ["experimental-l9/constitution-bca"],
 "l9:dual-memory": ["experimental-l9/dual-memory"],
 "l9:dmn": ["experimental-l9/dmn"], "l9:goalstack": ["experimental-l9/goalstack"],
}''', "mapping")

# 3) LEVELS L9 adds 补全 + gate 文案纠正（不再承诺"正文随 absorb 展示"）
sub(''' "L9": {"name":"内省仿生:BCA","adds":["l9:emotion","l9:gwt","l9:sleepgate"],"gate":"先展示BCA公理+验收三件(消融/干预/谄媚),人类确认"},''',
''' "L9": {"name":"内省仿生:BCA","adds":["l9:emotion","l9:gwt","l9:sleepgate","l9:instrumentation",
                                  "l9:bca","l9:dual-memory","l9:dmn","l9:goalstack"],
        "gate":"BCA四公理+验收三件(消融/干预/谄媚)——确认后交付 constitution-bca(append-axioms/ABLATIONS)，安装前可在 bodies 预览,人类确认"},''', "levels")

# 4) DEPS 补依赖边（与各 install.md 声明的依赖一致）
sub('''DEPS = {"m-evolve": ["m-schema3"], "m-sleep": ["m-reflect"], "l9:emotion": ["l8:governor"],
        "l9:gwt": ["l9:emotion"], "l9:sleepgate": ["l9:emotion"], "m-vector": ["m-search"]}''',
'''DEPS = {"m-evolve": ["m-schema3"], "m-sleep": ["m-reflect"], "l9:emotion": ["l8:governor"],
        "l9:gwt": ["l9:emotion"], "l9:sleepgate": ["l9:emotion"], "m-vector": ["m-search"],
        # v3.8.2/L9-DELIVER：依赖边对齐内容体 install.md 声明
        "l9:bca": ["l8:governor"], "l9:dual-memory": ["l9:emotion"],
        "l9:dmn": ["l9:instrumentation"], "l9:goalstack": ["l9:instrumentation"]}''', "deps")

# 5) _deliver 排除 __pycache__/.pyc（scripts 目录带 .pyc 垃圾，映射后必须挡住）
sub('''            rel = meta["src"].replace("\\\\", "/")
            if not any(rel == p or rel.startswith(p.rstrip("/") + "/") for p in prefixes): continue''',
'''            rel = meta["src"].replace("\\\\", "/")
            if not any(rel == p or rel.startswith(p.rstrip("/") + "/") for p in prefixes): continue
            if "__pycache__" in rel.split("/") or rel.endswith((".pyc", ".pyo")): continue  # v3.8.2/L9-DELIVER：缓存/二进制不交付''', "deliver-skip")

# 6) L9 gate 文案（cmd_install 内）
sub('gate = CHARTER_L8 if level == "L8" else "BCA 公理+验收三件（消融/干预/谄媚）——正文随 absorb 内容体展示"',
    'gate = CHARTER_L8 if level == "L8" else "BCA 四公理+验收三件（消融/干预/谄媚）——确认后交付 constitution-bca（append-axioms/ABLATIONS），安装前可在 bodies 预览"',
    "gate-text")

# 7) absorb 源头加二进制/缓存黑名单（.pyc 不再被 errors=replace 当文本吸进 bodies）
sub('''        if not slot: continue
        if p.stat().st_size > 512 * 1024:''',
'''        if not slot: continue
        if p.suffix.lower() in (".pyc", ".pyo") or "__pycache__" in rel.split("/"):
            skipped.append(f"{rel}（二进制缓存不吸收）"); continue  # v3.8.2/L9-DELIVER
        if p.stat().st_size > 512 * 1024:''', "absorb-skip")

# 8) 新增回归测试（插在 cmd_run_tests 之前）
tests = '''
@t
def t_l9_full_delivery():
    """v3.8.2/L9-DELIVER：L9 交付补全——bca/dmn/dual-memory/goalstack/instrumentation 与 scripts/*.txt 全落盘，.pyc 不交付"""
    tmp = _tmpdir("_bsv3t_l9full")
    try:
        cmd_install("L9", [], tmp, True)
        must = ["experimental-l9/constitution-bca/install.md",
                "experimental-l9/constitution-bca/template/append-axioms.md",
                "experimental-l9/constitution-bca/template/ABLATIONS.md",
                "experimental-l9/dmn/install.md", "experimental-l9/dmn/template/OPEN-QUESTIONS.md",
                "experimental-l9/dual-memory/install.md", "experimental-l9/dual-memory/template/trajectory-header.md",
                "experimental-l9/goalstack/install.md", "experimental-l9/goalstack/template/GOALS.md",
                "experimental-l9/instrumentation/install.md",
                "experimental-l9/scripts/state_snapshot.txt",
                "experimental-l9/scripts/state_intervene.txt",
                "experimental-l9/scripts/state_update.txt"]
        for rel in must:
            assert (tmp / rel).exists(), f"L9 漏交付 {rel}"
        mods, missing = resolve("L9", [])
        assert not missing, f"L9 依赖缺失 {missing}"
        need = {"l9:bca", "l9:dmn", "l9:dual-memory", "l9:goalstack", "l9:instrumentation"}
        assert need <= set(mods), f"L9 模块缺 {need - set(mods)}"
        assert not list(tmp.rglob("*.pyc")), ".pyc 二进制缓存被交付"
        assert not any("__pycache__" in p.parts for p in tmp.rglob("*") if p.is_file()), "__pycache__ 被交付"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

@t
def t_l8_not_deliver_l9():
    """v3.8.2/L9-DELIVER：L8 不越级交付 L9 专有内容体"""
    tmp = _tmpdir("_bsv3t_l8bound")
    try:
        cmd_install("L8", [], tmp, True)
        assert not (tmp / "experimental-l9").exists(), "L8 越级带出 L9 目录"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

@t
def t_l9_module_deps():
    """v3.8.2/L9-DELIVER：新增 L9 依赖边在位且全图无环"""
    assert DEPS["l9:dmn"] == ["l9:instrumentation"]
    assert DEPS["l9:goalstack"] == ["l9:instrumentation"]
    assert DEPS["l9:dual-memory"] == ["l9:emotion"]
    assert DEPS["l9:bca"] == ["l8:governor"]
    detect_cycle()

'''
sub("def cmd_run_tests():", tests + "def cmd_run_tests():", "tests")

print("已应用 hunks:", changes)
assert len(changes) == 8

# 语法检查
compile(new, "<patched>", "exec")
print("patched 语法 OK")

# unified diff
diff = difflib.unified_diff(
    orig.splitlines(keepends=False), new.splitlines(keepends=False),
    fromfile="bootstrap_v3.py (v3.8.1 原始)", tofile="bootstrap_v3.py (v3.8.2 L9-DELIVER 补丁后)",
    lineterm="")
diff_text = "\n".join(diff) + "\n"
out_dir = Path(r"D:\zcode专用！！！！危险！！！！！！！！！\library-bootstrap-v3.0\review-20260908")
(out_dir / "L9交付映射补丁.patch").write_text(diff_text, encoding="utf-8")
print("patch 行数:", len(diff_text.splitlines()))

# 临时副本验证：复制 py + bootstrap_data 到 temp，跑 run-tests
work = Path(os.environ["TEMP"]) / "_bsv3_patch_test"
if work.exists(): shutil.rmtree(work)
work.mkdir(parents=True)
(work / "bootstrap_data").mkdir()
proj = Path(r"D:\zcode专用！！！！危险！！！！！！！！！\library-bootstrap-v3.0")
shutil.copy(proj / "bootstrap_data" / "bodies.json", work / "bootstrap_data" / "bodies.json")
(work / "bootstrap_v3.py").write_text(new, encoding="utf-8")
# 用补丁后的 MODULE_MAPPING 重生成 level_mapping.json（真实结构：mapping/package_mapping/absorbed_from）
import importlib.util, json as _json
spec = importlib.util.spec_from_file_location("patched_bs", work / "bootstrap_v3.py")
pbs = importlib.util.module_from_spec(spec); spec.loader.exec_module(pbs)
lm = {"mapping": pbs.MODULE_MAPPING, "package_mapping": pbs.PACKAGE_MAPPING,
      "absorbed_from": "regenerated by v3.8.2/L9-DELIVER patch"}
(work / "bootstrap_data" / "level_mapping.json").write_text(
    _json.dumps(lm, ensure_ascii=False, indent=1), encoding="utf-8")
(out_dir / "level_mapping_补丁后.json").write_text(
    _json.dumps(lm, ensure_ascii=False, indent=1), encoding="utf-8")
print("level_mapping 模块键数:", len(lm["mapping"]), "| L9 键:", [k for k in lm["mapping"] if k.startswith("l9")])
r = subprocess.run([sys.executable, "-X", "utf8", "bootstrap_v3.py", "run-tests"],
                   cwd=work, capture_output=True, text=True, encoding="utf-8", errors="replace")
log = r.stdout + "\n[stderr]\n" + r.stderr
(work.parent / "patch_test_log.txt").write_text(log, encoding="utf-8")
# 只打印 FAIL 行与汇总
for line in log.splitlines():
    if "FAIL" in line or "run_tests:" in line or "Error" in line:
        print(line)
print("exit code:", r.returncode)
# 单独确认三个新测试 PASS
for name in ("t_l9_full_delivery", "t_l8_not_deliver_l9", "t_l9_module_deps"):
    m = [l for l in log.splitlines() if name in l]
    print(m[0] if m else f"!! {name} 未出现在结果里")
