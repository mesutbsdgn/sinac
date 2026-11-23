---
name: sinac
description: "Sınaç — ders notu, konu anlatımı, rehber, çalışma kâğıdı, ezber/kelime listesi ve öğrenci PDF'ini (Türkçe ya da İngilizce) kanıta dayalı 8 boyutlu ölçekle denetler (doğruluk, hedef uyumu, seviye, ezber ve kavrama, okunaklılık, sıra ve akış, kendini sınama, verimlilik) ve üç durumlu karar verir (yayına engel var / denetim eksik / uygun), bulguları satır numarasıyla gösterir. Belgenin dilini, bilim dalını (32 alan: tıp ve 7 sağlık dalı, psikoloji, matematik, fen, mühendislik, bilgisayar, hukuk, iktisat, tarih, ilahiyat, edebiyat, yabancı dil…) ve biçimini kendisi tanır. Sağlıkta doz yazımı (5,0 mg), doz hesabı, ISMP kısaltmaları, hasta kimliği ve TC no alandan bağımsız denetlenir. Audits Turkish or English study notes and teaching PDFs: use when asked to check, audit or score lecture notes or a vocabulary list; 'ders notumu denetle', 'bu PDF öğretir mi', 'Sınaç'."
version: "2.1.1"
metadata:
  author: mesutbsdgn
  tags: [education, teaching-materials, medical-education, quality-check, turkish]
---

# Sınaç

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
   Yalnız PDF geldiyse `pdftotext -layout BELGE.pdf BELGE.md` ile çıkar ve `--pdf BELGE.pdf` ile birlikte ver; tabloların
   çıkarımda bozulabileceğini kullanıcıya söyle. Önce `--alan` vermeden çalıştır ve `tespit`'e bak; yalnız ana alan
   yanlışsa `--alan` ver (verince bölüm alanları kapanır; karma belgede — tıp + istatistik gibi — bu kontroller kaybolur).
   PDF'ten çıkarılan md'de satır numarası kullanıcının elindeki belgeye değil çıkarıma aittir: bulguyu cümlesiyle göster.
   Uzun yabancı dilli metinde (dergi, öykü) `destek: zayıf` ve `genel` olağandır; öğretim notu değilse puanı yorumlama.
2. Kullanıcı dilin sadeleşmesini de istediyse Durulaç'ın Temizle kipini **yalnız Türkçe açıklamaya** uygula; yabancı
   örnek cümle, okunuş, formül, doz, diş/kanun numarası, tablo aynen kalır. İstenmediyse metne dokunma.
3. Denetle:
   ```bash
   python3 <beceri kökü>/scripts/ogretim_denetim.py BELGE.md [--pdf BELGE.pdf] [--alan AD] [--dil fr] [--yil YYYY] --json [--duzelt]
   ```
   Alanı kendisi bulur; ilaç/doz örüntüsü varsa sağlık güvenlik kontrolleri **alandan bağımsız** çalışır; karma
   belgede bölüm alanlarını da ekler. `--duzelt` önce `.bak` yedeği alır, kod/formül/frontmatter'a dokunmaz.
4. Kullanıcıya ver: **karar**, alan ve destek (zayıfsa alanı sor), "k/8 boyut ölçüldü" ve puan tablosu, **bütün ENGEL
   ve HATA bulguları satır numarası ve kural kimliğiyle**, ilk 5 uyarı, elle bekleyen maddeler, alanın elle listesi.
5. **Betik çalışmazsa puan uydurma:** çalışmadığını söyle, elle listeyi uygula, puan verme.

**Çıktıdaki `belge_dili` ve `grup`:** `belge_dili` (tr, en, fr) birim dil tahminlerinin çoğunluğudur; `grup` alanın
grubudur (saglik, sayisal_fen, sosyal_beseri, dil_genel). Alan eşik altındaysa ama sağlık grubu eşiği geçiyorsa alan `tip`
olur (sağlık kontrolleri gelir, destek zayıf). Sağlık içi alt alan (hemşirelik, eczacılık, tıp) ve karma belgede alan
yanılabilir; kullanıcıya söyle, `alan:` ile düzelt. İngilizce belgede uyarı mesajları yine Türkçedir.

**Karar (üç durum):**
- **yayına engel var** (çıkış 1): en az bir ENGEL (hasta güvenliği: doz yazımı, doz/dönüşüm aritmetiği, hasta kimliği,
  TC no; PDF metninde bulunanlar da) ya da HATA (biçim: Kiril karışması, uzun Latin sözcükte Yunan harfi, TODO, çok
  küçük yazı, boş sayfa, sayfa tavanı).
- Karar için daima JSON'daki `karar` alanına bak; çıkış kodu 2 kullanım/okuma hatasıdır.
- **karar için denetim eksik** (çıkış 3): engel yok ama `denetim:` (gerçek bir tarih içermeli; "incelenmedi", "bekliyor",
  "---" reddedilir) ya da `hedef:` boş/olumsuz
  ("yok", "henüz yapılmadı" reddedilir), ya da belge düzeyinde bir ENGEL/HATA susturulmuş.
