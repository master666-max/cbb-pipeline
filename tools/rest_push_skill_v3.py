# -*- coding: utf-8 -*-
"""rest_push_skill_v3.py — R4 修复批同步到 GitHub 技能仓（cbb-pipeline）。

清单=本批同步的 18 件（17 更新 + 1 新增）。推后逐件回读远端内容做 sha256 校验
（推了≠推对了：以字节一致为准）。通道沿用 Git Data REST（git 协议在部分网络受阻）。
"""
import hashlib
import io
import json
import os
import subprocess
import time

REPO = "master666-max/cbb-pipeline"
SRC = r"D:\zcode专用！！！！危险！！！！！！！！！\正典库构建系统\cbb-pipeline-skill\cbb-pipeline"
FILES = [
    "references/审查与收口.md",
    "scripts/cbb/cbb-store/cbb_store.py",
    "scripts/cbb/cbb-store/test_cbb_store.py",
    "scripts/cbb/cbb-anchor/cbb_anchor.py",
    "scripts/cbb/cbb-anchor/test_cbb_anchor.py",
    "scripts/cbb/cbb-coordinate/cbb_coordinate.py",
    "scripts/cbb/cbb-coordinate/test_cbb_coordinate.py",
    "scripts/cbb/cbb-extract/cbb_extract.py",
    "scripts/cbb/cbb-extract/test_cbb_extract.py",
    "scripts/cbb/tools/矛盾分流.py",
    "scripts/cbb/tools/test_矛盾分流.py",
    "scripts/cbb/tools/graphiti_ready.py",
    "scripts/cbb/tools/test_graphiti_ready.py",
    "scripts/cbb/tools/ledger_chain.py",
    "scripts/cbb/tools/test_ledger_chain.py",
    "scripts/cbb/tools/neo4j_export.py",
    "scripts/cbb/tools/test_neo4j_export.py",
    "scripts/cbb/tools/embed_dedup_scan.py",
]
TMP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_rest_skill_v3_tmp.json")


def gh(args, input_file=None):
    cmd = ["gh", "api"] + args
    if input_file:
        cmd += ["--input", input_file]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        raise RuntimeError(f"gh fail: {' '.join(args[:3])} :: {r.stderr[:300]}")
    return json.loads(r.stdout) if r.stdout.strip() else {}


def gh_json(args, payload):
    io.open(TMP, "w", encoding="utf-8").write(json.dumps(payload, ensure_ascii=False))
    return gh(args, input_file=TMP)


MSG = ("fix: 审计 R4 修复批同步（A2 原子写+撕裂 JSON 披露 / A4 有效态轨迹 / A5 裁决差集+台账幂等 / "
       "A6 哨兵D口径 / A7 版本数值排序 / A8 BOM 剥离 / A9 跳过块登记 / C1 账本缓存+校验读盘 / "
       "A13 端口口径对齐）+ 18 件含各反例测试；embed_dedup_scan 补齐超长路径/dict 脏行防御；"
       "审查与收口.md 增『账本前置/后置门』纪律")

for i in range(1, 9):
    try:
        ref = gh([f"repos/{REPO}/git/refs/heads/main"])
        parent = ref["object"]["sha"]
        tree = gh([f"repos/{REPO}/git/commits/{parent}"])["tree"]["sha"]
        entries, local_sha = [], {}
        for rel in FILES:
            content = io.open(os.path.join(SRC, *rel.split("/")), encoding="utf-8",
                              newline="").read()
            local_sha[rel] = hashlib.sha256(content.encode("utf-8")).hexdigest()
            blob = gh(["-X", "POST", f"repos/{REPO}/git/blobs",
                       "-f", f"content={content}", "-f", "encoding=utf-8"])
            entries.append({"path": rel, "mode": "100644", "type": "blob", "sha": blob["sha"]})
            print(f"  blob OK {rel} ({len(content)}B)")
        newtree = gh_json(["-X", "POST", f"repos/{REPO}/git/trees"],
                          {"base_tree": tree, "tree": entries})
        commit = gh_json(["-X", "POST", f"repos/{REPO}/git/commits"],
                         {"message": MSG, "tree": newtree["sha"], "parents": [parent]})
        gh_json(["-X", "PATCH", f"repos/{REPO}/git/refs/heads/main"],
                {"sha": commit["sha"], "force": False})
        time.sleep(2)
        chk = gh([f"repos/{REPO}/commits/{commit['sha']}"])
        print(f"✓ 推送确认 {chk['sha'][:7]}")

        # 回读校验：逐件拿远端 blob 内容算 sha256，必须与本地一致
        bad = []
        for rel in FILES:
            tree_item = next(t for t in chk["files"] + [] if False) if False else None
            blob = gh([f"repos/{REPO}/contents/{rel}?ref={chk['sha']}"])
            remote = subprocess.run(
                ["gh", "api", f"repos/{REPO}/git/blobs/{blob['sha']}"],
                capture_output=True, text=True, encoding="utf-8")
            data = json.loads(remote.stdout)
            import base64
            content = base64.b64decode(data["content"]).decode("utf-8")
            if hashlib.sha256(content.encode("utf-8")).hexdigest() != local_sha[rel]:
                bad.append(rel)
        if bad:
            raise RuntimeError(f"回读校验不一致：{bad}")
        print(f"✓ 回读校验 {len(FILES)}/{len(FILES)} 件字节一致")
        break
    except Exception as e:
        print(f"第{i}轮失败：{str(e)[:200]}；重试")
        time.sleep(4)
else:
    print("✗ 八轮未成功")
