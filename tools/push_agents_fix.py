# -*- coding: utf-8 -*-
"""push_agents_fix.py — 补推 AGENTS.md 被测件表的本线行（幂等守卫误跳过的第二处插入修复）"""
import base64, io, json, subprocess, time

REPO = "master666-max/research-hub"
TMP = r"C:\Users\26672\AppData\Local\Temp\rest_push_f4_tmp.json"
ANCHOR = "mem_common.py` 为忠实复刻） |"
MARK = "九前缀冻结档案族"
ROW = "| `F4-档案冻结族/` | 九前缀冻结档案族（**本机 `大审查\\` 嵌套仓**，只读引用——冻结族文件与审计区账本均不复制，只锚 commit + 哈希） |"

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

for attempt in range(6):
    try:
        parent = head()
        r = gh(["repos/%s/contents/AGENTS.md" % REPO])
        text = base64.b64decode(r["content"]).decode("utf-8")
        if MARK in text:
            print("already present; nothing to do")
            raise SystemExit(0)
        lines = text.split("\n")
        idx = None
        for i, ln in enumerate(lines):
            if ANCHOR in ln:
                idx = i
                break
        if idx is None:
            raise SystemExit("anchor missing")
        lines.insert(idx + 1, ROW)
        new = "\n".join(lines)
        sha = blob(new.encode("utf-8"))
        ghead = gh(["repos/%s/git/commits/%s" % (REPO, parent)])
        tree = gh(["-X", "POST", "repos/%s/git/trees" % REPO],
                  {"base_tree": ghead["tree"]["sha"],
                   "tree": [{"path": "AGENTS.md", "mode": "100644", "type": "blob", "sha": sha}]})
        commit = gh(["-X", "POST", "repos/%s/git/commits" % REPO],
                    {"message": "F4线：AGENTS 被测件表补入本线行（修复：上一提交幂等守卫误跳过第二处插入）",
                     "tree": tree["sha"], "parents": [parent]})
        gh(["-X", "PATCH", "repos/%s/git/refs/heads/main" % REPO],
           {"sha": commit["sha"], "force": False})
        print("fix commit:", commit["sha"])
        break
    except SystemExit:
        raise
    except Exception as e:
        print("retry %d: %s" % (attempt, e))
        time.sleep(3)
