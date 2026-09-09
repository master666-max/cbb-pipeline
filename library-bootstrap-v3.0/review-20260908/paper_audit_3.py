# -*- coding: utf-8 -*-
"""三轮：精确短语取证 + L9 未交付目录清单 + 档位-模块-论文对照。"""
import json, importlib.util, re
from pathlib import Path

ROOT = Path(r"D:\zcode专用！！！！危险！！！！！！！！！")
SRC = ROOT / "library-bootstrap-v3.0" / "bootstrap_v3.py"
BODIES = ROOT / "library-bootstrap-v3.0" / "bootstrap_data" / "bodies.json"
code = SRC.read_text(encoding="utf-8")
bodies = json.loads(BODIES.read_text(encoding="utf-8"))
blob = {k: v.get("body", "") for slot, items in bodies.items() if isinstance(items, dict) for k, v in items.items()}

def where(kw):
    c = len(re.findall(re.escape(kw), code))
    b = [k for k, t in blob.items() if kw.lower() in t.lower()]
    return c, b

for kw in ["MIRIX", "六类", "Knowledge Vault", "Vault", "12.4", "150 行", "150行",
           "superseded", "锦标赛", "TOURNAMENT", "三因子", "BCA", "消融", "谄媚",
           "心智议会", "四席位", "sleep_gate", "兴趣", "stakes", "分页", "页调度"]:
    c, b = where(kw)
    print(f"{kw:14s} 代码 {c:2d}  内容体 {len(b):2d}  {b[:2]}")

# L9 未映射目录的文件量
print("\n--- experimental-l9 各目录文件数 / 是否在 L9 交付 ---")
spec = importlib.util.spec_from_file_location("bsv3", SRC)
bs = importlib.util.module_from_spec(spec); spec.loader.exec_module(bs)
pre9 = set()
mods, _ = bs.resolve("L9", [])
for m in mods:
    if m.startswith("x:") or m in ("dirs", "laws"): continue
    pre9.update(bs.MODULE_MAPPING.get(m, []))
dirs = {}
for slot, items in bodies.items():
    if not isinstance(items, dict): continue
    for k, v in items.items():
        rel = v.get("src", "").replace("\\", "/")
        if rel.startswith("experimental-l9/"):
            head = "/".join(rel.split("/")[:2])
            dirs.setdefault(head, []).append(rel)
for head in sorted(dirs):
    ok = any(head == p.rstrip("/") or head.startswith(p.rstrip("/") + "/") for p in pre9)
    print(f"  {'交付' if ok else '不交付':4s} {head:38s} {len(dirs[head])} 文件")

# 引擎操作 vs Memory-R1 四操作
print("\n--- engine 支持的 op ---")
ops = re.findall(r'elif op == "(\w[\w-]*)"|if op == "(\w[\w-]*)"', code)
print(sorted({a or b for a, b in ops}))
# 检索打分是否使用情绪
rank = code[code.index("def _rank_entries"):code.index("def cmd_engine")]
print("rank 函数内出现 emotion:", "emotion" in rank, "| 出现 mood:", "mood" in rank)
