#!/usr/bin/env python3
"""Sınaç: alanını tanıyan öğretim materyali denetçisi (8 boyut × 0–2). 0 jeton, ağ yok, yalnız standart kütüphane.

Belgenin ALANINI (32 profil) ve BİÇİMİNİ (sözel / görsel) tespit eder; her alanda çalışan ortak çekirdeğe ve
alandan bağımsız RİSK TARAMASINA (hasta kimliği, TC no, ilaç dozu yazımı) o alanın kontrollerini ekler.
Profiller: references/ogretim-alanlari.json · ölçek ve gerekçeler: references/ogretim.md.

Kullanım:
  python3 ogretim_denetim.py BELGE.md [--pdf BELGE.pdf] [--alan AD] [--dil KOD] [--yil YYYY] [--json] [--duzelt]
Seçenekler:
  --pdf DOSYA   ölçülecek PDF (verilmezse aynı adlı .pdf aranır; yoksa yazı boyu ve sayfa ölçülmez)
  --alan AD     tespiti geç (frontmatter `alan:` da olur); geçerli adlar references/ogretim-alanlari.json'da
  --dil KOD     yalnız dil alanında: öğretilen dil fr|en|de|es|it (verilmezse metinden tahmin edilir)
  --yil YYYY    değerlendirme yılı (kılavuz yaşı için; verilmezse bu yıl). Çıktıya yazılır
  --json        sonucu JSON ver
  --duzelt      yalnız güvenli iki düzeltme (önce BELGE.md.bak yedeği): karışık yazılmış sözcükte Kiril benzer harf
                → Latin (sayısal/fen alanlarında Yunan harflerine dokunmaz; kod, formül ve frontmatter korunur);
                html/body font-size 8,5 pt altı → 9 pt
Susturma (gerekçe zorunlu): <!-- sinac: yoksay KURAL[,KURAL] — gerekçe -->  ya da satır sonunda <!-- sinac: yoksay — gerekçe -->
Düzeyler: ENGEL (güvenlik: doz yazımı, hasta kimliği, TC no, doz/dönüşüm aritmetiği) · HATA (yayına engel biçim
kusuru) · UYARI. Karar: "yayına engel var" / "karar için denetim eksik" (elle maddeler boş) / "tanımlı kapsamda uygun".
Çıkış kodu: 0 uygun · 1 yayına engel var · 3 karar için denetim eksik · 2 dosya/kullanım hatası.
PDF ölçümü için poppler `pdftotext`, `pdfimages` (boş sayfa için `pdftoppm`) gerekir; yoksa "ölçülmedi" olur.
"""
from __future__ import annotations

import collections
import functools
import html
import json
import re
import shutil
import statistics
import subprocess
import sys
import unicodedata
from datetime import date
from pathlib import Path

sys.dont_write_bytecode = True

BOYUTLAR = ["Doğruluk", "Hedefle uyum", "Seviye", "Ezber ve kavrama",
            "Okunaklılık", "Sıra ve akış", "Kendini sınama", "Verimlilik"]
PROFIL_DOSYASI = Path(__file__).resolve().parents[1] / "references" / "ogretim-alanlari.json"
DUZEY_SIRA = {"ENGEL": 0, "HATA": 1, "UYARI": 2}

# ── Eşikler (gerekçeleri references/ogretim.md; ikisi birlikte değişir) ──
# PDF kelime kutusu yüksekliği / punto oranı, kendi ürettiğimiz PDF'lerde ölçüldü (poppler pdftotext -bbox):
# Helvetica 0,925 · Times 0,900 · Courier 0,786. Kutudan punto ARALIĞI çıkarılır; HATA yalnız en iyimser tahmin
# bile 7 pt'nin altındaysa (her yazı tipinde çok küçük), UYARI en kötümser tahmin 9 pt'nin altındaysa.
KUTU_ORAN_UST, KUTU_ORAN_ALT = 0.925, 0.786
PUNTO_HATA, PUNTO_UYARI = 7.0, 9.0
ALT_BILGI = 0.93                       # sayfa yüksekliğinin bu oranından aşağısı alt bilgi sayılır
BOS_SAYFA = 0.06                       # metin alt sınırı bundan azsa: metinsiz sayfa adayı
MUREKKEP_ESIK = 0.002                  # düşük çözünürlüklü çizimde boyalı piksel oranı bundan azsa: gerçekten boş
YARIM_SAYFA, YARIM_ORAN = 0.40, 0.20   # metin alt sınırı %40'tan az olan sayfaların oranı %20'yi aşarsa (son sayfa hariç)
SAYFA_UYARI = 16                       # sayfa_tavan yoksa: 16+ sayfa gerekçe ister
TERIM_ESIK = 12                        # dil: dil bilgisi terimi sayısı
HEDEF_DISI_ESIK = 8                    # dil: hedef dışı açıklama dili sözcüğü
OKUNUS_UZUN, OKUNUS_UZUN_ORAN = 16, 0.15
YABANCI_ESIK = 3
KISALTMA_ESIK = 3                      # tanımsız kısaltma (≥2 kez kullanılan) sayısı
VERI_YILSIZ_ESIK = 2
ALAN_EN_AZ = 4                         # en yüksek alan puanı bundan azsa: genel
ALAN_SOZCUK_TAVAN = 3                  # tek sözcük puana en çok 3 kez katkı verir
ALT_ALAN_ORAN, ALT_ALAN_EN_AZ = 0.15, 3   # alt alan ≥3 puan ve üst alan puanının %15'i: alt alan (güvenlik kontrollerini zaten miras alır)
BOLUM_EN_AZ_KELIME = 40                # bölüm bazlı ek alan için en az kelime
DESTEK_GUCLU, DESTEK_ORTA = 2.0, 1.3
GORSEL_KELIME = 120
GORSEL_SAYFA_ORAN = 0.5
DUZELT_PUNTO_ALT, DUZELT_PUNTO = 8.5, "9"
KILAVUZ_YAS = 5                        # yerel tarama politikası (NHMRC: geleneksel kılavuz ~5 yılda gözden geçirilir)
KILAVUZ_YAS_YILLIK = 1                 # her yıl güncellenen raporlar (GINA, GOLD, ADA Standards): bir sürüm geride
ARITMETIK_TOLERANS = 0.03              # doz/dönüşüm hesabında kabul edilen göreli fark

SAGLIK_ALANLAR = {"tip", "dis", "hemsirelik", "eczacilik", "veteriner", "beslenme", "fizyoterapi", "acil", "psikoloji"}
FEN_ALANLAR = {"fen", "fizik", "kimya", "biyoloji", "muhendislik", "ziraat", "yer_bilimleri", "matematik", "istatistik"}
SAYISAL_ALANLAR = {"matematik", "istatistik", "fen", "fizik", "kimya", "biyoloji", "muhendislik", "bilgisayar",
                   "yer_bilimleri", "ziraat", "iktisat", "tip", "dis", "hemsirelik", "eczacilik", "veteriner",
                   "beslenme", "fizyoterapi", "acil", "psikoloji", "mimarlik"}

DIL = {
    "fr": {"terim": ["participe", "imparfait", "subjonctif", "conditionnel", "auxiliaire", "infinitif", "gérondif",
                     "complément d'objet", "pronom relatif", "pronom personnel", "adjectif possessif", "déterminant",
                     "plus-que-parfait", "COD", "COI", "partitif", "passé simple", "voix passive"],
           "sik": r"je|tu|il|elle|nous|vous|ils|est|suis|sont|le|la|les|une?|des|du|et|avec|pour|dans|mon|ma|mes|pas",
           "aksan": r"[àâçéèêëîïôûùœ]"},
    "en": {"terim": ["present perfect", "past participle", "gerund", "infinitive", "auxiliary", "modal verb",
                     "passive voice", "relative clause", "conditional", "determiner", "phrasal verb"],
           "sik": r"the|and|is|are|you|this|that|with|have|has|do|does|my|your|it|of|to",
           "aksan": None},
    "de": {"terim": ["Akkusativ", "Dativ", "Genitiv", "Nominativ", "Partizip", "Konjunktiv", "Präteritum",
                     "Perfekt", "Hilfsverb", "Infinitiv", "Relativpronomen", "Passiv", "trennbare"],
           "sik": r"der|die|das|und|ist|ich|du|nicht|mit|ein|eine|sie|wir|bin|haben|zu|auf",
           "aksan": r"[ßä]"},
    "es": {"terim": ["subjuntivo", "pretérito", "imperfecto", "participio", "gerundio", "infinitivo", "auxiliar",
                     "pronombre", "complemento directo", "condicional"],
           "sik": r"el|la|los|las|y|es|soy|está|un|una|con|para|por|yo|tú|que|de|en|no",
           "aksan": r"[áéíóúñ¿¡]"},
    "it": {"terim": ["congiuntivo", "passato prossimo", "imperfetto", "participio", "gerundio", "infinito",
                     "ausiliare", "pronome", "complemento oggetto", "condizionale"],
           "sik": r"il|la|lo|gli|le|e|è|sono|un|una|con|per|io|tu|che|di|non|ho",
           "aksan": r"[àèéìòù]"},
}
TR_TERIMLER = ["nesne zamiri", "yüklem", "tümleç", "edilgen", "ortaç", "ulaç", "dolaylı tümleç", "belirteç"]
INGILIZCE = re.compile(r"\b(the|and|with|which|you|this|that|from|should|would|because)\b")

KIRIL = re.compile(r"[\u0400-\u04FF]")
YUNAN = re.compile(r"[\u0370-\u03FF]")
BENZER_KIRIL = {"е": "e", "а": "a", "о": "o", "р": "p", "с": "c", "х": "x", "у": "y", "і": "i", "ј": "j", "ѕ": "s",
                "Е": "E", "А": "A", "О": "O", "Р": "P", "С": "C", "Т": "T", "М": "M", "Н": "H", "К": "K", "В": "B",
                "Х": "X", "І": "I"}
BENZER_YUNAN = {"ο": "o", "α": "a", "ε": "e", "ι": "i", "ν": "v", "ρ": "p", "τ": "t", "υ": "u", "κ": "k",
                "Ο": "O", "Α": "A", "Ε": "E", "Ι": "I", "Ν": "N", "Ρ": "P", "Τ": "T", "Κ": "K", "Μ": "M", "Β": "B",
                "Η": "H", "Χ": "X", "Ζ": "Z"}
LATIN = re.compile(r"[A-Za-zÀ-ɏ]")
SOZCUK = re.compile(r"[^\W\d_]+(?:['’][^\W\d_]+)?")
MIKRO_BIRIM = re.compile(r"^[μµ][a-zA-Z]{1,3}$")
YER_TUTUCU = re.compile(r"^\s*(?:[-*]\s*)?(?:TODO|FIXME|XXX)\b|\b(?:TODO|FIXME)\s*[:：]|^\s*\?{3,}\s*$|\[\s*\?{3,}\s*\]", re.M)
SINAMA_GUCLU = re.compile(r"kendini\s+(?:dene|sına|test)|cevap\s+anahtar|boşluk\s+doldur|bakmadan|kapat(?:ıp|arak)"
                          r"|dilsiz\s+harita|vaka\s+sorusu|\bprova", re.I)
SINAMA_SOZ = re.compile(r"alıştırma|soru\s*[–-]\s*cevap|\btest(?:i|ler|leri)?\b|\bsınav|\bquiz\b|\bexercise|\bsorular\b"
                        r"|\bsoru\s*\d|\bproblemler\b", re.I)
SORU_IZI = re.compile(r"\?|_{3,}|…{2,}|^\s*\d+[.)]\s|\bsoru\s*\d", re.I | re.M)
OKUNUS = re.compile(r"(?<![\w/])/([a-zçğıöşüâêîôû' ·‿\-]{3,})/(?![\w/])")
BASLIK_MD = re.compile(r"^#{1,4}\s+(\d+(?:\.\d+)*)(\+*)[\s.)]", re.M)
BASLIK_HTML = re.compile(r"<h[1-4][^>]*>\s*(\d+(?:\.\d+)*)(\+*)[\s.)]", re.I)
SAYFA_GONDERME = re.compile(r"(?:\bs\.|\bsayfa)\s*\d+\s*['’][a-zçğıöşü]+", re.I)
PUNTO = re.compile(r"(?:html|body)\s*\{[^}]*?font-size:\s*([\d.]+)\s*pt", re.I)
GORSEL_MD = re.compile(r"!\[([^\]\n]{0,300})\]\(([^)\n]{0,500})\)|<img\b[^>\n]{0,1000}>|<svg\b|<figure\b", re.I)
SEKIL_BASLIGI = re.compile(r"\b(şekil|görsel|resim|figure|fig\.|harita|tablo)\s*\d+", re.I)
YIL = re.compile(r"\b(1[5-9]\d{2}|20\d{2})\b")
CUMLE = re.compile(r"(?:[^.!?\n]|(?<=\d)\.(?=\d))+[.!?]?")   # ondalık nokta cümleyi bölmez (5.0 mg)
SINAMA_ISTEYEN = ("konu-anlatimi", "pano", "rehber", "ders-notu", "")
OKUNUS_ISTEMEYEN = ("indeks", "yonetim")
SUSTURMA = re.compile(r"<!--\s*sinac:\s*yoksay\s*([a-z_,\s]*?)\s*(?:[—–-]+\s*(.*?))?\s*-->", re.I)
ALT_SIMGE = str.maketrans("₀₁₂₃₄₅₆₇₈₉₊₋", "0123456789+-")


_PROFIL_ONBELLEK: dict = {}


def profiller() -> dict:
    """Profil dosyası bir kez okunur (dosya değişirse yeniden)."""
    zaman = PROFIL_DOSYASI.stat().st_mtime
    if _PROFIL_ONBELLEK.get("zaman") != zaman:
        _PROFIL_ONBELLEK.update(zaman=zaman, veri=json.loads(PROFIL_DOSYASI.read_text(encoding="utf-8")))
    return json.loads(json.dumps(_PROFIL_ONBELLEK["veri"]))


def alan_adlari(profil: dict) -> list[str]:
    return [k for k, v in profil.items() if not k.startswith("_") and isinstance(v, dict)]


def kontrol_listesi(profil: dict, alan: str) -> list[str]:
    """Profilin kontrolleri; '@grup' adları `_gruplar`dan açılır, tekrarlar atılır (sıra korunur)."""
    cikti = []
    for ad in profil[alan]["kontroller"]:
        for k in (profil["_gruplar"][ad[1:]] if ad.startswith("@") else [ad]):
            if k not in cikti:
                cikti.append(k)
    return cikti


def elle_listesi(profil: dict, alan: str) -> list[str]:
    cikti = list(profil.get("_ortak_elle", []))
    for g in profil[alan].get("elle_gruplar", []):
        cikti += profil["_elle_gruplar"][g]
    return cikti + profil[alan]["elle"]


# ── Metin hazırlığı ──
def tr_kucuk(s: str) -> str:
    return s.replace("İ", "i").replace("I", "ı").lower()


def en_kucuk(s: str) -> str:
    return s.replace("İ", "i").lower()


FRONT_SATIR = re.compile(r"^\s*(?:#.*|[\w-]+\s*:.*|-\s.*|\s+\S.*)?$")


def on_bilgi(metin: str) -> tuple[dict, str, int]:
    """Frontmatter, gövde ve gövdenin başladığı satır (0 tabanlı). Frontmatter yalnız `anahtar: değer` satırlarından
    oluşuyorsa kabul edilir; '---' arasında düz metin varsa belge frontmatter'sız sayılır (içerik denetlenir)."""
    metin = metin.lstrip("\ufeff").replace("\r\n", "\n")
    m = re.match(r"^[ \t]*---[ \t]*\n(.*?)\n---[ \t]*(?:\n|$)", metin, re.S)
    if not m or not all(FRONT_SATIR.match(x) for x in m.group(1).splitlines()):
        return {}, metin, 0
    meta = {}
    for satir in m.group(1).splitlines():
        if ":" in satir and not satir.lstrip().startswith("#"):
            a, b = satir.split(":", 1)
            meta[a.strip()] = b.strip().strip('"').strip("'")
    return meta, metin[m.end():], metin[:m.end()].count("\n")


def _blok_sil(metin: str, acilis: str, kapanis: str, harf_duyarsiz: bool = False) -> str:
    """Açılış–kapanış arasını, satır sayısını koruyarak boşlukla değiştirir (doğrusal; kapanışsız açılışta durur)."""
    ara = metin.lower() if harf_duyarsiz else metin
    parcalar, i = [], 0
    while True:
        a = ara.find(acilis, i)
        if a < 0:
            break
        k = ara.find(kapanis, a + len(acilis))
        if k < 0:
            break
        k += len(kapanis)
        parcalar.append(metin[i:a])
        parcalar.append("\n" * metin.count("\n", a, k))
        i = k
    parcalar.append(metin[i:])
    return "".join(parcalar)


def _html_tablo_birim(govde: str) -> str:
    """<table> içinde <th> başlığında birim varsa ('Doz (mg)') o sütundaki sayısal <td>'ye birimi ekler."""
    def tablo(m):
        blok = m.group(0)
        satirlar = re.findall(r"<tr\b[^>]{0,200}>.{0,20000}?</tr>", blok, re.S | re.I)
        if not satirlar:
            return blok
        baslik = re.findall(r"<th\b[^>]{0,200}>(.{0,500}?)</th>", satirlar[0], re.S | re.I)
        birim = []
        for h in baslik:
            b = TABLO_BIRIM.search(re.sub(r"<[^>]{0,200}>", "", h))
            birim.append((b.group(1) or b.group(2)) if b else "")
        if not any(birim):
            return blok
        def satir(ms):
            k = [-1]
            def hucre(mh):
                k[0] += 1
                ic = mh.group(2)
                if k[0] < len(birim) and birim[k[0]] and re.fullmatch(r"\s*[\d.,]+\s*", ic):
                    return f"{mh.group(1)}{ic.strip()} {birim[k[0]]}{mh.group(3)}"
                return mh.group(0)
            return re.sub(r"(<td\b[^>]{0,200}>)(.{0,500}?)(</td>)", hucre, ms.group(0), flags=re.S | re.I)
        return re.sub(r"<tr\b[^>]{0,200}>.{0,20000}?</tr>", satir, blok, flags=re.S | re.I)
    return re.sub(r"<table\b.{0,200000}?</table>", tablo, govde, flags=re.S | re.I)


def _html_tablo_satirlari(govde: str) -> str:
    """<tr><td>..</td></tr> satırlarını Markdown tablo satırına çevirir; satır sayısı korunur."""
    def cevir(m):
        blok = m.group(0)
        n = blok.count("\n")
        hucre = re.findall(r"<t[dh]\b[^>]{0,200}>(.{0,2000}?)</t[dh]>", blok, re.S | re.I)
        satir = "| " + " | ".join(re.sub(r"\s+", " ", h).strip() for h in hucre) + " |" if hucre else blok
        return satir + "\n" * n
    return re.sub(r"<tr\b[^>]{0,200}>.{0,20000}?</tr>", cevir, govde, flags=re.S | re.I)


SI_MAKRO = [("\\micro\\gram", "mcg"), ("\\milli\\gram", "mg"), ("\\kilo\\gram", "kg"), ("\\milli\\litre", "mL"),
            ("\\milli\\liter", "mL"), ("\\micro\\litre", "µL"), ("\\gram", "g"), ("\\litre", "L"), ("\\liter", "L")]


