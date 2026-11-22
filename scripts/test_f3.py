#!/usr/bin/env python3
"""F3 testleri (dile duyarlı alan tespiti, sayı biçimi, lab dönüşümü, tablo doz hesabı): python3 scripts/test_f3.py"""
import os
import sys
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ogretim_denetim as o  # noqa: E402
import sozluk_goc  # noqa: E402

SAGLIK = {"tip", "dis", "hemsirelik", "eczacilik", "veteriner", "beslenme", "fizyoterapi", "acil", "psikoloji"}


def denetle(metin, **kw):
    return o.denetle(metin, None, kw.get("alan"), None, 2026)


def kural(s, ad, duzey=None):
    return [b for b in s["bulgular"] if b["kural"] == ad and (duzey is None or b["duzey"] == duzey)]


def puanlar(metin, profil=None):
    """Metnin alan puanları (ve kanıtı); profil verilirse o profille."""
    _, govde, ofset = o.on_bilgi(metin)
    satirlar = o.hazirla_satirlar(govde, ofset)
    gor = "\n".join(x["gor"] for x in satirlar)
    birimler, _ = o.birim_analizi(satirlar)
    return o.alan_puanlari(gor, profil or o.profiller(), birimler)


FR = "La classe commence à huit heures et nous avons une leçon pour les enfants dans la salle avec le professeur."
EN = "The patient should be given the dose and the nurse will check it before the drug is used in the ward."
TR = "Bu ilaç hasta için ve gerektiğinde verilir; ancak doz çok yüksek olmamalı ve kayıt tutulmalıdır."


class BirimDili(unittest.TestCase):
    def test_tr_en_fr(self):
        self.assertEqual(o.birim_dil(TR), "tr")
        self.assertEqual(o.birim_dil(EN), "en")
        self.assertEqual(o.birim_dil(FR), "fr")

    def test_yetersiz_isaret_soru_isareti(self):
        for t in ("Maximum dose: 1,000 mg", "Paris", "", "5 mg", "Le chat"):
            with self.subTest(t=t):
                self.assertEqual(o.birim_dil(t), "?")

    def test_turkce_ozgu_harf_tek_basina_yeter_ama_cve_ou_yetmez(self):
        self.assertEqual(o.birim_dil("Adım Ali."), "tr")          # ı: Türkçeye özgü
        self.assertEqual(o.birim_dil("Çocuk üç ölçü"), "?")        # ç ö ü Fransızca/Almancada da var

    def test_elisyon_ve_aksan_fransizca_kaniti(self):
        self.assertEqual(o.birim_dil("J'habite à Paris et c'est dans l'été."), "fr")

    def test_birim_ayirma_ve_kod(self):
        govde = ("# Başlık\n\n" + TR + "\nikinci satır aynı paragraf.\n\n- " + EN + "\n- madde iki\n\n| a | b |\n|---|---|\n"
                 "| " + FR + " | x |\n\n```python\ndef f():\n    return 1\n```\n")
        satirlar = o.hazirla_satirlar(govde)
        birimler, belge = o.birim_analizi(satirlar)
        diller = [(b["tur"], b["dil"]) for b in birimler]
        self.assertIn(("kod", "kod"), diller)
        self.assertIn(("liste", "en"), diller)
        self.assertIn(("tablo", "fr"), diller)
        self.assertIn(("paragraf", "tr"), diller)
        self.assertEqual(sum(1 for t, _ in diller if t == "liste"), 2)      # her liste maddesi ayrı birim
        self.assertIn(belge, ("tr", "en", "fr"))

    def test_soru_isaretli_birim_belge_cogunluguna_gider(self):
        govde = EN + "\n\n" + EN + "\n\nMaximum dose: 1,000 mg\n"
        satirlar = o.hazirla_satirlar(govde)
        birimler, belge = o.birim_analizi(satirlar)
        self.assertEqual(belge, "en")
        self.assertEqual([b["dil"] for b in birimler], ["en", "en", "en"])

    def test_cogunluk_yoksa_tr(self):
        birimler, belge = o.birim_analizi(o.hazirla_satirlar("5 mg\n\nParis\n"))
        self.assertEqual(belge, "tr")
        self.assertTrue(all(b["dil"] == "tr" for b in birimler))

    def test_belge_dili_ciktida(self):
        s = denetle("# 1 Not\n\n" + EN + "\n\n" + EN + "\n")
        self.assertEqual(s["belge_dili"], "en")
        kod, cikti, _ = _calistir_tmp(EN + "\n\n" + EN + "\n")
        self.assertIn("belge dili: en", cikti)


def _calistir_tmp(metin):
    import contextlib
    import io
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        yol = os.path.join(d, "n.md")
        with open(yol, "w", encoding="utf-8") as f:
            f.write(metin)
        cikti, hata = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(cikti), contextlib.redirect_stderr(hata):
            kod = o.main([yol])
        return kod, cikti.getvalue(), hata.getvalue()