- **tanımlı kapsamda uygun** (çıkış 0): engel yok, elle alanlar dolu. Bu, içeriğin doğru olduğu anlamına gelmez.

**Yanlış alarm:** kullanıcı bir bulgunun yanlış olduğunu söylerse gerekçeli susturma öner:
`<!-- sinac: yoksay KURAL — gerekçe -->` (belge) ya da aynı satırda `<!-- sinac: yoksay — gerekçe -->`. Gerekçesiz ya da
10 karakterden kısa gerekçeli susturma ENGEL/HATA'yı kaldırmaz; `KURAL` yazılırsa susturma bütün belgede geçerlidir, satır
susturması için kural adı yazma. Kod çiti (```) içindeki susturma yorumu sayılmaz. Sağlık ENGEL'ini susturmayı kendin önerme; kullanıcı açıkça "öğretici yanlış örnek"
derse öner.

## Kesin kurallar

- **Sağlık en sıkı kısımdır.** ENGEL'leri yumuşatma, kendiliğinden düzeltme: satırıyla kullanıcıya göster. Betik dozun
  **klinik doğruluğunu denetlemez**; doz, endikasyon ve etkileşimin güncel kaynakla elle karşılaştırılması gerektiğini
  her sağlık raporunda söyle. Kimlik bulgusunda maskeli örneği kullan, adı açık yazma.
- Belgeye kaynağında olmayan bilgi ekleme; eksik kaynak, yıl ya da künyeyi uydurma, **sor**.
- Kaynağı doğrulanmamış eşik ya da öneriyi kural gibi sunma (satır uzunluğu, satır aralığı: doğrulanamadı).
- Gerçek hasta, öğrenci ya da kişisel veri içeren belgeyi dışarıdaki bir modele gönderme. Elle doğruluk denetimini
  ("bağımsız modele okut") böyle belgede yalnız kimlik çıkarıldıktan sonra ya da yerel/kurum onaylı modelle yap.

## Sınırlar

- Alan sözcük puanıyla tahmin edilir ("destek" kalibre edilmiş olasılık değildir); karma belgede `alan:` ile düzelt.
- Betik yazımı, yapıyı ve ölçülebilen kusuru görür; içeriğin doğruluğunu, kanun yorumunu ya da tarihsel bilgiyi
  kanıtlamaz. Test bölümünün varlığı, soruların öğrenme hedefini gerçekten sınadığını kanıtlamaz.
- PDF ölçümü kelime kutusundan punto **aralığı** tahmin eder (Helvetica/Times/Courier'e kalibre). PDF yoksa, metin
  katmanı yoksa ya da poppler kurulu değilse okunaklılık ve verimlilik "ölçülmedi" olur.
- 8 boyutun öğretim kalitesini ayırt ettiği öğretmen ve öğrenci verisiyle sınanmadı; toplam puan yalnız göstergedir.

## Önkoşul

`python3` 3.9+; yalnız standart kütüphane, ağ yok. PDF ölçümü için isteğe bağlı poppler (`pdftotext`, `pdfimages`,
`pdftoppm`).

## Dosyalar

`references/ogretim.md` (ölçek, karar modeli, alan tabloları) · `references/ogretim-alanlari.json` (32 profil) ·
`scripts/ogretim_denetim.py` · testler: `scripts/test_ogretim_denetim.py`, `scripts/test_ozellikler.py` (gerçek PDF
dahil), `scripts/test_karsi_ornekler.py` + `scripts/tests/karsi_ornekler.json` (GPT-6.1 Sol, Qwen4 Max, Fable 5.2 ve
Gemini 4 Argon ve GPT-6.2 Astra incelemelerinden 211 karşı örnek) · `scripts/test_f3.py` (dil ve alan tespiti), `scripts/test_altin.py` (3 altın küme, 75 belge) · `eval.md` (son okuma) · `docs/kanitlar.md` (kanıt, açılamayan kaynaklar, inceleme özeti).

## English summary

Sınaç audits Turkish or English study notes, lecture notes, guides and teaching PDFs against an 8-dimension,
evidence-based scale and returns one of three verdicts (blocked / audit incomplete / fit within scope), with line numbers
and rule IDs. It guesses the language per unit (paragraph, list item, table row), detects the field (32 fields, 4 groups)
and format, and always runs patient-safety checks (dose writing such as "5.0 mg", dose and unit-conversion arithmetic,
ISMP abbreviations, patient identity) when drugs or doses appear. In English units "1,000 mg" is a thousands separator.
Output fields `belge_dili` (document language) and `grup` (field group) are reported. Warning and suggestion messages
are in Turkish. It checks writing and structure, not clinical or factual correctness; field detection is lexicon-based and
can be wrong for health sub-fields and mixed documents (override with `alan:` or `--alan`). Full documentation:
`README.en.md`.
