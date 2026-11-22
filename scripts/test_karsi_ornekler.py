#!/usr/bin/env python3
"""Bağımsız karşı örnek kümesi: GPT-6.1 Sol ve Qwen4 Max Preview incelemelerinin (22.11.2026) karşı örnekleri.
Örnekleri kodu yazan değil, iki bağımsız inceleyici üretti. python3 scripts/test_karsi_ornekler.py"""
import json
import os
import sys
import unittest

sys.dont_write_bytecode = True
BURA = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BURA)
import ogretim_denetim as o  # noqa: E402

ORNEKLER = json.load(open(os.path.join(BURA, "tests", "karsi_ornekler.json"), encoding="utf-8"))


class KarsiOrnekler(unittest.TestCase):
    def test_hepsi(self):
        for i, k in enumerate(ORNEKLER):
            with self.subTest(i=i, kaynak=k["kaynak"], girdi=k["girdi"][:50]):
                s = o.denetle(k["girdi"], None, k["alan"], None, 2026)
                kurallar = {b["kural"] for b in s["bulgular"]}
                mesaj = " ".join(b["mesaj"] for b in s["bulgular"])
                if k["karar"]:
                    self.assertEqual(s["karar"], k["karar"])
                for kr in k["kural_var"]:
                    self.assertIn(kr, kurallar)
                for kr in k["kural_yok"]:
                    self.assertNotIn(kr, kurallar)
                for p in k["var"]:
                    self.assertIn(p, mesaj)
                for p in k["yok"]:
                    self.assertNotIn(p, mesaj)


if __name__ == "__main__":
    unittest.main(verbosity=1)