def satir_hazirla(g: str) -> str:
    """Tek satırın görünen metni: NFKC, HTML varlıkları, bağlantı, etiket, LaTeX, Markdown biçim işaretleri."""
    g = unicodedata.normalize("NFKC", html.unescape(g)).translate(ALT_SIMGE)
    g = g.replace("\u00a0", " ").replace("\u2009", " ").replace("\u202f", " ").replace("\u2212", "-")
    g = re.sub(r"!\[([^\]\n]{0,300})\]\([^)\n]{0,500}\)", r"\1", g)
    g = re.sub(r"\[([^\]\n]{0,300})\]\([^)\n]{0,500}\)", r"\1", g)
    g = re.sub(r"https?://\S+", " ", g)
    g = re.sub(r"</?[A-Za-z][A-Za-z0-9-]{0,20}(?:\s[^<>\n]{0,500})?/?>", " ", g)
    g = g.replace("{,}", ",").replace("{.}", ".")
    g = re.sub(r"\\(?:SI|qty)\{([^}\n]{0,50})\}\{([^}\n]{0,50})\}", r"\1 \2", g)
    g = re.sub(r"\\si(?:unit)?\{([^}\n]{0,50})\}", r"\1", g)
    for a, b in SI_MAKRO:
        g = g.replace(a, b)
    g = re.sub(r"\\(?:text|mathrm|mathit|mbox|operatorname)\{([^}\n]{0,100})\}", r"\1", g)
    g = re.sub(r"\\frac\{([^}\n]{0,100})\}\{([^}\n]{0,100})\}", r"\1/\2", g)
    g = g.replace("{,}", ",").replace("{.}", ".")
    g = re.sub(r"\\[,;:! ]|~", " ", g).replace("\\times", "×").replace("\\cdot", "·")
    g = re.sub(r"\\[\[\]()]", " ", g).replace("$", " ")
    g = re.sub(r"^\s{0,3}>\s?", "", g)
    g = re.sub(r"_{3,}", " [BOŞLUK] ", g)
    g = g.replace("**", "").replace("__", "")
    g = re.sub(r"(?<![\w*])[*_](?=\S)([^*_\n]{1,300}?)(?<=\S)[*_](?![\w*])", r"\1", g)
    if re.match(r"^\s*\|?\s*:?-{3,}", g):
        return ""
    g = g.replace("|", " ")
    return re.sub(r"[ \t]+", " ", g).strip()


CIT = re.compile(r"^\s{0,3}(`{3,}|~{3,})")


def hazirla_satirlar(govde: str, ofset: int = 0) -> list[dict]:
    """Gövdeyi satır satır hazırlar: {no (belgedeki satır), tam (kod dahil), gor (kod hariç), kod}."""
    g = unicodedata.normalize("NFC", govde)
    g = _blok_sil(g, "<!--", "-->")
    g = _blok_sil(g, "<style", "</style>", True)
    g = _blok_sil(g, "<script", "</script>", True)
    g = _html_tablo_birim(g)
    g = re.sub(r"</?(?:table|tbody|thead|tfoot)\b[^>]{0,200}>", "", g, flags=re.I)
    g = _html_tablo_satirlari(g)
    cikti, kod, cit = [], False, ""
    for i, ham in enumerate(g.split("\n"), 1):
        m = CIT.match(ham)
        if m:
            if not kod:
                kod, cit = True, m.group(1)
            elif m.group(1)[0] == cit[0] and len(m.group(1)) >= len(cit) and not ham.strip()[len(m.group(1)):].strip():
                kod = False
            cikti.append({"no": i + ofset, "tam": "", "gor": "", "kod": True, "ham": ham})
            continue
        tam = satir_hazirla(ham.replace("`", ""))
        gor = "" if kod else satir_hazirla(re.sub(r"`[^`\n]*`", " ", ham))
        cikti.append({"no": i + ofset, "tam": tam, "gor": gor, "kod": kod, "ham": ham})
    return cikti


TABLO_BIRIM = re.compile(r"\(\s*(mg|mcg|µg|μg|mL|ml|ünite|IU|U|g|mEq|mmol)\s*\)|(?<![\w/])(mg|mcg|mL|ünite)\s*$", re.I)


AYIRICI_BORUSUZ = re.compile(r"^\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$")


def _borusuz_tablo(satirlar: list[dict]) -> list[dict]:
    """'a | b' / '--- | ---' biçimli (dış borusuz) tabloyu '| a | b |' biçimine getirir (yalnız tablo okuması için)."""
    yeni = [dict(x) for x in satirlar]
    for i, x in enumerate(yeni):
        if i and AYIRICI_BORUSUZ.match(x["ham"]) and "|" in yeni[i - 1]["ham"] and not yeni[i - 1]["ham"].lstrip().startswith("|"):
            j = i - 1
            while j < len(yeni) and "|" in yeni[j]["ham"] and not yeni[j]["ham"].lstrip().startswith("|"):
                yeni[j]["ham"] = "| " + yeni[j]["ham"].strip().strip("|") + " |"
                j += 1
    return yeni


def tablolar(satirlar: list[dict]) -> list[dict]:
    """Markdown tablolarını 'başlık: değer' satırlarına çevirir (anahtar–değer tablosu ve başlıklı sütun).
    Başlığında birim olan sütunun hücresine birim eklenir: '| Doz (mg) |' + '| 5,0 |' → 'Doz (mg): 5,0 mg'."""
    satirlar = _borusuz_tablo(satirlar)
    cikti, i = [], 0
    while i < len(satirlar):
        if not satirlar[i]["ham"].lstrip().startswith("|"):
            i += 1
            continue
        blok = []
        while i < len(satirlar) and satirlar[i]["ham"].lstrip().startswith("|"):
            blok.append(satirlar[i])
            i += 1
        hucreler = [[satir_hazirla(h) for h in s["ham"].strip().strip("|").split("|")] for s in blok]
        ayirici = [j for j, h in enumerate(hucreler) if all(re.fullmatch(r":?-{3,}:?|", x.strip()) for x in h)]
        baslik = hucreler[0] if ayirici and ayirici[0] == 1 else None
        for j, (s, h) in enumerate(zip(blok, hucreler)):
            if j in ayirici:
                continue
            if len(h) >= 2 and h[0] and h[1]:
                cikti.append({"no": s["no"], "tam": f"{h[0]}: {h[1]}", "gor": f"{h[0]}: {h[1]}", "kod": False})
            if baslik and j > 1:
                for k, deger in enumerate(h):
                    if k < len(baslik) and baslik[k] and deger:
                        b = TABLO_BIRIM.search(baslik[k])
                        birim = (b.group(1) or b.group(2)) if b else ""
                        ek = f" {birim}" if birim and re.fullmatch(r"[\d.,]+(?:\s*[-–—]\s*[\d.,]+)?", deger.strip()) else ""
                        satir = f"{h[0]} {baslik[k]}: {deger}{ek}"
                        cikti.append({"no": s["no"], "tam": satir, "gor": satir, "kod": False})
    return cikti


def hazirla(govde: str) -> tuple[str, str]:
    """(gor, tam) birleşik metin; satır yapısı korunur."""
    satirlar = hazirla_satirlar(govde)
    return "\n".join(s["gor"] for s in satirlar), "\n".join(s["tam"] for s in satirlar)


def cumleler(metin: str) -> list[str]:
    return [m.group(0) for m in CUMLE.finditer(metin)]


def paragraflar(metin: str) -> list[str]:
    return [re.sub(r"\s*\n\s*", " ", p) for p in re.split(r"\n\s*\n", metin) if p.strip()]


def bolumler(govde: str) -> list[tuple[str, str]]:
    parcalar = re.split(r"^(#{1,3}\s+.*)$", govde, flags=re.M)
    cikti, baslik, bekleyen = [], "", False
    for p in parcalar:
        if re.match(r"^#{1,3}\s+", p):
            if bekleyen:
                cikti.append((baslik, ""))
            baslik, bekleyen = p, True
        elif p.strip():
            cikti.append((baslik, p))
            bekleyen = False
    if bekleyen:
        cikti.append((baslik, ""))
    return cikti


def karisik_sozcukler(metin: str) -> list[str]:
    """Aynı sözcük gövdesinde Latin harfle karışık Kiril/Yunan harf. Kesme işaretinden sonraki Türkçe ek sayılmaz
    (СССР'nin, λόγος'un karışık değildir)."""
    cikti = []
    for s in SOZCUK.findall(metin):
        if any((KIRIL.search(p) or YUNAN.search(p)) and LATIN.search(p) and not MIKRO_BIRIM.match(p)
               for p in re.split(r"['’]", s)):
            cikti.append(s)
    return cikti


def say(desen: str, metin: str) -> int:
    return len(re.findall(desen, metin))


def sayi(s: str) -> float:
    s = s.strip()
    if re.fullmatch(r"[1-9]\d{0,2}(?:\.\d{3})+", s):   # 1.500 binlik; 0.125 ondalık
        return float(s.replace(".", ""))
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", ".")
    return float(s)


# ── PDF ölçümü ──
def _murekkep(pdf: Path, sayfa: int) -> float | None:
    if not shutil.which("pdftoppm"):
        return None
    r = subprocess.run(["pdftoppm", "-f", str(sayfa), "-l", str(sayfa), "-r", "20", "-gray", str(pdf)],
                       capture_output=True)
    veri = r.stdout
    if r.returncode != 0 or not veri.startswith(b"P5"):
        return None
    m = re.match(rb"P5\s+(\d+)\s+(\d+)\s+(\d+)\s", veri)
    if not m:
        return None
    pikseller = veri[m.end():]
    return sum(1 for b in pikseller if b < 200) / max(len(pikseller), 1)


def pdf_olc(pdf: Path) -> dict | None:
    if not (shutil.which("pdftotext") and shutil.which("pdfimages")):
        return None
    cikti = subprocess.run(["pdftotext", "-bbox", str(pdf), "-"], capture_output=True, text=True)
    if cikti.returncode != 0:
        return None
    sayfalar = re.split(r"<page ", cikti.stdout)[1:]
    gorselli = set()
    liste = subprocess.run(["pdfimages", "-list", str(pdf)], capture_output=True, text=True).stdout
    for satir in liste.splitlines()[2:]:
        p = satir.split()
        if p and p[0].isdigit():
            gorselli.add(int(p[0]))
    yukseklik, doluluk, kelime, murekkep = [], [], [], {}
    for i, pg in enumerate(sayfalar, 1):
        h = re.search(r'height="([\d.]+)"', pg)
        H = float(h.group(1)) if h else 842.0
        kutular = [(float(a), float(b)) for a, b in re.findall(r'yMin="([\d.]+)" xMax="[\d.]+" yMax="([\d.]+)"', pg)]
        govde = [(a, b) for a, b in kutular if b < ALT_BILGI * H]
        yukseklik += [b - a for a, b in govde]
        alt_sinir = max((b for _, b in govde), default=0) / H
        doluluk.append((i, alt_sinir, i in gorselli))
        kelime.append(len(govde))
        if alt_sinir < BOS_SAYFA and i not in gorselli:
            murekkep[i] = _murekkep(pdf, i)
    kutu = round(statistics.median(yukseklik), 2) if yukseklik else 0.0
    return {"sayfa": len(sayfalar), "kutu": kutu, "doluluk": doluluk, "kelime": kelime, "murekkep": murekkep,
            "metin_var": any(kelime)}


# ── Alan ve biçim tespiti ──
def dil_tahmin(kucuk: str) -> tuple[str, int]:
    temiz = OKUNUS.sub(" ", kucuk)
    puan = {k: say(r"(?<!\w)(?:" + v["sik"] + r")(?!\w)", temiz) for k, v in DIL.items()}
    en = max(puan, key=puan.get)
    return en, puan[en]


EK = (r"(?:lik|lık|lük|luk|ci|cı|cu|cü|çi|çı|çu|çü|sal|sel|ler|lar|nin|nın|nun|nün|den|dan|ten|tan|si|sı|su|sü"
      r"|yi|yı|yu|yü|ye|ya|in|ın|un|ün|de|da|te|ta|dir|dır|i|ı|u|ü|e|a)")
YUMUSAMA = {"k": "kğg", "p": "pb", "t": "td", "ç": "çc"}


def sozcuk_deseni(s: str) -> str:
    """Anahtar sözcük deseni: sondaki ünsüz yumuşar (çürük → çürüğü, kitap → kitabı); 4 harf ve kısası yalnız ek
    zinciriyle eşleşir (gen ≠ genel, diş → dişçi); uzun anahtar kök olarak eşleşir."""
    s = s.strip()
    son = s[-1:]
    if len(s) >= 3 and son in YUMUSAMA and " " not in s:
        govde = re.escape(s[:-1]) + "[" + YUMUSAMA[son] + "]"
    else:
        govde = re.escape(s)
    e = r"(?<!\w)" + govde
    if len(s) <= 4 and son.isalpha():
        return e + EK + r"{0,3}(?![\w])"
    return e


def _agirliklar(profil: dict) -> dict:
    """Aynı sözcük birden çok profilde geçiyorsa ağırlığı bölünür (nüfus: coğrafya + sosyal → 0,5)."""
    say_ = {}
    for ad in alan_adlari(profil):
        for s in set(profil[ad].get("sozcukler", [])):
            say_[s] = say_.get(s, 0) + 1
    return {s: 1 / n for s, n in say_.items()}


def _sade_sozcukler(sozcukler: list[str]) -> list[str]:
    """Aynı profilde başka bir anahtarla başlayan anahtarı at (hemşire / hemşirelik çift sayılmasın)."""
    return [w for w in sozcukler if not any(v != w and len(v) >= 4 and w.startswith(v) for v in sozcukler)]


@functools.lru_cache(maxsize=4096)
def _desen(s: str):
    return re.compile(sozcuk_deseni(s))


