# -*- coding: utf-8 -*-
"""test_图库隔离.py — 建实例前的三条硬规矩必须可测（零 Docker、零网络）

判据锚：① 只绑回环 ② 端口先预检不许硬抢 ③ 口令不落 argv/仓内；
        ④ 归属四态 LEGIT/FOREIGN/UNDETERMINED/（不可达由 probe 侧管）——空与未判定不许混。
"""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import 图库隔离 as g  # noqa: E402


class 端口(unittest.TestCase):
    def test_撞端口顺延且跳过已占(self):
        taken = {7694, 7695, 7697}
        h, b = g.pick_ports(7697, 7696, taken)          # 期望避开 7694/7695/7697
        self.assertNotIn(h, taken)
        self.assertNotIn(b, taken)
        self.assertEqual(h - b, 1, "http/bolt 保持错开一位")

    def test_全空时按申请值给(self):
        self.assertEqual(g.pick_ports(7711, 7710, set()), (7711, 7710))


class 命令(unittest.TestCase):
    def test_只绑回环(self):
        c = g.build_command("neo4j-x", 7697, 7696, "v", None, True)
        pubs = [c[i + 1] for i, x in enumerate(c) if x == "--publish"]
        self.assertTrue(all(p.startswith("127.0.0.1:") for p in pubs), pubs)

    def test_口令不进命令行(self):
        c = g.build_command("neo4j-x", 7697, 7696, "v", "MY_PV", False, env_file="/secrets/x.env")
        self.assertIn("--env-file", c)
        self.assertNotIn("MY_PV", " ".join(c), "认证变量名也不该出现在 argv（值走 env-file）")
        self.assertNotIn("neo4j/none", " ".join(c))

    def test_无认证要显式声明(self):
        with self.assertRaises(ValueError):
            g.build_command("neo4j-x", 7697, 7696, "v", None, False)     # 既不给 env 也不声明 none
        with self.assertRaises(ValueError):
            g.build_command("neo4j-x", 7697, 7696, "v", "MY_PV", False)  # 给 env 却不给 env-file

    def test_空库与未判定不许混(self):
        v0 = g.ownership_verdict(0, 0, {}, "tok")
        v1 = g.ownership_verdict(50, 0, {}, "tok")
        v2 = g.ownership_verdict(50, 50, {}, "tok")
        v3 = g.ownership_verdict(901, 0, {"mishen": 44, "<无标记>": 857}, "tok")
        self.assertEqual((v0["verdict"], v1["verdict"], v2["verdict"], v3["verdict"]),
                         ("LEGIT", "UNDETERMINED", "LEGIT", "FOREIGN"))
        self.assertIn("未判定不等于干净", v1["结论"])
        self.assertIn("假干净", v3["结论"])
        self.assertEqual(v3["他项目分布"]["<无标记>"], 857, "无标记节点算脏，不许假定归属")

    def test_实例名可预测且只含安全字符(self):
        self.assertEqual(g.instance_name("Zhongmo_Canon/"), "neo4j-zhongmo-canon")


if __name__ == "__main__":
    unittest.main(verbosity=2)