class DileDuyarliEslestirme(unittest.TestCase):
    def profil_class(self):
        p = o.profiller()
        p["bilgisayar"]["sozcukler_en"] = p["bilgisayar"].get("sozcukler_en", []) + ["class"]
        return p

    def test_fransizca_classe_bilgisayar_puani_vermez(self):
        pz, _ = puanlar(FR + "\n\nLa classe de français est dans la salle.\n", self.profil_class())
        self.assertEqual(pz["bilgisayar"], 0)

    def test_fransizca_birim_turkce_ek_zinciri_ve_ingilizce_listeye_katilmaz(self):
        p = o.profiller()
        p["bilgisayar"]["sozcukler"] = p["bilgisayar"].get("sozcukler", []) + ["class"]          # Türkçe liste: class+e ek zinciri
        p["bilgisayar"]["sozcukler_en"] = p["bilgisayar"].get("sozcukler_en", []) + ["important"]  # İngilizce liste: tam sözcük
        fr = FR + "\n\nLa classe est important pour les enfants et nous avons une leçon dans la salle avec le professeur.\n"
        self.assertEqual(puanlar(fr, p)[0]["bilgisayar"], 0)
        # aynı sözcükler Türkçe/İngilizce birimde sayılır (kontrol)
        self.assertGreater(puanlar(TR + "\n\nBu classe ve bu için çok önemli bir şey ve bu da çok güzel.\n", p)[0]["bilgisayar"], 0)
        self.assertGreater(puanlar(EN + "\n\nThe important thing is that the nurse will check it before the drug is used.\n", p)[0]["bilgisayar"], 0)

    def test_ingilizce_class_puan_verir_ve_cogul_alir(self):
        pz, _ = puanlar(EN + "\n\nThe class extends the base class; both classes use the loop.\n", self.profil_class())
        self.assertGreaterEqual(pz["bilgisayar"], 3)

    def test_turkce_birimde_ingilizce_liste_sayilmaz_ve_tersi(self):
        pz_tr, _ = puanlar("Bu ilaç ve bu hasta için çok önemli; doz gibi bir şey ve bir patient diagnosis treatment.\n")
        pz_en, _ = puanlar(EN + "\n\nSomething about the hasta and the tanı and the tedavi and the klinik semptom.\n")
        # Türkçe birimde 'patient/diagnosis/treatment' (İngilizce liste) sayılmaz: yalnız 'hasta', 'ilaç', 'doz' (Türkçe liste)
        self.assertLess(pz_tr["tip"], 6)
        self.assertGreater(pz_en["tip"], 0)

    # Sözlük büyüdükçe kırılmasın diye öbek ağırlığı ve ek/çoğul kuralı sabit, küçük bir deneme profiliyle sınanır.
    DENEME = {"_alan_gruplari": {"saglik": ["tip", "hemsirelik"]},
              "tip": {"ad": "Tıp", "sozcukler": ["ilaç"], "obekler": ["yan etki", "kalp yetmezliği"]},
              "hemsirelik": {"ad": "Hemşirelik", "ust": "tip", "sozcukler_en": ["nurse", "nursing"],
                             "obekler_en": ["care plan", "nursing diagnosis"]}}

    def test_obek_agirligi_iki(self):
        pz, kanit = puanlar("Bu bir not ve bu için yan etki yazılır ve bu çok önemlidir.\n", self.DENEME)
        self.assertEqual(pz["tip"], 2.0)
        self.assertIn("yan etki", kanit["tip"])

    def test_obek_son_sozcuk_ek_alir_ve_ingilizce_cogul(self):
        pz, _ = puanlar("Bu not için ve bu kalp yetmezliğinde kullanılır ve çok önemlidir.\n", self.DENEME)
        self.assertEqual(pz["tip"], 2.0)
        pz, _ = puanlar("The nurse follows the care plans and the nursing diagnoses in the ward.\n", self.DENEME)
        self.assertGreaterEqual(pz["hemsirelik"], 4.0)    # care plan(s) 2 + nursing diagnosis(es) 2 (+ nurse)

    def test_kisaltma_dilden_bagimsiz_tam_sozcuk(self):
        pz, _ = puanlar("Le CPR est dans la salle pour les enfants avec le DNA.\n")     # fr birimde de sayılır
        self.assertGreaterEqual(pz["acil"], 1)
        self.assertGreaterEqual(pz["biyoloji"], 1)
        pz, _ = puanlar("The phi value and the dnas of the ward are not abbreviations of the cprs.\n")
        self.assertEqual(pz["kimya"], 0)                  # 'ph' tam sözcük: phi sayılmaz

    def test_kod_blogu_yalniz_bilgisayara_katki_verir(self):
        govde = "Bu not için ve bu bir örnek.\n\n```python\ndef f():\n    return protein + dna\nprint(f())\n```\n"
        pz, _ = puanlar(govde)
        self.assertGreaterEqual(pz["bilgisayar"], 3)      # def, return, print(, python
        self.assertEqual(pz["biyoloji"], 0)               # kodda 'protein' / 'dna' biyoloji sayılmaz
        self.assertEqual(pz["fen"], 0)

    def test_tavan_ve_paylasim_agirligi(self):
        pz, _ = puanlar("Bu not ve bu için ilaç " * 1 + "hasta hasta hasta hasta hasta hasta.\n")
        # 'hasta' tavan 3: tip en çok 3 (hasta) + 1 (ilaç)
        self.assertLessEqual(pz["tip"], 4.0)

    def test_baslik_cift_sayilir(self):
        a, _ = puanlar("Bu not ve bu için çok önemli bir ayrıntı.\n\nhasta\n")
        b, _ = puanlar("Bu not ve bu için çok önemli bir ayrıntı.\n\n# hasta\n")
        self.assertEqual(a["tip"] * 2, b["tip"])


