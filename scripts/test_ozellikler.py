#!/usr/bin/env python3
"""Sınaç v2 özellik testleri: karar, kapsam, konum, susturma, --duzelt güvenliği, karma belge, gerçek PDF ölçümü."""
import contextlib
import io
import os
import shutil
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
BURA = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BURA)
sys.path.insert(0, os.path.join(BURA, "tests"))
import ogretim_denetim as o  # noqa: E402
import pdf_uret  # noqa: E402

POPPLER = all(shutil.which(x) for x in ("pdftotext", "pdfimages", "pdftoppm"))
TAM = """---
alan: tip
denetim: 2026-11-22 kişi
hedef: farmakoloji ara sınavı
---
# 1 Hipertansiyon
Tanı ofis ölçümüyle konur. Örnek vaka: 60 yaşında hasta, 160/100 mmHg. Çözüm: yaşam tarzı ve ilaç.
# 2 Sorular
Soru 1: Gebede hangi ilaç kontrendikedir? Cevap: ACE inhibitörü.
"""


def calistir(*arg):
    cikti = io.StringIO()
    with contextlib.redirect_stdout(cikti), contextlib.redirect_stderr(io.StringIO()):
        kod = o.main(list(arg))
    return kod, cikti.getvalue()


class Karar(unittest.TestCase):
    def test_uc_durum(self):
        self.assertEqual(o.denetle(TAM)["karar"], "tanımlı kapsamda uygun")
        self.assertEqual(o.denetle(TAM.replace("hedef: farmakoloji ara sınavı\n", ""))["karar"], "karar için denetim eksik")
        self.assertEqual(o.denetle(TAM + "\nİlaç 5,0 mg.\n")["karar"], "yayına engel var")

    def test_olculmeyen_boyut_puanlanmaz(self):
        s = o.denetle(TAM.replace("hedef: farmakoloji ara sınavı\n", ""))
        self.assertIsNone(s["puan"]["Hedefle uyum"])
        self.assertIsNone(s["puan"]["Verimlilik"])
        self.assertEqual(s["azami"], 2 * s["olculen_boyut"])

    def test_karma_belge_ek_alan(self):
        metin = ("# 1 Türev\n" + "Teorem ispat fonksiyon türev integral limit denklem matris polinom logaritma. " * 6 +
                 "\n# 2 Vaka\n" + "Hasta tanı tedavi klinik ilaç doz semptom sendrom komplikasyon prognoz. " * 6)
        s = o.denetle(metin)
        self.assertIn("tip", {s["alan"], *s["ek_alanlar"]})
        self.assertIn("matematik", {s["alan"], *s["ek_alanlar"]})

    def test_risk_taramasi_alandan_bagimsiz(self):
        s = o.denetle("# 1 Tarih\nOsmanlı padişahı ilaç olarak 5,0 mg afyon aldı. Ferman antlaşma yüzyıl savaş.\n")
        self.assertTrue(s["risk_taramasi"] or "tip_doz_yazimi" in s["kontroller"])
        self.assertEqual(s["karar"], "yayına engel var")


class KonumVeSusturma(unittest.TestCase):
    def test_satir_numarasi(self):
        s = o.denetle(TAM + "\nİlaç 5,0 mg.\n")
        engel = [b for b in s["bulgular"] if b["duzey"] == "ENGEL"][0]
        self.assertEqual(engel["satir"], TAM.count("\n") + 2)
        self.assertEqual(engel["kural"], "tip_doz_yazimi")

    def test_gerekceli_susturma(self):
        m = TAM + "\nİlaç 5,0 mg. <!-- sinac: yoksay — öğretici yanlış örnek, altında doğrusu var -->\n"
        s = o.denetle(m)
        self.assertNotEqual(s["karar"], "yayına engel var")
        self.assertEqual(len(s["susturulan"]), 1)

    def test_gerekcesiz_susturma_engeli_kaldirmaz(self):
        s = o.denetle(TAM + "\nİlaç 5,0 mg. <!-- sinac: yoksay -->\n")
        self.assertEqual(s["karar"], "yayına engel var")
        s = o.denetle("<!-- sinac: yoksay tip_doz_yazimi -->\n" + TAM + "\nİlaç 5,0 mg.\n")
        self.assertEqual(s["karar"], "yayına engel var")

    def test_belge_duzeyi_susturma(self):
        s = o.denetle("<!-- sinac: yoksay tip_doz_yazimi — ISMP örneklerini anlatan sayfa -->\n" + TAM + "\nİlaç 5,0 mg.\n")
        self.assertNotEqual(s["karar"], "yayına engel var")

    def test_kimlik_ornegi_maskelenir(self):
        s = o.denetle(TAM + "\nHasta: Ayşe Yılmaz.\n")
        b = [x for x in s["bulgular"] if x["kural"] == "hasta_kimlik"][0]
        self.assertNotIn("Ayşe", b["ornek"] + b["mesaj"])


