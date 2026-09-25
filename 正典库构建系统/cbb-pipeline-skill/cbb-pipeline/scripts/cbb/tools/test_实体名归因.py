# -*- coding: utf-8 -*-
"""test_实体名归因.py — 四分类必须各有一正一负对照，且"不许默认判模型的锅"要能测

夹具全部现造（临时目录＋自写语料），不依赖外部语料与网络。
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
import 实体名归因 as m  # noqa: E402

CORPUS = "梅芙莉莎握紧沙姆希尔。弗恩·西蒙站在中庭。言万说：面具是审判者给的。"


class 归一(unittest.TestCase):
    def test_间隔号与全角被抹平(self):
        self.assertEqual(m.canon("弗恩·西蒙"), "弗恩西蒙")
        self.assertEqual(m.canon("Ａ９２３"), "a923")

    def test_空名不炸(self):
        self.assertEqual(m.canon(""), "")


class 分类(unittest.TestCase):
    def setUp(self):
        self.low = CORPUS.lower()
        self.norm = m.canon(CORPUS)

    def test_逐字命中(self):
        cls, _ = m.classify("沙姆希尔", self.low, self.norm, {}, False)
        self.assertEqual(cls, "命中")

    def test_A_少写间隔号算写法变体不算幻觉(self):
        cls, _ = m.classify("弗恩西蒙", self.low, self.norm, {}, False)
        self.assertEqual(cls, "A 写法变体")

    def test_B_括注剥掉能找到(self):
        cls, _ = m.classify("言万（代称）", self.low, self.norm, {}, False)
        self.assertEqual(cls, "B 括注修饰")

    def test_C排在A前_有原始回执才敢判流水线的锅(self):
        raws = {"弗恩西蒙": ["弗恩·西蒙"]}          # 原文里正是「弗恩·西蒙」
        cls, why = m.classify("弗恩西蒙", self.low, self.norm, raws, True)
        self.assertEqual(cls, "C 转换吃字符")
        self.assertIn("原始写法", why)

    def test_无原始回执时同一名字只判A且带保留意见(self):
        cls, why = m.classify("弗恩西蒙", self.low, self.norm, {}, False)
        self.assertEqual(cls, "A 写法变体")
        self.assertIn("不能排除", why)               # 不许把责任默认推给模型

    def test_D1_可合成与D2_纯命名分得开(self):
        c1, _ = m.classify("梅芙莉莎的手枪", self.low, self.norm, {}, False)
        c2, _ = m.classify("终末对抗", self.low, self.norm, {}, False)
        self.assertEqual((c1, c2), ("D1 可合成", "D2 纯命名"))


class 端到端(unittest.TestCase):
    def _run(self, rows, strict=False, raw=None):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            cp = d / "corpus.txt"
            cp.write_text(CORPUS, encoding="utf-8")
            inp = d / "e.jsonl"
            inp.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows),
                           encoding="utf-8")
            argv = ["x", "--in", str(inp), "--corpus", str(cp)]
            if raw:
                rd = d / "raw"
                rd.mkdir()
                (rd / "0").write_text(json.dumps({"result": {"response": raw}},
                                                 ensure_ascii=False), encoding="utf-8")
                argv += ["--raw-dir", str(rd)]
            if strict:
                argv.append("--strict")
            buf = io.StringIO()
            old = sys.argv
            sys.argv = argv
            try:
                with redirect_stdout(buf):
                    rc = m.main()
            finally:
                sys.argv = old
            return rc, json.loads(buf.getvalue())

    def test_计数与处置映射都落盘(self):
        rc, out = self._run([{"name": "沙姆希尔"}, {"name": "终末对抗", "support": 2}])
        self.assertEqual(rc, 0)
        self.assertEqual(out["计数"]["命中"], 1)
        self.assertEqual(out["计数"]["D2 纯命名"], 1)
        self.assertIn("处置映射", out)
        self.assertIn("口径上界", out)   # 只报数不报界＝不合格

    def test_零支撑自造词严格模式退出码1(self):
        rc, out = self._run([{"name": "终末对抗", "support": 0}], strict=True)
        self.assertEqual(rc, 1)
        self.assertEqual(out["计数"]["reject 零支撑自造"], 1)

    def test_无support字段不判reject(self):
        rc, out = self._run([{"name": "终末对抗"}])
        self.assertEqual(rc, 0)
        self.assertNotIn("reject 零支撑自造", out["计数"])

    def test_原始回执判出C类(self):
        rows = [{"name": "弗恩西蒙", "support": 1}]
        rc, out = self._run(rows, raw='他提到"弗恩·西蒙"一次')
        self.assertEqual(rc, 0)
        self.assertEqual(out["计数"].get("C 转换吃字符"), 1,
                         "原写法可精确命中而终值不可 ⇒ 该记流水线的锅")


class 输入(unittest.TestCase):
    def test_每行一名支持(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "n.txt"
            p.write_text("沙姆希尔\n\n梅芙莉莎的手枪\n", encoding="utf-8")
            rows = m.load_rows(p)
            self.assertEqual([r["name"] for r in rows], ["沙姆希尔", "梅芙莉莎的手枪"])

    def test_text_unit_ids也算支撑计数(self):
        self.assertEqual(m.support_of({"name": "x", "text_unit_ids": ["a", "b"]}), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
