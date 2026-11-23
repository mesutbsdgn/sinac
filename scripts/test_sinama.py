#!/usr/bin/env python3
"""Sınaç 2.1.1: 23 Kasım 2026 sınama raporunun 15 bulgusu (S1–S15) için testler. python3 scripts/test_sinama.py

Her kural grubunda: olumlu (bulunmalı), olumsuz (bulunmamalı) ve rapordaki en küçük girdilerden bağımsız yazılmış
varyantlar (tr/en; farklı sözcük sırası, satır kırılması, tablo, liste). Beklenti ENGEL/HATA/UYARI ya da None (bulgu yok)."""
import contextlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

sys.dont_write_bytecode = True
BURA = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BURA)
sys.path.insert(0, os.path.join(BURA, "tests"))
import ogretim_denetim as o  # noqa: E402

FM = "---\nhedef: Örnek hedef cümlesi\ndenetim: 2026-11-21 Dr. Ada Deneme (uzman)\n---\n\n"
EN = "The patient should be given the dose and the nurse will check it before the drug is used in the ward."
TR = "Bu ilaç hasta için ve gerektiğinde verilir; ancak doz çok yüksek olmamalı ve kayıt tutulmalıdır."


def sonuc(govde, baslik="# Not", alan=None):
    return o.denetle(FM + baslik + "\n\n" + govde + "\n", None, alan, None, 2026)


def agir(s, kural=None):
    return [b for b in s["bulgular"] if b["duzey"] in ("ENGEL", "HATA") and (kural is None or b["kural"] == kural)]


def duzey(s, kural):
    """kuralın en ağır düzeyi ('ENGEL'/'HATA'/'UYARI') ya da None."""
    d = [b["duzey"] for b in s["bulgular"] if b["kural"] == kural]
    for x in ("ENGEL", "HATA", "UYARI"):
        if x in d:
            return x
    return None


class Temel(unittest.TestCase):
    def dz(self, govde, beklenen, kural, baslik="# Not", alan=None, dolgu=None):
        """govde için kuralın en ağır düzeyi beklenene eşit olmalı. dolgu: dil için ek cümle ('en' ya da 'tr')."""
        if dolgu:
            govde = (EN if dolgu == "en" else TR) + "\n\n" + govde + "\n\n" + (EN if dolgu == "en" else TR)
        s = sonuc(govde, baslik, alan)
        self.assertEqual(duzey(s, kural), beklenen, msg=f"{govde!r} → {[(b['duzey'], b['kural'], b['mesaj']) for b in s['bulgular']]}")
        return s

    def ag(self, govde, beklenen, kural, baslik="# Not", alan=None, dolgu=None):
        """Yalnız ENGEL/HATA var mı (UYARI sayılmaz): beklenen 'ENGEL' ya da None."""
        if dolgu:
            govde = (EN if dolgu == "en" else TR) + "\n\n" + govde + "\n\n" + (EN if dolgu == "en" else TR)
        s = sonuc(govde, baslik, alan)
        var = "ENGEL" if agir(s, kural) else None
        self.assertEqual(var, beklenen, msg=f"{govde!r} → {[(b['duzey'], b['kural'], b['mesaj']) for b in s['bulgular']]}")
        return s

    def vaka_listesi(self, vakalar, kural, **kw):
        for govde, beklenen in vakalar:
            with self.subTest(govde=govde[:70]):
                (self.ag if kw.pop("agir", False) else self.dz)(govde, beklenen, kural, **kw)

    def agir_listesi(self, vakalar, kural, **kw):
        for govde, beklenen in vakalar:
            with self.subTest(govde=govde[:70]):
                self.ag(govde, beklenen, kural, **kw)


# ── S1–S2, Ek: doz hesabı ──
class S1UniteDozlari(Temel):
    def test_olumlu_ve_olumsuz(self):
        K = "doz_aritmetigi"
        self.vaka_listesi([
            # tablo, oran önce, devam hesabı (÷ 50, → 24 mL/saat) ilk eşitliği engellemez
            ("| Kilo | İlaç | Hesap | Hız |\n|---|---|---|---|\n| 70 kg | Heparin | 18 ünite/kg/saat × 70 kg = 1.300 ünite/saat ÷ 50 | 26 mL/saat |", "ENGEL"),
            ("| Kilo | İlaç | Hesap | Hız |\n|---|---|---|---|\n| 70 kg | Heparin | 18 ünite/kg/saat × 70 kg = 1.260 ünite/saat ÷ 50 | 25 mL/saat |", None),
            ("Hasta 80 kg. Heparin 18 ünite/kg/saat ile saatlik doz 1.620 ünite/saat olarak hesaplanır.", "ENGEL"),
            ("Hasta 80 kg. Heparin 18 ünite/kg/saat ile saatlik doz 1.440 ünite/saat olarak hesaplanır.", None),
            ("İnsülin 0,1 ünite/kg/saat × 70 kg = 9 ünite/saat.", "ENGEL"),
            ("İnsülin 0,1 ünite/kg/saat × 70 kg = 7 ünite/saat.", None),
            ("70 kg × 0,1 U/kg/saat = 8 U/saat", "ENGEL"),
            ("70 kg × 0,1 U/kg/saat = 7 U/saat", None),
            ("Hasta 60 kg; 50 İÜ/kg doz = 3.500 İÜ.", "ENGEL"),
            ("Hasta 60 kg; 50 İÜ/kg doz = 3.000 İÜ.", None),
            # mg ile de kaçıyordu
            ("Heparin 18 mg/kg/saat × 80 kg = 1200 mg/saat.", "ENGEL"),
            ("Heparin 18 mg/kg/saat × 80 kg = 1440 mg/saat.", None),
        ], K)

    def test_en(self):
        K = "doz_aritmetigi"
        self.vaka_listesi([
            ("The patient weighs 80 kg. The infusion starts at 18 units/kg/h, so the hourly dose is 1,620 units/h.", "ENGEL"),
            ("The patient weighs 80 kg. The infusion starts at 18 units/kg/h, so the hourly dose is 1,440 units/h.", None),
            ("Regular insulin 0.1 units/kg/hour by infusion; for a 70 kg adult that is 9 units/hour.", "ENGEL"),
            ("Regular insulin 0.1 units/kg/hour by infusion; for a 70 kg adult that is 7 units/hour.", None),
            ("A 60 kg patient on oxytocin 0.5 IU/kg/h receives 45 IU/h.", "ENGEL"),
            ("A 60 kg patient on oxytocin 0.5 IU/kg/h receives 30 IU/h.", None),
            ("Heparin bolus 80 units/kg for a 75 kg patient: 8,000 units.", "ENGEL"),
            ("Heparin bolus 80 units/kg for a 75 kg patient: 6,000 units.", None),
            ("- Weight 90 kg\n- Rate 12 units/kg/h → 1,300 units/h", "ENGEL"),
            ("- Weight 90 kg\n- Rate 12 units/kg/h → 1,080 units/h", None),
            # seyreltme ve derişim sonuç değildir
            ("Weight 80 kg; heparin 18 units/kg/h = 1,440 units/h; 25,000 units in 250 mL (100 units/mL).", None),
        ], K, dolgu="en")

    def test_tablo_basliklari_birimli(self):
        K = "doz_aritmetigi"
        bas = "| Weight (kg) | Rate (units/kg/h) | Dose (units/h) |\n|---|---|---|\n"
        self.dz(bas + "| 80 | 18 | 1,440 |\n| 70 | 18 | 1,400 |", "ENGEL", K, dolgu="en")
        self.dz(bas + "| 80 | 18 | 1,440 |\n| 70 | 18 | 1,260 |", None, K, dolgu="en")
        bas = "| Kilo | Hız (ünite/kg/saat) | Doz (ünite/saat) |\n|---|---|---|\n"
        self.dz(bas + "| 80 | 18 | 1.440 |\n| 70 | 18 | 1.400 |", "ENGEL", K, dolgu="tr")


