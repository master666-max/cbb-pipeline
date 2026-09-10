"""E134 复跑驱动（ZCode 接手 2026-09-09）
按 HANDOVER-ZCode线 §4 P-014 轨迹注：import 后重定向 OUT 到新路径，不触碰原始数据。
原始数据：自演化离线实验_v4/自演化离线实验/res_e134.json
"""
import sys

PROTO = r"D:\临时工作区\大审查-工作包-20260909\混元\自演化离线实验_v4\自演化离线实验\proto"
OUT = r"D:\临时工作区\大审查-工作包-20260909\混元\复跑验证-ZCode接手-20260909\res_e134_rerun.json"

sys.path.insert(0, PROTO)
import run_e134

run_e134.OUT = OUT
run_e134.main()
