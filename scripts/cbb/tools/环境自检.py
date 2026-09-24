# -*- coding: utf-8 -*-
"""环境自检.py — 步骤⓪：外部环境自检 ＋ 知识图谱归属判定（先于开书）

为什么要这一步：L4 参考层（图/索引/摘要视图）在 `references/架构与profile.md` 的六层不变式里是
**强制参考面，不是可选装饰**——入库不依赖它，**终审必须依赖它**（导出债务清零才许进终审）。
但"这台机器上到底有没有那些服务""那台在跑的图库是不是本项目的"这两问，此前只能在跑起来之后靠猜。
本件把这两问变成一次可复算、可留痕的判定。

三态严格区分（不许互相顶替）：
  READY     探到了、凭证在、归属已判
  BLOCKED   该件不可用——写清缺哪一项、怎么补；**未探＝未探，不许写 N/A 蒙过**
  N/A       仅当命令行显式声明不用（--disable embed,rerank,graph），并记入未达项口径

退出码：
  0 = 可以开书（主链必需项全 READY；增值项 BLOCKED 不阻断，但逐条出现在「未达项」里）
  2 = 主链必需项缺失，或判定面为空（**空判定不许读成通过**）

用法：
  py -X utf8 环境自检.py --project-token zhongmo-canon [--store 本体库] [--json]
  py -X utf8 环境自检.py --probe-only            # 只探环境不判归属（不许拿这个当终审依据）
  py -X utf8 环境自检.py --judge agent           # 声明语义判定者=宿主 Agent（写进回执，防冒称本地模型）

端点与环境变量（与包内既有件同一套名字，不另造）：
  NEO4J_HTTP（默认 http://localhost:7695）· NEO4J_PASSWORD / NEO4J_AUTH ·
  EMBED_HTTP（默认 http://127.0.0.1:8080/v1/embeddings）·
  RERANK_HTTP（默认 http://127.0.0.1:8081/v1/rerank）· LMSTUDIO_BASE :1234 · DEEPSEEK_API_KEY
"""
from __future__ import annotations

import base64
import json
import os
import socket
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

NEO4J_HTTP_DEFAULT = "http://localhost:7695"
EMBED_DEFAULT = "http://127.0.0.1:8080/v1/embeddings"
RERANK_DEFAULT = "http://127.0.0.1:8081/v1/rerank"
LMSTUDIO_DEFAULT = "http://127.0.0.1:1234/v1"
EMBED_MODEL_DEFAULT = "text-embedding-qwen3-embedding-8b@q8_0"
RERANK_MODEL_DEFAULT = "qwen3-reranker-4b"

REQUIRED = ("M1 解释器", "M2 依赖 yaml", "M3 工作区可写", "M4 账本可追加")


def item(name: str, state: str, note: str, **extra) -> dict:
    d = {"item": name, "state": state, "note": note}
    d.update(extra)
    return d


def tcp_ok(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def http_json(url: str, payload: dict | None = None, timeout: float = 20.0,
              auth: tuple[str, str] | None = None) -> tuple[dict, float]:
    """返回 (解析后的 JSON, 耗时秒)。凭证只从参数进，绝不写进任何输出。"""
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    if auth:
        tok = base64.b64encode(f"{auth[0]}:{auth[1]}".encode()).decode()
        req.add_header("Authorization", "Basic " + tok)
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "ignore")), time.time() - t0


# ---------------- 主链必需四项 ----------------

def check_required(workspace: Path, ledger: Path) -> list[dict]:
    out = []
    v = sys.version_info
    out.append(item("M1 解释器", "READY" if (v.major, v.minor) >= (3, 10) else "BLOCKED",
                    f"Python {v.major}.{v.minor}.{v.micro}（需 ≥3.10）"))
    try:
        import yaml  # noqa: F401
        out.append(item("M2 依赖 yaml", "READY", "可导入"))
    except ImportError:
        out.append(item("M2 依赖 yaml", "BLOCKED", "缺：py -m pip install pyyaml"))

    workspace.mkdir(parents=True, exist_ok=True)
    probe = workspace / ".env-selftest-write.probe"
    try:
        probe.write_text("probe", encoding="utf-8")
        ok = probe.stat().st_size == len("probe")
        probe.unlink()
        out.append(item("M3 工作区可写", "READY" if ok and not probe.exists() else "BLOCKED",
                        f"真写一发再删：{workspace}"))
    except OSError as e:
        out.append(item("M3 工作区可写", "BLOCKED", f"{type(e).__name__}: {e}"))

    if ledger.exists():
        before = ledger.stat().st_size
        try:
            with open(ledger, "a", encoding="utf-8"):
                pass
            same = ledger.stat().st_size == before
            out.append(item("M4 账本可追加", "READY" if same else "BLOCKED",
                            f"以追加模式打开且字节未变（{before}）"))
        except OSError as e:
            out.append(item("M4 账本可追加", "BLOCKED", f"{type(e).__name__}: {e}"))
    else:
        out.append(item("M4 账本可追加", "READY", f"账本尚不存在（首写方）：{ledger}"))
    return out


