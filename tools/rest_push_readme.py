# -*- coding: utf-8 -*-
"""rest_push_readme.py — 经 Git Data REST 更新 cbb-pipeline 仓 README（git 协议被阻时的通道）"""
import io, json, os, subprocess, time

REPO = "master666-max/cbb-pipeline"
SRC = r"C:\Users\26672\AppData\Local\Temp\cbb-pipeline-pub\README.md"
TMP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_rest_readme_tmp.json")

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

for i in range(1, 9):
    try:
        ref = gh([f"repos/{REPO}/git/refs/heads/main"])
        parent = ref["object"]["sha"]
        tree = gh([f"repos/{REPO}/git/commits/{parent}"])["tree"]["sha"]
        content = io.open(SRC, encoding="utf-8").read()
        blob = gh(["-X", "POST", f"repos/{REPO}/git/blobs",
                   "-f", f"content={content}", "-f", "encoding=utf-8"])
        newtree = gh_json(["-X", "POST", f"repos/{REPO}/git/trees"],
                          {"base_tree": tree,
                           "tree": [{"path": "README.md", "mode": "100644",
                                     "type": "blob", "sha": blob["sha"]}]})
        commit = gh_json(["-X", "POST", f"repos/{REPO}/git/commits"],
                         {"message": "docs: plain-language README (人话版门面) — 治什么病/怎么治/三步开跑/术语对照表",
                          "tree": newtree["sha"], "parents": [parent]})
        gh_json(["-X", "PATCH", f"repos/{REPO}/git/refs/heads/main"],
                {"sha": commit["sha"], "force": False})
        time.sleep(2)
        chk = gh([f"repos/{REPO}/commits/{commit['sha']}"])
        print(f"✓ README 已更新并远端确认 {chk['sha'][:7]}")
        break
    except Exception as e:
        print(f"第{i}轮失败：{str(e)[:180]}；重试")
        time.sleep(4)
else:
    print("✗ 八轮未成功")
