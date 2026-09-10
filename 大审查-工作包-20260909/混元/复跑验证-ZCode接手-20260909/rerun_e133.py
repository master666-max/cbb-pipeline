"""E133 复跑驱动（ZCode 接手 2026-09-09）"""
import sys

PROTO = r"D:\临时工作区\大审查-工作包-20260909\混元\自演化离线实验_v4\自演化离线实验\proto"
OUT = r"D:\临时工作区\大审查-工作包-20260909\混元\复跑验证-ZCode接手-20260909\res_e133_rerun.json"

sys.path.insert(0, PROTO)
import run_e133

run_e133.OUT = OUT
run_e133.main()
