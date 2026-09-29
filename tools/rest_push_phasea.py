# -*- coding: utf-8 -*-
"""rest_push_phasea.py — REST 通道推送（git smart-http 被反代阻，P-025 先例）。

v2（2026-09-28）升级（P-018/P-029/P-020 教训落地）：
  1. BASE 合法性：diff 为 0 = 异常中止（远端 tip 不在本地对象库的静默空 diff 防线）。
  2. 二进制安全：utf-8 严格解码失败 → base64 blob（不再 errors=replace 静默损坏）。
  3. blob 缓存：内容 sha1 → 远端 blob sha（tools/_rest_blob_cache.json），重试轮不再重传。
  4. 提交信息：arg 或自动取 `git log BASE..TARGET --format=%s`（不再硬编码旧战役文案）。
  5. 树 POST 耐心重试：5 次，退避 10/30/60/120/120s（HTTP 502 族）。
  6. 失败 exit 1，成功 exit 0（不再管道假绿）。
用法：py -X utf8 rest_push_phasea.py <BASE本地提交> [BRANCH] [TARGET默认master] [MSG]
"""
import base64
import hashlib
import io
import json
import os
import subprocess
import sys
import time

REPO = "master666-max/cbb-pipeline"
REPO_ROOT = r"D:\zcode专用！！！！危险！！！！！！！！！"
BASE = sys.argv[1] if len(sys.argv) > 1 else ""
BRANCH = sys.argv[2] if len(sys.argv) > 2 else "refactor/phase-a"
TARGET = sys.argv[3] if len(sys.argv) > 3 else "master"
MSG = sys.argv[4] if len(sys.argv) > 4 else ""
TMP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_rest_phasea_tmp.json")
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_rest_blob_cache.json")

if not BASE:
    print("用法：rest_push_phasea.py <BASE本地提交> [BRANCH] [TARGET] [MSG]")
    sys.exit(2)


def gh(args, input_file=None):
    cmd = ["gh", "api"] + args
    if input_file:
        cmd += ["--input", input_file]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        raise RuntimeError(f"gh fail: {' '.join(args[:3])} :: {r.stderr[:200]}")
    return json.loads(r.stdout) if r.stdout.strip() else {}


def gh_json(args, payload):
    io.open(TMP, "w", encoding="utf-8").write(json.dumps(payload, ensure_ascii=False))
    return gh(args, input_file=TMP)


os.chdir(REPO_ROOT)
rng = f"{BASE}..{TARGET}"
files = subprocess.run(["git", "diff", "--name-only", rng],
                       capture_output=True, text=True, encoding="utf-8").stdout.split()
deleted = set(subprocess.run(["git", "diff", "--name-only", "--diff-filter=D", rng],
                             capture_output=True, text=True, encoding="utf-8").stdout.split())
print(f"diff {len(files)} files (deleted {len(deleted)})  [{rng}]")
if not files and not deleted:
    print("✗ diff 为 0：BASE 可能是远端铸造哈希（不在本地对象库）——用树哈希找本地同树提交，见 P-029")
    sys.exit(2)

if not MSG:
    msgs = subprocess.run(["git", "log", rng, "--format=%s"],
                          capture_output=True, text=True, encoding="utf-8").stdout.strip().splitlines()
    MSG = " | ".join(reversed(msgs))[:2000] or "(empty)"
print(f"commit msg: {MSG[:120]}...")

cache = {}
if os.path.exists(CACHE):
    cache = json.load(io.open(CACHE, encoding="utf-8"))

for attempt in range(1, 6):
    try:
        try:
            ref = gh([f"repos/{REPO}/git/ref/heads/{BRANCH}"])
        except RuntimeError:
            ref = gh([f"repos/{REPO}/git/ref/heads/refactor/reimagine"])
        parent = ref["object"]["sha"]
        tree = gh([f"repos/{REPO}/git/commits/{parent}"])["tree"]["sha"]
        entries = []
        for i, rel in enumerate(files):
            if rel in deleted:
                entries.append({"path": rel, "mode": "100644", "type": "blob", "sha": None})
                continue
            # 条目类型分派（v1.17）：gitlink(160000) 保真传递——blob cat-file 对嵌套仓指针必 bad file
            t = subprocess.run(["git", "cat-file", "-t", f"{TARGET}:{rel}"], capture_output=True, text=True)
            if t.returncode == 0 and t.stdout.strip() == "commit":
                gsha = subprocess.run(["git", "rev-parse", f"{TARGET}:{rel}"],
                                      capture_output=True, text=True).stdout.strip()
                entries.append({"path": rel, "mode": "160000", "type": "commit", "sha": gsha})
                continue
            raw = subprocess.run(["git", "cat-file", "blob", f"{TARGET}:{rel}"],
                                 capture_output=True)
            if raw.returncode != 0:
                raise RuntimeError(f"cat-file 失败 {rel}: {raw.stderr[:100]}")
            raw = raw.stdout  # 提交内容字节级（LF 原样）——非工作树读（隔离 EOL 漂移与未提交变更）
            csha = hashlib.sha1(raw).hexdigest()
            if csha in cache:
                bsha = cache[csha]
            else:
                try:
                    text = raw.decode("utf-8")
                    payload = {"content": text, "encoding": "utf-8"}
                except UnicodeDecodeError:
                    payload = {"content": base64.b64encode(raw).decode("ascii"), "encoding": "base64"}
                io.open(TMP, "w", encoding="utf-8").write(json.dumps(payload, ensure_ascii=False))
                bsha = gh(["-X", "POST", f"repos/{REPO}/git/blobs", "--input", TMP])["sha"]
                cache[csha] = bsha
                io.open(CACHE, "w", encoding="utf-8").write(json.dumps(cache, ensure_ascii=False))
            entries.append({"path": rel, "mode": "100644", "type": "blob", "sha": bsha})
            if (i + 1) % 40 == 0:
                print(f"  blob {i+1}/{len(files)}")

        newtree = None
        for t_try, wait in enumerate([10, 30, 60, 120, 120], 1):
            try:
                newtree = gh_json(["-X", "POST", f"repos/{REPO}/git/trees"],
                                  {"base_tree": tree, "tree": entries})
                break
            except RuntimeError as e:
                if t_try == 5:
                    raise
                print(f"  树 POST 第{t_try}次失败（{str(e)[:80]}），退避 {wait}s…")
                time.sleep(wait)
        commit = gh_json(["-X", "POST", f"repos/{REPO}/git/commits"],
                         {"message": MSG, "tree": newtree["sha"], "parents": [parent]})
        try:
            gh_json(["-X", "POST", f"repos/{REPO}/git/refs"],
                    {"ref": f"refs/heads/{BRANCH}", "sha": commit["sha"]})
        except RuntimeError:
            gh_json(["-X", "PATCH", f"repos/{REPO}/git/refs/heads/{BRANCH}"],
                    {"sha": commit["sha"], "force": False})
        time.sleep(2)
        chk = gh([f"repos/{REPO}/commits/{commit['sha']}"])
        print(f"✓ 已推送远端确认 {chk['sha'][:7]} → {BRANCH}")
        sys.exit(0)
    except Exception as e:
        print(f"第{attempt}轮失败：{str(e)[:180]}；重试")
        time.sleep(10)
print("✗ 五轮未成功")
sys.exit(1)
