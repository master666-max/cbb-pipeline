# -*- coding: utf-8 -*-
"""rest_push_phasea.py — REST 通道推送 Phase A（git smart-http 被反代阻，P-025 先例）。
基 = 远端 refactor/reimagine tip fd0fd6a（= 本地 v2-baseline），增量 146 件。
"""
import io, json, os, subprocess, time

REPO = "master666-max/cbb-pipeline"
REPO_ROOT = r"D:\zcode专用！！！！危险！！！！！！！！！"
BASE = "fd0fd6a"
BRANCH = "refactor/phase-a"
TMP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_rest_phasea_tmp.json")

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
files = subprocess.run(["git", "diff", "--name-only", "v2-baseline..master"],
                       capture_output=True, text=True, encoding="utf-8").stdout.split()
deleted = set(subprocess.run(["git", "diff", "--name-only", "--diff-filter=D",
                              "v2-baseline..master"],
                             capture_output=True, text=True, encoding="utf-8").stdout.split())
print(f"diff {len(files)} files (deleted {len(deleted)})")

for attempt in range(1, 4):
    try:
        ref = gh([f"repos/{REPO}/git/ref/heads/refactor/reimagine"])
        parent = ref["object"]["sha"]
        tree = gh([f"repos/{REPO}/git/commits/{parent}"])["tree"]["sha"]
        entries = []
        for i, rel in enumerate(files):
            if rel in deleted:
                entries.append({"path": rel, "mode": "100644", "type": "blob", "sha": None})
                continue
            content = io.open(os.path.join(REPO_ROOT, rel), "r",
                              encoding="utf-8", errors="replace").read()
            io.open(TMP, "w", encoding="utf-8").write(
                json.dumps({"content": content, "encoding": "utf-8"}, ensure_ascii=False))
            blob = gh(["-X", "POST", f"repos/{REPO}/git/blobs", "--input", TMP])
            entries.append({"path": rel, "mode": "100644", "type": "blob", "sha": blob["sha"]})
            if (i + 1) % 40 == 0:
                print(f"  blob {i+1}/{len(files)}")
        newtree = gh_json(["-X", "POST", f"repos/{REPO}/git/trees"],
                          {"base_tree": tree, "tree": entries})
        msg = ("phaseA: 地基收口——契约v3(profiles六库+断言/陈述/mutable/immutable)+store写入决策树五分支"
               "(互补陈述/失效记账/闸1闸2)+at全链强制+gate候选态输入档+NLI双通道(本地LLM活体冒烟真通)+运行契约闸;"
               "604积压重分流真库执行336自动纳/268人工桶/信息保全186,预注册四判据全过(dry-run一致/仅剩人工桶/对样20/20/账本零新错);"
               "反例包6转绿7移交;24测试+PROVEN锚+金丝雀全绿;彩排4轮抓3bug真库零事故")
        commit = gh_json(["-X", "POST", f"repos/{REPO}/git/commits"],
                         {"message": msg, "tree": newtree["sha"], "parents": [parent]})
        try:
            gh_json(["-X", "POST", f"repos/{REPO}/git/refs"],
                    {"ref": f"refs/heads/{BRANCH}", "sha": commit["sha"]})
        except RuntimeError:
            gh_json(["-X", "PATCH", f"repos/{REPO}/git/refs/heads/{BRANCH}"],
                    {"sha": commit["sha"], "force": False})
        time.sleep(2)
        chk = gh([f"repos/{REPO}/commits/{commit['sha']}"])
        print(f"✓ Phase A 已推送远端确认 {chk['sha'][:7]} → {BRANCH}")
        break
    except Exception as e:
        print(f"第{attempt}轮失败：{str(e)[:180]}；重试")
        time.sleep(5)
else:
    print("✗ 三轮未成功")