def alan_puanlari(gor: str, profil: dict) -> tuple[dict, dict]:
    basliklar = "\n".join(x for x in gor.splitlines() if x.lstrip().startswith("#"))
    gor = gor + "\n" + basliklar                      # başlık sözcükleri çift sayılır
    kt, ke = tr_kucuk(gor), en_kucuk(gor)
    agirlik = _agirliklar(profil)
    puanlar, kanit = {}, {}
    sozcuk_tr = collections.Counter(SOZCUK.findall(kt))
    sozcuk_en = collections.Counter(SOZCUK.findall(ke))
    for ad in alan_adlari(profil):
        p = profil[ad]
        if not p.get("sozcukler"):
            continue
        toplam, ip = 0.0, []
        for s in _sade_sozcukler(p["sozcukler"]):
            desen = _desen(s)
            if re.fullmatch(r"[^\W\d_]+", s.strip()):        # tek sözcük: yalnız benzersiz sözcükler üzerinde
                n_tr = sum(n for w, n in sozcuk_tr.items() if desen.match(w))
                n_en = sum(n for w, n in sozcuk_en.items() if desen.match(w))
            else:
                n_tr, n_en = len(desen.findall(kt)), len(desen.findall(ke))
            n = min(max(n_tr, n_en), ALAN_SOZCUK_TAVAN)
            if n:
                toplam += n * agirlik.get(s, 1)
                ip.append(s.strip())
        puanlar[ad], kanit[ad] = round(toplam, 2), ip
    okunus = len(OKUNUS.findall(gor))
    _, sik = dil_tahmin(kt)
    puanlar["dil"] = 3 * okunus + (6 if re.search(r"\bokunuş", kt) else 0) + (min(sik, 30) // 3 if okunus else 0)
    kanit["dil"] = [f"{okunus} okunuş /…/"] if okunus else []
    return puanlar, kanit


def alan_tespit(meta: dict, gor: str, profil: dict, alan: str | None = None) -> dict:
    """Önce --alan, sonra frontmatter `alan:`, sonra sözcük puanı."""
    secilen = alan or meta.get("alan", "").strip().lower()
    if secilen:
        if secilen not in alan_adlari(profil):
            raise ValueError(f"bilinmeyen alan: {secilen} ({', '.join(alan_adlari(profil))})")
        return {"alan": secilen, "kaynak": "kullanıcı seçimi", "destek": "—", "kanit": [], "ikinci": None,
                "puanlar": {}}
    puanlar, kanit = alan_puanlari(gor, profil)
    sira = sorted(puanlar.items(), key=lambda x: -x[1])
    en, p1 = sira[0]
    ust = profil.get(en, {}).get("ust") if en != "dil" else None
    aile_kok = ust or en
    altlar = [(a, puanlar.get(a, 0)) for a in alan_adlari(profil) if profil[a].get("ust") == aile_kok]
    if altlar and en == aile_kok:
        alt, pa = max(altlar, key=lambda x: x[1])
        if pa >= ALT_ALAN_EN_AZ and pa >= ALT_ALAN_ORAN * p1:
            en, p1 = alt, max(pa, ALAN_EN_AZ)
    aile = {aile_kok} | {a for a, _ in altlar}
    rakipler = [(a, p) for a, p in sira if a not in aile and a != en]
    rakip_ad, rakip = (rakipler[0] if rakipler else (None, 0))
    ikinci = aile_kok if en != aile_kok and puanlar.get(aile_kok, 0) >= ALAN_EN_AZ else (
        rakip_ad if rakip >= ALAN_EN_AZ else None)
    # Uzun metinde birkaç dağınık sözcük alan kanıtı sayılmaz: eşik her 10 000 sözcükte 1 artar (en çok +8).
    en_az = ALAN_EN_AZ + min(8, len(gor.split()) // 10000)
    if p1 < en_az:
        return {"alan": "genel", "kaynak": "tespit", "destek": "zayıf", "kanit": [], "ikinci": en if p1 else None,
                "puanlar": puanlar}
    destek = ("güçlü" if p1 >= DESTEK_GUCLU * max(rakip, 1) and p1 >= 2 * ALAN_EN_AZ
              else "orta" if p1 >= DESTEK_ORTA * max(rakip, 1) else "zayıf")
    return {"alan": en, "kaynak": "tespit", "destek": destek, "kanit": kanit[en][:6], "ikinci": ikinci,
            "puanlar": puanlar}


def bolum_alanlari(govde: str, profil: dict, ana: str) -> list[str]:
    """Karma belge: yeterince uzun bir bölümün en güçlü alanı ana alandan farklıysa ek profil olarak döner."""
    ek = []
    for _, icerik in bolumler(govde):
        gor, _ = hazirla(icerik)
        if len(SOZCUK.findall(gor)) < BOLUM_EN_AZ_KELIME:
            continue
        puanlar, _ = alan_puanlari(gor, profil)
        en, p = max(puanlar.items(), key=lambda x: x[1])
        if p >= ALAN_EN_AZ and en not in (ana, "dil") and en not in ek:
            ek.append(en)
    return ek


def bicim_tespit(meta: dict, govde: str, gor: str, olcum: dict | None) -> str:
    if meta.get("bicim") in ("gorsel", "sozel"):
        return meta["bicim"]
    gorsel = len(GORSEL_MD.findall(govde))
    kelime = len(SOZCUK.findall(gor))
    if gorsel >= 2 and kelime / gorsel < GORSEL_KELIME:
        return "gorsel"
    if olcum and olcum["sayfa"]:
        kelimeler = olcum.get("kelime") or [0] * olcum["sayfa"]
        oran = sum(1 for (_, _, g), k in zip(olcum["doluluk"], kelimeler) if g and k < GORSEL_KELIME) / olcum["sayfa"]
        if oran >= GORSEL_SAYFA_ORAN:
            return "gorsel"
    return "sozel"


# ── Dil kontrolleri ──
def k_dil_terim(c, ekle):
    terim = sum(say(r"(?<!\w)" + re.escape(t) + r"(?!\w)", c["kucuk"]) for t in
                [tr_kucuk(x) for x in DIL[c["dil"]]["terim"] + TR_TERIMLER])
    if terim > TERIM_ESIK:
        ekle("Seviye", "UYARI", f"Dil bilgisi terimi {terim} kez (eşik {TERIM_ESIK})",
             "Acemide terim yerine KİM–FİİL–GERİSİ şeması ve Türkçe açıklama kullan")


def k_dil_hedef_disi(c, ekle):
    if c["dil"] != "en":
        ing = INGILIZCE.findall(c["kucuk_en"])
        if len(ing) > HEDEF_DISI_ESIK:
            ekle("Seviye", "UYARI", f"Hedef dışı dil (İngilizce) sözcükleri: {len(ing)} (eşik {HEDEF_DISI_ESIK})",
                 "Açıklama Türkçe olmalı; hedef dışı dil öğrenciye gitmez")


def k_dil_okunus_uzun(c, ekle):
    oku = c["okunuslar"]
    uzun = [o for o in oku if len(o.replace("·", " ").split()) > OKUNUS_UZUN]
    if oku and len(uzun) / len(oku) > OKUNUS_UZUN_ORAN:
        ekle("Ezber ve kavrama", "UYARI", f"Uzun cümle oranı yüksek: {len(uzun)}/{len(oku)} okunuş {OKUNUS_UZUN}+ kelime",
             "Ezber için cümleyi böl; tekrar eden iskelet kullan")


def k_dil_okunussuz(c, ekle):
    ayar = DIL[c["dil"]]
    sik = say(r"(?<!\w)(?:" + ayar["sik"] + r")(?!\w)", OKUNUS.sub(" ", c["kucuk"]))
    yabanci = sik >= YABANCI_ESIK or bool(ayar["aksan"] and re.search(ayar["aksan"], c["gor"]))
    if not c["okunuslar"] and yabanci and c["tur"] not in OKUNUS_ISTEMEYEN:
        ekle("Ezber ve kavrama", "UYARI", "Yabancı dilde metin var ama Türkçe harfli okunuş (/…/) yok",
             "Her yabancı cümlenin yanına okunuş ve Türkçe karşılık koy (Yabancı · Okunuş · Türkçe)")


# ── Sağlık: doz yazımı (risk taraması, alandan bağımsız; satır satır, her eşleşme ayrı bulgu) ──
ILAC_BIRIM = (r"(?:(?i:mg|mcg|µg|μg|ng|ünite|unite|iu|meq|mmol|mgr|miligram|mikrogram|cc)(?:l[ıiuü]k|[ıiuü]n)?(?![a-zA-Z])"
              r"|(?:mL|ml|ML)(?![a-zA-Z])|U(?![a-zA-Z]))")
GRAM = r"(?:g|gr|gram)(?![a-zA-Z])"
LAB_PAYDA = r"(?!\s*/\s*(?:dL|dl|L|l|mL|ml)\b)"
ILAC_ADI = re.compile(r"\b(?:parasetamol|paracetamol|acetaminophen|asetaminofen|ibuprofen|aspirin|morfin|morphine|fentanil|fentanyl"
                      r"|insülin|insulin|heparin|enoksaparin|enoxaparin|adrenalin|adrenaline|epinephrine|amoxicillin|ceftriaxone"
                      r"|vancomycin|furosemide|digoxin|warfarin|metoprolol|dexamethasone|ondansetron"
                      r"|epinefrin|digoksin|furosemid|metformin|amoksisilin|seftriakson|vankomisin|gentamisin|diazepam"
                      r"|midazolam|lorazepam|ketamin|propofol|ondansetron|metoklopramid|deksametazon|prednizolon|metilprednizolon"
                      r"|varfarin|potasyum klorür|kcl|magnezyum sülfat|kalsiyum glukonat|amiodaron|atropin|naloksan|tramadol"
                      r"|kodein|oksitosin|salbutamol|ipratropium|levotiroksin|kinin|klorokin|siprofloksasin|azitromisin"
                      r"|bisoprolol|metoprolol|propranolol|ramipril|enalapril|amlodipin|losartan|atorvastatin|haloperidol"
                      r"|ketiapin|olanzapin|risperidon|lityum|valproat|karbamazepin|fenitoin|levetirasetam)\w*"
                      r"|\b\w+(?:mab|nib|pril|sartan|olol|statin|azol|misin|mycin|silin|cillin|floksasin|oxacin|dipin|prazol"
                      r"|tidin|zepam|zolam|kain|caine|parin|faks)\b", re.I)
DOZ_BAGLAM = re.compile(r"\bilaç|\bdoz|verilir|verilmeli|verilecek|verildi|verilmesi|uygulan|\biv\b|\bim\b|\bpo\b|\bsc\b|tablet|kapsül|ampul|flakon|enjeksiyon"
                        r"|infüzyon|reçete|şurup|\d\s*x\s*\d|\bdrug|\bdose|administer|başlan|yapılır|\bdaily\b|\bbid\b|\btid\b"
                        r"|\bqid\b|\bnightly\b|\btablets?\b|\bgiven\b|içilir|ağızdan|\boral\b|topikal|süspansiyon|takviye|yemeklerden\s+(?:önce|sonra)|(?:aç|tok)\s+karnına", re.I)
DUZEY_BAGLAM = re.compile(r"düzey|seviye|çukur|pik|level|ölçül|sonuç|değeri|çıkış|volüm|hacmi|klirens|normal|referans", re.I)
BESIN_BAGLAM = re.compile(r"lif|protein|karbonhidrat|yağ|şeker|tuz|porsiyon|besin|gıda|fiber|sodyum alımı|kcal|enerji"
                          r"|vitamin|mineral|folat|bulunur|içerir|içeriği", re.I)
SIVI_OLCUM = re.compile(r"idrar|çıkış|diürez|drenaj|balans|kayb|urine output", re.I)
BINLIK = r"\d{1,3}(?:\.\d{3})+(?![.,]?\d)"
ARALIK_EK = r"(?:\s*(?:[-–—/]|,\s|\b(?:ve|veya|ya da|ile|or|and|to)\b)\s*\d+(?:[.,]\d+)?)*\s*"
SONDAKI_SIFIR = re.compile(r"(?<![\d.,])(?!" + BINLIK + r")\d+[.,]0+(?!\d)" + ARALIK_EK + ILAC_BIRIM + LAB_PAYDA)
ARALIK_SIFIR = re.compile(r"(?<![\d.,])\d+[.,]0+\s*(?:veya|ya da|ile|or)\s*\d+(?:[.,]\d+)?\s*" + ILAC_BIRIM + LAB_PAYDA)
SONDAKI_SIFIR_G = re.compile(r"(?<![\d.,])(?!" + BINLIK + r")\d+[.,]0+(?!\d)" + ARALIK_EK + GRAM + LAB_PAYDA)
ONDALIK_SONU_SIFIR = re.compile(r"(?<![\d.,])(?!" + BINLIK + r")\d+[.,]\d*[1-9]0+\s*" + ILAC_BIRIM + LAB_PAYDA)
CIPLAK_ONDALIK = re.compile(r"(?<![\d\w.,])[.,]\d+" + ARALIK_EK + "(?:" + ILAC_BIRIM + "|" + GRAM + ")")
OCR_SIFIR = re.compile(r"(?<![\d.,])\d+[.,]\s?[Oo]\s*" + ILAC_BIRIM)
BINLIK_VIRGUL = re.compile(r"(?<![\d.,])\d{1,3},\d{3}(?![\d.,])\s*" + ILAC_BIRIM)
DOZ_IZI = re.compile(r"\d\s*" + ILAC_BIRIM)
OGRETICI_YANLIS = re.compile(r"❌|✗|✘|\byanlış\s*(?:yazım|örnek|kullanım|gösterim)?\s*[:：]|\bhatalı\s*(?:yazım|örnek|kullanım)\s*[:：]"
                             r"|\bwrong\s*:|\bdo not write", re.I)
# Zayıf işaret ('yazılmaz', 'kullanmayın'): yalnız dozun hemen yanında ('5,0 mg yazılmaz', 'kullanmayın: 5,0 mg')
OGRETICI_ZAYIF = r"(?:yazılmaz|yazmayın|kullanmayın|kullanılmaz|do not use)"


def ogretici_satir(t: str) -> bool:
    """Kısaltma/yazım kuralı anlatan satır ('U/IU kullanmayın'): kısaltma ve boşluk uyarısı verilmez."""
    return bool(OGRETICI_YANLIS.search(t) or re.search(r"\b" + OGRETICI_ZAYIF, t, re.I))


def ogretici_mi(t: str, b: str) -> bool:
    k = t.find(b)
    for m in OGRETICI_YANLIS.finditer(t):
        ara = t[m.end():k] if k > m.end() else ""
        if k < 0 or k < m.start() or not re.search(r"ardından|sonra|\bthen\b|;|\bama\b|\bancak\b", ara, re.I):
            return True       # işaret bu doza ait (aradaki 'ardından …' başka bir talimatı başlatır)
    e = re.escape(b)
    return bool(re.search(e + r"[\s\"'”»)]{0,3}(?:şeklinde|biçiminde|diye)?\s*" + OGRETICI_ZAYIF, t, re.I)
                or re.search(OGRETICI_ZAYIF + r"\s*[:：]?\s*[\"'“«(]?\s*" + e, t, re.I))


# Tartım/hazırlamada sondaki sıfır ölçüm duyarlılığıdır (anlamlı basamak), doz yazımı değil.
HAZIRLAMA = re.compile(r"tartıl|tartım|analitik terazi|anlamlı basamak|significant fig|duyarlılı|hassasiyet|pipetle"
                       r"|stok çözelti|çözelti hazırla|weigh", re.I)
ONDALIK_IZI = re.compile(r"\d[.,]|[.,]\d")


def tarama_satirlari(c) -> list[dict]:
    return [s for s in c["satirlar"] if s["tam"]] + c["tablo"]


SATIR_SONU_SAYI = re.compile(r"\d(?:[.,]\d+)?\s*$|(?<![\d\w])[.,]\d+\s*$")
SATIR_BASI_BIRIM = re.compile(r"^\s*(?:mg|mcg|µg|μg|g|mL|ml|ünite|IU|mEq)\b", re.I)


def doz_satirlari(c) -> list[dict]:
    """Tarama satırları; satır sonu sayı + sonraki satır başı birim ise ('4,0' / 'mg IV') iki satır birleştirilir."""
    sat = tarama_satirlari(c)
    cikti = []
    for i, st in enumerate(sat):
        t = st["tam"]
        bitisik = (st["no"] is None or sat[i + 1]["no"] is None or sat[i + 1]["no"] == st["no"] + 1) if i + 1 < len(sat) else False
        if bitisik and SATIR_SONU_SAYI.search(t) and SATIR_BASI_BIRIM.match(sat[i + 1]["tam"]):
            t = t.rstrip() + " " + sat[i + 1]["tam"].lstrip()
        cikti.append({**st, "tam": t})
    return cikti


def _ilac_satiri(s: str) -> bool:
    return bool(ILAC_ADI.search(s) or DOZ_BAGLAM.search(s))


def yan_cumleler(satir: str) -> list[str]:
    """Satırı yan cümlelere böler; ondalık nokta ve '.5' gibi baştaki noktayı bölmez."""
    return [x for x in re.split(r"(?<=[.!?;])\s+(?=[A-ZÇĞİÖŞÜ0-9(])|;\s*", satir) if x.strip()]


def k_tip_doz_yazimi(c, ekle):
    fen = bool(c["alanlar"] & FEN_ALANLAR) and not (c["alanlar"] & SAGLIK_ALANLAR)
    for st0 in doz_satirlari(c):
        if not ONDALIK_IZI.search(st0["tam"]):   # bütün desenler rakama bitişik nokta/virgül ister: hızlı eleme
            continue
        satir_ilac = _ilac_satiri(st0["tam"])
        for t in yan_cumleler(st0["tam"]):
            if not ONDALIK_IZI.search(t):
                continue
            st = {"no": st0["no"], "tam": t}
            ilac = (_ilac_satiri(t) if satir_ilac else False) or (
                satir_ilac and not DUZEY_BAGLAM.search(t) and not BESIN_BAGLAM.search(t))
            if DUZEY_BAGLAM.search(t) and not ilac:
                continue
            if fen and not ilac:
                continue
            if BESIN_BAGLAM.search(t) and not ilac:
                continue
            bul = [m.group(0) for m in SONDAKI_SIFIR.finditer(t)] + [m.group(0) for m in CIPLAK_ONDALIK.finditer(t)]
            sivi = SIVI_OLCUM.search(t) and not re.search(r"\bdoz|çekilecek|\bdose", t, re.I)
            bul = [b for b in bul if not (re.search(r"m[lL]\b", b) and (not ilac or sivi))]
            if ilac and not BESIN_BAGLAM.search(t):
                bul += [m.group(0) for m in SONDAKI_SIFIR_G.finditer(t)]
            for b in dict.fromkeys(bul):
                if ogretici_mi(t, b):
                    ekle("Doğruluk", "UYARI", f"Yanlış doz yazımı öğretici örnek olarak işaretli ({b})",
                         "Doğrusunun hemen yanında olduğundan emin ol", ornek=b, satir=st["no"])
                else:
                    ekle("Doğruluk", "ENGEL", f"Doz yazımında sondaki sıfır ya da baştaki sıfırsız ondalık ({b})",
                         "5,0 mg → 5 mg; ,5 mg → 0,5 mg. Virgül görülmezse 10 kat doz hatası (ISMP)", ornek=b, satir=st["no"])
            for m in ([] if HAZIRLAMA.search(t) else ONDALIK_SONU_SIFIR.finditer(t)):
                ekle("Doğruluk", "UYARI", f"Ondalık kısmın sonunda sıfır ({m.group(0)})",
                     "0,50 mg → 0,5 mg yazmak daha güvenli (ISMP kuralı tam sayı dozlar için; bu kullanım belirsiz)",
                     ornek=m.group(0), satir=st["no"])
            for m in OCR_SIFIR.finditer(t):
                ekle("Doğruluk", "UYARI", f"Doz rakamında harf olabilir ({m.group(0)})",
                     "OCR/yazım hatası şüphesi: 'O' harfi mi sıfır mı, kaynağa bak", ornek=m.group(0), satir=st["no"])
            for m in BINLIK_VIRGUL.finditer(t):
                ekle("Doğruluk", "UYARI", f"Virgüllü binlik belirsiz ({m.group(0)})",
                     "Türkçede virgül ondalıktır: '1,000 mg' 1 mg okunabilir; '1000 mg' ya da '1.000 mg' yaz",
                     ornek=m.group(0), satir=st["no"])


TEHLIKELI = [
    (re.compile(r"\b\d+\s*(?:U|u|IU|iu)\b(?!\s*/\s*(?:L|l|dL)\b)"), "U / IU (ünite)", "'ünite' yaz"),
    (re.compile(r"\b\d+\s*cc\b"), "cc", "'mL' yaz"),
    (re.compile(r"(?<!\w)q\.?o?\.?d\.?(?!\w)", re.I), "q.d. / q.o.d.", "'günde bir' / 'iki günde bir' yaz"),
    (re.compile(r"\b(?:MSO4|MgSO4)\b"), "MSO4 / MgSO4", "ilacın tam adını yaz"),
    (re.compile(r"\d\s*[μµ]g\b"), "μg", "'mcg' yaz"),
]
TEHLIKELI_EK = [
    (re.compile(r"(?<![\w/])(?:SC|SQ|S\.C\.|subq|sub-q)(?!\w)|\d\s*(?:mg|mL|ml|ünite|U)\s+sc\b"), "SC/SQ (deri altı)",
     "'SUBQ' ya da 'deri altı' yaz"),
    (re.compile(r"(?<!\w)(?:t\.?i\.?w\.?|D/C)(?!\w)", re.I), "TIW / D/C", "'haftada üç kez', 'kes' ya da 'taburcu' yaz"),
    (re.compile(r"(?<!\w)(?:AD|AS|AU|OD|OS|OU)\s+(?:damla|uygula|\d+\s*(?:damla|gtt|drops?)\b)", re.I), "AD/AS/AU, OD/OS/OU (kulak/göz)",
     "'sağ kulak', 'sol göz' diye yaz"),
    (re.compile(r"(?<![\w<>])[<>]\s*\d+\s*(?:mg|mcg|mL|ml|U)\b"), "doz önünde > / <", "'en çok' / 'en az' yaz"),
    (re.compile(r"(?<![\d.,])\d+(?:[.,]\d+)?\s*ml\b"), "ml", "'mL' yaz (küçük l, 1 ile karışır)"),
    (re.compile(r"(?i:adrenalin|epinefrin|epinephrine)[^.\n]{0,40}?\b1\s*:\s*\d{1,3}(?:[.,]?\d{3})+"),
     "oranla derişim (1:1000)", "miktar/hacim yaz: 1 mg/mL"),
]


def _kisaltma_tara(c, liste) -> list:
    bulunan = []
    for desen, ad, oneri in liste:
        for st in tarama_satirlari(c):
            m = desen.search(st["tam"])
            if m and not ogretici_satir(st["tam"]) and not re.search(r"motor|silindir|ISMP", st["tam"], re.I):
                bulunan.append((ad, oneri, m.group(0), st["no"]))
    return bulunan


def k_tip_tehlikeli_kisaltma(c, ekle):
    for ad, oneri, ornek, no in _kisaltma_tara(c, TEHLIKELI):
        ekle("Doğruluk", "UYARI", f"Karıştırılmaya açık tıbbi kısaltma: {ad}", oneri + " (ISMP 2024)", ornek=ornek, satir=no)


def k_saglik_kisaltma_ek(c, ekle):
    for ad, oneri, ornek, no in _kisaltma_tara(c, TEHLIKELI_EK):
        ekle("Doğruluk", "UYARI", f"Karıştırılmaya açık klinik yazım: {ad}", oneri + " (ISMP 2024)", ornek=ornek, satir=no)


# g ve U yalnız ilaç/doz bağlamlı yan cümlede: "5G ağı", "2g NaCl tartılır" gibi fen satırları sayılmaz (g küçük harf).
BITISIK_DOZ_EK = re.compile(r"(?<![\w.,])\d+(?:[.,]\d+)?(?:g|U|mEq)(?![\w/])")
BITISIK_DOZ = re.compile(r"(?<![\w.,])\d+(?:[.,]\d+)?(?:mg|mcg|mL|ml|ünite|IU)\b|[a-zçğıöşüA-ZÇĞİÖŞÜ]{3,}\d+(?:[.,]\d+)?\s*(?:mg|mcg|mL)\b")


def k_saglik_bosluk(c, ekle):
    for st in tarama_satirlari(c):
        if ogretici_satir(st["tam"]):
            continue
        m = BITISIK_DOZ.search(st["tam"])
        if not m and BITISIK_DOZ_EK.search(st["tam"]):
            for t in yan_cumleler(st["tam"]):
                if ILAC_ADI.search(t) or DOZ_BAGLAM.search(t):
                    m = BITISIK_DOZ_EK.search(t)
                    if m:
                        break
        if m:
            ekle("Doğruluk", "UYARI", f"İlaç adı, doz ve birim bitişik ({m.group(0)})",
                 "Araya boşluk koy: 10 mg, propranolol 20 mg (ISMP: 'propranolol20 mg' 120 mg okunmuş)",
                 ornek=m.group(0), satir=st["no"])


MGKG = re.compile(r"(?<![\d.,])\d[\d.,]*\s*(?:mg|mcg|g|mL|ml|U|ünite|IU)\s*/\s*kg(?:\s*/\s*([a-zçğıöşü]+))?", re.I)
ZAMAN = re.compile(r"günde|günlük|/\s*gün|her\s+\d+\s*saat|saatte\s+bir|doz\s+başına|tek\s+doz|bölünmüş|/\s*doz"
                   r"|per\s+day|/\s*day|daily|divided|\bq\d+h\b|/\s*saat|/\s*dk|/\s*h\b|/\s*\d+\s*(?:saat|h)\b", re.I)


def k_doz_kg_belirsiz(c, ekle):
    for st in tarama_satirlari(c):
        for cm in cumleler(st["tam"]):
            for m in MGKG.finditer(cm):
                ek_birim = (m.group(1) or "").lower()
                if ek_birim == "d":
                    ekle("Doğruluk", "UYARI", f"'mg/kg/d': d gün mü doz mu belirsiz ({m.group(0)})",
                         "'mg/kg/gün' ya da 'mg/kg/doz' diye açık yaz", ornek=m.group(0), satir=st["no"])
                elif not ek_birim and not ZAMAN.search(cm):
                    ekle("Doğruluk", "UYARI", f"Kiloya göre doz zaman birimi belirsiz ({m.group(0)})",
                         "'mg/kg/gün' mü 'mg/kg/doz' mu yaz; sıklığı ve en yüksek dozu ekle", ornek=m.group(0), satir=st["no"])


SAYI = r"(?<![\d.,])(\d+(?:[.,]\d+)*)"   # yalnız sayının başından: uzun rakam dizisinde karesel süre olmasın
DOZ_B = r"(mg|mcg|µg|μg|g|mL|ml|ünite|IU)"
EK_PAYDA = r"(?:\s*/\s*(?:doz|gün|day|dose))?"
KG_HESAP = [re.compile(SAYI + r"\s*kg\s*[×x*·]\s*" + SAYI + r"\s*" + DOZ_B + r"\s*/\s*kg" + EK_PAYDA + r"\s*(?:=|→|->|eder|olur)\s*"
                       + SAYI + r"\s*" + DOZ_B, re.I),
            re.compile(SAYI + r"\s*" + DOZ_B + r"\s*/\s*kg" + EK_PAYDA + r"\s*[×x*·]\s*" + SAYI + r"\s*kg\s*(?:=|→|->|eder|olur)\s*"
                       + SAYI + r"\s*" + DOZ_B, re.I)]
DERISIM = re.compile(SAYI + r"\s*mg\s*/\s*(?:" + SAYI + r"\s*)?mL", re.I)   # '8 mg/mL' = 8 mg / 1 mL
HACIM_HESAP = re.compile(SAYI + r"\s*mg\s*(?:=|→|için|karşılığı)\s*" + SAYI + r"\s*mL", re.I)
SEYRELTME = re.compile(r"\s*(?:%\s*[\d.,]+\s*)?(?:SF|serum|izotonik|dekstroz|NaCl|içine|içinde|ile\s+sulandır|ile\s+seyrelt|sıvı)", re.I)
BIRIM_KAT = {"g": 1e6, "mg": 1e3, "mcg": 1.0, "µg": 1.0, "μg": 1.0}
BIRIM_DONUSUM = re.compile(SAYI + r"\s*(g|mg|mcg|µg|μg)\s*=\s*" + SAYI + r"\s*(g|mg|mcg|µg|μg)\b")


def _yakin(a: float, b: float) -> bool:
    return abs(a - b) <= ARITMETIK_TOLERANS * max(abs(a), abs(b), 1e-9)


ONDALIK_NOKTA = re.compile(r"decimal point|nokta\s+ondalık|ondalık\s+(?:ayırıcı|ayracı|işareti)\s+(?:olarak\s+)?nokta", re.I)


def sayi_adaylari(s: str, nokta_ondalik: bool = False) -> list[float]:
    """'1.125' Türkçede 1125, İngilizcede 1,125 olabilir: belirsizse iki yorum da döner (ENGEL ancak ikisi de tutmazsa).
    Belge noktanın ondalık olduğunu açıkça söylüyorsa ('decimal point', 'nokta ondalık') yalnız ondalık yorum."""
    s = s.strip()
    if re.fullmatch(r"[1-9]\d{0,2}\.\d{3}", s):
        return [float(s)] if nokta_ondalik else [float(s.replace(".", "")), float(s)]
    return [sayi(s)]


def _herhangi(adaylar, kosul) -> bool:
    import itertools
    return any(kosul(*x) for x in itertools.product(*adaylar))


HACIM_B = {"ml"}


def k_doz_aritmetigi(c, ekle):
    son_derisim, son_no = None, None
    nok = bool(ONDALIK_NOKTA.search(c["tam"]))
    sayi_adaylari_ = functools.partial(sayi_adaylari, nokta_ondalik=nok)
    for st in tarama_satirlari(c):
        t = st["tam"]
        hatali = []
        for desen in KG_HESAP:
            for m in desen.finditer(t):
                g = m.groups()
                if desen is KG_HESAP[0]:
                    kg, doz, b1, sonuc, b2 = g[0], g[1], g[2].lower(), g[3], g[4].lower()
                else:
                    doz, b1, kg, sonuc, b2 = g[0], g[1].lower(), g[2], g[3], g[4].lower()
                b1, b2 = b1.replace("μ", "µ"), b2.replace("μ", "µ")
                k1, k2 = BIRIM_KAT.get(b1), BIRIM_KAT.get(b2)
                ad = [sayi_adaylari_(kg), sayi_adaylari_(doz), sayi_adaylari_(sonuc)]
                ornek = sayi(kg) * sayi(doz)
                if (b1 in HACIM_B) != (b2 in HACIM_B):
                    hatali.append((m.group(0), f"birim uyuşmuyor: {b1}/kg × kg = {b1}, sonuç {b2} yazılmış (derişim olmadan kütle hacme çevrilmez)"))
                elif b1 == b2 and not _herhangi(ad, lambda a, b, s_: _yakin(a * b, s_)):
                    hatali.append((m.group(0), f"{ornek:g} {b1}"))
                elif b1 != b2 and k1 and k2 and not _herhangi(ad, lambda a, b, s_: _yakin(a * b * k1, s_ * k2)):
                    hatali.append((m.group(0), f"{ornek:g} {b1} = {ornek * k1 / k2:g} {b2}"))
        derisimler = list(DERISIM.finditer(t))
        bolumler = [(sayi(d.group(1)), sayi(d.group(2)) if d.group(2) else 1.0,
                     t[d.end():derisimler[i + 1].start() if i + 1 < len(derisimler) else len(t)])
                    for i, d in enumerate(derisimler)]
        if not derisimler and son_derisim and son_no is not None and st["no"] is not None and st["no"] == son_no + 1:
            bolumler = [(son_derisim[0], son_derisim[1], t)]     # derişim bir önceki satırda ('12 mg/mL.' / '36 mg = 30 mL')
        for mg, ml, bolum in bolumler:
            for m in HACIM_HESAP.finditer(bolum):
                if SEYRELTME.match(bolum, m.end()):
                    continue
                ad = [sayi_adaylari_(m.group(1)), sayi_adaylari_(m.group(2))]
                if mg and not _herhangi(ad, lambda z, w: _yakin(z * ml / mg, w)):
                    z = sayi(m.group(1))
                    hatali.append((m.group(0), f"{z:g} mg = {z * ml / mg:g} mL"))
        if derisimler:
            d = derisimler[-1]
            son_derisim = (sayi(d.group(1)), sayi(d.group(2)) if d.group(2) else 1.0)
        son_no = st["no"] if (derisimler or son_no is None or st["no"] != (son_no or 0) + 1) else son_no
        if derisimler:
            son_no = st["no"]
        for m in BIRIM_DONUSUM.finditer(t):
            ba, bb = m.group(2), m.group(4)
            ad = [sayi_adaylari_(m.group(1)), sayi_adaylari_(m.group(3))]
            if ba != bb and not _herhangi(ad, lambda a, b: _yakin(a * BIRIM_KAT[ba], b * BIRIM_KAT[bb])):
                a = sayi(m.group(1))
                hatali.append((m.group(0), f"{a:g} {ba} = {a * BIRIM_KAT[ba] / BIRIM_KAT[bb]:g} {bb}"))
            elif ba != bb and len(ad[0]) * len(ad[1]) > 1 and not all(
                    _yakin(a * BIRIM_KAT[ba], b * BIRIM_KAT[bb]) for a in ad[0] for b in ad[1]):
                ekle("Doğruluk", "UYARI", f"Noktalı sayı iki türlü okunabiliyor («{m.group(0)}»): binlik mi ondalık mı?",
                     "Türkçede ondalık virgülle yazılır (1,125 mg); binlikse 1125 mg yaz", ornek=m.group(0), satir=st["no"])
        for h, dogru in hatali:
            ekle("Doğruluk", "ENGEL", f"Doz hesabı tutmuyor («{h}» → {'' if dogru.startswith('birim') else 'doğrusu '}{dogru})",
                 "Hesabı yeniden yap; sonuç nottaki sayıyla aynı olmalı", ornek=h, satir=st["no"])


def k_cocuk_azami_doz(c, ekle):
    for par in paragraflar(c["tam"]):
        m = MGKG.search(par)
        if m and re.search(r"çocuk|pediatri|bebek|yenidoğan|süt çocuğu|children|pediatric", tr_kucuk(par)) \
                and not re.search(r"en fazla|en çok|maksimum|maks\.?|azami|\bmax\b|geçmeyecek|geçmemeli|tavan|erişkin dozu",
                                  tr_kucuk(par)):
            ekle("Doğruluk", "UYARI", "Çocukta kiloya göre doz var ama en yüksek doz yazılmamış",
                 "Hesaplanan doz genelde erişkin en yüksek dozunu geçmemeli; tavanı kaynağıyla yaz (bpac NZ)", ornek=m.group(0))


PRN = re.compile(r"gerektiğinde|gerekirse\b(?=[^.\n]{0,40}?(?:alınır|verilir|uygulanır|yapılır|tekrarlanır))"
                 r"|ihtiyaç\s+halinde|lüzumu?\s+halinde|ağrı(?:sı)?\s+olursa|ateşi\s+olursa"
                 r"|ateş\s+olursa|\bprn\b|when required", re.I)


def k_prn_talimat(c, ekle):
    for st in tarama_satirlari(c):
        t = st["tam"]
        if PRN.search(t) and DOZ_IZI.search(t) and not re.search(
                r"en az\s+\d+\s*saat|saatte\s+bir|\d+\s*saatte|günde\s+en\s+(?:fazla|çok)|maksimum|azami|en\s+(?:fazla|çok)"
                r"|\bmax\b|\bmaks\b|tavan|\bq\d+h\b|her\s+\d+\s*saat", t, re.I):
            ekle("Doğruluk", "UYARI", "'Gerektiğinde' talimatında doz aralığı ya da günlük en yüksek doz yok",
                 "En kısa doz aralığını ve günlük en yüksek dozu yaz (bpac NZ)", ornek=PRN.search(t).group(0), satir=st["no"])


ANALIT = {"glukoz": ("mg/dl", "mmol/l", "g"), "glikoz": ("mg/dl", "mmol/l", "g"), "kan şekeri": ("mg/dl", "mmol/l", "g"),
          "kolesterol": ("mg/dl", "mmol/l", None), "kreatinin": ("mg/dl", "(?:µ|μ|u)mol/l", "k"),
          "üre": ("mg/dl", "mmol/l", None), "kalsiyum": ("mg/dl", "mmol/l", None), "trigliserit": ("mg/dl", "mmol/l", None),
          "bilirubin": ("mg/dl", "(?:µ|μ|u)mol/l", None), "hemoglobin": ("g/dl", "g/l|mmol/l", None),
          "glucose": ("mg/dl", "mmol/l", "g"), "blood sugar": ("mg/dl", "mmol/l", "g"),
          "creatinine": ("mg/dl", "(?:µ|μ|u)mol/l", "k"), "cholesterol": ("mg/dl", "mmol/l", None),
          "urea": ("mg/dl", "mmol/l", None), "calcium": ("mg/dl", "mmol/l", None),
          "triglyceride": ("mg/dl", "mmol/l", None)}
LAB_IZI = re.compile(r"\d\s*(?:mg/dl|mmol/l|[µμu]mol/l)\b", re.I)
DONUSUM_IZI = re.compile(r"dönüşüm|katsayı|÷\s*18|/\s*18\b|×\s*0[.,]0555|×\s*88[.,]4|88[.,]4", re.I)


def k_lab_birim_karisik(c, ekle):
    belge_donusum = bool(DONUSUM_IZI.search(c["tam"]))
    karisik = []
    for analit, (geleneksel, si, tip) in ANALIT.items():
        sat = [st for st in tarama_satirlari(c) if analit in tr_kucuk(st["tam"])]
        if not sat:
            continue
        g = any(re.search(re.escape(geleneksel), en_kucuk(st["tam"])) for st in sat)
        s_ = any(re.search(si, en_kucuk(st["tam"])) for st in sat)
        esitlik = False
        if tip:
            for st in sat:
                k = en_kucuk(st["tam"])
                bag = r"\s*(=|≈|ya da|veya|yani|\()\s*"
                for yon, desen in ((1, SAYI + r"\s*" + re.escape(geleneksel) + bag + SAYI + r"\s*(?:" + si + ")"),
                                   (-1, SAYI + r"\s*(?:" + si + ")" + bag + SAYI + r"\s*" + re.escape(geleneksel))):
                    for m in re.finditer(desen, k):
                        esitlik = True
                        a, b = sayi(m.group(1)), sayi(m.group(3))
                        if yon == 1:
                            beklenen = a * 88.4 if tip == "k" else a / 18.0
                        else:
                            beklenen = a / 88.4 if tip == "k" else a * 18.0
                        if not _yakin(beklenen, b) and abs(beklenen - b) > 0.15:
                            duzey = "UYARI" if m.group(2) in ("ya da", "veya") else "ENGEL"
                            ekle("Doğruluk", duzey, f"Birim dönüşümü tutmuyor («{m.group(0)}» → yaklaşık {round(beklenen, 2)})",
                                 "Glukoz: mg/dL ÷ 18 = mmol/L; kreatinin: mg/dL × 88,4 = µmol/L"
                                 + (" ('ya da' iki ayrı eşik de olabilir; dönüşümse düzelt)" if duzey == "UYARI" else ""),
                                 ornek=m.group(0), satir=st["no"])
        if g and s_ and not belge_donusum and not esitlik:
            karisik.append(analit)
    if karisik:
        ekle("Doğruluk", "UYARI", f"Aynı analit iki birimle ve dönüşüm yazılmadan ({', '.join(karisik)})",
             "Tek birim kullan ya da dönüşüm katsayısını yaz (ör. glukoz mg/dL ÷ 18 = mmol/L)")


def k_referans_kaynaksiz(c, ekle):
    yok = [x.strip() for x in cumleler(c["gor"])
           if re.search(r"referans aralı|normal değer|normal aralı|reference range", x, re.I)
           and not re.search(r"kaynak|laboratuvar|\(\w[^()]*\d{4}\)|\[\d+\]", x, re.I)]
    if yok:
        ekle("Doğruluk", "UYARI", f"Referans aralığı kaynaksız ({len(yok)} yer)",
             "Aralık laboratuvara, yönteme, yaşa ve cinsiyete göre değişir; kaynağını ve geçerli grubu yaz", ornek=yok[0])


def k_gebelik_kategorisi(c, ekle):
    if "veteriner" in c["alanlar"]:
        return
    m = re.search(r"gebelik\s+kategori\w*\s*[:：]?\s*[ABCDX]\b|kategori\s+[ABCDX]\b[^.\n]*gebe|pregnancy\s+category\s+[ABCDX]\b",
                  c["gor"], re.I)
    if m:
        ekle("Doğruluk", "UYARI", "Harfli gebelik kategorisi (A/B/C/D/X) kullanılmış",
             "FDA bu harfleri insan reçeteli ilaç etiketinden 2015'te (PLLR) kaldırdı; hangi sistemi kullandığını yaz ya da "
             "güncel prospektüsün gebelik/emzirme bölümünü özetle", ornek=m.group(0))


ESKI_SURUM = [(re.compile(r"\bDSM[- ]?(?:III|IV)(?:-TR)?\b"), "DSM-IV/III", "DSM-5-TR (2022)", r"DSM[- ]?5")]


def k_tani_surumu_eski(c, ekle):
    for desen, ad, yeni, guncel in ESKI_SURUM:
        m = desen.search(c["gor"])
        if m and not re.search(guncel, c["gor"]):
            ekle("Doğruluk", "UYARI", f"Eski tanı sistemi sürümü: {ad}", f"Güncel sürüm {yeni}; tarihçe değilse güncelle",
                 ornek=m.group(0))


KURUM = r"(?:ESC|ESH|AHA|ACC|ERC|ILCOR|GINA|GOLD|KDIGO|ADA|NICE|WHO|DSÖ|IDSA|EULAR|ACR|NCCN|ASCO|TKD|TTD)"
YILLIK = {"GINA", "GOLD", "ADA"}
KILAVUZ_YIL = re.compile(r"\b(" + KURUM[3:-1] + r")\b[^.\n]{0,25}?\b(19\d{2}|20\d{2})\b"
                         r"|\b(19\d{2}|20\d{2})\b\s*(?:yılı\s*)?(?:tarihli\s*)?\b(" + KURUM[3:-1] + r")\b")
TARIHCE = re.compile(r"karşılaştır|önceki sürüm|eski sürüm|yerine geçt|güncellendi|tarihçe|ilk kez|ilk yayın|değişti", re.I)


def k_kilavuz_eski(c, ekle):
    eski = []
    for p in paragraflar(c["gor"]):
        for cm in cumleler(p):
            if TARIHCE.search(cm):
                continue
            for m in KILAVUZ_YIL.finditer(cm):
                kurum = m.group(1) or m.group(4)
                yil = int(m.group(2) or m.group(3))
                sinir = KILAVUZ_YAS_YILLIK if kurum in YILLIK else KILAVUZ_YAS
                if yil <= c["yil"] and c["yil"] - yil > sinir:
                    eski.append(f"{kurum} {yil}")
    if eski:
        ekle("Doğruluk", "UYARI", f"Kılavuzun güncelliği doğrulanmalı ({', '.join(sorted(set(eski))[:3])})",
             f"Güncel sürümü kontrol et; eski sürümü bilerek kullanıyorsan nedenini yaz (yerel tarama politikası: "
             f"{KILAVUZ_YAS} yıl, yıllık raporlarda {KILAVUZ_YAS_YILLIK} yıl; değerlendirme yılı {c['yil']})",
             ornek=eski[0].split()[0])


def k_kilavuz_yilsiz(c, ekle):
    yilsiz = [cm.strip() for cm in cumleler(c["gor"])
              if re.search(r"\b" + KURUM + r"\b[^.\n]{0,30}(?:kılavuz|guideline|rehber|raporu|konsensüs)"
                           r"|(?:[A-ZÇĞİÖŞÜ][a-zçğıöşü]+\s+){1,3}(?:Derneği|Cemiyeti|Bakanlığı)\s+(?:kılavuz|rehber)", cm)
              and not YIL.search(cm)]
    if yilsiz:
        ekle("Doğruluk", "UYARI", f"Kılavuz adı var ama yılı yok ({len(yilsiz)} yer)",
             "Kılavuzun adını ve sürüm yılını yaz; güncelliğini kontrol et", ornek=yilsiz[0][:40])


def tc_gecerli(n: str) -> bool:
    """TC kimlik numarası sağlaması: 10. hane = ((tekler×7) − çiftler) mod 10, 11. hane = ilk 10 hanenin toplamı mod 10.
    Sağlamaya uyan sayıların gerçek kişiye ait olduğunu KANITLAMAZ; rastgele 11 hanenin yaklaşık %1'i de uyar."""
    d = [int(x) for x in n]
    return (len(d) == 11 and d[0] != 0 and ((sum(d[0:9:2]) * 7 - sum(d[1:8:2])) % 10) == d[9]
            and sum(d[:10]) % 10 == d[10])


AD = r"(?:[A-ZÇĞİÖŞÜ][a-zçğıöşü]+|[A-ZÇĞİÖŞÜ]{2,})"
AD_DEGIL = {"genel", "durumu", "durum", "iyi", "kötü", "akut", "kronik", "erkek", "kadın", "yaşında", "bilinç", "açık",
            "kapalı", "stabil", "örnek", "kişi", "hasta", "vaka", "olgu", "tanı", "tedavi", "takip", "bulgular", "öykü",
            "şikâyet", "şikayet", "başvuru", "acil", "servis", "yoğun", "bakım", "taburcu", "yatış", "astım", "atağı",
            "pnömoni", "otuz", "kırk", "elli", "altmış", "yetmiş", "seksen", "yirmi", "on", "iki", "yaşlı", "genç",
            "boşluk", "öğrenci", "no", "numara", "numarası", "sağ", "sol", "ağrı", "ateş", "build", "and", "test", "john",
            "smith", "jane", "doe"}
AD_ETIKET = (r"(?i:\b(?:hasta(?:nın)?\s+(?:ad[ıi]|ismi|isim)(?:\s*(?:/|ve)?\s*soyad[ıi])?|hasta\s+adı\s*/\s*soyadı"
             r"|ad[ıi]?\s+soyad[ıi]?|patient\s+name|hasta|vaka|patient))")
HASTA_AD = re.compile(AD_ETIKET + r"[ \t]*[:：][ \t]*(" + AD + r"(?:[ \t]+" + AD + r"){1,2})")
# Açık etiketten sonra küçük harfle yazılmış ad ('Hasta adı: ayşe yılmaz'); çıplak 'hasta' etiketi burada sayılmaz.
HASTA_AD_KUCUK = re.compile(r"(?i:\b(?:hasta(?:nın)?\s+(?:ad[ıi]|ismi|isim)(?:\s*(?:/|ve)?\s*soyad[ıi])?|ad[ıi]?\s+soyad[ıi]?"
                            r"|patient\s+name))[ \t]*[:：][ \t]*([a-zçğıöşü]{2,}[ \t]+[a-zçğıöşü]{2,}(?:[ \t]+[a-zçğıöşü]{2,})?)\b")
HASTA_AD_VIRGUL = re.compile(r"(?i:\bhasta)[ \t]+(" + AD + r"[ \t]+" + AD + r")[ \t]*,[ \t]*\d{1,3}[ \t]*yaşında")
HASTA_BAS_HARF = re.compile(AD_ETIKET + r"[ \t]*[:：][ \t]*([A-ZÇĞİÖŞÜ]\.[ \t]*" + AD + r")")
PROTOKOL_KESIN = re.compile(r"(?i:\b(?:protokol|mrn|hbys)\s*(?:no|numarası|nr)?\.?)[ \t]*[:：]?[ \t]*([A-Z]{0,3}-?\d{4,})(?![/\d])")
PROTOKOL_VAKA = re.compile(r"(?i:\b(?:dosya|hasta|kayıt|arşiv|yatış)\s*(?:no|numarası|nr)\.?)[ \t]*[:：]?[ \t]*([A-Z]{0,3}-?\d{4,})(?![/\d])")
AYLAR = (r"(?:ocak|şubat|mart|nisan|mayıs|haziran|temmuz|ağustos|eylül|ekim|kasım|aralık|january|february|march|april"
         r"|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sept?|oct|nov|dec)\.?")
DOGUM = re.compile(r"(?i:\bdoğum\s+tarihi|\bd\.\s?t\.|\bdt\b|date of birth|\bdob\b)[ \t]*[:：]?[ \t]*"
                   r"(\d{1,2}[./-]\d{1,2}[./-](\d{2,4})|\d{1,2}[ \t]+" + "(?i:" + AYLAR + r")[ \t]+(\d{4})"
                   r"|(\d{4})-\d{1,2}-\d{1,2})")
YATIS = re.compile(r"(?i:yatış|taburcu|başvuru|muayene)\s+tarihi\s*[:：]?\s*\d{1,2}[./-]\d{1,2}[./-]\d{4}")
TELEFON = re.compile(r"(?:\+90|\b0)\s*5\d{2}[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}\b")
EPOSTA = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b")
KURMACA = re.compile(r"(?:kurmaca|sentetik|hayali|temsili|uydurma)\s+(?:bir\s+)?(?:vaka|hasta|olgu|isim|ad\b|kişi)"
                     r"|(?:vaka|hasta|olgu|isim|ad|kişi)\w*\s+(?:kurmacadır|kurmaca|hayalidir|temsilidir|uydurmadır)"
                     r"|örnek isim|gerçek kişi değil|fictional|synthetic patient", re.I)
VAKA_BAGLAM = re.compile(r"hasta(?!ne)|vaka|olgu|patient|klinik|servis|poliklinik|yatış|tanı", re.I)   # 'hastane' vaka değil
TC_ETIKET = re.compile(r"(?i:\bt\.?\s?c\.?(?:\s*kimlik)?(?:\s*(?:no|numarası))?\.?|\btckn|kimlik\s+(?:no|numarası))"
                       r"[ \t]*[:：]?[ \t]*((?:\d[ \t.-]?){11})")
TC_GRUPLU = re.compile(r"(?<![\d.-])\d{3}[ .-]\d{3}[ .-]\d{3}[ .-]\d{2}(?![\d.-])")


def _maskele(s: str) -> str:
    return re.sub(r"(?<=\w)\w", "*", s)


KLINIK_KOK = ("ağrı", "diyabet", "mellitus", "klinik", "tablo", "grup", "göğüs", "karın", "nefes", "solunum", "sinüs",
              "ritim", "ritm", "normal", "stabil", "tanı", "sendrom", "hastalı", "yetmez", "enfeksiyon", "kanser", "tümör",
              "travma", "sepsis", "hipertansiyon", "hipotansiyon", "hipoglisemi", "hiperglisemi", "akciğer", "böbrek",
              "karaciğer", "beyin", "öksürük", "bulantı", "kusma", "ishal", "pediatri", "erişkin", "miyokard", "enfarkt",
              "pankreat", "apandisit", "kolesist", "pnömotoraks", "anemi", "lösemi", "lenfoma", "hepatit", "gastrit",
              "menenjit", "bronş", "nefrit", "sistit", "artrit", "dermatit", "astım", "pnömoni")
AD_OLABILIR = {"ateş", "genç"}   # sözlükte klinik/genel ama soyadı ya da ad da olabilen sözcükler
# Ad olabilen kökler (Başak, Belgin, Ateş, Kalp değil) kök listesine alınmaz; yalnız tam sözcük olarak AD_DEGIL'de.
AD_DEGIL |= {"not", "recorded", "unknown", "withheld", "redacted", "anonymous", "kayıt", "dışı", "yok", "bilinmiyor",
             "belirtilmedi", "belirtilmemiş", "gizli", "gizlendi", "maskelendi", "anonim", "silindi", "yazılmadı", "none",
             "yüksek", "düşük", "baş", "bel", "kalp", "şok", "gebe", "kırık", "kontrol", "yeni", "doğum", "ağrısı", "çocuk", "bebek"}


def _ad_mi(ad: str) -> bool:
    sozcukler = [tr_kucuk(w) for w in ad.split()]
    if any(w.startswith(KLINIK_KOK) for w in sozcukler):
        return False
    return not any(w in AD_DEGIL and w not in AD_OLABILIR for w in sozcukler)


def paragraf_bayragi(c, desen) -> dict:
    """id(satır) → o satırın paragrafında desen geçiyor mu. Boş satır paragraf ayırır (PDF metninde de)."""
    bayrak, grup = {}, []
    for x in c["satirlar"] + [{"no": None, "tam": ""}]:
        if x["tam"].strip():
            grup.append(x)
            continue
        var = any(desen.search(y["tam"]) for y in grup)
        for y in grup:
            bayrak[id(y)] = var
        grup = []
    return bayrak


def k_hasta_kimlik(c, ekle):
    """Ortak çekirdek: her alanda (HIPAA Safe Harbor tanımlayıcıları; kimliksizleştirme yönetmeliği)."""
    paragraf_kurmaca = paragraf_bayragi(c, KURMACA)
    paragraf_vaka = paragraf_bayragi(c, VAKA_BAGLAM)
    saglik = bool(c["alanlar"] & SAGLIK_ALANLAR)
    satirlar = tarama_satirlari(c)
    for st in satirlar:
        t, no = st["tam"], st["no"]
        kurmaca = paragraf_kurmaca.get(id(st), bool(KURMACA.search(t)))
        duzey = "UYARI" if kurmaca else "ENGEL"
        not_ = " — kurmaca olarak belirtilmiş" if kurmaca else ""
        for desen in (HASTA_AD, HASTA_AD_VIRGUL, HASTA_AD_KUCUK):
            for m in desen.finditer(t):
                if _ad_mi(m.group(1)):
                    c["maske"].add(m.group(1))
                    ekle("Doğruluk", duzey, f"Vakada hasta adı ({_maskele(m.group(1))}){not_}",
                         "Adı çıkar; yaş ve cinsiyetle anlat ('58 yaşında erkek hasta')", ornek=m.group(1), satir=no)
        for m in HASTA_BAS_HARF.finditer(t):
            c["maske"].add(m.group(1))
            ekle("Doğruluk", "UYARI", f"Vakada baş harf + soyadı ({_maskele(m.group(1))})",
                 "Soyadı da tanıtıcıdır; yalnız yaş ve cinsiyet kullan", ornek=m.group(1), satir=no)
        protokoller = list(PROTOKOL_KESIN.finditer(t))
        if VAKA_BAGLAM.search(t) or c["alanlar"] & SAGLIK_ALANLAR:
            protokoller += list(PROTOKOL_VAKA.finditer(t))
        for m in protokoller:
            c["maske"].add(m.group(1))
            ekle("Doğruluk", duzey, f"Vakada protokol/dosya numarası{not_}", "Numarayı çıkar", ornek=m.group(1), satir=no)
        vaka = paragraf_vaka.get(id(st), bool(VAKA_BAGLAM.search(t)))
        for m in DOGUM.finditer(t):
            yil = m.group(2) or m.group(3) or m.group(4) or ""
            yil = (int(yil) + (2000 if int(yil) <= c["yil"] % 100 else 1900) if len(yil) == 2 else int(yil)) if yil.isdigit() else 0
            if yil and yil < 1930 and not vaka:
                continue          # tarihsel kişi (vaka bağlamı yok)
            c["maske"].add(m.group(1))
            if vaka or saglik:
                ekle("Doğruluk", duzey, f"Vakada tam doğum tarihi{not_}", "Tam tarihi çıkar; yaşı yaz", ornek=m.group(1), satir=no)
            else:
                ekle("Doğruluk", "UYARI", "Tam doğum tarihi (vaka bağlamı yok; biyografiyse sorun değil)",
                     "Gerçek bir öğrenci/hasta değilse yoksay; kişisel veriyse çıkar", ornek=m.group(1), satir=no)
        for m in YATIS.finditer(t):
            ekle("Doğruluk", "UYARI", "Vakada tam yatış/başvuru tarihi", "Yalnız yıl ya da göreli süre yaz ('3. gün')",
                 ornek=m.group(0), satir=no)
    for par in paragraflar(c["tam"]):
        if not VAKA_BAGLAM.search(par):
            continue
        for desen, ad in ((TELEFON, "telefon numarası"), (EPOSTA, "e-posta adresi")):
            m = desen.search(par)
            if m:
                ekle("Doğruluk", "UYARI", f"Vakada {ad}", "Kişisel iletişim bilgisi öğrenci materyaline girmez", ornek=m.group(0))


KIMLIK_BAGLAM = re.compile(r"hasta|öğrenci|kimlik|vaka|olgu|patient|student|vatandaş|nüfus|kişi|başvur|kayıt|tc\b|t\.c\.",
                           re.I)


def k_tc_kimlik(c, ekle):
    """Etiketli ('TC:') ya da 3-3-3-2 gruplu aday: ENGEL. Etiketsiz 11 hane: aynı paragrafta kişi/kimlik bağlamı varsa
    ENGEL, yoksa UYARI (rastgele 11 hanenin ~%1'i sağlamaya uyar; 22.11.2026 kararı, seçenek b)."""
    gorulen = set()
    paragraf = paragraf_bayragi(c, KIMLIK_BAGLAM)
    for st in tarama_satirlari(c):
        t = st["tam"]
        etiketli = [re.sub(r"\D", "", m.group(1)) for m in TC_ETIKET.finditer(t)]
        etiketli += [re.sub(r"\D", "", m.group(0)) for m in TC_GRUPLU.finditer(t)]
        ciplak = re.findall(r"(?<![\w-])[1-9]\d{10}(?![\w-])", t)   # karma/kod içindeki rakam dizisi değil
        sentetik = bool(re.search(r"sentetik|algoritma|sağlama|uydurma numara|örnek numara|maskeli", t, re.I))
        baglam = paragraf.get(id(st), bool(KIMLIK_BAGLAM.search(t)))
        for n, etiket in [(x, True) for x in etiketli] + [(x, False) for x in ciplak]:
            if len(n) == 11 and tc_gecerli(n) and n not in gorulen:
                gorulen.add(n)
                c["maske"].add(n)
                engel = not sentetik and (etiket or baglam)
                neden = (" (sağlama/sentetik örnek bağlamında)" if sentetik else
                         "" if engel else " (etiketsiz ve kişi bağlamı yok; ölçüm/kod numarası olabilir)")
                ekle("Doğruluk", "ENGEL" if engel else "UYARI", "TC kimlik sağlamasına uyan sayı" + neden,
                     "Numarayı sil; algoritma öğretiyorsan sağlamaya uymayan maskeli örnek kullan (1234567****)",
                     ornek=n, satir=st["no"])


CINSLER = (r"Escherichia|Staphylococcus|Streptococcus|Mycobacterium|Salmonella|Pseudomonas|Klebsiella|Candida|"
                   r"Plasmodium|Helicobacter|Clostridium|Clostridioides|Bacillus|Homo|Drosophila|Saccharomyces|Arabidopsis|"
                   r"Enterococcus|Neisseria|Listeria|Treponema|Toxoplasma|Giardia|Aspergillus|Acinetobacter|Proteus|Enterobacter|"
                   r"Serratia|Haemophilus|Bordetella|Legionella|Shigella|Vibrio|Campylobacter|Corynebacterium|Borrelia|"
                   r"Chlamydia|Trichomonas|Leishmania|Entamoeba|Cryptococcus|Pneumocystis|Toxocara|Echinococcus|Taenia|"
                   r"Ascaris|Canis|Felis|Bos|Equus|Rattus|Mus|Ovis|Capra|Gallus|Sus|Triticum|Zea|Oryza")
BINOM = re.compile(r"\b(" + CINSLER + r")\s+([A-Za-z]+)")
BINOM_DUZ = re.compile(r"(?<![*_\w])(?:" + CINSLER + r")\s+[a-z]{3,}(?![*_\w])")
BINOM_KUCUK = re.compile(r"(?<![\w.])(escherichia|staphylococcus|streptococcus|mycobacterium|salmonella|pseudomonas|"
                         r"klebsiella|candida|plasmodium|helicobacter|acinetobacter|enterococcus)\s+[a-z]+")
BITISIK_KISALTMA = re.compile(r"\b([A-Z])\.(coli|aureus|pneumoniae|pylori|albicans|tuberculosis|sapiens|melanogaster|baumannii)\b")


def k_tur_adi_yazimi(c, ekle):
    hatali = [f"{a} {b}" for a, b in BINOM.findall(c["gor"]) if b[:1].isupper()]
    hatali += BINOM_KUCUK.findall(c["gor"])
    hatali += [f"{a}.{b}" for a, b in BITISIK_KISALTMA.findall(c["gor"])]
    if hatali:
        ekle("Doğruluk", "UYARI", f"Tür adı yazımı ({', '.join(sorted(set(hatali))[:3])})",
             "Cins büyük, tür küçük harfle ve italik: *Escherichia coli*, kısaltırken *E. coli* (noktadan sonra boşluk)",
             ornek=hatali[0])
    duz = BINOM_DUZ.findall(c["govde_kodsuz"])
    if duz and not hatali:
        ekle("Doğruluk", "UYARI", f"Tür adı italik değil ({', '.join(sorted(set(duz))[:2])})",
             "Bilimsel adı italik yaz: *Escherichia coli* (ICZN)", ornek=duz[0])


VET_TUR = re.compile(r"köpek|kedi|\bat\b|atlar|sığır|koyun|keçi|domuz|tavuk|kanatlı|tavşan|kemirgen|buzağı|kuzu|"
                     r"equine|canine|feline|bovine", re.I)


def k_vet_tursuz_doz(c, ekle):
    tursuz = [x.strip()[:50] for x in cumleler(c["tam"])
              if re.search(r"\d\s*(?:mg|mcg|mL|ml)\s*/\s*kg", x, re.I) and not VET_TUR.search(x)]
    if tursuz:
        ekle("Doğruluk", "UYARI", f"Türü belirtilmemiş doz ({len(tursuz)}; ilki: «{tursuz[0]}»)",
             "Doz türe göre değişir (ör. kedide parasetamol toksik); her dozun yanına hayvan türünü yaz", ornek=tursuz[0])
    if re.search(r"\b(?:sığır|koyun|keçi|tavuk|kanatlı|domuz|süt|yumurta)\b", c["gor"], re.I) and \
            re.search(r"\d\s*(?:mg|mL|ml)\s*/\s*kg", c["tam"], re.I) and not re.search(r"arınma|bekleme süresi|withdrawal", c["gor"], re.I):
        ekle("Doğruluk", "UYARI", "Gıda hayvanında ilaç dozu var ama arınma (bekleme) süresi yok",
             "Et/süt/yumurta için arınma süresini yaz")


def k_beslenme_birim(c, ekle):
    m = re.search(r"\d\s*kalori\b", c["gor"], re.I)
    if m:
        ekle("Doğruluk", "UYARI", "Enerji 'kalori' diye yazılmış", "Besin enerjisi kcal (ya da kJ) ile yazılır: '2000 kcal'",
             ornek=m.group(0))


SAGLIK_BEYANI = re.compile(r"(?:kanser|diyabet|şeker hastalığı|tansiyon|hastalığ\w*|enfeksiyon)\w*\s+(?:\w+\s+){0,3}"
                           r"(?:tedavi eder|iyileştirir|önler|geçirir|yok eder|şifa)", re.I)


def k_saglik_beyani(c, ekle):
    b = SAGLIK_BEYANI.findall(c["gor"])
    if b:
        ekle("Doğruluk", "UYARI", f"Besine hastalık tedavi/önleme özelliği yükleniyor ({len(b)} yer)",
             "Gıdaya hastalığı önleme/tedavi etme özelliği atfetmek beyan mevzuatında yasak; kanıtı ve kaynağı yaz, "
             "ifadeyi 'X ile ilişkili bulundu (kaynak)' diye daralt", ornek=b[0])


def k_bakim_plani(c, ekle):
    if re.search(r"bakım planı|hemşirelik süreci", c["gor"], re.I):
        eksik = [ad for ad, d in [("tanı", r"hemşirelik tanısı|tanı\s*[:：]"), ("amaç/hedef", r"amaç|hedef|beklenen sonuç"),
                                  ("girişim", r"girişim|uygulama"), ("değerlendirme", r"değerlendirme")]
                 if not re.search(d, c["gor"], re.I)]
        if eksik:
            ekle("Sıra ve akış", "UYARI", f"Bakım planında aşama eksik: {', '.join(eksik)}",
                 "Hemşirelik süreci: veri toplama → tanı → amaç → girişim → değerlendirme")


def k_egzersiz_recetesi(c, ekle):
    recete = [x for x in cumleler(c["gor"]) if re.search(r"egzersiz|germe|kuvvetlendirme", x, re.I) and re.search(r"\d", x)]
    if recete:
        tum = " ".join(recete)
        eksik = [ad for ad, d in [("sıklık", r"günde|haftada|kez|gün"), ("yoğunluk", r"yoğunluk|%|rpe|borg|kg|direnç|ağırlık"),
                                  ("süre/tekrar", r"dakika|dk|saniye|sn|tekrar|set"), ("tip", r"aerobik|izometrik|germe|kuvvet|denge")]
                 if not re.search(d, tum, re.I)]
        if len(eksik) >= 2:
            ekle("Ezber ve kavrama", "UYARI", f"Egzersiz reçetesinde FITT öğesi eksik: {', '.join(eksik)}",
                 "Sıklık, yoğunluk, süre (set × tekrar) ve tipi yaz", ornek=recete[0][:40])


# ── Ortak eğitim kontrolleri ──
KISALTMA = re.compile(r"(?<![\w.])([A-ZÇĞİÖŞÜ][A-ZÇĞİÖŞÜ0-9]{1,5})(?![\w.])")
ROMA = re.compile(r"^[IVXLCDM]+$")
BILINEN = {"TL", "ABD", "AB", "TC", "BM", "NATO", "DNA", "RNA", "ATP", "PDF", "SI", "OK", "TV", "MÖ", "MS", "TDK",
           "TBMM", "UYARI", "HATA", "NOT", "KİM", "FİİL", "GERİSİ", "ENGEL",
           "EKG", "EEG", "EMG", "MR", "MRG", "BT", "USG", "PET", "TSH", "CRP", "INR", "ALT", "AST", "GGT", "LDH", "HDL",
           "LDL", "IV", "IM", "PO", "HIV", "HPV", "HBV", "HCV", "COVID", "WHO", "DSÖ", "ICD", "DSM", "SPO2", "KOAH", "BMI",
           "UV", "IR", "NADH", "NADPH", "ADP", "AMP", "PCR", "CPU", "GPU", "RAM", "ROM", "API", "SQL", "HTML", "CSS", "URL",
           "HTTP", "HTTPS", "JSON", "XML", "USB", "GPS", "ISO", "TS", "EN", "IUPAC", "GHS", "TÜİK", "TCMB", "AYM", "HMK",
           "TBK", "TMK", "TCK", "CMK", "TTK", "İİK", "FDI", "ISMP", "FDA", "NANDA", "OSCE", "KPR", "ABCDE"}


def _bas_harfler_tutuyor(k: str, sonra: str) -> bool:
    harfler = [w[0] for w in re.findall(r"[^\W\d_]+", sonra)[:len(k) + 2]]
    return "".join(harfler).upper().startswith(k[:2].upper())


def k_kisaltma_tanimsiz(c, ekle):
    sayac = {}
    for k in KISALTMA.findall(c["gor"]):
        if not ROMA.match(k) and k not in BILINEN and sum(ch.isalpha() for ch in k) >= 2:
            sayac[k] = sayac.get(k, 0) + 1
    tanimsiz = []
    for k, n in sayac.items():
        if n < 2:
            continue
        e = re.escape(k)
        if re.search(r"\(\s*" + e + r"\s*[),;]|(?<!\w)" + e + r"\s*\(", c["gor"]):
            continue
        tanim = re.search(r"(?<!\w)" + e + r"\s*(?:[:=]|–|—)\s*([^\n.]{3,60})", c["gor"])
        if tanim and _bas_harfler_tutuyor(k, tanim.group(1)):
            continue
        tanimsiz.append(k)
    if len(tanimsiz) >= KISALTMA_ESIK:
        ekle("Seviye", "UYARI", f"Tanımsız kısaltma ({len(tanimsiz)}: {', '.join(sorted(tanimsiz)[:5])})",
             "İlk geçtiği yerde açılımını yaz: 'Ayırıcı tanı (AT)' ya da başa Kısaltmalar listesi koy", ornek=sorted(tanimsiz)[0])


ORNEK = re.compile(r"(?:^|\n)\s*(?:#+\s*|[-*]\s*)?(?:çözülmüş\s+)?(?:örnek|örnek vaka|vaka|çözüm|example)\s*\d*\s*[:：.)]"
                   r"|^#+[^\n]*\b(?:örnek|çözüm|vaka)|çözülmüş örnek|worked example", re.I | re.M)
CEVAP_BASLIK = re.compile(r"^#+[^\n]*\b(?:cevap|cevaplar|yanıt|çözüm|çözümler|answer)", re.I | re.M)


def k_cozulmus_ornek(c, ekle):
    if c["tur"] in SINAMA_ISTEYEN and not ORNEK.search(c["gor"]):
        ekle("Sıra ve akış", "UYARI", "Çözülmüş örnek (ya da örnek vaka) yok",
             "Kuraldan hemen sonra adım adım çözülmüş bir örnek koy; sonra yarım çözümlü, sonra çözümsüz")


def k_cevapsiz_alistirma(c, ekle):
    """Soru–cevap kapsamı: soruların kaçının cevabı var? (IES: düzeltici geri bildirim)"""
    sorular = len(re.findall(r"\bsoru\s*\d+", c["gor"], re.I)) or len(re.findall(r"\?\s*$", c["gor"], re.M))
    if sorular == 0:
        return
    satir_ici = len(re.findall(r"\b(?:cevap|yanıt|çözüm|answer)\s*\d*\s*[:：]", c["gor"], re.I))
    bolum = 0
    for baslik, icerik in bolumler(c["govde"]):
        if CEVAP_BASLIK.match(baslik or ""):
            bolum += len(re.findall(r"(?:^|\s)\d+[.)]\s|^\s*[-*]\s|^\s*\d+\s*[-–:]", icerik, re.M)) or (1 if icerik.strip() else 0)
    cevaplar = max(satir_ici, bolum)
    if cevaplar == 0:
        ekle("Kendini sınama", "UYARI", f"{sorular} soru var ama cevap ya da çözüm yok",
             "Cevap anahtarını ya da çözüm adımlarını ayrı bir bölüme koy")
    elif sorular >= 2 and cevaplar < sorular:
        ekle("Kendini sınama", "UYARI", f"{sorular} sorudan yalnız {cevaplar}'inin cevabı görünüyor",
             "Her soruya cevap ya da çözüm adımı ekle; cevapları numarayla eşleştir")


DIS_SAYI = re.compile(r"(\d{1,2})\s*(?:numaralı|nolu|no['’]lu|no\.?)\s*diş|\bdiş\s*(?:no\.?|numarası)?\s*:?\s*#?(\d{1,2})\b"
                      r"|#(\d{1,2})\b", re.I)


def k_dis_numara_karisik(c, ekle):
    fdi, universal = set(), set()
    for m in DIS_SAYI.finditer(c["gor"]):
        no = next(g for g in m.groups() if g)
        n = int(no)
        if m.group(3) or not (10 < n < 90 and 1 <= n // 10 <= 8 and 1 <= n % 10 <= 8):
            universal.add(no)
        else:
            fdi.add(no)
    if fdi and universal:
        ekle("Doğruluk", "UYARI", f"Diş numaralama karışık: FDI gibi ({', '.join(sorted(fdi)[:3])}) ve "
             f"Universal gibi ({', '.join(sorted(universal)[:3])})",
             "Tek sistem seç (FDI/ISO 3950 ya da Universal), adını belgenin başına yaz")


OTORITE = re.compile(r"(?:tarihçilere|uzmanlara|araştırmacılara|bilim insanlarına|bazı kaynaklara|kaynaklara|çalışmalara)\s+göre"
                     r"|bilindiği üzere|herkesçe bilin|kesin olarak bilinmektedir|genel(?:likle)? kabul edil", re.I)
ATIF = re.compile(r"\([^()]*\d{4}[^()]*\)|\[\d+\]")


def k_kaynaksiz_otorite(c, ekle):
    n = [m.group(0) for s in cumleler(c["gor"]) for m in OTORITE.finditer(s) if not ATIF.search(s)]
    if n:
        ekle("Doğruluk", "UYARI", f"Kaynağı belirsiz otorite ({len(n)}: {', '.join(sorted(set(n))[:3])})",
             "Kimin söylediğini ve kaynağını yaz (yazar, yıl) ya da ifadeyi çıkar", ornek=n[0])


KAYNAKCA_BASLIK = re.compile(r"^#+\s*(?:kaynak|kaynakça|kaynaklar|bibliyografya|references)\b", re.I)
KAYNAK_IZI = re.compile(r"kaynak(?:ça|lar)?\s*[:：]\s*\S|\([A-ZÇĞİÖŞÜ][^()]*\d{4}[^()]*\)", re.I)


def k_kaynakca_yok(c, ekle):
    if c["tur"] == "pano":
        return
    kaynakca = [(b, i) for b, i in bolumler(c["govde"]) if KAYNAKCA_BASLIK.match(b or "")]
    girdiler = sum(len([s for s in i.splitlines() if re.search(r"[^\W\d_]{3,}", s)]) for _, i in kaynakca)
    numaralar = set(re.findall(r"\[(\d+)\]", c["gor"]))
    if kaynakca and girdiler == 0:
        ekle("Doğruluk", "UYARI", "Kaynakça başlığı var ama içi boş", "Kaynak künyelerini yaz")
    elif not kaynakca and not KAYNAK_IZI.search(c["gor"]) and not numaralar:
        ekle("Doğruluk", "UYARI", "Hiç kaynak gösterilmemiş", "Sonuna kaynakça ya da konu yanına (yazar, yıl) ekle")
    if numaralar:
        liste = "\n".join(i for _, i in kaynakca)
        eksik = sorted((n for n in numaralar if not re.search(r"(?:^|\n)\s*\[?" + n + r"[\].)]", liste)), key=int)
        if eksik:
            ekle("Doğruluk", "UYARI", f"Metindeki atıfın kaynakçada karşılığı yok ([{'], ['.join(eksik[:5])}])",
                 "Her [n] atıfına kaynakçada aynı numaralı bir künye yaz", ornek=f"[{eksik[0]}]")


def k_yuzyil_yazimi(c, ekle):
    roma = re.search(r"\b[XVI]+\.\s*(?:yüzyıl|yy)", c["gor"])
    arap = re.search(r"\b\d{1,2}\.\s*(?:yüzyıl|yy)", c["gor"])
    if roma and arap:
        ekle("Ezber ve kavrama", "UYARI", f"Yüzyıl yazımı karışık ({roma.group(0)} ve {arap.group(0)})",
             "Belge boyunca tek yazım kullan", ornek=arap.group(0))


VERI = re.compile(r"(?<![\d.,])\d[\d.,]*\s*(?:%|km²|km2|kişi|ton|milyon|milyar|mm\b|°c|hektar|dekar|m³)|%\s*\d|nüfus[^.\n]*\d", re.I)


def k_veri_yilsiz(c, ekle):
    yilsiz = [s.strip() for s in cumleler(c["gor"]) if VERI.search(s) and not YIL.search(s)]
    if len(yilsiz) >= VERI_YILSIZ_ESIK:
        ekle("Doğruluk", "UYARI", f"Yılı ve kaynağı olmayan sayısal veri ({len(yilsiz)} cümle; ilki: «{yilsiz[0][:60]}»)",
             "Veriyi yılı ve kaynağıyla ver (ör. TÜİK, 2024)", ornek=yilsiz[0][:40])


HARITA_OGELERI = [("lejant", r"lejant|açıklama kutusu|legend|\bkey\b"), ("ölçek", r"ölçek|scale|1\s*:\s*\d"),
                  ("kuzey/yön", r"kuzey|yön oku|north"), ("kaynak", r"kaynak|source")]


def k_harita_ogeleri(c, ekle):
    eksik = []
    for m in re.finditer(r"!\[([^\]\n]{0,300})\]\([^)\n]{0,500}\)", c["govde"]):
        cevre = c["govde"][max(0, m.start() - 300): m.end() + 300].lower()
        if "harita" not in m.group(1).lower() and "harita" not in c["govde"][m.end(): m.end() + 150].lower():
            continue
        yok = [ad for ad, desen in HARITA_OGELERI if not re.search(desen, cevre)]
        if yok:
            eksik.append(f"«{m.group(1)[:30] or 'adsız'}»: {', '.join(yok)}")
    if eksik:
        ekle("Okunaklılık", "UYARI", f"Haritada öğe eksik ({len(eksik)}): {'; '.join(eksik[:3])}",
             "Her haritaya başlık (konu + yer + yıl), lejant, ölçek, kuzey oku ve kaynak (kurum + veri yılı) ekle")


# ── Fen, mühendislik, sayısal alanlar ──
SI_YANLIS = re.compile(r"\d\s*(Kg|KG|Km|KM|gr|Gr|lt|Lt|LT|KW|Kw|kw|Mhz|MHZ|mhz|KHz|khz)\b")
SI_DOGRU = {"Kg": "kg", "KG": "kg", "Km": "km", "KM": "km", "gr": "g", "Gr": "g", "lt": "L", "Lt": "L", "LT": "L",
            "KW": "kW", "Kw": "kW", "kw": "kW", "Mhz": "MHz", "MHZ": "MHz", "mhz": "MHz", "KHz": "kHz", "khz": "kHz"}


def k_si_birim(c, ekle):
    yanlis = sorted(set(SI_YANLIS.findall(c["gor"])))
    if yanlis:
        ekle("Doğruluk", "UYARI", f"Birim sembolü yanlış yazılmış ({', '.join(yanlis[:5])})",
             "SI sembolleri büyük/küçük harfe duyarlıdır: " + ", ".join(f"{y} → {SI_DOGRU[y]}" for y in yanlis[:5]),
             ornek=SI_YANLIS.search(c["gor"]).group(0))


SI_BITISIK = re.compile(r"(?<![\w.,/])\d+(?:[.,]\d+)?(kg|km|cm|mm|mg|mL|ml|kJ|kcal|kPa|MPa|Pa|kW|kN|N|J|W|V|mA|A|Hz|kHz|MHz|mol|K|°C)\b")


def k_si_bosluk(c, ekle):
    bitisik = sorted(set(m.group(0) for m in SI_BITISIK.finditer(c["gor"])))
    if len(bitisik) >= 2:
        ekle("Ezber ve kavrama", "UYARI", f"Sayı ile birim bitişik ({', '.join(bitisik[:4])})",
             "SI kuralı: sayı ile birim arasına boşluk (5 kg, 12 V, 20 °C); yalnız açı derecesi (30°) bitişik",
             ornek=bitisik[0])


TEHLIKELI_KIMYASAL = re.compile(r"\b(?:HCl|H2SO4|HNO3|NaOH|KOH|derişik|asit|aseton|eter|etanol|metanol|formaldehit|"
                                r"amonyak|klor|civa|benzen|kloroform|bek|alev|ısıt)\w*", re.I)


def k_lab_guvenlik(c, ekle):
    if re.search(r"deney|laboratuvar|föy|uygulama adımları", c["gor"], re.I) and TEHLIKELI_KIMYASAL.search(c["gor"]) and \
            not re.search(r"güvenlik|koruyucu|gözlük|eldiven|önlük|çeker ocak|GHS|H\d{3}|tehlike", c["gor"], re.I):
        ekle("Doğruluk", "UYARI", "Deneyde tehlikeli madde/ısı var ama güvenlik notu yok",
             "Kişisel koruyucu (gözlük, eldiven, önlük), çeker ocak ve GHS tehlike ifadelerini ekle",
             ornek=TEHLIKELI_KIMYASAL.search(c["gor"]).group(0))


P_SIFIR = re.compile(r"\bp\s*[=<≤]\s*0*[.,]0+(?![.,]?\d)|\bp\s*=\s*0(?![.,]?\d)", re.I)


def k_p_degeri(c, ekle):
    m = P_SIFIR.search(c["gor"])
    if m:
        ekle("Doğruluk", "UYARI", f"p değeri sıfır yazılmış ({m.group(0)})",
             "p sıfır olamaz: 'p < ,001' (APA: p < .001) yaz; raporlanan hassasiyete dikkat", ornek=m.group(0))


def k_kod_ornegi(c, ekle):
    bloklar = [(m.group(2), m.group(3)) for m in re.finditer(r"^[ \t]{0,3}(`{3,}|~{3,})([^\n]*)\n(.*?)^[ \t]{0,3}\1", c["govde"], re.S | re.M)]
    etiketsiz = [b for dil, b in bloklar if not dil.strip()]
    if len(bloklar) >= 2 and etiketsiz:
        ekle("Okunaklılık", "UYARI", f"Dil etiketi olmayan kod bloğu ({len(etiketsiz)}/{len(bloklar)})",
             "```python gibi dil etiketi koy (renklendirme ve kopyalama için)")
    kod = "\n".join(b for _, b in bloklar)
    m = (re.search(r"^\s*print\s+[\"'\w]", kod, re.M) or re.search(r"(?<!['\"\w])raw_input\(", kod)
         or re.search(r"\bpython\s*2(?:\.\d)?\b", c["gor"], re.I))
    if m:
        ekle("Doğruluk", "UYARI", "Python 2 sözdizimi ya da sürümü", "Python 2 1 Ocak 2020'de desteğini yitirdi; print(...) ve Python 3 kullan",
             ornek=m.group(0).strip())
    uzun = [satir for dil, b in bloklar if dil.strip().lower() in ("python", "py") for satir in b.splitlines() if len(satir) > 99]
    if uzun:
        ekle("Okunaklılık", "UYARI", f"Python kodunda 99 karakteri aşan satır ({len(uzun)})",
             "PEP 8: satır en çok 79 karakter; ekip anlaşmasıyla 99'a kadar izin verir. Satırı böl", ornek=uzun[0][:40])
    if bloklar and not re.search(r"python\s*3\.\d+|sürüm|versiyon|version|node\s*\d+|java\s*\d+|gcc|requirements", c["govde"], re.I):
        ekle("Ezber ve kavrama", "UYARI", "Kod örneği var ama dil/kitaplık sürümü yazılmamış",
             "Örneğin çalıştığı sürümü yaz (ör. Python 3.12)")


# ── Hukuk ──
MULGA = {"765": "5237 sayılı TCK (2005)", "818": "6098 sayılı TBK (2012)", "743": "4721 sayılı TMK (2002)",
         "1086": "6100 sayılı HMK (2011)", "6762": "6102 sayılı TTK (2012)", "1412": "5271 sayılı CMK (2005)"}
KARSILASTIRMA = re.compile(r"mülga|yürürlükten kalk|eski kanun|önceki|karşılaştır|kıyas|farklı|yerine|değiştir"
                           r"|yürürlükteyken|(?:tarihinde|yılında)\s+(?:kurulan|yapılan|gerçekleşen|imzalanan|doğan|açılan)"
                           r"|geçmiş|\b(?:19\d{2}|200\d|201[01])\b(?!\s*(?:baskı|basım|yayın|tarihli\s+kitap|edition))", re.I)


def k_hukuk_mulga(c, ekle):
    bulunan = []
    for cm in cumleler(c["gor"]):
        if KARSILASTIRMA.search(cm):
            continue
        for no in MULGA:
            if re.search(r"\b" + no + r"\s+sayılı|\(\s*" + no + r"\s*\)", cm):
                bulunan.append(no)
    if bulunan:
        bulunan = sorted(set(bulunan), key=bulunan.index)
        ekle("Doğruluk", "UYARI", f"Yürürlükten kalkmış kanun anılıyor ({', '.join(no + ' sayılı' for no in bulunan)}): "
             "zaman bakımından uygulamayı incele",
             "Yerine: " + "; ".join(MULGA[n] for n in bulunan) + ". Geçmiş olaya uygulanıyorsa bunu yaz "
             "(6101 sayılı Kanun m. 1: TBK'dan önceki işlemlere o zamanki kanun uygulanır)", ornek=bulunan[0])


def k_hukuk_kanun_numarasiz(c, ekle):
    adlar = set(re.findall(r"\b((?:[A-ZÇĞİÖŞÜ][a-zçğıöşü]+\s+){1,4}Kanunu)\b", c["gor"]))
    numarasiz = [a for a in adlar if not re.search(r"\d{3,4}\s+sayılı\s+" + re.escape(a.split()[0]), c["gor"])]
    if len(numarasiz) >= 2:
        ekle("Doğruluk", "UYARI", f"Kanun adı numarasız ({', '.join(sorted(numarasiz)[:3])})",
             "İlk geçtiği yerde '6098 sayılı Türk Borçlar Kanunu' gibi numarasıyla yaz", ornek=sorted(numarasiz)[0])


def k_hukuk_karar_kunyesi(c, ekle):
    eksik = [x.strip()[:50] for x in cumleler(c["gor"])
             if re.search(r"Yargıtay|Danıştay|Anayasa Mahkemesi|Bölge Adliye", x) and re.search(r"karar|içtihat", x, re.I)
             and not re.search(r"E\.\s*\d|K\.\s*\d|Esas|B\.\s*No|\d{4}/\d+", x)]
    if eksik:
        ekle("Doğruluk", "UYARI", f"Mahkeme kararı künyesiz anılıyor ({len(eksik)})",
             "Daire, E. (esas), K. (karar) ve T. (tarih) yaz: 'Yarg. 4. HD, E. 2019/123, K. 2020/456, T. 12.03.2020'",
             ornek=eksik[0])


# ── Beşerî bilimler ──
def k_hadis_kaynaksiz(c, ekle):
    yok = [x.strip()[:50] for x in cumleler(c["gor"]) if re.search(r"hadis|buyurdu|rivayet", x, re.I)
           and not re.search(r"Buhâr|Buhar|Müslim|Tirmiz|Ebû Dâvûd|Ebu Davud|Nesâ|Nesai|İbn Mâce|İbn Mace|Ahmed|Mâlik|Malik|"
                             r"Dârimî|\(\w[^()]*\d+\)", x, re.I)]
    if yok:
        ekle("Doğruluk", "UYARI", f"Hadis kaynaksız ({len(yok)}; ilki: «{yok[0]}»)",
             "Kaynağını (ör. Buhârî, Îmân, 2) ve gerekiyorsa sıhhat derecesini yaz", ornek=yok[0])


def k_ayet_kaynaksiz(c, ekle):
    yok = [x.strip()[:50] for x in cumleler(c["gor"]) if re.search(r"\bayet|âyet", x, re.I) and re.search(r"[\"“«]", x)
           and not re.search(r"\d+\s*[:/]\s*\d+|sûre|sure\w*\s+\d", x, re.I)]
    if yok:
        ekle("Doğruluk", "UYARI", f"Âyet meali sure:âyet numarasız ({len(yok)})", "Sure adı ve âyet numarasını yaz: (Bakara 2/255)",
             ornek=yok[0])


ALINTI = re.compile(r"[\"“«]([^\"”»]{60,})[\"”»]")
KUNYE = re.compile(r"\(\w[^()]*(?:\d{4}|s\.\s*\d|\d+\s*[:/]\s*\d+)[^()]*\)|\[\d+\]|—\s*[A-ZÇĞİÖŞÜ]")


def k_alinti_kaynaksiz(c, ekle):
    yok = []
    for p in paragraflar(c["gor"]):
        for m in ALINTI.finditer(p):
            cevre = p[max(0, m.start() - 120): m.start()] + " " + p[m.end(): m.end() + 120]
            if not KUNYE.search(cevre):
                yok.append(m.group(1)[:40])
    for m in re.finditer(r"^\s{0,3}>\s?(.{60,})$", c["govde"], re.M):
        sonraki = c["govde"][m.end(): m.end() + 150]
        if not KUNYE.search(m.group(1) + " " + sonraki):
            yok.append(m.group(1)[:40])
    if yok:
        ekle("Doğruluk", "UYARI", f"Doğrudan alıntı kaynaksız ({len(yok)})",
             "Alıntının önüne ya da ardına yazar, eser, yıl ve sayfa yaz: (Tanpınar, 1949, s. 12)", ornek=yok[0])


def k_eser_kunyesi(c, ekle):
    eksik = [alt for alt in re.findall(r"!\[([^\]\n]{1,300})\]\(", c["govde"]) if not YIL.search(alt) and not re.search(r"yy|yüzyıl|\d{2,4}", alt)]
    if len(eksik) >= 2:
        ekle("Okunaklılık", "UYARI", f"Eser görselinde künye eksik ({len(eksik)}: {', '.join(e[:25] for e in eksik[:2])})",
             "Her eser için sanatçı, eser adı, yıl, teknik ve bulunduğu yer yaz", ornek=eksik[0])


def k_cizim_olcegi(c, ekle):
    if re.search(r"\b(?:plan|kesit|görünüş|vaziyet|rölöve|detay)\b", c["gor"], re.I) and GORSEL_MD.search(c["govde"]) and \
            not re.search(r"\b1\s*[:/]\s*\d+|ölçek", c["gor"], re.I):
        ekle("Okunaklılık", "UYARI", "Teknik çizim var ama ölçek yok", "Her çizime ölçek (1:50, 1:100) ve kuzey/yön ekle")


KONTROLLER = {
    "dil_terim": k_dil_terim, "dil_hedef_disi": k_dil_hedef_disi, "dil_okunus_uzun": k_dil_okunus_uzun,
    "dil_okunussuz": k_dil_okunussuz, "tip_doz_yazimi": k_tip_doz_yazimi,
    "tip_tehlikeli_kisaltma": k_tip_tehlikeli_kisaltma, "kisaltma_tanimsiz": k_kisaltma_tanimsiz,
    "kilavuz_yilsiz": k_kilavuz_yilsiz, "cozulmus_ornek": k_cozulmus_ornek,
    "cevapsiz_alistirma": k_cevapsiz_alistirma, "dis_numara_karisik": k_dis_numara_karisik,
    "kaynaksiz_otorite": k_kaynaksiz_otorite, "kaynakca_yok": k_kaynakca_yok, "yuzyil_yazimi": k_yuzyil_yazimi,
    "veri_yilsiz": k_veri_yilsiz, "harita_ogeleri": k_harita_ogeleri,
    "saglik_kisaltma_ek": k_saglik_kisaltma_ek, "saglik_bosluk": k_saglik_bosluk, "doz_kg_belirsiz": k_doz_kg_belirsiz,
    "doz_aritmetigi": k_doz_aritmetigi, "cocuk_azami_doz": k_cocuk_azami_doz, "prn_talimat": k_prn_talimat,
    "lab_birim_karisik": k_lab_birim_karisik, "referans_kaynaksiz": k_referans_kaynaksiz,
    "gebelik_kategorisi": k_gebelik_kategorisi, "tani_surumu_eski": k_tani_surumu_eski, "kilavuz_eski": k_kilavuz_eski,
    "hasta_kimlik": k_hasta_kimlik, "tur_adi_yazimi": k_tur_adi_yazimi, "vet_tursuz_doz": k_vet_tursuz_doz,
    "beslenme_birim": k_beslenme_birim, "saglik_beyani": k_saglik_beyani, "bakim_plani": k_bakim_plani,
    "egzersiz_recetesi": k_egzersiz_recetesi, "si_birim": k_si_birim, "si_bosluk": k_si_bosluk, "lab_guvenlik": k_lab_guvenlik,
    "p_degeri": k_p_degeri, "kod_ornegi": k_kod_ornegi, "hukuk_mulga": k_hukuk_mulga,
    "hukuk_kanun_numarasiz": k_hukuk_kanun_numarasiz, "hukuk_karar_kunyesi": k_hukuk_karar_kunyesi,
    "hadis_kaynaksiz": k_hadis_kaynaksiz, "ayet_kaynaksiz": k_ayet_kaynaksiz, "alinti_kaynaksiz": k_alinti_kaynaksiz,
    "eser_kunyesi": k_eser_kunyesi, "cizim_olcegi": k_cizim_olcegi, "tc_kimlik": k_tc_kimlik,
}
# Alandan bağımsız risk taraması: sağlık örüntüsü (doz/ilaç) görülürse alan ne olursa olsun çalışır.
RISK_KONTROLLERI = ["tip_doz_yazimi", "tip_tehlikeli_kisaltma", "saglik_kisaltma_ek", "saglik_bosluk", "doz_kg_belirsiz", "doz_aritmetigi",
                    "lab_birim_karisik", "prn_talimat", "cocuk_azami_doz"]
CEKIRDEK_KONTROLLER = ["hasta_kimlik", "tc_kimlik"]


# ── Ortak çekirdek (her alanda) ──
def cekirdek(c, ek, profil_alan):
    gor, govde, meta, olcum = c["gor"], c["govde"], c["meta"], c["olcum"]
    gevsek = bool(c["alanlar"] & SAYISAL_ALANLAR)
    kiril = [s for s in karisik_sozcukler(gor) if KIRIL.search(s)]
    yunan = [s for s in karisik_sozcukler(gor) if YUNAN.search(s) and not KIRIL.search(s)]
    if kiril:
        ek("alfabe")("Doğruluk", "HATA", f"Latin harfle karışık Kiril harfi ({len(kiril)} sözcük: {', '.join(sorted(set(kiril))[:3])})",
             "--duzelt benzer Kiril harfleri Latin harfe çevirir", ornek=kiril[0])
    if yunan and not gevsek:
        uzun = [s for s in yunan if len(s) >= 4 and len(LATIN.findall(s)) >= 2]
        ek("alfabe")("Doğruluk", "HATA" if uzun else "UYARI",
             f"Latin harfle karışık Yunan harfi ({len(yunan)} sözcük: {', '.join(sorted(set(yunan))[:3])})",
             "Sembol değilse Latin harfe çevir; formülse alanı belirt (alan: fizik)", ornek=yunan[0])
    for m in list(YER_TUTUCU.finditer(gor))[:20]:
        ek("yer_tutucu")("Doğruluk", "HATA", "Bitmemiş yer işareti (TODO/FIXME/???) öğrenciye gidiyor", "Tamamla ya da sil", ornek=m.group(0).strip())

    basliklar = BASLIK_MD.findall(govde) + BASLIK_HTML.findall(govde)
    if any(arti for _, arti in basliklar):
        ek("baslik_no")("Sıra ve akış", "UYARI", "Ek numaralı başlık (3.5+)", "Düz numarala; araya giren bölümle yeniden numarala")
    gorulen, onceki = set(), None
    for no, _ in basliklar:
        if no in gorulen:
            ek("baslik_no")("Sıra ve akış", "UYARI", f"Aynı başlık numarası iki kez: {no}", "Yeniden numarala", ornek=f"{no}.")
        gorulen.add(no)
        t = tuple(int(x) for x in no.split("."))
        if onceki and len(t) == len(onceki) and t[:-1] == onceki[:-1] and t[-1] < onceki[-1]:
            ek("baslik_no")("Sıra ve akış", "UYARI", f"Başlık numarası geriye gidiyor: {'.'.join(map(str, onceki))} → {no}",
                 "Sırayı düzelt")
        onceki = t
    gonderme = SAYFA_GONDERME.findall(gor)
    if gonderme and c["tur"] != "kilavuz":
        ek("sayfa_gonderme")("Sıra ve akış", "UYARI", f"Belge içi sayfa göndermesi ({', '.join(sorted(set(gonderme))[:3])})",
             "Sayfa kayar; bölüm numarası ya da adı kullan", ornek=gonderme[0])

    if c["tur"] in SINAMA_ISTEYEN and not (SINAMA_GUCLU.search(gor) or (SINAMA_SOZ.search(gor) and SORU_IZI.search(gor))):
        ek("kendini_sinama")("Kendini sınama", "UYARI", "Kapalı kitap sınama bölümü yok (soru, boşluk ya da numaralı madde içeren test)",
             profil_alan["sinama_oneri"])

    bos_alt = len(re.findall(r"!\[[ \t]{0,20}\]\(", govde)) + len([m for m in re.findall(r"<img\b[^>\n]{0,1000}>", govde, re.I)
                                                           if not re.search(r"\balt\s*=\s*['\"][^'\"]+", m)])
    if bos_alt:
        ek("alt_metin")("Okunaklılık", "UYARI", f"Açıklamasız görsel ({bos_alt}): alt metin yok", "Her görsele ne gösterdiğini yaz")
    if c["bicim"] == "gorsel" and len(GORSEL_MD.findall(govde)) >= 3 and not SEKIL_BASLIGI.search(gor):
        ek("sekil_basligi")("Okunaklılık", "UYARI", "Görsel ağırlıklı belgede şekil başlığı/numarası yok",
             "Her görsele 'Şekil N: …' başlığı ve kısa açıklama koy; metinde numarasıyla an")

    if olcum and olcum.get("metin_var", True):
        kutu = olcum.get("kutu", olcum.get("yazi", 0.0))
        if kutu:
            en_az, en_cok = kutu / KUTU_ORAN_UST, kutu / KUTU_ORAN_ALT
            if en_cok < PUNTO_HATA:
                ek("pdf_yazi")("Okunaklılık", "HATA", f"Yazı çok küçük (tahmini {en_az:.1f}–{en_cok:.1f} pt; kelime kutusu {kutu} pt)",
                     "Gövdeyi ≥ 11 pt, tabloyu ≥ 9 pt yap")
            elif en_az < PUNTO_UYARI:
                ek("pdf_yazi")("Okunaklılık", "UYARI", f"Yazı küçük olabilir (tahmini {en_az:.1f}–{en_cok:.1f} pt; kelime kutusu {kutu} pt)",
                     "Tabloyu ≥ 9 pt, gövdeyi ≥ 11 pt yap; yazı tipine göre tahmin değişir")
        try:
            not_say = int(meta.get("not_sayfasi", 0) or 0)
        except ValueError:
            not_say = 0
        icerik = olcum["doluluk"][: len(olcum["doluluk"]) - not_say] if not_say else olcum["doluluk"]
        murekkep = olcum.get("murekkep", {})
        bos, cizimli = [], []
        for i, d, g in icerik:
            if d < BOS_SAYFA and not g:
                mk = murekkep.get(i)
                if mk is None:
                    cizimli.append(i)
                elif mk < MUREKKEP_ESIK:
                    bos.append(i)
        if bos:
            ek("pdf_bos_sayfa")("Okunaklılık", "HATA", f"Boş sayfa: {bos}", "Zorunlu sayfa geçişini kaldır")
        if cizimli:
            ek("pdf_bos_sayfa")("Okunaklılık", "UYARI", f"Metinsiz sayfa (çizim ya da boş olabilir; doğrulanamadı): {cizimli}",
                 "Sayfaya bak; boşsa kaldır")
        yarim = [i for i, d, g in icerik[:-1] if BOS_SAYFA <= d < YARIM_SAYFA and not g]
        if icerik and len(yarim) / len(icerik) > YARIM_ORAN:
            ek("pdf_yarim_sayfa")("Verimlilik", "UYARI", f"Yarım sayfa çok ({len(yarim)}/{len(icerik)}: {yarim[:8]})",
                 "Zorunlu sayfa geçişlerini azalt; büyük tabloyu bölünebilir yap")
        tavan = meta.get("sayfa_tavan", "")
        if tavan.isdigit() and olcum["sayfa"] > int(tavan):
            ek("sayfa_tavan")("Verimlilik", "HATA", f"Sayfa tavanı aşıldı: {olcum['sayfa']} > {tavan}",
                 "Tekrarı ve dolguyu at, tavanın altına indir")
        elif not tavan.isdigit() and olcum["sayfa"] >= SAYFA_UYARI:
            ek("sayfa_tavan")("Verimlilik", "UYARI", f"{olcum['sayfa']} sayfa ({SAYFA_UYARI}+): gerekçe ister",
                 "Frontmatter'a sayfa_tavan yaz ya da kısalt")


# ── Konum ve susturma ──
def _sade(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[*_`|>$\\]", "", unicodedata.normalize("NFKC", s).translate(ALT_SIMGE))).strip()


def satir_dizini(satirlar: list[str]) -> list[str]:
    return [_sade(s) for s in satirlar]


def satir_bul(ornek: str, dizin: list[str], sonra: int = 0) -> int | None:
    hedef = _sade(ornek) if ornek else ""
    if not hedef:
        return None
    for i, s in enumerate(dizin, 1):
        if i <= sonra:
            continue
        if hedef in s:
            return i
    return None


SUSTURMA_MIN_GEREKCE = 10


def susturmalar(metin: str) -> tuple[dict, dict]:
    """Belge düzeyi: {kural: gerekçe}; satır düzeyi (kuralsız): {satır: gerekçe}. Düzenli ifade kullanılmaz (ReDoS)."""
    belge, satir = {}, {}
    cit = None
    for i, s in enumerate(metin.splitlines(), 1):
        mc = CIT.match(s)
        if mc:
            f = mc.group(1)
            if cit is None:
                cit = f
            elif f[0] == cit[0] and len(f) >= len(cit) and not s.strip()[len(f):].strip():
                cit = None
            continue
        if cit:
            continue   # kod örneğindeki susturma yorumu gerçek susturma değildir
        j = 0
        while True:
            a = s.find("<!--", j)
            if a < 0:
                break
            if s.count("`", 0, a) % 2:      # satır içi kodun içinde: yalnız gösterim
                j = a + 4
                continue
            k = s.find("-->", a + 4)
            if k < 0:
                break
            ic = s[a + 4:k].strip()
            j = k + 3
            if not ic.lower().startswith("sinac:"):
                continue
            ic = ic[6:].strip()
            if not ic.lower().startswith("yoksay"):
                continue
            ic = ic[6:].strip()
            konum = [(ic.find(x), x) for x in ("—", "–", " - ", "--") if x in ic]
            if ic.startswith("- "):
                konum.append((0, "- "))
            if konum:
                k0, ayrac = min(konum)
                kurallar_s, gerekce = ic[:k0], ic[k0 + len(ayrac):]
            else:
                kurallar_s, gerekce = ic, ""
            kurallar = [x.strip() for x in kurallar_s.split(",") if x.strip()]
            gerekce = gerekce.strip()
            if kurallar:
                for kr in kurallar:
                    belge[kr] = gerekce
            else:
                satir[i] = gerekce
    return belge, satir


OLUMSUZ = re.compile(r"^\s*(?:yok|hayır|none|no|n/?a)\b|^\s*[-—–?.…_*]+"
                     r"|\b(?:yapılmadı|yapılmamış|henüz|bekliyor|beklemede|belirsiz|tbd|todo|planlandı|pending|not done"
                     r"|yapılacak|edilecek|unspecified|unknown|not\s+(?:yet|specified|reviewed|checked|done|available|set))\b|\b\w{2,}(?:lmedi|lmadı|nmedi|nmadı|lmemiş|lmamış|nmemiş|nmamış)\b")


def _gercek_tarih(y: int, a: int, g: int) -> bool:
    try:
        date(y, a, g)
        return True
    except ValueError:
        return False


def elle_gecerli(anahtar: str, deger: str) -> bool:
    if not deger or OLUMSUZ.search(tr_kucuk(deger)):
        return False
    if anahtar == "denetim":
        for g, a, y in re.findall(r"\b(\d{1,2})[./](\d{1,2})[./](\d{4})\b", deger):
            if not _gercek_tarih(int(y), int(a), int(g)):
                return False
        for g, a, y in re.findall(r"\b(\d{1,2})[./](\d{1,2})[./](\d{2})\b(?![./]\d)", deger):
            if not _gercek_tarih(2000 + int(y), int(a), int(g)):
                return False
        for y, a, g in re.findall(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", deger):
            if not _gercek_tarih(int(y), int(a), int(g)):
                return False
        return bool(re.search(r"\b(?:19|20)\d{2}\b|\d{1,2}[./]\d{1,2}[./]\d{2,4}", deger))
    return len(deger.strip()) >= 2 and bool(re.search(r"\w", deger))   # 'A1', 'B2' geçerli hedef


# ── Denetim ──
def denetle(metin: str, olcum: dict | None = None, alan: str | None = None, dil: str | None = None,
            yil: int | None = None, pdf_metin: str | None = None) -> dict:
    """metin: .md içeriği; olcum: pdf_olc() sonucu ya da None; alan/dil: tespiti geçmek için; yil: değerlendirme yılı;
    pdf_metin: PDF'ten çıkarılan metin (verilirse kimlik ve ilaç güvenlik kontrolleri PDF'te de çalışır)."""
    profil = profiller()
    meta, govde, ofset = on_bilgi(metin)
    satirlar = hazirla_satirlar(govde, ofset)
    gor = "\n".join(x["gor"] for x in satirlar)
    tam = "\n".join(x["tam"] for x in satirlar)
    tespit = alan_tespit(meta, gor, profil, alan)
    a = tespit["alan"]
    if dil and dil not in DIL:
        raise ValueError(f"desteklenmeyen dil: {dil} ({', '.join(DIL)})")
    dil_kodu = dil or meta.get("dil") or (dil_tahmin(tr_kucuk(gor))[0] if a == "dil" else "")
    if dil_kodu and dil_kodu not in DIL:
        # 'tr-fr', 'tr/fr', 'fr+tr' gibi çift dilli notlarda öğretilen dil Türkçe olmayan parçadır
        parca = [x for x in re.split(r"[-/+,\s]+", dil_kodu.lower()) if x and x != "tr"]
        if len(parca) == 1 and parca[0] in DIL:
            dil_kodu = parca[0]
    if a == "dil" and dil_kodu not in DIL:
        raise ValueError(f"desteklenmeyen dil: {dil_kodu} ({', '.join(DIL)}); Kiril/Arap alfabeli diller desteklenmiyor")
    ek_alanlar = [] if tespit["kaynak"] == "kullanıcı seçimi" else bolum_alanlari(govde, profil, a)
    alanlar = {a, *ek_alanlar}
    tur = re.sub(r"[\s_]+", "-", meta.get("tur", "").strip().lower())
    govde_kodsuz = re.sub(r"^```.*?^```", " ", govde, flags=re.S | re.M) if govde.count("```") < 2000 else govde
    c = {"meta": meta, "govde": govde, "govde_kodsuz": govde_kodsuz, "gor": gor, "tam": tam, "kucuk": tr_kucuk(gor),
         "kucuk_en": en_kucuk(gor), "tur": tur, "olcum": olcum, "dil": dil_kodu, "satirlar": satirlar,
         "tablo": tablolar(satirlar), "okunuslar": OKUNUS.findall(gor), "bicim": bicim_tespit(meta, govde, gor, olcum),
         "alanlar": alanlar, "yil": yil or date.today().year, "maske": set()}
    bulgu: list[dict] = []

    def ekleyici(kural, kaynak="md"):
        def ekle(boyut, duzey, mesaj, oneri="", ornek="", satir=None):
            bulgu.append({"boyut": boyut, "duzey": duzey, "mesaj": mesaj, "oneri": oneri, "kural": kural,
                          "ornek": ornek, "satir": satir, "kaynak": kaynak})
        return ekle

    cekirdek(c, ekleyici, profil[a])
    if tur and tur not in SINAMA_ISTEYEN + OKUNUS_ISTEMEYEN + ("kilavuz", "indeks", "yonetim", "sinav", "kelime-listesi"):
        ekleyici("tur")("Kendini sınama", "UYARI", f"Bilinmeyen tur: '{meta.get('tur')}'",
                        "Geçerli değerler: konu-anlatimi, rehber, ders-notu, pano, kilavuz, indeks, yonetim; "
                        "bilinmeyen değerde kendini sınama denetlenmez")
    kontroller = list(CEKIRDEK_KONTROLLER)
    for al in [a] + ek_alanlar:
        for k in kontrol_listesi(profil, al):
            if k not in kontroller:
                kontroller.append(k)
    risk_izi = any(ILAC_ADI.search(x["tam"]) or (DOZ_IZI.search(x["tam"]) and DOZ_BAGLAM.search(x["tam"]))
                   or LAB_IZI.search(x["tam"]) for x in satirlar + c["tablo"])
    risk = risk_izi and not all(k in kontroller for k in RISK_KONTROLLERI)
    if risk:
        kontroller += [k for k in RISK_KONTROLLERI if k not in kontroller]
    for k in kontroller:
        KONTROLLER[k](c, ekleyici(k))

    # PDF metni: kimlik ve ilaç güvenliği PDF'te de (md ile PDF farklı olabilir)
    if pdf_metin:
        ps = [{"no": None, "tam": satir_hazirla(x), "gor": satir_hazirla(x), "kod": False, "ham": x}
              for x in pdf_metin.splitlines()]
        cp = dict(c, satirlar=ps, tablo=[], tam="\n".join(x["tam"] for x in ps), gor="\n".join(x["gor"] for x in ps))
        _, satir_sus_md = susturmalar(metin)
        mevcut = {}
        for b in bulgu:
            if b.get("satir") in satir_sus_md:
                continue   # md satırı susturulmuş: öğrenciye giden PDF'teki aynı hata ayrıca raporlanır
            anahtar = (b["kural"], _sade(b.get("ornek", "")))
            mevcut[anahtar] = min(mevcut.get(anahtar, 9), DUZEY_SIRA[b["duzey"]])
        pdf_bulgu_bas = len(bulgu)
        for k in CEKIRDEK_KONTROLLER + RISK_KONTROLLERI:
            KONTROLLER[k](cp, ekleyici(k, "pdf"))
        c["maske"] |= cp["maske"]
        yeni = []
        for b in bulgu[pdf_bulgu_bas:]:
            onceki = mevcut.get((b["kural"], _sade(b.get("ornek", ""))), 9)
            if onceki <= DUZEY_SIRA[b["duzey"]]:
                continue   # md'de aynı ya da daha ağır düzeyde var
            b["mesaj"] = ("PDF'te (md'de daha hafif): " if onceki < 9 else "PDF'te (md'de yok): ") + b["mesaj"]
            yeni.append(b)
        bulgu = bulgu[:pdf_bulgu_bas] + yeni

    # Konum, maske, susturma
    dizin = satir_dizini(metin.lstrip("﻿").splitlines())
    belge_sus, satir_sus = susturmalar(metin)
    maske = sorted(c["maske"], key=len, reverse=True)
    kalan, susturulan = [], []
    belge_engel_susturuldu = False
    son_satir = {}
    for b in bulgu:
        if b["satir"] is None and b["kaynak"] == "md":
            anahtar = (b["kural"], b.get("ornek", ""))
            b["satir"] = satir_bul(b.get("ornek", ""), dizin, son_satir.get(anahtar, 0)) or satir_bul(b.get("ornek", ""), dizin)
            if b["satir"]:
                son_satir[anahtar] = b["satir"]
        for m in maske:
            if m and len(m) >= 3:
                b["mesaj"] = b["mesaj"].replace(m, _maskele(m))
                b["ornek"] = (b.get("ornek") or "").replace(m, _maskele(m))
        if b["kural"] in belge_sus:
            gerekce, duzey_s = belge_sus[b["kural"]], "belge"
        elif b["satir"] in satir_sus:
            gerekce, duzey_s = satir_sus[b["satir"]], "satır"
        else:
            kalan.append(b)
            continue
        yeterli = len(gerekce) >= SUSTURMA_MIN_GEREKCE
        if b["duzey"] == "UYARI" or yeterli:
            susturulan.append({**b, "gerekce": gerekce or "—", "susturma": duzey_s})
            if duzey_s == "belge" and b["duzey"] in ("ENGEL", "HATA"):
                belge_engel_susturuldu = True
            continue
        kalan.append({**b, "mesaj": b["mesaj"] + f" (susturma gerekçesi yok ya da {SUSTURMA_MIN_GEREKCE} karakterden kısa; susturulmadı)"})
    bulgu = sorted(kalan, key=lambda x: (DUZEY_SIRA[x["duzey"]], BOYUTLAR.index(x["boyut"]), x.get("satir") or 0))

    # Elle alanlar, puan ve kapsam
    hedefler = [meta.get("hedef", ""), meta.get("sinav", "")]
    elle_ham = {"Doğruluk": meta.get("denetim", ""),
                "Hedefle uyum": next((h for h in hedefler if elle_gecerli("hedef", h)), next((h for h in hedefler if h), ""))}
    elle = {k: v if elle_gecerli("denetim" if k == "Doğruluk" else "hedef", v) else "" for k, v in elle_ham.items()}
    gorsel_var = bool(GORSEL_MD.search(govde))
    olculmeyen = set()
    if not olcum or not olcum.get("metin_var", True):
        olculmeyen.add("Verimlilik")
        if not gorsel_var:
            olculmeyen.add("Okunaklılık")
    if not elle["Hedefle uyum"]:
        olculmeyen.add("Hedefle uyum")
    if c["tur"] not in SINAMA_ISTEYEN:
        olculmeyen.add("Kendini sınama")
    puan = {}
    for bo in BOYUTLAR:
        d = [x["duzey"] for x in bulgu if x["boyut"] == bo]
        if not d and bo in olculmeyen:
            puan[bo] = None
        else:
            puan[bo] = 0 if ("ENGEL" in d or "HATA" in d) else 1 if "UYARI" in d else 2
    for x in susturulan:
        if x["duzey"] in ("ENGEL", "HATA") and puan.get(x["boyut"]) == 2:
            puan[x["boyut"]] = 1      # susturulan engel tam puan getirmez
    if not elle["Doğruluk"] and puan["Doğruluk"] == 2:
        puan["Doğruluk"] = 1          # otomatik temiz ama içerik elle doğrulanmadı
    olculen = [v for v in puan.values() if v is not None]
    engel = any(x["duzey"] == "ENGEL" for x in bulgu)
    hata = any(x["duzey"] == "HATA" for x in bulgu)
    elle_eksik = [k for k, v in elle.items() if not v]
    if engel or hata:
        karar = "yayına engel var"
    elif elle_eksik or belge_engel_susturuldu:
        karar = "karar için denetim eksik"
    else:
        karar = "tanımlı kapsamda uygun"
    return {"alan": a, "alan_adi": profil[a]["ad"], "ek_alanlar": ek_alanlar, "tespit": tespit,
            "risk_taramasi": risk, "bicim": c["bicim"], "dil": dil_kodu, "tur": c["tur"],
            "degerlendirme_yili": c["yil"], "puan": puan, "toplam": sum(olculen), "azami": 2 * len(olculen),
            "olculen_boyut": len(olculen), "bulgular": bulgu, "susturulan": susturulan,
            "belge_duzeyi_engel_susturuldu": belge_engel_susturuldu, "elle": elle, "elle_eksik": elle_eksik,
            "elle_reddedilen": [k for k in elle if elle_ham[k] and not elle[k]],
            "elle_liste": elle_listesi(profil, a) + (profil["_gorsel"]["elle"] if c["bicim"] == "gorsel" else []),
            "kontroller": kontroller, "pdf_icerik_denetlendi": bool(pdf_metin),
            "sayfa": olcum["sayfa"] if olcum else None,
            "kutu_pt": (olcum.get("kutu", olcum.get("yazi")) if olcum else None),
            "sonuc": "ENGEL" if engel else "HATA" if hata else ("UYARI" if bulgu else "TEMIZ"),
            "karar": karar}


# ── Düzeltme ──
def _korunan_araliklar(govde: str) -> list[tuple[int, int]]:
    """Kod (``` ~~~ çit, girintili blok, satır içi), formül ($…$, $$…$$, \\[…\\], \\(…\\)) ve <pre>/<code>."""
    araliklar = []
    for m in re.finditer(r"^[ \t]{0,3}((?:>[ \t]?)*)((`|~)\3{2,})[^\n]*\n(?:.*?^[ \t]{0,3}\1\2\3*[ \t]*\r?$|.*\Z)",
                         govde, re.S | re.M):
        araliklar.append(m.span())
    for m in re.finditer(r"(?:^(?: {4}|\t)[^\n]*\n?)+", govde, re.M):
        onceki = govde[:m.start()].replace("\r\n", "\n").rstrip(" \t")
        if not onceki or onceki.endswith("\n\n"):
            araliklar.append(m.span())
    for desen in (r"(?<!`)(`+)(?!`).{0,2000}?(?<!`)\1(?!`)", r"<pre\b.{0,20000}?</pre>", r"<code\b.{0,5000}?</code>"):
        for m in re.finditer(desen, govde, re.S | re.I):
            araliklar.append(m.span())
    # Formül, kodun dışında aranır: kod içindeki '$' dışarıdaki '$' ile eşleşmesin
    maskeli = list(govde)
    for a, b in araliklar:
        for i in range(a, b):
            if maskeli[i] != "\n":
                maskeli[i] = " "
    maskeli = "".join(maskeli)
    for desen in (r"\$\$.{0,5000}?\$\$", r"\$[^$\n]{1,500}\$", r"\\\[.{0,5000}?\\\]", r"\\\(.{0,2000}?\\\)",
                  r"\\begin\{([A-Za-z]+)(\*?)\}.{0,20000}?\\end\{\1\2\}"):
        for m in re.finditer(desen, maskeli, re.S):
            araliklar.append(m.span())
    birlesik = []
    for a, b in sorted(araliklar):
        if birlesik and a <= birlesik[-1][1]:
            birlesik[-1] = (birlesik[-1][0], max(birlesik[-1][1], b))
        else:
            birlesik.append((a, b))
    return birlesik


def duzelt(metin: str, alan: str = "genel") -> tuple[str, list[str]]:
    """Yalnız güvenli düzeltmeler; korunan bölgelere (kod, formül, frontmatter) dokunulmaz."""
    yapilan, sayac = [], {"kiril": 0, "yunan": 0}
    m_on = re.match(r"^﻿?[ \t]*---[ \t]*\r?\n.*?\r?\n---[ \t]*\r?\n", metin, re.S)
    on, govde = (metin[:m_on.end()], metin[m_on.end():]) if m_on else ("", metin)
    yunan_serbest = alan not in SAYISAL_ALANLAR

    def parca(gov):
        if MIKRO_BIRIM.match(gov) or not LATIN.search(gov):
            return gov
        kiril = [ch for ch in gov if KIRIL.match(ch)]
        yunan = [ch for ch in gov if YUNAN.match(ch)]
        yeni = gov
        if kiril and all(ch in BENZER_KIRIL for ch in kiril):
            yeni = "".join(BENZER_KIRIL.get(ch, ch) for ch in yeni)
            sayac["kiril"] += 1
        if yunan and yunan_serbest and len(gov) >= 4 and len(LATIN.findall(gov)) > len(yunan) \
                and all(ch in BENZER_YUNAN for ch in yunan):
            yeni = "".join(BENZER_YUNAN.get(ch, ch) for ch in yeni)
            sayac["yunan"] += 1
        return yeni

    def cevir(m):
        return "".join(parca(x) if i % 2 == 0 else x for i, x in enumerate(re.split(r"(['’])", m.group(0))))

    parcalar, son = [], 0
    for a, b in _korunan_araliklar(govde):
        if a >= son:
            parcalar.append(SOZCUK.sub(cevir, govde[son:a]))
            parcalar.append(govde[a:b])
            son = b
    parcalar.append(SOZCUK.sub(cevir, govde[son:]))
    govde_yeni = "".join(parcalar)
    korunan = _korunan_araliklar(govde_yeni)
    if sayac["kiril"]:
        yapilan.append(f"{sayac['kiril']} sözcükte Kiril benzer harf Latin harfe çevrildi")
    if sayac["yunan"]:
        yapilan.append(f"{sayac['yunan']} sözcükte Yunan benzer harf Latin harfe çevrildi")
    for m in PUNTO.finditer(govde_yeni):
        if any(a <= m.start() < b for a, b in korunan):
            continue
        if float(m.group(1)) < DUZELT_PUNTO_ALT:
            yapilan.append(f"Gövde yazısı {m.group(1)} pt → {DUZELT_PUNTO} pt (sayfa düzeni değişebilir, PDF'e bak)")
            govde_yeni = govde_yeni[:m.start(1)] + DUZELT_PUNTO + govde_yeni[m.end(1):]
        break
    return on + govde_yeni, yapilan


# ── Çıktı ──
ISARET = {"ENGEL": "⛔", "HATA": "⛔", "UYARI": "⚠"}


def yazdir(ad: str, s: dict, notlar: list[str]) -> None:
    bas = {"yayına engel var": "⛔", "karar için denetim eksik": "◐", "tanımlı kapsamda uygun": "✓"}[s["karar"]]
    ek = f" · {s['sayfa']} s. · kelime kutusu {s['kutu_pt']} pt" if s["sayfa"] is not None else " · PDF ölçülmedi"
    print(f"{bas} {ad}: {s['karar'].replace('i', 'İ').upper()} · {s['toplam']}/{s['azami']} ({s['olculen_boyut']}/8 boyut ölçüldü){ek}")
    t = s["tespit"]
    neden = f"; ipucu: {', '.join(t['kanit'])}" if t["kanit"] else ""
    ikinci = f"; ikinci aday: {t['ikinci']}" if t["ikinci"] else ""
    dil = f" ({s['dil']})" if s["alan"] == "dil" else ""
    print(f"  Alan: {s['alan_adi']}{dil} · {t['kaynak']}, destek {t['destek']}{neden}{ikinci} · biçim: {s['bicim']}")
    if s["ek_alanlar"]:
        print(f"  Bölüm alanları: {', '.join(s['ek_alanlar'])} (bu alanların kontrolleri de çalıştı)")
    if s["risk_taramasi"]:
        print("  Risk taraması: ilaç/doz örüntüsü bulundu; sağlık güvenlik kontrolleri alandan bağımsız çalıştı")
    if t["kaynak"] == "tespit" and t["destek"] != "güçlü":
        print("  (alan yanlışsa frontmatter'a `alan: …` yaz ya da --alan ver)")
    for n in notlar:
        print(f"  {n}")
    print("  | Boyut | Puan |\n  |---|---|")
    for b, v in s["puan"].items():
        print(f"  | {b} | {'ölçülmedi' if v is None else v} |")
    engeller = [x for x in s["bulgular"] if x["duzey"] in ("ENGEL", "HATA")]
    uyarilar = [x for x in s["bulgular"] if x["duzey"] == "UYARI"]
    for x in engeller + uyarilar[:5]:
        yer = f"satır {x['satir']} · " if x.get("satir") else ""
        print(f"  {ISARET[x['duzey']]} {x['duzey']} · {yer}{x['boyut']}: {x['mesaj']}"
              + (f" → {x['oneri']}" if x["oneri"] else "") + f"  [{x['kural']}]")
    if len(uyarilar) > 5:
        print(f"  … ve {len(uyarilar) - 5} uyarı daha (--json ile tümü)")
    for x in s["susturulan"]:
        print(f"  ⊘ susturuldu [{x['kural']}] {x['mesaj']} — gerekçe: {x['gerekce']}")
    if s["elle_eksik"]:
        print(f"  ☐ elle bekleyen: {', '.join(s['elle_eksik'])} (frontmatter denetim: / hedef:)")
    if s.get("elle_reddedilen"):
        print(f"  ✗ elle değeri geçersiz sayıldı: {', '.join(s['elle_reddedilen'])} (boş/olumsuz ya da denetimde tarih yok)")
    if any(k in s["kontroller"] for k in RISK_KONTROLLERI):
        print("  ℹ Betik doz YAZIMINI denetler, dozun klinik doğruluğunu denetlemez: güncel kaynakla karşılaştır")
    for m in s["elle_liste"]:
        print(f"  ☐ {m}")


def main(argv: list[str]) -> int:
    arg = {"pdf": None, "dil": None, "alan": None, "yil": None, "json": False, "duzelt": False}
    dosyalar, i = [], 0
    while i < len(argv):
        a = argv[i]
        if a in ("--pdf", "--dil", "--alan", "--yil"):
            if i + 1 >= len(argv):
                print(f"{a} değer ister", file=sys.stderr)
                return 2
            arg[a[2:]] = argv[i + 1]
            i += 2
            continue
        if a in ("--json", "--duzelt"):
            arg[a[2:]] = True
        elif a in ("-h", "--help"):
            print(__doc__)
            return 0
        elif a.startswith("--"):
            print(f"bilinmeyen seçenek: {a}", file=sys.stderr)
            return 2
        else:
            dosyalar.append(a)
        i += 1
    if len(dosyalar) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    if arg["yil"] and not re.fullmatch(r"\d{4}", arg["yil"]):
        print("--yil YYYY olmalı", file=sys.stderr)
        return 2
    md = Path(dosyalar[0])
    if not md.is_file():
        print(f"dosya yok: {md}", file=sys.stderr)
        return 2
    ham = md.read_bytes()
    notlar = []
    try:
        metin = ham.decode("utf-8")
    except UnicodeDecodeError:
        try:
            metin = ham.decode("cp1254")
            notlar.append("Dosya UTF-8 değil; Windows-1254 (Türkçe) olarak okundu. UTF-8'e çevirmen önerilir")
        except UnicodeDecodeError:
            print(f"dosya okunamadı (UTF-8 ya da Windows-1254 değil): {md}", file=sys.stderr)
            return 2
    if not metin.strip():
        print(f"boş belge: {md}", file=sys.stderr)
        return 2
    yil = int(arg["yil"]) if arg["yil"] else None
    arg["dil"] = arg["dil"].lower() if arg["dil"] else None
    md_degisti = False
    if arg["duzelt"]:
        try:
            on_alan = denetle(metin, None, arg["alan"], arg["dil"], yil)["alan"]
        except ValueError as e:
            print(str(e), file=sys.stderr)
            return 2
        yeni, yapilan = duzelt(metin, on_alan)
        if yapilan:
            yedek = md.with_name(md.name + ".bak")
            n = 1
            while yedek.exists():
                yedek = md.with_name(f"{md.name}.bak{n}")
                n += 1
            yedek.write_bytes(ham)
            with open(md, "w", encoding="utf-8", newline="") as f:
                f.write(yeni)
            metin = yeni
            md_degisti = True
            notlar += [f"🔧 {y} (yedek: {yedek.name}; PDF'i yeniden üret)" for y in yapilan]
    pdf = Path(arg["pdf"]) if arg["pdf"] else md.with_suffix(".pdf")
    if arg["pdf"] and not pdf.is_file():
        print(f"PDF yok: {pdf}", file=sys.stderr)
        return 2
    olcum, pdf_metin = None, None
    if pdf.is_file() and md_degisti:
        notlar.append("md düzeltildiği için eski PDF ölçülmedi; PDF'i yeniden üretip tekrar çalıştır")
    elif pdf.is_file():
        olcum = pdf_olc(pdf)
        if olcum is None:
            notlar.append("PDF ölçülemedi (pdftotext/pdfimages yok ya da PDF okunamadı)")
        elif not olcum["metin_var"]:
            notlar.append("PDF'te metin katmanı yok (taranmış olabilir): yazı boyu, sayfa ve PDF içeriği ölçülmedi")
        else:
            r = subprocess.run(["pdftotext", "-enc", "UTF-8", "-layout", str(pdf), "-"], capture_output=True,
                               encoding="utf-8", errors="replace")
            pdf_metin = r.stdout if r.returncode == 0 else None
    try:
        s = denetle(metin, olcum, arg["alan"], arg["dil"], yil, pdf_metin)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 2
    s["md"], s["pdf"], s["notlar"] = str(md), str(pdf) if olcum else "", notlar
    if arg["json"]:
        print(json.dumps(s, ensure_ascii=False, indent=1))
    else:
        yazdir(md.name, s, notlar)
    return {"yayına engel var": 1, "karar için denetim eksik": 3, "tanımlı kapsamda uygun": 0}[s["karar"]]


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
