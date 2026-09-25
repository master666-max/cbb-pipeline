# -*- coding: utf-8 -*-
"""test_web_supplement.py — 网络补充层的闸门必须可测（零网络：HTTP 打桩）

上游提交语称本件带"admissible=False 硬标记／准入闸／引文核验必拒"，但随仓无同名测试。
缺测试的闸门等于没闸门：一次重构就能把 raise 悄悄删掉而全绿。
"""
import importlib
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ws = importlib.import_module("web_supplement")

# 桩照引擎真实结构写（<li class="b_algo"> 一块一条）；写成别的结构就是在测解析器的另一条分支
HTML = ("""<html><body><ol>"""
        """<li class="b_algo"><h2><a href="https://ex.test/a">相川涡波 设定</a></h2>"""
        """<p>手持创世手环的少年</p></li>"""
        """<li class="b_algo"><h2><a href="https://ex.test/b">斯诺·沃克</a></h2>"""
        """<p>情报传递者</p></li>"""
        """</ol></body></html>""")


class 抓取(unittest.TestCase):
    def setUp(self):
        self._原 = ws._http
        ws._http = lambda url, timeout=15.0: HTML

    def tearDown(self):
        ws._http = self._原

    def test_返回体必带不可采信硬标记(self):
        rep = ws.search("涡波", n=2)
        self.assertIs(rep["admissible"], False, "网络材料必须硬标记为不可采信")
        self.assertEqual(rep["confidence"], "low")
        self.assertEqual(len(rep["results"]), 2, rep)
        self.assertTrue(all(r.get("url") for r in rep["results"]), "每条要可回溯到 URL")
        self.assertEqual(rep["results"][0]["title"], "相川涡波 设定")

    def test_标签剥净不留尖括号(self):
        for r in ws.search("涡波", n=2)["results"]:
            self.assertNotIn("<", json.dumps(r, ensure_ascii=False), r)

    def test_引擎失败如实披露不伪造(self):
        def boom(url, timeout=15.0):
            raise RuntimeError("网络不通")
        ws._http = boom
        rep = ws.search("涡波", n=2)
        self.assertEqual(rep["results"], [])
        self.assertTrue(rep["errors"], "失败必须进 errors，不许静默给空结果")


class 准入闸(unittest.TestCase):
    def test_网络条目拒入正典(self):
        with self.assertRaises(PermissionError):
            ws.guard_block_admission({"admissible": False, "source": "web"})

    def test_低置信度同样拒(self):
        with self.assertRaises(PermissionError):
            ws.guard_block_admission({"confidence": "low", "source": "web"})

    def test_库内记录不误伤(self):
        """闸门只挡网络材料；把库内记录也挡了就是自残（负对照）。"""
        ws.guard_block_admission({"record_id": "e-1", "source": "本体库"})

    def test_无标记空条目拒放行(self):
        """没 admissible、没 confidence、也没来源 ⇒ 判不了就不放行（缺席/为空/通过不同形）。"""
        for bad in ({}, {"title": "某网页"}):
            with self.assertRaises(ValueError, msg=str(bad)):
                ws.guard_block_admission(bad)


class 不写库(unittest.TestCase):
    def test_本件不碰写库通道(self):
        src = (HERE / "web_supplement.py").read_text(encoding="utf-8")
        for mod in ("cbb_store", "ledger_chain", "apipeline", ".insert("):
            self.assertNotIn(mod, src, f"网络补充层不该碰写库通道：{mod}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