# ---------------- L4 图：连通 ＋ 归属 ----------------

def check_graph(project_token: str, probe_only: bool, http_get=http_json) -> list[dict]:
    base = os.environ.get("NEO4J_HTTP", NEO4J_HTTP_DEFAULT)
    out = []
    try:
        disc, el = http_get(base.rstrip("/") + "/", timeout=5)
        bolt_uri = disc.get("bolt_routing") or disc.get("bolt") or ""
        out.append(item("G1 Neo4j HTTP", "READY", f"{base} 回 discovery（{el:.2f}s）",
                        bolt_routing=bolt_uri))
    except Exception as e:
        out.append(item("G1 Neo4j HTTP", "BLOCKED", f"{base} 不通：{type(e).__name__} {str(e)[:60]}"))
        out.append(item("G2 bolt 端口", "BLOCKED", "G1 不通 ⇒ 无从解析 bolt 地址"))
        out.append(item("G4 图库归属", "BLOCKED", "库不可达 ⇒ 归属未判定；未判定不得启用 graph 载体"))
        return out

    host, port = "127.0.0.1", 7687          # 兜底默认值；真值优先取 discovery 自报的 bolt_routing
    frag = bolt_uri or ""
    if ":" in frag:
        host = frag.rsplit("//", 1)[-1].split(":")[0] or host
        try:
            port = int(frag.rsplit(":", 1)[-1])
        except ValueError:
            pass
    out.append(item("G2 bolt 端口", "READY" if tcp_ok(host, port) else "BLOCKED",
                    f"discovery 自报 {host}:{port}（注意：该值常是容器内地址，宿主机映射端口可能不同）"))

    pw = os.environ.get("NEO4J_PASSWORD") or os.environ.get("NEO4J_AUTH")
    if not pw:
        out.append(item("G3 Neo4j 凭证", "BLOCKED", "缺 NEO4J_PASSWORD（D-004：凭证只走环境变量，值不读出）"))
        out.append(item("G4 图库归属", "BLOCKED", "无凭证 ⇒ 无法读取图内容，归属未判定；未判定不得启用 graph 载体"))
        return out
    out.append(item("G3 Neo4j 凭证", "READY", "在位（值不读出）"))
    if probe_only:
        out.append(item("G4 图库归属", "BLOCKED", "--probe-only 已跳过归属判定；不许拿本次结果当终审依据"))
        return out

    user = os.environ.get("NEO4J_USER", "neo4j")
    db = os.environ.get("NEO4J_DATABASE", "neo4j")
    q = base.rstrip("/") + f"/db/{db}/tx/commit"

    def _one(statement: str):
        """跑一条 Cypher，返回 (行列表, 错误列表)；有错即抛，绝不把空结果当成"查过了"。"""
        res, _ = http_get(q, {"statements": [{"statement": statement}]}, timeout=15, auth=(user, pw))
        errs = [e for e in res.get("errors", []) if e]
        if errs:
            raise RuntimeError(f"Cypher 报错：{errs[0].get('code')} {str(errs[0].get('message'))[:60]}")
        return [row["row"] for row in (res.get("results") or [{}])[0].get("data", [])]

    try:
        total = int(_one("MATCH (n) RETURN count(n) AS c")[0][0])
    except Exception as e:
        out.append(item("G4 图库归属", "BLOCKED", f"计数查询失败：{type(e).__name__} {str(e)[:70]}"))
        return out

    owned = foreign = 0
    try:
        for g, c in _one("MATCH (n) RETURN DISTINCT coalesce(n.group_id, n.canon_group, '<无归属标记>') "
                         "AS g, count(n) AS c LIMIT 50"):
            if g == project_token:
                owned += int(c)
            else:
                foreign += int(c)
    except Exception as e:
        out.append(item("G4 图库归属", "BLOCKED",
                        f"归属分布查询失败（共 {total} 节点，无法区分本/他项目）：{type(e).__name__} {str(e)[:60]}"))
        return out

    # 分布查询一条都没回而总数>0 ⇒ 无法归因，按未判定处理（空结果面不许读成"全属本项目"）
    if total > 0 and owned + foreign == 0:
        out.append(item("G4 图库归属", "BLOCKED",
                        f"库有 {total} 节点但归属分布查询零回行 ⇒ 未判定；须显式带 group_id/canon_group 标记或换独立 database"))
        return out

    if total == 0:
        out.append(item("G4 图库归属", "READY", f"库为空（0 节点）；本项目命名空间={project_token}（尚未写入）",
                        节点总数=0, 本项目节点=0, 他项目节点=0))
    elif foreign == 0:
        out.append(item("G4 图库归属", "READY", f"库内节点全部带本项目标记（{owned}/{total}）",
                        节点总数=total, 本项目节点=owned, 他项目节点=0))
    else:
        out.append(item("G4 图库归属", "BLOCKED",
                        f"库内有 {foreign} 个节点不带本项目标记「{project_token}」（共 {total}）"
                        "⇒ 这是别的项目/共享的图库，跨库巡检会产出假干净；须换独立 database 或走文件兜底",
                        节点总数=total, 本项目节点=owned, 他项目节点=foreign))
    return out


