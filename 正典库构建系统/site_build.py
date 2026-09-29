# -*- coding: utf-8 -*-
"""site_build.py — 批次 3·X4 静态前端生成器（快照只读公理的浏览面）。

读 store（只读）+ SNAPSHOT，产 site/：index / 类型浏览 / 记录页 / 搜索索引 / egocentric 图谱。
零依赖零网络（离线内联 CSS/JS）；三态着色：provisional=琥珀 confirmed=绿 quarantine=红。
用法：py -X utf8 site_build.py --store 迷深实战-本体库 --snapshot 快照目录/SNAPSHOT.json --out 快照目录/site
"""
import argparse
import html
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "cbb-v2"))
from cbb2 import export  # noqa: E402

CSS = """body{font-family:system-ui,'Microsoft YaHei',sans-serif;margin:0;background:#f7f7f5;color:#222}
header{background:#2b2b2b;color:#fff;padding:14px 20px}header a{color:#ffd凤}.bad{color:#8a6d00;background:#fff3cd;padding:1px 6px;border-radius:4px}
.good{color:#0a6b2d;background:#d4edda;padding:1px 6px;border-radius:4px}
.quar{color:#a11;background:#f8d7da;padding:1px 6px;border-radius:4px}
main{max-width:960px;margin:20px auto;padding:0 12px}table{border-collapse:collapse;width:100%;background:#fff}
td,th{border:1px solid #ddd;padding:6px 8px;text-align:left}tr:nth-child(even){background:#fafafa}
a{color:#0b5394;text-decoration:none}a:hover{text-decoration:underline}
.quote{border-left:4px solid #ccc;margin:6px 0;padding:4px 10px;background:#fff}
pre{background:#f0f0ee;padding:8px;overflow:auto}"""

BADGE = {"provisional": '<span class="bad">provisional</span>',
         "confirmed": '<span class="good">confirmed</span>',
         "quarantine": '<span class="quar">quarantine</span>'}


def badge(status):
    return BADGE.get(status, html.escape(str(status)))


def page_shell(title, body, rel=""):
    return (f"<!doctype html><html lang=zh><meta charset=utf-8><title>{html.escape(str(title))}</title>"
            f"<style>{CSS}</style>"
            f"<header><a href='{rel}index.html' style='color:#fff'>⌂ 库况</a> · "
            f"<a href='{rel}browse/' style='color:#fff'>浏览</a> · "
            f"<a href='{rel}graph.html' style='color:#fff'>图谱</a> · "
            f"<a href='{rel}search.html' style='color:#fff'>搜索</a></header>"
            f"<main><h1>{html.escape(str(title))}</h1>{body}</main>")


