# -*- coding: utf-8 -*-
"""test_环境自检.py — 步骤⓪ 判定件的正负对照（零网络：HTTP/端口/环境全注入）

判据锚（三条，全是这次实战换来的）：
  1 归属未判定 ⇒ 不许启用 graph 载体，且不许读成"没有别人的数据"；
  2 空判定面 ≠ 通过（items 为空、归属分布零回行，两种"什么都没查到"都必须 BLOCKED/FAIL）；
  3 未探不许写成 N/A（N/A 只允许出现在命令行显式禁用时）。
两侧成对：正对照（该 READY）＋负对照（该 BLOCKED），且负对照必须抓到**指定项**。
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import 环境自检 as es  # noqa: E402


def fake_http(routes):
    """routes: 若干 (子串匹配, 返回体)；按序取第一条命中的；命中不了=抛（模拟端点不通）。"""
    def _f(url, payload=None, timeout=20.0, auth=None):
        for key, body in routes:
            if key in url:
                if isinstance(body, Exception):
                    raise body
                return body, 0.01
            if key in json.dumps(payload or {}, ensure_ascii=False):
                if isinstance(body, Exception):
                    raise body
                return body, 0.01
        raise ConnectionError(f"无路由匹配：{url}")
    return _f


def g_routes(count_rows=None, group_rows=None, errors=None):
    """图的两条路径：/db/ 下走 Cypher 分流，其余（裸址 discovery）回 bolt_routing。
    少了 discovery 那条，所有用例会统一撞在"库不可达"上，伪装成 G4 判定失败。"""
    q = cypher(count_rows, group_rows, errors)

    def _f(url, payload=None, timeout=20.0, auth=None):
        if "/db/" in url:
            return q(url, payload, timeout, auth)
        return {"bolt_routing": "neo4j://127.0.0.1:7687"}, 0.01
    return _f


def cypher(count_rows=None, group_rows=None, errors=None):
    """把 tx/commit 的两次调用（计数、归属分布）按语句内容分流。"""
    def _f(url, payload=None, timeout=20.0, auth=None):
        stmt = (payload or {}).get("statements", [{}])[0].get("statement", "")
        if errors:
            return {"errors": errors}, 0.01
        if "count(n) AS c" in stmt and "group_id" not in stmt:
            return {"results": [{"data": [{"row": r} for r in (count_rows or [[0]])]}]}, 0.01
        return {"results": [{"data": [{"row": r} for r in (group_rows or [])]}]}, 0.01
    return _f


def graph_items(tok="zhongmo-canon", probe_only=False, routes=None, tcp=True, env=None):
    old_tcp = es.tcp_ok
    es.tcp_ok = lambda h, p, timeout=2.0: tcp
    old_env = dict(os.environ)
    os.environ.clear()
    os.environ.update({"NEO4J_HTTP": "http://127.0.0.1:7695", **(env or {})})
    try:
        return es.check_graph(tok, probe_only, http_get=routes)
    finally:
        es.tcp_ok = old_tcp
        os.environ.clear()
        os.environ.update(old_env)


def find(items, name):
    return next(i for i in items if i["item"] == name)


class 主链必需(unittest.TestCase):
    def test_可写工作区与账本(self):
        with tempfile.TemporaryDirectory() as t:
            ws, led = Path(t) / "工作区", Path(t) / "ledger.jsonl"
            led.write_text('{"a":1}\n', encoding="utf-8")
            its = es.check_required(ws, led)
            self.assertTrue(all(i["state"] == "READY" for i in its), its)
            self.assertEqual(led.stat().st_size, 9, "M4 只许以追加模式打开，不许改字节")

    def test_账本不可追加时报BLOCKED不报错(self):
        with tempfile.TemporaryDirectory() as t:
            ws = Path(t) / "工作区"
            led = Path(t) / "我是目录"      # 用目录冒充不可追加的账本 ⇒ 打开应失败
            led.mkdir()
            its = es.check_required(ws, led)
            self.assertEqual(find(its, "M4 账本可追加")["state"], "BLOCKED")


class 归属判定(unittest.TestCase):
    def test_正对照_空库可启用图载体(self):
        its = graph_items(routes=g_routes([[0]], []), env={"NEO4J_PASSWORD": "x"})
        self.assertEqual(find(its, "G4 图库归属")["state"], "READY")
        rep = es.evaluate(its + [es.item("M1 解释器", "READY", "")], set())
        self.assertEqual(rep["carrier"], "graph")
        self.assertEqual(rep["exit"], 0)

    def test_正对照_全属本项目(self):
        its = graph_items(routes=g_routes([[7]], [["zhongmo-canon", 7]]),
                         env={"NEO4J_PASSWORD": "x"})
        g = find(its, "G4 图库归属")
        self.assertEqual(g["state"], "READY")
        self.assertEqual((g["本项目节点"], g["他项目节点"]), (7, 0), "每个数须带口径")

    def test_负对照_库里是别人的图(self):
        its = graph_items(routes=g_routes([[118189]], [["mishen-canon", 118189]]),
                         env={"NEO4J_PASSWORD": "x"})
        g = find(its, "G4 图库归属")
        self.assertEqual(g["state"], "BLOCKED", "指定项必须是 G4")
        self.assertIn("假干净", g["note"])
        rep = es.evaluate(its, set())
        self.assertEqual(rep["carrier"], "file")

    def test_负对照_无凭证即未判定(self):
        its = graph_items(routes=g_routes())
        self.assertEqual(find(its, "G3 Neo4j 凭证")["state"], "BLOCKED")
        g = find(its, "G4 图库归属")
        self.assertEqual(g["state"], "BLOCKED")
        self.assertIn("未判定不得启用", g["note"])
        self.assertEqual([i["item"] for i in its if i["item"].startswith("G")],
                         ["G1 Neo4j HTTP", "G2 bolt 端口", "G3 Neo4j 凭证", "G4 图库归属"],
                         "四项须逐项回执，不许静默少查")

    def test_负对照_零回行不许读成全属本项目(self):
        its = graph_items(routes=g_routes([[50]], []), env={"NEO4J_PASSWORD": "x"})
        g = find(its, "G4 图库归属")
        self.assertEqual(g["state"], "BLOCKED", "总数>0 而归属分布零回行 ⇒ 未判定")
        self.assertIn("零回行", g["note"])

    def test_负对照_cypher报错不许吞(self):
        its = graph_items(routes=g_routes(errors=[{"code": "Neo.ClientError", "message": "no such"}]),
                         env={"NEO4J_PASSWORD": "x"})
        self.assertEqual(find(its, "G4 图库归属")["state"], "BLOCKED")

    def test_负对照_probe_only不许冒充已判定(self):
        its = graph_items(probe_only=True, routes=g_routes([[0]], []),
                          env={"NEO4J_PASSWORD": "x"})
        self.assertIn("当终审依据", find(its, "G4 图库归属")["note"])

    def test_负对照_bolt自报值与宿主映射不同也算不通(self):
        its = graph_items(tcp=False, routes=g_routes([[0]], []),
                          env={"NEO4J_PASSWORD": "x"})
        self.assertEqual(find(its, "G2 bolt 端口")["state"], "BLOCKED")


class 增值件(unittest.TestCase):
    def test_嵌入维度与耗时入回执(self):
        r = fake_http([("embeddings", {"data": [{"embedding": [0.1] * 4096}]})])
        it = es.check_embed(http_get=r)
        self.assertEqual((it["state"], it["维度"]), ("READY", 4096))

    def test_嵌入不通须提示超时口径(self):
        it = es.check_embed(http_get=fake_http([]))
        self.assertEqual(it["state"], "BLOCKED")
        self.assertIn("timeout", it["note"])

    def test_重排排序判据是真的(self):
        good = fake_http([("rerank", {"results": [{"index": 1, "relevance_score": .9},
                                                  {"index": 0, "relevance_score": .1}]})])
        bad = fake_http([("rerank", {"results": [{"index": 0, "relevance_score": .1},
                                                 {"index": 1, "relevance_score": .9}]})])
        self.assertEqual(es.check_rerank(http_get=good)["state"], "READY")
        self.assertEqual(es.check_rerank(http_get=bad)["state"], "BLOCKED", "把不相关的排到第一 ⇒ 判坏")


class 汇总纪律(unittest.TestCase):
    def test_空判定面判FAIL(self):
        rep = es.evaluate([], set())
        self.assertEqual((rep["overall"], rep["exit"]), ("FAIL", 2))

    def test_NA只来自显式禁用(self):
        base = [es.item("M1 解释器", "READY", ""), es.item("E1 嵌入端点", "BLOCKED", "不通")]
        rep = es.evaluate(list(base), {"embed"})
        e = find(rep["items"], "E1 嵌入端点")
        self.assertEqual((e["state"], e["原状态"]), ("N/A", "BLOCKED"), "禁用须留原状态痕")
        self.assertEqual(rep["exit"], 0)

    def test_禁用名写错要现形而不是静默无效(self):
        base = [es.item("M1 解释器", "READY", ""), es.item("E1 嵌入端点", "BLOCKED", "不通")]
        rep = es.evaluate(base, {"embedt"})            # 少写一个字母
        x = [i for i in rep["items"] if i["item"].startswith("X ")]
        self.assertEqual(len(x), 1, "写错的禁用名必须冒出一条 BLOCKED")
        self.assertEqual(find(rep["items"], "E1 嵌入端点")["state"], "BLOCKED", "没禁成功就不许假装禁了")
        self.assertIn("未达项", str(rep))

    def test_主链缺项必阻断(self):
        base = [es.item("M1 解释器", "BLOCKED", "版本低"), es.item("E1 嵌入端点", "READY", "")]
        rep = es.evaluate(base, set())
        self.assertEqual(rep["exit"], 2)
        self.assertEqual(rep["主链必需缺"], ["M1 解释器"])

    def test_终审可用要图归属与零债务同时成立(self):
        with tempfile.TemporaryDirectory() as t:
            store = Path(t)
            (store / "导出债务.jsonl").write_text("{}\n{}\n", encoding="utf-8")
            its = [es.item("M1 解释器", "READY", ""), es.item("G4 图库归属", "READY", "")]
            self.assertFalse(es.evaluate(its, set(), store)["终审可用"], "欠 2 笔债务 ⇒ 终审不可用")
            (store / "导出债务.jsonl").write_text("", encoding="utf-8")
            self.assertTrue(es.evaluate(its, set(), store)["终审可用"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
