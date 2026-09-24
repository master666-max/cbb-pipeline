# -*- coding: utf-8 -*-
"""图库隔离.py — 给本项目起一个独立的 Neo4j 实例（解决 community 版无多库隔离）

为什么要它：Neo4j 社区版只有一个用户库 ⇒ "给本书单开 database"做不到；唯一真隔离方式是**另起实例**。
靠 `group_id` 属性 + 每条查询记得过滤是纸闸门——漏一个 WHERE 就横跨两个项目扫实体，
而且返回的是"零孤悬/零矛盾"，与做对时完全同形（本机实测：共享实例 901 节点，0 个属本书）。

三条硬规矩（都写进代码，不靠自觉）：
  1. **只绑回环**：发布成 `127.0.0.1:<端口>`，绝不 `0.0.0.0`——本机就吃过撞端口的亏
     （LM Studio 绑 127.0.0.1:8080、Docker 绑 0.0.0.0:8080，前者一停流量就掉进后者的 nginx 拿 404）。
  2. **端口先预检再占用**：与已在听端口、与其他项目实例的端口都要错开；撞了就报冲突并给出建议值，不许硬抢。
  3. **口令不落盘、不进 argv**：`--auth-env` 指定环境变量名（默认 NEO4J_ISOLATED_PASSWORD）；
     不填则 `--auth-none` 显式声明"无认证 + 仅回环"，两者都不给就拒绝创建。
     口令绝不写进命令行（`docker ps`/进程表会泄露），统一走 `--env-file`，文件放在仓外并只提示路径。

用法：
  py -X utf8 图库隔离.py plan   --project-token zhongmo-canon            # 只打计划，什么都不动
  py -X utf8 图库隔离.py create --project-token zhongmo-canon --auth-none --run
  py -X utf8 图库隔离.py verify --project-token zhongmo-canon            # 建完/每批收口时复验
  py -X utf8 图库隔离.py env    --project-token zhongmo-canon            # 打出该导出的 NEO4J_HTTP 等

verify 的判据就是 环境自检 里 G4 那一条，两边共用 `ownership_verdict()`：
  空库 / 全部节点带本项目标记 ⇒ 合法；出现任一 foreign 节点 ⇒ 不合法（这正是"能用"与"能连"的差别）。
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import time
import urllib.request
from pathlib import Path

IMAGE_DEFAULT = "neo4j:5"
HTTP_BASE, BOLT_BASE = 7474, 7687          # 容器内端口（discovery 会自报这两个值，别当真值用）


def port_free(port: int, host: str = "127.0.0.1") -> bool:
    s = socket.socket()
    s.settimeout(1.0)
    try:
        return s.connect_ex((host, port)) != 0        # 连不上 = 没人听 = 空闲
    finally:
        s.close()


def pick_ports(http_want: int, bolt_want: int, taken: set[int]) -> tuple[int, int]:
    """端口预检：撞了就往后找空闲对，并保留 http/bolt 相差 1 的习惯；找到 40 个窗口内为止。"""
    h, b = http_want, bolt_want
    for _ in range(40):
        busy = {p for p in (h, b) if p in taken or not port_free(p)}
        if not busy:
            return h, b
        h, b = h + 2, b + 2
    raise RuntimeError(f"端口窗口内无空闲对（从 {http_want} 起）；已占用提示：{sorted(taken)[:12]}")


def build_command(name: str, http_port: int, bolt_port: int, volume: str,
                  auth_env: str | None, auth_none: bool, image: str = IMAGE_DEFAULT,
                  env_file: str | None = None) -> list[str]:
    if not auth_none and not auth_env:
        raise ValueError("必须二选一：--auth-env <变量名> 或 --auth-none（无认证仅允许回环暴露）")
    if not auth_none and env_file is None:
        raise ValueError("带口令时必须给 --env-file：口令不得出现在命令行或 docker inspect 里")
    cmd = ["docker", "run", "-d", "--name", name,
           "--publish", f"127.0.0.1:{http_port}:7474",
           "--publish", f"127.0.0.1:{bolt_port}:7687",
           "--volume", f"{volume}:/data",
           "-e", "NEO4J_dbms_memory_heap_max__size=1G",
           "-e", "NEO4J_server_memory_pagecache_size=512M"]
    if auth_none:
        cmd += ["-e", "NEO4J_AUTH=neo4j/none"]
    else:
        cmd += ["--env-file", env_file]                 # NEO4J_AUTH 由仓外 env 文件提供
    return cmd + [image]


def http_query(base: str, statement: str, user: str | None = None, password: str | None = None,
               timeout: float = 15.0) -> dict:
    import base64
    req = urllib.request.Request(base.rstrip("/") + "/db/neo4j/tx/commit",
                                 data=json.dumps({"statements": [{"statement": statement}]},
                                                 ensure_ascii=False).encode(),
                                 headers={"Content-Type": "application/json"})
    if password:
        req.add_header("Authorization", "Basic " + base64.b64encode(
            f"{user or 'neo4j'}:{password}".encode()).decode())
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.loads(r.read().decode("utf-8", "ignore"))
    errs = [e for e in d.get("errors", []) if e]
    if errs:
        raise RuntimeError(f"{errs[0].get('code')}: {str(errs[0].get('message'))[:80]}")
    res = (d.get("results") or [{}])[0]
    return {"columns": res.get("columns"), "rows": [row["row"] for row in res.get("data", [])]}


def ownership_verdict(total: int, owned: int, foreign_groups: dict[str, int], token: str) -> dict:
    """图归属判据（与 环境自检.py 的 G4 同一套规则，一份规则两载体）。"""
    if total == 0:
        st, note = "LEGIT", f"空库，尚无任何项目写入 ⇒ 本项目独占可用（token={token}）"
    elif total > 0 and owned == 0 and not foreign_groups:
        st, note = "UNDETERMINED", (f"库有 {total} 节点但归属分布零回行 ⇒ 未判定；"
                                    "未判定不等于干净，只许走文件兜底或换实例")
    elif not foreign_groups:
        st, note = "LEGIT", f"{total} 个节点全部带本项目标记 ⇒ 归属干净"
    else:
        top = "、".join(f"{g}×{c}" for g, c in sorted(foreign_groups.items(), key=lambda x: -x[1])[:4])
        st = "FOREIGN"
        note = (f"库内出现非本项目节点 {sum(foreign_groups.values())}/{total}（{top}）"
                "⇒ 该实例不是本书独占，跨库巡检会产出假干净；须换实例或重建空实例")
    return {"verdict": st, "token": token, "总节点": total, "本项目节点": owned,
            "他项目分布": foreign_groups, "结论": note}


def probe(base: str, token: str, user: str | None = None, password: str | None = None) -> dict:
    """读实况并给归属判定。auth=none 的实例直接不带凭证；带凭证而 401 时如实报不可判。"""
    try:
        total = int(http_query(base, "MATCH (n) RETURN count(n) AS c", user, password)["rows"][0][0])
        rows = http_query(base, "MATCH (n) RETURN coalesce(n.group_id, n.canon_group, '<无标记>') AS g, "
                                "count(*) AS c", user, password)["rows"]
    except Exception as e:
        return {"verdict": "UNREACHABLE", "note": f"{type(e).__name__} {str(e)[:80]}", "uri": base}
    groups = {g: int(c) for g, c in rows}
    foreign = {g: c for g, c in groups.items() if g not in (token, "<无标记>")}
    untagged = groups.get("<无标记>", 0)
    if untagged:
        foreign["<无标记>"] = untagged            # 无标记节点同样算不干净：不能假定它属于谁
    return ownership_verdict(total, groups.get(token, 0), foreign, token)


def instance_name(token: str) -> str:
    return "neo4j-" + token.strip("/").replace("_", "-").lower()[:40]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="本项目独占 Neo4j 实例的创建与复验")
    ap.add_argument("action", choices=["plan", "create", "verify", "env"])
    ap.add_argument("--project-token", required=True)
    ap.add_argument("--http-port", type=int, default=7697)
    ap.add_argument("--bolt-port", type=int, default=7696)
    ap.add_argument("--auth-env", default="NEO4J_ISOLATED_PASSWORD")
    ap.add_argument("--auth-none", action="store_true", help="无认证（仅回环暴露时才允许）")
    ap.add_argument("--env-file", default=None)
    ap.add_argument("--image", default=IMAGE_DEFAULT)
    ap.add_argument("--run", action="store_true", help="create 时真的执行 docker run（否则只打计划）")
    ap.add_argument("--cred-out", default=None, help="归属凭据落盘路径（不含任何口令）")
    ns = ap.parse_args(argv)

    name, vol = instance_name(ns.project_token), f"cbb-graph-{ns.project_token}"
    taken = {7694, 7695}                                   # 本机 step0 实例已占
    h, b = pick_ports(ns.http_port, ns.bolt_port, taken)
    base = f"http://127.0.0.1:{h}"

    if ns.action in ("plan", "create"):
        auth_none = ns.auth_none or not os.environ.get(ns.auth_env)
        cmd = build_command(name, h, b, vol, ns.auth_env, auth_none, ns.image, ns.env_file)
        printed = list(cmd)
        print(json.dumps({"实例名": name, "卷": vol, "HTTP": base, "bolt": f"neo4j://127.0.0.1:{b}",
                          "端口预检": f"{h}/{b} 空闲（已避开 {sorted(taken)}）",
                          "认证": "none（仅回环）" if auth_none else f"env-file:{ns.env_file}",
                          "命令": printed}, ensure_ascii=False, indent=1))
        if ns.action == "plan":
            return 0
        if not ns.run:
            print("（未加 --run ⇒ 只打计划，什么都没创建）")
            return 0
        import subprocess
        r = subprocess.run(cmd, capture_output=True, text=True)
        print("docker run rc=%s %s" % (r.returncode, (r.stderr or r.stdout).strip()[:200]))
        if r.returncode:
            return 1
        for _ in range(30):                                # 等就绪，最长 60s
            time.sleep(2)
            p = probe(base, ns.project_token, password=None if auth_none else os.environ.get(ns.auth_env))
            if p.get("verdict") != "UNREACHABLE":
                break
        p = probe(base, ns.project_token, password=None if auth_none else os.environ.get(ns.auth_env))
        p.update({"实例名": name, "uri": base, "instrument_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
        print(json.dumps(p, ensure_ascii=False, indent=1))
        if ns.cred_out:
            Path(ns.cred_out).parent.mkdir(parents=True, exist_ok=True)
            Path(ns.cred_out).write_text(json.dumps(p, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
        return 0 if p.get("verdict") == "LEGIT" else 1

    pw = None if ns.auth_none else os.environ.get(ns.auth_env)
    if ns.action == "env":
        print("setx NEO4J_HTTP \"%s\"\nsetx NEO4J_PASSWORD \"<与 env 文件同一个值，勿写进脚本>\"%s"
              % (base, "" if pw is None else ""))
        return 0
    p = probe(base, ns.project_token, password=pw)
    print(json.dumps(p, ensure_ascii=False, indent=1))
    return 0 if p.get("verdict") == "LEGIT" else 1


if __name__ == "__main__":
    raise SystemExit(main())