def record_html(rec, anchor):
    canon = rec.get("canonical") or {}
    name = canon.get("name") or rec["record_id"]
    quotes = "".join(
        f'<div class=quote>[卷{e.get("vol","?")} 章{e.get("chapter","?")} 行{e.get("line","?")}] '
        f'{html.escape(str(e.get("quote", "")))}</div>'
        for e in (rec.get("evidence") or []) if isinstance(e, dict))
    canon_html = html.escape(str(json.dumps(canon, ensure_ascii=False, sort_keys=True, indent=1)))
    aliases = "、".join(html.escape(str(a)) for a in (rec.get("_aliases") or [])) or "—"
    return page_shell(
        f"{name} · {rec['record_id']}",
        f"<p>状态 {badge(rec.get('status','?'))} ｜ 别名：{aliases} ｜ "
        f"<code>{html.escape(str(rec['record_id']))}</code></p>"
        f"<h2>断言（canonical）</h2><pre>{canon_html}</pre>"
        f"<h2>证据引文（逐字）</h2>{quotes}"
        f"<p style='color:#888'>快照锚 rows={anchor['检查点']['rows']} "
        f"chain_head=<code>{str(anchor['检查点']['chain_head'])[:12]}</code></p>")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", required=True)
    ap.add_argument("--snapshot", required=True, help="快照目录/SNAPSHOT.json")
    ns = ap.parse_args()
    store = Path(ns.store).resolve()
    snapdir = Path(ns.snapshot).resolve().parent
    out = snapdir / "site"
    (out / "pages").mkdir(parents=True, exist_ok=True)
    (out / "browse").mkdir(exist_ok=True)

    snapshot = json.loads(Path(ns.snapshot).read_text(encoding="utf-8"))
    records = []
    for f in sorted((store / "libraries").glob("*/*/*.json")):
        records.append(json.loads(f.read_text(encoding="utf-8")))
    nodes = [json.loads(l) for l in (snapdir / "graph" / "nodes.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    edges = [json.loads(l) for l in (snapdir / "graph" / "edges.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]

    # 记录页 + 搜索索引 + 浏览页
    search = []
    by_lib = {}
    for rec in records:
        lib = rec.get("library") or "misc"
        by_lib.setdefault(lib, []).append(rec)
        canon = rec.get("canonical") or {}
        name = canon.get("name") or rec["record_id"]
        d = out / "pages" / lib
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{rec['record_id']}.html").write_text(record_html(rec, snapshot), encoding="utf-8")
        search.append({"rid": rec["record_id"], "name": name, "lib": lib,
                       "status": rec.get("status"),
                       "aliases": rec.get("_aliases") or [],
                       "url": f"pages/{lib}/{rec['record_id']}.html"})
    for lib, rs in sorted(by_lib.items()):
        rows = "".join(
            f"<tr><td>{badge(r.get('status','?'))}</td>"
            f"<td><a href='../pages/{lib}/{r['record_id']}.html'>"
            f"{html.escape(str((r.get('canonical') or {}).get('name') or r['record_id']))}</a></td>"
            f"<td><code>{r['record_id']}</code></td></tr>"
            for r in sorted(rs, key=lambda x: x["record_id"]))
        (out / "browse" / f"{lib}.html").write_text(
            page_shell(f"{lib} · {len(rs)} 件",
                       f"<table><tr><th>状态</th><th>名称</th><th>record_id</th></tr>{rows}</table>",
                       rel="../"), encoding="utf-8")

    # 首页：库况 + 统计 + 类型导航
    stats = "".join(f"<li>{html.escape(k)}：{v}</li>" for k, v in snapshot.get("对账", {}).items())
    nav = "".join(f"<li><a href='browse/{lib}.html'>{html.escape(lib)}</a>（{len(rs)} 件）</li>"
                  for lib, rs in sorted(by_lib.items()))
    (out / "index.html").write_text(page_shell(
        f"正典库 · {html.escape(snapshot.get('store_root', ''))}",
        f"<h2>快照 {snapshot.get('状态')}</h2><ul>{stats}</ul>"
        f"<p>检查点 rows={snapshot['检查点']['rows']}｜图谱 {len(nodes)} 节点/{len(edges)} 边｜"
        f"隔离页 {snapshot.get('隔离页数', 0)}</p>"
        f"<h2>浏览</h2><ul>{nav}</ul>"
        f"<p style='color:#888'>快照只读——发现错误请走产线反馈，勿手改本站。</p>",
        rel=""), encoding="utf-8")

    # 搜索页（客户端过滤 search.json）
    (out / "search.json").write_text(json.dumps(search, ensure_ascii=False), encoding="utf-8")
    (out / "search_data.js").write_text("const data = " + json.dumps(search, ensure_ascii=False) + ";")
    search_inline = json.dumps(search, ensure_ascii=False)
    (out / "search.html").write_text(page_shell("搜索", """
<input id=q placeholder='输入名称/别名/record_id' style='width:60%;padding:6px'>
<ul id=results></ul>
<script src="search_data.js"></script>
<script>
const q = document.getElementById('q'), ul = document.getElementById('results');
q.addEventListener('input', () => {
  const s = q.value.trim().toLowerCase();
  ul.innerHTML = '';
  if (!s) return;
  for (const it of data) {
    if ((it.name + ' ' + (it.aliases || []).join(' ') + ' ' + it.rid).toLowerCase().includes(s)) {
      const li = document.createElement('li');
      li.innerHTML = `<a href='${it.url}'>${it.name || it.rid}</a> [${it.status}] ${it.rid}`;
      ul.appendChild(li);
      if (ul.children.length >= 200) break;
    }
  }
});
</script>""", rel=""), encoding="utf-8")

    # 图谱页（egocentric：选节点看一度关系，SVG 简绘）
    graph_json = json.dumps({"nodes": nodes, "edges": edges}, ensure_ascii=False)
    graph_js = """
const G = graph_data;
const adj = {};
for (const e of G.edges) {
  (adj[e.source] = adj[e.source] || []).push({to: e.target, p: e.predicate, st: e.status});
  (adj[e.target] = adj[e.target] || []).push({to: e.source, p: e.predicate, st: e.status});
}
const names = {}; for (const n of G.nodes) names[n.name] = n;
const sel = document.getElementById('sel');
Object.keys(adj).sort().forEach(k => { const o = document.createElement('option'); o.value = k; o.textContent = k; sel.appendChild(o); });
function draw() {
  const center = sel.value;
  const nb = adj[center] || [];
  document.getElementById('info').textContent = center + ' 的一度关系：' + nb.length;
  const svg = document.getElementById('svg');
  svg.innerHTML = '';
  const W = 900, H = 500, cx = W/2, cy = H/2, R = 180;
  const mk = (x, y, label, color) => {
    const c = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    c.setAttribute('cx', x); c.setAttribute('cy', y); c.setAttribute('r', 8); c.setAttribute('fill', color);
    const t = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    t.setAttribute('x', x + 12); t.setAttribute('y', y + 4); t.textContent = label;
    svg.appendChild(c); svg.appendChild(t);
  };
  mk(cx, cy, center, '#0b5394');
  nb.forEach((n, i) => {
    const ang = (i / Math.max(nb.length, 1)) * 2 * Math.PI;
    const x = cx + R * Math.cos(ang), y = cy + R * Math.sin(ang);
    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    line.setAttribute('x1', cx); line.setAttribute('y1', cy); line.setAttribute('x2', x); line.setAttribute('y2', y);
    line.setAttribute('stroke', '#bbb'); svg.appendChild(line);
    mk(x, y, n.to, '#7a9e01');
  });
  const ul = document.getElementById('nb'); ul.innerHTML = '';
  nb.forEach(n => { const li = document.createElement('li');
    li.textContent = n.to + '（' + n.p + '）'; ul.appendChild(li); });
}
sel.addEventListener('change', draw);
sel.value = sel.options.length ? sel.options[0].value : '';
if (sel.value) draw();
"""
    (out / "graph_data.json").write_text(graph_json, encoding="utf-8")
    (out / "graph.html").write_text(page_shell("egocentric 图谱", f"""
<p>选择节点查看一度关系（{len(nodes)} 节点 / {len(edges)} 边；三态着色随节点状态）。</p>
<p><b id=info></b></p>
<p><select id=sel></select></p>
<svg id=svg width=900 height=500 style='background:#fff;border:1px solid #ddd'></svg>
<ul id=nb></ul>
<script>const graph_data = {graph_json};</script>
<script>{graph_js}</script>""", rel=""), encoding="utf-8")

    print(json.dumps({"site": str(out), "pages": len(records),
                      "nodes": len(nodes), "edges": len(edges)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