class S2DuzyaziDoz(Temel):
    K = "doz_aritmetigi"

    def test_tr(self):
        self.vaka_listesi([
            ("Çocuk 22 kg tartıldı. Adrenalin 0,01 mg/kg ile 0,3 mg IM verildi.", "ENGEL"),
            ("Çocuk 22 kg tartıldı. Adrenalin 0,01 mg/kg ile 0,22 mg IM verildi.", None),
            ("Hasta 18 kg. Amoksisilin 25 mg/kg/doz ile 500 mg verilir.", "ENGEL"),
            ("Hasta 18 kg. Amoksisilin 25 mg/kg/doz ile 450 mg verilir.", None),
            ("Parasetamol 15 mg/kg/doz; 20 kg'lık çocuğa tek doz 350 mg uygulanır.", "ENGEL"),
            ("Parasetamol 15 mg/kg/doz; 20 kg'lık çocuğa tek doz 300 mg uygulanır.", None),
            ("Çocuk 22 kg\ntartıldı; adrenalin 0,01 mg/kg ile\n0,3 mg IM verildi.", "ENGEL"),
            ("- 12 kg bebek: ibuprofen 10 mg/kg/doz = 150 mg", "ENGEL"),
            ("- 12 kg bebek: ibuprofen 10 mg/kg/doz = 120 mg", None),
            ("15 kg çocuk; 100 mg/kg/gün; günlük toplam 1.200 mg", "ENGEL"),
            ("15 kg çocuk; 100 mg/kg/gün; günlük toplam 1.500 mg", None),
            ("Çocuk 20 kg, 40 mg/kg/gün günde iki kez; doz başına 500 mg", "ENGEL"),
            ("Çocuk 20 kg, 40 mg/kg/gün günde iki kez; doz başına 400 mg", None),
            ("10 kg'lık köpek için 2 mg/kg dozun toplamı 25 mg olarak hesaplanır.", "ENGEL"),
            ("10 kg'lık köpek için 2 mg/kg dozun toplamı 20 mg olarak hesaplanır.", None),
            ("Olgu 3 yaşında, 18 kg. Ateş 38,6 °C. Amoksisilin 25 mg/kg/doz\nolarak planlandı ve günde iki kez 600 mg verilmesi yazıldı.", "ENGEL"),
        ], self.K)

    def test_en(self):
        self.vaka_listesi([
            ("A 24 kg child is prescribed ibuprofen 10 mg/kg every 8 hours; each dose is therefore 420 mg.", "ENGEL"),
            ("A 24 kg child is prescribed ibuprofen 10 mg/kg every 8 hours; each dose is therefore 240 mg.", None),
            ("A 4 kg cat receives meloxicam 5 mg/kg; the total dose is 30 mg.", "ENGEL"),
            ("A 4 kg cat receives meloxicam 5 mg/kg; the total dose is 20 mg.", None),
            ("The child weighs 30 kg. Ceftriaxone 50 mg/kg is therefore 2,000 mg.", "ENGEL"),
            ("The child weighs 30 kg. Ceftriaxone 50 mg/kg is therefore 1,500 mg.", None),
            ("Ampicillin 100 mg/kg/day divided q6h: for a 15 kg child that is 1,200 mg/day, or 300 mg per dose.", "ENGEL"),
            ("Ampicillin 100 mg/kg/day divided q6h: for a 15 kg child that is 1,500 mg/day, or 375 mg per dose.", None),
            ("Gentamicin 7 mg/kg/day; for a 60 kg patient that is 450 mg/day.", "ENGEL"),
            ("Gentamicin 7 mg/kg/day; for a 60 kg patient that is 420 mg/day.", None),
            ("A 70 kg adult at 15 mg/kg/dose → 1,200 mg per dose.", "ENGEL"),
            ("| 25 kg | Cefazolin | 25 mg/kg/dose | 700 mg |", "ENGEL"),
            ("| 25 kg | Cefazolin | 25 mg/kg/dose | 625 mg |", None),
            ("The 20 kg child gets amoxicillin\n25 mg/kg/dose; the\ndose calculated is 600 mg.", "ENGEL"),
        ], self.K, dolgu="en")

    def test_gunluk_toplam_ve_doz_basina(self):
        # günlük toplam W×R; doz başına W×R/n (n verilmişse yalnız o)
        self.dz("15 kg child, 100 mg/kg/day divided q6h: 1,500 mg/day or 375 mg per dose", None, self.K, dolgu="en")
        self.dz("15 kg child, 100 mg/kg/day divided q6h: 1,500 mg/day or 300 mg per dose", "ENGEL", self.K, dolgu="en")
        self.dz("15 kg çocuk, 100 mg/kg/gün günde üç kez: günlük 1.500 mg, doz başına 500 mg", None, self.K, dolgu="tr")
        self.dz("15 kg çocuk, 100 mg/kg/gün günde üç kez: günlük 1.500 mg, doz başına 375 mg", "ENGEL", self.K, dolgu="tr")

    def test_sonuc_sayilmayanlar(self):
        self.vaka_listesi([
            ("20 kg child, 15 mg/kg/dose: give 300 mg per dose; do not exceed 500 mg.", None),
            ("20 kg child, 15 mg/kg/dose: give 300 mg; maximum 900 mg/day.", None),
            ("20 kg child, 15 mg/kg/dose: give 300 mg (one 300 mg tablet; tablets of 500 mg are not suitable).", None),
            ("20 kg child, 15 mg/kg/dose: give 300 mg; suspension 250 mg/5 mL is 6 mL.", None),
            ("20 kg çocuk, 15 mg/kg/doz: 300 mg verilir; en fazla 450 mg verilebilir.", None),
            ("20 kg çocuk, 15 mg/kg/doz: 300 mg verilir; 500 mg'lık tablet kullanılmaz.", None),
            # belirsiz: iki kilo ya da iki oran ya da aralık sessiz kalır (mevcut test_f3 beklentisi)
            ("A 10 kg dog and a 20 kg dog at 5 mg/kg/dose: give 80 mg.", None),
            ("A 10 kg dog needs 10-15 mg/kg/dose, give 80 mg.", None),
        ], self.K, dolgu="en")

    def test_tolerans_ve_yuvarlama(self):
        # yaklaşık 225 mg için 220 ENGEL değil; %3 içinde
        self.dz("15 kg child, 15 mg/kg/dose: about 220 mg per dose.", None, self.K, dolgu="en")
        self.dz("15 kg child, 15 mg/kg/dose: about 300 mg per dose.", "ENGEL", self.K, dolgu="en")
        # zaman ve doz sözü yoksa %20'ye kadar sapma yalnız UYARI
        self.dz("20 kg çocuğa 15 mg/kg ile 250 mg verilir.", "UYARI", self.K, dolgu="tr")

    def test_iki_ilac(self):
        # iki ilaç adı: sonuç başka ilacın dozuysa eşleşmez
        self.dz("Hasta 20 kg: ibuprofen 10 mg/kg/doz = 200 mg; parasetamol 500 mg verilir.", None, self.K, dolgu="tr")


class EkBirimDonusumu(Temel):
    def test_mcg_mg_g(self):
        K = "doz_aritmetigi"
        self.vaka_listesi([
            ("Hasta 70 kg, hedef 5 mcg/kg/dk dopamin.\n\n1. Dakikalık doz: 70 × 5 = 350 mcg/dk.\n2. Miligrama çevir: 350 mcg/dk = 3,5 mg/dk.", "ENGEL"),
            ("2. Miligrama çevir: 350 mcg/dk = 0,35 mg/dk.", None),
            ("500 mg = 5 g", "ENGEL"),
            ("500 mg = 0,5 g", None),
            ("2 g = 200 mg", "ENGEL"),
            ("2 g = 2000 mg", None),
            ("0.5 mg/kg = 5 mcg/kg", "ENGEL"),
            ("0.5 mg/kg = 500 mcg/kg", None),
            ("1 mg/saat = 1000 mcg/saat", None),
            ("1 mg/saat = 100 mcg/saat", "ENGEL"),
            # payda farklıysa başka bir dönüşüm: sessiz
            ("60 mg/saat = 1 mg/dk", None),
        ], K)


