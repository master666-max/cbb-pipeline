# -*- coding: utf-8 -*-
"""verify_release.py — 发布树完整性自检：HASHES.json 逐件 sha256 核对（手改即 FAIL）。"""
import hashlib, json, sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
m = json.loads((root / "HASHES.json").read_text(encoding="utf-8"))
actual = {}
for p in root.rglob("*"):
    if p.is_file() and "__pycache__" not in p.parts and p.name != "HASHES.json":
        actual[p.relative_to(root).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
errors = []
for rel, sha in m["files"].items():
    if rel not in actual:
        errors.append(f"缺失: {rel}")
    elif actual[rel] != sha:
        errors.append(f"漂移: {rel}")
for rel in actual:
    if rel not in m["files"]:
        errors.append(f"多出(构建区外新增): {rel}")
if errors:
    print("FAIL\n" + "\n".join(errors[:20]))
    sys.exit(1)
print(f"OK 发布树与 manifest 逐位一致（{len(m['files'])} 件）")
