---
name: ogretim-denetci
description: "Öğretim Denetçisi — ders notu, konu anlatımı, rehber, çalışma kâğıdı, ezber/kelime listesi ve öğrenci PDF'ini kanıta dayalı 8 boyutlu ölçekle denetler (doğruluk, hedef uyumu, seviye, ezber ve kavrama, okunaklılık, sıra ve akış, kendini sınama, verimlilik; /16) ve 'yayınlanabilir mi' kararı verir. Belgenin bilim dalını (32 alan: tıp, diş, hemşirelik, eczacılık, veteriner, beslenme, fizyoterapi, acil, psikoloji, matematik, istatistik, fizik, kimya, biyoloji, mühendislik, bilgisayar, hukuk, iktisat, tarih, coğrafya, ilahiyat, edebiyat, sanat, mimarlık, yabancı dil…) ve görsel/sözel biçimini kendisi tanır. Sağlıkta doz yazımı (5,0 mg), ISMP kısaltmaları, hasta kimliği, TC kimlik no, kılavuz yaşı; hukukta mülga kanun; fende SI birimi. Use when the user asks to check, audit or score study notes, lecture notes, a teaching PDF or a vocabulary list: 'ders notumu denetle', 'bu PDF öğretir mi', 'notum doğru yazılmış mı', 'öğretim materyali ölçeği'."
version: "1.0.0"
metadata:
  author: mesutbsdgn
  tags: [education, teaching-materials, medical-education, quality-check, turkish]
---

# Öğretim Denetçisi

Öğrenciye giden belgeyi bir öğretim tasarımcısı ve alanın titiz bir hocası gibi denetle: önce **alanı** ve **biçimi**
belirle, sonra her alanda aynı kalan ortak çekirdeği ve o alanın profilini uygula, puanla, karar ver. Dil
sadeleştirme bu becerinin işi değildir (o iş Durulaç'ın, `turkce-ai-durulac`).

**Zorunlu okuma:** `references/ogretim.md` (8 boyut, eşikler, alan tabloları, elle kontrol listesi, ortak dil şablonu).

## Ne zaman açık, ne zaman kapalı

- **Açık:** ders notu, konu anlatımı, rehber, çalışma kâğıdı, ezber/kelime listesi, sınav hazırlık notu, pano; hukuk
  ve edebiyat **ders notu** da dahil.
- **Kapalı:** sözleşme, dilekçe, resmî yazı, edebî eserin kendisi, sohbet, akademik makale/tez (tez için Durulaç
  `--tur tez`).

## İş akışı

1. Belgeyi oku; hedefi (sınav görevi ya da öğrenme hedefi) ve seviyeyi belirle. Metin dosyada değilse `.md` olarak yaz.
2. Kullanıcı dilin sadeleşmesini de istediyse Durulaç'ın Temizle kipini **yalnız Türkçe açıklamaya** uygula; yabancı
   örnek cümle, okunuş, formül, doz, diş/kanun numarası, tablo aynen kalır. İstenmediyse metne dokunma.
3. Denetle:
   ```bash
   python3 scripts/ogretim_denetim.py BELGE.md [--pdf BELGE.pdf] [--alan AD] [--dil fr] [--json] [--duzelt]
   ```
   Alanı kendisi bulur (`--alan` ya da frontmatter `alan:` tespiti geçer). `--duzelt` yalnız anlamı değiştirmeyen iki
   düzeltmeyi yapar (benzer yabancı harf → Latin, 8,5 pt altı gövde → 9 pt); PDF'i yeniden üretmek gerekir.
4. Kullanıcıya ver: **alan ve güveni** (güven düşükse alanı sor), 8 boyut + puan tablosu, ilk 5 bulgu (öneriyle),
   alanın **elle kontrol listesi**, **karar**.
5. **Betik çalışmazsa puan uydurma:** çalışmadığını söyle, elle listeyi uygula, puan verme.

**Karar:** otomatik denetimde HATA varsa **yayınlanamaz** (çıkış 1). UYARI yayını durdurmaz, düzeltme listesine girer.
Doğruluk ve hedef uyumu her zaman elle maddedir; boşsa "otomatik denetimden geçti, elle maddeler bekliyor" de.

## Kesin kurallar

- **Sağlık en sıkı kısımdır.** Doz yazımı (5,0 mg; ,5 mg), hasta adı/protokol no ve TC kimlik numarası HATA'dır;
  bunları yumuşatma, kendiliğinden düzeltme: kullanıcıya göster. Betik dozun **klinik doğruluğunu denetlemez**; doz,
  endikasyon ve etkileşimin güncel kaynakla elle karşılaştırılması gerektiğini her sağlık raporunda söyle.
- Belgeye kaynağında olmayan bilgi ekleme; eksik kaynak, yıl ya da künyeyi uydurma, **sor**.
- Kaynağı doğrulanmamış eşik ya da öneriyi kural gibi sunma (satır uzunluğu, satır aralığı: doğrulanamadı).
- Gerçek hasta, öğrenci ya da kişisel veri içeren belgeyi dışarıdaki bir modele gönderme.

## Sınırlar

- Alan sözcük puanıyla tahmin edilir; karma belgede yanılabilir (`alan:` ya da `--alan` ile düzelt).
- Betik yazımı, yapıyı ve ölçülebilen kusuru görür; içeriğin doğruluğunu, kanun yorumunu ya da tarihsel bilgiyi
  kanıtlamaz.
- PDF yoksa ya da poppler (`pdftotext`, `pdfimages`) kurulu değilse okunaklılık ve verimlilik "ölçülmedi" olur.

## Önkoşul

`python3` 3.9+; yalnız standart kütüphane, ağ yok. PDF ölçümü için isteğe bağlı poppler.

## Dosyalar

`references/ogretim.md` (ölçek) · `references/ogretim-alanlari.json` (32 alan profili; yeni alan buraya) ·
`scripts/ogretim_denetim.py` (denetçi) · `scripts/test_ogretim_denetim.py` (61 test) · `eval.md` (son okuma) ·
`docs/kanitlar.md` (alıntılı kanıt ve açılamayan kaynaklar).
