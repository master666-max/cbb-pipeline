# -*- coding: utf-8 -*-
"""canon_server.py — 正典库动态控制台 + LLM wiki（活体服务）。

store 每次请求现读——判卷写入/物料化/新章摄入，刷新即最新。零导出零同步。
用法：py -X utf8 canon_server.py --store 迷深实战-本体库 [--port 8420]
"""
import json
import re
import sys
from html import escape as _e
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT = Path(__file__).resolve().parent
STORE = ROOT / "迷深实战-本体库"


def load_records() -> dict:
    recs = {}
    for f in (STORE / "libraries").glob("*/*/*.json"):
        r = json.loads(f.read_text(encoding="utf-8"))
        recs[r["record_id"]] = r
    return recs


def load_quarantine() -> list:
    qz = STORE / "quarantine-zone" / "items.jsonl"
    if not qz.exists():
        return []
    return [json.loads(l) for l in qz.read_text(encoding="utf-8").splitlines() if l.strip()]


def effective_map() -> dict:
    """R13 effective status：文件 status + transitions 叠加（末条胜出）。"""
    eff = {}
    tf = STORE / "transitions.jsonl"
    if tf.exists():
        for l in tf.read_text(encoding="utf-8").splitlines():
            s = l.strip()
            if not s:
                continue
            e = json.loads(s)
            eff[e.get("record_id")] = e.get("to")
    return eff


def load_ledger_head() -> dict:
    lf = STORE / "ledger.jsonl"
    rows = 0
    last = ""
    if lf.exists():
        for l in lf.read_text(encoding="utf-8").splitlines():
            if l.strip():
                rows += 1
                try:
                    last = json.loads(l).get("hash", last)
                except Exception:
                    pass
    return {"rows": rows, "chain_head": last[:12]}


CSS = """body{font-family:system-ui,'Microsoft YaHei',sans-serif;margin:0;background:#f7f7f5;color:#222}
nav{background:#2b2b2b;padding:12px 20px;display:flex;gap:18px;align-items:center}
nav a{color:#fff;text-decoration:none;font-size:15px}nav a:hover{text-decoration:underline}
nav .sp{flex:1}main{max-width:1100px;margin:20px auto;padding:0 14px}
.bad{color:#8a6d00;background:#fff3cd;padding:1px 6px;border-radius:4px;font-size:13px}
.good{color:#0a6b2d;background:#d4edda;padding:1px 6px;border-radius:4px;font-size:13px}
.quar{color:#a11;background:#f8d7da;padding:1px 6px;border-radius:4px;font-size:13px}
table{border-collapse:collapse;width:100%;background:#fff}td,th{border:1px solid #ddd;padding:6px 8px;text-align:left}
tr:nth-child(even){background:#fafafa}a{color:#0b5394;text-decoration:none}
input[type=text]{width:50%;padding:8px;font-size:15px}.quote{border-left:3px solid #bbb;margin:4px 0;padding:3px 8px;background:#fff}
pre{background:#f0f0ee;padding:8px;overflow:auto}.stat{display:inline-block;margin:6px 14px;text-align:center}
.stat .num{font-size:28px;font-weight:bold}.stat .lbl{font-size:12px;color:#888}
h1{font-size:22px}h2{font-size:17px;border-bottom:1px solid #ddd;padding-bottom:4px}"""

NAV = ('<nav><a href="/">库况</a><a href="/browse/character">人物</a>'
       '<a href="/browse/event">事件</a><a href="/browse/relation">关系</a>'
       '<a href="/browse/foreshadow">伏笔</a><a href="/browse/setting">场景</a>'
       '<a href="/search?q=">搜索</a><a href="/graph">图谱</a>'
       '<a href="/wiki/_index">LLM wiki</a><span class=sp></span>'
       '<a href="/api/stats" style="color:#aaa;font-size:12px">API</a></nav>')

BADGE = {"confirmed": '<span class=good>confirmed ✅</span>',
         "provisional": '<span class=bad>provisional ◐</span>',
         "quarantine": '<span class=quar>quarantine ⚠</span>'}