class Sozluk(unittest.TestCase):
    def test_goc_idempotent(self):
        p = o.profiller()
        self.assertEqual(sozluk_goc.goc(p), [])

    def test_ingilizce_oge_turkce_listede_kalmadi(self):
        p = o.profiller()
        for ad in o.alan_adlari(p):
            for s in p[ad].get("sozcukler", []):
                self.assertNotIn(s, sozluk_goc.INGILIZCE - sozluk_goc.IKI_DILDE, ad)
                self.assertNotIn(" ", s.strip(), f"{ad}: {s!r} öbek, obekler'de olmalı")

    def test_gruplar_32_alani_tam_kapsar(self):
        p = o.profiller()
        g = p["_alan_gruplari"]
        self.assertEqual(set(g), {"saglik", "sayisal_fen", "sosyal_beseri", "dil_genel"})
        tum = [a for liste in g.values() for a in liste]
        self.assertEqual(len(tum), len(set(tum)))
        self.assertEqual(set(tum), set(o.alan_adlari(p)))
        self.assertEqual(set(g["saglik"]), SAGLIK)


class Grup(unittest.TestCase):
    def test_ingilizce_kisa_tip_notu_saglik_grubunda(self):
        s = denetle("# 1 Note\n\nThe patient has an infection and the physician started the medication for the "
                    "clinical symptom; the syndrome needs therapy.\n")
        self.assertIn(s["alan"], SAGLIK)
        self.assertEqual(s["tespit"]["grup"], "saglik")

    def test_turkce_acil_vaka_notu_saglik_grubunda(self):
        s = denetle("# 1 Vaka\n\nHasta göğüs ağrısıyla acile geldi. Triyaj yapıldı, ABCDE değerlendirmesi ve KPR hazırlığı "
                    "tamamlandı. Defibrilasyon, entübasyon, hava yolu açıklığı ve şok bulguları izlendi.\n")
        self.assertIn(s["alan"], SAGLIK)
        self.assertEqual(s["tespit"]["grup"], "saglik")

    def test_zayif_alan_ama_saglik_grubu_toplami_tip(self):
        s = denetle("The patient follows a diet and the nursing visit and the physiotherapy are in the plan.\n")
        t = s["tespit"]
        self.assertEqual((s["alan"], t["kaynak"], t["destek"], t["grup"]), ("tip", "grup", "zayıf", "saglik"))
        self.assertTrue(t["kanit"])
        self.assertIn("tip_doz_yazimi", s["kontroller"])          # tip güvenlik kontrolleri geldi

    def test_zayif_alan_baska_grupta_genel_kalir_grup_yazilir(self):
        s = denetle("Bu not için enflasyon, şiir, Osmanlı, demokrasi ve mantık ile bir de felsefe gibi ve çok konu var.\n")
        self.assertEqual(s["alan"], "genel")
        self.assertEqual(s["tespit"]["grup"], "sosyal_beseri")

    def test_grup_yok_esik_alti(self):
        s = denetle("Bu bir not ve bu için çok kısa bir metin.\n")
        self.assertEqual((s["alan"], s["tespit"]["grup"]), ("genel", None))

    def test_secilen_alanin_grubu_yazilir(self):
        s = denetle("Bu bir not.\n", alan="hukuk")
        self.assertEqual(s["tespit"]["grup"], "sosyal_beseri")

    def test_grup_yazdirmada_gorunur(self):
        _, cikti, _ = _calistir_tmp("The patient has an infection and the physician started the medication for the "
                                    "clinical symptom; the syndrome needs therapy.\n\nThe patient is in the ward.\n")
        self.assertIn("grup: saglik", cikti)


EN_DOZ = ("# 1 Dose limit\n\nThe nurse should check the dose and the label before the drug is given to the patient.\n\n"
          "Maximum dose: 1,000 mg\n\nThe order is for the patient and it should be checked by the nurse in the ward.\n")
TR_DOZ = ("# 1 Doz sınırı\n\nHemşire ilacı vermeden önce dozu ve etiketi kontrol eder ve bu hasta için çok önemlidir.\n\n"
          "Doz 1,000 mg olarak verilir.\n\nBu not için hasta ve ilaç kaydı tutulur.\n")


class DileDuyarliSayi(unittest.TestCase):
    def test_en_binlik_virgul_engel_degil(self):
        s = denetle(EN_DOZ)
        self.assertEqual(kural(s, "tip_doz_yazimi"), [])

    def test_tr_binlik_virgul_engel(self):
        s = denetle(TR_DOZ)
        self.assertTrue(kural(s, "tip_doz_yazimi", "ENGEL"))

    def test_en_1150_mg_ondalik_sonu_sifir_degil(self):
        s = denetle(EN_DOZ.replace("1,000", "1,150"))
        self.assertEqual(kural(s, "tip_doz_yazimi"), [])

    def test_en_noktali_sondaki_sifir_yine_engel(self):
        s = denetle(EN_DOZ.replace("1,000 mg", "5.0 mg"))
        self.assertTrue(kural(s, "tip_doz_yazimi", "ENGEL"))

    def test_binlik_nokta_kurali_degismedi(self):
        s = denetle(TR_DOZ.replace("1,000", "1.000"))
        self.assertEqual(kural(s, "tip_doz_yazimi", "ENGEL"), [])

    def test_en_cok_kisimli_binlik(self):
        s = denetle(EN_DOZ.replace("1,000 mg", "12,500 mg"))
        self.assertEqual(kural(s, "tip_doz_yazimi"), [])

    def test_aritmetik_en_satirda_binlik(self):
        dogru = EN_DOZ + "\nExample: 75 kg × 20 mg/kg = 1,500 mg per dose.\n"
        yanlis = EN_DOZ + "\nExample: 75 kg × 20 mg/kg = 1,600 mg per dose.\n"
        self.assertEqual(kural(denetle(dogru), "doz_aritmetigi"), [])
        self.assertTrue(kural(denetle(yanlis), "doz_aritmetigi", "ENGEL"))

    def test_aritmetik_tr_satirda_virgul_ondalik(self):
        # Türkçede 1,500 = 1,5 : 75 × 20 = 1500 ≠ 1,5
        s = denetle(TR_DOZ + "\nÖrnek: 75 kg × 20 mg/kg = 1,500 mg olur.\n")
        self.assertTrue(kural(s, "doz_aritmetigi", "ENGEL"))


