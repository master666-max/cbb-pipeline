# -*- coding: utf-8 -*-
"""test_路径惯例.py — 三条判据可测：能推的推、推不出报错、绝不凭空建上一项目的目录"""
import importlib
import os
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
惯 = importlib.import_module("路径惯例")


class 推导(unittest.TestCase):
    def setUp(self):
        import tempfile
        self._td = tempfile.TemporaryDirectory()
        self.root = Path(self._td.name)

    def tearDown(self):
        self._td.cleanup()

    def test_从store反推项目根与工作区(self):
        store = self.root / "甲项目-本体库"
        store.mkdir()
        (self.root / "甲项目-工作区").mkdir()
        self.assertEqual(惯.project_root(store), self.root)
        self.assertEqual(惯.workspace_of(store).name, "甲项目-工作区")

    def test_无惯例工作区时退到通用名(self):
        store = self.root / "乙-本体库"
        store.mkdir()
        self.assertEqual(惯.workspace_of(store).name, "工作区")

    def test_绝不凭空造出上一项目的目录名(self):
        """回归锚：旧版检索层默认把日志写到 <同级>/迷深实战-工作区/logs/，换项目就凭空长出一棵树。"""
        store = self.root / "丙-本体库"
        store.mkdir()
        ws = 惯.workspace_of(store)
        self.assertNotIn("迷深", str(ws))
        self.assertFalse((self.root / "迷深实战-工作区").exists())

    def test_explicit优先(self):
        store = self.root / "丁-本体库"
        store.mkdir()
        e = self.root / "别处"
        self.assertEqual(惯.workspace_of(store, e), e)


class 图基址(unittest.TestCase):
    def test_不给就报错不兜默认(self):
        old = os.environ.pop("NEO4J_HTTP", None)
        try:
            with self.assertRaises(惯.GraphBaseMissing):
                惯.graph_base(None)
        finally:
            if old is not None:
                os.environ["NEO4J_HTTP"] = old

    def test_env与参数都算给了且去掉尾斜杠(self):
        old = os.environ.get("NEO4J_HTTP")
        os.environ["NEO4J_HTTP"] = "http://127.0.0.1:7474/"
        try:
            self.assertEqual(惯.graph_base(), "http://127.0.0.1:7474")
            self.assertEqual(惯.graph_base("http://x:1/"), "http://x:1")
        finally:
            if old is None:
                os.environ.pop("NEO4J_HTTP", None)
            else:
                os.environ["NEO4J_HTTP"] = old

    def test_报错文本里带补救动作(self):
        old = os.environ.pop("NEO4J_HTTP", None)
        try:
            惯.graph_base(None)
        except 惯.GraphBaseMissing as e:
            self.assertIn("--base", str(e))
            self.assertIn("NEO4J_HTTP", str(e))
        finally:
            if old is not None:
                os.environ["NEO4J_HTTP"] = old


if __name__ == "__main__":
    unittest.main(verbosity=2)
