# -*- coding: utf-8 -*-
"""gen_module_graph.py — 正典库构建系统 模块依赖图自动生成（架构图/04）。

原则三：依赖图永远自动生成，禁止手画。stdlib ast，零第三方依赖。
范围：正典库构建系统/*.py（顶层 runner）+ cbb-v2/cbb2/*.py + cbb-v2/tests/test_*。
输出：架构图/04-模块依赖图.md（Mermaid，GitHub 原生渲染）。
"""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "架构图" / "04-模块依赖图.md"

targets = sorted(ROOT.glob("*.py"))
targets += sorted((ROOT / "cbb-v2" / "cbb2").glob("*.py"))
targets += sorted((ROOT / "cbb-v2" / "tests").glob("test_*.py"))

modmap = {f.stem: f for f in targets}
edges = set()

for f in targets:
    try:
        tree = ast.parse(f.read_text(encoding="utf-8"))
    except SyntaxError as e:
        print(f"跳过语法异常件 {f.name}: {e}")
        continue
    for node in ast.walk(tree):
        cands = []
        if isinstance(node, ast.Import):
            cands = [a.name.split(".")[0] for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module == "cbb2":
                cands = [a.name for a in node.names]  # from cbb2 import promote → promote
            elif node.module.startswith("cbb2."):
                cands = [node.module.split(".")[1]]
            else:
                cands = [node.module.split(".")[0]]
        for c in cands:
            if c in modmap and c != f.stem:
                edges.add((f.stem, c))

lines = [
    "# 04 · 模块依赖图（自动生成，禁止手画）",
    "",
    f"> 生成器：`tools/gen_module_graph.py`（stdlib ast）· 范围=顶层 runner {len([f for f in targets if f.parent == ROOT])} 件 + cbb2 模块 + tests · 重生成：`py -X utf8 tools/gen_module_graph.py`",
    "",
    "```mermaid",
    "graph LR",
]
for a, b in sorted(edges):
    lines.append(f"  {a} --> {b}")
lines.append("```")
lines.append("")
lines.append("## 读图提示")
lines.append("")
lines.append("- 边=`import`（含 `from cbb2 import X`）；越靠近 cbb2 的节点越是被复用的地基（ops/promote/audit/twd）。")
lines.append("- 顶层 runner 之间**零横边**是纪律：runner 只准依赖 cbb2，不准互相 import（copy-paste 复用走模块化，不走 import 链）。")
lines.append("")

OUT.write_text("\n".join(lines), encoding="utf-8")
print(f"{len(edges)} 条依赖边 -> {OUT}")