def _lab(satir, dil="en"):
    govde = EN if dil == "en" else TR
    return denetle("# 1 Lab\n\n" + govde + "\n\n" + satir + "\n\n" + govde + "\n")


class LabDonusumu(unittest.TestCase):
    def test_kolesterol_yanlis_engel(self):
        s = _lab("Total cholesterol 200 mg/dL = 0.52 mmol/L.")
        b = kural(s, "lab_birim_karisik", "ENGEL")
        self.assertTrue(b)
        self.assertIn("38,67", b[0]["oneri"])
        self.assertIn("88,5", b[0]["oneri"])

    def test_kolesterol_dogru_bulgusuz(self):
        self.assertEqual(kural(_lab("Total cholesterol 200 mg/dL = 5.2 mmol/L."), "lab_birim_karisik"), [])

    def test_kolesterol_turkce(self):
        self.assertTrue(kural(_lab("Total kolesterol 200 mg/dL = 0,52 mmol/L.", "tr"), "lab_birim_karisik", "ENGEL"))
        self.assertEqual(kural(_lab("Total kolesterol 200 mg/dL = 5,2 mmol/L.", "tr"), "lab_birim_karisik"), [])

    def test_ldl_hdl(self):
        self.assertTrue(kural(_lab("LDL 130 mg/dL = 1.3 mmol/L."), "lab_birim_karisik", "ENGEL"))
        self.assertEqual(kural(_lab("LDL 130 mg/dL = 3.36 mmol/L."), "lab_birim_karisik"), [])
        self.assertEqual(kural(_lab("HDL 40 mg/dL = 1.03 mmol/L."), "lab_birim_karisik"), [])
        self.assertTrue(kural(_lab("HDL 40 mg/dL = 10.3 mmol/L."), "lab_birim_karisik", "ENGEL"))

    def test_ldl_kolesterol_cift_bulgu_vermez(self):
        s = _lab("LDL cholesterol 130 mg/dL = 1.3 mmol/L.")
        self.assertEqual(len(kural(s, "lab_birim_karisik", "ENGEL")), 1)

    def test_trigliserit(self):
        self.assertTrue(kural(_lab("Triglyceride 150 mg/dL = 16.9 mmol/L."), "lab_birim_karisik", "ENGEL"))
        self.assertEqual(kural(_lab("Triglyceride 150 mg/dL = 1.69 mmol/L."), "lab_birim_karisik"), [])
        self.assertEqual(kural(_lab("Trigliserit 150 mg/dL = 1,7 mmol/L.", "tr"), "lab_birim_karisik"), [])
        self.assertTrue(kural(_lab("Trigliserit 150 mg/dL = 17 mmol/L.", "tr"), "lab_birim_karisik", "ENGEL"))

    def test_ters_yon(self):
        self.assertEqual(kural(_lab("Total cholesterol 5.2 mmol/L = 200 mg/dL."), "lab_birim_karisik"), [])
        self.assertTrue(kural(_lab("Total cholesterol 5.2 mmol/L = 20 mg/dL."), "lab_birim_karisik", "ENGEL"))

    def test_glukoz_ve_kreatinin_degismedi(self):
        self.assertEqual(kural(_lab("Glucose 126 mg/dL ≈ 7.0 mmol/L."), "lab_birim_karisik"), [])
        self.assertTrue(kural(_lab("Glucose 126 mg/dL = 70 mmol/L."), "lab_birim_karisik", "ENGEL"))
        self.assertEqual(kural(_lab("Creatinine 1 mg/dL = 88.4 µmol/L."), "lab_birim_karisik"), [])

    def test_katsayilar(self):
        self.assertAlmostEqual(o.KATSAYI["c"], 38.67)
        self.assertAlmostEqual(o.KATSAYI["t"], 88.5)
        self.assertAlmostEqual(386.7 / 10, o.KATSAYI["c"], places=2)      # PubChem CID 5997: mmol/L = mg/dL × 10 / MA
        self.assertAlmostEqual(885.4 / 10, o.KATSAYI["t"], places=1)      # PubChem CID 5497163


def _tablo(satirlar, dil="en", baslik="| Weight | Ordered dose rate | Calculated dose |"):
    govde = EN if dil == "en" else TR
    return denetle("# 1 Table\n\n" + govde + "\n\n" + baslik + "\n|---|---|---|\n" + "\n".join(satirlar) + "\n\n" + govde + "\n")


