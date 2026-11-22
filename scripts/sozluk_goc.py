#!/usr/bin/env python3
"""Alan sözlüklerini F3 şemasına göç ettirir (idempotent): references/ogretim-alanlari.json

Eski şema: alan başına tek `sozcukler` listesi (Türkçe, bir kısmı İngilizce, bir kısmı çok sözcüklü).
Yeni şema: `sozcukler` (Türkçe tek sözcük/kök), `obekler` (Türkçe öbek), `sozcukler_en`, `obekler_en`,
`kisaltmalar` (dilden bağımsız tam sözcük). Ayrıca `_alan_gruplari` eklenir ve `_aciklama` güncellenir.

  python3 scripts/sozluk_goc.py            # göçü uygular, taşınanların listesini yazdırır
  python3 scripts/sozluk_goc.py --kuru     # dosyaya yazmaz, yalnız listeyi gösterir

Sınıflandırma açık listelerle yapılır (otomatik dil tahmini yok): listede olmayan öğe Türkçe sayılır;
boşluk içeriyorsa `obekler`'e, değilse `sozcukler`'de kalır. İkinci çalıştırma hiçbir şeyi değiştirmez.
"""
import json
import sys
from pathlib import Path

DOSYA = Path(__file__).resolve().parents[1] / "references" / "ogretim-alanlari.json"

# İngilizce öğeler: tek sözcük → sozcukler_en, çok sözcüklü → obekler_en (Türkçe listeden çıkar).
INGILIZCE = {
    "diagnosis", "treatment", "patient", "clinical", "dose", "drug", "syndrome", "symptom", "therapy", "infection",
    "mg daily", "hypertension", "physician", "medication", "nursing", "nurse", "care plan", "nursing diagnosis",
    "pharmacokinetics", "pharmacology", "bioavailability", "half-life", "drug interaction", "veterinary", "dog", "cat",
    "cattle", "livestock", "nutrition", "diet", "dietitian", "calorie", "physiotherapy", "rehabilitation",
    "range of motion", "emergency", "resuscitation", "triage", "psychology", "cognitive", "behavior", "psychiatry",
    "theorem", "proof", "derivative", "equation", "matrix", "statistics", "regression", "hypothesis",
    "confidence interval", "algorithm", "function", "variable", "loop", "compiler",
}
# İki dilde aynı yazılan sözcükler: hem Türkçe hem İngilizce listede kalır.
IKI_DILDE = {"sepsis", "mastitis", "ruminant", "atom", "element", "protein", "mineral", "vitamin", "momentum", "limit",
             "mol", "newton", "joule"}
# Dilden bağımsız kısaltma, simge ve kod simgeleri: kisaltmalar.
KISALTMA = {"mmhg", "mg/kg", "fdi", "nanda", "kcal", "bki", "eha", "abcde", "kpr", "gks", "cpr", "dsm", "ph", "dna", "anova",
            "python", "java", "javascript", "sql", "api", "github", "gsyh", "km²",
            "print(", "def", "return", "select", "insert into", "import numpy", "import pandas", "from import",
            "\\frac", "\\int", "∫", "∑", "√"}

GRUPLAR = {
    "saglik": ["tip", "dis", "hemsirelik", "eczacilik", "veteriner", "beslenme", "fizyoterapi", "acil", "psikoloji"],
    "sayisal_fen": ["matematik", "istatistik", "fen", "fizik", "kimya", "biyoloji", "yer_bilimleri", "ziraat",
                    "muhendislik", "bilgisayar", "mimarlik"],
    "sosyal_beseri": ["hukuk", "iktisat", "tarih", "cografya", "sosyal", "ilahiyat", "edebiyat", "felsefe", "sanat",
                      "egitim"],
    "dil_genel": ["dil", "genel"],
}

