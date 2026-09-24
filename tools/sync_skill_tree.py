# -*- coding: utf-8 -*-
"""sync_skill_tree.py — 主线 cbb/ → 发布树 cbb-pipeline/scripts/cbb/ 显式清单同步。

原则：只同步"主线为真源"的件；技能树布局适配件（如 build_evidence_index.py 的
HERE 深度）**不同步**——盲拷会打断包内相对路径。每件同步后逐字节校验。
"""
import hashlib
import pathlib
import shutil

MAIN = pathlib.Path(r"D:/zcode专用！！！！危险！！！！！！！！！/正典库构建系统/cbb")
SK = pathlib.Path(r"D:/zcode专用！！！！危险！！！！！！！！！/正典库构建系统/cbb-pipeline-skill/cbb-pipeline/scripts/cbb")

SYNC = [
    # 本批 R4 修复件（源码）
    "cbb-store/cbb_store.py", "cbb-anchor/cbb_anchor.py", "cbb-coordinate/cbb_coordinate.py",
    "cbb-extract/cbb_extract.py", "tools/矛盾分流.py", "tools/graphiti_ready.py",
    "tools/ledger_chain.py", "tools/neo4j_export.py",
    # 对应测试
    "cbb-store/test_cbb_store.py", "cbb-anchor/test_cbb_anchor.py",
    "cbb-coordinate/test_cbb_coordinate.py", "cbb-extract/test_cbb_extract.py",
    "tools/test_矛盾分流.py", "tools/test_ledger_chain.py", "tools/test_neo4j_export.py",
    # 新测试（技能树此前无此件）
    "tools/test_graphiti_ready.py",
    # 技能树滞留的旧版（主线已修：超长路径防御/脏行防御/confirmed 目录扫描）
    "tools/embed_dedup_scan.py",
]
# 不同步（技能树布局适配，主线版本会打断包内相对路径）：
SKIP_LAYOUT = ["tools/build_evidence_index.py"]

def h(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

for rel in SYNC:
    src = MAIN / pathlib.PurePosixPath(rel)
    dst = SK / pathlib.PurePosixPath(rel)
    assert src.exists(), f"主线缺件: {rel}"
    before = h(dst) if dst.exists() else None
    if before == h(src):
        print(f"  = 已一致 {rel}")
        continue
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
    assert h(dst) == h(src), f"校验失败 {rel}"
    print(f"  → {'新增' if before is None else '更新'} {rel}")

for rel in SKIP_LAYOUT:
    a, b = MAIN / rel, SK / rel
    same = a.exists() and b.exists() and h(a) == h(b)
    print(f"  ⚠ 跳过（布局适配件，差异为设计使然）{rel}：{'一致' if same else '差异保留'}")

print("✓ 同步完成")