# ── S3, S7: lab dönüşümü ──
class S3LabDonusumu(Temel):
    K = "lab_birim_karisik"

    def test_tr_duzyazi(self):
        self.agir_listesi([
            ("- Toplam kolesterol 240 mg/dL, 8,2 mmol/L'ye karşılık gelir; bu değer yüksek risk kategorisindedir.", "ENGEL"),
            ("- Toplam kolesterol 240 mg/dL, 6,2 mmol/L'ye karşılık gelir; bu değer yüksek risk kategorisindedir.", None),
            ("Kan glukozu 360 mg/dL ölçülmüşse yaklaşık 22 mmol/L eder.", "ENGEL"),
            ("Kan glukozu 360 mg/dL ölçülmüşse yaklaşık 20 mmol/L eder.", None),
            ("Kreatinin 1,2 mg/dL'lik değer 160 µmol/L'dir.", "ENGEL"),
            ("Kreatinin 1,2 mg/dL'lik değer 106 µmol/L'dir.", None),
            ("Trigliserit düzeyi 150 mg/dL, yani 17 mmol/L olarak bulundu.", "ENGEL"),
            ("Trigliserit düzeyi 150 mg/dL, yani 1,7 mmol/L olarak bulundu.", None),
            # zaman/olay ayracı: iki ayrı ölçüm, dönüşüm değil
            ("Glikoz 300 mg/dL idi; tedaviden sonra 10 mmol/L'ye düştü.", None),
            ("Açlık glukozu 126 mg/dL, hedef değer 5 mmol/L.", None),
        ], self.K, dolgu="tr")

    def test_en_duzyazi(self):
        self.agir_listesi([
            ("Serum creatinine is reported in both units. A result of 1.2 mg/dL therefore corresponds to about 1060 µmol/L.", "ENGEL"),
            ("Serum creatinine is reported in both units. A result of 1.2 mg/dL therefore corresponds to about 106 µmol/L.", None),
            ("LDL cholesterol of 130 mg/dL is about 5.4 mmol/L.", "ENGEL"),
            ("LDL cholesterol of 130 mg/dL is about 3.4 mmol/L.", None),
            ("Triglycerides were 150 mg/dL, i.e. 17 mmol/L.", "ENGEL"),
            ("Triglycerides were 150 mg/dL, i.e. 1.7 mmol/L.", None),
            ("Glucose 250 mg/dL on admission and 6 mmol/L after treatment.", None),
            ("Glucose fell from 250 mg/dL to 9 mmol/L over six hours.", None),
            ("The 5.6 mmol/L fasting glucose equals 100 mg/dL; the target is below 7 mmol/L.", None),
            ("Blood sugar of 180 mg/dL, which is 14 mmol/L, needs review.", "ENGEL"),
            ("- Glucose\n  180 mg/dL\n  = 10 mmol/L", None),
            ("Glucose 180 mg/dL\ncorresponds to 14 mmol/L.", "ENGEL"),
        ], self.K, dolgu="en")

    def test_tablo(self):
        K = self.K
        self.ag("| Değer | SI | Yorum |\n|---|---|---|\n| Kreatinin 0,9 mg/dL | 62 µmol/L | düşük-normal sınırda |", "ENGEL", K, dolgu="tr")
        self.ag("| Değer | SI | Yorum |\n|---|---|---|\n| Kreatinin 0,9 mg/dL | 80 µmol/L | normal |", None, K, dolgu="tr")
        self.ag("| Glucose (mg/dL) | Glucose (mmol/L) |\n|---|---|\n| 180 mg/dL | 10 mmol/L |\n| 360 mg/dL | 22 mmol/L |", "ENGEL", K, dolgu="en")
        self.ag("| Glucose (mg/dL) | Glucose (mmol/L) |\n|---|---|\n| 180 | 10 |\n| 360 | 20 |", None, K, dolgu="en")
        self.ag("| Glucose (mg/dL) | Glucose (mmol/L) |\n|---|---|\n| 180 | 10 |\n| 360 | 22 |", "ENGEL", K, dolgu="en")
        self.ag("| Analyte | mg/dL | mmol/L |\n|---|---|---|\n| Glucose | 180 | 10 |\n| Cholesterol | 200 | 15 |", "ENGEL", K, dolgu="en")
        self.ag("| Analyte | mg/dL | mmol/L |\n|---|---|---|\n| Glucose | 180 | 10 |\n| Cholesterol | 200 | 5.2 |", None, K, dolgu="en")
        self.ag("## Glucose\n\n| mg/dL | mmol/L |\n|---|---|\n| 180 | 12 |", "ENGEL", K, dolgu="en")
        # iki farklı analit aynı satırda: eşleşmez
        self.ag("| Analyte | mg/dL | mmol/L |\n|---|---|---|\n| Glucose / sodium | 180 | 139 |", None, K, dolgu="en")

    def test_kolesterol_ve_trigliserit_katsayilari(self):
        self.ag("Total cholesterol 240 mg/dL = 6.2 mmol/L.", None, self.K, dolgu="en")
        self.ag("Total cholesterol 240 mg/dL = 62 mmol/L.", "ENGEL", self.K, dolgu="en")
        self.ag("Triglyceride 177 mg/dL = 2.0 mmol/L.", None, self.K, dolgu="en")
        self.ag("Triglyceride 177 mg/dL = 20 mmol/L.", "ENGEL", self.K, dolgu="en")
        self.ag("Trigliserit 177 mg/dL, 20 mmol/L'ye karşılık gelir.", "ENGEL", self.K, dolgu="tr")


class S7FormulDonusumDegil(Temel):
    K = "lab_birim_karisik"

    def test_formuller(self):
        self.agir_listesi([
            ("- Corrected sodium = measured Na + 1.6 × (glucose − 100) ÷ 100. For Na 132 and glucose 540 mg/dL: 132 + 1.6 × 4.4 = 139 mmol/L.", None),
            ("Düzeltilmiş sodyum: Na 130 ve glukoz 450 mg/dL için 130 + 1,6 × 3,5 = 135,6 mmol/L bulunur.", None),
            ("Glucose 540 mg/dL, sodium 139 mmol/L.", None),
            ("Sodium 139 mmol/L; glucose 540 mg/dL.", None),
            ("Anion gap = Na − (Cl + HCO3) = 140 − 100 − 24 = 16 mmol/L; glucose 100 mg/dL.", None),
            ("Osmolalite = 2 × Na + glukoz (mg/dL) ÷ 18 = 290 mmol/L; glukoz 180 mg/dL.", None),
            ("Glucose 180 mg/dL, potassium 5.0 mmol/L.", None),
            # gerçek dönüşüm formülü hâlâ denetlenir
            ("Glucose 180 mg/dL ÷ 18 = 12 mmol/L.", "ENGEL"),
            ("Glucose 180 mg/dL ÷ 18 = 10 mmol/L.", None),
        ], self.K, dolgu="en")


# ── S4, S6: hasta kimliği ──
class S4HastaKimligi(Temel):
    K = "hasta_kimlik"

    def test_ad_yastan_once(self):
        self.agir_listesi([
            ("Marcus Whitfield, a 52-year-old man, presented with chest pain.", "ENGEL"),
            ("Ayşe Yıldırım, 58 yaşında, göğüs ağrısıyla acile başvurdu.", "ENGEL"),
            ("Case 2: Marcus Whitfield, a 52-year-old man with cirrhosis, was referred for malnutrition.", "ENGEL"),
            ("1996 doğumlu Ayşe Yıldırım acile başvurdu.", "ENGEL"),
            ("A 58-year-old woman, Jane Doe, arrived with wheeze and hives.", "ENGEL"),
            ("58 yaşındaki Mehmet Karaca göğüs ağrısı şikâyetiyle getirildi.", "ENGEL"),
        ], self.K, dolgu="en")

    def test_etiketler(self):
        self.agir_listesi([
            ("Danışan: Gizem Tunçdemir (d. 14.03.1996), TÜ Psikoloji Birimi protokol no 2026/4471", "ENGEL"),
            ("Client: Maria Lopez (b. 1996-03-14), referred for anxiety; MRN 2026/4471", "ENGEL"),
            ("Olgu: Selim Arıkan, şikâyet: uykusuzluk. Muayene sonrası tedavi edildi.", "ENGEL"),
            ("Vaka 3: Derya Kılıç başvurdu ve tedavi edildi.", "ENGEL"),
            ("Hasta: Ahmet Demir (b. 1996-03-14)", "ENGEL"),
            ("Case 4: Priya Raman was admitted with fever.", "ENGEL"),
        ], self.K, dolgu="en")
        # bağlam yok (sağlık belgesi değil): başlık söz öbeği ya da iş belgesi ad sayılmaz
        self.ag("# Canine Respiratory Case: Dosing Sheet\n\nThe offer was signed on Monday.", None, self.K)
        self.ag("Client: Acme Holdings signed the contract on Monday after a long discussion with the board.", None, self.K)

    def test_dogum_ve_protokol(self):
        self.agir_listesi([
            ("Hasta: Ayşe Kaya, doğum tarihi 14.03.1996.", "ENGEL"),
            ("Hasta adı: Ayşe Kaya; DOB 14/03/1996.", "ENGEL"),
            ("Vaka sunumu: Gizem Tunçdemir protokol no 2026/4471", "ENGEL"),
            ("Hasta Ayşe Kaya, protokol: 2026/4471 ile yatırıldı.", "ENGEL"),
            ("Konferans bildirisi no 2026/4471 sayfa 3.", None),
        ], self.K, dolgu="tr")

    def test_dogum_tarihi_ve_protokol_ayri_bulgu(self):
        s = sonuc("Danışan: Gizem Tunçdemir (d. 14.03.1996), TÜ Psikoloji Birimi protokol no 2026/4471", alan="psikoloji")
        mesajlar = [b["mesaj"] for b in agir(s, "hasta_kimlik")]
        self.assertTrue(any("doğum tarihi" in m for m in mesajlar), msg=mesajlar)
        self.assertTrue(any("protokol" in m for m in mesajlar), msg=mesajlar)
        self.assertTrue(any("hasta adı" in m for m in mesajlar), msg=mesajlar)
        for govde in ("Hasta: Ali Veli (b. 1996-03-14)", "Hasta Ali Veli, DOB 14/03/1996.", "Hasta Ali Veli (doğ. 14.03.1996)"):
            with self.subTest(govde=govde):
                self.assertTrue(any("doğum tarihi" in b["mesaj"] for b in agir(sonuc(govde, alan="tip"), "hasta_kimlik")))

    def test_vaka_baglami_basliktan(self):
        for baslik in ("Worked example", "Case", "Scenario", "Vignette", "Örnek olgu", "Senaryo"):
            with self.subTest(baslik=baslik):
                self.ag(f"## {baslik}\nA 58-year-old woman, Jane Doe, arrived with wheeze and hives.", "ENGEL", self.K, dolgu="en")
        self.ag("## Worked example\nJane Doe, a 58-year-old woman, was the first person we interviewed.", "ENGEL", self.K, dolgu="en")