class YanlisAlarm(unittest.TestCase):
    def test_dil_alistirmasindaki_ornek_eposta_kisisel_veri_degil(self):
        m = "# 1 Form\nÖğrenci formu doldurur: E-mail: pierre@exemple.fr, téléphone 0532 123 45 67.\n"
        self.assertNotIn("hasta_kimlik", {b["kural"] for b in o.denetle(m, alan="dil", dil="fr")["bulgular"]})

    def test_vakada_iletisim_bilgisi_uyarir(self):
        m = TAM + "\nVaka: hasta 0532 123 45 67 numaradan aradı.\n"
        self.assertIn("Vakada telefon numarası", " ".join(b["mesaj"] for b in o.denetle(m)["bulgular"]))

    def test_python_3_9_uyumlu_sozdizimi(self):
        import ast
        kaynak = open(os.path.join(BURA, "ogretim_denetim.py"), encoding="utf-8").read()
        ast.parse(kaynak, feature_version=(3, 9))


class Duzelt(unittest.TestCase):
    def test_kod_formul_frontmatter_korunur(self):
        metin = "---\nbaslik: vαr\n---\nJе suis. `x = 'α'`\n$\\alpha = 1$\n```python\nx='α'\n```\nvαriable\n"
        yeni, _ = o.duzelt(metin, "genel")
        self.assertIn("baslik: vαr", yeni)
        self.assertIn("`x = 'α'`", yeni)
        self.assertIn("x='α'", yeni)
        self.assertIn("Je suis", yeni)
        self.assertIn("variable", yeni)

    def test_fen_alaninda_yunan_harfine_dokunmaz(self):
        yeni, _ = o.duzelt("Kaldırma kuvveti ρgV, açı α = 30°, vαriable.\n", "fizik")
        self.assertIn("ρgV", yeni)
        self.assertIn("α = 30", yeni)

    def test_yedek_alinir(self):
        d = tempfile.mkdtemp()
        try:
            yol = os.path.join(d, "not.md")
            with open(yol, "w", encoding="utf-8") as f:
                f.write("# 1\nJе suis.\n")
            calistir(yol, "--duzelt")
            self.assertTrue(os.path.exists(yol + ".bak"))
            with open(yol + ".bak", encoding="utf-8") as f:
                self.assertIn("Jе", f.read())
        finally:
            shutil.rmtree(d)


class CikisKodu(unittest.TestCase):
    def test_kodlar(self):
        d = tempfile.mkdtemp()
        try:
            def yaz(ad, m):
                p = os.path.join(d, ad)
                with open(p, "w", encoding="utf-8") as f:
                    f.write(m)
                return p
            self.assertEqual(calistir(yaz("a.md", TAM))[0], 0)
            self.assertEqual(calistir(yaz("b.md", TAM + "\nİlaç 5,0 mg.\n"))[0], 1)
            self.assertEqual(calistir(yaz("c.md", TAM.replace("hedef: farmakoloji ara sınavı\n", "")))[0], 3)
            self.assertEqual(calistir(yaz("d.md", TAM), "--yil", "20x6")[0], 2)
        finally:
            shutil.rmtree(d)


