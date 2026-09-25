# -*- coding: utf-8 -*-
"""test_派生层对账.py — 半途写必须现形（夹具全自造，零网络零服务）

锚的实测事实：LightRAG 在嵌入端点挂掉时把节点写进了图、没写进向量库，
操作"成功"返回但两边计数不等 ⇒ 只有双查能抓到。
"""
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import 派生层对账 as m  # noqa: E402

GRAPHML = """<?xml version="1.0" ?>
<graphml>
  <key id="d0" for="node" attr.name="entity_id" attr.type="string" />
  <key id="d1" for="node" attr.name="entity_type" attr.type="string" />
  <key id="d2" for="node" attr.name="source_id" attr.type="string" />
  <graph edgedefault="undirected">
    <node id="梅芙"><data key="d0">梅芙</data><data key="d1">PERSON</data>
      <data key="d2">卷1·第1话·行1237</data></node>
    <node id="沙姆希尔"><data key="d0">沙姆希尔</data><data key="d1">OBJECT</data>
      <data key="d2">卷1·第1话·行1240</data></node>
    <node id="裸节点"><data key="d0">裸节点</data><data key="d1">TERM</data></node>
    <edge source="梅芙" target="沙姆希尔" />
  </graph>
</graphml>"""


def _run(files: dict, extra=()):
    with tempfile.TemporaryDirectory() as t:
        d = Path(t)
        for name, content in files.items():
            (d / name).parent.mkdir(parents=True, exist_ok=True)
            (d / name).write_text(content, encoding="utf-8") if isinstance(content, str) \
                else (d / name).write_text(json.dumps(content, ensure_ascii=False), encoding="utf-8")
        argv = ["x", "--graph", str(d / "g.graphml"),
                "--vdb", str(d / "vdb_entities.json"), str(d / "vdb_rel.json"), *extra]
        if "canon.jsonl" in files:
            argv += ["--canon", str(d / "canon.jsonl")]
        old, buf = sys.argv, io.StringIO()
        sys.argv = argv
        try:
            with redirect_stdout(buf):
                rc = m.main()
        finally:
            sys.argv = old
        return rc, json.loads(buf.getvalue())


VDB2 = {"data": [{"entity_name": "梅芙", "__id__": "x"}, {"entity_name": "沙姆希尔", "__id__": "y"}]}
VDB3 = {"data": [{"entity_name": n, "__id__": i} for i, n in
                 enumerate(["梅芙", "沙姆希尔", "裸节点"])]}
VDBREL1 = {"data": [{"source": "梅芙", "target": "沙姆希尔"}]}


class 解析(unittest.TestCase):
    def test_graphml属性与边数(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "g.graphml"
            p.write_text(GRAPHML, encoding="utf-8")
            nodes, edges = m.graphml_nodes(p)
            self.assertEqual((len(nodes), edges), (3, 1))
            self.assertEqual(nodes[0]["entity_type"], "PERSON")
            self.assertEqual(nodes[0]["source_id"], "卷1·第1话·行1237")

    def test_vdb三种壳形(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "v.json"
            for shape, want in [({"data": [{"name": "a"}]}, 1),
                                ([{"name": "a"}, {"name": "b"}], 2),
                                ({"k1": {"name": "a"}}, 1)]:
                p.write_text(json.dumps(shape), encoding="utf-8")
                self.assertEqual(m.vdb_count(p)[0], want, str(shape))


class 四道检查(unittest.TestCase):
    def test_C1抓到半途写(self):
        rc, rep = _run({"g.graphml": GRAPHML, "vdb_entities.json": VDB2,
                        "vdb_rel.json": VDBREL1})
        self.assertEqual(rc, 1)
        self.assertEqual(rep["计数"]["图节点"], 3)
        self.assertEqual(rep["计数"]["实体向量"], 2)
        self.assertTrue(any("C1" in x for x in rep["未过项"]))
        self.assertEqual(rep["差集"]["图有向量无"], ["裸节点"], "图里有、向量库里没有的那条要点名")

    def test_C3无坐标节点(self):
        rc, rep = _run({"g.graphml": GRAPHML, "vdb_entities.json": VDB3,
                        "vdb_rel.json": VDBREL1})
        self.assertIn("裸节点", rep["缺坐标清单"])
        self.assertTrue(any("C3" in x for x in rep["未过项"]))

    def test_全等且带坐标时只剩C3不过(self):
        # 第三个节点无坐标 ⇒ 仍 FAIL；证明 C1/C2 与 C3 是分开报的，不是一锅端
        rc, rep = _run({"g.graphml": GRAPHML, "vdb_entities.json": VDB3,
                        "vdb_rel.json": VDBREL1})
        self.assertFalse(any("C1" in x for x in rep["未过项"]))
        self.assertFalse(any("C2" in x for x in rep["未过项"]))

    def test_正典名单为空判失败而非通过(self):
        rc, rep = _run({"g.graphml": GRAPHML, "vdb_entities.json": VDB3,
                        "vdb_rel.json": VDBREL1, "canon.jsonl": ""})
        self.assertEqual(rc, 1)
        self.assertTrue(any("C4" in x for x in rep["未过项"]),
                        "判定面为空不许读成『都对得上』")

    def test_与正典对账只报数(self):
        canon = "\n".join(json.dumps({"canonical_name": n}, ensure_ascii=False)
                          for n in ["梅芙", "沙姆希尔"])
        rc, rep = _run({"g.graphml": GRAPHML, "vdb_entities.json": VDB3,
                        "vdb_rel.json": VDBREL1, "canon.jsonl": canon})
        self.assertIn("派生层名字命中正典", rep["与正典对账"])
        self.assertIn("口径上界", rep["与正典对账"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