class S6TarihiKisi(Temel):
    K = "hasta_kimlik"

    def test_tarihi_kisiler_engel_degil(self):
        self.agir_listesi([
            ("In 1854 Florence Nightingale, a 34-year-old nurse from a wealthy family, led a team of nurses to Scutari.", None),
            ("The 58-year-old Louis XVIII, back on the throne, relied on Talleyrand at the congress of 1814.", None),
            ("1919'da Paris'te Binet-Simon laboratuvarında çalışan 23 yaşındaki Jean Piaget, çocukların yanıtlarını inceledi.", None),
            ("Napoleon Bonaparte, 35 yaşında imparator olduğunda ülkeyi yeniden kurdu.", None),
            ("Marie Curie, a 36-year-old researcher, published her thesis in 1903.", None),
            ("Isaac Newton, a 23-year-old student, developed calculus in 1666.", None),
            ("Elizabeth I, a 25-year-old queen, took the throne in 1558.", None),
        ], self.K, dolgu="en")

    def test_hemsirelik_belgesinde_yil_ve_klinik_eylem_yoksa(self):
        self.ag("In 1854 Florence Nightingale, a 34-year-old nurse, led a team of nurses to Scutari.", None, self.K, alan="hemsirelik", dolgu="en")
        self.ag("Florence Nightingale, a 34-year-old nurse, led a team to Scutari in 1854.", None, self.K, alan="hemsirelik", dolgu="en")

    def test_ayni_paragrafta_klinik_kelime_tarihi_kisiyi_hasta_yapmaz(self):
        self.ag("A man was admitted to the ward. The 58-year-old Louis XVIII, back on the throne, relied on him entirely.", None, self.K, dolgu="en")

    def test_gercek_hasta_hala_engel(self):
        # eski yıl tek başına tarihî kişi yapmaz: aynı cümlede klinik eylem varsa hasta kalır
        self.ag("In 2008 Marcus Whitfield, a 52-year-old man, presented with chest pain.", "ENGEL", self.K, dolgu="en")
        self.ag("In 1999 Marcus Whitfield, a 52-year-old man, was admitted to the ward.", "ENGEL", self.K, dolgu="en")
        self.agir_listesi([
            ("In 2024 Marcus Whitfield, a 52-year-old man, presented with chest pain.", "ENGEL"),
            ("Marcus Whitfield, a 52-year-old nurse, was admitted with chest pain in 2023.", "ENGEL"),
            ("1996 doğumlu Ayşe Yıldırım acile başvurdu.", "ENGEL"),
        ], self.K, dolgu="en")


# ── S5: öğretici yanlış örnek ──
class S5OgreticiYanlisOrnek(Temel):
    K = "tip_doz_yazimi"
    DIGER = "Give heparin 5000 units subcutaneously every 12 hours.\n\n"          # belgede başka bir ilaç dozu: tarama açık

    def test_ogretici_engel_degil(self):
        self.agir_listesi([
            (self.DIGER + "- Never leave a naked decimal: write 0.75 mg, never .75 mg, so a missed point cannot turn it into 75 mg.", None),
            (self.DIGER + "A bare .25 mg invites a tenfold error; always write 0.25 mg.", None),
            (self.DIGER + "Do not add a trailing zero: 5 mg, not 5.0 mg.", None),
            (self.DIGER + "Sık yapılan hata: dozu 5,0 mg biçiminde yazmak. Virgül silik çıkarsa doz 50 mg okunur.", None),
            (self.DIGER + "Common error: writing the dose as 5.0 mg instead of 5 mg.", None),
            (self.DIGER + "Asla ,5 mg yazma; her zaman 0,5 mg yaz.", None),
            (self.DIGER + "5,0 mg yerine 5 mg yazın; aksi halde 50 mg okunabilir.", None),
            (self.DIGER + "Common mistake: 10.0 mg. Correct: 10 mg.", None),
            (self.DIGER + "| .5 mg | ✗ unsafe |\n| 0.5 mg | ✓ safe |", None),
            (self.DIGER + "| Yazım | Değerlendirme |\n|---|---|\n| ,5 mg | ✗ yanlış; 5 mg okunabilir |\n| 0,5 mg | ✓ doğru |", None),
            (self.DIGER + "| Wrong | Right |\n|---|---|\n| 5.0 mg | 5 mg |\n| .25 mg | 0.25 mg |", None),
            (self.DIGER + "| Doz | Not |\n|---|---|\n| 10.0 mg | avoid: trailing zero |", None),
            (self.DIGER + "| ❌ 10.0 mg | ✓ 10 mg |", None),
        ], self.K, dolgu="en")

    def test_gercek_hata_engel_kalir(self):
        self.agir_listesi([
            ("Haloperidol 5,0 mg IM verilir.", "ENGEL"),
            ("Hastaya 5,0 mg verilmemeli, 10 mg verilir.", "ENGEL"),
            ("Doz: **5,0 mg** (yanlış hesaplanmış olabilir)", "ENGEL"),
            ("Give haloperidol 5.0 mg IM now.", "ENGEL"),
            ("Never skip the dose; haloperidol 5.0 mg IM.", "ENGEL"),
            ("Always check allergies; give haloperidol 5.0 mg. The next patient gets 5 mg.", "ENGEL"),
            ("| Dose | Status |\n|---|---|\n| 5.0 mg | stable |", "ENGEL"),
            ("Give .5 mg of haloperidol; avoid sedation.", "ENGEL"),
        ], self.K, dolgu="en")

    def test_belgedeki_baska_doz_karari_bozmaz(self):
        # S5a tek başına geçiyordu, başka bir doz olunca ENGEL oluyordu: gerekçe, doz taramasının yalnız ilaç/doz izi varken açılmasıydı
        tek = "- Never leave a naked decimal: write 0.75 mg, never .75 mg, so a missed point cannot turn it into 75 mg."
        self.ag(tek, None, self.K)
        self.ag("Give heparin 5000 units.\n\n" + tek, None, self.K)
        self.ag(tek + "\n\nMorphine 5 mg IV every 4 hours.", None, self.K)


# ── S8, S9: alan tespiti ──
def alan_sonuc(metin):
    s = o.denetle(metin, None, None, None, 2026)
    return s["alan"], s["tespit"].get("grup")


class S8S9Alan(unittest.TestCase):
    def test_lab_sozcukleri_tip_notunu_beslenmeye_cekmez(self):
        doc = FM + """# Lipid paneli ve glukoz yorumu

Açlık kan glukozu 126 mg/dL, total kolesterol 240 mg/dL, trigliserit 180 mg/dL olarak ölçüldü. Lipid paneli ve glukoz sonuçları
hasta dosyasında SI birimine çevrilir: glukoz mmol/L, kolesterol mmol/L, trigliserit mmol/L. Tanı için klinik bulgu ve öykü gerekir.

Fasting glucose, cholesterol and triglyceride values are interpreted together with the patient's history and diagnosis.
"""
        alan, grup = alan_sonuc(doc)
        self.assertNotEqual(alan, "beslenme")
        self.assertEqual(grup, "saglik")

    def test_beslenme_diyet_sozcuguyle_kazanir(self):
        doc = FM + """# Diyet ve porsiyon planı

Günlük kalori ihtiyacı hesaplanır; protein, karbonhidrat ve lif içeren porsiyonlar diyet listesine yazılır. Besin öğesi içeriği,
vitamin ve mineral alımı, kolesterol ve glukoz içeren gıdalar ile enerji dengesi diyetisyen tarafından izlenir. Kilo yönetimi için
porsiyon kontrolü ve besin değeri etiketi okunur.
"""
        self.assertEqual(alan_sonuc(doc)[0], "beslenme")

    def test_doz_yazimi_dersi_saglik_grubuna_duser(self):
        doc = FM + """# Güvenli doz yazımı

İlaç hatalarının önemli bir bölümü yanlış okunan dozdan kaynaklanır. Sık yapılan hata: dozu 5,0 mg biçiminde yazmak.
Morfin 5 mg, haloperidol 10 mg, parasetamol 500 mg ve heparin 5000 ünite örneklerinde ondalıktan önce sıfır yazılır.
"""
        self.assertEqual(alan_sonuc(doc)[1], "saglik")
        doc_en = FM + """# Writing doses safely

Trailing zeros are dangerous: write 5 mg, never 5.0 mg. Morphine 5 mg, haloperidol 10 mg and paracetamol 500 mg are examples.
A leading zero is required: 0.5 mg, never .5 mg.
"""
        self.assertEqual(alan_sonuc(doc_en)[1], "saglik")

    def test_fransizca_kelime_listesi_ingilizce_aciklamayla_dil_olur(self):
        doc = FM + """# French market words

| French | English | Example |
|---|---|---|
| le pain | bread | Je voudrais du pain pour le petit déjeuner. |
| le marché | market | Nous allons au marché le samedi matin avec nos amis. |
| le prix | price | Le prix des légumes est très bas aujourd'hui sur la place. |
| le coût | cost | Le coût de la vie augmente chaque année dans cette ville. |

The market price and the cost of bread are useful words. Buy the bread at the market at a low price.
"""
        self.assertEqual(alan_sonuc(doc)[0], "dil")

    def test_ingilizce_iktisat_notu_dil_olmaz(self):
        doc = FM + """# Market price and cost

The market price depends on supply and demand. Marginal cost and the price elasticity of demand determine the market equilibrium.
A monopoly sets the price above marginal cost, while a competitive market price equals marginal cost.
"""
        self.assertEqual(alan_sonuc(doc)[0], "iktisat")