class TabloDozHesabi(unittest.TestCase):
    def test_yanlis_satir_engel(self):
        s = _tablo(["| 60 kg | 15 mg/kg | 900 mg |", "| 70 kg | 15 mg/kg | **1,150 mg** |", "| 80 kg | 15 mg/kg | 1,200 mg |"])
        b = kural(s, "doz_aritmetigi", "ENGEL")
        self.assertEqual(len(b), 1)
        self.assertIn("1050 mg", b[0]["mesaj"])
        self.assertIn("Doz hesabı tutmuyor", b[0]["mesaj"])
        self.assertEqual(b[0]["satir"], 8)

    def test_dogru_tablo_bulgusuz(self):
        s = _tablo(["| 60 kg | 15 mg/kg | 900 mg |", "| 70 kg | 15 mg/kg | **1,050 mg** |", "| 80 kg | 15 mg/kg | 1,200 mg |"])
        self.assertEqual(kural(s, "doz_aritmetigi"), [])

    def test_baslikta_birim_ve_hucrede_sayi(self):
        bas = "| Weight (kg) | Dose (mg/kg) | Dose (mg) |"
        self.assertEqual(kural(_tablo(["| 60 | 15 | 900 |", "| 70 | 15 | 1,050 |"], baslik=bas), "doz_aritmetigi"), [])
        self.assertTrue(kural(_tablo(["| 60 | 15 | 900 |", "| 70 | 15 | 1,150 |"], baslik=bas), "doz_aritmetigi", "ENGEL"))

    def test_turkce_tablo_virgul_ondalik(self):
        bas = "| Kilo (kg) | Doz (mg/kg) | Doz (mg) |"
        self.assertEqual(kural(_tablo(["| 10 | 0,5 | 5 |", "| 20 | 1,5 | 30 |"], "tr", bas), "doz_aritmetigi"), [])
        self.assertTrue(kural(_tablo(["| 10 | 0,5 | 50 |"], "tr", bas), "doz_aritmetigi", "ENGEL"))

    def test_birim_donusumu_mcg(self):
        bas = "| Weight (kg) | Dose (mcg/kg) | Dose (mg) |"
        self.assertEqual(kural(_tablo(["| 10 | 50 | 0.5 |"], baslik=bas), "doz_aritmetigi"), [])
        self.assertTrue(kural(_tablo(["| 10 | 50 | 5 |"], baslik=bas), "doz_aritmetigi", "ENGEL"))

    def test_belirsiz_tablolar_atlanir(self):
        # aralık hücre
        self.assertEqual(kural(_tablo(["| 60 kg | 10-15 mg/kg | 900 mg |"]), "doz_aritmetigi"), [])
        # iki doz sütunu adayı
        bas = "| Weight (kg) | Dose (mg/kg) | Dose (mg) | Dose per day (mg) |"
        self.assertEqual(kural(_tablo(["| 60 | 15 | 100 | 100 |"], baslik=bas), "doz_aritmetigi"), [])
        # günlük/doz başına uyuşmazlığı
        bas = "| Weight (kg) | Dose (mg/kg/day) | Dose per administration (mg) |"
        self.assertEqual(kural(_tablo(["| 60 | 15 | 300 |"], baslik=bas), "doz_aritmetigi"), [])
        # en yüksek doz sütunu doz sayılmaz
        bas = "| Weight (kg) | Dose (mg/kg) | Maximum dose (mg) |"
        self.assertEqual(kural(_tablo(["| 60 | 15 | 500 |"], baslik=bas), "doz_aritmetigi"), [])
        # kilo sütunu yok
        bas = "| Age | Dose (mg/kg) | Dose (mg) |"
        self.assertEqual(kural(_tablo(["| 6 | 15 | 100 |"], baslik=bas), "doz_aritmetigi"), [])

    def test_kod_blogundaki_tablo_taranmaz(self):
        govde = EN + "\n\n```\n| Weight | Dose rate | Dose |\n|---|---|---|\n| 70 kg | 15 mg/kg | 1 mg |\n```\n"
        self.assertEqual(kural(denetle(govde), "doz_aritmetigi"), [])


