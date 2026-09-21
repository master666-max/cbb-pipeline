# -*- coding: utf-8 -*-
"""test_embed_dedup_scan.py — 嵌入查重工具单测（零网络：伪 embed_fn）。
py -X utf8 cbb/tools/test_embed_dedup_scan.py  （或 unittest 默认发现）
"""
import unittest

import embed_dedup_scan as m


def norm(v):
    n = (sum(x * x for x in v)) ** 0.5
    return [x / n for x in v]


FAKE = {"缇亚": norm([1.0, 0.02]), "缇妠": norm([0.999, 0.05]),   # 近同向 → 高相似
        "迷宫": norm([0.0, 1.0]), "基督·欧亚": norm([1.0, -0.5]),
        "克劳": norm([-1.0, 0.1]), "塞拉·雷迪安特": norm([0.5, -0.9])}


def fake_embed(texts):
    return [FAKE[t] for t in texts]


class TestCosine(unittest.TestCase):
    def test_identical_is_one(self):
        self.assertAlmostEqual(m.cosine([1, 0], [1, 0]), 1.0)

    def test_orthogonal_is_zero(self):
        self.assertAlmostEqual(m.cosine([1, 0], [0, 1]), 0.0)

    def test_zero_vector_safe(self):
        self.assertEqual(m.cosine([0, 0], [1, 1]), 0.0)


class TestBucket(unittest.TestCase):
    def test_boundaries(self):
        self.assertEqual(m.bucket(0.95), "dup_suspect")   # ≥0.95 含等
        self.assertEqual(m.bucket(0.9499), "uncertain")
        self.assertEqual(m.bucket(0.85), "uncertain")     # 0.85~0.95 含下界
        self.assertEqual(m.bucket(0.8499), "ok")

    def test_threshold_constants_钉住工单裁决(self):
        self.assertEqual((m.DUP_TAU, m.UNCERTAIN_TAU), (0.95, 0.85))


class TestScan(unittest.TestCase):
    def test_high_similarity_goes_dup(self):
        r = m.scan(["缇妠"], ["缇亚", "迷宫"], fake_embed)
        self.assertEqual(len(r["dup_suspect"]), 1)
        self.assertEqual(r["dup_suspect"][0]["library_match"], "缇亚")
        self.assertGreaterEqual(r["dup_suspect"][0]["similarity"], 0.95)

    def test_dissimilar_ok(self):
        r = m.scan(["迷宫"], ["基督·欧亚", "克劳"], fake_embed)
        self.assertEqual(r["dup_suspect"], [])
        self.assertEqual(r["uncertain"], [])

    def test_empty_inputs(self):
        self.assertEqual(m.scan([], ["迷宫"], fake_embed), {"dup_suspect": [], "uncertain": [], "pairs": []})
        self.assertEqual(m.scan(["迷宫"], [], fake_embed), {"dup_suspect": [], "uncertain": [], "pairs": []})

    def test_pairs_records_best_match(self):
        r = m.scan(["缇妠", "迷宫"], ["缇亚", "迷宫"], fake_embed)
        self.assertEqual(r["pairs"][1][0], "迷宫")
        self.assertEqual(r["pairs"][1][1], "迷宫")

    def test_pure_no_side_effect_determinism(self):
        a = m.scan(["缇妠"], ["缇亚"], fake_embed)
        b = m.scan(["缇妠"], ["缇亚"], fake_embed)
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main(verbosity=2)