# ── S10: ??? yer tutucusu ──
class S10YerTutucu(Temel):
    K = "yer_tutucu"

    def test_hucre_ve_satir_sonu(self):
        self.vaka_listesi([
            ("| Structure | Extra space |\n|---|---|\n| Hash map | O(n) |\n| Merge sort | ??? |", "HATA"),
            ("| Structure | Extra space |\n|---|---|\n| Merge sort | ???? | notes |", "HATA"),
            ("Merge sort extra space: ???", "HATA"),
            ("Merge sort extra space = ???", "HATA"),
            ("- Quick sort worst case: ???", "HATA"),
            ("| Structure | Extra space |\n|---|---|\n| Merge sort | O(n) |", None),
            ("Neden??? diye sordu ve çıktı.", None),
            ("Is this right??? Probably yes.", None),
            ("| Q | A |\n|---|---|\n| Why??? | Because |", None),
        ], self.K, dolgu="en")


# ── S12: karışık alfabe, her satır ──
class S12Alfabe(Temel):
    def test_her_satir_bildirilir(self):
        satirlar = "\n\n".join(f"Satır {i}: le pаin numara {i}." for i in range(1, 8))      # а = Kiril
        s = sonuc(satirlar)
        b = [x for x in s["bulgular"] if x["kural"] == "alfabe"]
        self.assertEqual(len(b), 7)
        self.assertEqual(len({x["satir"] for x in b}), 7)
        self.assertTrue(all(x["duzey"] == "HATA" for x in b))

    def test_en_cok_on_satir_ve_artan(self):
        satirlar = "\n\n".join(f"Satır {i}: le pаin numara {i}." for i in range(1, 15))
        b = [x for x in sonuc(satirlar)["bulgular"] if x["kural"] == "alfabe"]
        self.assertEqual(len(b), 10)
        self.assertIn("+4 satır daha", b[-1]["mesaj"])

    def test_temiz_belgede_yok(self):
        self.assertEqual([x for x in sonuc("Temiz metin: le pain, Ankara.")["bulgular"] if x["kural"] == "alfabe"], [])

    def test_yunan(self):
        b = [x for x in sonuc("Satır bir: dоz yok.\n\nSatır iki: аyrı kelime.")["bulgular"] if x["kural"] == "alfabe"]
        self.assertEqual(len(b), 2)


# ── S11: hız (doğrusal olmayan yerler) ──
def sure(metin, taban="Ayrı satır."):
    t0 = time.perf_counter()
    o.denetle(FM + "# Hız\n\n" + metin, None, None, None, 2026)
    return time.perf_counter() - t0


class S11Hiz(unittest.TestCase):
    SINIR = 2.0

    def test_uzun_tek_satir_tekrarlari(self):
        for ad, metin in [
            ("yinelenen doz", "5 mg/kg 10 kg " * 8000),
            ("uzun sözcük + lab", "a" * 40000 + " mg/dL = 99 mmol/L\n"),
            ("yalnız $", "$" * 40000),
            ("boşluk yığını", " " * 20000 + "x\n"),
            ("çizgi ve boşluk", "- " * 8000),
            ("yaş-ad yığını", "58 yaşındaki " * 3000),
            ("rakam-virgül", "1,000," * 10000),
        ]:
            with self.subTest(ad=ad):
                self.assertLess(sure(metin), self.SINIR, msg=ad)

    def test_dogrusal_buyume(self):
        # iki katı girdi ≈ iki katı süre: 4 katı geçmemeli (karesel olsaydı ≥ 4)
        for sablon in ("5 mg/kg 10 kg ", "a" * 50 + " ", "58 yaşındaki ", "x" * 10 + "$ "):
            kucuk, buyuk = sure(sablon * 1500), sure(sablon * 6000)
            with self.subTest(sablon=sablon[:14]):
                self.assertLess(buyuk, max(4.0 * 4 * kucuk, 1.0), msg=f"{kucuk:.2f}s → {buyuk:.2f}s")

    def test_genis_tablo_sinirlanir_ve_not_duser(self):
        satir = "|" + "|".join(["kg", "mg/kg", "mg"] * 1500) + "|"
        ayr = "|" + "|".join(["---"] * 4500) + "|"
        s = o.denetle(FM + "# T\n\n" + "\n".join([satir, ayr] + [satir.replace("kg", "20") for _ in range(8)]) + "\n", None, None, None, 2026)
        self.assertTrue([b for b in s["bulgular"] if b["kural"] == "tablo_genis"])
        # sütun sınırı: sütun-değer satırı sayısı genişlikle değil sınırla büyür (süre doğrusal kalsın)
        satirlar = o.hazirla_satirlar("\n".join([satir, ayr] + [satir.replace("kg", "20") for _ in range(8)]) + "\n")
        self.assertLessEqual(len(o.tablolar(satirlar)), 8 * (o.TABLO_SUTUN_TAVAN + 1) + 8)
        self.assertLessEqual(max(len(tb["hucreler"][0]) for tb in o.tablo_ayristir(satirlar)), o.TABLO_SUTUN_TAVAN)

    def test_cok_satir_ve_kisa_not(self):
        self.assertLess(sure("Hasta 20 kg; 15 mg/kg ile 300 mg verilir.\n" * 4000), 4.0)
        self.assertLess(sure("Kısa not: doz 5 mg verilir.\n"), 1.0)


# ── S13, S14: PDF ──
POPPLER = all(shutil.which(x) for x in ("pdftotext", "pdfimages", "pdftoppm", "pdffonts"))


@unittest.skipUnless(POPPLER, "poppler yok")
class S13S14Pdf(unittest.TestCase):
    def setUp(self):
        import pdf_uret
        self.pdf_uret = pdf_uret
        self.dizin = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dizin, ignore_errors=True)

    def hazirla(self, ad, punto, font="Helvetica", baytlar=None):
        md = os.path.join(self.dizin, ad + ".md")
        open(md, "w", encoding="utf-8").write(FM + "# Not\n\nBir iki üç dört beş altı yedi sekiz dokuz on.\n")
        pdf = os.path.join(self.dizin, ad + ".pdf")
        veri = baytlar if baytlar is not None else self.pdf_uret.pdf([self.pdf_uret.satirlar(punto)], font=font)
        open(pdf, "wb").write(veri)
        return md

    def calistir(self, md):
        cikti = io.StringIO()
        with contextlib.redirect_stdout(cikti), contextlib.redirect_stderr(io.StringIO()):
            kod = o.main([md, "--json"])
        import json
        return kod, json.loads(cikti.getvalue())

    def yazi(self, s):
        return [b for b in s["bulgular"] if b["kural"] == "pdf_yazi"]

    def test_6_pt_standart_yazi_tipleri_hata(self):
        for font in ("Helvetica", "Times-Roman", "Courier"):
            with self.subTest(font=font):
                kod, s = self.calistir(self.hazirla("p6" + font[:3], 6, font))
                b = self.yazi(s)
                self.assertEqual([x["duzey"] for x in b], ["HATA"], msg=f"{font}: {s['kutu_pt']} {[x['mesaj'] for x in b]}")
                self.assertEqual(s["karar"], "yayına engel var")

    def test_aralik_daraldi(self):
        # Helvetica 6 pt: eski genel aralık 6,0–7,06 pt idi; yazı tipi bilindiği için en çok ≈ 6,1 pt
        kod, s = self.calistir(self.hazirla("p6b", 6))
        m = self.yazi(s)[0]["mesaj"]
        import re
        a, b = map(float, re.search(r"tahmini ([\d.]+)–([\d.]+) pt", m).groups())
        self.assertLess(b - a, 0.5, msg=m)
        self.assertLess(b, 7.0)

    def test_esikler_degismedi(self):
        _, s8 = self.calistir(self.hazirla("p8", 8))
        self.assertEqual([x["duzey"] for x in self.yazi(s8)], ["UYARI"])          # 8 pt: < 9 uyarı, ≥ 7 hata değil
        _, s11 = self.calistir(self.hazirla("p11", 11))
        self.assertEqual(self.yazi(s11), [])
        _, s7 = self.calistir(self.hazirla("p7", 7))
        self.assertEqual([x["duzey"] for x in self.yazi(s7)], ["UYARI"])          # 7,0 pt tam eşik: hata değil

    def test_bozuk_pdf_uygun_olamaz(self):
        md = self.hazirla("bozuk", 11, baytlar=b"%PDF-1.4\nbozuk")
        kod, s = self.calistir(md)
        self.assertEqual(s["karar"], "karar için denetim eksik")
        self.assertEqual(kod, 3)
        b = [x for x in s["bulgular"] if x["kural"] == "pdf_okunamadi"]
        self.assertEqual([x["duzey"] for x in b], ["UYARI"])
        self.assertTrue(s["pdf_olculemedi"])

    def test_pdf_yoksa_degismez(self):
        md = os.path.join(self.dizin, "yalniz.md")
        open(md, "w", encoding="utf-8").write(FM + "# Not\n\nBir iki üç.\n")
        _, s = self.calistir(md)
        self.assertFalse(s["pdf_olculemedi"])
        self.assertEqual([x for x in s["bulgular"] if x["kural"] == "pdf_okunamadi"], [])

    def test_iyi_pdf_bulgusuz(self):
        _, s = self.calistir(self.hazirla("iyi", 11))
        self.assertEqual([x for x in s["bulgular"] if x["kural"] in ("pdf_yazi", "pdf_okunamadi")], [])
        self.assertFalse(s["pdf_olculemedi"])