# ---------------- 增值件：嵌入 / 重排 / LLM / graphiti ----------------

def check_embed(http_get=http_json) -> dict:
    url = os.environ.get("EMBED_HTTP", EMBED_DEFAULT)
    try:
        res, el = http_get(url, {"model": os.environ.get("EMBED_MODEL", EMBED_MODEL_DEFAULT),
                                 "input": ["环境自检"]}, timeout=60)
        dim = len(res["data"][0]["embedding"])
        return item("E1 嵌入端点", "READY", f"{dim} 维 · {el:.2f}s（首含模型载入，慢≠不通）", 维度=dim)
    except Exception as e:
        return item("E1 嵌入端点", "BLOCKED", f"{url} 不可用：{type(e).__name__} {str(e)[:60]}"
                                             "（首包超时请把 timeout 调大后重试，别一次失败就记永久不可用）")


def check_rerank(http_get=http_json) -> dict:
    url = os.environ.get("RERANK_HTTP", RERANK_DEFAULT)
    try:
        res, el = http_get(url, {"model": os.environ.get("RERANK_MODEL", RERANK_MODEL_DEFAULT),
                                 "query": "自检", "documents": ["无关文档", "自检相关文档"]}, timeout=90)
        order = [r.get("index") for r in res.get("results", [])]
        ok = bool(order) and order[0] == 1
        return item("R1 重排端点", "READY" if ok else "BLOCKED",
                    f"{el:.2f}s · 排序={order}（判据：最相关文档排到首位）")
    except Exception as e:
        return item("R1 重排端点", "BLOCKED", f"{url} 不可用：{type(e).__name__} {str(e)[:60]}")


def check_llm(preset: str) -> dict:
    if os.environ.get("DEEPSEEK_API_KEY"):
        return item("L1 语义判定端点", "READY", "preset=deepseek · 凭证在位（值不读出）")
    if tcp_ok("127.0.0.1", int(os.environ.get("LMSTUDIO_PORT", "1234"))):
        return item("L1 语义判定端点", "READY", "LM Studio :1234 在听（NLI 判定器可走本地）")
    return item("L1 语义判定端点", "BLOCKED",
                f"既无 DEEPSEEK_API_KEY，:1234 也不通 ⇒ NLI 矛盾预筛不可用；"
                "若改由宿主 Agent 代判，必须 --judge agent 声明身份并在报告同口径写出")


def check_graphiti() -> dict:
    try:
        import graphiti_core  # noqa: F401
        return item("P1 graphiti 包", "READY", "graphiti_core 可导入")
    except ImportError:
        return item("P1 graphiti 包", "BLOCKED", "未安装：py -m pip install graphiti-core ⇒ 深融⑤ 增值层无实现")


def check_judge(judge: str) -> dict:
    if judge == "agent":
        return item("J1 判定者身份", "DECLARED", "语义类判定（NLI/评分）由宿主 Agent 执行，非本地模型；"
                                             "须在报告里同口径声明，并固定 prompt 版本＋逐对独立判定")
    return item("J1 判定者身份", "READY", f"判定者={judge}（本地/付费端点，须给出可复现口径）")


# ---------------- 汇总 ----------------

