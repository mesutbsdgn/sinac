#!/usr/bin/env python3
"""Altın küme ölçümü: scripts/tests/altin/ altındaki belgeleri denetler, beklenen.json ile karşılaştırır.

Ölçülenler (dil başına ve toplam): alan isabeti, karar isabeti, kaçırılan ENGEL/HATA (beklenen satırda bulgu yok),
yanlış ENGEL/HATA (beklenmeyen satırda bulgu). Beklentiler belgeler yazılırken, betik çalıştırılmadan kaydedildi.

  python3 scripts/altin_olc.py            # özet tablo + belge belge farklar
  python3 scripts/altin_olc.py --json     # makine okur
"""
import json
import os
import sys
from collections import defaultdict

sys.dont_write_bytecode = True
BURA = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BURA)
import ogretim_denetim as o  # noqa: E402

KLASOR = os.environ.get("ALTIN_KLASOR") or os.path.join(BURA, "tests", "altin")
YIL = 2026


def satir_bul(metin, parca):
    """parca'nın geçtiği 1 tabanlı satır numaraları."""
    return [i for i, s in enumerate(metin.splitlines(), 1) if parca in s]


def olc():
    beklenen = json.load(open(os.path.join(KLASOR, "beklenen.json"), encoding="utf-8"))
    sonuc = []
    for k in beklenen:
        metin = open(os.path.join(KLASOR, k["dosya"]), encoding="utf-8").read()
        s = o.denetle(metin, None, None, None, YIL)
        agir = [b for b in s["bulgular"] if b["duzey"] in ("ENGEL", "HATA") and b.get("kaynak", "md") == "md"]
        agir_satir = defaultdict(list)
        for b in agir:
            agir_satir[b.get("satir")].append(b)
        beklenen_satir = set()
        kacan = []
        for e in k.get("engel", []) + k.get("hata", []):
            sat = satir_bul(metin, e["satir_metni"])
            if len(sat) != 1:
                kacan.append({**e, "sorun": f"satir_metni {len(sat)} kez geçiyor"})
                continue
            beklenen_satir.add(sat[0])
            if not agir_satir.get(sat[0]):
                kacan.append({**e, "satir": sat[0]})
        yanlis = [b for b in agir if b.get("satir") not in beklenen_satir]
        sonuc.append({
            "dosya": k["dosya"], "dil": k["dil"],
            "grup_beklenen": o.alan_grubu(o.profiller(), k["alan"]), "grup_bulunan": s.get("tespit", {}).get("grup")
            or o.alan_grubu(o.profiller(), s["alan"]),
            "alan_beklenen": k["alan"], "alan_bulunan": s["alan"],
            "karar_beklenen": k["karar"], "karar_bulunan": s["karar"],
            "kacan": kacan,
            "yanlis": [{"satir": b.get("satir"), "duzey": b["duzey"], "kural": b["kural"], "ornek": b.get("ornek", "")}
                       for b in yanlis],
        })
    return beklenen, sonuc


def ozet(beklenen, sonuc):
    tablo = {}
    for dil in ("tr", "en", "toplam"):
        r = [x for x in sonuc if dil == "toplam" or x["dil"] == dil]
        b = [k for k in beklenen if dil == "toplam" or k["dil"] == dil]
        tablo[dil] = {
            "belge": len(r),
            "alan_dogru": sum(x["alan_beklenen"] == x["alan_bulunan"] for x in r),
            "grup_dogru": sum(x["grup_beklenen"] == x["grup_bulunan"] and x["alan_bulunan"] != "genel"
                              for x in r),
            "karar_dogru": sum(x["karar_beklenen"] == x["karar_bulunan"] for x in r),
            "beklenen_engel": sum(len(k.get("engel", [])) + len(k.get("hata", [])) for k in b),
            "kacan_engel": sum(len(x["kacan"]) for x in r),
            "yanlis_engel": sum(len(x["yanlis"]) for x in r),
            "yanlis_engelli_belge": sum(bool(x["yanlis"]) for x in r),
        }
    return tablo


def main(argv):
    beklenen, sonuc = olc()
    tablo = ozet(beklenen, sonuc)
    if "--json" in argv:
        print(json.dumps({"ozet": tablo, "belgeler": sonuc}, ensure_ascii=False, indent=1))
        return 0
    print("| Dil | Belge | Alan doğru | Grup doğru | Karar doğru | Beklenen ENGEL/HATA | Kaçan | Yanlış ENGEL/HATA (belge) |")
    print("|---|---|---|---|---|---|---|---|")
    for dil, t in tablo.items():
        print(f"| {dil} | {t['belge']} | {t['alan_dogru']} | {t['grup_dogru']} | {t['karar_dogru']} | {t['beklenen_engel']} | "
              f"{t['kacan_engel']} | {t['yanlis_engel']} ({t['yanlis_engelli_belge']}) |")
    print()
    for x in sonuc:
        farklar = []
        if x["alan_beklenen"] != x["alan_bulunan"]:
            farklar.append(f"alan {x['alan_beklenen']} → {x['alan_bulunan']}")
        if x["karar_beklenen"] != x["karar_bulunan"]:
            farklar.append(f"karar «{x['karar_beklenen']}» → «{x['karar_bulunan']}»")
        for e in x["kacan"]:
            farklar.append(f"KAÇAN {e['tur']} satır {e.get('satir', '?')}: {e['satir_metni'][:60]} {e.get('sorun', '')}")
        for y in x["yanlis"]:
            farklar.append(f"YANLIŞ {y['duzey']} [{y['kural']}] satır {y['satir']}: {str(y['ornek'])[:60]}")
        if farklar:
            print(f"- {x['dosya']}")
            for f in farklar:
                print(f"    {f}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
