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

import bisect
import collections
import functools
import html
import itertools
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
ALFABE_SATIR_TAVAN = 10                # karışık alfabe: en çok bu kadar satır ayrı bildirilir, fazlası '+N satır daha'
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
TABLO_SUTUN_TAVAN = 64                 # tablo satırında bakılan en çok sütun (geniş tabloda doğrusal süre; aşılırsa tablo_genis notu düşülür)
ESLESME_TAVAN = 200                    # bir satırda/cümlede bir kural için bakılan en çok eşleşme (çok uzun satırda doğrusal süre; aşılırsa not düşülür)
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
YER_TUTUCU_JETON = re.compile(r"(?<![\w?+\-−×*/=<>])(?<![+\-−×*/=<>]\s)\?{3,}(?![\w?])(?!\s*[+\-−×*/=<>])")
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


# Bu işaretlerden hiçbiri yoksa satır_hazirla'nın biçim temizliği satırı değiştirmez (yalnız boşluk sıkıştırma kalır)
SATIR_OZEL = re.compile(r"[\\$<>\[\]_*|&~{}`\u00a0\u2009\u202f\u2212]|https?:|^\s{0,3}>")


def satir_hazirla(g: str) -> str:
    """Tek satırın görünen metni: NFKC, HTML varlıkları, bağlantı, etiket, LaTeX, Markdown biçim işaretleri."""
    g = unicodedata.normalize("NFKC", html.unescape(g)).translate(ALT_SIMGE)
    if not SATIR_OZEL.search(g):                   # düz düzyazı satırı: biçim temizleme desenlerinin hiçbiri uygulanamaz (hızlı yol)
        if re.match(r"^\s*(?:\|\s*)?:?-{3,}", g):
            return ""
        return re.sub(r"[ \t]+", " ", g).strip()
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
    if re.match(r"^\s*(?:\|\s*)?:?-{3,}", g):
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


@functools.lru_cache(maxsize=8192)
def _hucre_hazirla(h: str) -> str:
    return satir_hazirla(h)


def tablo_ayristir(satirlar: list[dict]) -> list[dict]:
    """Kod dışı Markdown tablo blokları, hücreleri bir kez hazırlanmış olarak: [{blok, hucreler, ayirici}] (tüm tablo kuralları paylaşır)."""
    cikti = []
    for blok in _tablo_bloklari(satirlar):
        hucreler = [[_hucre_hazirla(h) for h in s["ham"].strip().strip("|").split("|", TABLO_SUTUN_TAVAN)[:TABLO_SUTUN_TAVAN]] for s in blok]
        ayirici = [j for j, h in enumerate(hucreler) if all(re.fullmatch(r":?-{3,}:?|", x.strip()) for x in h)]
        cikti.append({"blok": blok, "hucreler": hucreler, "ayirici": ayirici})
    return cikti


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
        hucreler = [[_hucre_hazirla(h) for h in s["ham"].strip().strip("|").split("|", TABLO_SUTUN_TAVAN)[:TABLO_SUTUN_TAVAN]] for s in blok]
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


def tablo_ogretici_haritasi(tbl: list[dict]) -> dict:
    """{satır no: bayrak}: tabloda satırda ✗ ✘ ❌ / unsafe / wrong / yanlış / hatalı / avoid varsa ya da sütun başlığı Yanlış/Wrong/Unsafe/Avoid ise
    o satırdaki hücreler yanlış yazım ÖĞRETİYOR sayılır (ham satır ve sütun-değer satırı için)."""
    harita = {}
    for tb in tbl:
        blok, hucreler, ayirici = tb["blok"], tb["hucreler"], tb["ayirici"]
        baslik = hucreler[0] if ayirici and ayirici[0] == 1 else []
        baslik_bayrak = any(OGR_TABLO_BASLIK.search(h) for h in baslik)
        for j, (s, h) in enumerate(zip(blok, hucreler)):
            if j in ayirici or (baslik and j == 0):
                continue
            if baslik_bayrak or any(OGR_TABLO_HUCRE.search(x) for x in h):
                harita[s["no"]] = True
    return harita


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
# Oranı ölçülmüş yazı tipi aileleri (kutu yüksekliği / punto): standart 14'ün üç ailesi. Belgedeki yazı tiplerinin hepsi bunlardan biriyse
# punto tahmini yalnız o ailelerin oran aralığından yapılır (daha dar); biri bilinmiyorsa genel aralık (KUTU_ORAN_ALT–UST) kullanılır.
YAZI_ORANLARI = [(re.compile(r"^(?:[A-Z]{6}\+)?Helvetica", re.I), 0.925), (re.compile(r"^(?:[A-Z]{6}\+)?Times", re.I), 0.900),
                 (re.compile(r"^(?:[A-Z]{6}\+)?Courier", re.I), 0.786)]
ORAN_PAYI = 0.01        # kutu iki ondalığa yuvarlanır; ±%1 pay


def pdf_yazi_orani(pdf: Path):
    """(alt, üst) kutu/punto oranı ya da None (pdffonts yok, yazı tipi yok ya da bilinmeyen aile var)."""
    if not shutil.which("pdffonts"):
        return None
    r = subprocess.run(["pdffonts", str(pdf)], capture_output=True, text=True)
    if r.returncode != 0:
        return None
    adlar = [satir.split()[0] for satir in r.stdout.splitlines()[2:] if satir.split()]
    if not adlar:
        return None
    oranlar = []
    for ad in adlar:
        bulunan = [o_ for desen, o_ in YAZI_ORANLARI if desen.match(ad)]
        if not bulunan:
            return None
        oranlar.append(bulunan[0])
    return min(oranlar), max(oranlar)

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
            "metin_var": any(kelime), "oran": pdf_yazi_orani(pdf)}


# ── Alan ve biçim tespiti ──
def dil_tahmin(kucuk: str) -> tuple[str, int]:
    temiz = OKUNUS.sub(" ", kucuk)
    puan = {k: say(r"(?<!\w)(?:" + v["sik"] + r")(?!\w)", temiz) for k, v in DIL.items()}
    en = max(puan, key=puan.get)
    return en, puan[en]


# ── Birim dili (F3): paragraf / liste maddesi / tablo satırı / kod bloğu başına tr | en | fr | ? | kod ──
# Durak sözcükler iki dilde de yaygın olanlardan arındırıldı (de, en, on, a, son, ne, but, was, plus bilerek yok).
DURAK = {
    "tr": ("ve bir bu şu için ile olarak gibi çok daha her ama veya ya ise kadar sonra önce olan olur olmalı değil var yok "
           "ancak fakat hem göre arasında üzerinde ilk iki tüm bütün diye da ki mi bunu bunlar onu ona ben sen biz siz "
           "olabilir yapılır edilir").split(),
    "en": ("the and of to in is are were for with that this it be by at from not have has will should can which if when "
           "than then each all after before during may must they you your we our also into more most only other these "
           "those their been does do").split(),
    "fr": ("le la les un une des du et est sont dans pour avec que qui pas ce cette ces au aux sur par mais ou nous vous "
           "ils elles je tu il elle être avoir fait comme sans très aussi ont mon ma mes ton ta tes ses sa").split(),
}
DURAK_TERS: dict[str, list[str]] = {}
for _dil, _liste in DURAK.items():
    for _s in _liste:
        DURAK_TERS.setdefault(_s, []).append(_dil)
OZGU_TR = re.compile(r"[ıİğĞşŞ]")                 # ç ö ü Fransızca/Almancada da var: kanıt sayılmaz
FR_AKSAN = re.compile(r"[éèêëïœùàô]", re.I)        # â î û Türkçede de var (âyet, hâlâ): kanıt sayılmaz
ELISYON = re.compile(r"(?<![^\W\d_])(?:[ldjnsctm]|qu)['’](?=[^\W\d_]{2})", re.I)   # l'hôpital, j'habite, qu'est
JETON = re.compile(r"[^\W\d_]+|\d+|[.!?;:]")       # harf öbeği; rakam ve cümle noktalaması öbek eşleşmesini keser
DIL_EN_AZ_DURAK = 3                                # bundan az durak sözcük ve özgü harf yoksa: '?'
LISTE_BASI = re.compile(r"^\s*(?:[-*+•]|\d+[.)])\s+")
BASKIN_DILLER = ("tr", "en", "fr")


def _birim_dil(metin: str, jeton: list[str]) -> str:
    puan = dict.fromkeys(DURAK, 0)
    for j in jeton:
        for d in DURAK_TERS.get(j, ()):
            puan[d] += 1
    if OZGU_TR.search(metin):
        puan["tr"] += 3
    puan["fr"] += min(len(FR_AKSAN.findall(metin)) + len(ELISYON.findall(metin)), 3)
    en_iyi = max(puan.values())
    adaylar = [d for d, p in puan.items() if p == en_iyi]
    return adaylar[0] if en_iyi >= DIL_EN_AZ_DURAK and len(adaylar) == 1 else "?"


def birim_dil(metin: str) -> str:
    """Tek birimin dili: 'tr' | 'en' | 'fr' | '?' (yetersiz işaret: < 3 durak sözcük ve Türkçe özgü harf yok ya da berabere)."""
    return _birim_dil(metin, JETON.findall(en_kucuk(metin)))


def birim_analizi(satirlar: list[dict], varsayilan: str | None = None) -> tuple[list[dict], str]:
    """Gövdeyi birimlere ayırır: boş satırla ayrılan paragraf; liste maddesi, tablo satırı ve başlık tek birim; kod
    bloğu ayrı birim (dil 'kod'). '?' birimler `varsayilan` dile (yoksa belgenin sözcük ağırlıklı çoğunluk diline;
    çoğunluk da yoksa 'tr') atanır. Dönüş: (birimler, belge_dili); birim: {dil, tur, nolar, metin, kucuk, jeton, kelime}."""
    gruplar: list[tuple[str, list[dict]]] = []
    tampon: list[dict] = []
    tur = ""

    def kapat():
        nonlocal tampon, tur
        if tampon:
            gruplar.append((tur, tampon))
        tampon, tur = [], ""

    for s in satirlar:
        if s["kod"]:
            if tur != "kod":
                kapat()
                tur = "kod"
            tampon.append(s)
            continue
        g = s["gor"]
        if not g.strip():
            kapat()
        elif g.lstrip().startswith("#"):
            kapat()
            gruplar.append(("baslik", [s]))
        elif s["ham"].count("|") >= 2:
            kapat()
            gruplar.append(("tablo", [s]))
        elif LISTE_BASI.match(g):
            kapat()
            tur, tampon = "liste", [s]
        elif tur == "liste" and s["ham"][:1] in (" ", "\t"):
            tampon.append(s)                       # liste maddesinin devam satırı
        else:
            if tur not in ("paragraf",):
                kapat()
                tur = "paragraf"
            tampon.append(s)
    kapat()
    birimler = []
    for tur, ls in gruplar:
        metin = "\n".join(x["tam"] if tur == "kod" else x["gor"] for x in ls)
        kucuk = en_kucuk(metin)
        jeton = JETON.findall(kucuk)
        dil = "kod" if tur == "kod" else _birim_dil(metin, jeton)
        birimler.append({"dil": dil, "tur": tur, "nolar": [x["no"] for x in ls], "metin": metin, "kucuk": kucuk,
                         "jeton": jeton, "kelime": sum(1 for j in jeton if j.isalpha())})
    agirlik = collections.Counter()
    for b in birimler:
        if b["dil"] in BASKIN_DILLER:
            agirlik[b["dil"]] += b["kelime"]
    belge_dili = varsayilan or (agirlik.most_common(1)[0][0] if agirlik else "tr")
    for b in birimler:
        if b["dil"] == "?":
            b["dil"] = belge_dili
    return birimler, belge_dili


def _gor_satirlari(gor: str) -> list[dict]:
    """Yalnız görünen metin verilmişse (kod bloğu bilgisi yok) birim analizi için satır sözlükleri."""
    return [{"no": i, "gor": x, "tam": x, "ham": x, "kod": False} for i, x in enumerate(gor.splitlines(), 1)]


class _Dizin:
    """Bir dilin birleşik metni: jeton listesi (birimler arası '\\0'), jeton sayacı, 2 harf ön ek dizini, ilk sözcük konumları."""
    __slots__ = ("jeton", "metin", "_sayac", "_onek", "_konum")

    def __init__(self, jeton: list[str], metin: str):
        self.jeton, self.metin = jeton, metin
        self._sayac = self._onek = self._konum = None

    @property
    def sayac(self):
        if self._sayac is None:
            self._sayac = collections.Counter(self.jeton)
        return self._sayac

    @property
    def onek(self):
        if self._onek is None:
            self._onek = {}
            for w, n in self.sayac.items():
                if w[:1].isalpha():
                    self._onek.setdefault(w[:2], []).append((w, n))
        return self._onek

    @property
    def konum(self):
        if self._konum is None:
            self._konum = {}
            for i, w in enumerate(self.jeton):
                if w[:1].isalpha():
                    self._konum.setdefault(w, []).append(i)
        return self._konum


def _diziler(birimler: list[dict]) -> dict:
    """tr, en, tum (kod hariç her dil: kısaltmalar), kod. Başlıklar iki kez eklenir (başlık sözcüğü çift sayılır)."""
    jeton = {"tr": [], "en": [], "tum": [], "kod": []}
    metin = {"tr": [], "en": [], "tum": [], "kod": []}
    for b in birimler:
        d = b["dil"]
        tekrar = 2 if b["tur"] == "baslik" else 1
        if d == "kod":
            hedefler = [("kod", b["jeton"], b["kucuk"])]
        else:
            hedefler = [("tum", b["jeton"], b["kucuk"])]
            if d == "tr":
                if "I" in b["metin"]:                    # Türkçede I → ı: ek zinciri eşleşmesi için
                    kt = tr_kucuk(b["metin"])
                    hedefler.append(("tr", JETON.findall(kt), kt))
                else:
                    hedefler.append(("tr", b["jeton"], b["kucuk"]))
            elif d == "en":
                hedefler.append(("en", b["jeton"], b["kucuk"]))
        for ad, j, k in hedefler:
            for _ in range(tekrar):
                jeton[ad].extend(j)
                jeton[ad].append("\0")
                metin[ad].append(k)
    return {ad: _Dizin(jeton[ad], "\n".join(metin[ad])) for ad in jeton}


EK = (r"(?:lik|lık|lük|luk|ci|cı|cu|cü|çi|çı|çu|çü|sal|sel|ler|lar|nin|nın|nun|nün|den|dan|ten|tan|si|sı|su|sü"
      r"|yi|yı|yu|yü|ye|ya|in|ın|un|ün|de|da|te|ta|dir|dır|i|ı|u|ü|e|a)")
YUMUSAMA = {"k": "kğg", "p": "pb", "t": "td", "ç": "çc"}
JETONLU_ANAHTAR = re.compile(r"[^\W\d_]+(?:[ \-]+[^\W\d_]+)*")


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


def _agirliklar(profil: dict, anahtar: str = "sozcukler") -> dict:
    """Aynı sözcük birden çok profilin AYNI listesinde geçiyorsa ağırlığı bölünür (nüfus: coğrafya + sosyal → 0,5)."""
    say_ = {}
    for ad in alan_adlari(profil):
        for s in set(profil[ad].get(anahtar, [])):
            say_[s] = say_.get(s, 0) + 1
    return {s: 1 / n for s, n in say_.items()}


def _sade_sozcukler(sozcukler: list[str]) -> list[str]:
    """Aynı profilde başka bir anahtarla başlayan anahtarı at (hemşire / hemşirelik çift sayılmasın)."""
    return [w for w in sozcukler if not any(v != w and len(v) >= 4 and w.startswith(v) for v in sozcukler)]


@functools.lru_cache(maxsize=4096)
def _desen(s: str):
    return re.compile(sozcuk_deseni(s))


@functools.lru_cache(maxsize=4096)
def _jetonlar(s: str):
    """Anahtarın jetonları (yalnız harf öbekleri ve boşluk/tire ile birleşenler); noktalama/simge içeriyorsa None."""
    return tuple(JETON.findall(s)) if JETONLU_ANAHTAR.fullmatch(s) else None


@functools.lru_cache(maxsize=1024)
def _duz_desen(s: str):
    """Kısaltma/simge: harf-rakamla başlıyorsa önüne, bitiyorsa arkasına sözcük sınırı konur; boşluk esnek."""
    e = re.escape(s).replace(r"\ ", r"\s+")
    return re.compile((r"(?<!\w)" if s[:1].isalnum() or s[:1] == "_" else "") + e
                      + (r"(?!\w)" if s[-1:].isalnum() or s[-1:] == "_" else ""))


def _en_bicimleri(w: str) -> frozenset:
    f = {w, w + "s", w + "es"}
    if len(w) > 2 and w.endswith("y") and w[-2] not in "aeiou":
        f.add(w[:-1] + "ies")
    return frozenset(f)


def _faz_say(dz: _Dizin, j: tuple, son_esles) -> int:
    """Çok jetonlu öbek: ilk ve ara jetonlar aynen, son jeton `son_esles` ile (ek zinciri / çoğul)."""
    k, tok, n = len(j), dz.jeton, 0
    for i in dz.konum.get(j[0], ()):
        if i + k <= len(tok) and all(tok[i + t] == j[t] for t in range(1, k - 1)) and son_esles(tok[i + k - 1]):
            n += 1
    return n


def _say_tr(dz: _Dizin, s: str) -> int:
    j = _jetonlar(s)
    if j is None:
        return len(_desen(s).findall(dz.metin))
    d = _desen(j[-1] if len(j) > 1 else s)
    if len(j) == 1:
        return sum(c for w, c in dz.onek.get(j[0][:2], ()) if d.match(w))
    return _faz_say(dz, j, d.match)


def _say_en(dz: _Dizin, s: str) -> int:
    j = _jetonlar(s)
    if j is None:
        return len(_duz_desen(s).findall(dz.metin))
    if len(j) == 1:
        return sum(dz.sayac.get(f, 0) for f in _en_bicimleri(j[0]))
    return _faz_say(dz, j, _en_bicimleri(j[-1]).__contains__)


def _say_kisaltma(dz: _Dizin, s: str) -> int:
    j = _jetonlar(s)
    if j is None:
        return len(_duz_desen(s).findall(dz.metin))
    if len(j) == 1:
        return dz.sayac.get(j[0], 0)
    return _faz_say(dz, j, j[-1].__eq__)


# (profil anahtarı, dizin, tür: S tek sözcük ağırlık 1 · O öbek ağırlık 2 · K kısaltma ağırlık 1, sayım işlevi)
# Genel klinik laboratuvar sözcükleri beslenmeyi ayırt etmez (tıp notu beslenme sanılıyordu); diyet/porsiyon/kalori/besin sözcükleri tam ağırlıkta kalır
GENEL_LAB_SOZCUK = {"glukoz", "kolesterol", "trigliserit", "lipid", "glikoz", "triglyceride", "cholesterol", "glucose", "fasting",
                    "blood glucose response", "kilo"}     # 'kilo': dozun kiloya göre yazıldığı her notta geçer
GENEL_LAB_AGIRLIK = 0.25
DOZ_YOGUNLUK = re.compile(r"(?<![\d.,])\d[\d.,]*\s*(?:mg|mcg|µg|μg|ünite|units?|IU|İÜ)(?![A-Za-z])|\bmg\s*/\s*kg\b")
FR_EN_AZ_KELIME, FR_ORAN = 15, 0.25
SOZLUK_LISTELERI = (("sozcukler", "tr", "S", _say_tr), ("obekler", "tr", "O", _say_tr),
                    ("sozcukler_en", "en", "S", _say_en), ("obekler_en", "en", "O", _say_en),
                    ("kisaltmalar", "tum", "K", _say_kisaltma),
                    ("kod_sozcukler", "kod", "K", _say_kisaltma))   # yalnız kod bloğunda (def, return, select…)
KOD_LISTELERI = {"sozcukler_en", "obekler_en", "kisaltmalar"}   # kod blokları yalnız bilgisayar alanına ve bu listelerle


