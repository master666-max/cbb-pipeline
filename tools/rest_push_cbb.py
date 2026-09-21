# -*- coding: utf-8 -*-
"""rest_push_cbb.py — 绕开 git 协议，经 GitHub Git Data REST API 推送 CBB 三根文件
用 api.github.com（gh api 通道，本机稳定），竞态时自动重试。
"""
import base64, io, json, os, subprocess, sys, time

REPO = "master666-max/research-hub"
BASE = "CBB-正典库构建"
FILES = ["START-HERE.md", "INDEX.md", "被测件锚.md"]
SRC = r"C:\Users\26672\AppData\Local\Temp\research-hub"

def gh(args, input_file=None):
    cmd = ["gh", "api"] + args
    if input_file:
        cmd += ["--input", input_file]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        raise RuntimeError(f"gh fail: {' '.join(args[:3])} :: {r.stderr[:300]}")
    return json.loads(r.stdout) if r.stdout.strip() else {}

TMP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_rest_push_tmp.json")

def gh_json(args, payload):
    io.open(TMP, "w", encoding="utf-8").write(json.dumps(payload, ensure_ascii=False))
    return gh(args, input_file=TMP)

def attempt(round_no):
    ref = gh([f"repos/{REPO}/git/refs/heads/main"])
    parent = ref["object"]["sha"]
    ghead = gh([f"repos/{REPO}/git/commits/{parent}"])
    tree = ghead["tree"]["sha"]
    print(f"[{round_no}] parent={parent[:7]} tree={tree[:7]}")
    # 幂等：若三文件已在树中则检查内容是否一致（简化：直接覆盖式新建 blob/tree/commit）
    entries = []
    for f in FILES:
        p = os.path.join(SRC, BASE, f)
        content = io.open(p, encoding="utf-8").read()
        blob = gh(["-X", "POST", f"repos/{REPO}/git/blobs", "-f", f"content={content}", "-f", "encoding=utf-8"])
        entries.append({"path": f"{BASE}/{f}", "mode": "100644", "type": "blob", "sha": blob["sha"]})
        print(f"  blob {f} -> {blob['sha'][:7]}")
    newtree = gh_json(["-X", "POST", f"repos/{REPO}/git/trees"],
                      {"base_tree": tree, "tree": entries})
    commit = gh_json(["-X", "POST", f"repos/{REPO}/git/commits"],
                     {"message": "CBB线：补入三根文件（START-HERE/INDEX/被测件锚）——只加本线文件，不改他线行/表",
                      "tree": newtree["sha"], "parents": [parent]})
    csha = commit["sha"]
    print(f"  commit -> {csha[:7]}")
    # 更新 ref（fast-forward only；被抢则异常重试）
    gh_json(["-X", "PATCH", f"repos/{REPO}/git/refs/heads/main"], {"sha": csha, "force": False})
    return csha

for i in range(1, 9):
    try:
        csha = attempt(i)
        time.sleep(2)
        chk = gh([f"repos/{REPO}/commits/{csha}"])
        print(f"✓ 远端已确认提交 {chk['sha'][:7]}")
        break
    except Exception as e:
        print(f"第{i}轮失败：{str(e)[:200]}；重试")
        time.sleep(4)
else:
    print("✗ 八轮未成功")