# ── S15: --duzelt ──
class S15Duzelt(unittest.TestCase):
    def setUp(self):
        self.dizin = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dizin, ignore_errors=True)

    def test_baglanti_epostasi_yol_degismez(self):
        govde = ("# Doz\n\nSözcük: dоz ve le pаin düzeltilir.\n"
                 "URL: https://example.com/dоz_notu ve www.exаmple.org/yol\n"
                 "E-posta: аdmin@exаmple.com kullanılır.\n"
                 "Yol: /Users/ali/Notlar/dоz.md ve ~/Belgeler/dоz.txt ve ./dоz/sonuc.md\n"
                 "Bağlantı: [dоz kılavuzu](https://example.com/kılаvuz) ve [yol](../dоz/not.md).\n")
        md = os.path.join(self.dizin, "n.md")
        open(md, "w", encoding="utf-8").write(FM + govde)
        cikti = io.StringIO()
        with contextlib.redirect_stdout(cikti), contextlib.redirect_stderr(io.StringIO()):
            o.main([md, "--duzelt"])
        yeni = open(md, encoding="utf-8").read()
        for korunan in ("https://example.com/dоz_notu", "www.exаmple.org/yol", "аdmin@exаmple.com", "/Users/ali/Notlar/dоz.md",
                        "~/Belgeler/dоz.txt", "./dоz/sonuc.md", "https://example.com/kılаvuz", "../dоz/not.md"):
            self.assertIn(korunan, yeni, msg=korunan)               # Kiril harfi hâlâ orada (dokunulmadı)
        self.assertIn("Sözcük: doz ve le pain düzeltilir.", yeni)   # düz metin düzeltildi
        self.assertIn("[doz kılavuzu](", yeni)                      # bağlantı METNİ düzeltildi
        self.assertIn("elle bak", cikti.getvalue())                 # bağlantıda Kiril: bulgu olarak bildirildi

    def test_bulgu_olarak_bildirilir(self):
        s = o.denetle(FM + "# N\n\nAdres https://example.com/dоz ve [kılavuz](https://example.com/kılаvuz) bağlantısı.\n", None, None, None, 2026)
        b = [x for x in s["bulgular"] if x["kural"] == "alfabe"]
        self.assertTrue(b)
        self.assertTrue(all(x["duzey"] == "UYARI" for x in b))
        self.assertIn("elle bak", b[0]["mesaj"])

    def test_temiz_baglanti_bulgu_vermez(self):
        s = o.denetle(FM + "# N\n\nAdres https://example.com/doz ve admin@example.com ve /usr/bin/doz.\n", None, None, None, 2026)
        self.assertEqual([x for x in s["bulgular"] if x["kural"] == "alfabe"], [])

    def test_ikinci_calistirma_yedegi_ezmez(self):
        md = os.path.join(self.dizin, "n.md")
        open(md, "w", encoding="utf-8").write(FM + "# N\n\ndоz yazıldı.\n")
        for _ in range(2):
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                o.main([md, "--duzelt"])
        self.assertIn("dоz", open(md + ".bak", encoding="utf-8").read())


# ── İkinci tur: çapraz eşleme, bağımsız ???, kilo önceki maddede ──
class T2LabBireBir(Temel):
    K = "lab_birim_karisik"

    def test_tr_en_eslemeler(self):
        self.agir_listesi([
            ("Hedef glukoz aralığı 126 mg/dL (7,0 mmol/L) ile 162 mg/dL (9,0 mmol/L) arasındadır.", None),
            ("Hedef glukoz aralığı 126 mg/dL (7,0 mmol/L) ile 162 mg/dL (19,0 mmol/L) arasındadır.", "ENGEL"),
            ("Glukoz hedefi 90–180 mg/dL (5,0–10,0 mmol/L) olarak alınır.", None),
            ("Glukoz hedefi 90–180 mg/dL (5,0–12,0 mmol/L) olarak alınır.", "ENGEL"),
            ("Glukoz düzeyleri 90 mg/dL (5,0 mmol/L), 126 mg/dL (7,0 mmol/L) ve 180 mg/dL (10,0 mmol/L) olarak ölçüldü.", None),
            ("Glukoz düzeyleri 90 mg/dL (5,0 mmol/L), 126 mg/dL (7,0 mmol/L) ve 216 mg/dL (21,6 mmol/L) olarak ölçüldü.", "ENGEL"),
            ("Kan glukozu 126 mg/dL (7,0 mmol/L); ikinci ölçümde 216 mg/dL (21,6 mmol/L) bulundu.", "ENGEL"),
        ], self.K, dolgu="tr")
        self.agir_listesi([
            ("Target glucose range is 126 mg/dL (7.0 mmol/L) to 162 mg/dL (9.0 mmol/L).", None),
            ("Target glucose range is 90–180 mg/dL (5.0–10.0 mmol/L).", None),
            ("Glucose readings: 90 mg/dL (5.0 mmol/L), 126 mg/dL (7.0 mmol/L), 162 mg/dL (9.0 mmol/L).", None),
            ("Glucose readings: 90 mg/dL (5.0 mmol/L), 126 mg/dL (7.0 mmol/L), 216 mg/dL (2.16 mmol/L).", "ENGEL"),
        ], self.K, dolgu="en")

    def test_tablo_hucreleri(self):
        bas = "| Analyte | Target | Alert |\n|---|---|---|\n"
        self.ag(bas + "| Glucose | 90–180 mg/dL (5.0–10.0 mmol/L) | < 54 mg/dL (3.0 mmol/L) or ketonuria |", None, self.K, dolgu="en")
        self.ag(bas + "| Glucose | 90–180 mg/dL (5.0–10.0 mmol/L) | < 54 mg/dL (30 mmol/L) or ketonuria |", "ENGEL", self.K, dolgu="en")
        self.ag(bas + "| Glucose | 90–180 mg/dL (5.0–12.0 mmol/L) | < 54 mg/dL (3.0 mmol/L) |", "ENGEL", self.K, dolgu="en")
        self.ag("| Analit | Hedef | Uyarı |\n|---|---|---|\n| Glukoz | 90–180 mg/dL (5,0–10,0 mmol/L) | < 54 mg/dL (3,0 mmol/L) |", None, self.K, dolgu="tr")

    def test_belirsiz_en_cok_uyari(self):
        # değer sayıları tutmuyor (artan değer): ENGEL yok
        s = sonuc("Glukoz 126 mg/dL ölçüldü, sonra 7,0 mmol/L ve 162 mg/dL yazıldı.")
        self.assertFalse(agir(s, self.K))


class T2Yertutucu(Temel):
    def test_bagimsiz_jeton(self):
        self.vaka_listesi([
            ("İkinci fonksiyonun ispatı ??? burada tamamlanacak.", "HATA"),
            ("The proof of the second function ??? will be completed here.", "HATA"),
            ("Sonuç (???) sonra yazılacak.", "HATA"),
            ("Neden??? diye sordu.", None),
            ("Gerçekten mi??? Evet.", None),
            ("Really??? Yes.", None),
        ], "yer_tutucu", dolgu="tr")