class LabDuzyaziDonusum(unittest.TestCase):
    """'=' olmadan, bağlayıcı ipucuyla yazılmış dönüşüm (analit + mg/dL + SI değeri)."""

    def eng(self, satir, dil="en"):
        return kural(_lab(satir, dil), "lab_birim_karisik", "ENGEL")

    def hepsi(self, satir, dil="en"):
        return kural(_lab(satir, dil), "lab_birim_karisik")

    def test_tr_glukoz_yanlis_engel(self):
        self.assertTrue(self.eng("Açlık kan glukozu 180 mg/dL ölçülen bir hastada SI karşılığı 14,0 mmol/L olarak raporlanır.", "tr"))

    def test_tr_glukoz_dogru_bulgusuz(self):
        self.assertEqual(self.hepsi("Açlık kan glukozu 180 mg/dL ölçülen bir hastada SI karşılığı 10,0 mmol/L olarak raporlanır.", "tr"), [])

    def test_tr_kreatinin_degeri(self):
        self.assertTrue(self.eng("Serum kreatinin düzeyi 2,0 mg/dL olan hastada SI değeri 120,0 µmol/L düzeyindedir.", "tr"))
        self.assertEqual(self.hepsi("Serum kreatinin düzeyi 2,0 mg/dL olan hastada SI değeri 176,8 µmol/L düzeyindedir.", "tr"), [])

    def test_en_corresponds_to(self):
        self.assertEqual(self.hepsi("A fasting glucose of 126 mg/dL corresponds to 7.0 mmol/L."), [])
        self.assertTrue(self.eng("A fasting glucose of 126 mg/dL corresponds to 70 mmol/L."))

    def test_en_ie_ve_which_is_equivalent(self):
        self.assertTrue(self.eng("Total cholesterol of 200 mg/dL, i.e. 2.6 mmol/L"))
        self.assertEqual(self.hepsi("Total cholesterol of 200 mg/dL, which is equivalent to 5.2 mmol/L"), [])
        self.assertTrue(self.eng("Total cholesterol of 200 mg/dL, which is equivalent to 2.6 mmol/L"))

    def test_ok_ve_ters_yon(self):
        self.assertTrue(self.eng("Glukoz 180 mg/dL → 14 mmol/L.", "tr"))
        self.assertEqual(self.hepsi("Glukoz 180 mg/dL → 10 mmol/L.", "tr"), [])
        self.assertTrue(self.eng("Total cholesterol 5.2 mmol/L equals 20 mg/dL."))
        self.assertEqual(self.hepsi("Total cholesterol 5.2 mmol/L equals 200 mg/dL."), [])

    def test_ipucu_yoksa_denetlenmez(self):
        for satir, dil in (("glukoz 180 mg/dL, 6 saat sonra 7 mmol/L", "tr"), ("Glucose 180 mg/dL, 6 hours later 7 mmol/L", "en")):
            self.assertEqual(self.eng(satir, dil), [])

    def test_cumle_siniri_asilmaz(self):
        self.assertEqual(self.eng("Glucose 180 mg/dL. It equals 7 mmol/L."), [])

    def test_iki_analit_yalniz_acik_cift(self):
        self.assertEqual(self.hepsi("Glucose 180 mg/dL and creatinine 1 mg/dL, i.e. 88.4 µmol/L."), [])
        self.assertTrue(self.eng("Glucose 180 mg/dL and creatinine 1 mg/dL, i.e. 8.4 µmol/L."))
        self.assertEqual(self.eng("Glucose is 180 mg/dL and creatinine is 1 mg/dL, i.e. 7 mmol/L and 88.4 µmol/L."), [])

    def test_mevcut_esitlik_yolu_cift_bulgu_vermez(self):
        self.assertEqual(len(self.eng("Glucose 126 mg/dL = 70 mmol/L.")), 1)
        self.assertEqual(len(self.eng("LDL cholesterol of 130 mg/dL, i.e. 1.3 mmol/L")), 1)


class OgreticiYanlisOrnek(unittest.TestCase):
    """Yazım kuralını anlatan satır ENGEL olmaz; gerçek reçete ENGEL kalır."""

    def _s(self, satir):
        g = EN if satir.isascii() else TR
        return denetle("# 1 Test\n\n" + g + "\n\n" + satir + "\n\n" + g + "\n")

    def test_ogretici_satirlar_engel_degil(self):
        for satir in ('- Tam sayıların sonuna gereksiz sıfır eklenmez. Yanlış yazım örneği: "5,0 mg" yerine "5 mg" yazılmalıdır.',
                      '2. İlaç dozunda sondaki sıfırın ("5,0 mg") oluşturduğu başlıca risk nedir?',
                      "Do not write 5.0 mg; write 5 mg.", "Wrong: 5.0 mg — Right: 5 mg",
                      'Avoid trailing zeros such as "5.0 mg".', "Never write 5.0 mg.", 'Incorrect: "5.0 mg".',
                      "5,0 mg yerine 5 mg yazılmalıdır.", "5,0 mg yazılmamalıdır."):
            with self.subTest(satir=satir):
                self.assertEqual(kural(self._s(satir), "tip_doz_yazimi", "ENGEL"), [])

    def test_gercek_recete_engel_kalir(self):
        for satir in ("Haloperidol 5,0 mg IM verilir.", "Hastaya 5,0 mg verilmemeli, 10 mg verilir.",
                      "Doz: **5,0 mg** (yanlış hesaplanmış olabilir)", "Ketiapin 300,0 mg (hatalı örnek değil)",
                      "Avoid giving haloperidol 5.0 mg to the patient.", "The order was wrong, haloperidol 5.0 mg IM was given.",
                      "Malzemenin yanlış örnek: etiketsiz şırınga olduğunu gösterin, ardından ilaç dozunu 7,0 mg olarak yazın."):
            with self.subTest(satir=satir):
                self.assertTrue(kural(self._s(satir), "tip_doz_yazimi", "ENGEL"))

    def test_ogretici_isaretli_uyari_olarak_kalir(self):
        b = kural(self._s('Avoid trailing zeros such as "5.0 mg".'), "tip_doz_yazimi")
        self.assertTrue(b and all(x["duzey"] == "UYARI" for x in b))


