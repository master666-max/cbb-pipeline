# -*- coding: utf-8 -*-
"""build_release.py — Phase E 单命令构建：源真 → 发布树 + HASHES.json（--verify 可复算）。

同步语义（build-managed 区）：
  · scripts/cbb/{六技能目录,contracts,tools} ← 生产 cbb/ 同名目录（排除退役/实验族）
  · scripts/cbb2 ← cbb-v2/cbb2（v3 核心包）
build-managed 区内发布树多出的文件 = 构建产物漂移 → --verify FAIL；非管理区
（SKILL.md/references/assets/全流程说明书/README/init_project）为发布自有资产，构建不动它们。
排除族：graphiti_*（裁④退役）、lightrag_*、exp_*（对照实验）、web_console*、
adapt_record_to_tier1（DEAD）、__pycache__/临时件。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import py_compile
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REL = ROOT / "cbb-pipeline-skill" / "cbb-pipeline"
SRC_CBB = ROOT / "cbb"
SRC_V2 = ROOT / "cbb-v2"
MANIFEST = REL / "HASHES.json"
VERSION = "v3.0.0"

SYNC_DIRS = [("cbb-anchor", "cbb-anchor"), ("cbb-coordinate", "cbb-coordinate"),
             ("cbb-extract", "cbb-extract"), ("cbb-gate1", "cbb-gate1"),
             ("cbb-quarantine", "cbb-quarantine"), ("cbb-store", "cbb-store"),
             ("contracts", "contracts"), ("tools", "tools")]
EXCLUDE_PREFIX = ("exp_", "graphiti_", "lightrag_", "web_console", "adapt_record",
                  "_", "test_d2", "test_图链")
EXCLUDE_NAMES = {"判例.md"}  # 判例=实例侧资产，不进发布包（references/判例模板.md 为模板）


def git_anchor() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                          cwd=str(ROOT)).stdout.strip()[:12]


def wanted_files(src: Path) -> set[Path]:
    out = set()
    for p in src.rglob("*"):
        if not p.is_file() or "__pycache__" in p.parts:
            continue
        rel = p.relative_to(src)
        if any(part.startswith(".") for part in rel.parts):
            continue
        name = p.name
        if name.startswith(EXCLUDE_PREFIX) or name in EXCLUDE_NAMES or name.endswith(".pyc"):
            continue
        out.add(rel)
    return out


def sync_dir(src: Path, dst: Path) -> tuple[int, int]:
    copied = removed = 0
    wanted = wanted_files(src)
    for rel in sorted(wanted):
        s, d = src / rel, dst / rel
        if d.exists() and d.read_bytes() == s.read_bytes():
            continue
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(s, d)
        copied += 1
    for p in sorted(dst.rglob("*"), reverse=True):
        if not p.is_file():
            continue
        if "__pycache__" in p.parts or p.name.startswith(EXCLUDE_PREFIX) or p.name.endswith(".pyc"):
            p.unlink()
            removed += 1
            continue
        rel = p.relative_to(dst)
        if rel not in wanted:
            p.unlink()
            removed += 1
    for p in sorted(dst.rglob("*"), reverse=True):
        if p.is_dir() and not any(p.iterdir()):
            p.rmdir()
    return copied, removed


def build() -> dict:
    report = {"synced": {}, "removed_total": 0}
    for src_name, dst_name in SYNC_DIRS:
        copied, removed = sync_dir(SRC_CBB / src_name, REL / "scripts" / "cbb" / dst_name)
        report["synced"][dst_name] = {"copied": copied, "removed": removed}
        report["removed_total"] += removed
    copied, removed = sync_dir(SRC_V2 / "cbb2", REL / "scripts" / "cbb2")
    report["synced"]["cbb2"] = {"copied": copied, "removed": removed}
    report["removed_total"] += removed

    files = {}
    for p in sorted(REL.rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts and p.name != "HASHES.json":
            rel = p.relative_to(REL).as_posix()
            files[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    manifest = {"version": VERSION, "built_at_anchor": git_anchor(),
                "口径": "发布树=构建产物；手改即 verify FAIL（治拷贝漂移病1）",
                "files": files}
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=1),
                        encoding="utf-8")

    n_py = 0
    for p in REL.rglob("*.py"):
        if "__pycache__" in p.parts:
            continue
        py_compile.compile(str(p), doraise=True)
        n_py += 1
    report["py_compiled"] = n_py
    report["files_in_manifest"] = len(files)
    report["status"] = "BUILT"
    return report


def verify() -> dict:
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    errors = []
    actual = {p.relative_to(REL).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in REL.rglob("*")
              if p.is_file() and "__pycache__" not in p.parts and p.name != "HASHES.json"}
    for rel, sha in m["files"].items():
        if rel not in actual:
            errors.append(f"缺失: {rel}")
        elif actual[rel] != sha:
            errors.append(f"漂移: {rel}")
    for rel in actual:
        if rel not in m["files"]:
            errors.append(f"多出(构建区外新增): {rel}")
    return {"ok": not errors, "files": len(m["files"]), "errors": errors[:10]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true", help="只验 manifest，不构建")
    ns = ap.parse_args()
    if ns.verify:
        r = verify()
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return 0 if r["ok"] else 1
    r = build()
    v = verify()
    r["verify"] = v
    print(json.dumps(r, ensure_ascii=False, indent=1))
    return 0 if v["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