class T2KiloOncekiMaddede(Temel):
    K = "doz_aritmetigi"

    def test_listede(self):
        self.agir_listesi([
            ("- Vaka ağırlığı: 30 kg ağırlığında köpek.\n- Lidokain infüzyonu 2 mg/kg/saat üzerinden ayarlandığında saatte 90 mg uygulanır.", "ENGEL"),
            ("- Vaka ağırlığı: 30 kg ağırlığında köpek.\n- Lidokain infüzyonu 2 mg/kg/saat üzerinden ayarlandığında saatte 60 mg uygulanır.", None),
            ("- Weight: a 30 kg dog.\n- Lidocaine CRI at 2 mg/kg/h gives 90 mg/h.", "ENGEL"),
            ("- Weight: a 30 kg dog.\n- Lidocaine CRI at 2 mg/kg/h gives 60 mg/h.", None),
            # iki hasta: her madde kendi önceki maddesinin kilosunu kullanır
            ("- Dog: 30 kg.\n- Lidocaine 2 mg/kg/h gives 60 mg/h.\n- Cat: 4 kg.\n- Ketamine 1 mg/kg/h gives 10 mg/h.", "ENGEL"),
            ("- Dog: 30 kg.\n- Lidocaine 2 mg/kg/h gives 60 mg/h.\n- Cat: 4 kg.\n- Ketamine 1 mg/kg/h gives 4 mg/h.", None),
        ], self.K, dolgu="en")

    def test_baslik_araya_girerse_kullanilmaz(self):
        self.ag("- Dog: 30 kg.\n\n## Başka bölüm\n\n- Lidocaine 2 mg/kg/h gives 90 mg/h.", None, self.K, dolgu="en")


# ── Üçüncü tur ──
class U3DogruSonucVarsa(Temel):
    K = "doz_aritmetigi"

    def test_a_dogru_sonuc_varsa_bulgu_yok(self):
        self.agir_listesi([
            ("Güvenlik sınırı 13 mL/kg/saat; 70 kg için 910 mL/saat. 750 mL/saat bunun altındadır.", None),
            ("Güvenlik sınırı 13 mL/kg/saat; 70 kg için 900 mL/saat. 750 mL/saat bunun altındadır.", None),
            ("The safe limit is 13 mL/kg/h; for 70 kg that is 910 mL/h. The achieved 750 mL/h is below it.", None),
            ("The safe limit is 13 mL/kg/h; for 70 kg that is 990 mL/h. The achieved 750 mL/h is below it.", "ENGEL"),
            ("Ampicillin 100 mg/kg/day for a 15 kg child is 1,500 mg/day; the target was 1,200 mg/day last week.", None),
            ("İlaç 5 mg/kg/doz; 20 kg için doz başına 100 mg verilir. Önceki hastada 80 mg verilmişti.", None),
        ], self.K, dolgu="tr")

    def test_b_sikliga_gore_etiket(self):
        self.agir_listesi([
            ("Metronidazole 15 mg/kg q12h. For the same 10 kg dog the dose is 150 mg per dose, or 300 mg/day.", None),
            ("The patient weighs 70 kg. Enoxaparin 1 mg/kg q12h gives 70 mg per injection, 140 mg/day.", None),
            ("Çocuk 20 kg; günde iki kez 10 mg/kg verilir: doz başına 200 mg, günlük toplam 400 mg.", None),
            ("Metronidazole 15 mg/kg q12h. For the same 10 kg dog the dose is 150 mg per dose, or 150 mg/day.", "ENGEL"),
            ("The patient weighs 70 kg. Enoxaparin 1 mg/kg q12h gives 70 mg per injection, 70 mg/day.", "ENGEL"),
            ("Çocuk 20 kg; günde iki kez 10 mg/kg verilir: doz başına 100 mg.", None),
            ("Gentamicin 7 mg/kg/day for 60 kg: 420 mg/day, or 210 mg per dose q12h.", None),
            ("Gentamicin 7 mg/kg/day for 60 kg: 420 mg/day, or 420 mg per dose q12h.", "ENGEL"),
        ], self.K, dolgu="en")

    def test_c_soru_cumlesi_sonuc_vermez(self):
        self.agir_listesi([
            ("1. 25 kg'lık çocukta parasetamol 15 mg/kg ile doz kaç mg'dır?\n2. 0,25 mg kaç mcg'dır ve reçetede nasıl yazılır?", None),
            ("1. What is the dose of paracetamol 15 mg/kg for a 25 kg child? How many mg?\n2. How many mcg is 0.25 mg?", None),
            ("1. Calculate the dose for a 25 kg child at 15 mg/kg.\n2. Convert 0.25 mg to mcg.", None),
            ("- Hasta 25 kg.\n- Parasetamol 15 mg/kg ile doz 400 mg mıdır?", None),
            ("A 25 kg child, paracetamol 15 mg/kg: is 400 mg correct?", None),
            ("A 25 kg child, paracetamol 15 mg/kg: the dose is 400 mg.", "ENGEL"),
            ("- Hasta 25 kg.\n- Parasetamol 15 mg/kg ile doz kaç mg'dır? Cevap: 375 mg.", None),
            ("- Hasta 25 kg.\n- Parasetamol 15 mg/kg ile doz kaç mg'dır? Cevap: 400 mg.", "ENGEL"),
            ("- Hasta 25 kg.\n- Parasetamol 15 mg/kg/doz ile doz 450 mg verilir.", "ENGEL"),
        ], self.K, dolgu="tr")

    def test_d_birden_cok_etiketsiz_aday_uyari(self):
        for g in ("Hasta 20 kg; 15 mg/kg ile 500 mg ya da 600 mg verilir.", "A 20 kg patient; 15 mg/kg gives 500 mg or 600 mg."):
            s = sonuc(g)
            self.assertFalse(agir(s, self.K), msg=g)
            self.assertTrue([b for b in s["bulgular"] if b["kural"] == self.K and b["duzey"] == "UYARI"], msg=g)


class U3BaslikOranTavan(Temel):
    K = "doz_aritmetigi"
    BAS = "| Weight | Bolus 60 units/kg (max 4,000) | Infusion 12 units/kg/h (max 1,000) |\n|---|---|---|\n"

    def test_tavanli_tablo(self):
        self.agir_listesi([
            (self.BAS + "| 50 kg | 3,000 units | 600 units/h |\n| 70 kg | 4,000 units (capped) | 840 units/h |\n"
             "| 90 kg | 4,000 units (capped) | 1,000 units/h (capped) |", None),
            (self.BAS + "| 50 kg | 3,000 units | 600 units/h |\n| 70 kg | 4,000 units (capped) | 940 units/h |", "ENGEL"),
            (self.BAS + "| 70 kg | 4,200 units | 840 units/h |", "ENGEL"),
            (self.BAS + "| 90 kg | 5,400 units | 1,000 units/h (capped) |", "ENGEL"),
            (self.BAS + "| 90 kg | 4,000 units (capped) | 1,080 units/h |", "ENGEL"),
        ], self.K, dolgu="en")
        self.ag("| Ağırlık | Bolus 60 ünite/kg (en fazla 4.000) | Hız 12 ünite/kg/saat (en fazla 1.000) |\n|---|---|---|\n"
                "| 70 kg | 4.000 ünite (tavan) | 940 ünite/saat |", "ENGEL", self.K, dolgu="tr")
        self.ag("| Ağırlık | Bolus 60 ünite/kg (en fazla 4.000) | Hız 12 ünite/kg/saat (en fazla 1.000) |\n|---|---|---|\n"
                "| 70 kg | 4.000 ünite (tavan) | 840 ünite/saat |", None, self.K, dolgu="tr")

    def test_tavansiz_baslik_orani(self):
        self.ag("| Weight | Dose 5 mg/kg |\n|---|---|\n| 20 kg | 100 mg |\n| 30 kg | 140 mg |", "ENGEL", self.K, dolgu="en")
        self.ag("| Weight | Dose 5 mg/kg |\n|---|---|\n| 20 kg | 100 mg |\n| 30 kg | 150 mg |", None, self.K, dolgu="en")


class U3Kimlik(Temel):
    K = "hasta_kimlik"

    def test_yeni_biçimler(self):
        self.agir_listesi([
            ("Maria Lindqvist, 61, arrives with crushing chest pain radiating to the left arm.", "ENGEL"),
            ("Hasta Kemal Arslan (82 yaşında, 58 kg) üç aydır süren düşme yakınmasıyla başvurdu.", "ENGEL"),
            ("Session 3 note: a 34-year-old teacher, Sarah Whitfield, reported that exposure homework had reduced her avoidance.", "ENGEL"),
            ("Selin Aydın, 45, şiddetli baş ağrısı şikâyetiyle acile başvurdu.", "ENGEL"),
            ("Alfred Wegener, 31, presented the idea of continental drift to the Geological Association on 6 January 1912.", None),
            ("Marie Curie, 36, published her thesis in 1903 while working in Paris.", None),
            ("Napoleon Bonaparte (35 yaşında) imparator olduğunda ülkeyi yeniden kurdu.", None),
            ("Albert Einstein, a 26-year-old clerk, published four papers in 1905.", None),
        ], self.K, dolgu="en")


class U3SondakiSifir(Temel):
    K = "tip_doz_yazimi"

    def test_parantezli_esdeger(self):
        self.agir_listesi([
            ("Levotiroksin 0,050 mg (50 mcg) sabah aç karnına alınır.", "ENGEL"),
            ("Levothyroxine 0.050 mg (50 mcg) once daily on an empty stomach.", "ENGEL"),
            ("Digoxin 0.250 mg (250 mcg) once daily.", "ENGEL"),
            ("0,050 mg yazılmaz, 50 mcg yazılır.", None),
            ("Write 50 mcg, not 0.050 mg (50 mcg).", None),
            ("Levotiroksin 50 mcg sabah aç karnına alınır.", None),
            ("Levothyroxine 0.05 mg (50 mcg) once daily.", None),
        ], self.K, dolgu="en")


