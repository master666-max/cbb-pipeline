# -*- coding: utf-8 -*-
"""push_f4_sync.py — F4镜像对账波同步推送（目录一次提交 + README 本线行口径更新）"""
import base64, io, json, os, subprocess, time

REPO = "master666-max/research-hub"
STAGE = r"C:\Users\26672\AppData\Local\Temp\research-hub"
BASE = "F4-档案冻结族"
TMP = r"C:\Users\26672\AppData\Local\Temp\rest_push_f4_tmp.json"

def gh(args, payload=None):
    cmd = ["gh", "api"] + args
    if payload is not None:
        io.open(TMP, "w", encoding="utf-8").write(json.dumps(payload, ensure_ascii=False))
        cmd += ["--input", TMP]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        raise RuntimeError("gh fail: %s :: %s" % (" ".join(args[:4]), r.stderr[:400]))
    return json.loads(r.stdout) if r.stdout.strip() else {}

def blob(data):
    return gh(["-X", "POST", "repos/%s/git/blobs" % REPO],
              {"content": base64.b64encode(data).decode("ascii"), "encoding": "base64"})["sha"]

def head():
    return gh(["repos/%s/git/refs/heads/main" % REPO])["object"]["sha"]

def commit_tree(entries, message, parent):
    ghead = gh(["repos/%s/git/commits/%s" % (REPO, parent)])
    tree = gh(["-X", "POST", "repos/%s/git/trees" % REPO],
              {"base_tree": ghead["tree"]["sha"], "tree": entries})
    commit = gh(["-X", "POST", "repos/%s/git/commits" % REPO],
                {"message": message, "tree": tree["sha"], "parents": [parent]})
    gh(["-X", "PATCH", "repos/%s/git/refs/heads/main" % REPO], {"sha": commit["sha"], "force": False})
    return commit["sha"]

# ---------- 阶段1：目录全量（变更件自然入树） ----------
def phase1():
    root = os.path.join(STAGE, BASE)
    files = []
    for dp, dn, fns in os.walk(root):
        for fn in fns:
            full = os.path.join(dp, fn)
            files.append((os.path.relpath(full, STAGE).replace(os.sep, "/"), full))
    files.sort()
    for attempt in range(6):
        try:
            parent = head()
            entries = []
            for rel, full in files:
                sha = blob(io.open(full, "rb").read())
                entries.append({"path": rel, "mode": "100644", "type": "blob", "sha": sha})
            csha = commit_tree(entries,
                "F4线：对账波镜像同步（用户令俯瞰对账后）——口径刷新至 1,143 claim（声明§八，基准时点标注）"
                "+新件 生态与状态/状态快照-20260930；START-HERE/INDEX/哈希登记表随刷新；%d 件全量重推（变更自然入树）" % len(files),
                parent)
            print("phase1 commit:", csha)
            return csha
        except Exception as e:
            print("retry %d: %s" % (attempt, e)); time.sleep(3)
    raise SystemExit("phase1 failed")

# ---------- 阶段2：README 本线行口径更新 ----------
OLD = "97 节点/1044 claim：DS/CB/QWEN/GLM/PLAN/REVIEW/SYN/PART1/spur30"
NEW = "97 节点/1,143 claim（09-30 复算；基准 1,044）：DS/CB/QWEN/GLM/PLAN/REVIEW/SYN/PART1/spur30"

def phase2():
    for attempt in range(6):
        try:
            parent = head()
            r = gh(["repos/%s/contents/README.md" % REPO])
            text = base64.b64decode(r["content"]).decode("utf-8")
            if NEW in text:
                print("README already updated; skip"); return None
            n = text.count(OLD)
            assert n == 1, "README count=%d (expect 1)" % n
            text = text.replace(OLD, NEW)
            sha = blob(text.encode("utf-8"))
            csha = commit_tree([{"path": "README.md", "mode": "100644", "type": "blob", "sha": sha}],
                "F4线：README 本线行口径更新（97 节点/1,143 claim·09-30 复算；仅改本行）", parent)
            print("phase2 commit:", csha)
            return csha
        except Exception as e:
            print("retry %d: %s" % (attempt, e)); time.sleep(3)
    raise SystemExit("phase2 failed")

if __name__ == "__main__":
    print("P1:", phase1())
    print("P2:", phase2())