class FableBulgulari(unittest.TestCase):
    """Fable 5.2 incelemesi (22.11.2026): --duzelt, kodlama, susturma, maskeleme, performans."""
    def gecici(self, ad, icerik, ikili=False):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d)
        yol = os.path.join(d, ad)
        with open(yol, "wb") as f:
            f.write(icerik if ikili else icerik.encode("utf-8"))
        return yol

    def test_duzelt_kod_blogundaki_css_ye_dokunmaz(self):
        yeni, _ = o.duzelt("# CSS\n\n```css\nbody { font-size: 8pt; }\n```\n", "bilgisayar")
        self.assertIn("font-size: 8pt", yeni)
        for korunan in ("~~~\nJе\n~~~\n", "\n    Jе kod\n", "\\[ Jе \\]", "<pre>Jе</pre>"):
            yeni, _ = o.duzelt("Metin.\n\n" + korunan, "genel")
            self.assertIn("Jе", yeni, korunan)

    def test_duzelt_yedegi_ezmez_ve_crlf_korur(self):
        yol = self.gecici("a.md", "# 1\r\nJе suis.\r\n")
        calistir(yol, "--duzelt")
        with open(yol, "w", encoding="utf-8", newline="") as f:
            f.write("# 1\r\nJе suis encore.\r\n")
        calistir(yol, "--duzelt")
        self.assertTrue(os.path.exists(yol + ".bak") and os.path.exists(yol + ".bak1"))
        with open(yol, "rb") as f:
            self.assertIn(b"\r\n", f.read())
        with open(yol + ".bak", "rb") as f:
            self.assertIn("Jе suis.".encode("utf-8"), f.read())

    def test_kodlama_ve_bos_dosya(self):
        yol = self.gecici("c.md", "# Not\n\nMorfin 5 mg. Yaş 58.\n".encode("cp1254"), ikili=True)
        kod, cikti = calistir(yol)
        self.assertIn(kod, (0, 1, 3))
        self.assertIn("Windows-1254", cikti)
        self.assertEqual(calistir(self.gecici("bos.md", "  \n"))[0], 2)

    def test_belge_duzeyi_engel_susturma_uygun_demez(self):
        m = "<!-- sinac: yoksay tip_doz_yazimi — ISMP yanlış yazım örneklerini anlatan sayfa -->\n" + TAM + "\nİlaç 5,0 mg.\n"
        s = o.denetle(m)
        self.assertEqual(s["karar"], "karar için denetim eksik")
        self.assertTrue(s["belge_duzeyi_engel_susturuldu"])

    def test_kisa_gerekce_engeli_susturmaz(self):
        s = o.denetle(TAM + "\nİlaç 5,0 mg. <!-- sinac: yoksay — x -->\n")
        self.assertEqual(s["karar"], "yayına engel var")

    def test_ad_hicbir_alanda_acik_kalmaz(self):
        import json
        s = o.denetle("# Not\n\nHasta: Emine Korkmaz, parasetamol 500 mg gerektiğinde alınır.\n", alan="tip")
        dokum = json.dumps(s, ensure_ascii=False)
        self.assertNotIn("Emine", dokum)
        self.assertNotIn("Korkmaz", dokum)

    def test_olumsuz_elle_deger_kabul_edilmez(self):
        s = o.denetle(TAM.replace("denetim: 2026-11-22 kişi", "denetim: hayır, yapılmadı"))
        self.assertEqual(s["karar"], "karar için denetim eksik")
        self.assertIn("Doğruluk", s["elle_reddedilen"])

    def test_bilinmeyen_tur_uyarir(self):
        s = o.denetle("---\ntur: ders notu\n---\n# 1\nMetin.\n")
        self.assertEqual(s["tur"], "ders-notu")
        s = o.denetle("---\ntur: dersnotu\n---\n# 1\nMetin.\n")
        self.assertIn("tur", {b["kural"] for b in s["bulgular"]})

    def test_duzelt_crlf_kod_ve_satir_ici_kod_korunur(self):
        m = "# Not\r\n\r\n```css\r\nbody { font-size: 8pt; }\r\n/* p\u043ert */\r\n```\r\n"
        yeni, _ = o.duzelt(m, "bilgisayar")
        self.assertIn("8pt", yeni)
        self.assertIn("p\u043ert", yeni)
        yeni, _ = o.duzelt("# Not\n\n\u00dccret 10$ \u043elup komut `echo $p\u043ert` \u015feklindedir.\n")
        self.assertIn(" olup ", yeni)
        self.assertIn("`echo $p\u043ert`", yeni)

    def test_ayni_ornek_ikinci_paragrafta_kendi_satirini_alir(self):
        s = o.denetle("# Not\n\n\u00c7ocukta parasetamol 15 mg/kg <!-- sinac: yoksay \u2014 pedagojik kar\u015f\u0131 \u00f6rnek -->\n\n"
                      "Tedavi: \u00e7ocukta parasetamol 15 mg/kg verilir.\n", None, "tip")
        self.assertIn(5, [b["satir"] for b in s["bulgular"] if b["kural"] == "cocuk_azami_doz"])

    def test_susturulan_engel_tam_puan_getirmez(self):
        s = o.denetle("---\ndenetim: 2026-11-22 Claude\nhedef: A1\n---\n# Not\n\n"
                      "Morfin 5,0 mg <!-- sinac: yoksay \u2014 \u00f6\u011fretici yanl\u0131\u015f \u00f6rnek sat\u0131r\u0131 -->\n", None, "tip")
        self.assertLessEqual(s["puan"]["Doğruluk"], 1)

    def test_duzelt_uzun_cit_cift_tirnak_ve_equation_korunur(self):
        for m in ("# Not\n\n````python\n```\nd\u0435ger = 4\n```\n````\n\nMetin d\u0435ger.\n",
                  "# Not\n\nKod ``d\u0435ger = `x` `` ve d\u0435ger.\n",
                  "# Not\n\n\\begin{equation}\nd\u0435ger = 1\n\\end{equation}\n\nd\u0435ger burada.\n"):
            yeni, _ = o.duzelt(m)
            self.assertEqual(yeni.count("\u0435"), 1, m[:30])

    def test_redos_ve_karesel_girdiler_hizli(self):
        import time
        for m in ("<!-- sinac: yoksay " + " " * 3000 + "x", "<!-- a " * 20000, "![a](" * 20000, "\\frac{" * 20000,
                  "." + "5" * 100000 + " mg", "5" * 100000 + " mg/kg", "1." * 50000 + "5 mg", "5" + " ve 5" * 20000 + " mg"):
            t = time.time()
            o.denetle("# Not\n\n" + m, None, "tip")
            self.assertLess(time.time() - t, 10, m[:20])


