# -*- coding: utf-8 -*-
"""rest_push_f4.py — research-hub「F4-档案冻结族」建线推送（GitHub REST API 通道，gh）
两阶段：①目录 22 件（不受根表并发影响）；②根 README/AGENTS 锚点插入本线行（幂等，抗并发）。
依据：本机 git push 被全局 insteadOf 改写为 SSH（坑18）→ 走 api.github.com；先例 rest_push_cbb.py。
"""
import base64, io, json, os, subprocess, time

REPO = "master666-max/research-hub"
STAGE = r"C:\Users\26672\AppData\Local\Temp\research-hub"
BASE = "F4-档案冻结族"
TMP = r"C:\Users\26672\AppData\Local\Temp\rest_push_f4_tmp.json"

ANCHOR_F1ROW = "`自演化推演-F1实验族/START-HERE.md` |"
ANCHOR_MEMCOMMON = "mem_common.py` 为忠实复刻） |"

ROW_README = "| `F4-档案冻结族/` | **档案治理位**（自演化知识库体系 F4 工位）：九前缀档案族冻结登记（**FROZEN-READONLY**，97 节点/1044 claim：DS/CB/QWEN/GLM/PLAN/REVIEW/SYN/PART1/spur30）· 触发器生命周期与活引用「冻结不解引」（RADAR 归一已兑现 / DS E57 corr=1 端点已取证闭案；余 P-A4/P-D4 在位）· 家族整合记账五步法 + 开工与核证三步（P-019/PT-018）· 跨区派发回执链全史（发出者：**F4 工位会话（ZCode）**） | 九前缀冻结维持、审计区账本零接触；两触发器在位未触发；**纯值守态**（22 件自足镜像 + 哈希登记表已备，读完即开工） | `F4-档案冻结族/START-HERE.md` |"

ROW_AGENTS = "| `F4-档案冻结族/` | **档案治理位**（自演化知识库体系 F4 工位）：九前缀档案族冻结登记（FROZEN-READONLY）· 触发器与活引用生命周期（冻结不解引：RADAR 归一已兑现 / DS E57 端点已取证闭案）· 家族整合记账五步法与开工三步（P-019/PT-018）· 跨区派发回执链<br>_发出者：F4 工位会话（ZCode）_ | `F4-档案冻结族/START-HERE.md` |"

ROW_ANCHORS2 = "| `F4-档案冻结族/` | 九前缀冻结档案族（**本机 `大审查\\` 嵌套仓**，只读引用——冻结族文件与审计区账本均不复制，只锚 commit + 哈希） |"


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
    r = gh(["-X", "POST", "repos/%s/git/blobs" % REPO],
           {"content": base64.b64encode(data).decode("ascii"), "encoding": "base64"})
    return r["sha"]


def head():
    return gh(["repos/%s/git/refs/heads/main" % REPO])["object"]["sha"]


def commit_tree(entries, message, parent):
    ghead = gh(["repos/%s/git/commits/%s" % (REPO, parent)])
    tree = gh(["-X", "POST", "repos/%s/git/trees" % REPO],
              {"base_tree": ghead["tree"]["sha"], "tree": entries})
    commit = gh(["-X", "POST", "repos/%s/git/commits" % REPO],
                {"message": message, "tree": tree["sha"], "parents": [parent]})
    csha = commit["sha"]
    gh(["-X", "PATCH", "repos/%s/git/refs/heads/main" % REPO], {"sha": csha, "force": False})
    return csha


def collect_dir_files():
    root = os.path.join(STAGE, BASE)
    out = []
    for dp, dn, fns in os.walk(root):
        for fn in fns:
            full = os.path.join(dp, fn)
            out.append((os.path.relpath(full, STAGE).replace(os.sep, "/"), full))
    out.sort()
    return out


def phase1():
    files = collect_dir_files()
    print("phase1: %d files" % len(files))
    for attempt in range(6):
        try:
            parent = head()
            entries = []
            for rel, full in files:
                sha = blob(io.open(full, "rb").read())
                entries.append({"path": rel, "mode": "100644", "type": "blob", "sha": sha})
                print("  blob %s %s" % (rel, sha[:7]))
            csha = commit_tree(
                entries,
                "F4线：建线——档案治理位（档案冻结族）自足镜像 22 件（START-HERE/INDEX/接手契约/"
                "真源锚/哈希登记表/登记与取证×2/方法论×4/生态与状态×2/下发链×7/SOP）；"
                "发出者=F4工位会话（ZCode）",
                parent)
            print("phase1 commit:", csha)
            return csha
        except Exception as e:
            print("retry %d: %s" % (attempt, e))
            time.sleep(3)
    raise SystemExit("phase1 failed")


def fetch_text(path):
    r = gh(["repos/%s/contents/%s" % (REPO, path)])
    return base64.b64decode(r["content"]).decode("utf-8")


def insert_after(text, anchor, row):
    """锚点行后插入；已含本线行→(text, False, 'present'); 锚点缺失→(text, None, 'missing')"""
    if "F4-档案冻结族/" in text:
        return text, False, "present"
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        if anchor in ln:
            lines.insert(i + 1, row)
            return "\n".join(lines), True, "inserted"
    return text, None, "missing"


def phase2():
    tasks = {
        "README.md": [(ANCHOR_F1ROW, ROW_README)],
        "AGENTS.md": [(ANCHOR_F1ROW, ROW_AGENTS), (ANCHOR_MEMCOMMON, ROW_ANCHORS2)],
    }
    for attempt in range(6):
        try:
            parent = head()
            entries = []
            for path, ins in sorted(tasks.items()):
                text = fetch_text(path)
                if "F4-档案冻结族/" in text:
                    print("  %s: already has F4 row, skip" % path)
                    continue
                ok = True
                for anchor, row in ins:
                    text, did, why = insert_after(text, anchor, row)
                    if did is None:
                        print("  %s: anchor MISSING (%s) — abort this file" % (path, anchor[:40]))
                        ok = False
                        break
                if not ok:
                    continue
                sha = blob(text.encode("utf-8"))
                entries.append({"path": path, "mode": "100644", "type": "blob", "sha": sha})
                print("  update %s -> %s" % (path, sha[:7]))
            if not entries:
                print("phase2: nothing to push")
                return None
            csha = commit_tree(
                entries,
                "F4线：根表只加本线行（README 研究线表 + AGENTS 研究线表 + 被测件表；"
                "发出者=F4工位会话（ZCode）；只加本线行、不动他线行/表）",
                parent)
            print("phase2 commit:", csha)
            return csha
        except Exception as e:
            print("retry %d: %s" % (attempt, e))
            time.sleep(3)
    raise SystemExit("phase2 failed")


if __name__ == "__main__":
    c1 = phase1()
    c2 = phase2()
    print("DONE phase1=%s phase2=%s" % (c1, c2))
