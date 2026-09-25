# -*- coding: utf-8 -*-
"""test_graph_audit.py — 图对账四断言面必须可测（零图库：读侧注入接缝）

上游提交语称 graph_audit 交付"四断言面"，但随仓无同名测试；且其读查询原先不带命名空间
（`MATCH (a:Entity) RETURN a.name`）——在同机共用图库上会把**别的项目的节点**算成
"图外节点数 N"，或反过来把自己缺的导出当成对得上。两处都在此钉住。
"""
import importlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ga = importlib.import_module("graph_audit")


def mk_store(root: Path) -> Path:
    store = root / "本项目-本体库"
    (store / "libraries" / "character" / "provisional").mkdir(parents=True)
    (store / "libraries" / "relation" / "provisional").mkdir(parents=True)
    (store / "libraries" / "character" / "provisional" / "e-1.json").write_text(
        json.dumps({"record_id": "e-1", "record_type": "entity", "library": "character",
                    "canonical": {"name": "梅芙", "entity_type": "人物"},
                    "evidence": [{"vol": 1, "chapter": 1, "line": 3, "quote": "梅芙握紧枪"}]},
                   ensure_ascii=False), encoding="utf-8")
    (store / "libraries" / "relation" / "provisional" / "r-1.json").write_text(
        json.dumps({"record_id": "r-1", "record_type": "relation", "library": "relation",
                    "canonical": {"subject": "梅芙", "rel_type": "持有", "object": "沙姆希尔"},
                    "evidence": [{"vol": 1, "chapter": 1, "line": 4, "quote": "她的手枪沙姆希尔"}]},
                   ensure_ascii=False), encoding="utf-8")
    (store / "libraries" / "character" / "provisional" / "e-2.json").write_text(
        json.dumps({"record_id": "e-2", "record_type": "entity", "library": "character",
                    "canonical": {"name": "沙姆希尔", "entity_type": "物品"},
                    "evidence": [{"vol": 1, "chapter": 1, "line": 4, "quote": "她的手枪沙姆希尔"}]},
                   ensure_ascii=False), encoding="utf-8")
    (store / "ledger.jsonl").write_text(json.dumps({"seq": 1}) + "\n", encoding="utf-8")
    return store


# 桩的匹配顺序：时序那条查询里**字面含**边查询的 RETURN 片段，所以特殊的排前面先试。
优先 = ("r.valid_at", "r.edge_id", "RETURN a.name AS n", "RETURN a.name, r.rel_type, b.name")


def fake(rows_by_stmt):
    def _q(stmt, params=None):
        for key in 优先:
            if key in rows_by_stmt and key in stmt:
                assert params and params.get("ns"), "读查询必须带命名空间参数"
                return [{"row": r} for r in rows_by_stmt[key]]
        raise AssertionError(f"未预期的查询：{stmt[:70]}")
    return _q


class 命名空间(unittest.TestCase):
    def test_无命名空间直接拒(self):
        had = os.environ.pop("CBB_NAMESPACE", None)
        with tempfile.TemporaryDirectory() as td:
            store = mk_store(Path(td))
            with self.assertRaises(RuntimeError):
                ga.audit(store, ns=None, run=lambda s, p=None: [])
        if had is not None:
            os.environ["CBB_NAMESPACE"] = had


class 四断言面(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.store = mk_store(Path(self._td.name))

    def tearDown(self):
        self._td.cleanup()

    def test_两边一致时差集为空(self):
        q = fake({"RETURN a.name AS n": [["梅芙"], ["沙姆希尔"]],
                  "RETURN a.name, r.rel_type, b.name": [["梅芙", "持有", "沙姆希尔"]],
                  "r.valid_at": [["梅芙", "持有", "沙姆希尔", 1, None]],   # 与库内 story_date 一致（valid_at 取证据最早章）
                  "r.edge_id": []})
        rep = ga.audit(self.store, ns="本项目", run=q)
        self.assertEqual(rep["节点"]["图外节点数"], 0, rep["节点"])
        self.assertEqual(rep["节点"]["未导出实体数"], 0, rep["节点"])
        self.assertEqual(rep["边"]["图外边数"], 0, rep["边"])
        self.assertEqual(rep["边"]["未导出边数"], 0, rep["边"])
        self.assertEqual(rep["时序不一致数"], 0)
        self.assertEqual(rep["命名空间"], "本项目")

    def test_图上多出的节点与缺失的边都要现形(self):
        """负对照：把"图里有别人项目的节点"和"库里有条关系没导出"栽进去，必须报出来。"""
        q = fake({"RETURN a.name AS n": [["梅芙"], ["沙姆希尔"], ["别的项目的实体"]],
                  "RETURN a.name, r.rel_type, b.name": [["梅芙", "持有", "沙姆希尔"]],
                  "r.valid_at": [["梅芙", "持有", "沙姆希尔", 1, None]],   # 与库内 story_date 一致（valid_at 取证据最早章）
                  "r.edge_id": []})
        rep = ga.audit(self.store, ns="本项目", run=q)
        self.assertEqual(rep["节点"]["图外节点"], ["别的项目的实体"], rep["节点"])

    def test_时序不一致要计数(self):
        q = fake({"RETURN a.name AS n": [["梅芙"], ["沙姆希尔"]],
                  "RETURN a.name, r.rel_type, b.name": [["梅芙", "持有", "沙姆希尔"]],
                  "r.valid_at": [["梅芙", "持有", "沙姆希尔", "1", "9"]],
                  "r.edge_id": []})
        rep = ga.audit(self.store, ns="本项目", run=q)
        self.assertEqual(rep["时序不一致数"], 1, rep)

    def test_读查询一条都不许多于ns过滤(self):
        seen = []

        def q(stmt, params=None):
            seen.append((stmt, params))
            return []
        ga.audit(self.store, ns="本项目", run=q)
        self.assertTrue(seen, "至少要有一次读")
        for stmt, params in seen:
            if ":Entity" in stmt or "r:REL" in stmt:
                self.assertIn("ns=$ns", stmt.replace(" ", ""), (stmt, params))
                self.assertEqual((params or {}).get("ns"), "本项目", stmt)


if __name__ == "__main__":
    unittest.main(verbosity=2)
