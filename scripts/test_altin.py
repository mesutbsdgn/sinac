#!/usr/bin/env python3
"""Altın kümeler (F3, 22.11.2026): geliştirme kümesi (tests/altin, 40 belge, Sonnet 5.5) ve iki görülmemiş küme
(tests/gorulmemis-gemini, 20 belge, Gemini 4 Neon; tests/gorulmemis-deepseek, 15 belge, DeepSeek V4.1 Flash).
Beklentiler belgeler yazılırken, betik çalıştırılmadan kaydedildi. Karar, kaçan ENGEL/HATA ve yanlış ENGEL/HATA
kilitlenir; alan isabeti yalnız ölçülür (scripts/altin_olc.py), test edilmez.
2.1.1 (23.11.2026): beş sınama kümesi eklendi (tests/sinama-*, 103 belge; Sonnet 5.5, Claude ve Gemini 4 Neon yazdı)."""
import os
import sys
import unittest

sys.dont_write_bytecode = True
BURA = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BURA)
import altin_olc  # noqa: E402

KUMELER = ["altin", "gorulmemis-gemini", "gorulmemis-deepseek",
           # 23.11.2026 sınaması ve 2.1.1 düzeltmesi: hepsi ilk geçişte açık bulmak için kullanıldı, artık regresyon kümesidir
           "sinama-sonnet", "sinama-claude", "sinama-neon1", "sinama-sonnet2", "sinama-neon2"]


class AltinKumeler(unittest.TestCase):
    def test_kararlar_ve_engeller(self):
        for ad in KUMELER:
            altin_olc.KLASOR = os.path.join(BURA, "tests", ad)
            _, sonuc = altin_olc.olc()
            for x in sonuc:
                with self.subTest(kume=ad, dosya=x["dosya"]):
                    self.assertEqual(x["karar_bulunan"], x["karar_beklenen"])
                    self.assertEqual(x["kacan"], [])
                    self.assertEqual(x["yanlis"], [])


if __name__ == "__main__":
    unittest.main(verbosity=1)
