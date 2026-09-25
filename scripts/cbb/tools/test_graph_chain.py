# -*- coding: utf-8 -*-
"""test_graph_chain.py — 链构造器包内自洽测试（Neo4j 缺席→如实 SKIP，不计过）。"""
import importlib
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

try:
    import graph_chain as gc
except Exception as e:  # 依赖缺席
    gc = None
    _import_err = str(e)


@unittest.skipIf(gc is None, f"graph_chain 不可导入: {_import_err if gc is None else ''}")
class TestGraphChain(unittest.TestCase):
    def test_depth_guard(self):
        with self.assertRaises(ValueError):
            gc.chains(["任意"], depth=3)

    def test_empty_seeds(self):
        self.assertEqual(gc.chains([], depth=1), [])

    def test_live_if_available(self):
        try:
            import urllib.request
            with urllib.request.urlopen(gc.BASE + "/", timeout=3):
                pass
        except Exception:
            self.skipTest("Neo4j 缺席（如实跳过，不计过）")
        import graph_chain as gc2
        rows = gc2._cypher("MATCH (a:Entity)-[r:REL]-() WITH a, count(r) AS d "
                           "RETURN a.name AS n ORDER BY d DESC LIMIT 1", {})
        if not rows:
            self.skipTest("图为空")
        seed = rows[0]["row"][0]
        c1 = gc2.chains([seed], depth=1, max_chains=3)
        for c in c1:
            self.assertEqual(len(c["nodes"]), 2)
            self.assertTrue(c["hops"][0]["rel"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
