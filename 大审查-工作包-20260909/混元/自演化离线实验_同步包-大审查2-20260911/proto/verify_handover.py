"""交接自检 —— 本地 agent 拿到包后第一件事就是跑这个

    cd 自演化离线实验
    python3 proto/verify_handover.py

检查四件事：
  1. 文件完整性（关键文件是否都在）
  2. 依赖可用性（是否缺第三方库）
  3. 内核验收测试（结论是否真的落进了代码）
  4. 试点套件端到端（能否产出报告）

退出码 0 = 交接无损；非 0 = 有缺失，看输出定位。
"""
import os, sys, subprocess, importlib

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(HERE)

REQUIRED = [
    # 入口
    "HANDOVER.md",
    "离线实验总纲_从零复现.md",
    # 核心知识
    "自演化推演_实验总报告.md",
    "自演化推演_方法论总结.md",
    # 原始对象
    "bootstrap_v3.py",
    # 工单
    "bootstrap_v3_修复工单.md",
    "bootstrap_v3_v4重构工单集.md",
    "bootstrap_自演化落地工单集.md",
    # 可运行产物
    "proto/kernel.py",
    "proto/verify_kernel.py",
    "proto/evolve9.py",
    "proto/bs3v4.py",
    "pilot/pilot.py",
    "pilot/analyze.py",
    # 数据
    "sample_traces.jsonl",
    "res_e111.json",
    "res_e112.json",
    "res_e121.json",
]

ok = True


def sec(t):
    print(f"\n{'='*60}\n{t}\n{'='*60}")


sec("1/4 文件完整性")
missing = [f for f in REQUIRED if not os.path.exists(f)]
if missing:
    ok = False
    for m in missing:
        print(f"  ✗ 缺失：{m}")
else:
    print(f"  ✓ {len(REQUIRED)} 个关键文件全部就位")

n_md = len([f for f in os.listdir(".") if f.endswith(".md")])
n_py = len([f for f in os.listdir("proto") if f.endswith(".py")])
print(f"  · 顶层 Markdown {n_md} 份，proto/ Python {n_py} 个")
if n_md < 37 or n_py < 39:
    print("  ⚠ 数量少于预期（37 / 39），可能拷贝不完整")
    ok = False

sec("2/4 依赖可用性")
print(f"  · Python {sys.version.split()[0]}")
if sys.version_info < (3, 8):
    print("  ✗ 需要 Python 3.8+（用了 dataclasses / typing.Literal）")
    ok = False
else:
    print("  ✓ Python 版本满足（3.8+）")
try:
    importlib.import_module("dataclasses")
    from typing import Literal
    print("  ✓ 仅用标准库，无需 pip install")
except Exception as e:
    print(f"  ✗ 标准库异常：{e}")
    ok = False

sec("3/4 内核验收测试")
r = subprocess.run([sys.executable, "proto/verify_kernel.py"],
                   capture_output=True, text=True, timeout=600)
lines = [l for l in r.stdout.strip().split("\n") if l.strip()]
# verify_kernel.py 末尾是分隔线，取含 "PASS" 的那行才是结论
summary = next((l for l in reversed(lines) if "PASS" in l), lines[-1] if lines else "(无输出)")
if r.returncode == 0:
    print(f"  ✓ 通过：{summary}")
else:
    ok = False
    print(f"  ✗ 失败（退出码 {r.returncode}）：{summary}")
    for l in lines[-12:]:
        print("    " + l)

sec("4/4 试点套件端到端")
if os.path.exists("sample_traces.jsonl"):
    r2 = subprocess.run([sys.executable, "pilot/analyze.py", "sample_traces.jsonl"],
                        capture_output=True, text=True, timeout=600)
    if r2.returncode == 0 and "采纳率" in r2.stdout:
        verdict = [l for l in r2.stdout.split("\n")
                   if l.startswith(("✅", "⏸"))]
        print("  ✓ 分析器可运行")
        print(f"  · 结论：{verdict[0] if verdict else '(见完整输出)'}")
    else:
        ok = False
        print(f"  ✗ 分析器失败：{r2.stderr.strip()[-300:]}")
else:
    ok = False
    print("  ✗ 缺 sample_traces.jsonl")

sec("结果")
if ok:
    print("✅ 交接无损 —— 可以开始工作")
    print("\n下一步建议：")
    print("  1. 读 HANDOVER.md（唯一入口，含『已被推翻的结论』）")
    print("  2. 读 自演化推演_实验总报告.md（125 个实验全表）")
    print("  3. 若要继续实验，先读『已被推翻的结论』避免重复劳动")
    sys.exit(0)
else:
    print("❌ 交接有缺失 —— 请根据上面 ✗ 项补齐后再开始")
    sys.exit(1)