# ── Dördüncü tur ──
class V4CumleDuzeyiKilo(Temel):
    K = "doz_aritmetigi"

    def test_h_cumle_duzeyi_eslesme(self):
        S1 = "For a 50 kg adult requiring a 20 mg/kg loading dose of vancomycin, the calculated initial dose is {a} mg IV."
        S2 = " When enterococcal coverage requires ampicillin 200 mg/kg/day divided q6h in a 60 kg adult, each 6-hour infusion equals {b} mg ({c} g/day)."
        self.agir_listesi([
            (S1.format(a="1,000") + S2.format(b="3,000", c="12"), None),
            (S1.format(a="1,200") + S2.format(b="3,000", c="12"), "ENGEL"),
            (S1.format(a="1,000") + S2.format(b="3,000", c="9"), "ENGEL"),
            # günlük toplam doğruysa etiketsiz öteki sayı başka şey sayılır (ilke A)
            (S1.format(a="1,000") + S2.format(b="2,500", c="12"), "ENGEL"),   # 'each 6-hour infusion' doz başına etiketidir
            (S1.format(a="1,000") + S2.format(b="3,000", c="10"), "ENGEL"),
            ("For a 50 kg adult on 20 mg/kg, the dose is 1,000 mg. In a 60 kg adult on 10 mg/kg/dose, the dose is 600 mg.", None),
            ("For a 50 kg adult on 20 mg/kg, the dose is 1,000 mg. In a 60 kg adult on 10 mg/kg/dose, the dose is 500 mg.", "ENGEL"),
            ("50 kg'lık erişkinde 20 mg/kg yükleme dozu 1.000 mg'dır. 60 kg'lık erişkinde 10 mg/kg/doz ile doz 600 mg verilir.", None),
            ("50 kg'lık erişkinde 20 mg/kg yükleme dozu 1.000 mg'dır. 60 kg'lık erişkinde 10 mg/kg/doz ile doz 500 mg verilir.", "ENGEL"),
            # kilo cümlede yoksa önceki cümlenin kilosu (birimde tek kilo)
            ("The patient weighs 70 kg. Give 10 mg/kg/dose, which is 700 mg.", None),
            ("The patient weighs 70 kg. Give 10 mg/kg/dose, which is 500 mg.", "ENGEL"),
            # g ↔ mg
            ("A 60 kg adult on 200 mg/kg/day receives 12 g/day.", None),
            ("A 60 kg adult on 200 mg/kg/day receives 10 g/day.", "ENGEL"),
        ], self.K, dolgu="en")


class V4TabloSiklikEtiket(Temel):
    K = "doz_aritmetigi"
    BAS = "| Drug | Weight | Rate | Calculated dose |\n|---|---|---|---|\n"

    def test_i_etiketli_tablo_sonuclari(self):
        self.agir_listesi([
            (self.BAS + "| Gentamicin | 70 kg | 3 mg/kg/day (q8h) | 70 mg per dose (210 mg/day) |", None),
            (self.BAS + "| Daptomycin | 80 kg | 8 mg/kg (q24h) | 640 mg once daily |", None),
            (self.BAS + "| Daptomycin | 80 kg | 8 mg/kg (q24h) | 500 mg once daily |", "ENGEL"),
            (self.BAS + "| Gentamicin | 70 kg | 3 mg/kg/day (q8h) | 75 mg per dose (210 mg/day) |", "ENGEL"),
            (self.BAS + "| Gentamicin | 70 kg | 3 mg/kg/day (q8h) | 70 mg per dose (250 mg/day) |", "ENGEL"),
            (self.BAS + "| Enoxaparin | 70 kg | 1 mg/kg (q12h) | 70 mg per dose (140 mg/day) |", None),
            (self.BAS + "| Enoxaparin | 70 kg | 1 mg/kg (q12h) | 70 mg per dose (70 mg/day) |", "ENGEL"),
        ], self.K, dolgu="en")
        self.ag("| İlaç | Kilo | Oran | Hesaplanan doz |\n|---|---|---|---|\n| Gentamisin | 70 kg | 3 mg/kg/gün (q8h) | doz başına 70 mg (günlük 210 mg) |",
                None, self.K, dolgu="tr")
        self.ag("| İlaç | Kilo | Oran | Hesaplanan doz |\n|---|---|---|---|\n| Gentamisin | 70 kg | 3 mg/kg/gün (q8h) | doz başına 80 mg (günlük 210 mg) |",
                "ENGEL", self.K, dolgu="tr")


class V4BirimCevrimliSonuc(Temel):
    K = "doz_aritmetigi"

    def test_j_mcg_mg_g(self):
        self.agir_listesi([
            ("60 kg hasta için 2 mcg/kg IV fentanil bolus istendiğinde **1,2 mg** (1200 mcg) çekilir.", "ENGEL"),
            ("60 kg hasta için 2 mcg/kg IV fentanil bolus istendiğinde **0,12 mg** (120 mcg) çekilir.", None),
            ("60 kg hasta için 2 mcg/kg IV fentanil bolus istendiğinde 120 mcg (0,12 mg) çekilir.", None),
            ("60 kg hasta için 2 mcg/kg IV fentanil bolus istendiğinde 1,2 mg çekilir.", "ENGEL"),
            ("For a 60 kg patient, a 2 mcg/kg fentanyl bolus means drawing up **1.2 mg** (1200 mcg).", "ENGEL"),
            ("For a 60 kg patient, a 2 mcg/kg fentanyl bolus means drawing up **0.12 mg** (120 mcg).", None),
            ("For a 60 kg patient, a 5 mg/kg dose is 0.3 g (300 mg).", None),
            ("For a 60 kg patient, a 5 mg/kg dose is 3 g (3000 mg).", "ENGEL"),
        ], self.K, dolgu="en")


# ── Beşinci tur (Claude): kısa metinde dil belirsiz binlik virgül, 'each … infusion' etiketi, sapma ölçütü ──
class V5KisaMetinVeEtiket(Temel):
    K = "doz_aritmetigi"

    def test_binlik_virgul_dil_belirsizken_iki_yorum(self):
        """Kısa tek cümlede satır dili tahmin edilemeyebilir: '6,000 units' doğru çarpımsa ENGEL çıkmaz."""
        self.agir_listesi([
            ("Heparin bolus 80 units/kg for a 75 kg patient is 6,000 units.", None),
            ("Heparin bolus 80 units/kg for a 75 kg patient is 7,500 units.", "ENGEL"),
            ("Paracetamol 15 mg/kg for a 75 kg patient is 1,125 mg.", None),
            ("Paracetamol 15 mg/kg for a 75 kg patient is 1,525 mg.", "ENGEL"),
            ("Çocuk 12 kg. Doz 0,1 mg/kg ile 1,200 mg hesaplanır.", None),
            ("Çocuk 12 kg. Doz 0,1 mg/kg ile 1,500 mg hesaplanır.", "ENGEL"),
        ], self.K)

    def test_infuzyon_enjeksiyon_doz_basina_etiketi(self):
        self.agir_listesi([
            ("When ampicillin 200 mg/kg/day divided q6h is given to a 60 kg adult, each 6-hour infusion equals 2,500 mg (12 g/day).", "ENGEL"),
            ("When ampicillin 200 mg/kg/day divided q6h is given to a 60 kg adult, each 6-hour infusion equals 3,000 mg (12 g/day).", None),
            ("Hasta 80 kg. Sefazolin 100 mg/kg/gün, 8 saatte bir; her infüzyon 2000 mg olarak hazırlanır.", "ENGEL"),
            ("Hasta 64 kg. Enoksaparin 1 mg/kg günde iki kez uygulanır; her enjeksiyon 46 mg olarak hazırlanır.", "ENGEL"),
            ("Hasta 64 kg. Enoksaparin 1 mg/kg günde iki kez uygulanır; her enjeksiyon 64 mg olarak hazırlanır.", None),
            ("Each infusion bag holds 500 mL. The 20 kg child gets ceftriaxone 50 mg/kg, that is 1,000 mg.", None),
            ("Every patient on the ward is weighed. For a 60 kg adult, vancomycin 15 mg/kg q12h gives 900 mg per dose, 1,800 mg/day.", None),
        ], self.K)

    def test_sapma_beklenene_gore(self):
        """%20 payı beklenen doza göre ölçülür: 6000 yerine 7500 (%25 fazla) ENGEL; 300 yerine 250 UYARI kalır."""
        self.dz("20 kg çocuğa 15 mg/kg ile 250 mg verilir.", "UYARI", self.K)
        self.ag("Heparin bolusu 80 ünite/kg, 75 kg hasta için 7500 ünite eder.", "ENGEL", self.K)


if __name__ == "__main__":
    unittest.main(verbosity=1)