ACIKLAMA = (
    "ogretim_denetim.py alan profilleri. Alan: ad, isteğe bağlı ust (alt alan: üst alanın sözcükleri de geçse daha özel "
    "olan seçilir), kontroller (betikteki KONTROLLER adları ya da '@grup'), elle_gruplar, elle, sinama_oneri ve alan "
    "sözlükleri. Sözlük anahtarları (hepsi isteğe bağlı, küçük harf): sozcukler (Türkçe tek sözcük ya da kök; Türkçe "
    "birimde ek zinciriyle eşleşir; 4 harf ve kısası yalnız tam sözcük + ek, \"plan\", \"baz\", \"tür\" gibi genel sözcük "
    "koyma), obekler (Türkçe çok sözcüklü öbek; son sözcük ek alabilir; ağırlık 2), sozcukler_en (İngilizce terim; tam "
    "sözcük + -s/-es/-ies çoğul), obekler_en (İngilizce öbek; son sözcük çoğul alabilir, öbekler tekil yazılır; ağırlık 2), "
    "kisaltmalar (dilden bağımsız kısaltma, simge, kod simgesi; büyük/küçük harf duyarsız tam sözcük; fr birimde de sayılır). "
    "Türkçe listeler yalnız Türkçe birimde, İngilizce listeler yalnız İngilizce birimde sayılır; Fransızca ve öteki "
    "birimler alan puanına katılmaz. Kod blokları yalnız bilgisayar alanına katkı verir; kod_sozcukler (def, return, "
    "select…) yalnız kod bloğunda sayılır, düzyazıda puan vermez. '_' ile başlayan anahtarlar profil "
    "değildir: _gruplar ve _elle_gruplar ortak listeler, _alan_gruplari alan grupları (saglik, sayisal_fen, sosyal_beseri, "
    "dil_genel), _gorsel görsel biçim eki. Gerekçeler: references/ogretim.md ve docs/kanitlar.md. '_ortak_elle' her alanın "
    "elle listesinin başına eklenir. Hasta kimliği ve TC kimlik kontrolleri ortak çekirdektedir; ilaç/doz örüntüsü "
    "görülürse sağlık güvenlik kontrolleri alandan bağımsız çalışır (risk taraması)."
)


def ekle(liste: list, oge: str) -> bool:
    if oge in liste:
        return False
    liste.append(oge)
    return True


def goc(profil: dict) -> list[str]:
    """Profili yerinde göç ettirir; yapılan her taşımayı satır olarak döndürür."""
    log = []
    for ad, p in profil.items():
        if ad.startswith("_") or not isinstance(p, dict) or "sozcukler" not in p:
            continue
        kalan, yeni = [], {"obekler": list(p.get("obekler", [])), "sozcukler_en": list(p.get("sozcukler_en", [])),
                           "obekler_en": list(p.get("obekler_en", [])), "kisaltmalar": list(p.get("kisaltmalar", []))}
        for oge in p["sozcukler"]:
            s = oge.strip()
            if s in KISALTMA:
                if ekle(yeni["kisaltmalar"], s):
                    log.append(f"{ad}: {s!r} -> kisaltmalar")
            elif s in INGILIZCE:
                anahtar = "obekler_en" if " " in s else "sozcukler_en"
                if ekle(yeni[anahtar], s):
                    log.append(f"{ad}: {s!r} -> {anahtar}")
            elif s in IKI_DILDE:
                kalan.append(s)
                if ekle(yeni["sozcukler_en"], s):
                    log.append(f"{ad}: {s!r} -> hem sozcukler hem sozcukler_en (iki dilde aynı)")
            elif " " in s:
                if ekle(yeni["obekler"], s):
                    log.append(f"{ad}: {s!r} -> obekler")
            else:
                kalan.append(s)
        p["sozcukler"] = kalan
        sirali = {}
        for k, v in p.items():
            if k in yeni and k in sirali:      # yeni liste zaten "sozcukler"in ardına kondu; eskisi ezmesin
                continue
            sirali[k] = v
            if k == "sozcukler":
                for yk in ("obekler", "sozcukler_en", "obekler_en", "kisaltmalar"):
                    if yeni[yk]:
                        sirali[yk] = yeni[yk]
        for yk in ("obekler", "sozcukler_en", "obekler_en", "kisaltmalar"):   # sozcukler'i boşalmış olsa da yer koru
            if yeni[yk] and yk not in sirali:
                sirali[yk] = yeni[yk]
        p.clear()
        p.update(sirali)
    if profil.get("_alan_gruplari") != GRUPLAR:
        profil["_alan_gruplari"] = GRUPLAR
        log.append("_alan_gruplari eklendi/güncellendi")
    if profil.get("_aciklama") != ACIKLAMA:
        profil["_aciklama"] = ACIKLAMA
        log.append("_aciklama güncellendi")
    return log


def main(argv: list[str]) -> int:
    ham = DOSYA.read_text(encoding="utf-8")
    profil = json.loads(ham)
    log = goc(profil)
    for satir in log:
        print(satir)
    print(f"-- {len(log)} değişiklik")
    yeni = json.dumps(profil, ensure_ascii=False, indent=1) + "\n"
    if "--kuru" in argv:
        return 0
    if yeni != ham:
        DOSYA.write_text(yeni, encoding="utf-8")
        print(f"yazıldı: {DOSYA}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