class DuzyaziDozHesabi(unittest.TestCase):
    def _s(self, satir):
        g = EN if (satir.isascii() or "child" in satir) else TR
        return denetle("# 1 Test\n\n" + g + "\n\n" + satir + "\n\n" + g + "\n")

    def eng(self, satir):
        return kural(self._s(satir), "doz_aritmetigi", "ENGEL")

    def hepsi(self, satir):
        return kural(self._s(satir), "doz_aritmetigi")

    def test_en_doz_basina(self):
        self.assertTrue(self.eng("For a 10 kg dog at 5 mg/kg/dose, give 80 mg per dose orally."))
        self.assertEqual(self.hepsi("For a 10 kg dog at 5 mg/kg/dose, give 50 mg per dose orally."), [])

    def test_tr_doz(self):
        self.assertEqual(self.hepsi("20 kg çocuğa 15 mg/kg/doz ile 300 mg verilir."), [])
        self.assertTrue(self.eng("20 kg çocuğa 15 mg/kg/doz ile 450 mg verilir."))

    def test_gunluk_bolunmus_doz(self):
        for d in (300, 150, 100, 75):               # W×R, ÷2, ÷3, ÷4
            self.assertEqual(self.hepsi(f"20 kg çocuğa 15 mg/kg/gün ile {d} mg verilir."), [], d)
        self.assertEqual(self.hepsi("20 kg çocuğa günlük 15 mg/kg ile 150 mg verilir."), [])
        self.assertTrue(self.eng("20 kg çocuğa 15 mg/kg/gün ile 250 mg verilir."))
        self.assertTrue(self.eng("For a 20 kg child at 15 mg/kg/day, give 250 mg per dose."))

    def test_siklik_belirsiz_uyari(self):
        b = self.hepsi("20 kg çocuğa 15 mg/kg ile 250 mg verilir.")
        self.assertTrue(b and all(x["duzey"] == "UYARI" for x in b))
        self.assertEqual(self.hepsi("20 kg çocuğa 15 mg/kg ile 300 mg verilir."), [])

    def test_tavan_sayisi_doz_sayilmaz(self):
        self.assertEqual(self.hepsi("For a 20 kg child at 15 mg/kg/dose, give 300 mg per dose; do not exceed 500 mg."), [])
        self.assertEqual(self.hepsi("20 kg çocuğa 15 mg/kg/doz ile en fazla 450 mg verilir."), [])
        self.assertEqual(self.hepsi("For a 20 kg child at 15 mg/kg/dose, the maximum 250 mg applies; give 300 mg."), [])
        self.assertTrue(self.eng("For a 20 kg child at 15 mg/kg/dose, give 500 mg (maximum 500 mg)."))

    def test_en_binlik_virgul(self):
        self.assertEqual(self.hepsi("For a 100 kg adult at 15 mg/kg/dose, give 1,500 mg per dose."), [])
        self.assertTrue(self.eng("For a 100 kg adult at 15 mg/kg/dose, give 1,000 mg per dose."))
        self.assertEqual(self.hepsi("100 kg erişkine 15 mg/kg/doz ile toplam 1.500 mg verilir."), [])

    def test_birim_donusumu_mcg(self):
        self.assertEqual(self.hepsi("For a 10 kg dog at 50 mcg/kg/dose, give 0.5 mg per dose."), [])
        self.assertTrue(self.eng("For a 10 kg dog at 50 mcg/kg/dose, give 5 mg per dose."))

    def test_belirsiz_cumleler_atlanir(self):
        self.assertEqual(self.hepsi("A 10 kg dog needs 10-15 mg/kg/dose, give 80 mg."), [])
        self.assertEqual(self.hepsi("10 kg dog and 20 kg dog at 5 mg/kg/dose, give 80 mg."), [])

    def test_carpma_biciminde_cift_bulgu_yok(self):
        self.assertEqual(len(self.eng("For a 75 kg adult: 75 kg × 20 mg/kg = 1,600 mg per dose.")), 1)


class ArdisikCumleVeSaatlikDoz(unittest.TestCase):
    def _s(self, satir):
        g = EN if satir.isascii() else TR
        return denetle("# 1 Test\n\n" + g + "\n\n" + satir + "\n\n" + g + "\n")

    def eng(self, satir, kural_adi="doz_aritmetigi"):
        return kural(self._s(satir), kural_adi, "ENGEL")

    def hepsi(self, satir, kural_adi="doz_aritmetigi"):
        return kural(self._s(satir), kural_adi)

    def test_oran_onceki_cumlede(self):
        ust = "Önerilen doz 5 mg/kg'dır. 70 kg hastada toplam doz {} mg olarak hesaplanır ve 100 mL içinde 30 dakikada verilir."
        b = self.eng(ust.format(300))
        self.assertTrue(b)
        self.assertIn("350 mg", b[0]["mesaj"])
        self.assertEqual(self.hepsi(ust.format(350)), [])

    def test_oran_iki_cumle_geride_ve_ipuclari(self):
        self.assertTrue(self.eng("Önerilen doz 5 mg/kg'dır. Bu bir uyarıdır. 70 kg hastada doz 300 mg hesaplanır."))
        self.assertTrue(self.eng("Önerilen doz 5 mg/kg'dır. 70 kg hastada doz 300 mg bulunur."))
        self.assertTrue(self.eng("The dose is 5 mg/kg. For a 70 kg adult it is calculated as 300 mg."))
        self.assertTrue(self.eng("The dose is 5 mg/kg. For a 70 kg adult it comes to 300 mg."))
        self.assertEqual(self.hepsi("The dose is 5 mg/kg. For a 70 kg adult it is calculated as 350 mg."), [])

    def test_oran_cok_geride_ya_da_birden_cok_oran_atlanir(self):
        self.assertEqual(self.hepsi("Önerilen doz 5 mg/kg'dır. Bu bir uyarıdır. Başka. 70 kg hastada doz 300 mg hesaplanır."), [])
        self.assertEqual(self.hepsi("Doz 5 mg/kg'dır; bazı kılavuzlar 10 mg/kg'dır. 70 kg hastada doz 300 mg hesaplanır."), [])

    def test_saatlik_oran(self):
        self.assertTrue(self.eng("Naloxone infusion 0.05 mg/kg/h for a 70 kg adult gives 0.35 mg/h."))
        self.assertEqual(self.hepsi("Naloxone infusion 0.05 mg/kg/h for a 70 kg adult gives 3.5 mg/h."), [])
        self.assertEqual(self.hepsi("Fentanyl 1 mcg/kg IV for a 70 kg adult gives 70 mcg."), [])
        self.assertTrue(self.eng("Naloxone 0.05 mg/kg per hour for a 70 kg adult gives 0.35 mg/hr."))
        self.assertTrue(self.eng("Naloksan 0.05 mg/kg/saat ile 70 kg erişkine 0.35 mg/saat verilir."))
        self.assertEqual(self.hepsi("Naloksan 0.05 mg/kg/saat ile 70 kg erişkine 3,5 mg/saat verilir."), [])
        self.assertEqual(self.hepsi("Fentanil 1 mcg/kg/h, 70 kg erişkinde 0.07 mg/h verilir."), [])      # mcg → mg

    def test_lab_yeni_ipuclari(self):
        for ipucu in ("is written as", "is reported as", "is expressed as", "is recorded as"):
            with self.subTest(ipucu=ipucu):
                self.assertTrue(kural(_lab(f"A glucose of 126 mg/dL {ipucu} 5.4 mmol/L in the chart"), "lab_birim_karisik", "ENGEL"))
                self.assertEqual(kural(_lab(f"A glucose of 126 mg/dL {ipucu} 7.0 mmol/L in the chart"), "lab_birim_karisik"), [])
        for ipucu in ("olarak yazılır", "olarak ifade edilir", "olarak kaydedilir"):
            with self.subTest(ipucu=ipucu):
                self.assertTrue(kural(_lab(f"Glukoz 126 mg/dL değeri 5,4 mmol/L {ipucu}.", "tr"), "lab_birim_karisik", "ENGEL"))
                self.assertEqual(kural(_lab(f"Glukoz 126 mg/dL değeri 7,0 mmol/L {ipucu}.", "tr"), "lab_birim_karisik"), [])
        self.assertTrue(kural(_lab("Glukoz 126 mg/dL, kayıtlarda 5,4 mmol/L olarak ifade edilir.", "tr"), "lab_birim_karisik", "ENGEL"))