def alan_puanlari(gor: str, profil: dict, birimler: list[dict] | None = None) -> tuple[dict, dict]:
    """Dile duyarlı alan puanı: Türkçe listeler yalnız tr birimde, İngilizce listeler yalnız en birimde, kısaltmalar kod
    hariç her birimde; fr ve öteki birimler alan puanına katılmaz; kod blokları yalnız `bilgisayar`a katkı verir.
    Bir etiket (aynı anahtar, tr+en birlikte) puana en çok ALAN_SOZCUK_TAVAN kez katkı verir; öbek ağırlığı 2."""
    basliklar = "\n".join(x for x in gor.splitlines() if x.lstrip().startswith("#"))
    gor2 = gor + "\n" + basliklar                      # başlık sözcükleri çift sayılır (dil puanı için)
    if birimler is None:
        birimler, _ = birim_analizi(_gor_satirlari(gor))
    diz = _diziler(birimler)
    agirlik = {a: _agirliklar(profil, a) for a, _, _, _ in SOZLUK_LISTELERI}
    puanlar, kanit = {}, {}
    genel_lab_katki = 0.0
    for ad in alan_adlari(profil):
        p = profil[ad]
        if not any(p.get(a) for a, _, _, _ in SOZLUK_LISTELERI):
            continue
        etiket: dict[tuple, list] = {}
        for anahtar, dizin_ad, tur, say_ in SOZLUK_LISTELERI:
            liste = p.get(anahtar)
            if not liste:
                continue
            dz, kod = diz[dizin_ad], diz["kod"]
            for s in (liste if anahtar == "kisaltmalar" else _sade_sozcukler(liste)):
                s = s.strip()
                n = say_(dz, s) if dz.jeton else 0
                if ad == "bilgisayar" and anahtar in KOD_LISTELERI and kod.jeton:
                    n += (_say_kisaltma if anahtar == "kisaltmalar" else _say_en)(kod, s)
                if n:
                    e = etiket.setdefault((tur if tur == "O" else "S", s), [0, agirlik[anahtar].get(s, 1)])
                    e[0] += n
        toplam = 0.0
        for (tur, s), (n, w) in etiket.items():
            katki = min(n, ALAN_SOZCUK_TAVAN) * w * (2 if tur == "O" else 1)
            if ad == "beslenme" and s in GENEL_LAB_SOZCUK:
                genel_lab_katki += katki * (1 - GENEL_LAB_AGIRLIK)   # glukoz/kolesterol/lipid genel klinik lab sözcüğüdür: beslenmeyi ayırt etmez
                katki *= GENEL_LAB_AGIRLIK
            toplam += katki
        puanlar[ad], kanit[ad] = round(toplam, 2), [s for _, s in etiket]
    if genel_lab_katki and "tip" in puanlar and genel_lab_katki >= 1:
        puanlar["tip"] = round(puanlar["tip"] + 0.5 * genel_lab_katki, 2)    # ... ama sağlık grubuna işarettir: tıp notuna yarısı yazılır
        kanit.setdefault("tip", []).append("genel klinik lab sözcükleri")
    okunus = len(OKUNUS.findall(gor2))
    kt = tr_kucuk(gor2)
    _, sik = dil_tahmin(kt)
    puanlar["dil"] = round(puanlar.get("dil", 0) + 3 * okunus + (6 if re.search(r"\bokunuş", kt) else 0)
                           + (min(sik, 30) // 3 if okunus else 0), 2)   # sözlük puanı + okunuş işareti
    kanit["dil"] = kanit.get("dil", []) + ([f"{okunus} okunuş /…/"] if okunus else [])
    # (S9) Doz/reçete yazımı dersi: ilaç adı + doz birimi yoğunluğu sağlık işaretidir (en yüksek puanlı sağlık alanına eklenir)
    gorunen = gor[:60000]                           # çok büyük belgede doğrusal süre: ilk 60 KB yeter (yoğunluk ölçüsü)
    doz_n, ilac_n = len(DOZ_YOGUNLUK.findall(gorunen)), len(ILAC_ADI.findall(gorunen))
    if (doz_n >= 3 and (ilac_n >= 1 or len(DOZ_BAGLAM.findall(gorunen)) >= 2)) or doz_n >= 6:
        saglik_ = [a for a in puanlar if a in SAGLIK_ALANLAR]
        if saglik_:
            hedef = max(saglik_, key=lambda a: puanlar[a])
            puanlar[hedef] = round(puanlar[hedef] + min(doz_n, 10) * 0.5 + min(ilac_n, 5), 2)
            kanit.setdefault(hedef, []).append("doz yoğunluğu")
    # (S9) Birimlerin kayda değer kısmı (≥ %25) hedef dil (Fransızca) ise ya da belge Fransızca sözcük listesi ise: dil
    if birimler:
        toplam_k = sum(b["kelime"] for b in birimler if b["dil"] in BASKIN_DILLER)
        fr_k = sum(b["kelime"] for b in birimler if b["dil"] == "fr")
        if toplam_k and fr_k >= FR_EN_AZ_KELIME and fr_k / toplam_k >= FR_ORAN:
            digerler = [v for a, v in puanlar.items() if a != "dil"]
            if puanlar["dil"] <= max(digerler, default=0):
                puanlar["dil"] = round(max(digerler, default=0) + 1, 2)
                kanit["dil"] = kanit.get("dil", []) + [f"hedef dil birimleri %{round(100 * fr_k / toplam_k)}"]
    return puanlar, kanit


def alan_grubu(profil: dict, alan: str) -> str | None:
    for g, liste in profil.get("_alan_gruplari", {}).items():
        if alan in liste:
            return g
    return None


def alan_tespit(meta: dict, gor: str, profil: dict, alan: str | None = None, birimler: list[dict] | None = None) -> dict:
    """Önce --alan, sonra frontmatter `alan:`, sonra sözcük puanı. Çıktıda `grup` her zaman var (seçilen alanın grubu; alan
    'genel' ise grup toplam puanı eşiği geçen en yüksek grup, yoksa None). En iyi alan eşik altında ama sağlık grubunun
    toplamı eşiği geçiyor ve en yüksek gruptaysa: alan `tip`, destek 'zayıf', kaynak 'grup'."""
    secilen = alan or meta.get("alan", "").strip().lower()
    if secilen:
        if secilen not in alan_adlari(profil):
            raise ValueError(f"bilinmeyen alan: {secilen} ({', '.join(alan_adlari(profil))})")
        return {"alan": secilen, "kaynak": "kullanıcı seçimi", "destek": "—", "kanit": [], "ikinci": None,
                "puanlar": {}, "grup": alan_grubu(profil, secilen)}
    puanlar, kanit = alan_puanlari(gor, profil, birimler)
    sira = sorted(puanlar.items(), key=lambda x: -x[1])
    en, p1 = sira[0]
    ust = profil.get(en, {}).get("ust") if en != "dil" else None
    aile_kok = ust or en
    altlar = [(a, puanlar.get(a, 0)) for a in alan_adlari(profil) if profil[a].get("ust") == aile_kok]
    if altlar and en == aile_kok:
        # Beslenme alt alanı yalnız genel klinik lab sözcükleriyle (glukoz, kolesterol, lipid…) doğmaz: diyet/porsiyon/kalori/besin kanıtı ister
        altlar_ = [(a, p_) for a, p_ in altlar if not (a == "beslenme" and all(k in GENEL_LAB_SOZCUK for k in kanit.get(a, [])))]
        alt, pa = max(altlar_, key=lambda x: x[1]) if altlar_ else (None, 0)
        if alt and pa >= ALT_ALAN_EN_AZ and pa >= ALT_ALAN_ORAN * p1:
            en, p1 = alt, max(pa, ALAN_EN_AZ)
    aile = {aile_kok} | {a for a, _ in altlar}
    rakipler = [(a, p) for a, p in sira if a not in aile and a != en]
    rakip_ad, rakip = (rakipler[0] if rakipler else (None, 0))
    ikinci = aile_kok if en != aile_kok and puanlar.get(aile_kok, 0) >= ALAN_EN_AZ else (
        rakip_ad if rakip >= ALAN_EN_AZ else None)
    # Uzun metinde birkaç dağınık sözcük alan kanıtı sayılmaz: eşik her 10 000 sözcükte 1 artar (en çok +8).
    en_az = ALAN_EN_AZ + min(8, len(gor.split()) // 10000)
    if p1 < en_az:
        gruplar = {g: round(sum(puanlar.get(a, 0) for a in liste), 2) for g, liste in profil.get("_alan_gruplari", {}).items()}
        en_grup, gp = max(gruplar.items(), key=lambda x: x[1]) if gruplar else (None, 0)
        grup = en_grup if gp >= en_az else None
        if grup == "saglik":
            sag = sorted((a for a in profil["_alan_gruplari"]["saglik"] if puanlar.get(a)), key=lambda a: -puanlar[a])
            ipucu = [k for a in sag for k in kanit.get(a, [])][:6]
            return {"alan": "tip", "kaynak": "grup", "destek": "zayıf", "kanit": ipucu, "ikinci": None,
                    "puanlar": puanlar, "grup": grup}
        return {"alan": "genel", "kaynak": "tespit", "destek": "zayıf", "kanit": [], "ikinci": en if p1 else None,
                "puanlar": puanlar, "grup": grup}
    destek = ("güçlü" if p1 >= DESTEK_GUCLU * max(rakip, 1) and p1 >= 2 * ALAN_EN_AZ
              else "orta" if p1 >= DESTEK_ORTA * max(rakip, 1) else "zayıf")
    return {"alan": en, "kaynak": "tespit", "destek": destek, "kanit": kanit[en][:6], "ikinci": ikinci,
            "puanlar": puanlar, "grup": alan_grubu(profil, en)}


def bolum_alanlari(govde: str, profil: dict, ana: str, belge_dili: str | None = None) -> list[str]:
    """Karma belge: yeterince uzun bir bölümün en güçlü alanı ana alandan farklıysa ek profil olarak döner."""
    ek = []
    for _, icerik in bolumler(govde):
        satirlar = hazirla_satirlar(icerik)
        gor = "\n".join(x["gor"] for x in satirlar)
        if len(SOZCUK.findall(gor)) < BOLUM_EN_AZ_KELIME:
            continue
        birimler, _ = birim_analizi(satirlar, belge_dili)
        puanlar, _ = alan_puanlari(gor, profil, birimler)
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
BINLIK = r"[1-9]\d{0,2}(?:\.\d{3})+(?![.,]?\d)"        # 0.050 binlik değil (baştaki sıfır)
ARALIK_EK = r"(?:\s*(?:[-–—/]|,\s|\b(?:ve|veya|ya da|ile|or|and|to)\b)\s*\d+(?:[.,]\d+)?)*\s*"
SONDAKI_SIFIR = re.compile(r"(?<![\d.,])(?!" + BINLIK + r")\d+[.,]0+(?!\d)" + ARALIK_EK + ILAC_BIRIM + LAB_PAYDA)
ARALIK_SIFIR = re.compile(r"(?<![\d.,])\d+[.,]0+\s*(?:veya|ya da|ile|or)\s*\d+(?:[.,]\d+)?\s*" + ILAC_BIRIM + LAB_PAYDA)
SONDAKI_SIFIR_G = re.compile(r"(?<![\d.,])(?!" + BINLIK + r")\d+[.,]0+(?!\d)" + ARALIK_EK + GRAM + LAB_PAYDA)
ONDALIK_SONU_SIFIR = re.compile(r"(?<![\d.,])(?!" + BINLIK + r")\d+[.,]\d*[1-9]0+\s*" + ILAC_BIRIM + LAB_PAYDA)
CIPLAK_ONDALIK = re.compile(r"(?<![\d\w.,])[.,]\d+" + ARALIK_EK + "(?:" + ILAC_BIRIM + "|" + GRAM + ")")
OCR_SIFIR = re.compile(r"(?<![\d.,])\d+[.,]\s?[Oo]\s*" + ILAC_BIRIM)
BINLIK_VIRGUL = re.compile(r"(?<![\d.,])\d{1,3},\d{3}(?![\d.,])\s*" + ILAC_BIRIM)
BINLIK_EN = re.compile(r"(?<![\d.,])\d{1,3}(?:,\d{3})+(?!\d)")   # İngilizce birimde virgül binlik ayırıcıdır (1,000 = 1000)
DOZ_IZI = re.compile(r"\d\s*" + ILAC_BIRIM)
OGRETICI_YANLIS = re.compile(r"❌|✗|✘|\byanlış\s*(?:yazım|örnek|kullanım|gösterim)?\s*[:：]|\bhatalı\s*(?:yazım|örnek|kullanım)\s*[:：]"
                             r"|\bwrong\s*:|\bdo not write", re.I)
# Zayıf işaret ('yazılmaz', 'kullanmayın'): yalnız dozun hemen yanında ('5,0 mg yazılmaz', 'kullanmayın: 5,0 mg')
OGRETICI_ZAYIF = r"(?:yazılmaz|yazmayın|kullanmayın|kullanılmaz|do not use)"


def ogretici_satir(t: str) -> bool:
    """Kısaltma/yazım kuralı anlatan satır ('U/IU kullanmayın'): kısaltma ve boşluk uyarısı verilmez."""
    return bool(OGRETICI_YANLIS.search(t) or re.search(r"\b" + OGRETICI_ZAYIF, t, re.I))


# Yazım kuralını anlatan yan cümle ('yanlış yazım örneği: "5,0 mg" yerine "5 mg" yazılmalı', 'Avoid trailing zeros such as "5.0 mg"').
# Kesin işaret: yazımı adlandırır ya da yasaklar; doz aynı yan cümlede, işarete ≤ 80 karakter yakın ve araya başka talimat girmemiş olmalı.
# Zayıf işaret (çıplak 'yanlış', 'wrong', 'avoid'): yalnız doz tırnak içindeyse ya da yan cümlede yazım/sıfır sözü varsa.
# 'Doz: 5,0 mg (yanlış hesaplanmış olabilir)' ya da '(hatalı örnek değil)' öğretici sayılmaz: yazım değil hesap/olumsuz.
OGR_KESIN = re.compile(
    r"\b(?:yanlış|yanlis|hatalı)\s+(?:yazım|yazılış|gösterim|kullanım|örnek|biçim|şekil|doz\s+yazımı)\w*(?!\s*değil)"
    r"|\b(?:wrong|incorrect)\s*[:：]|\b(?:wrong|incorrect)\s+(?:example|notation|format|way|writing|usage)\b"
    r"|\bsondaki\s+sıfır\w*|\btrailing\s+zero\w*"
    r"|\b(?:do\s*not|don['’]t|never|should\s+not\s+be|must\s+not\s+be)\s+(?:be\s+)?(?:write|written|use|used)\b"
    r"|\b(?:yazılmaz|yazılmamalı\w*|yazmayın\w*|yazılmasın)\b", re.I)
OGR_ZAYIF = re.compile(r"\b(?:yanlış|yanlis|hatalı|wrong|incorrect|avoid|hata|hatası|errors?|mistakes?)\b(?!\s*değil)", re.I)
OGR_YAZIM_IZI = re.compile(r"trailing|\bzeros?\b|sıfır|\bwrit(?:e|ten|ing)\b|notation|\bformat\b|yazım|yazılış|yazmak|yazma\b|biçim|gösterim|şekilde yaz",
                           re.I)
# Aynı satırda sorunlu yazımın düzeltilmiş hâli ve bir olumsuzlama/uyarı sözcüğü ('write 0.75 mg, never .75 mg')
OGR_UYARI_SOZ = re.compile(r"\b(?:never|always|do\s+not|don['’]t|avoid|must|should|errors?|mistakes?|misread|misinterpret\w*|tenfold|ten-fold|"
                           r"wrong|incorrect|unsafe|confus\w*|asla|her\s+zaman|kaçın\w*|yazma\w*|yazılmaz|yazılmamalı\w*|yanlış|hata\w*|"
                           r"karıştır\w*|10\s+kat|on\s+kat)\b", re.I)
OGR_TABLO_HUCRE = re.compile(r"[✗✘❌]|\b(?:unsafe|wrong|incorrect|avoid|yanlış|yanlis|hatalı|hatali|asla)\b|\bdo\s+not\b|\bdon['’]t\b", re.I)
OGR_TABLO_BASLIK = re.compile(r"^\W*(?:yanlış|yanlis|hatalı|hatali|wrong|incorrect|unsafe|avoid|bad|kötü|kaçınılacak)\b|[✗✘❌]", re.I)
OGR_ARA = re.compile(r"ardından|sonra|\bthen\b|\bama\b|\bancak\b|\bbut\b|\bhowever\b", re.I)
OGR_TIRNAK = re.compile(r'"[^"\n]*"|“[^”\n]*”|«[^»\n]*»|‘[^’\n]*’|(?<![\w])\'[^\'\n]*\'(?!\w)')


def ogretici_ek(t: str, b: str) -> bool:
    """Yan cümle b dozunun yazımını anlatıyor mu (kesin işaret, ya da tırnaklı/yazım sözlü zayıf işaret)."""
    k = t.find(b)
    if k < 0:
        return False
    tirnakta = any(m.start() <= k and k + len(b) <= m.end() for m in OGR_TIRNAK.finditer(t))
    yerine = re.search(re.escape(b) + r"[\s\"'”»“«)]{0,4}yerine\b[^.;]{0,50}?\byaz\w*", t, re.I)
    if yerine:
        return True
    adaylar = [(m, True) for m in OGR_KESIN.finditer(t)] + \
              [(m, False) for m in OGR_ZAYIF.finditer(t) if tirnakta or OGR_YAZIM_IZI.search(t)]
    for m, kesin in adaylar:
        ara = t[m.end():k] if k >= m.end() else t[k + len(b):m.start()] if k + len(b) <= m.start() else ""
        if len(ara) > 80 or OGR_ARA.search(ara):
            continue
        if kesin or tirnakta or OGR_YAZIM_IZI.search(t):
            return True
    return False


def ogr_duzeltilmis(cumleler_: list[str], i: int, b: str) -> bool:
    """b (sorunlu yazım, örn. '.75 mg', '5,0 mg') i. yan cümlede; aynı birimde düzeltilmiş hâli (0,75 mg / 5 mg) aynı ya da komşu yan cümlede
    geçiyor ve b'nin ya da düzeltilmiş hâlin cümlesinde bir olumsuzlama/uyarı sözcüğü varsa öğreticidir."""
    sayilar = re.findall(r"[.,]?\d+(?:[.,]\d+)?", b)
    birim = re.search(r"([A-Za-zµμ]+)\s*$", b)
    if not sayilar or not birim:
        return False
    b1 = sayilar[0]
    try:
        v = float(b1.replace(",", "."))
    except ValueError:
        return False
    for j in range(max(0, i - 1), min(len(cumleler_), i + 2)):
        if re.search(r"\bnot\b|\bdeğil\b|\binstead\b|\byerine\b", cumleler_[i] + " " + cumleler_[j], re.I) and sifir_esdegeri(cumleler_[j], b):
            return True                                # 'Write 50 mcg, not 0.050 mg': başka birimdeki eşdeğer + olumsuzlama
        if not (OGR_UYARI_SOZ.search(cumleler_[i]) or OGR_UYARI_SOZ.search(cumleler_[j])):
            continue
        for m in re.finditer(r"(?<![\d.,])(\d+(?:[.,]\d+)?)\s*" + re.escape(birim.group(1)) + r"(?![A-Za-z])", cumleler_[j]):
            if m.group(1) == b1 or m.group(0).strip() == b.strip():
                continue
            try:
                if abs(float(m.group(1).replace(",", ".")) - v) < 1e-9:
                    return True
            except ValueError:
                pass
    return False


def sifir_esdegeri(satir: str, b: str) -> str | None:
    """b ('0,050 mg') sondaki sıfırlı; aynı satırda aynı miktarın başka birimdeki eşdeğeri ('50 mcg') var mı: o metni döner."""
    m = re.match(r"(\d+[.,]\d*)\s*(mg|g|mcg|µg|μg)\b", b)
    if not m:
        return None
    try:
        v = float(m.group(1).replace(",", "."))
    except ValueError:
        return None
    kat = {"g": 1e6, "mg": 1e3, "mcg": 1.0, "µg": 1.0, "μg": 1.0}
    for q in re.finditer(r"(?<![\d.,])(\d+(?:[.,]\d+)?)\s*(mg|g|mcg|µg|μg)\b", satir):
        if q.group(2) == m.group(2) or q.group(0) == b:
            continue
        try:
            w = float(q.group(1).replace(",", "."))
        except ValueError:
            continue
        if abs(w * kat[q.group(2)] - v * kat[m.group(2)]) <= 1e-6 * max(1.0, v * kat[m.group(2)]):
            return q.group(0)
    return None


def ogretici_mi(t: str, b: str) -> bool:
    if ogretici_ek(t, b):
        return True
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


def satir_dili(c, no) -> str:
    """Satırın birim dili (tr/en/fr/kod); bilinmiyorsa (PDF metni, birleşik satır) belge dili."""
    return (c.get("satir_dili") or {}).get(no) or c.get("belge_dili") or "tr"


def en_binlik_sil(t: str) -> str:
    return BINLIK_EN.sub(lambda m: m.group(0).replace(",", ""), t)


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
        en_satir = satir_dili(c, st0["no"]) == "en"
        yan_liste = yan_cumleler(st0["tam"])
        if en_satir:
            yan_liste = [en_binlik_sil(x) for x in yan_liste]   # '1,000 mg' İngilizce satırda 1000 mg: sondaki sıfır/virgül kuralı uygulanmaz
        for yan_i, t in enumerate(yan_liste):
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
                if ogretici_mi(t, b) or st0.get("ogretici") or ogr_duzeltilmis(yan_liste, yan_i, b):
                    ekle("Doğruluk", "UYARI", f"Yanlış doz yazımı öğretici örnek olarak işaretli ({b})",
                         "Doğrusunun hemen yanında olduğundan emin ol", ornek=b, satir=st["no"])
                else:
                    ekle("Doğruluk", "ENGEL", f"Doz yazımında sondaki sıfır ya da baştaki sıfırsız ondalık ({b})",
                         "5,0 mg → 5 mg; ,5 mg → 0,5 mg. Virgül görülmezse 10 kat doz hatası (ISMP)", ornek=b, satir=st["no"])
            for m in ([] if HAZIRLAMA.search(t) else ONDALIK_SONU_SIFIR.finditer(t)):
                esdeger = sifir_esdegeri(st0["tam"], m.group(0))
                if esdeger and not (ogretici_mi(t, m.group(0)) or st0.get("ogretici") or ogr_duzeltilmis(yan_liste, yan_i, m.group(0))):
                    ekle("Doğruluk", "ENGEL", f"Doz yazımında sondaki sıfır ({m.group(0)}); aynı satırda eşdeğeri var ({esdeger}): küçük birimle yaz",
                         "0,050 mg → 50 mcg (ya da 0,05 mg): sondaki sıfır 10 kat doz hatasına yol açar (ISMP)", ornek=m.group(0), satir=st["no"])
                    continue
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
BITISIK_DOZ = re.compile(r"(?<![\w.,])\d+(?:[.,]\d+)?(?:mg|mcg|mL|ml|ünite|IU)\b|(?<![a-zçğıöşüA-ZÇĞİÖŞÜ])[a-zçğıöşüA-ZÇĞİÖŞÜ]{3,}\d+(?:[.,]\d+)?\s*(?:mg|mcg|mL)\b")


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
            zaman_var = None                          # cümle başına bir kez (her eşleşmede yeniden taramak karesel süreydi)
            for sira, m in enumerate(MGKG.finditer(cm)):
                if sira >= ESLESME_TAVAN:
                    ekle("Doğruluk", "UYARI", f"Satır çok uzun: ilk {ESLESME_TAVAN} kiloya göre doz bakıldı, sonrası taranmadı",
                         "Satırı böl", ornek=m.group(0), satir=st["no"])
                    break
                ek_birim = (m.group(1) or "").lower()
                if ek_birim == "d":
                    ekle("Doğruluk", "UYARI", f"'mg/kg/d': d gün mü doz mu belirsiz ({m.group(0)})",
                         "'mg/kg/gün' ya da 'mg/kg/doz' diye açık yaz", ornek=m.group(0), satir=st["no"])
                elif not ek_birim:
                    if zaman_var is None:
                        zaman_var = bool(ZAMAN.search(cm))
                    if not zaman_var:
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
BIRIM_KAT = {"g": 1e6, "mg": 1e3, "mcg": 1.0, "µg": 1.0, "μg": 1.0, "ng": 1e-3}
BIRIM_DONUSUM = re.compile(SAYI + r"\s*(g|mg|mcg|µg|μg|ng)(?![A-Za-z])((?:\s{0,2}/\s{0,2}[A-Za-zçğıöşü²0-9]{1,8})?)\s*(?:=|≈|eşittir|equals?)\s*"
                           + SAYI + r"\s*(g|mg|mcg|µg|μg|ng)(?![A-Za-z])((?:\s{0,2}/\s{0,2}[A-Za-zçğıöşü²0-9]{1,8})?)")


def _yakin(a: float, b: float) -> bool:
    return abs(a - b) <= ARITMETIK_TOLERANS * max(abs(a), abs(b), 1e-9)


ONDALIK_NOKTA = re.compile(r"decimal point|nokta\s+ondalık|ondalık\s+(?:ayırıcı|ayracı|işareti)\s+(?:olarak\s+)?nokta", re.I)


EN_BINLIK_SAYI = re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?")


def sayi_dil(s: str, en: bool = False) -> float:
    """İngilizce satırda '1,150' = 1150 (virgül binlik); Türkçede sayi() ile aynı (1,150 = 1,15)."""
    s = s.strip()
    if en and EN_BINLIK_SAYI.fullmatch(s):
        return float(s.replace(",", ""))
    return sayi(s)


def sayi_adaylari(s: str, nokta_ondalik: bool = False, en: bool = False) -> list[float]:
    """'1.125' Türkçede 1125, İngilizcede 1,125 olabilir: belirsizse iki yorum da döner (ENGEL ancak ikisi de tutmazsa).
    Belge noktanın ondalık olduğunu açıkça söylüyorsa ('decimal point', 'nokta ondalık') yalnız ondalık yorum."""
    s = s.strip()
    if en and EN_BINLIK_SAYI.fullmatch(s):
        return [sayi_dil(s, True)]
    if re.fullmatch(r"[1-9]\d{0,2}\.\d{3}", s):
        return [float(s)] if nokta_ondalik else [float(s.replace(".", "")), float(s)]
    return [sayi(s)]


def _herhangi(adaylar, kosul) -> bool:
    import itertools
    return any(kosul(*x) for x in itertools.product(*adaylar))


HACIM_B = {"ml"}


KILO_BASLIK = re.compile(r"(?<![/\w])kg\b(?!\s*/)|\b(?:weight|ağırlık|kilo|vücut ağırlığı)\b", re.I)
PERKG_BIRIM = re.compile(r"(mg|mcg|µg|μg|g|ünite|units?|iu|iü|u)\s*/\s*kg\b", re.I)
PERKG_HUCRE = re.compile(r"^(mg|mcg|µg|μg|g|ünite|units?|iu|iü|u)\s*/\s*kg\b", re.I)
DOZ_BASLIK = re.compile(r"\b(?:doz|dose|dosage|dosis)\b", re.I)
DOZ_BASLIK_BIRIM = re.compile(r"\(\s*(mg|mcg|µg|μg|g|ünite|units?|iu|iü|u)(?:\s*/\s*(?:h|hr|saat|sa|dk|min|gün|day|doz|dose))?\s*\)", re.I)
ZAMAN_BASLIK = re.compile(r"/\s*(h|hr|saat|sa|dk|min|gün|day|doz|dose)\b\s*(?:\)|$)", re.I)
DOZ_DISLA = re.compile(r"\b(?:max|maks|maksimum|maximum|azami|tavan|ceiling|limit|volume|hacim|hız|rate|ml)\b|en fazla|en çok|üst sınır",
                       re.I)
GUNLUK_IZ = re.compile(r"/\s*(?:gün|day|24)|\bgünlük|\bdaily|\bper day|\bgünde|\btoplam|\btotal", re.I)
HUCRE_SAYI = re.compile(r"^[~≈]?\s*(\d[\d.,]*)\s*(.*)$")
DOZ_BIRIM_ADI = {"mg": "mg", "mcg": "mcg", "µg": "µg", "μg": "µg", "g": "g", "ünite": "ünite", "unit": "ünite",
                 "units": "ünite", "iu": "ünite", "iü": "ünite", "u": "ünite"}


def _tablo_bloklari(satirlar: list[dict]) -> list[list[dict]]:
    sat = _borusuz_tablo(satirlar)
    bloklar, i = [], 0
    while i < len(sat):
        if sat[i]["kod"] or not sat[i]["ham"].lstrip().startswith("|"):
            i += 1
            continue
        blok = []
        while i < len(sat) and not sat[i]["kod"] and sat[i]["ham"].lstrip().startswith("|"):
            blok.append(sat[i])
            i += 1
        bloklar.append(blok)
    return bloklar


def _hucre_oku(h: str):
    """'70 kg' → ('70', 'kg'); aralık ('10-15'), sayısız ya da birden çok sayılı hücre → None."""
    m = HUCRE_SAYI.match(h.strip())
    if not m or re.match(r"[-–—]\s*\d|\d", m.group(2)) or re.search(r"\d\s*[-–—/]\s*\d", h):
        return None
    return m.group(1).rstrip(".,"), m.group(2).strip()


def tablo_doz_hatalari(c) -> list[tuple]:
    """Markdown tabloda kilo × (kiloya göre doz) = doz denetimi. Başlıklardan biri kilo (kg / weight / ağırlık), biri kiloya
    göre doz (mg/kg ...; başlıkta ya da hücrede), biri doz (mg/mcg; başlıkta ya da hücrede) olan tabloda her veri
    satırı hesaplanır. Belirsizse (birden çok aday sütun, günlük/doz başına uyuşmazlığı, aralık hücre) satır/tablo atlanır."""
    hatalar = []
    for tb in c["tbl"]:
        blok, hucreler, ayirici = tb["blok"], tb["hucreler"], tb["ayirici"]
        if not ayirici or ayirici[0] != 1:
            continue
        baslik = hucreler[0]
        veri = [(s, h) for j, (s, h) in enumerate(zip(blok, hucreler)) if j > 1 and j not in ayirici]
        if not veri:
            continue

        def sutun(k):
            return [h[k] for _, h in veri if k < len(h) and h[k].strip()]

        kilo, perkg, doz = [], [], []
        for k, b in enumerate(baslik):
            ornek_hucre = sutun(k)[:3]
            if PERKG_BIRIM.search(b) or (ornek_hucre and all(PERKG_HUCRE.match((_hucre_oku(x) or ("", ""))[1]) for x in ornek_hucre)):
                perkg.append(k)
            elif KILO_BASLIK.search(b):
                kilo.append(k)
            elif (DOZ_BASLIK.search(b) or DOZ_BASLIK_BIRIM.search(b)) and not DOZ_DISLA.search(b):
                doz.append(k)
        if len(kilo) != 1 or len(perkg) != 1 or len(doz) != 1:
            continue
        kk, pk, dk = kilo[0], perkg[0], doz[0]
        if bool(GUNLUK_IZ.search(baslik[pk])) != bool(GUNLUK_IZ.search(baslik[dk])):
            continue
        zp, zd = ZAMAN_BASLIK.search(baslik[pk]), ZAMAN_BASLIK.search(baslik[dk])
        if bool(zp) != bool(zd) or (zp and Y_ZAMAN.get(zp.group(1).lower(), zp.group(1).lower()) != Y_ZAMAN.get(zd.group(1).lower(), zd.group(1).lower())):
            continue                      # oran saatlik/dakikalık, sonuç değil (ya da tersi): başka büyüklük
        b_birim = PERKG_BIRIM.search(baslik[pk])
        d_birim = DOZ_BASLIK_BIRIM.search(baslik[dk])
        for s, h in veri:
            if max(kk, pk, dk) >= len(h):
                continue
            k_ = _hucre_oku(h[kk])
            p_ = _hucre_oku(h[pk])
            d_ = _hucre_oku(h[dk])
            if not (k_ and p_ and d_) or k_[1].lower() not in ("", "kg"):
                continue
            if re.search(r"\d|\bper\b|günlük|daily|once|q\d|\bhr\b", d_[1] + " " + p_[1], re.I) or re.search(r"\(\s*q\d+h|günde|daily", h[pk] + " " + h[dk], re.I):
                continue                      # sıklık/etiketli ya da ikinci sonuçlu hücre: satır motoru (kg_yapisal) etiketine göre denetler
            pm = PERKG_HUCRE.match(p_[1])
            u1 = DOZ_BIRIM_ADI.get((pm.group(1) if pm else (b_birim.group(1) if b_birim else "")).lower())
            dm = re.match(r"^(mg|mcg|µg|μg|g|ünite|units?|iu|u)\b", d_[1], re.I)
            u2 = DOZ_BIRIM_ADI.get((dm.group(1) if dm else (d_birim.group(1) if d_birim else "")).lower())
            if not u1 or not u2 or (p_[1] and not pm) or (d_[1] and not dm):
                continue
            k1, k2 = BIRIM_KAT.get(u1), BIRIM_KAT.get(u2)
            if u1 != u2 and not (k1 and k2):
                continue
            en = satir_dili(c, s["no"]) == "en"
            ad = [sayi_adaylari(k_[0], en=en), sayi_adaylari(p_[0], en=en), sayi_adaylari(d_[0], en=en)]
            kat1, kat2 = (k1, k2) if u1 != u2 else (1.0, 1.0)
            if _herhangi(ad, lambda a, b, d: _yakin(a * b * kat1, d * kat2)):
                continue
            hesap = sayi_dil(k_[0], en) * sayi_dil(p_[0], en) * kat1 / kat2
            ornek = f"{h[kk].strip()} × {h[pk].strip()}{'' if p_[1] else ' ' + u1 + '/kg'} = {h[dk].strip()}"
            hatalar.append((ornek, f"{hesap:g} {u2}", s["no"]))
    return hatalar


# Düzyazıda doz hesabı: '×'/'=' olmadan tek yan cümlede kilo (W kg) + kiloya göre doz (R mg/kg[/doz|/gün]) + sonuç doz (D).
# D yalnız fiil/ipucu yanındaysa sayılır ('give 80 mg', '300 mg verilir', 'toplam 450 mg', 'dose of 80 mg'); 'en fazla/maximum' sayısı D değildir.
KG_AGIRLIK = re.compile(SAYI + r"\s*kg(?![\w/])", re.I)
KG_ORAN = re.compile(SAYI + r"\s*(mg|mcg|µg|μg|g)\s*/\s*kg(?:\s*/\s*(doz|dose|gün|day|d|h|hr|saat|sa)(?![\w])|\s+per\s+(dose|day|hour)\b)?(?![\w/])", re.I)
KG_DOZ_SAAT = re.compile(SAYI + r"\s*(mg|mcg|µg|μg|g)\s*/\s*(?:h|hr|saat|sa|hour)(?![\w])", re.I)
KG_DOZ = re.compile(SAYI + r"\s*(mg|mcg|µg|μg|g)(?![\w/])", re.I)
KG_TAVAN = re.compile(r"en\s+fazla|en\s+çok|\bmaksimum\b|\bmaks\b|\bmax\b|\bmaximum\b|tavan|azami|not\s+exceed|\bceiling\b|üst\s+sınır|\bup\s+to\b"
                      r"|\blimit\b|\bexceed", re.I)
KG_TAVAN_SONRA = re.compile(r"^\s*(?:['’]\w+\s*)?(?:is\s+the\s+(?:max|ceiling)|\bmax|\bmaks|en\s+fazla|tavan|ceiling|'?[ıiuü]?\s*(?:geç|aş)\w*)", re.I)
KG_ONCE_IPUCU = re.compile(r"(?:\b(?:give|gives|giving|administer|administered|ver|verin|uygula|uygulayın)(?:\s+[^\W\d]+){0,2}"
                           r"|\btotal(?:\s+dose)?(?:\s+(?:of|is))?|\bcalculated\s+(?:as|to\s+be)|\bcomes?\s+to|\bworks?\s+out\s+to|\btoplam(?:\s+doz)?|\bdose\s+(?:of|is)\b|\bof\b|\bis\b|→|->)\s*$", re.I)
KG_SONRA_IPUCU = re.compile(r"^\W{0,3}(?:[^\W\d]+\s+){0,3}(?:(?:olarak\s+)?hesaplan\w*|bulun\w*|verilir|verilmeli\w*|verilecek|ver\b|verin|uygula\w*|give\w*)", re.I)
KG_GUNLUK = re.compile(r"\bper\s+day\b|\bdaily\b|/\s*day\b|\bgünlük\b|/\s*gün\b", re.I)
KG_BOL = (2, 3, 4, 6)
KG_DOZ_ADI = re.compile(r"\b(?:doz|dose|dosage)\w*\W{0,4}(?:(?:is|of|olarak|başına)\W{0,4})?$", re.I)


def kg_duzyazi(t: str, nok: bool, en: bool):
    """(ifade, doğrusu, düzey) ya da None. Belirsizse (birden çok kilo/oran/doz adayı, aralık, birim) None."""
    if KG_HESAP[0].search(t) or KG_HESAP[1].search(t):
        return None                                  # '×' / '=' biçimi başka yolda denetleniyor
    kilolar, oranlar = list(KG_AGIRLIK.finditer(t)), list(KG_ORAN.finditer(t))
    if len(kilolar) != 1 or len(oranlar) != 1:
        return None
    w, r = kilolar[0], oranlar[0]
    if re.search(r"\d\s*[-–—]\s*$", t[:r.start(1)]) or re.match(r"\s*[-–—]\s*\d", t[r.end():]) \
            or re.search(r"\d\s*[-–—]\s*$", t[:w.start(1)]) or re.match(r"\s*[-–—]\s*\d", t[w.end():]):
        return None                                  # aralık ('10-15 mg/kg')
    sonek = (r.group(3) or r.group(4) or "").lower()
    if sonek == "d":
        return None                                  # 'mg/kg/d' belirsizliği doz_kg_belirsiz'de
    saatlik = sonek in ("h", "hr", "saat", "sa", "hour")
    adaylar = []
    for d in (KG_DOZ_SAAT if saatlik else KG_DOZ).finditer(t):
        if d.start() < r.end() and d.end() > r.start() or d.start() < w.end() and d.end() > w.start():
            continue                                 # oranın/kilonun kendi sayısı
        onceki, sonraki = t[:d.start()], t[d.end():]
        tavan = None
        for tm in KG_TAVAN.finditer(onceki):
            ara = onceki[tm.end():]
            if len(ara) <= 40 and not re.search(r"\d|[,;]|\b(?:give|ver\w*|uygula\w*)\b", ara):
                tavan = tm
        if tavan or KG_TAVAN_SONRA.match(sonraki):
            continue
        if KG_ONCE_IPUCU.search(onceki) or KG_SONRA_IPUCU.match(sonraki):
            adaylar.append(d)
    if len(adaylar) != 1:
        return None
    d = adaylar[0]
    b1, b2 = r.group(2).lower().replace("μ", "µ"), d.group(2).lower().replace("μ", "µ")
    k1, k2 = BIRIM_KAT.get(b1), BIRIM_KAT.get(b2)
    if not (k1 and k2):
        return None
    ad = [sayi_adaylari(w.group(1), nok, en), sayi_adaylari(r.group(1), nok, en), sayi_adaylari(d.group(1), nok, en)]
    hesap = sayi_dil(w.group(1), en) * sayi_dil(r.group(1), en) * k1 / k2

    def uyar(bolen=1):
        return _herhangi(ad, lambda a, b, x: _yakin(a * b * k1 / bolen, x * k2))
    gunluk = sonek in ("gün", "day") or (not sonek and bool(KG_GUNLUK.search(t)))
    ifade = f"{w.group(0).strip()} × {r.group(0).strip()} → {d.group(0).strip()}"
    dogru = f"{hesap:g} {b2}"
    if saatlik:
        return None if uyar() else (ifade, dogru + "/saat", "ENGEL")
    if sonek in ("doz", "dose"):
        return None if uyar() else (ifade, dogru, "ENGEL")
    if gunluk:
        return None if any(uyar(n) for n in (1,) + KG_BOL) else (ifade, dogru + " (günlük toplam; bölünmüşse ÷2/3/4/6)", "ENGEL")
    if not sonek and KG_DOZ_ADI.search(t[:r.start()]):
        return None if uyar() else (ifade, dogru, "ENGEL")     # 'Önerilen doz 5 mg/kg': oran doz başınadır
    return None if uyar() else (ifade, dogru, "UYARI")


# ── Yapısal doz hesabı (v2.1.1): bir birimde kilo + kiloya göre doz + sonuç doz ──
# Birim = paragraf (satır sonları birleşik), liste maddesi ya da tablo satırı. Bağlaç/ipucu sözcüğü aranmaz: yapı aranır.
# İpucu yalnız belirsizliği giderir (ENGEL mi UYARI mı). Belirsizse (iki kilo, iki oran, iki ilaç) ENGEL verilmez.
Y_BIRIM = {"g": ("kutle", 1e6), "mg": ("kutle", 1e3), "mcg": ("kutle", 1.0), "µg": ("kutle", 1.0), "μg": ("kutle", 1.0),
           "ug": ("kutle", 1.0), "ng": ("kutle", 1e-3), "ünite": ("unite", 1.0), "unite": ("unite", 1.0), "unit": ("unite", 1.0),
           "units": ("unite", 1.0), "u": ("unite", 1.0), "iu": ("unite", 1.0), "iü": ("unite", 1.0), "meq": ("meq", 1.0),
           "mmol": ("mmol", 1.0), "ml": ("hacim", 1.0)}
Y_SAYI = r"\d+(?:[.,]\d+)*"
Y_ZAMAN = {"h": "saat", "hr": "saat", "hrs": "saat", "hour": "saat", "hours": "saat", "saat": "saat", "sa": "saat",
           "min": "dk", "dk": "dk", "dak": "dk", "minute": "dk", "minutes": "dk", "dakika": "dk",
           "gün": "gun", "gun": "gun", "day": "gun", "24h": "gun", "24": "gun", "24saat": "gun",
           "doz": "doz", "dose": "doz", "dozda": "doz"}
Y_KAN = re.compile(r"(?<![\w.,])(" + Y_SAYI + r")\s*[-]?\s*(?:kg|kilogram|kilo)(?![\w/²])", re.I)
Y_MIKTAR = re.compile(
    r"(?<![\w.,])(?P<s1>" + Y_SAYI + r")(?:\s*(?P<ar>[-–—]|\bto\b)\s*(?P<s2>" + Y_SAYI + r"))?\s*"
    r"(?P<b>(?i:mcg|µg|μg|ug|mg|ng|mEq|mmol|mL|IU|İÜ|ünite|unite|units?)|g|U)(?![A-Za-zÇĞİÖŞÜçğıöşü])"
    r"(?P<pay>(?:\s{0,2}/\s{0,2}[A-Za-zçğıöşüÇĞİÖŞÜ²0-9]{1,12}){0,2}(?:\s+per\s+[A-Za-z]{2,8})?)")
Y_PAY = re.compile(r"/\s*([A-Za-zçğıöşüÇĞİÖŞÜ²0-9]+)|\bper\s+([A-Za-z]+)", re.I)
Y_TAVAN_ON = re.compile(KG_TAVAN.pattern + r"|\bmax\b", re.I)
Y_GUC = re.compile(r"^[\s'’-]{0,3}(?:l[ıiuü]k\b|tablet|tab\b|tabs\b|capsule|cap\b|caps\b|kapsül|ampul|ampoule|vial|flakon|şurup|syrup|"
                   r"süspansiyon|suspension|patch|yama|damla|drops?|sachet|saşe|suppository|fitil|strength|gücünde)", re.I)
Y_GUC_ON = re.compile(r"(?:tablets?|capsules?|vials?|ampoules?|kapsül|tablet|flakon|ampul)\s*(?:of|gücü|strength|:)?\s*$|strength\s*(?:of|:)?\s*$", re.I)
Y_SEYRELTME = re.compile(r"^\s*(?:in|into|içinde|içine|ile|diluted\s+in|added\s+to|dissolved\s+in|mixed\s+with)\s+\d[\d.,]*\s*(?:mL|ml|L\b|litre)", re.I)
Y_GUNLUK_ON = re.compile(r"(?:günlük|daily|per\s+day|a\s+day)\W{0,12}$", re.I)
Y_ROL_ON = re.compile(r"(?:each|every|per|single|her|tek)\s+(?:[\w-]+\s+){0,2}?(?:dose|doz|infusion|injection|bolus|administration|infüzyon|enjeksiyon|uygulama)\w*\W{0,12}(?:[^\W\d]+\W{1,12}){0,3}$"
                      r"|(?:doz|dose)\s+başına\W{0,8}$|(?:her\s+doz\w*)\W{0,12}$", re.I)
Y_SAAT_ON = re.compile(r"(?:\bsaatte|saat\s+başına|\bper\s+hour|\ban\s+hour|\beach\s+hour|\bhourly|\bsaatlik)\W{0,6}$", re.I)
Y_SAAT_SON = re.compile(r"^\s*(?:per\s+hour|an\s+hour|hourly|saatte)\b", re.I)
Y_DK_ON = re.compile(r"(?:\bdakikada|\bper\s+minute|\ba\s+minute|\bdakikalık)\W{0,6}$", re.I)
Y_DK_SON = re.compile(r"^\s*(?:per\s+minute|a\s+minute|dakikada)\b", re.I)
Y_ROL_SON = re.compile(r"^\s*(?:per\s+dose|each\s+dose|per\s+administration|(?:her\s+)?doz\s+başına|her\s+dozda|/\s*doz|/\s*dose)", re.I)
Y_GUN_SON = re.compile(r"^\s*(?:per\s+day|a\s+day|daily|each\s+day|günlük|toplam\s+günlük|/\s*gün|/\s*day)", re.I)
Y_IPUCU_ON = re.compile(r"(?:\b(?:give|gives|giving|given|administer\w*|dose|doz\w*|total|toplam|calculated|hesapl\w*|ver\w*|uygula\w*|"
                        r"therefore|thus|that\s+is|so|olur|eder)\b)\W{0,12}(?:\w+\W{0,12}){0,2}$", re.I)
Y_IPUCU_SON = re.compile(r"^\W{0,4}(?:\w+\s+){0,3}(?:ver\w*|uygula\w*|hesapl\w*|give\w*|administer\w*|olarak|iv\b|im\b|po\b|sc\b|oral)", re.I)
Y_SIKLIK = [
    (re.compile(r"\bq\.?\s?(\d{1,2})\s?h\b", re.I), lambda m: 24 / int(m.group(1)) if int(m.group(1)) else None),
    (re.compile(r"(?:her|every)\s+(\d{1,2})\s*(?:saat|hours?|h)\b", re.I), lambda m: 24 / int(m.group(1)) if int(m.group(1)) else None),
    (re.compile(r"\b(\d{1,2})\s*saatte\s+bir", re.I), lambda m: 24 / int(m.group(1)) if int(m.group(1)) else None),
    (re.compile(r"günde\s+(\d{1,2})\s*(?:kez|defa|kere|doz|öğün)", re.I), lambda m: int(m.group(1))),
    (re.compile(r"günde\s+(bir|iki|üç|dört|beş|altı)\s*(?:kez|defa|kere|doz|öğün)", re.I),
     lambda m: {"bir": 1, "iki": 2, "üç": 3, "dört": 4, "beş": 5, "altı": 6}[m.group(1).lower()]),
    (re.compile(r"\b(once|twice|three\s+times|four\s+times)\s+(?:a\s+day|daily|per\s+day)", re.I),
     lambda m: {"once": 1, "twice": 2, "three times": 3, "four times": 4}[re.sub(r"\s+", " ", m.group(1).lower())]),
    (re.compile(r"\b(?:divided|split)\s+(?:in|into)\s+(\d)\s+(?:equal\s+)?doses?", re.I), lambda m: int(m.group(1))),
    (re.compile(r"\b(?:bölünerek|bölünmüş)\s+(\d)\s+doz", re.I), lambda m: int(m.group(1))),
    (re.compile(r"\b(qd|od)\b", re.I), lambda m: 1), (re.compile(r"\bbid\b", re.I), lambda m: 2),
    (re.compile(r"\btid\b", re.I), lambda m: 3), (re.compile(r"\bqid\b", re.I), lambda m: 4),
]
Y_N_IZINLI = (1, 2, 3, 4, 6, 8, 12)
Y_DOZ_SOZU = re.compile(r"\b(?:doz|dose|dosage|dosis)\w*", re.I)
Y_CUMLE_SINIR = re.compile(r"(?<=[.!?;])\s+(?=[A-ZÇĞİÖŞÜ0-9(])")
Y_METIN_TAVAN = 30000               # kg_yapisal bir birimin en çok bu kadar karakterine bakar
Y_SINIR = 40                       # bir birimde bakılan en çok kilo/oran/doz sayısı (çok uzun satırda doğrusal süre)


def _y_ay(s: str, nok: bool, en: bool) -> list[float]:
    try:
        ay = sayi_adaylari(s, nok, en)
        # satırın dili kısa metinde yanlış tahmin edilebilir: '6,000' hem 6 hem 6000 olabilir; ENGEL ancak ikisi de tutmazsa
        if not en and re.fullmatch(r"[1-9]\d{0,2}(?:,\d{3})+", s.strip()):
            ay = ay + [float(s.strip().replace(",", ""))]
        return ay
    except ValueError:
        return []


def _y_birim(b: str):
    b = b.replace("İ", "i").lower().replace("μ", "µ")
    return Y_BIRIM.get(b)


def _y_pay(metin: str):
    """Paydadan (perkg, zaman, belirsiz, yogun): zaman 'saat'/'dk'/'gun'/'doz'/None; belirsiz: 'mg/kg/d'; yogun: mg/mL."""
    perkg, zaman, belirsiz, yogun, taninmayan = False, None, False, False, False
    for m in Y_PAY.finditer(metin):
        t = (m.group(1) or m.group(2) or "").lower()
        if t == "kg":
            perkg = True
        elif t == "d":
            belirsiz = True
        elif t in Y_ZAMAN:
            zaman = Y_ZAMAN[t]
        elif t in ("ml", "dl", "l", "m2", "m²", "cm2", "cm²", "mm", "tablet", "tab"):
            yogun = True
        else:
            taninmayan = True
    return perkg, zaman, belirsiz, yogun, taninmayan


def y_miktarlar(t: str, nok: bool, en: bool):
    """Birimdeki kilolar, kiloya göre oranlar ve aday doz miktarları. (kilolar, oranlar, adaylar, belirsiz_mi, kesildi_mi)"""
    kilolar, oranlar, adaylar, belirsiz, kesildi = [], [], [], False, False
    for i, m in enumerate(Y_KAN.finditer(t)):
        if i >= Y_SINIR:
            kesildi = True
            break
        kilolar.append({"bas": m.start(1), "son": m.end(), "ay": _y_ay(m.group(1), nok, en), "s": m.group(1)})
    for i, m in enumerate(Y_MIKTAR.finditer(t)):
        if i >= 4 * Y_SINIR:
            kesildi = True
            break
        b = _y_birim(m.group("b"))
        if not b:
            continue
        perkg, zaman, bel, yogun, tanimayan = _y_pay(m.group("pay") or "")
        aralik = bool(m.group("ar"))
        q = {"bas": m.start(), "son": m.end(), "aile": b[0], "kat": b[1], "birim": m.group("b").replace("İ", "i").lower().replace("μ", "µ"),
             "ay": _y_ay(m.group("s1"), nok, en), "ay2": _y_ay(m.group("s2"), nok, en) if aralik else None,
             "perkg": perkg, "zaman": zaman, "yogun": yogun, "tanimayan": tanimayan, "ham": m.group(0).strip(),
             "tarih": bool(re.match(r"\d{1,2}\s*[-–]\s*\d{1,2}", m.group(0)) and not m.group("pay"))}
        if bel and perkg:
            belirsiz = True
            continue
        if not q["ay"]:
            continue
        if perkg and not yogun:
            oranlar.append(q)
        elif not perkg and not yogun and not tanimayan:
            adaylar.append(q)
    return kilolar, oranlar, adaylar, belirsiz, kesildi


def _y_ilac_konumlari(t: str):
    cikti = []
    for i, m in enumerate(ILAC_ADI.finditer(t)):
        if i >= 40:
            break
        cikti.append((m.start(), m.end(), re.sub(r"[ıİI]", "i", m.group(0)).lower()[:6]))
    return cikti


def _y_en_yakin_ilac(konumlar, bas: int, son: int):
    en, fark = None, 10 ** 9
    for b, s, ad in konumlar:
        d = bas - s if s <= bas else (b - son if b >= son else 0)
        if d < fark:
            en, fark = ad, d
    return en if fark <= 160 else None


def _y_tavan(t: str, q) -> bool:
    onceki, sonraki = t[max(0, q["bas"] - 80):q["bas"]], t[q["son"]:q["son"] + 60]
    for tm in Y_TAVAN_ON.finditer(onceki):
        ara = onceki[tm.end():]
        if len(ara) <= 40 and not re.search(r"\d|[,;]|\b(?:give|ver\w*|uygula\w*)\b", ara):
            return True
    return bool(KG_TAVAN_SONRA.match(sonraki))


def _y_sayi_say(t: str, q) -> bool:
    """Aralık ('10–15 mg') ya da tarih/başka sayıya bitişik mi."""
    return bool(q["ay2"]) or bool(re.search(r"\d\s*[-–—]\s*$", t[max(0, q["bas"] - 6):q["bas"]]))


def _y_rol(t: str, q) -> str | None:
    """Adayın rolü: payda ya da çevre sözcükle 'saat' / 'dk' / 'gun' / 'doz' / None."""
    if q["zaman"]:
        return q["zaman"]
    onceki, sonraki = t[max(0, q["bas"] - 60):q["bas"]], t[q["son"]:q["son"] + 40]
    if Y_SAAT_ON.search(onceki) or Y_SAAT_SON.match(sonraki):
        return "saat"
    if Y_DK_ON.search(onceki) or Y_DK_SON.match(sonraki):
        return "dk"
    if Y_ROL_SON.match(sonraki):
        return "doz"
    if Y_GUN_SON.match(sonraki) or Y_GUNLUK_ON.search(onceki):
        return "gun"
    if Y_ROL_ON.search(onceki):
        return "doz"
    return None


def y_siklik(t: str) -> float | None:
    for desen, f in Y_SIKLIK:
        m = desen.search(t)
        if m:
            try:
                n = f(m)
            except (ValueError, KeyError, ZeroDivisionError):
                continue
            if n and 1 <= n <= 24:
                return n
    return None


def _y_beklenen(w: float, r, rq, rol: str | None, n_siklik, gunluk_sozu: bool):
    """Oran r (sayı), oran miktarı rq, adayın rolü → kabul edilen sonuç değerleri [(değer, tolerans_kat)] (oranın birimi cinsinden)."""
    zr = rq["zaman"]
    temel = w * r
    if zr in ("saat", "dk"):
        return [temel] if rol == zr else None
    if zr == "gun" or (zr is None and gunluk_sozu):
        if rol == "gun":
            return [temel]
        if rol == "doz":
            return [temel / n for n in ([n_siklik] if n_siklik else Y_N_IZINLI)]
        if rol is None:
            return [temel / n for n in ([n_siklik] if n_siklik else Y_N_IZINLI)] + ([temel] if n_siklik else [])
        return None
    if zr == "doz":
        if rol in ("doz", None):
            return [temel]
        if rol == "gun" and n_siklik:
            return [temel * n_siklik]
        return None
    # zaman paydası yok, günlük sözü yok: doz başına varsayılır
    if rol in ("doz", None):
        return [temel] + ([temel / n_siklik] if n_siklik and n_siklik > 1 else [])
    if rol == "gun" and n_siklik:
        return [temel * n_siklik]
    return None


def _y_tekil(liste, anahtar):
    gor, cikti = set(), []
    for x in liste:
        k = anahtar(x)
        if k not in gor:
            gor.add(k)
            cikti.append(x)
    return cikti


Y_SORU = re.compile(r"\?\s*$|\bkaç\b|\bhow\s+(?:many|much)\b|hesaplay\w*|\bcalculate\b|\bbulunuz\b|\bfind\s+the\b", re.I)


def _y_soru_cumlesi(t: str, a, siniri: list) -> bool:
    """Aday, soru/alıştırma cümlesinde mi ('doz kaç mg'dır?', 'Calculate …'): soru sonuç vermez."""
    i = bisect.bisect_right(siniri, a["bas"])
    bas = siniri[i - 1] if i else 0
    son = siniri[i] if i < len(siniri) else len(t)
    return bool(Y_SORU.search(t[bas:son]))


def kg_yapisal(t: str, nok: bool, en: bool):
    """Bir birimin doz hesabı. [(ifade, doğrusu, düzey, konum)] ya da None (yapı yok / belirsiz). Düzey: ENGEL | UYARI.
    Her aday sonuç için kendi oranı ve kilosu seçilir: aday ile ≤ 2 cümle uzaklıktaki, tercihen adaydan ÖNCEKİ (yoksa sonraki)
    kilo ve oran. O kümede iki farklı kilo ya da oran varsa, aralıklı oran varsa ya da 'mg/kg/d' gibi payda belirsizse sessiz kalınır."""
    if not re.search(r"(?i)kg", t):
        return None
    t = t[:Y_METIN_TAVAN]                              # çok uzun tek satırda doğrusal süre (aşım k_doz_aritmetigi'nde not düşülür)
    kilolar, oranlar, adaylar, belirsiz, kesildi = y_miktarlar(t, nok, en)
    if belirsiz or not kilolar or not oranlar:
        return None
    for k in kilolar:                                 # aralıklı kilo ('10-12 kg')
        if re.search(r"\d\s*[-–—]\s*$", t[max(0, k["bas"] - 4):k["bas"]]) or re.match(r"\s*[-–—]\s*\d", t[k["son"]:k["son"] + 4]):
            return None
    ilaclar = _y_ilac_konumlari(t)
    ilac_sayisi = len({a for _, _, a in ilaclar})
    siniri = [m.end() for m in Y_CUMLE_SINIR.finditer(t)]
    for x in kilolar + oranlar + adaylar:
        x["c"] = bisect.bisect_right(siniri, x["bas"])    # cümle numarası (bir kez)
    cumle_no = lambda poz: bisect.bisect_right(siniri, poz)      # noqa: E731
    siklik = y_siklik(t)
    gunluk_sozu = bool(KG_GUNLUK.search(t)) and not siklik   # sıklık (q12h, günde iki kez) verilmişse paydasız oran doz başınadır
    uygun = []                                        # aday elemesi: oran/kilo sayıları, tavan, tablet gücü, seyreltme, aralık
    for a in adaylar:
        if _y_sayi_say(t, a):
            continue
        if any(a["bas"] < k["son"] and a["son"] > k["bas"] for k in kilolar) or \
                any(a["bas"] < r["son"] and a["son"] > r["bas"] for r in oranlar):
            continue
        if _y_tavan(t, a) or _y_soru_cumlesi(t, a, siniri):
            continue
        sonraki, onceki = t[a["son"]:a["son"] + 30], t[max(0, a["bas"] - 30):a["bas"]]
        if Y_GUC.match(sonraki) or Y_GUC_ON.search(onceki) or Y_SEYRELTME.match(sonraki):
            continue
        uygun.append(a)
    elenen = []
    for i, a in enumerate(uygun):                     # '1,2 mg (1200 mcg)': parantezli eşdeğer ayrı aday değildir
        if i and uygun[i - 1]["aile"] == a["aile"] and uygun[i - 1]["birim"] != a["birim"] and re.search(r"\(\s*[≈=]?\s*$", t[max(0, a["bas"] - 6):a["bas"]]) \
                and t[uygun[i - 1]["son"]:a["bas"]].strip() in ("(", "(≈", "(=") and \
                any(_yakin(x * uygun[i - 1]["kat"], y * a["kat"]) for x in uygun[i - 1]["ay"] for y in a["ay"]):
            elenen.append(a)
    uygun = [a for a in uygun if a not in elenen]

    def yakin_kume(liste, a, ayni_aile=None):
        """a'ya ≤ 2 cümle uzaklıktaki öğeler; önce a'dan önce gelenler, yoksa sonrakiler."""
        ca = a["c"]
        yakin = [x for x in liste if abs(x["c"] - ca) <= 2 and (ayni_aile is None or x["aile"] == ayni_aile)]
        once = [x for x in yakin if x["bas"] < a["bas"]]
        return once or yakin

    sonuclar = []
    for a in uygun:
        rs = [r for r in oranlar if r["perkg"] and r["aile"] == a["aile"] and r["c"] == a["c"]] or \
            yakin_kume([r for r in oranlar if r["perkg"]], a, a["aile"])      # önce adayla aynı cümledeki oran
        if not rs:
            continue
        ilac_net = ilac_sayisi <= 1                   # ilaç eşleşmesi belirsiz mi (iki ilaç adı, ilaç bulunamadı)
        if ilac_sayisi > 1:                           # iki ilaç adı: sonuç, ilacı oranın ilacıyla aynı olana bağlanır
            ia = _y_en_yakin_ilac(ilaclar, a["bas"], a["son"])
            rs = [r for r in rs if ia is None or _y_en_yakin_ilac(ilaclar, r["bas"], r["son"]) in (ia, None)]
            if not rs:
                continue
            ilac_net = ia is not None and all(_y_en_yakin_ilac(ilaclar, r["bas"], r["son"]) == ia for r in rs)
        rt = _y_tekil(rs, lambda x: (tuple(x["ay"]), tuple(x["ay2"] or ()), x["birim"], x["zaman"]))
        if len(rt) > 1 or rt[0]["ay2"]:
            continue                                  # iki farklı oran ya da aralıklı oran: sessiz
        r = rt[0]
        ks = [k_ for k_ in kilolar if k_["c"] == r["c"]] or [k_ for k_ in kilolar if k_["c"] == a["c"]] or \
            yakin_kume(kilolar, r) or yakin_kume(kilolar, a)               # kilo: önce oranın, sonra adayın kendi cümlesi; yoksa önceki cümle
        kt = _y_tekil(ks, lambda x: tuple(x["ay"]))
        if not kt or len(kt) > 1:
            continue                                  # kilo yok ya da iki farklı kilo: sessiz
        k = kt[0]
        rol = _y_rol(t, a)
        ipucu = bool(Y_IPUCU_ON.search(t[max(0, a["bas"] - 70):a["bas"]]) or Y_IPUCU_SON.match(t[a["son"]:a["son"] + 40]))
        beklenenler = []
        for w in k["ay"]:
            for rv in r["ay"]:
                bek = _y_beklenen(w, rv, r, rol, siklik, gunluk_sozu)
                if bek is not None:
                    beklenenler.append((bek, w))
        if not beklenenler:
            continue
        tutan = any(_yakin(b * r["kat"], d * a["kat"]) for bek, _w in beklenenler for b in bek for d in a["ay"])
        sonuclar.append({"a": a, "r": r, "rol": rol, "ipucu": ipucu, "tutan": tutan, "bek": beklenenler, "ilac_net": ilac_net})
    if not sonuclar:
        return None
    cikti = []
    for x in sonuclar:
        if x["tutan"]:
            continue
        a, r, rol = x["a"], x["r"], x["rol"]
        acik = rol is not None
        ayni_oran = [y for y in sonuclar if y["r"] is r]              # aynı orana bağlı adaylar (başka cümledeki oran/kilo karışmaz)
        tutanlar = [y for y in ayni_oran if y["tutan"]]
        etiketsiz = [y for y in ayni_oran if y["rol"] is None]
        if tutanlar and (not acik or any(y["rol"] == rol for y in tutanlar)):
            continue                                  # aynı etiketli aday beklenene eşit: hesap doğru, kalan sayılar başka şeydir
        doz_sozu = bool(Y_DOZ_SOZU.search(t[max(0, r["bas"] - 40):r["son"] + 30]) or Y_DOZ_SOZU.search(t[max(0, a["bas"] - 40):a["bas"] + 8]))
        acik = acik or doz_sozu
        kesin = (acik or len(etiketsiz) == 1) and x["ilac_net"]      # birden çok etiketsiz aday: UYARI
        bek, w = x["bek"][0]
        if kesin and not acik and r["zaman"] is None:
            # oranda da sonuçta da zaman bilgisi yok: %20'ye kadar sapma yuvarlama/uygulama dozu olabilir (UYARI), ötesi ENGEL
            sapma = min(abs(d * a["kat"] - b_ * r["kat"]) / max(abs(b_ * r["kat"]), 1e-9)      # beklenene göre sapma
                        for b1, _w in x["bek"] for b_ in b1 for d in a["ay"])
            if sapma <= 0.20:
                kesin = False
        deger = bek[0] * r["kat"] / a["kat"]
        gunluk_not = ""
        if len(bek) > 1 and (r["zaman"] == "gun" or gunluk_sozu) and rol is None:
            gunluk_not = " (günlük toplam; bölünmüşse ÷2/3/4/6)"
        dogru = f"{deger:g} {a['birim']}" + (f"/{rol}" if rol in ("saat", "dk") else "") + gunluk_not
        ifade = f"{w:g} kg × {r['ham']} → {a['ham']}"
        cikti.append((ifade, dogru, "ENGEL" if kesin else "UYARI", a["bas"]))
    return cikti


# Kiloya göre doz ('18 ünite/kg/saat', '5 mcg/kg/dk') ya da kütle birimi dönüşümü ('500 mg = 5 g') tek başına risk taramasını açar
RISK_ORAN = re.compile(r"\d\s*(?:mg|mcg|µg|μg|ng|mEq|mmol|ünite|units?|IU|İÜ|U)(?![A-Za-z])\s*/\s*kg\b"
                       r"|\d\s*(?:mg|mcg|µg|μg|g)(?:\s*/\s*[A-Za-z]{1,6})?\s*=\s*\d[\d.,]*\s*(?:mg|mcg|µg|μg|g)(?![A-Za-z])")
LISTE_MADDE = re.compile(r"^\s*(?:[-*+•]|\d+[.)])\s+")


BIRIM_KARAKTER_TAVAN = 1500       # bir paragraf birimi bu kadar karakteri geçerse yeni birime bölünür (çok satırlı dev paragrafta doğrusal süre)


def doz_birimleri(c) -> list[dict]:
    """Birim = paragraf (boş satırla ayrılan; satır sonları birleştirilir), liste maddesi, tablo satırı ya da başlık.
    {'nolar': [satır numaraları], 'bas': [her satırın birleşik metindeki başlangıcı], 'tam': birleşik metin (İngilizce
    satırlarda binlik virgül silinmiş), 'tablo': bool, 'liste': bool}. Kod bloğu satırı birim değildir.
    Paragraf BIRIM_KARAKTER_TAVAN karakteri aşarsa satır sınırında bölünür (not: pencere dışına taşan hesap eşleşmez)."""
    if c.get("_dz") is not None:
        return c["_dz"]
    cikti, cur = [], None

    def kapat():
        nonlocal cur
        if cur:
            cur["tam"] = " ".join(cur.pop("parca"))
            cikti.append(cur)
        cur = None

    def yeni_birim(tablo=False, liste=False, baslik=False):
        return {"nolar": [], "bas": [], "parca": [], "uzun": 0, "tablo": tablo, "liste": liste, "baslik": baslik}

    def ekle_satir(b, no, t):
        b["bas"].append(b["uzun"] + (1 if b["parca"] else 0))
        b["uzun"] += len(t) + (1 if b["parca"] else 0)
        b["nolar"].append(no)
        b["parca"].append(t)
    for x in _borusuz_tablo(c["satirlar"]):
        t, ham = x["tam"], x["ham"]
        if not ham.strip() or not t:
            kapat()
            continue
        if x["kod"]:
            kapat()                                   # kod bloğundaki satır birim değildir (eski tarama yine görür)
            continue
        if satir_dili(c, x["no"]) == "en":
            t = en_binlik_sil(t)
        if ham.lstrip().startswith("|") or ham.lstrip().startswith("#"):
            kapat()
            b = yeni_birim(tablo=ham.lstrip().startswith("|"), baslik=ham.lstrip().startswith("#"))
            ekle_satir(b, x["no"], t)
            b["tam"] = b.pop("parca")[0]
            cikti.append(b)
            continue
        if cur is None or LISTE_MADDE.match(ham) or cur["uzun"] > BIRIM_KARAKTER_TAVAN:
            kapat()
            cur = yeni_birim(liste=bool(LISTE_MADDE.match(ham)))
        ekle_satir(cur, x["no"], t)
    kapat()
    for b in cikti:
        b.pop("uzun", None)
    c["_dz"] = cikti
    return cikti


def liste_bloklari(c) -> list[dict]:
    """Bitişik (araya boş satır girmemiş) en çok 8 liste maddesi tek blok sayılır: kilo, oran ve sonuç ayrı maddelerde olabilir."""
    cikti, cur = [], []

    def kapat():
        nonlocal cur
        if len(cur) >= 2:
            blok = {"nolar": [], "bas": [], "tam": "", "tablo": False, "liste": True, "baslik": False}
            for x in cur:
                taban = len(blok["tam"]) + (1 if blok["tam"] else 0)
                blok["bas"] += [taban + y for y in x["bas"]]
                blok["nolar"] += x["nolar"]
                blok["tam"] = (blok["tam"] + " " + x["tam"]) if blok["tam"] else x["tam"]
            cikti.append(blok)
        cur = []
    for b in doz_birimleri(c):
        if b["liste"] and cur and cur[-1]["nolar"][-1] + 1 == b["nolar"][0] and len(cur) < 8:
            cur.append(b)
        else:
            kapat()
            if b["liste"]:
                cur.append(b)
    kapat()
    return cikti


def onceki_birimle_birlesik(c) -> list[dict]:
    """Oran + sonuç var ama kilo yok: hemen önceki liste maddesi (araya başlık/boş satır girmemiş) tek kilo taşıyorsa ikisi birlikte
    bir birim sayılır (kilo bir önceki maddede)."""
    cikti, onceki = [], None
    for b in doz_birimleri(c):
        if onceki and b["liste"] and onceki["liste"] and onceki["nolar"][-1] + 1 == b["nolar"][0] \
                and not re.search(r"(?i)\d\s*kg(?![\w/])", b["tam"]) and re.search(r"(?i)kg", b["tam"]):
            kilolar = {x.group(1) for x in Y_KAN.finditer(onceki["tam"])}
            if len(kilolar) == 1 and not Y_MIKTAR_PERKG.search(onceki["tam"]):
                taban = len(onceki["tam"]) + 1
                cikti.append({"nolar": onceki["nolar"] + b["nolar"], "bas": onceki["bas"] + [taban + y for y in b["bas"]],
                              "tam": onceki["tam"] + " " + b["tam"], "tablo": False, "liste": True, "baslik": False,
                              "ilk_yeni": taban})
        onceki = b if b["liste"] else None
    return cikti


Y_MIKTAR_PERKG = re.compile(r"/\s*kg\b", re.I)


Y_TAVAN_BASLIK = re.compile(r"\(\s*(?:max|maks|maksimum|maximum|tavan|azami|up\s+to|en\s+fazla)\.?\s*[:=]?\s*(" + Y_SAYI + r")", re.I)
Y_HUCRE_SAYI = re.compile(r"^[~≈]?\s*(" + Y_SAYI + r")\s*([^\d]*)$")


def tablo_baslik_oran_hatalari(c) -> list[tuple]:
    """Sütun başlığında oran (ve tavan) olan tablo: 'Bolus 60 units/kg (max 4,000)' | hücre = sonuç. Beklenen = min(kilo × oran, tavan);
    hücrede '(capped)/(tavan)' notu olabilir. Kilo sütunu tek ve başlığında kg/weight/ağırlık olmalı."""
    hatalar = []
    for tb in c["tbl"]:
        blok, hucreler, ayirici = tb["blok"], tb["hucreler"], tb["ayirici"]
        if not ayirici or ayirici[0] != 1:
            continue
        baslik = hucreler[0]
        kilo = [k for k, b in enumerate(baslik) if KILO_BASLIK.search(b) and not Y_MIKTAR_PERKG.search(b)]
        sutunlar = []
        for k, b in enumerate(baslik):
            m = Y_MIKTAR.search(b)
            if not m or k in kilo:
                continue
            perkg, zaman, bel, yogun, _t = _y_pay(m.group("pay") or "")
            bil = _y_birim(m.group("b"))
            if not (perkg and bil) or bel or m.group("ar"):
                continue
            tav = Y_TAVAN_BASLIK.search(b)
            sutunlar.append((k, m, bil, tav))
        if len(kilo) != 1 or not sutunlar:
            continue
        en = satir_dili(c, blok[0]["no"]) == "en"
        for j, (s_, h) in enumerate(zip(blok, hucreler)):
            if j < 2 or j in ayirici or kilo[0] >= len(h):
                continue
            wm = Y_HUCRE_SAYI.match(h[kilo[0]].strip())
            if not wm or not re.search(r"(?i)kg", wm.group(2)) and wm.group(2).strip():
                continue
            for k, m, bil, tav in sutunlar:
                if k >= len(h):
                    continue
                hm = Y_HUCRE_SAYI_UC.match(h[k].strip())
                if not hm:
                    continue
                w, r_, v = sayi_dil(wm.group(1), en), sayi_dil(m.group("s1"), en), sayi_dil(hm.group(1), en)
                bek = w * r_
                if tav:
                    bek = min(bek, sayi_dil(tav.group(1), en))
                hucre_b = _y_birim_ilk(hm.group(2))
                kat = (hucre_b[1] if hucre_b and hucre_b[0] == bil[0] else bil[1]) / bil[1]
                if not _yakin(bek * bil[1], v * kat * bil[1]):
                    hatalar.append((f"{h[kilo[0]].strip()} × {m.group(0).strip()}{' (max ' + tav.group(1) + ')' if tav else ''} → {h[k].strip()}",
                                    f"{bek:g}", s_["no"]))
    return hatalar


Y_HUCRE_SAYI_UC = re.compile(r"^[~≈]?\s*(" + Y_SAYI + r")\s*([A-Za-zµμ/İÜ]*)")


def _y_birim_ilk(metin: str):
    m = re.match(r"\s*(mcg|µg|μg|mg|ng|g|ünite|units?|IU|U)\b", metin or "", re.I)
    return _y_birim(m.group(1)) if m else None


def k_doz_aritmetigi(c, ekle):
    son_derisim, son_no = None, None
    rapor_satir: set = set()
    nok = bool(ONDALIK_NOKTA.search(c["tam"]))
    for st in tarama_satirlari(c):
        t = st["tam"]
        en = satir_dili(c, st["no"]) == "en"          # İngilizce satırda '1,150' = 1150
        sayi_adaylari_ = functools.partial(sayi_adaylari, nokta_ondalik=nok, en=en)
        sy = functools.partial(sayi_dil, en=en)
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
                ornek = sy(kg) * sy(doz)
                if (b1 in HACIM_B) != (b2 in HACIM_B):
                    hatali.append((m.group(0), f"birim uyuşmuyor: {b1}/kg × kg = {b1}, sonuç {b2} yazılmış (derişim olmadan kütle hacme çevrilmez)"))
                elif b1 == b2 and not _herhangi(ad, lambda a, b, s_: _yakin(a * b, s_)):
                    hatali.append((m.group(0), f"{ornek:g} {b1}"))
                elif b1 != b2 and k1 and k2 and not _herhangi(ad, lambda a, b, s_: _yakin(a * b * k1, s_ * k2)):
                    hatali.append((m.group(0), f"{ornek:g} {b1} = {ornek * k1 / k2:g} {b2}"))
        derisimler = list(DERISIM.finditer(t))
        bolumler = [(sy(d.group(1)), sy(d.group(2)) if d.group(2) else 1.0,
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
                    z = sy(m.group(1))
                    hatali.append((m.group(0), f"{z:g} mg = {z * ml / mg:g} mL"))
        if derisimler:
            d = derisimler[-1]
            son_derisim = (sy(d.group(1)), sy(d.group(2)) if d.group(2) else 1.0)
        son_no = st["no"] if (derisimler or son_no is None or st["no"] != (son_no or 0) + 1) else son_no
        if derisimler:
            son_no = st["no"]
        for m in list(BIRIM_DONUSUM.finditer(t))[:Y_SINIR]:
            ba, bb = m.group(2), m.group(5)
            pa, pb = re.sub(r"\s+", "", m.group(3) or "").lower(), re.sub(r"\s+", "", m.group(6) or "").lower()
            if pa != pb:
                continue                              # paydalar farklıysa ('mg/saat = mg/dk') başka bir dönüşüm
            ad = [sayi_adaylari_(m.group(1)), sayi_adaylari_(m.group(4))]
            if ba != bb and not _herhangi(ad, lambda a, b: _yakin(a * BIRIM_KAT[ba], b * BIRIM_KAT[bb])):
                a = sy(m.group(1))
                hatali.append((m.group(0), f"{a:g} {ba}{pa} = {a * BIRIM_KAT[ba] / BIRIM_KAT[bb]:g} {bb}{pb}"))
            elif ba != bb and len(ad[0]) * len(ad[1]) > 1 and not all(
                    _yakin(a * BIRIM_KAT[ba], b * BIRIM_KAT[bb]) for a in ad[0] for b in ad[1]):
                ekle("Doğruluk", "UYARI", f"Noktalı sayı iki türlü okunabiliyor («{m.group(0)}»): binlik mi ondalık mı?",
                     "Türkçede ondalık virgülle yazılır (1,125 mg); binlikse 1125 mg yaz", ornek=m.group(0), satir=st["no"])
        for h, dogru in hatali:
            rapor_satir.add(st["no"])
            ekle("Doğruluk", "ENGEL", f"Doz hesabı tutmuyor («{h}» → {'' if dogru.startswith('birim') else 'doğrusu '}{dogru})",
                 "Hesabı yeniden yap; sonuç nottaki sayıyla aynı olmalı", ornek=h, satir=st["no"])
    tablo_hatalari = tablo_doz_hatalari(c)
    rapor_satir.update(no for _h, _d, no in tablo_hatalari)
    # Yapısal doz hesabı: birim (paragraf / liste maddesi / tablo satırı) başına kilo + kiloya göre doz + sonuç doz
    yapisal_satir = set()
    uzun_not = 0
    for b in doz_birimleri(c) + onceki_birimle_birlesik(c):
        if len(b["tam"]) > Y_METIN_TAVAN and re.search(r"(?i)kg", b["tam"]) and uzun_not < 3:
            uzun_not += 1
            ekle("Doğruluk", "UYARI", f"Satır çok uzun ({len(b['tam'])} karakter): doz hesabı denetimi yalnız ilk {Y_METIN_TAVAN} karakterde yapıldı",
                 "Satırı böl", ornek=b["tam"][:40], satir=b["nolar"][0])
        if rapor_satir.intersection(b["nolar"]) or not re.search(r"(?i)kg", b["tam"]) or \
                (len(b["nolar"]) > 1 and b["liste"] and yapisal_satir.intersection(b["nolar"])) or \
                ("ilk_yeni" in b and yapisal_satir.intersection(b["nolar"][len(b["nolar"]) - sum(1 for x in b["bas"] if x >= b["ilk_yeni"]):])):
            continue
        en_b = satir_dili(c, b["nolar"][0]) == "en"
        sonuc_l = kg_yapisal(b["tam"], nok, en_b)
        if sonuc_l is None:
            continue
        yapisal_satir.update(b["nolar"])
        for ifade, dogru, duzey, poz in sonuc_l[:5]:
            if "ilk_yeni" in b and poz < b["ilk_yeni"]:
                continue
            no_ = b["nolar"][max(bisect.bisect_right(b["bas"], poz) - 1, 0)]
            if duzey == "ENGEL":
                ekle("Doğruluk", "ENGEL", f"Doz hesabı tutmuyor («{ifade}» → doğrusu {dogru})",
                     "Hesabı yeniden yap; sonuç nottaki sayıyla aynı olmalı", ornek=ifade, satir=no_)
            else:
                ekle("Doğruluk", "UYARI", f"Doz hesabı tutmuyor olabilir («{ifade}» → doğrusu {dogru}); eşleşme ya da sıklık belirsiz",
                     "Kilo, oran ve sonuç dozunu aynı cümlede açık yaz; günlük mü doz başına mı belirt", ornek=ifade, satir=no_)
    tablo_idleri = {id(x) for x in c["tablo"]}
    for st in tarama_satirlari(c):
        if id(st) in tablo_idleri or st["no"] in yapisal_satir:
            continue
        en = satir_dili(c, st["no"]) == "en"
        cumle_listesi = [en_binlik_sil(x) if en else x for x in yan_cumleler(st["tam"])]
        for i, t in enumerate(cumle_listesi):
            if not KG_ORAN.search(t) and KG_AGIRLIK.search(t) and len(KG_ORAN.findall(st["tam"])) == 1:
                for geri in (1, 2):                   # oran en çok 2 cümle önce (aynı satır/madde), tek olmalı
                    onceki = " ".join(cumle_listesi[max(0, i - geri):i])
                    n_oran = len(KG_ORAN.findall(onceki))
                    if n_oran == 1 and i - geri >= 0:
                        t = onceki + " " + t
                        break
                    if n_oran > 1:
                        break
            sonuc = kg_duzyazi(t, nok, en)
            if sonuc and sonuc[2] == "ENGEL":
                ekle("Doğruluk", "ENGEL", f"Doz hesabı tutmuyor («{sonuc[0]}» → doğrusu {sonuc[1]})",
                     "Hesabı yeniden yap; sonuç nottaki sayıyla aynı olmalı", ornek=sonuc[0], satir=st["no"])
            elif sonuc:
                ekle("Doğruluk", "UYARI", f"Doz hesabı tutmuyor olabilir («{sonuc[0]}» → W×R = {sonuc[1]}); sıklık belirsiz",
                     "'mg/kg/doz' mu 'mg/kg/gün' mü yaz; günlük doz bölünüyorsa sıklığı belirt", ornek=sonuc[0], satir=st["no"])
    for h, dogru, no in tablo_baslik_oran_hatalari(c):
        if no in rapor_satir:
            continue
        rapor_satir.add(no)
        ekle("Doğruluk", "ENGEL", f"Doz hesabı tutmuyor («{h}» → doğrusu {dogru}; tavan varsa tavanla sınırlı)",
             "Hesabı yeniden yap; hücre = min(kilo × oran, tavan) olmalı", ornek=h, satir=no)
    for h, dogru, no in tablo_hatalari:
        ekle("Doğruluk", "ENGEL", f"Doz hesabı tutmuyor («{h}» → doğrusu {dogru})",
             "Hesabı yeniden yap; sonuç nottaki sayıyla aynı olmalı", ornek=h, satir=no)


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
          "kolesterol": ("mg/dl", "mmol/l", "c"), "kreatinin": ("mg/dl", "(?:µ|μ|u)mol/l", "k"),
          "üre": ("mg/dl", "mmol/l", None), "kalsiyum": ("mg/dl", "mmol/l", None), "trigliserit": ("mg/dl", "mmol/l", "t"),
          "bilirubin": ("mg/dl", "(?:µ|μ|u)mol/l", None), "hemoglobin": ("g/dl", "g/l|mmol/l", None),
          "glucose": ("mg/dl", "mmol/l", "g"), "blood sugar": ("mg/dl", "mmol/l", "g"),
          "creatinine": ("mg/dl", "(?:µ|μ|u)mol/l", "k"), "cholesterol": ("mg/dl", "mmol/l", "c"), "ldl": ("mg/dl", "mmol/l", "c"), "hdl": ("mg/dl", "mmol/l", "c"),
          "urea": ("mg/dl", "mmol/l", None), "calcium": ("mg/dl", "mmol/l", None),
          "triglyceride": ("mg/dl", "mmol/l", "t")}
# Dönüşüm katsayısı f: mg/dL ÷ f = SI birimi. glukoz 18; kreatinin 1/88,4 (µmol/L = mg/dL × 88,4);
# kolesterol (total/LDL/HDL) 38,67 (PubChem CID 5997, C27H46O 386,7 g/mol; mmol/L = mg/dL × 10 / MA);
# trigliserit 88,5 (PubChem CID 5497163, triolein C57H104O6 885,4 g/mol).
KATSAYI = {"g": 18.0, "k": 1 / 88.4, "c": 38.67, "t": 88.5}
LAB_IZI = re.compile(r"\d\s*(?:mg/dl|mmol/l|[µμu]mol/l)\b", re.I)
DONUSUM_IZI = re.compile(r"dönüşüm|katsayı|÷\s*18|/\s*18\b|×\s*0[.,]0555|×\s*88[.,]4|88[.,]4|conversion factor"
                         r"|38[.,]67|88[.,]5\b|×\s*0[.,]0259|×\s*0[.,]0113", re.I)


# Düzyazı dönüşümü: '=' olmadan, bağlayıcı ipucuyla ('karşılığı', 'corresponds to', 'i.e.' ...). Çift, aynı satırdaki ardışık iki
# laboratuvar değeridir (mg/dL sonra SI ya da tersi); araya başka analit adı, başka lab değeri ya da cümle sonu girmemelidir.
LAB_DEGER = re.compile(SAYI + r"\s*(g/dl|mg/dl|mmol/l|[µμu]mol/l|g/l)(?![\w/])")
LAB_IPUCU = re.compile(r"karş[ıi]l[ıi][gğ][ıi]|karş[ıi]l[ıi]k\s+gel|de[gğ]er[ıi]|e[sş]de[gğ]er|e[sş][ıi]tt[ıi]r|\by[aı]n[ıi]\b"
                       r"|olarak\s+raporlan|→|->|≈|=|corresponds?\s+to|equivalent|equals?\b|i\.e\.|which\s+is"
                       r"|converts?\s+to|in\s+si\s+units"
                       r"|(?:written|reported|expressed|recorded)\s+as\b|olarak\s+(?:yaz[ıi]l[ıi]r|ifade\s+edilir|kaydedilir)")
CUMLE_SONU = re.compile(r"[.;!?](?:\s|$)")


def lab_duzyazi_ciftleri(k: str, analit: str, geleneksel: str, si: str, tip: str):
    """k: küçük harfli satır. [((bas, son), a, b, yon)] döner: a ilk, b ikinci değer; yon 1: mg/dL → SI, -1: SI → mg/dL."""
    anlar = [m for m in re.finditer(r"(?<![\w])" + re.escape(analit) + r"\w*", k)]
    if not anlar:
        return []
    digerleri = [m for a2, (_, _, t2) in ANALIT.items() if t2 != tip or t2 is None
                 for m in re.finditer(r"(?<![\w])" + re.escape(a2) + r"\w*", k)]
    degerler = list(LAB_DEGER.finditer(k))
    cikti = []
    for v1, v2 in zip(degerler, degerler[1:]):
        b1, b2 = v1.group(2), v2.group(2)
        if re.fullmatch(re.escape(geleneksel), b1) and re.fullmatch(si, b2):
            yon = 1
        elif re.fullmatch(si, b1) and re.fullmatch(re.escape(geleneksel), b2):
            yon = -1
        else:
            continue
        onceki = [m for m in anlar if m.end() <= v1.start()]
        if not onceki:
            continue
        ad = onceki[-1]
        g1, g2 = k[ad.end():v1.start()], k[v1.end():v2.start()]
        izin = re.sub(r"i\.e\.", "i_e_", g1 + "§" + g2)
        if len(g1) > 60 or len(g2) > 80 or CUMLE_SONU.search(izin) or lab_formul_mu(g2) or lab_formul_mu(g1):
            continue
        if any(ad.end() <= m.start() and m.end() <= v1.start() for m in digerleri) or \
                any(v1.end() <= m.start() and m.end() <= v2.start() for m in digerleri):
            continue
        son = k[v2.end():v2.end() + 30]
        son = son[:CUMLE_SONU.search(son).start()] if CUMLE_SONU.search(son) else son
        if LAB_IPUCU.search(g2) or re.match(r"\s*(?:olarak\s+(?:raporlan|yaz[ıi]l[ıi]r|ifade\s+edilir|kaydedilir)|e[sş][ıi]tt[ıi]r)", son):
            cikti.append(((v1.start(), v2.end()), v1.group(1), v2.group(1), yon))
    return cikti


# ── Lab dönüşümü, yapısal (v2.1.1): aynı analitin iki birimli değeri ──
LAB_ANALIT_AD = {"glukoz": "glukoz", "glikoz": "glukoz", "kan şekeri": "glukoz", "glucose": "glukoz", "blood sugar": "glukoz",
                 "kolesterol": "kolesterol", "cholesterol": "kolesterol", "ldl": "ldl", "hdl": "hdl", "kreatinin": "kreatinin",
                 "creatinine": "kreatinin", "trigliserit": "trigliserit", "triglyceride": "trigliserit"}
LAB_ANALIT_IS = {"glukoz": "g", "kolesterol": "c", "ldl": "c", "hdl": "c", "kreatinin": "k", "trigliserit": "t"}
LAB_ANALIT_UNIT = {"glukoz": ("mg/dl", "mmol/l"), "kolesterol": ("mg/dl", "mmol/l"), "ldl": ("mg/dl", "mmol/l"),
                   "hdl": ("mg/dl", "mmol/l"), "kreatinin": ("mg/dl", "(?:µ|μ|u)mol/l"), "trigliserit": ("mg/dl", "mmol/l")}
LAB_DIGER = r"sodyum|sodium|potasyum|potassium|bikarbonat|bicarbonate|hco3|klor(?:ür|ur)?|chloride|osmolalite|osmolality|osmolarite|osmolarity|anyon|anion\s+gap|laktat|lactate|magnezyum|magnesium|fosfat|phosphate|bun\b|ürik|uric|\bna\b|\bk\+|\bcl\b"
LAB_ANALIT_RE = re.compile(r"(?<![\w])(?:(?P<ldl>ldl|hdl)(?:[\s-]*(?:cholesterol|kolesterol))?|(?P<ad>" + "|".join(
    sorted((re.escape(a) for a in LAB_ANALIT_AD if a not in ("ldl", "hdl")), key=len, reverse=True)) + r")\w*|(?P<diger>" + LAB_DIGER + r"))")
LAB_AYRAC = re.compile(r"sonra|after|\bsaat|\bhours?\b|\b\d+\s*h\b|\bgün|\bdays?\b|haftas?\b|\bweeks?\b|tedavi|treat|düş|yüksel|çık(?:tı|mış)|arttı|azaldı|"
                      r"\bfell\b|\brose\b|dropped|increas|decreas|reduc|hedef|target|goal|baseline|başlangıç|\bönce|before|\bvs\b|versus|"
                      r"compared|karşılaştır|\bthen\b|ardından|followed|later|yatış|taburcu|admission|discharge|nadir|\bpeak|tepe")
LAB_DEN = re.compile(r"^['’]?[dt][ae]n\b")                     # '250 mg/dL'den 9 mmol/L'ye': değişim anlatımı
LAB_ONCE = re.compile(r"\bfrom\b|\bfell\b|\brose\b|dropped|increased|decreased|düştü|yükseldi|başlangıç|baseline|\bfrom\b")
LAB_BILINEN_CARPAN = re.compile(r"0[.,]0555|0[.,]0259|0[.,]0113|88[.,]4|38[.,]67|88[.,]5|\b18\b")
LAB_FORMUL_KELIME = re.compile(r"corrected|düzeltilmiş|duzeltilmis|anyon|anion\s+gap|osmolal|osmolar", re.I)


def lab_formul_mu(ara: str) -> bool:
    """İki değer arasındaki metin bir hesap mı (toplama/çıkarma ya da bilinmeyen çarpan): dönüşüm değil formüldür."""
    if re.search(r"\d\s*[+−]\s*\d|[+−]\s*\d+[.,]?\d*\s*[×x*]", ara) or re.search(r"\d\s*-\s*\(", ara):
        return True
    for m in re.finditer(r"[×*·]\s*(\d[\d.,]*)", ara):
        if not LAB_BILINEN_CARPAN.search(m.group(0)):
            return True
    return False


def lab_deger_analit(k: str, bas: int, onceki_analit: str | None):
    """Değerin hemen solundaki en yakın analit adı: (kanon ad | 'diger' | None). Aynı cümle ya da ≤ 200 karakter geri."""
    en_yakin = None
    for m in LAB_ANALIT_RE.finditer(k, max(0, bas - 200), bas):
        en_yakin = m
    if en_yakin is None:
        return onceki_analit
    if en_yakin.group("diger"):
        return "diger"
    if en_yakin.group("ldl"):
        return "ldl" if en_yakin.group("ldl")[0] == "l" else "hdl"
    return LAB_ANALIT_AD.get(en_yakin.group("ad"))


def _lab_bicim(birim: str):
    """('g'|'si', anahtar) lab birimine göre: trad (mg/dl, g/dl) ya da SI (mmol/l, µmol/l, g/l)."""
    b = birim.lower().replace("μ", "µ").replace("u", "µ", 1) if birim.lower().startswith("umol") else birim.lower().replace("μ", "µ")
    return "trad" if b in ("mg/dl", "g/dl") else "si"


def lab_cift_denetle(analit: str, v1, v2, en: bool):
    """İki değer (g1: trad ya da SI) → (beklenen, yazılan, yön) ya da None (birim uyuşmuyor)."""
    geleneksel, si = LAB_ANALIT_UNIT[analit]
    b1, b2 = v1.group(2), v2.group(2)
    if re.fullmatch(re.escape(geleneksel), b1) and re.fullmatch(si, b2):
        yon = 1
    elif re.fullmatch(si, b1) and re.fullmatch(re.escape(geleneksel), b2):
        yon = -1
    else:
        return None
    a, b = sayi_dil(v1.group(1), en), sayi_dil(v2.group(1), en)
    kat = KATSAYI[LAB_ANALIT_IS[analit]]
    beklenen = a / kat if yon == 1 else a * kat
    return beklenen, b, a, yon


LAB_DEGER2 = re.compile(SAYI + r"(?:\s*[-–—]\s*(\d+(?:[.,]\d+)*))?\s*(g/dl|mg/dl|mmol/l|[µμu]mol/l|g/l)(?![\w/])")
LAB_PAREN_ON = re.compile(r"\s*\(\s*(?:[≈=]\s*)?$")


def lab_eslestir(k: str, onceki_analit: str | None):
    """Bir birimdeki (ya da tablo hücresindeki) lab değerlerini bire bir eşler. Önce parantezli çift ('126 mg/dL (7,0 mmol/L)'; aralık
    'a–b mg/dL (c–d mmol/L)' uç uca), sonra kalanlar sırayla en yakın komşuyla; her değer bir kez kullanılır.
    Döner: ([(v1, v2, parantezli)], eşleşmeyen_dönüştürülebilir_değer_sayısı)."""
    deg = []
    for m in itertools.islice(LAB_DEGER2.finditer(k), 60):
        deg.append({"m": m, "bas": m.start(), "son": m.end(), "lo": m.group(1), "hi": m.group(2), "birim": m.group(3),
                    "klas": _lab_bicim(m.group(3)), "analit": lab_deger_analit(k, m.start(), onceki_analit)})
    kullan, cift = set(), []
    for i in range(len(deg) - 1):
        a, c_ = deg[i], deg[i + 1]
        if i in kullan or i + 1 in kullan or a["klas"] == c_["klas"] or a["analit"] != c_["analit"]:
            continue
        if LAB_PAREN_ON.fullmatch(k[a["son"]:c_["bas"]]) and re.match(r"\s*\)", k[c_["son"]:c_["son"] + 4]):
            cift.append((a, c_, True))
            kullan.update((i, i + 1))
    kalan = [i for i in range(len(deg)) if i not in kullan]
    j = 0
    while j < len(kalan) - 1:
        a, c_ = deg[kalan[j]], deg[kalan[j + 1]]
        ara = k[a["son"]:c_["bas"]]
        izin = re.sub(r"i\.e\.", "i_e_", ara)
        uygun = (a["klas"] != c_["klas"] and a["analit"] in LAB_ANALIT_IS and a["analit"] == c_["analit"] and len(ara) <= 100
                 and not CUMLE_SONU.search(izin) and not LAB_AYRAC.search(ara) and not lab_formul_mu(ara) and not re.search(r"\d", ara)
                 and not LAB_DEN.match(ara) and not LAB_ONCE.search(k[max(0, a["bas"] - 30):a["bas"]]) and "(" not in ara and ")" not in ara)
        if uygun:
            cift.append((a, c_, False))
            kullan.update((kalan[j], kalan[j + 1]))
            j += 2
        else:
            j += 1
    artan = sum(1 for i, d in enumerate(deg) if i not in kullan and d["analit"] in LAB_ANALIT_IS)
    return cift, artan


def lab_eslestir_raporla(c, ekle, bildirilen_cift, k, metin, bas_listesi, nolar, onceki_analit, en, tek_no=None):
    cift, artan = lab_eslestir(k, onceki_analit)
    for a, c_, paren in cift:
        analit = a["analit"]
        if analit not in LAB_ANALIT_IS:
            continue
        geleneksel, si = LAB_ANALIT_UNIT[analit]
        if a["klas"] == "trad":
            trad, sid, yon = a, c_, 1
        else:
            trad, sid, yon = c_, a, -1
        if not (re.fullmatch(re.escape(geleneksel), trad["birim"]) and re.fullmatch(si, sid["birim"])):
            continue
        if bool(trad["hi"]) != bool(sid["hi"]):
            continue                                   # biri aralık, biri tek değer: eşleme belirsiz
        kat = KATSAYI[LAB_ANALIT_IS[analit]]
        uclar = [(trad["lo"], sid["lo"])] + ([(trad["hi"], sid["hi"])] if trad["hi"] else [])
        for x_t, x_s in uclar:
            t_, s_ = sayi_dil(x_t, en), sayi_dil(x_s, en)
            beklenen = t_ / kat
            no_ = tek_no if tek_no is not None else nolar[max(bisect.bisect_right(bas_listesi, a["bas"]) - 1, 0)]
            anahtar = (no_, round(t_, 6), round(s_, 6))
            if _yakin(beklenen, s_) or abs(beklenen - s_) <= 0.15 or anahtar in bildirilen_cift:
                continue
            ara = k[a["son"]:c_["bas"]]
            bitisik = len(ara) <= 40
            ipucu = bool(LAB_IPUCU.search(ara) or LAB_IPUCU.search(k[c_["son"]:c_["son"] + 40]))
            kesin = paren or (artan == 0 and (ipucu or bitisik))
            bildirilen_cift.add(anahtar)
            ifade = metin[a["bas"]:c_["son"]] if len(k) == len(metin) else k[a["bas"]:c_["son"]]
            ekle("Doğruluk", "ENGEL" if kesin else "UYARI",
                 f"Birim dönüşümü tutmuyor («{ifade}» → yaklaşık {round(beklenen, 2)})"
                 + ("" if kesin else "; eşleme belirsiz (birimde eşleşmeyen lab değeri var)"),
                 "Glukoz: mg/dL ÷ 18 = mmol/L; kreatinin: mg/dL × 88,4 = µmol/L; "
                 "kolesterol (total/LDL/HDL): mg/dL ÷ 38,67 = mmol/L; trigliserit: mg/dL ÷ 88,5 = mmol/L",
                 ornek=ifade, satir=no_)


def lab_yapisal(c, ekle, bildirilen_cift: set) -> None:
    """Düzyazıda (paragraf / liste maddesi / tablo satırı) ve tabloda aynı analitin iki birimli değerini eşleştirip dönüşümü denetler.
    İpucu sözcüğü gerekmez: aynı cümlede, bitişik, zaman/olay ayracı ve formül olmayan iki değer dönüşüm sayılır."""
    onceki_baslik_analit = None
    for b in doz_birimleri(c):
        metin = b["tam"]
        k = en_kucuk(metin)
        if len(k) > 4000:
            k = k[:4000]                               # çok uzun birimde doğrusal süre (ilk 4000 karakter)
        if b["baslik"] or not LAB_DEGER.search(k):
            m_ = None
            for m_ in LAB_ANALIT_RE.finditer(k):
                pass
            if m_ and b["baslik"]:
                onceki_baslik_analit = "diger" if m_.group("diger") else ("ldl" if m_.group("ldl") and m_.group("ldl")[0] == "l"
                                       else "hdl" if m_.group("ldl") else LAB_ANALIT_AD.get(m_.group("ad")))
            continue
        if b["tablo"] or LAB_FORMUL_KELIME.search(k):
            continue                                   # tablo satırını lab_tablo (hücre sınırı bilen) işler
        en = satir_dili(c, b["nolar"][0]) == "en"
        lab_eslestir_raporla(c, ekle, bildirilen_cift, k, metin, b["bas"], b["nolar"], onceki_baslik_analit, en)
    lab_tablo(c, ekle, bildirilen_cift)


LAB_BIRIM_HUCRE = re.compile(r"(?<![\w/])(mg/dl|g/dl|mmol/l|[µμu]mol/l|g/l)(?![\w/])", re.I)
LAB_SAYI_HUCRE = re.compile(r"^[~≈<>]?\s*(\d[\d.,]*)\s*$")


def lab_tablo(c, ekle, bildirilen_cift: set) -> None:
    """Tablo: satırda aynı analitin geleneksel ve SI birimli iki değeri (birim hücrede ya da sütun başlığında). Analit satır
    etiketinde, sütun başlığında ya da tablonun üstündeki başlık/cümlede olabilir."""
    satirlar = _borusuz_tablo(c["satirlar"])
    onceki = {}
    son_analit = None
    for x in satirlar:
        onceki[x["no"]] = son_analit
        m_ = None
        for m_ in LAB_ANALIT_RE.finditer(en_kucuk(x["tam"])):
            pass
        if m_ and not x["ham"].lstrip().startswith("|"):
            son_analit = "diger" if m_.group("diger") else ("ldl" if m_.group("ldl") and m_.group("ldl")[0] == "l"
                         else "hdl" if m_.group("ldl") else LAB_ANALIT_AD.get(m_.group("ad")))
        elif x["tam"].strip() and not x["ham"].lstrip().startswith("|"):
            son_analit = None if not m_ else son_analit
    for tb in c["tbl"]:
        blok, hucreler, ayirici = tb["blok"], tb["hucreler"], tb["ayirici"]
        if not ayirici or ayirici[0] != 1:
            continue
        baslik = hucreler[0]
        baslik_ad = [lab_deger_analit(en_kucuk(h), len(h), None) if LAB_ANALIT_RE.search(en_kucuk(h)) else None for h in baslik]
        baslik_birim = []
        for h in baslik:
            m = LAB_BIRIM_HUCRE.search(h)
            baslik_birim.append(m.group(1) if m else None)
        tablo_analit = onceki.get(blok[0]["no"])
        for j, (s, h) in enumerate(zip(blok, hucreler)):
            if j in ayirici or j == 0:
                continue
            satir_etiket = None
            if h and LAB_ANALIT_RE.search(en_kucuk(h[0])):
                satir_etiket = lab_deger_analit(en_kucuk(h[0]), len(h[0]), None)
            degerler = []                              # (analit, birim, sayı metni)
            for ci, hucre in enumerate(h):
                kh = en_kucuk(hucre)
                vm = list(LAB_DEGER.finditer(kh))
                analit = (lab_deger_analit(kh, vm[0].start(), None) if vm and LAB_ANALIT_RE.search(kh[:vm[0].start()]) else None) or \
                    (baslik_ad[ci] if ci < len(baslik_ad) else None) or satir_etiket or tablo_analit
                if len(vm) >= 2:
                    lab_eslestir_raporla(c, ekle, bildirilen_cift, kh, hucre, [0], [s["no"]], analit or tablo_analit, satir_dili(c, s["no"]) == "en",
                                         tek_no=s["no"])
                elif len(vm) == 1:
                    degerler.append((analit, vm[0].group(2), vm[0].group(1)))
                elif not vm and ci < len(baslik_birim) and baslik_birim[ci] and LAB_SAYI_HUCRE.match(hucre.strip()):
                    degerler.append((analit, baslik_birim[ci].lower(), LAB_SAYI_HUCRE.match(hucre.strip()).group(1)))
            tek = {d[0] for d in degerler if d[0]}
            if len(tek) == 1:                         # analit adı yalnız bir hücre/başlıkta ('Glucose' | 'mmol/L'): satırdaki öteki değerler de onundur
                degerler = [(next(iter(tek)), d[1], d[2]) for d in degerler]
            if len(degerler) < 2:
                continue
            en = satir_dili(c, s["no"]) == "en"
            for analit in {d[0] for d in degerler if d[0] in LAB_ANALIT_IS}:
                grup = [d for d in degerler if d[0] == analit]
                trad = [d for d in grup if _lab_bicim(d[1]) == "trad"]
                si = [d for d in grup if _lab_bicim(d[1]) == "si"]
                if len(trad) != 1 or len(si) != 1:
                    continue
                geleneksel, si_bi = LAB_ANALIT_UNIT[analit]
                if not (re.fullmatch(geleneksel, trad[0][1].lower()) and re.fullmatch(si_bi, si[0][1].lower().replace("μ", "µ"))):
                    continue
                a, b = sayi_dil(trad[0][2], en), sayi_dil(si[0][2], en)
                beklenen = a / KATSAYI[LAB_ANALIT_IS[analit]]
                anahtar = (s["no"], round(a, 6), round(b, 6))
                if _yakin(beklenen, b) or abs(beklenen - b) <= 0.15 or anahtar in bildirilen_cift:
                    continue
                bildirilen_cift.add(anahtar)
                ifade = f"{trad[0][2]} {trad[0][1]} | {si[0][2]} {si[0][1]}"
                ekle("Doğruluk", "ENGEL", f"Birim dönüşümü tutmuyor («{ifade}» → yaklaşık {round(beklenen, 2)})",
                     "Glukoz: mg/dL ÷ 18 = mmol/L; kreatinin: mg/dL × 88,4 = µmol/L; "
                     "kolesterol (total/LDL/HDL): mg/dL ÷ 38,67 = mmol/L; trigliserit: mg/dL ÷ 88,5 = mmol/L",
                     ornek=ifade, satir=s["no"])


def k_lab_birim_karisik(c, ekle):
    belge_donusum = bool(DONUSUM_IZI.search(c["tam"]))
    karisik, bildirilen, bildirilen_cift = [], set(), set()
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
                        beklenen = a / KATSAYI[tip] if yon == 1 else a * KATSAYI[tip]
                        bildirilen_cift.add((st["no"], round(a, 6), round(b, 6)))
                        if not _yakin(beklenen, b) and abs(beklenen - b) > 0.15 and (st["no"], m.group(0)) not in bildirilen:
                            bildirilen.add((st["no"], m.group(0)))
                            duzey = "UYARI" if m.group(2) in ("ya da", "veya") else "ENGEL"
                            ekle("Doğruluk", duzey, f"Birim dönüşümü tutmuyor («{m.group(0)}» → yaklaşık {round(beklenen, 2)})",
                                 "Glukoz: mg/dL ÷ 18 = mmol/L; kreatinin: mg/dL × 88,4 = µmol/L; "
                                 "kolesterol (total/LDL/HDL): mg/dL ÷ 38,67 = mmol/L; trigliserit: mg/dL ÷ 88,5 = mmol/L"
                                 + (" ('ya da' iki ayrı eşik de olabilir; dönüşümse düzelt)" if duzey == "UYARI" else ""),
                                 ornek=m.group(0), satir=st["no"])
        if tip:
            for st in sat:
                k = en_kucuk(st["tam"])
                for (i0, i1), x1, x2, yon in lab_duzyazi_ciftleri(k, analit, geleneksel, si, tip):
                    esitlik = True
                    ifade = st["tam"][i0:i1] if len(k) == len(st["tam"]) else k[i0:i1]
                    en = satir_dili(c, st["no"]) == "en"
                    a, b = sayi_dil(x1, en), sayi_dil(x2, en)
                    beklenen = a / KATSAYI[tip] if yon == 1 else a * KATSAYI[tip]
                    anahtar = (st["no"], round(a, 6), round(b, 6))
                    if not _yakin(beklenen, b) and abs(beklenen - b) > 0.15 and anahtar not in bildirilen_cift:
                        bildirilen_cift.add(anahtar)
                        ekle("Doğruluk", "ENGEL", f"Birim dönüşümü tutmuyor («{ifade}» → yaklaşık {round(beklenen, 2)})",
                             "Glukoz: mg/dL ÷ 18 = mmol/L; kreatinin: mg/dL × 88,4 = µmol/L; "
                             "kolesterol (total/LDL/HDL): mg/dL ÷ 38,67 = mmol/L; trigliserit: mg/dL ÷ 88,5 = mmol/L",
                             ornek=ifade, satir=st["no"])
        if g and s_ and not belge_donusum and not esitlik:
            karisik.append(analit)
    lab_yapisal(c, ekle, bildirilen_cift)
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
# Danışan / Client / Olgu / Case N etiketi 'Hasta:' gibidir; numaralı biçimleri ('Case 2:', 'Vaka 3:') de
HASTA_AD_ETIKET2 = re.compile(r"(?i:\b(?:danışan|client|olgu|case|vaka|hasta|patient)(?:\s*(?:no\.?|nr\.?|#)?\s*\d+)?)[ \t]*[:：][ \t]*("
                              + AD + r"(?:[ \t]+" + AD + r"){1,2})")
HASTA_BAS_HARF = re.compile(AD_ETIKET + r"[ \t]*[:：][ \t]*([A-ZÇĞİÖŞÜ]\.[ \t]*" + AD + r")")
PROTOKOL_KESIN = re.compile(r"(?i:\b(?:protokol|mrn|hbys)\s*(?:no|numarası|nr)?\.?)[ \t]*[:：]?[ \t]*([A-Z]{0,3}-?\d{4,}(?:/\d{3,})?)(?![/\d])")
PROTOKOL_VAKA = re.compile(r"(?i:\b(?:dosya|hasta|kayıt|arşiv|yatış)\s*(?:no|numarası|nr)\.?)[ \t]*[:：]?[ \t]*([A-Z]{0,3}-?\d{4,})(?![/\d])")
AYLAR = (r"(?:ocak|şubat|mart|nisan|mayıs|haziran|temmuz|ağustos|eylül|ekim|kasım|aralık|january|february|march|april"
         r"|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sept?|oct|nov|dec)\.?")
DOGUM = re.compile(r"(?i:\bdoğum\s+tarihi|\bd\.\s?t\.|\bdt\b|date of birth|\bdob\b)[ \t]*[:：]?[ \t]*"
                   r"(\d{1,2}[./-]\d{1,2}[./-](\d{2,4})|\d{1,2}[ \t]+" + "(?i:" + AYLAR + r")[ \t]+(\d{4})"
                   r"|(\d{4})-\d{1,2}-\d{1,2})")
DOGUM_PAREN = re.compile(r"\(\s*(?i:d\.|b\.|doğ\.|doğum|born|dob)\s*[:：]?\s*(\d{1,2}[./-]\d{1,2}[./-]\d{4}|\d{4}-\d{1,2}-\d{1,2})\s*\)")
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


YAS_TR = r"\d{1,3}\s*yaş(?:ında|ındaki|indeki|undaki|ündeki|lı|li)"
YAS_EN = r"\d{1,3}[- ]year[- ]old"
ADSOY = AD + r"(?:[ \t]+" + AD + r"){1,2}"
YAS_AD = [re.compile(r"(?<!\w)" + YAS_TR + r"[ \t]+(" + ADSOY + r")"),
          re.compile(YAS_EN + r"(?:[ \t]+(?i:woman|man|male|female|girl|boy|patient|adult|child|lady|gentleman|person))?[ \t]*,?[ \t]*(" + ADSOY + r")(?=[ \t]*[,.;:]|[ \t]+(?:[a-z]))"),
          re.compile(r"(?<![\w])(" + ADSOY + r")[ \t]*,[ \t]*(?:(?i:an?|aged)[ \t]+)?(?:" + YAS_EN + r"|\d{1,3}\s*yaşında)"),
          re.compile(r"(?<!\w)\d{4}[ \t]+doğumlu[ \t]+(" + ADSOY + r")"),
          re.compile(r"(?<![\w])(" + ADSOY + r")[ \t]*,[ \t]*\d{1,3}[ \t]*,"),                                  # Maria Lindqvist, 61, arrives …
          re.compile(r"(?<![\w])(?:(?i:hasta|patient|danışan)[ \t]+)?(" + ADSOY + r")[ \t]*\([ \t]*\d{1,3}[ \t]*(?:yaşında|yaşlı|years?\b|yo\b|y\b)"),  # Kemal Arslan (82 yaşında, 58 kg)
          re.compile(YAS_EN + r"(?:[ \t]+[a-z]{3,}){1,2}[ \t]*,[ \t]*(" + ADSOY + r")(?=[ \t]*[,.;:])")]            # a 34-year-old teacher, Sarah Whitfield,
# Yaş kalıbından sonra gelen büyük harfli sözcük bu listedeyse ad değildir (cinsiyet/hasta sözcüğü, kurum, yer, bölüm)
YAS_AD_DEGIL = {"hasta", "kadın", "erkek", "çocuk", "bebek", "kız", "oğlan", "genç", "yetişkin", "erişkin", "patient", "man", "woman",
                "male", "female", "girl", "boy", "adult", "child", "infant", "lady", "gentleman", "person", "emergency", "department",
                "hospital", "university", "clinic", "ward", "unit", "intensive", "care", "nurse", "doctor", "physician",
                "adım", "adı", "ad", "soyadım", "soyadı", "ismim", "ismi", "isim", "name", "my", "his", "her"}   # 'Adım Mesut, 31 yaşındayım' bir ad etiketidir
YAS_AD_KURUM = ("üniversite", "hastane", "bakanlı", "okul", "lise", "mahalle", "cadde", "sokak", "klinik", "merkez", "enstitü",
                "fakülte", "servis", "poliklinik", "bölüm", "kliniği", "dernek", "vakıf")


# Yaş kalıbının yanında John Doe / Jane Smith da gerçek bir ad gibi okunur ("58 yaşındaki John Smith" kimliktir); etiketli "Ad: John Smith" kuralı değişmedi.
YER_TUTUCU_AD = {"john", "jane", "smith", "doe"}


YAS_VAKA = re.compile(VAKA_BAGLAM.pattern + r"|emergency|hospital|\bward\b|presented|admitted|complain|symptom|diagnos|nurse|physician"
                      r"|\bacil|hastane|başvur|şikâyet|şikayet|taburcu|muayene|semptom|belirti", re.I)


# Klinik eylem: vaka bağlamının cümle düzeyindeki kanıtı. Genel 'klinik', 'hemşire' sözcüğü eylem değildir.
KLINIK_EYLEM = re.compile(r"başvur|getiril|getirdi|şikâyet|şikayet|yakınma|acile|acil\s+servis|yatırıl|yatış|taburcu|muayene|kabul\s+edil|sevk\s+edil"
                          r"|tedavi\s+(?:edil|altın|başlan)|arriv(?:ed|es|ing)\b|present(?:ed|s|ing)\b(?!\s+(?:the|a|an|his|her|their|its|our|this|that|these|those|results?|findings?|data|paper|idea|theory|case|work)\b)|admitted|admission|complain|referred|brought\s+(?:in|to)"
                          r"|\bsessions?\b|\bseans|homework|ev\s+ödevi|terapi\s+(?:seans|not)|exposure\s+therapy"
                          r"|was\s+(?:seen|treated|diagnosed)|diagnosed\s+with|hospitali[sz]ed|prescribed|underwent|ameliyat|reçete|semptom|symptom"
                          r"|wheez|hives|nöbet\s+geçir|teşhis|tanısı\s+kon|tanı\s+kon|vital\s+(?:bulgu|sign)|\bED\b|emergency\s+(?:department|room)", re.I)
# Tarihî/kamusal kişi işareti (yapısal): hükümdar sırası ya da unvan, 1900 öncesi/açık geçmiş yıl, meslek + geçmiş anlatı fiili
TARIH_UNVAN = re.compile(r"\bthrone\b|\btaht|\bkral\w*|\bkraliçe|\bimparator|\bsultan|\bking\b|\bqueen\b|\bemperor\b|\btsar\b|\bczar\b|\bpharaoh|"
                         r"firavun|\bprince|\bprens|\bduke\b|\bdük\b|\bcaliph|halife|\b(?:[IVXL]{2,7}|II)\b(?!\s*(?:diabet|tip|type))")
TARIH_YIL = re.compile(r"\b(?:in|during|by|until|since|around|circa|after|before|of)\s+(\d{4})\b|\b(\d{4})\s*['’]?\s*(?:da|de|ta|te)\b|"
                       r"\b(\d{4})\s+yılında|\b(\d{4})['’]?(?:den|dan|ten|tan)\b", re.I)
TARIH_MESLEK = re.compile(r"\b(?:nurse|physician|doctor|researcher|scientist|surgeon|psychologist|professor|hemşire|doktor|hekim|araştırmacı|"
                          r"bilim\s*insanı|cerrah|psikolog|profesör)\b", re.I)
TARIH_FIIL = re.compile(r"\b(?:led|founded|published|established|pioneered|invented|discovered|developed|wrote|taught|worked|worked\s+at|"
                        r"kurdu|kurmuş|yayımladı|yayımlamış|geliştirdi|geliştirmiş|çalışan|çalıştı|yazdı|keşfetti|keşfetmiş|öncülük|yönetti)\b", re.I)
VAKA_BASLIK = re.compile(r"worked\s+example|\bcases?\b|scenario|vignette|"
                         r"örnek\s+(?:olgu|vaka|sunum)|\bolgu|\bvaka|senaryo|çözümlü\s+örnek|örnek\s+sunum", re.I)


# 'Case: Dosing Sheet' gibi başlık söz öbekleri ad değildir
ETIKET_AD_DEGIL = {"study", "studies", "report", "reports", "example", "examples", "presentation", "sheet", "frame", "analysis", "review",
                   "management", "summary", "series", "notes", "note", "definition", "history", "scenario", "discussion", "outcome",
                   "plan", "table", "dosing", "dose", "protocol", "guideline", "overview", "introduction", "conclusion", "exercise",
                   "çalışması", "raporu", "örnek", "örneği", "sunumu", "özeti", "tablosu", "planı", "analizi", "tartışma", "giriş", "sonuç"}


YAS_VAKA_GENIS = re.compile(YAS_VAKA.pattern + "|" + KLINIK_EYLEM.pattern, re.I)


def cumle_penceresi(t: str, bas: int, son: int) -> str:
    """Eşleşmeyi içeren cümle (çok uzun satırda ≤ 600 karakterlik pencere; ondalık nokta cümleyi bölmez)."""
    a = max(0, bas - 300)
    onceki = t[a:bas]
    ayrac = [m.end() for m in re.finditer(r"(?<=[.!?])\s+(?=[A-ZÇĞİÖŞÜ0-9\"“(])", onceki)]
    bas_c = a + (ayrac[-1] if ayrac else 0)
    sonraki = t[son:son + 300]
    m2 = re.search(r"(?<=[.!?])\s+(?=[A-ZÇĞİÖŞÜ0-9\"“(])", sonraki)
    return t[bas_c:son + (m2.start() if m2 else len(sonraki))]


def tarihi_isaret(cumle: str, yil: int) -> bool:
    """Cümle tarihî/kamusal kişiyi anlatıyor mu: yapısal işaretler (ad listesi yok)."""
    for y in YIL.findall(cumle):
        if int(y) < 1900 or int(y) <= yil - 40:
            return True
    for m in TARIH_YIL.finditer(cumle):
        y = int(next(g for g in m.groups() if g))
        if y <= yil - 10:
            return True
    if TARIH_UNVAN.search(cumle):
        return True
    return bool(TARIH_MESLEK.search(cumle) and TARIH_FIIL.search(cumle))


def yas_ad_mi(ad: str) -> bool:
    soz = [tr_kucuk(w) for w in ad.split()]
    if any(w.startswith(KLINIK_KOK) or w.startswith(YAS_AD_KURUM) or w in YAS_AD_DEGIL
           or (w in AD_DEGIL and w not in AD_OLABILIR and w not in YER_TUTUCU_AD) for w in soz):
        return False
    return True


def k_hasta_kimlik(c, ekle):
    """Ortak çekirdek: her alanda (HIPAA Safe Harbor tanımlayıcıları; kimliksizleştirme yönetmeliği)."""
    paragraf_kurmaca = paragraf_bayragi(c, KURMACA)
    paragraf_vaka = paragraf_bayragi(c, VAKA_BAGLAM)
    paragraf_yas_vaka = paragraf_bayragi(c, YAS_VAKA_GENIS)
    saglik = bool(c["alanlar"] & SAGLIK_ALANLAR)
    satirlar = tarama_satirlari(c)
    bolum_vaka, son_baslik = {}, False             # satır no → bölüm başlığı vaka bağlamı mı ('Worked example', 'Case', 'Senaryo'…)
    for x in c["satirlar"]:
        if x["ham"].lstrip().startswith("#"):
            son_baslik = bool(VAKA_BASLIK.search(x["tam"]))
        bolum_vaka[x["no"]] = son_baslik
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
        bildirilen_ad = {m.group(1) for desen in (HASTA_AD, HASTA_AD_VIRGUL, HASTA_AD_KUCUK) for m in desen.finditer(t)}
        yas_vaka_par = paragraf_yas_vaka.get(id(st), bool(YAS_VAKA_GENIS.search(t))) or bolum_vaka.get(no, False)
        for m in itertools.islice(HASTA_AD_ETIKET2.finditer(t), 100):       # Danışan: / Client: / Olgu: / Case 2:
            ad = m.group(1)
            if ad in bildirilen_ad or not _ad_mi(ad) or not yas_ad_mi(ad) or t.startswith("#") \
                    or any(w in ETIKET_AD_DEGIL for w in tr_kucuk(ad).split()):
                continue
            bildirilen_ad.add(ad)
            c["maske"].add(ad)
            if saglik or yas_vaka_par:
                ekle("Doğruluk", duzey, f"Vakada hasta adı ({_maskele(ad)}){not_}",
                     "Adı çıkar; yaş ve cinsiyetle anlat ('58 yaşında erkek hasta')", ornek=ad, satir=no)
            else:
                ekle("Doğruluk", "UYARI", f"Etiketli ad-soyad ({_maskele(ad)}); vaka bağlamı yok",
                     "Gerçek bir kişiyse adı çıkar; yaş ve cinsiyetle anlat", ornek=ad, satir=no)
        for desen in YAS_AD:
            for m in itertools.islice(desen.finditer(t), 100):
                ad = m.group(1)
                if ad in bildirilen_ad or not yas_ad_mi(ad):
                    continue
                bildirilen_ad.add(ad)
                cumle = cumle_penceresi(t, m.start(), m.end())
                klinik = bool(KLINIK_EYLEM.search(cumle))
                tarihi = tarihi_isaret(cumle, c["yil"])
                vaka_ = (klinik or yas_vaka_par) and not (tarihi and not klinik)
                c["maske"].add(ad)
                if not vaka_:
                    ek_not = "; tarihî/kamusal kişi gibi görünüyor (yıl, unvan ya da meslek + anlatı)" if tarihi and not klinik else \
                        "; vaka bağlamı yok, biyografiyse sorun değil"
                    ekle("Doğruluk", "UYARI", f"Yaşın yanında ad-soyad ({_maskele(ad)}){ek_not}",
                         "Gerçek bir hasta/öğrenciyse adı çıkar; yaş ve cinsiyetle anlat", ornek=ad, satir=no)
                else:
                    ekle("Doğruluk", duzey, f"Vakada hasta adı ({_maskele(ad)}){not_}",
                         "Adı çıkar; yaş ve cinsiyetle anlat ('58 yaşında erkek hasta')", ornek=ad, satir=no)
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
        dogumlar = [(m.group(1), m.group(2) or m.group(3) or m.group(4) or "") for m in DOGUM.finditer(t)]
        dogumlar += [(m.group(1), (re.search(r"(?<!\d)(\d{4})(?!\d)", m.group(1)) or [None, ""])[1]) for m in DOGUM_PAREN.finditer(t)]
        for tarih_metni, yil in dogumlar:
            yil = (int(yil) + (2000 if int(yil) <= c["yil"] % 100 else 1900) if len(yil) == 2 else int(yil)) if yil.isdigit() else 0
            if yil and yil < 1930 and not vaka:
                continue          # tarihsel kişi (vaka bağlamı yok)
            c["maske"].add(tarih_metni)
            if vaka or saglik:
                ekle("Doğruluk", duzey, f"Vakada tam doğum tarihi{not_}", "Tam tarihi çıkar; yaşı yaz", ornek=tarih_metni, satir=no)
            else:
                ekle("Doğruluk", "UYARI", "Tam doğum tarihi (vaka bağlamı yok; biyografiyse sorun değil)",
                     "Gerçek bir öğrenci/hasta değilse yoksay; kişisel veriyse çıkar", ornek=tarih_metni, satir=no)
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
    kiril_satir, yunan_satir = [], []             # (satır no, sözcükler): karışık alfabe geçen her satır (S12)
    for x in c["satirlar"]:
        if not x["gor"] or (not KIRIL.search(x["gor"]) and not YUNAN.search(x["gor"])):
            continue
        kar = karisik_sozcukler(x["gor"])
        k_ = [w for w in kar if KIRIL.search(w)]
        y_ = [w for w in kar if YUNAN.search(w) and not KIRIL.search(w)]
        if k_:
            kiril_satir.append((x["no"], k_))
        if y_:
            yunan_satir.append((x["no"], y_))
    kiril = [w for _, ws in kiril_satir for w in ws]
    yunan = [w for _, ws in yunan_satir for w in ws]
    if kiril_satir:
        for sira, (no, ws) in enumerate(kiril_satir[:ALFABE_SATIR_TAVAN]):
            kalan = len(kiril_satir) - ALFABE_SATIR_TAVAN
            ek_not = f" (+{kalan} satır daha)" if sira == ALFABE_SATIR_TAVAN - 1 and kalan > 0 else ""
            ek("alfabe")("Doğruluk", "HATA", f"Latin harfle karışık Kiril harfi ({len(ws)} sözcük: {', '.join(sorted(set(ws))[:3])}){ek_not}"
                         if sira else f"Latin harfle karışık Kiril harfi ({len(kiril)} sözcük, {len(kiril_satir)} satır: {', '.join(sorted(set(kiril))[:3])}){ek_not}",
                 "--duzelt benzer Kiril harfleri Latin harfe çevirir", ornek=ws[0], satir=no)
    if yunan and not gevsek:
        uzun = [s for s in yunan if len(s) >= 4 and len(LATIN.findall(s)) >= 2]
        for sira, (no, ws) in enumerate(yunan_satir[:ALFABE_SATIR_TAVAN]):
            kalan = len(yunan_satir) - ALFABE_SATIR_TAVAN
            ek_not = f" (+{kalan} satır daha)" if sira == ALFABE_SATIR_TAVAN - 1 and kalan > 0 else ""
            ek("alfabe")("Doğruluk", "HATA" if uzun else "UYARI",
                         f"Latin harfle karışık Yunan harfi ({len(ws)} sözcük: {', '.join(sorted(set(ws))[:3])}){ek_not}",
                         "Sembol değilse Latin harfe çevir; formülse alanı belirt (alan: fizik)", ornek=ws[0], satir=no)
    for x in c["satirlar"][:]:                    # S15: URL / e-posta / dosya yolu / bağlantı hedefinde karışık alfabe: --duzelt dokunmaz, elle bak
        if x["kod"] or not x["ham"] or not (KIRIL.search(x["ham"]) or YUNAN.search(x["ham"])):
            continue
        for b_, s_ in _baglanti_araliklari(x["ham"]):
            parca = x["ham"][b_:s_]
            if LATIN.search(parca) and (KIRIL.search(parca) or YUNAN.search(parca)):
                ek("alfabe")("Doğruluk", "UYARI", "Bağlantıda/adreste Latin harfle karışık Kiril ya da Yunan harf: elle bak (--duzelt dokunmaz)",
                             "Adres, e-posta ve dosya yolundaki harf değiştirilmez; doğru adresi kaynaktan kontrol et", ornek=parca[:60], satir=x["no"])
                break
    ph = [(x["no"], x["ham"], x["gor"]) for x in c["satirlar"] if not x["kod"] and "???" in x["ham"]]
    for no, ham, gor_ in ph:
        # hücrenin tamamı / satır sonu / cümle ortasında bağımsız jeton (iki yanı boşluk, satır ucu ya da noktalama; sözcüğe yapışık 'Neden???' değil)
        if re.search(r"\|\s*\?{3,}\s*(?=\|)|\|\s*\?{3,}\s*$|[:=]\s*\?{3,}\s*$", ham) or YER_TUTUCU_JETON.search(gor_):
            ek("yer_tutucu")("Doğruluk", "HATA", "Bitmemiş yer işareti (???) tablo hücresinde ya da satır sonunda", "Tamamla ya da sil",
                             ornek=re.search(r"[^|:=]*\?{3,}", ham).group(0).strip() or "???", satir=no)
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
            alt_, ust_ = KUTU_ORAN_ALT, KUTU_ORAN_UST
            if olcum.get("oran"):
                alt_, ust_ = olcum["oran"][0] * (1 - ORAN_PAYI), olcum["oran"][1] * (1 + ORAN_PAYI)
            en_az, en_cok = kutu / ust_, kutu / alt_
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
            yil: int | None = None, pdf_metin: str | None = None, pdf_olculemedi: bool = False) -> dict:
    """metin: .md içeriği; olcum: pdf_olc() sonucu ya da None; alan/dil: tespiti geçmek için; yil: değerlendirme yılı;
    pdf_metin: PDF'ten çıkarılan metin (verilirse kimlik ve ilaç güvenlik kontrolleri PDF'te de çalışır)."""
    profil = profiller()
    meta, govde, ofset = on_bilgi(metin)
    satirlar = hazirla_satirlar(govde, ofset)
    gor = "\n".join(x["gor"] for x in satirlar)
    tam = "\n".join(x["tam"] for x in satirlar)
    birimler, belge_dili = birim_analizi(satirlar)
    satir_dili_ = {no: b["dil"] for b in birimler for no in b["nolar"]}
    tespit = alan_tespit(meta, gor, profil, alan, birimler)
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
    ek_alanlar = [] if tespit["kaynak"] == "kullanıcı seçimi" else bolum_alanlari(govde, profil, a, belge_dili)
    alanlar = {a, *ek_alanlar}
    tur = re.sub(r"[\s_]+", "-", meta.get("tur", "").strip().lower())
    govde_kodsuz = re.sub(r"^```.*?^```", " ", govde, flags=re.S | re.M) if govde.count("```") < 2000 else govde
    tbl = tablo_ayristir(satirlar)
    ogr_harita = tablo_ogretici_haritasi(tbl)
    for x in satirlar:
        if ogr_harita.get(x["no"]):
            x["ogretici"] = True
    tablo_ = tablolar(satirlar)
    for x in tablo_:
        if ogr_harita.get(x["no"]):
            x["ogretici"] = True
    c = {"meta": meta, "govde": govde, "govde_kodsuz": govde_kodsuz, "gor": gor, "tam": tam, "kucuk": tr_kucuk(gor),
         "kucuk_en": en_kucuk(gor), "tur": tur, "olcum": olcum, "dil": dil_kodu, "satirlar": satirlar,
         "tablo": tablo_, "okunuslar": OKUNUS.findall(gor), "bicim": bicim_tespit(meta, govde, gor, olcum),
         "alanlar": alanlar, "yil": yil or date.today().year, "maske": set(),
         "satir_dili": satir_dili_, "belge_dili": belge_dili, "tbl": tbl}
    bulgu: list[dict] = []

    def ekleyici(kural, kaynak="md"):
        def ekle(boyut, duzey, mesaj, oneri="", ornek="", satir=None):
            bulgu.append({"boyut": boyut, "duzey": duzey, "mesaj": mesaj, "oneri": oneri, "kural": kural,
                          "ornek": ornek, "satir": satir, "kaynak": kaynak})
        return ekle

    cekirdek(c, ekleyici, profil[a])
    genis = max((s_["ham"].count("|") for tb in tbl for s_ in tb["blok"]), default=0)
    if genis > TABLO_SUTUN_TAVAN + 1:
        ekleyici("tablo_genis")("Doğruluk", "UYARI", f"Tablo çok geniş (~{genis - 1} sütun): her satırın ilk {TABLO_SUTUN_TAVAN} sütunu denetlendi, sonrası taranmadı",
                                "Tabloyu böl; geniş tablo öğrenciye de okunaksızdır")
    if pdf_olculemedi:
        ekleyici("pdf_okunamadi")("Okunaklılık", "UYARI", "Aynı adlı PDF var ama ölçülemedi (bozuk ya da okunamadı): PDF denetlenmedi",
                                  "PDF'i yeniden üret; karar PDF ölçülmeden verilemez")
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
                   or LAB_IZI.search(x["tam"]) or RISK_ORAN.search(x["tam"]) for x in satirlar + c["tablo"])
    risk = risk_izi and not all(k in kontroller for k in RISK_KONTROLLERI)
    if risk:
        kontroller += [k for k in RISK_KONTROLLERI if k not in kontroller]
    for k in kontroller:
        KONTROLLER[k](c, ekleyici(k))

    # PDF metni: kimlik ve ilaç güvenliği PDF'te de (md ile PDF farklı olabilir)
    if pdf_metin:
        ps = [{"no": None, "tam": satir_hazirla(x), "gor": satir_hazirla(x), "kod": False, "ham": x}
              for x in pdf_metin.splitlines()]
        cp = dict(c, satirlar=ps, tablo=[], tbl=tablo_ayristir(ps), _dz=None, tam="\n".join(x["tam"] for x in ps), gor="\n".join(x["gor"] for x in ps))
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
    elif elle_eksik or belge_engel_susturuldu or pdf_olculemedi:
        karar = "karar için denetim eksik"
    else:
        karar = "tanımlı kapsamda uygun"
    return {"alan": a, "alan_adi": profil[a]["ad"], "ek_alanlar": ek_alanlar, "tespit": tespit,
            "risk_taramasi": risk, "bicim": c["bicim"], "dil": dil_kodu, "belge_dili": belge_dili, "tur": c["tur"],
            "degerlendirme_yili": c["yil"], "puan": puan, "toplam": sum(olculen), "azami": 2 * len(olculen),
            "olculen_boyut": len(olculen), "bulgular": bulgu, "susturulan": susturulan,
            "belge_duzeyi_engel_susturuldu": belge_engel_susturuldu, "elle": elle, "elle_eksik": elle_eksik,
            "elle_reddedilen": [k for k in elle if elle_ham[k] and not elle[k]],
            "elle_liste": elle_listesi(profil, a) + (profil["_gorsel"]["elle"] if c["bicim"] == "gorsel" else []),
            "kontroller": kontroller, "pdf_icerik_denetlendi": bool(pdf_metin),
            "sayfa": olcum["sayfa"] if olcum else None,
            "kutu_pt": (olcum.get("kutu", olcum.get("yazi")) if olcum else None),
            "sonuc": "ENGEL" if engel else "HATA" if hata else ("UYARI" if bulgu else "TEMIZ"),
            "pdf_olculemedi": bool(pdf_olculemedi), "karar": karar}


# ── Düzeltme ──
BAGLANTI_DESENLERI = [re.compile(r"(?i)\b(?:https?|ftp)://[^\s<>\"')\]]+"), re.compile(r"(?i)\bwww\.[^\s<>\"')\]]+"),
                      re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"),
                      re.compile(r"\]\(\s*<?([^)\s>]+)"),                                   # Markdown bağlantı hedefi
                      re.compile(r"(?:(?<=[\s(\"'])|^)(?:~|\.{1,2})?/(?:[^\s/<>()\"']+/)+[^\s/<>()\"']+"),   # dosya yolu (en az 2 parça)
                      re.compile(r"\b[A-Za-z]:\\[^\s<>\"']+")]


def _baglanti_araliklari(metin: str) -> list[tuple[int, int]]:
    """URL, e-posta, dosya yolu ve Markdown bağlantı hedefinin aralıkları ((başlangıç, bitiş), birleşik)."""
    ar = []
    for d in BAGLANTI_DESENLERI:
        for i, m in enumerate(d.finditer(metin)):
            if i >= 500:
                break
            ar.append(m.span(1) if m.re.groups and m.group(1) else m.span())
    ar.sort()
    birlesik = []
    for a, b in ar:
        if birlesik and a <= birlesik[-1][1]:
            birlesik[-1] = (birlesik[-1][0], max(birlesik[-1][1], b))
        else:
            birlesik.append((a, b))
    return birlesik


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
    birles = []
    for a, b in sorted(_korunan_araliklar(govde) + _baglanti_araliklari(govde)):
        if birles and a <= birles[-1][1]:
            birles[-1] = (birles[-1][0], max(birles[-1][1], b))
        else:
            birles.append((a, b))
    for a, b in birles:
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
    grup = f" · grup: {t['grup']}" if t.get("grup") else ""
    print(f"  Alan: {s['alan_adi']}{dil} · {t['kaynak']}, destek {t['destek']}{neden}{ikinci} · biçim: {s['bicim']}"
          f" · belge dili: {s['belge_dili']}{grup}")
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
    olcum, pdf_metin, pdf_olculemedi = None, None, False
    if pdf.is_file() and md_degisti:
        notlar.append("md düzeltildiği için eski PDF ölçülmedi; PDF'i yeniden üretip tekrar çalıştır")
    elif pdf.is_file():
        olcum = pdf_olc(pdf)
        if olcum is None:
            notlar.append("PDF ölçülemedi (pdftotext/pdfimages yok ya da PDF okunamadı)")
            pdf_olculemedi = True
        elif not olcum["metin_var"]:
            notlar.append("PDF'te metin katmanı yok (taranmış olabilir): yazı boyu, sayfa ve PDF içeriği ölçülmedi")
        else:
            r = subprocess.run(["pdftotext", "-enc", "UTF-8", "-layout", str(pdf), "-"], capture_output=True,
                               encoding="utf-8", errors="replace")
            pdf_metin = r.stdout if r.returncode == 0 else None
    try:
        s = denetle(metin, olcum, arg["alan"], arg["dil"], yil, pdf_metin, pdf_olculemedi)
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