def badge(st):
    return BADGE.get(st, _e(str(st)))


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass  # 静默 access log（控制台输出保持干净）

    def _html(self, body, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(f"<!doctype html><html lang=zh><meta charset=utf-8>"
                         f"<title>正典库</title><style>{CSS}</style>{NAV}"
                         f"<main>{body}</main>".encode("utf-8"))

    def _json(self, obj, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(obj, ensure_ascii=False, indent=1).encode("utf-8"))

    def _md(self, text):
        self.send_response(200)
        self.send_header("Content-Type", "text/markdown; charset=utf-8")
        self.end_headers()
        self.wfile.write(text.encode("utf-8"))

    def _redirect(self, path):
        self.send_response(302)
        self.send_header("Location", path)
        self.end_headers()

    def do_GET(self):
        url = urlparse(self.path)
        path = url.path.rstrip("/") or "/"
        qs = parse_qs(url.query)

        records = load_records()
        eff = effective_map()
        quar = load_quarantine()
        ledger = load_ledger_head()

        def status(rid):
            return eff.get(rid) or (records[rid].get("status") if rid in records else "?")

        if path == "/" or path == "/index.html":
            dist = {}
            for r in records.values():
                st = eff.get(r["record_id"]) or r.get("status", "?")
                dist[st] = dist.get(st, 0) + 1
            qz_dist = {}
            for q in quar:
                qz_dist[q.get("status", "?")] = qz_dist.get(q.get("status", "?"), 0) + 1
            body = f"""<h1>正典库 · 迷深实战</h1>
<p>账本 rows={ledger['rows']} chain_head=<code>{ledger['chain_head']}</code></p>
<div>
<span class=stat><div class=num>{dist.get('confirmed',0)}</div><div class=lbl>confirmed ✅</div></span>
<span class=stat><div class=num>{dist.get('provisional',0)}</div><div class=lbl>provisional ◐</div></span>
<span class=stat><div class=num>{len(quar)}</div><div class=lbl>隔离区</div></span>
<span class=stat><div class=num>{len(records)}</div><div class=lbl>总记录</div></span>
</div>
<h2>隔离区分布</h2><ul>"""
            for k, v in sorted(qz_dist.items()):
                body += f"<li>{_e(str(k))}: {v}</li>"
            body += "</ul><p style='color:#888'>每次请求现读 store——刷新即最新。</p>"
            self._html(body)

        elif path == "/api/stats":
            dist = {}
            for r in records.values():
                st = eff.get(r["record_id"]) or r.get("status", "?")
                dist[st] = dist.get(st, 0) + 1
            self._json({"records": len(records), "tri_state": dist,
                        "ledger": ledger, "quarantine": len(quar)})

        elif path.startswith("/browse/"):
            lib = path.split("/")[-1]
            subset = sorted((r for r in records.values() if r.get("library") == lib),
                            key=lambda x: x["record_id"])
            q = qs.get("q", [""])[0].lower()
            if q:
                subset = [r for r in subset
                          if q in (r.get("canonical") or {}).get("name", "").lower()
                          or q in r["record_id"].lower()]
            rows = ""
            for r in subset:
                rid = r["record_id"]
                nm = (r.get("canonical") or {}).get("name") or rid
                st = eff.get(rid) or r.get("status", "?")
                rows += (f"<tr><td>{badge(st)}</td>"
                         f"<td><a href='/record/{rid}'>{_e(nm)}</a></td>"
                         f"<td><code>{rid}</code></td></tr>")
            self._html(page_shell(f"{lib} · {len(subset)} 件",
                                  f"<input type=text id=q value='{_e(q)}' placeholder='过滤…' "
                                  f"onkeyup=\"location='?q='+this.value\">"
                                  f"<table><tr><th>状态</th><th>名称</th><th>record_id</th></tr>"
                                  f"{rows}</table>"))

        elif path.startswith("/record/"):
            rid = path.split("/")[-1]
            rec = records.get(rid)
            if rec is None:
                self._html(f"<h1>404</h1><p>{_e(rid)} 不在库</p>", code=404)
                return
            canon = rec.get("canonical") or {}
            nm = canon.get("name") or rid
            st = eff.get(rid) or rec.get("status", "?")
            ev = rec.get("evidence") or []
            quotes = "".join(f'<div class=quote>[卷{e.get("vol","?")} 章{e.get("chapter","?")} '
                             f'行{e.get("line","?")}] {_e(str(e.get("quote","")))}</div>'
                             for e in ev if isinstance(e, dict))
            canon_html = _e(json.dumps(canon, ensure_ascii=False, sort_keys=True, indent=1))
            obs = rec.get("observations") or []
            obs_html = "".join(f"<li>[{_e(str(o.get('category','')))}] {_e(str(o.get('text','')))}</li>"
                               for o in obs if isinstance(o, dict))
            self._html(page_shell(f"{nm} · {badge(st)}",
                                  f"<p><code>{rid}</code> ｜ library: {_e(rec.get('library',''))}</p>"
                                  f"<h2>断言（canonical）</h2><pre>{canon_html}</pre>"
                                  f"<h2>证据引文（逐字）</h2>{quotes or '<p>无</p>'}"
                                  + (f"<h2>观察</h2><ul>{obs_html}</ul>" if obs_html else "")
                                  + f"<p><a href='/wiki/{rid}'>LLM wiki (markdown)</a></p>"))

        elif path == "/search":
            q = qs.get("q", [""])[0].lower()
            results = []
            for rid, r in records.items():
                nm = (r.get("canonical") or {}).get("name", "")
                aliases = r.get("_aliases") or []
                if (q in nm.lower() or q in rid.lower()
                        or any(q in str(a).lower() for a in aliases)):
                    results.append((rid, nm, r))
            body = f"<h2>搜索「{_e(q)}」：{len(results)} 件</h2><table>"
            body += "<tr><th>名称</th><th>状态</th><th>类型</th><th>record_id</th></tr>"
            for rid, nm, r in results[:100]:
                st = eff.get(rid) or r.get("status", "?")
                body += (f"<tr><td><a href='/record/{rid}'>{_e(nm)}</a></td>"
                         f"<td>{badge(st)}</td><td><code>{rid}</code></td></tr>")
            body += "</table>"
            self._html(page_shell(f"搜索「{_e(q)}」", body))

        elif path == "/graph":
            nodes, edges = build_graph(records, eff)
            gj = json.dumps({"nodes": nodes, "edges": edges}, ensure_ascii=False)
            body = (f"<p>{len(nodes)} 节点 / {len(edges)} 边（选节点看一度关系）</p>"
                    f"<input id=sel_list list=dl list='dl' placeholder='跳到…' style='width:300px'>"
                    f"<datalist id=dl></datalist>"
                    f"<svg id=svg width=1000 height=600 style='background:#fff;border:1px solid #ddd'></svg>"
                    f"<script>const G = {gj};\n"
                    "const adj = {};\n"
                    "for (const e of G.edges) {\n"
                    "  (adj[e.source] = adj[e.source] || []).push({to: e.target, p: e.predicate, st: e.status});\n"
                    "  (adj[e.target] = adj[e.target] || []).push({to: e.source, p: e.predicate, st: e.status});\n"
                    "}\n"
                    "const dl = document.getElementById('dl');\n"
                    "const sel = document.getElementById('sel_list');\n"
                    "Object.keys(adj).sort().forEach(k => { const o = document.createElement('option'); o.value = k; dl.appendChild(o); });\n"
                    "function draw(center) {\n"
                    "  const nb = adj[center] || [];\n"
                    "  const svg = document.getElementById('svg'); svg.innerHTML = '';\n"
                    "  const W = 1000, H = 600, cx = W/2, cy = H/2, R = 220;\n"
                    "  const mk = (x,y,label,color,id) => { const c = document.createElementNS('http://www.w3.org/2000/svg','circle'); c.setAttribute('cx',x); c.setAttribute('cy',y); c.setAttribute('r',8); c.setAttribute('fill',color); if(id) c.setAttribute('id',id); const t = document.createElementNS('http://www.w3.org/2000/svg','text'); t.setAttribute('x',x+12); t.setAttribute('y',y+4); t.textContent = label; svg.appendChild(c); svg.appendChild(t); };\n"
                    "  mk(cx, cy, center, '#0b5394', 'center');\n"
                    "  nb.forEach((n,i) => { const a = (i/Math.max(nb.length,1))*2*Math.PI; const x = cx+R*Math.cos(a), y = cy+R*Math.sin(a);\n"
                    "    const ln = document.createElementNS('http://www.w3.org/2000/svg','line'); ln.setAttribute('x1',cx); ln.setAttribute('y1',cy); ln.setAttribute('x2',x); ln.setAttribute('y2',y); ln.setAttribute('stroke','#ccc'); svg.appendChild(ln);\n"
                    "    mk(x, y, n.to, '#7a9e01'); });\n"
                    "  document.getElementById('info').textContent = center + ' 一度：' + nb.length;\n"
                    "}\n"
                    "sel_list.addEventListener('change', () => draw(sel_list.value));\n"
                    "if (sel_list.value) draw(sel_list.value);\n</script>"
                    f"<p id=info></p>")
            self._html(page_shell("egocentric 图谱", body))

        elif path.startswith("/wiki/"):
            rid = path.split("/")[-1]
            rec = records.get(rid)
            if rec is None:
                self._md(f"# 404\n\n记录 {rid} 不在库。\n")
                return
            canon = rec.get("canonical") or {}
            nm = canon.get("name") or rid
            st = eff.get(rid) or rec.get("status", "?")
            ev = rec.get("evidence") or []
            aliases = rec.get("_aliases") or []
            lines = [
                f"---\nrecord_id: {rid}\ntype: {rec.get('library','?')}\nstatus: {st}\n"
                f"aliases: {json.dumps(aliases, ensure_ascii=False)}\n"
                f"evidence_count: {len(ev)}\n---\n",
                f"# {nm}\n",
                f"**状态**：{st}　**类型**：{rec.get('library','?')}\n",
                "## 断言（canonical）\n",
                "```json\n" + json.dumps(canon, ensure_ascii=False, sort_keys=True, indent=1) + "\n```\n",
                "## 证据引文（逐字）\n",
            ]
            for e in ev:
                if isinstance(e, dict):
                    lines.append(f"> [卷{e.get('vol','?')} 章{e.get('chapter','?')} "
                                 f"行{e.get('line','?')}] {e.get('quote','')}")
            obs = rec.get("observations") or []
            if obs:
                lines.append("\n## 观察\n")
                for o in obs:
                    if isinstance(o, dict):
                        lines.append(f"- [{o.get('category','')}] {o.get('text','')}")
            self._md("\n".join(lines) + "\n")

        elif path == "/api/records":
            out = []
            for rid, r in records.items():
                out.append({"record_id": rid, "library": r.get("library"),
                            "status": eff.get(rid) or r.get("status"),
                            "canonical": r.get("canonical"),
                            "evidence_count": len(r.get("evidence") or [])})
            self._json({"total": len(out), "records": out})

        elif path.startswith("/api/record/"):
            rid = path.split("/")[-1]
            rec = records.get(rid)
            if rec is None:
                self._json({"error": "not found", "record_id": rid}, code=404)
                return
            self._json({**rec, "effective_status": eff.get(rid)})

        else:
            self._html(f"<h1>404</h1><p>{_e(path)}</p>", code=404)


def page_shell(title, body):
    return (f"<!doctype html><html lang=zh><meta charset=utf-8><title>{_e(title)}</title>"
            f"<style>{CSS}</style>{NAV}<main><h1>{_e(title)}</h1>{body}</main>".replace(
                "<main><h1>", "<main>", 1))


def build_graph(records, eff):
    nodes, edges = [], []
    seen = set()
    for r in records.values():
        canon = r.get("canonical") or {}
        nm = canon.get("name")
        if nm and nm not in seen:
            seen.add(nm)
            rid = r["record_id"]
            nodes.append({"name": nm, "type": r.get("library"),
                          "status": eff.get(rid) or r.get("status"),
                          "record_id": rid, "aliases": r.get("_aliases") or []})
    for r in records.values():
        if r.get("library") != "relation":
            continue
        canon = r.get("canonical") or {}
        s, p, o = canon.get("subject"), canon.get("predicate"), canon.get("object")
        if s and o:
            edges.append({"source": s, "predicate": p or "关联", "target": o,
                          "status": eff.get(r["record_id"]) or r.get("status", "?")})
    return nodes, edges


def run_server(store_root: str, port: int = 8420):
    global STORE
    STORE = Path(store_root).resolve()
    server = HTTPServer(("127.0.0.1", port), Handler)
    print(f"正典库动态控制台 + LLM wiki → http://127.0.0.1:{port}"
          f"\n  每次请求现读 store——刷新即最新。Ctrl+C 停止。")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("停止。")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", default=str(ROOT / "迷深实战-本体库"))
    ap.add_argument("--port", type=int, default=8420)
    args = ap.parse_args()
    STORE = Path(args.store).resolve()
    server = HTTPServer(("127.0.0.1", args.port), Handler)
    print(f"正典库动态控制台 + LLM wiki → http://127.0.0.1:{args.port}"
          f"\n  每次请求现读 store——刷新即最新。Ctrl+C 停止。")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("停止。")