class YasYanindaAd(unittest.TestCase):
    def _s(self, satir):
        g = EN if satir.isascii() else TR
        return denetle("# 1 Test\n\n" + g + "\n\n" + satir + "\n\n" + g + "\n")

    def test_tr_ad_soyad_engel(self):
        s = self._s("Acil servise başvuran 58 yaşındaki Ayşe Yıldırım, 40 dakikadır süren göğüs ağrısı tarifliyor.")
        self.assertTrue(kural(s, "hasta_kimlik", "ENGEL"))

    def test_en_iki_yon_engel(self):
        for satir in ("A 58-year-old woman, Jane Doe, presented to the emergency department with chest pain.",
                      "Jane Doe, a 58-year-old, presented to the emergency department with chest pain.",
                      "The 58-year-old Jane Doe presented to the clinic."):
            with self.subTest(satir=satir):
                self.assertTrue(kural(self._s(satir), "hasta_kimlik", "ENGEL"))

    def test_sozluk_sozcukleri_ad_degil(self):
        for satir in ("Acil servise 58 yaşındaki kadın hasta başvurdu.", "Acil servise 58 yaşında Erkek Hasta başvurdu.",
                      "A 58-year-old Male Patient presented to the ward.", "A 58-year-old Woman presented to the ward.",
                      "Servis kaydına göre 30 yaşında Ankara Üniversitesi'ne başvuran hasta.",
                      "Atatürk 1881'de doğdu ve 57 yaşında vefat etti."):
            with self.subTest(satir=satir):
                self.assertEqual(kural(self._s(satir), "hasta_kimlik"), [])

    def test_biyografi_baglaminda_uyari(self):
        b = kural(self._s("Tarih dersinde 58 yaşındaki Mustafa Kemal Atatürk anlatıldı."), "hasta_kimlik")
        self.assertTrue(b and all(x["duzey"] == "UYARI" for x in b))

    def test_kurmaca_isareti_uyari(self):
        b = kural(self._s("Kurmaca vaka: 58 yaşındaki Ayşe Yıldırım acile geldi."), "hasta_kimlik")
        self.assertTrue(b and all(x["duzey"] == "UYARI" for x in b))

    def test_etiketli_ad_cift_bulgu_vermez(self):
        s = self._s("Hasta Ayşe Yıldırım, 58 yaşında, kliniğe geldi.")
        self.assertEqual(len(kural(s, "hasta_kimlik", "ENGEL")), 1)

    def test_ad_etiketi_ad_degil(self):
        self.assertEqual(kural(self._s("Konuşmada kendini tanıt: Adım Mesut, 31 yaşındayım."), "hasta_kimlik"), [])

    def test_etiketli_placeholder_degismedi(self):
        self.assertEqual(kural(self._s("Name: John Smith"), "hasta_kimlik"), [])


class KodSozcukleri(unittest.TestCase):
    def test_duzyazida_kod_sozcugu_puan_vermez(self):
        p = o.profiller()
        nesir = "# Pazarlama\n\nMüşteri select edilir ve return oranı hesaplanır. Return policy and select customers matter.\n"
        self.assertEqual(o.alan_puanlari(nesir, p)[0].get("bilgisayar", 0), 0)

    def test_kod_blogunda_kod_sozcugu_sayilir(self):
        p = o.profiller()
        kod = "# Python\n\nFonksiyon tanımı aşağıda.\n\n```python\ndef topla(a, b):\n    return a + b\n```\n"
        self.assertGreater(o.alan_puanlari(kod, p)[0].get("bilgisayar", 0), 0)


if __name__ == "__main__":
    unittest.main()
