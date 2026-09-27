# -*- coding: utf-8 -*-
"""考官编制 smoke：三通道各做一次隔离双序评审，报告可用性与时延。
密钥不打印、不落文件——base/model/key 全部来自进程 env（D-004）。
用法：先在进程 env 里备好 EXAMINER_{LOCAL,DEEPSEEK,QWEN}_{BASE,MODEL} 与
EXAMINER_*_API_KEY（或其公共回落 DASHSCOPE_API_KEY / DEEPSEEK_API_KEY），
然后 `py -X utf8 smoke_examiners.py`。
"""
import sys
import time

sys.path.insert(0, ".")

from cbb2 import ops
from cbb2.promote import build_panel, judge_isolated


def main() -> int:
    print("== 考官编制 smoke ==")
    for kind in ("LOCAL", "DEEPSEEK", "QWEN"):
        cfg = ops.examiner_env(kind)
        base = cfg["base"] or "(未编制)"
        model = cfg["model"] or "(未编制)"
        key_state = f"有（{cfg['key_source']}）" if cfg["key"] else "无"
        print(f"[{kind}] base={base} model={model} key={key_state}")

    panel, missing = build_panel()
    print(f"编制：{len(panel)} 名在列（缺席：{missing or '无'}）")
    if not panel:
        print("SMOKE FAIL：无可用考官")
        return 1

    conclusion = '{"name":"沈青崖","entity_type":"人物","status":"provisional"}'
    evidence = "第三百零二章：沈青崖推门而入，腰间悬着半旧的铁剑，眉眼间尽是风尘。"
    fail = False
    for ch in panel:
        t0 = time.time()
        try:
            v = judge_isolated(ch, conclusion, evidence)
            dt = time.time() - t0
            print(f"[{ch.kind}] 隔离双序判定={v}  时延={dt:.1f}s")
        except Exception as e:  # noqa: BLE001 — smoke 需要报告任何通道异常
            dt = time.time() - t0
            fail = True
            print(f"[{ch.kind}] FAIL（{dt:.1f}s）：{str(e)[:120]}")
    print("SMOKE " + ("FAIL" if fail else "PASS"))
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