@unittest.skipUnless(POPPLER, "poppler (pdftotext, pdfimages, pdftoppm) yok")
class GercekPdf(unittest.TestCase):
    def olc(self, sayfalar, font="Helvetica"):
        d = tempfile.mkdtemp()
        try:
            yol = os.path.join(d, "t.pdf")
            with open(yol, "wb") as f:
                f.write(pdf_uret.pdf(sayfalar, font))
            return o.pdf_olc(__import__("pathlib").Path(yol))
        finally:
            shutil.rmtree(d)

    def test_kalibrasyon_orani(self):
        for font, oran in (("Helvetica", 0.925), ("Times-Roman", 0.900), ("Courier", 0.786)):
            olcum = self.olc([pdf_uret.satirlar(10)], font)
            self.assertAlmostEqual(olcum["kutu"] / 10, oran, places=2)

    def test_11_pt_hic_uyari_vermez(self):
        for font in ("Helvetica", "Times-Roman"):
            s = o.denetle(TAM, self.olc([pdf_uret.satirlar(11)], font))
            self.assertNotIn("pdf_yazi", {b["kural"] for b in s["bulgular"]})

    def test_8_5_pt_hata_degil_uyari(self):
        s = o.denetle(TAM, self.olc([pdf_uret.satirlar(8.5)]))
        duzey = {b["duzey"] for b in s["bulgular"] if b["kural"] == "pdf_yazi"}
        self.assertEqual(duzey, {"UYARI"})

    def test_6_pt_hata(self):
        s = o.denetle(TAM, self.olc([pdf_uret.satirlar(5)]))
        self.assertIn("HATA", {b["duzey"] for b in s["bulgular"] if b["kural"] == "pdf_yazi"})

    def test_vektor_cizimli_sayfa_bos_degil(self):
        olcum = self.olc([pdf_uret.satirlar(11), ("CIZIM",), pdf_uret.satirlar(11)])
        s = o.denetle(TAM, olcum)
        self.assertNotIn("HATA", {b["duzey"] for b in s["bulgular"] if b["kural"] == "pdf_bos_sayfa"})

    def test_gercek_bos_sayfa_hata(self):
        olcum = self.olc([pdf_uret.satirlar(11), [], pdf_uret.satirlar(11)])
        s = o.denetle(TAM, olcum)
        self.assertIn("HATA", {b["duzey"] for b in s["bulgular"] if b["kural"] == "pdf_bos_sayfa"})

    def test_pdf_icerigi_de_denetlenir(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d)
        with open(os.path.join(d, "t.pdf"), "wb") as f:
            f.write(pdf_uret.pdf([[(11, "Morfin 5,0 mg IV. Hasta adi: Ayse Yilmaz", 700)]]))
        with open(os.path.join(d, "t.md"), "w", encoding="utf-8") as f:
            f.write(TAM)
        kod, cikti = calistir(os.path.join(d, "t.md"))
        self.assertEqual(kod, 1)
        self.assertIn("PDF'te (md'de yok)", cikti)

    def test_pdf_engeli_md_uyarisiyla_kaybolmaz(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d)
        with open(os.path.join(d, "t.pdf"), "wb") as f:
            f.write(pdf_uret.pdf([[(11, "Doz: 7,0 mg IV.", 700)]]))
        with open(os.path.join(d, "t.md"), "w", encoding="utf-8") as f:
            f.write("---\ndenetim: 2026-11-22 Claude\nhedef: A1\n---\n# Not\n\nYanl\u0131\u015f yaz\u0131m: Doz: 7,0 mg IV.\n")
        kod, cikti = calistir(os.path.join(d, "t.md"))
        self.assertEqual(kod, 1)

    def test_metinsiz_pdf_olculmedi(self):
        olcum = self.olc([("CIZIM",)])
        self.assertFalse(olcum["metin_var"])
        s = o.denetle(TAM, olcum)
        self.assertNotIn("pdf_bos_sayfa", {b["kural"] for b in s["bulgular"]})


if __name__ == "__main__":
    unittest.main(verbosity=1)
