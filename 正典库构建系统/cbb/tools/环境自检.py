# -*- coding: utf-8 -*-
"""环境自检.py — 步骤⓪：外部环境自检 ＋ 知识图谱归属判定（先于开书）

为什么要这一步：L4 参考层（图/索引/摘要视图）在 `references/架构与profile.md` 的六层不变式里是
**强制参考面，不是可选装饰**——入库不依赖它，**终审必须依赖它**（导出债务清零才许进终审）。
但"这台机器上到底有没有那些服务""那台在跑的图库是不是本项目的"这两问，此前只能在跑起来之后靠猜。
本件把这两问变成一次可复算、可留痕的判定。

四态严格区分（不许互相顶替）：
  READY     闸门件通过：探到了、凭证在、归属已判
  BLOCKED   闸门件不通过——写清缺哪一项、怎么补；**未探＝未检＝BLOCKED，不许写 N/A 蒙过**
  N/A       仅当命令行显式声明不用（--disable embed,rerank,graph），并保留原状态痕、记入未达项
  OBSERVED  观察项（推理端点等）：只报告事实，永不参与闸门

三件基础设施（B-图／B-嵌入／B-重排）按 2026-09-24 裁定为**不可抛弃、全程随流程跑**：
  任一项不是 READY ⇒ 默认阻断（退出码 2），不许"先跑起来再说"；
  确需降级必须 --allow-degraded "<理由>"，本件会自动往 导出债务.jsonl 追加一笔 infra-degraded，
  且回执 overall=DEGRADED、终审可用=false——降级只能带着债走，不能无痕通行。
  **未探＝未检＝BLOCKED**：基础设施不许以"没查"过关。

推理端点是**观察项**，不参与闸门：这套流程的判定者与执行者是宿主 Agent（J1 记身份）。
  本地聊天模型要不要接手 NLI 预筛，属于选型问题，用 --exam 真打三题微考给参考——
  依据（本机实测）：① 拿三分判定题问 gemma-3-1b-it，它答「迷宫」；② 问 35B-A3B 档，三题只对两题，
  错的正是「实体类型=人物（迷宫生物）」vs「实体类型=人物」这种**粒度冲突应判 contradicts** 的形态。
  ⇒ 服务在听、模型清单有货，都不等于能当判定器；但也⇒ 不许因为它判不准就把它当闸门卡住开书。
  另注：上游默认的 :1234 在本机属 Windows 保留端口段（1209–1308 被 Hyper-V/WinNAT 排除，
  `lms server start --port 1234` 报 EACCES），而 :8080 实为 Docker 转发在应答 ⇒ 候选端口取 1234/8080 探哪个通用哪个。

退出码：
  0 = 可以开书（三件基础设施皆 READY；观察项/增值件 BLOCKED 不阻断，但逐条出现在「未达项」里）
  2 = 主链必需项缺失、基础设施缺项且未给 --allow-degraded，或判定面为空（**空判定不许读成通过**）

用法：
  py -X utf8 环境自检.py --project-token zhongmo-canon [--store 本体库] [--json]
  py -X utf8 环境自检.py --allow-degraded "图库归属本周内解决"   # 带债继续：自动记一笔导出债务
  py -X utf8 环境自检.py --probe-only            # 只探环境不判归属（不许拿这个当终审依据）
  py -X utf8 环境自检.py --exam --model <模型名>  # 给本地推理端点做选型微考（观察项）

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

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import 图库隔离 as gi  # noqa: E402  图归属判据的单一事实源（规则一份，两处复用）

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

    dist = {}
    try:
        for g, c in _one("MATCH (n) RETURN DISTINCT coalesce(n.group_id, n.canon_group, '<无归属标记>') "
                         "AS g, count(n) AS c LIMIT 50"):
            dist[str(g)] = int(c)
    except Exception as e:
        out.append(item("G4 图库归属", "BLOCKED",
                        f"归属分布查询失败（共 {total} 节点，无法区分本/他项目）：{type(e).__name__} {str(e)[:60]}"))
        return out

    # 归属判定走 图库隔离.ownership_verdict —— 规则一份，两处共用，不许各写一版再漂
    owned = dist.get(project_token, 0) + dist.get("<无归属标记>", 0)   # 无标记算脏，见 ownership_verdict 入参
    foreign = {g: c for g, c in dist.items() if g != project_token}
    v = gi.ownership_verdict(total, dist.get(project_token, 0), foreign, project_token)
    out.append(item("G4 图库归属", "READY" if v["verdict"] == "LEGIT" else "BLOCKED", v["结论"],
                    节点总数=v["总节点"], 本项目节点=v["本项目节点"], 他项目节点=sum(foreign.values()),
                    归属分布=dist))
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


# ---- 本地 LLM：必须真打一发微考，不许"端口在听就算 READY" ----
# 依据（本机实测）：LM Studio :8080 TCP 在听、/v1/models 有响应，但拿三分判定题问 gemma-3-1b-it
# 它答「迷宫」——完全没按输出格式来。⇒ TCP/模型清单只证明"服务活着"，不证明"能当判定器"。
NLI_EXAM = [  # (前提, 假设, 期望标签)——覆盖三类各一，含粒度冲突这一最容易放过的形态
    ("缇达的实体类型为人物（迷宫生物）", "缇达的实体类型为人物", "contradicts"),
    ("拉丝缇娅拉是苍之学园的剑术教官", "拉丝缇娅拉擅长剑术", "entails"),
    ("言万心叶是苍之学园的学生", "店长关掉了店里的灯", "neutral"),
]
LLM_CANDIDATE_PORTS = (1234, 8080)     # 1234=上游默认；8080=本机 LM Studio 实听端口


def _chat(port: int, model: str, prompt: str, timeout: float = 90.0, http_get=http_json) -> str:
    body, _ = http_get(f"http://127.0.0.1:{port}/v1/chat/completions",
                       {"model": model, "temperature": 0,
                        "messages": [{"role": "user", "content": prompt}]}, timeout=timeout)
    return (body["choices"][0]["message"]["content"] or "").strip()


def _classify(port: int, model: str, premise: str, hypothesis: str, http_get=http_json) -> str:
    raw = _chat(port, model,
                "只回答一个词：entails、neutral 或 contradicts。\n"
                f"前提：{premise}\n假设：{hypothesis}", http_get=http_get)
    low = raw.lower()
    for lab in ("contradicts", "entails", "neutral"):
        if lab in low:
            return lab
    return f"<未按要求输出：{raw[:24]}>"


def check_llm(preset: str, model: str | None = None, exam: bool = False, http_get=http_json) -> dict:
    """推理端点＝**观察项**（判定者是宿主 Agent，见 J1），默认只列清单不考试、永不闸门。
    --exam 才真打三题微考——用途是"要不要把本地模型接进 NLI 预筛"的选型参考，不是开书条件。"""
    tag = "（观察项，不闸门）"
    if os.environ.get("DEEPSEEK_API_KEY"):
        return item("L1 推理端点(付费)", "READY", "preset=deepseek · 凭证在位（值不读出）" + tag)
    ports = [int(os.environ.get("LMSTUDIO_PORT"))] if os.environ.get("LMSTUDIO_PORT") else list(LLM_CANDIDATE_PORTS)
    for p in ports:
        if not tcp_ok("127.0.0.1", p):
            continue
        try:
            models, _ = http_get(f"http://127.0.0.1:{p}/v1/models", timeout=6)
            ids = [m.get("id") for m in models.get("data", [])]
            chat = [i for i in ids if i and "embed" not in i.lower() and "rerank" not in i.lower()]
        except Exception as e:
            continue  # 端口被别的进程占着（本机 :8080 实为 Docker 转发）也是"非推理端点"
        if not exam:
            return item("L1 推理端点(本地)", "OBSERVED",
                        f":{p} 在听 · 可对话模型 {len(chat)} 个（前 5：{'、'.join(chat[:5])}）"
                        f"；默认不考试——要选型加 --exam {tag}")
        pick = model or (chat[0] if len(chat) == 1 else None)
        if not pick:
            return item("L1 推理端点(本地)", "BLOCKED",
                        f":{p} 有多个可对话模型，--exam 必须配 --model 指定一个。候选（前 6 个）："
                        + "、".join(chat[:6]) + f"　⇒ 不许默认拿最小的那个凑数 {tag}")
        got = []
        for prem, hypo, want in NLI_EXAM:
            try:
                lab = _classify(p, pick, prem, hypo, http_get=http_get)
            except Exception as e:
                lab = f"<调用失败 {type(e).__name__}>"
            got.append((want, lab))
        good = sum(1 for w, g in got if w == g)
        detail = "；".join(f"期望{w}/实得{g}" for w, g in got)
        st = "READY" if good == len(NLI_EXAM) else "BLOCKED"
        note = (f":{p} · model={pick} · 微考 {good}/{len(NLI_EXAM)}（temp=0）"
                + ("" if good == len(NLI_EXAM) else " ⇒ 服务活着但判不准：粒度冲突这类最容易放过的形态它错了"))
        return item("L1 推理端点(本地)", st, note + tag, 端口=p, 模型=pick, 微考=detail)
    return item("L1 推理端点(本地)", "OBSERVED",
                "未发现可用推理端点（本机无 DEEPSEEK_API_KEY，候选端口 "
                + "/".join(f":{p}" for p in ports) + f" 不通）⇒ 判定者照旧是宿主 Agent {tag}")


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


# 三件基础设施：按用户裁定（2026-09-24）——**不可抛弃、全程随流程跑**，缺失即阻断，降级必留债。
# 只含 图／嵌入／重排。**推理端点不在闸门内**：本书流程的判定者与执行者是宿主 Agent（见 J1），
# 本地聊天模型只是 L1 的一项可选体检（--exam），它 BLOCKED 绝不许卡住开书或终审。
INFRA = {
    "graph": ("B-图 知识库图载体", [("G1 Neo4j HTTP",), ("G4 图库归属",)]),
    "embed": ("B-嵌入 向量模型", [("E1 嵌入端点",)]),
    "rerank": ("B-重排 重排模型", [("R1 重排端点",)]),
}
OBSERVE_ONLY = ("L1", "P1", "J1")   # 只报告、不闸门


def _slot_state(items: list[dict], alts: tuple[str, ...]) -> str:
    hit = [i for i in items if any(i["item"].startswith(a) for a in alts)]
    if not hit:
        return "NOT_PROBED"
    return "READY" if any(i["state"] == "READY" for i in hit) else "BLOCKED"


def _infra_state(items: list[dict], slots: list[tuple[str, ...]]) -> str:
    """所有槽位都 READY 才算就绪；少探一个槽位＝NOT_PROBED，任一 BLOCKED 即 BLOCKED。
    （图这条尤其不能松：G1 连通 ≠ G4 归属已判——把"能连上"当"可以用"正是共享库事故的入口。）"""
    st = [_slot_state(items, s) for s in slots]
    if "NOT_PROBED" in st:
        return "NOT_PROBED"
    return "READY" if all(x == "READY" for x in st) else "BLOCKED"


def evaluate(items: list[dict], disable: set[str], store: Path | None = None,
             allow_degraded: str | None = None) -> dict:
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
                "carrier": "file", "基础设施": {}, "基础设施缺": ["判定面为空"],
                "exit": 2, "口径": "空判定不许读成通过"}

    miss_req = [i["item"] for i in items if i["item"].startswith("M") and i["state"] != "READY"]
    graph_ready = _infra_state(items, INFRA["graph"][1]) == "READY"
    infra = {k: _infra_state(items, pres) for k, (label, pres) in INFRA.items()}
    infra_missing = [INFRA[k][0] for k, st in infra.items() if st != "READY"]

    debt_file = (Path(store) / "导出债务.jsonl") if store else None
    debt = None
    if debt_file:
        debt = sum(1 for x in debt_file.read_text(encoding="utf-8").splitlines() if x.strip()) \
            if debt_file.exists() else 0

    # 降级闸门：基础设施不齐 ⇒ 默认阻断（exit 2）；给了 --allow-degraded 才放行，但强制记一笔欠账
    degraded = bool(infra_missing) and bool(allow_degraded)
    if degraded and debt_file is not None:
        debt_file.parent.mkdir(parents=True, exist_ok=True)
        with open(debt_file, "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps({"type": "infra-degraded", "缺": infra_missing,
                                "理由": allow_degraded,
                                "口径": "降级运行：基础设施缺失期间产出的收口/终审结论均记未达项"},
                               ensure_ascii=False) + "\n")
        debt = (debt or 0) + 1
    blocked_hard = bool(infra_missing) and not allow_degraded

    not_done = [i for i in items if i["state"] in ("BLOCKED", "N/A")]
    exit_code = 2 if (miss_req or blocked_hard) else 0
    if miss_req:
        overall = "FAIL"
    elif blocked_hard:
        overall = "BLOCKED_INFRA"
    elif degraded:
        overall = "DEGRADED"
    else:
        overall = "READY" if not not_done else "PARTIAL"
    return {
        "overall": overall,
        "carrier": "graph" if graph_ready else "file",
        "carrier_reason": ("G4 归属已判为本项目 ⇒ 走图" if graph_ready
                           else "归属未判/图不可用 ⇒ 降级走文件兜底（同一套规则，两载体），且已记未达项"),
        "基础设施": infra,
        "基础设施缺": infra_missing,
        "降级运行": (f"是（--allow-degraded 理由：{allow_degraded}）⇒ 已写入导出债务台账"
                     if degraded else ("否" if not infra_missing else
                                       "否（未给 --allow-degraded ⇒ 阻断，退出码 2）")),
        "主链必需缺": miss_req,
        "未达项": [{"item": i["item"], "state": i["state"], "note": i["note"]} for i in not_done],
        "终审可用": bool(graph_ready) and infra["embed"] == "READY" and infra["rerank"] == "READY"
                    and (debt == 0 if debt is not None else False),
        "导出债务": debt if debt is not None else "未查（未给 --store）",
        "口径": "终审可用=图归属已判 且 嵌入/重排就绪 且 导出债务=0；任一不成立 ⇒ ⑦ 记未达项不许判通过。"
                "基础设施缺项默认阻断开书（exit 2），--allow-degraded 只能带着债务继续",
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
    ap.add_argument("--judge", default="agent", choices=["endpoint", "agent"],
                    help="语义判定者：默认 agent＝宿主 Agent（这套流程的正常形态）；"
                         "只有真把判定接进本地/付费端点时才填 endpoint")
    ap.add_argument("--probe-only", action="store_true", help="只探环境不判归属（结果不得用于终审）")
    ap.add_argument("--model", default=None, help="做 --exam 微考时指定的本地对话模型名")
    ap.add_argument("--exam", action="store_true",
                    help="给本地推理端点真打三题 NLI 微考（选型参考用；推理端点是观察项，**不参与闸门**）")
    ap.add_argument("--allow-degraded", default=None, metavar="理由",
                    help="基础设施缺项时带债继续（必须写理由；会自动追加一笔导出债务）。不给就阻断，退出码 2")
    ap.add_argument("--disable", default="", help="显式不用的件，逗号分隔，如 embed,rerank,graph")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out", default=None, help="回执落盘路径（建议 工作区/环境自检.json）")
    ns = ap.parse_args(argv)

    ws, store = Path(ns.workspace), (Path(ns.store) if ns.store else None)
    items = check_required(ws, (store or ws) / "ledger.jsonl")
    items += check_graph(ns.project_token, ns.probe_only)
    items += [check_embed(), check_rerank(), check_llm(ns.preset, ns.model, ns.exam), check_graphiti(),
              check_judge(ns.judge)]
    rep = evaluate(items, {x.strip() for x in ns.disable.split(",") if x.strip()}, store,
                   allow_degraded=ns.allow_degraded)
    text = json.dumps(rep, ensure_ascii=False, indent=1 if not ns.json else None)
    print(text)
    if ns.out:
        Path(ns.out).parent.mkdir(parents=True, exist_ok=True)
        Path(ns.out).write_text(text + "\n", encoding="utf-8", newline="\n")
    return rep["exit"]


if __name__ == "__main__":
    raise SystemExit(main())
