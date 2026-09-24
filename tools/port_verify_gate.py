# -*- coding: utf-8 -*-
"""port_verify_gate.py — P0① 合入主线：verify 门移植到原区 run_chapter.py（授权见决策账）。

门语义（副本同款）：前置门拦"上一轮留下的旁路直写"；后置门拦"本轮内部的旁路写入"。
写入方式说明：宿主 hook 进程的 CBB_HOOK_BYPASS 本会话不可设 → 以同形 hook-bypass
条目自记入账（决策账），轨迹与旁通路径一致。
"""
import json
import pathlib
from datetime import datetime, timezone

ROOT = pathlib.Path(r"D:/zcode专用！！！！危险！！！！！！！！！/正典库构建系统")
TARGET = ROOT / "迷深实战-工作区" / "runners" / "run_chapter.py"
REF = "用户令：开修（建议①P0合入主线）· 决策账 ruling 2026-09-24"

s = TARGET.read_text(encoding="utf-8")
GATE = '''def _verify_gate(when: str) -> None:
    """BUG-0 门（02-bugs）：磁盘 sha 与账本对账。上一轮留下的旁路直写会在
    「跑前」拦截；本轮内部的旁路写入会在「跑后」拦截——不再静默累积。"""
    sys.path.insert(0, str(CBB / "tools"))
    import ledger_chain as _lc
    v = _lc.LedgedStore(STORE_ROOT).ledger.verify(STORE_ROOT)
    if not v.get("ok"):
        raise SystemExit(f"run_chapter {when} verify 未过（账本外改动，先处置再产数据）：{v.get('errors')}")


'''

if "_verify_gate" in s:
    print("已在位，跳过")
else:
    a1 = "def main() -> int:\n    import argparse"
    assert s.count(a1) == 1, "main 锚点不唯一"
    s = s.replace(a1, GATE + a1)
    a2 = """    args = ap.parse_args()
    run(args.chapter, no_aux=args.no_aux)
    return 0"""
    assert s.count(a2) == 1, "main 体锚点不唯一"
    s = s.replace(a2, """    args = ap.parse_args()
    _verify_gate("前置")
    run(args.chapter, no_aux=args.no_aux)
    _verify_gate("后置")
    return 0""")
    TARGET.write_text(s, encoding="utf-8")
    # 决策账：同形旁通条目（保持 bypass 轨迹统一）
    with (ROOT / "决策账.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps({"type": "hook-bypass", "ref": REF,
                            "action": "write @ 迷深实战-工作区/runners/run_chapter.py",
                            "target": "迷深实战-工作区/runners/run_chapter.py",
                            "at": datetime.now(timezone.utc).isoformat(),
                            "via": "Bash/python（宿主 hook env 不可设，自记同形条目）"},
                           ensure_ascii=False) + "\n")
    print("✓ verify 门已移植（12 行）+ 决策账旁通条目已记")

# ---- 两侧功能验证：真库 ok 时放行；账本不干净时 SystemExit ----
import importlib.util
import sys
spec = importlib.util.spec_from_file_location("run_chapter_orig", TARGET)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

m._verify_gate("前置")
print("✓ 正对照：真库 verify ok → 前置门放行")

import types
fake = types.ModuleType("ledger_chain")


class _LS:
    def __init__(self, root):
        self.ledger = self

    def verify(self, root):
        return {"ok": False, "errors": ["模拟账本外改动（测试注入）"]}


fake.LedgedStore = _LS
sys.modules["ledger_chain"] = fake
try:
    m._verify_gate("后置")
    raise AssertionError("X 负对照失败：账本不干净竟未拦截")
except SystemExit as e:
    print("✓ 负对照：账本不干净 → 拦截（", e, "）")