# --disable 的短名 → 项目前缀（不配这张表，"embed" 匹配不到 "E1 嵌入端点"，会静默不禁）
DISABLE_ALIAS = {"embed": "E1", "rerank": "R1", "graph": "G", "llm": "L1", "graphiti": "P1",
                 "judge": "J1"}


def evaluate(items: list[dict], disable: set[str], store: Path | None = None) -> dict:
    # 禁用名写错（如 embedt）若被静默忽略，就等于"以为关了其实没关"⇒ 显式现形为 BLOCKED
    unknown = sorted(s for s in disable if s.lower() not in DISABLE_ALIAS)
    for short in disable:
        pre = DISABLE_ALIAS.get(short.lower())
        if not pre:
            continue
        items = [item(i["item"], "N/A", f"命令行显式禁用（--disable {short}）", 原状态=i["state"])
                 if i["item"].startswith(pre) and i["state"] != "N/A" else i for i in items]
    for bad in unknown:
        items.append(item(f"X 未知禁用名[{bad}]", "BLOCKED",
                          "--disable 只认 " + "/".join(sorted(DISABLE_ALIAS)) +
                          "；这条没生效，不要以为已经禁掉了对应件"))
    if not items:
        return {"overall": "FAIL", "items": [], "未达项": ["判定面为空：什么都没查"],
                "carrier": "file", "exit": 2, "口径": "空判定不许读成通过"}
    miss_req = [i["item"] for i in items if i["item"].startswith("M") and i["state"] != "READY"]
    graph_ready = any(i["item"] == "G4 图库归属" and i["state"] == "READY" for i in items)
    debt = None
    if store:
        f = Path(store) / "导出债务.jsonl"
        debt = sum(1 for x in f.read_text(encoding="utf-8").splitlines() if x.strip()) if f.exists() else 0
    not_done = [i for i in items if i["state"] in ("BLOCKED", "N/A")]
    exit_code = 2 if miss_req else 0
    overall = "READY" if not not_done else ("PARTIAL" if not miss_req else "FAIL")
    return {
        "overall": overall,
        "carrier": "graph" if graph_ready else "file",
        "carrier_reason": ("G4 归属已判定为本项目 ⇒ 可走图"
                           if graph_ready else "归属未判定或图不可用 ⇒ 走文件兜底（深融②允许同一套规则）"),
        "主链必需缺": miss_req,
        "未达项": [{"item": i["item"], "state": i["state"], "note": i["note"]} for i in not_done],
        "终审可用": bool(graph_ready) and (debt == 0 if debt is not None else False),
        "导出债务": debt if debt is not None else "未查（未给 --store）",
        "口径": "终审可用=归属已判 且 导出债务为 0；任一不成立 ⇒ ⑦ 不许判通过，只能记未达项",
        "exit": exit_code,
        "items": items,
    }


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="步骤⓪ 外部环境自检＋图库归属判定")
    ap.add_argument("--project-token", required=False, default="cbb-default",
                    help="本项目在图库里的命名空间（写入 group_id/canon_group 用的同一个值）")
    ap.add_argument("--workspace", default="工作区")
    ap.add_argument("--store", default=None, help="本体库根（给了才查导出债务）")
    ap.add_argument("--preset", default="deepseek", choices=["deepseek", "lmstudio-flash"])
    ap.add_argument("--judge", default="endpoint", choices=["endpoint", "agent"],
                    help="语义判定者：endpoint=本地/付费端点；agent=宿主 Agent 代判（须声明）")
    ap.add_argument("--probe-only", action="store_true", help="只探环境不判归属（结果不得用于终审）")
    ap.add_argument("--disable", default="", help="显式不用的件，逗号分隔，如 embed,rerank,graph")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out", default=None, help="回执落盘路径（建议 工作区/环境自检.json）")
    ns = ap.parse_args(argv)

    ws, store = Path(ns.workspace), (Path(ns.store) if ns.store else None)
    items = check_required(ws, (store or ws) / "ledger.jsonl")
    items += check_graph(ns.project_token, ns.probe_only)
    items += [check_embed(), check_rerank(), check_llm(ns.preset), check_graphiti(), check_judge(ns.judge)]
    rep = evaluate(items, {x.strip() for x in ns.disable.split(",") if x.strip()}, store)
    text = json.dumps(rep, ensure_ascii=False, indent=1 if not ns.json else None)
    print(text)
    if ns.out:
        Path(ns.out).parent.mkdir(parents=True, exist_ok=True)
        Path(ns.out).write_text(text + "\n", encoding="utf-8", newline="\n")
    return rep["exit"]


if __name__ == "__main__":
    raise SystemExit(main())
