<div align="center">

<img src="assets/sinac-logo.svg" width="120" alt="Sınaç logosu">

# Sınaç

### Ders notunu sınar: doğru mu, öğretir mi, yayınlanabilir mi?

![Lisans](https://img.shields.io/badge/lisans-kullanım%20hakkı-lightgrey) ![Biçim](https://img.shields.io/badge/bi%C3%A7im-Claude%20skill-8A63D2) ![Model](https://img.shields.io/badge/model-ba%C4%9F%C4%B1ms%C4%B1z-brightgreen) ![Dil](https://img.shields.io/badge/dil-T%C3%BCrk%C3%A7e%20%2B%20English-e30a17) ![Testler](https://img.shields.io/badge/testler-261%20test%20%2B%20211%20kar%C5%9F%C4%B1%20%C3%B6rnek-brightgreen) ![test](https://github.com/mesutbsdgn/sinac/actions/workflows/test.yml/badge.svg)

</div>

English: [README.en.md](README.en.md)

Adı *sınamak* fiilinden gelir, kardeşi Durulaç'la aynı ekle kurulur. Hem belgeyi sınar hem de ölçeğinin en önemli boyutunu, öğrencinin kendini sınamasını anlatır. Ders notunu, konu anlatımını, rehberi ve öğrenci PDF'ini kanıta dayalı bir ölçekle denetleyen Claude becerisidir (skill).

Belgenin **bilim dalını** ve **görsel/sözel biçimini** kendisi tanır; tıp notunu dil öğrenme ölçeğiyle, görsel bir anatomi atlasını düz metin ölçeğiyle değerlendirmez. Bulguları **satır numarası** ve kural kimliğiyle verir, üç durumlu bir karar söyler.

## İçindekiler

- [Karar](#karar)
- [Bir örnek](#bir-örnek)
- [Ölçek](#ölçek)
- [Üç katman](#üç-katman)
- [Sağlık kontrolleri](#sağlık-kontrolleri)
- [32 alan](#32-alan)
- [Öteki alanlardan örnekler](#öteki-alanlardan-örnekler)
- [Alan tespiti ve iki dil](#alan-tespiti-ve-iki-dil)
- [Kullanım](#kullanım)
- [Kurulum](#kurulum)
- [Nasıl sınandı](#nasıl-sınandı)
- [Kanıt](#kanıt)
- [Kardeş beceri: Durulaç](#kardeş-beceri-durulaç)
- [Sınırları](#sınırları)
- [Sürüm geçmişi](#sürüm-geçmişi)
- [Lisans](#lisans)

## Karar

Her denetim üç sonuçtan birini verir:

| Karar | Ne demek | Çıkış kodu |
|---|---|---|
| ⛔ **Yayına engel var** | Hasta güvenliğini ya da belgeyi bozan bir kusur bulundu (aşağıda ENGEL/HATA) | 1 |
| ◐ **Karar için denetim eksik** | Engel yok, ama içerik doğruluğu (`denetim:`) ya da hedef (`hedef:`) elle doğrulanmadı | 3 |
| ✓ **Tanımlı kapsamda uygun** | Engel yok, elle alanlar dolu. İçeriğin doğru olduğu anlamına gelmez | 0 |

Her bulgu üç düzeyden birini taşır:

| Düzey | Ne demek | Kararı etkiler mi |
|---|---|---|
| **ENGEL** | Hasta güvenliği | Evet, yayına engel |
| **HATA** | Yayını bozan biçim kusuru | Evet, yayına engel |
| **UYARI** | Düzeltme listesi | Hayır, liste olarak verilir |

## Bir örnek

Girdi, `farmakoloji-notu.md`:

```markdown
---
alan: tip
hedef: Dönem 3 öğrencisi pediatrik parasetamol dozunu hesaplar
denetim:
---

# Parasetamol: çocukta doz

## 1. Doz

Parasetamol oral 15 mg/kg, 6 saatte bir verilir.

Örnek: 20 kg çocuk için 20 kg × 15 mg/kg = 3000 mg.

Yetişkinde tablet 5,0 mg değil, 500 mg'dır; günde 4 kez, q.d. yazılmaz.

## 2. Kendini sına

1. 12 kg çocuğa tek doz kaç mg?
```

Komut (çıkış kodu 1):

```bash
python3 scripts/ogretim_denetim.py farmakoloji-notu.md --yil 2026
```

Çıktı (gerçek çıktıdır; yalnız uzun elle listesi kısaltılmıştır, kısaltılan satır aşağıda belirtilmiştir):

```text
⛔ farmakoloji-notu.md: YAYINA ENGEL VAR · 10/12 (6/8 boyut ölçüldü) · PDF ölçülmedi
  Alan: Tıp · kullanıcı seçimi, destek — · biçim: sozel · belge dili: tr · grup: saglik
  | Boyut | Puan |
  |---|---|
  | Doğruluk | 0 |
  | Hedefle uyum | 2 |
  | Seviye | 2 |
  | Ezber ve kavrama | 2 |
  | Okunaklılık | ölçülmedi |
  | Sıra ve akış | 2 |
  | Kendini sınama | 2 |
  | Verimlilik | ölçülmedi |
  ⛔ ENGEL · satır 13 · Doğruluk: Doz hesabı tutmuyor («20 kg × 15 mg/kg = 3000 mg» → doğrusu 300 mg) → Hesabı yeniden yap; sonuç nottaki sayıyla aynı olmalı  [doz_aritmetigi]
  ⛔ ENGEL · satır 15 · Doğruluk: Doz yazımında sondaki sıfır ya da baştaki sıfırsız ondalık (5,0 mg) → 5,0 mg → 5 mg; ,5 mg → 0,5 mg. Virgül görülmezse 10 kat doz hatası (ISMP)  [tip_doz_yazimi]
  ⚠ UYARI · satır 11 · Doğruluk: Çocukta kiloya göre doz var ama en yüksek doz yazılmamış → Hesaplanan doz genelde erişkin en yüksek dozunu geçmemeli; tavanı kaynağıyla yaz (bpac NZ)  [cocuk_azami_doz]
  ⚠ UYARI · satır 13 · Doğruluk: Kiloya göre doz zaman birimi belirsiz (15 mg/kg) → 'mg/kg/gün' mü 'mg/kg/doz' mu yaz; sıklığı ve en yüksek dozu ekle  [doz_kg_belirsiz]
  ☐ elle bekleyen: Doğruluk (frontmatter denetim: / hedef:)
  ℹ Betik doz YAZIMINI denetler, dozun klinik doğruluğunu denetlemez: güncel kaynakla karşılaştır
  … (sağlık elle listesi ve öğretim ☐ maddeleri; burada kısaltıldı, gerçek çıktıda tek tek yazılıdır)
```

Dört bulgu yakalandı. Doz hesabı (3000 mg yerine 300 mg olmalı) ve "5,0 mg" yazımı ENGEL sayıldığı için not yayına çıkamaz. Çocuk dozunda en yüksek dozun yazılmaması ile mg/kg'da zaman biriminin belirsizliği düzeltme listesine UYARI olarak girdi.

## Ölçek

8 boyut, her biri 0 (hata) · 1 (uyarı) · 2 (temiz). Ölçülemeyen boyut (PDF yoksa verimlilik, `hedef:` yoksa hedefle uyum…) puanlanmaz; çıktı "11/12 (6/8 boyut ölçüldü)" gibi yazar.

| Boyut | Örnek otomatik kontrol |
|---|---|
| Doğruluk | doz yazımı ve doz hesabı, hasta kimliği, TC no, yabancı alfabe karışması, TODO, mülga kanun, kaynaksız otorite |
| Hedefle uyum | elle (frontmatter `hedef:`) |
| Seviye | tanımsız kısaltma, dil bilgisi terimi yoğunluğu |
| Ezber ve kavrama | uzun cümle, okunuşsuz yabancı metin, yüzyıl yazımı, sayı–birim boşluğu |
| Okunaklılık | PDF'te yazı boyu (punto aralığı), boş sayfa, alt metinsiz görsel, harita öğeleri |
| Sıra ve akış | başlık numarası, sayfa göndermesi, çözülmüş örnek |
| Kendini sınama | kapalı kitap test bölümü, soru–cevap kapsamı |
| Verimlilik | sayfa tavanı, yarım sayfa oranı |

PDF verilirse yazı boyu ve sayfa düzeni ölçülür; PDF'in metni de hasta kimliği ve ilaç güvenliği için taranır (md'de olmayan bulgu "PDF'te" diye işaretlenir; diğer kontroller md üzerinde çalışır).

## Üç katman

| Katman | Ne yapar |
|---|---|
| 1. Ortak çekirdek (her alanda) | Yapı ve okunaklılık kontrolleri, **hasta kimliği** (ad, protokol no, tam doğum tarihi) ve **TC kimlik sağlamasına uyan sayı** (etiketli ya da kişi bağlamında ENGEL, bağlamsız UYARI) |
| 2. Risk taraması (alandan bağımsız) | Metinde ilaç ya da doz geçiyorsa sağlık güvenlik kontrolleri, belge tarih notu bile olsa çalışır |
| 3. Alan profili | 32 alanın kendi kontrolleri; karma belgede her bölümün alanı ayrıca eklenir |

## Sağlık kontrolleri

Yayını durduranlar:

| Kontrol | Düzey | Örnek |
|---|---|---|
| Doz yazımı | ENGEL | "5,0 mg", ".5 mg", ",5 mg" |
| Tutmayan doz hesabı | ENGEL | "20 kg × 5 mg/kg = 1000 mg" |
| Tutmayan birim dönüşümü | ENGEL | "Glukoz 90 mg/dL = 50 mmol/L" |
| Hasta adı, protokol numarası, tam doğum tarihi | ENGEL; vaka bağlamı yoksa (biyografi) yalnız UYARI | Açık etiketle küçük harfle yazılmış ad da, ISO biçimli doğum tarihi de yakalanır |

Doz yazımı kalın yazıda, kodda, tablo hücresinde (birim sütun başlığında olsa da), HTML'de, yaygın LaTeX biçimlerinde (`5{,}0`, `\SI{}{}`, `\mathrm{mg}`) ve tam genişlik rakamda da aranır; "5,0 mg/kg", "5,0-10 mg", "40.0 MG" da yakalanır. "1.000 mg" binlik sayılır; "PSA 4,0 ng/mL" gibi düzey ölçümü ve ilaç adı geçmeyen fen föyündeki "25,0 mL" sayılmaz.

Uyarı verenler:

| Kontrol | Düzey | Örnek |
|---|---|---|
| ISMP'nin karıştırılmaya açık kısaltmaları | UYARI | U, IU, cc, q.d., μg, SC, TIW, D/C, OD/OS/OU, ml, "1:1000" |
| Bitişik doz | UYARI | "10mg", "propranolol20 mg" |
| Zaman birimi yazılmamış mg/kg | UYARI | "15 mg/kg" |
| Çocuk dozunda en yüksek doz yok | UYARI | Kiloya göre doz var, tavan yazılmamış |
| "Gerektiğinde" talimatında doz aralığı yok | UYARI | — |
| Harfli gebelik kategorisi | UYARI | — |
| Kaynaksız referans aralığı | UYARI | — |
| Güncelliği doğrulanması gereken kılavuz, DSM-IV, yanlış yazılmış tür adı | UYARI | — |

Tıp ve yedi sağlık alt alanına ayrıca 11 maddelik ortak sağlık elle listesi eklenir (psikolojide yok).

## 32 alan

| Grup | Alanlar |
|---|---|
| Sağlık (en ayrıntılı) | tıp; diş hekimliği, hemşirelik ve ebelik, eczacılık, veteriner, beslenme, fizyoterapi, acil tıp; psikoloji |
| Sayısal ve fen | matematik, istatistik, fen, fizik, kimya, biyoloji, yer bilimleri, ziraat, mühendislik, bilgisayar, mimarlık |
| Sosyal ve beşerî | hukuk, iktisat ve işletme, tarih, coğrafya, sosyal bilgiler, ilahiyat, edebiyat, felsefe, sanat ve müzik, eğitim |
| Dil ve genel | yabancı dil (fr, en, de, es, it), genel |

Alan profilleri `references/ogretim-alanlari.json` dosyasındadır (32 alan profili).

## Öteki alanlardan örnekler

| Alan | Kontrol |
|---|---|
| Fen | SI birim yazımı; deney föyünde güvenlik notu |
| İstatistik | "p = 0,000" yazımı |
| Bilgisayar | Python 2 kullanımı |
| Hukuk | Yürürlükten kalkmış kanun: geçmiş olaya uygulanıyorsa sayılmaz (6101 sayılı Kanun m. 1); künyesiz mahkeme kararı |
| İlahiyat | Kaynaksız hadis |
| Edebiyat, tarih, felsefe, hukuk, ilahiyat, sanat | Kaynaksız alıntı |
| Coğrafya | Haritada lejant, ölçek, kuzey oku ya da kaynak eksikliği |

## Alan tespiti ve iki dil

v2.1.0'dan beri alan tespiti **dile duyarlıdır**: belge Türkçe, İngilizce ya da karışık olabilir.

- **Birim dil tahmini:** gövde birimlere ayrılır (paragraf, liste maddesi, tablo satırı). Her birimin dili (`tr`, `en`, `fr`)
  Türkçeye özgü harflerden ve durak sözcüklerden tahmin edilir; işaret yetersizse birim belgenin diline düşer. Çıktıda
  `belge_dili` ve `grup` yazılır.
- **Dile duyarlı eşleştirme:** Türkçe sözcük ve öbek listeleri yalnız Türkçe birimde (ek zinciriyle), İngilizce listeler
  yalnız İngilizce birimde (tam sözcük ve çoğul) aranır. Fransızca birimler alan puanına katılmaz; kod blokları yalnız
  bilgisayar alanına katkı verir.
- **Alan sözlüğü:** alan başına Türkçe ve İngilizce sözcük, öbek (ağırlık 2) ve kısaltma listesi. Toplamda Türkçe sözcük
  2355 (önce 718, hepsi Türkçe ve İngilizce karışıktı), Türkçe öbek 1499, İngilizce sözcük 2680, İngilizce öbek 1536,
  kısaltma 374.
- **Alan grupları:** sağlık, sayısal-fen, sosyal-beşerî, dil-genel. En iyi alan eşiğin altında kalsa da sağlık grubu
  eşiği geçiyorsa alan `tip` (tıp) olur; böylece sağlık kontrolleri ve elle listesi devreye girer.
- **Sayı biçimi dile bağlıdır:** İngilizce birimde "1,000 mg" binlik ayırıcıdır (doz yazımı ENGEL'i çıkmaz); Türkçede
  virgül ondalıktır.
- **Öteki yeni kurallar:** kolesterol (÷ 38,67) ve trigliserit (÷ 88,5) dönüşümü; tablo satırında ve düzyazıda doz hesabı
  (kilo × mg/kg = doz); düzyazıda lab dönüşümü. Öğretici yanlış örnek ("Yanlış yazım örneği: «5,0 mg» yerine…", "Do not
  write 5.0 mg") ENGEL değil UYARI verir. Yaş kalıbının yanındaki ad-soyad ("58 yaşındaki Ayşe Yıldırım") vaka bağlamında
  ENGEL, değilse UYARI.

Sözlüğün üretimi: Türkçe listeyi DeepSeek V4.1 Flash, İngilizce listeyi ve alan çekirdek sözcüklerini Gemini 4 Neon
yazdı; ikisi birbirinin listesini eleştirdi (416 Türkçe ve 283 İngilizce öğe çıkarıldı). Ardından yerel süzgeç: genel
akademik sözcük, üç ya da daha çok alanda geçen öğe, sözlükte geçen ya da birimle çakışan kısaltma elendi; sağlık alt
alanlarından alt alanı ayırt etmeyen genel klinik sözcükler çıkarıldı. Yayımlanmış alan listeleri (MAWL, CSAVL, EAWL;
hemşirelik, eczacılık, hukuk ve mühendislik listeleri) telif ve erişim nedeniyle kopyalanmadı; yalnız ilkeleri alındı.

### Ölçüm

Ölçüm `scripts/altin_olc.py` ile yapıldı; beklentiler betik çalıştırılmadan önce yazıldı. "Grup doğru" = grup doğru ve
alan "genel" değil.

| Küme | Yazan | Belge | Sürüm | Alan doğru | Grup doğru | Karar doğru | Kaçan ENGEL | Yanlış ENGEL |
|---|---|---|---|---|---|---|---|---|
| Geliştirme (`tests/altin`) | Sonnet 5.5 | 40 (20 tr, 20 en) | v2.0.1 | 14 | 22 | 38 | 2 | 1 |
| | | | v2.1.0 | 28 | 38 | 40 | 0 | 0 |
| Görülmemiş 1 (`tests/gorulmemis-gemini`) | Gemini 4 Neon | 20 (10/10) | v2.0.1 | 15 | — | 17 | — | — |
| | | | v2.1.0 ilk geçiş | 17 | 20 | 18 | 3 | 2 (1 belge) |
| | | | v2.1.0 son | 17 | 20 | 20 | 0 | 0 |
| Görülmemiş 2 (`tests/gorulmemis-deepseek`) | DeepSeek V4.1 Flash | 15 (7 tr, 8 en) | v2.0.1 | 4 (6'sı "genel") | — | 10 | — | — |
| | | | v2.1.0 ilk geçiş | 8 | 14 | 11 | 4 | 0 |
| | | | v2.1.0 son | 8 | 14 | 15 | 0 | 0 |

Geliştirme kümesinde alan ve grup doğruları dile göre: alan doğru v2.0.1'de 14 (tr 9, en 5), v2.1.0'da 28 (tr 15, en 13);
grup doğru v2.0.1'de 22 (tr 14, en 8), v2.1.0'da 38 (tr 19, en 19). Görülmemiş 1'de alan doğru v2.0.1'de 15 (tr 10, en 5).

**Dürüstlük notları:**

- Geliştirme kümesi geliştirme sırasında kullanıldı; asıl genelleme ölçüsü değildir.
- İki görülmemiş küme **ilk geçişte** kural açığı bulmak için kullanıldı, bulunan açıklar sonra düzeltildi. Bu yüzden
  "son" satırları artık görülmemiş sayılmaz, regresyon kümesidir. Asıl genelleme ölçüsü **"ilk geçiş"** satırlarıdır:
  Neon kümesinde karar 18/20, DeepSeek kümesinde 11/15; kaçan ENGEL sırasıyla 3 ve 4.
- Kalan alan hatalarının çoğu sağlık içi alt alan karışıklığıdır (hemşirelik, eczacılık ve tıp birbirine karışıyor; hepsi
  aynı sağlık kontrollerini aldığı için güvenlik açısından fark etmez) ve karma belgelerdir (sağlık + istatistik,
  fizik + kimya).
- DeepSeek kümesinde 15 belge var (dördüncü parti çıktı sınırında kesildi). DeepSeek frontmatter'a her belgede
  "denetime:" yazmıştı; ölçümden önce "denetim:" olarak düzeltildi.
- Üç küme de modellerce yazıldı; öğretmen ya da uzman etiketli gerçek altın küme hâlâ yok.

**Fransızca derlem** (368 gerçek ders notu, Türkçe açıklamalı Fransızca): `dil` olarak tanınan 340'tan 357'ye çıktı,
"genel" 19'dan 5'e indi. ENGEL artan belge yok; v2.0.1'deki tek yanlış ENGEL (kurgu karakterin doğum tarihi) gitti.
Hız: 1,9 MB gerçek belge yaklaşık 4,4 sn'den 3,2 sn'ye indi; kısa not yaklaşık 0,2 sn.

### v2.1.1 sınaması ve düzeltmesi (23 Kasım 2026)

v2.1.0 yayımlandıktan sonra yeni yazılmış belgelerle sınandı ve zayıf çıktı: taze bir ajanın yazdığı 22 belgede beklenen
22 ağır bulgunun 11'i kaçtı, 5 belgede yanlış ENGEL çıktı. v2.1.1 bu bulguları düzeltir. Düzeltme dört turda yapıldı;
her turun ardından **o ana kadar hiç görülmemiş** yeni bir küme ölçüldü. Aşağıdaki "ilk geçiş" sütunu, o kümenin kod
ona göre düzeltilmeden önceki sonucudur ve asıl genelleme ölçüsüdür.

| Küme (22'şer belge, 11 tr + 11 en) | Yazan | Beklenen ENGEL/HATA | v2.1.0: kaçan / yanlış ENGEL (belge) | Düzeltme sırasında ilk geçiş | v2.1.1 son |
|---|---|---|---|---|---|
| `tests/sinama-sonnet` (sınama raporunun asıl kümesi) | Sonnet 5.5 | 22 | 11 / 5 (5) | geliştirme kümesi | 0 / 0 |
| `tests/sinama-claude` (15 karşı örnek belgesi) | Claude | 11 | 4 / 4 (3) | geliştirme kümesi | 0 / 0 |
| `tests/sinama-neon1` | Gemini 4 Neon | 27 | 9 / 0 | 1. turdan sonra 2 / 2 (2) | 0 / 0 |
| `tests/sinama-sonnet2` | Sonnet 5.5 | 21 | 10 / 3 (3) | 2. turdan sonra 5 / 5 (4) | 0 / 0 |
| `tests/sinama-neon2` | Gemini 4 Neon | 25 | 9 / 2 (2) | 3. turdan sonra 1 / 2 (1) | 0 / 0 |

Dürüstlük notları:

- "v2.1.1 son" sütunundaki sıfırlar genelleme kanıtı değildir: her küme ilk geçişten sonra açık bulmak için kullanıldı ve
  artık regresyon kümesidir. Son görülmemiş kümede ilk geçişte 25 beklenen bulgunun 1'i kaçtı ve 1 belgede yanlış ENGEL
  çıktı; yeni bir belgede benzer oranda hata beklenmelidir.
- İkinci turda yeni doz kuralı doğru hesapları hata saydı (yanlış ENGEL 3 → 4 belge); üçüncü ve dördüncü turda düzeltildi.
- Dördüncü turdan sonra Claude'un yazdığı 12 yeni cümlenin 2'sinde açık çıktı (kısa metinde `6,000 units` binlik virgülü;
  "each 6-hour infusion" etiketi); ikisi de düzeltildi ve teste eklendi.
- Sınamayı Sınaç'ı geliştiren oturum yürüttü; tam bağımsız değildir. Belgeleri kodu görmeyen ajanlar yazdı, beklentiler
  betik çalışmadan önce SHA-256 ile kilitlendi.
- Fransızca derlem (368 gerçek ders notu): ENGEL'i artan belge 0, kararı değişen belge 0, alanı `dil`den çıkan belge 0.
- Hız: tek satırda ikinci dereceden büyüme giderildi (56 KB'lik tek satır 20 sn → 0,65 sn; 80 KB'lik boşluksuz sözcük
  27,8 sn → 0,49 sn). 370 KB – 0,9 MB arası dört yapay yığın girdisi hâlâ 2,4–5,6 sn sürer; 1,9 MB'lik gerçek ders notu
  yaklaşık 3,2 sn (değişmedi).

## Kullanım

```bash
python3 ~/.claude/skills/sinac/scripts/ogretim_denetim.py ders-notu.md   # alanı kendisi bulur
python3 scripts/ogretim_denetim.py not.md --pdf not.pdf --alan tip  # PDF ölçümü, alanı zorla
python3 scripts/ogretim_denetim.py not.md --json --yil 2026         # makine okur; değerlendirme yılı sabit
```

Claude'da doğal dille ya da adıyla: "Sınaç, bu farmakoloji notumu denetle", "Bu PDF öğretir mi?", "Hukuk ders notum güncel mi?"

**Yanlış alarmı susturmak** (gerekçe zorunlu; gerekçesiz susturma engeli kaldırmaz):

```markdown
<!-- sinac: yoksay tip_doz_yazimi — bu sayfa ISMP'nin yanlış yazım örneklerini anlatıyor -->
İlaç 5,0 mg <!-- sinac: yoksay — öğretici yanlış örnek; doğrusu altında -->
```

## Kurulum

```bash
git clone https://github.com/mesutbsdgn/sinac.git ~/.claude/skills/sinac
```

Python 3.9+, yalnız standart kütüphane, ağ yok. PDF ölçümü için isteğe bağlı poppler (`pdftotext`, `pdfimages`, `pdftoppm`).

## Nasıl sınandı

**Testler:** 261 test (211 karşı örnek ve 8 altın/sınama kümesi dahil), hepsi geçiyor.

| Dosya | Sayı | Kapsam |
|---|---|---|
| `test_ogretim_denetim.py` | 61 test | Denetim kuralları |
| `test_ozellikler.py` | 38 test | Gerçek üretilmiş PDF'lerle yazı boyu, vektör çizim, boş sayfa, PDF içeriği; `--duzelt`, kodlama, susturma, maskeleme, ReDoS |
| `test_f3.py` | 89 test | Birim dil tahmini, dile duyarlı eşleştirme, sözlük, alan grupları, yeni kurallar |
| `test_karsi_ornekler.py` | 1 test, 211 karşı örnek | Regresyon kümesi |
| `test_sinama.py` | 71 test | v2.1.1: ünite dozları, düzyazı ve tablo doz hesabı, lab eşleme, hasta kimliği, öğretici örnek, hız |
| `test_altin.py` | 1 test, 8 küme, 178 belge | Karar, kaçan ENGEL ve yanlış ENGEL kilitli |

GitHub Actions bu testleri Python 3.10 ve 3.13'te çalıştırır (Ubuntu 26.04 imajında 3.9 yok); Python 3.9.6'da yerelde sınandı.

İnceleme turları:

| Tur | Model | Ne sınadı | Sonuç |
|---|---|---|---|
| Bağımsız inceleme (22 Kasım 2026) | GPT-6.1 Sol, Qwen4 Max Preview | v1.0'ı yüksek eforla ve salt okunur inceledi | Raporlardaki karşı örneklerden 32'si betikte çalıştırıldı ve 32'si de gerçek çıktı; v2.0'da düzeltildi ve regresyon kümesine girdi (`scripts/tests/karsi_ornekler.json`) |
| Fable 5.2 testi (aynı gün, v2.0 adayı) | Fable 5.2 | 53 gerçekçi belge yazdı (28'i sağlık) | 35'inde kararı etkileyen kusur buldu, yayına hazırlık notu 3/10 verdi. Kritik ve yüksek bulguların hepsi yeniden üretildi, düzeltildi ve 55 kayıt olarak kümeye eklendi. Kümedeki 131 kaydın her birinde kaynak yazılı ("Sol 5", "Qwen K2", "Fable K3"); kaynağı "TC sağlama", "Hasta yaş", "Kiril" olan birkaç kenar örneğini Claude ekledi |
| Gemini 4 Argon incelemesi (aynı gün, v2.0 son adayı) | Gemini 4 Argon | Kodu okuyarak inceledi | 7,5/10 verdi. 25 karşı örneğinin 20'si betikte gerçek çıktı (3'ü çıkmadı, 2'si kısmen); hepsi düzeltildi ve 23 kayıt olarak kümeye eklendi (toplam 154) |
| Argon ikinci tur | Gemini 4 Argon | Karar, susturma, `--duzelt` bölümü | 6,5/10; 9 iddiadan 7'si gerçek çıktı ve düzeltildi |
| GPT-6.2 Astra sınaması (son aday) | GPT-6.2 Astra | Kopya üzerinde 44 gerçekçi belge, beklentiler önceden yazılı | 4/10; 18 belgede karar farklıydı, Claude hepsini yeniden üretti, hepsi gerçekti |
| Astra ikinci tur | GPT-6.2 Astra | 56 yeni belge (İngilizce sağlık notu, OCR, uzun tablo, LaTeX, hukuk, kod) | Yine 4/10; 23 belgede karar farklıydı, Claude 22'sini yeniden üretti, hepsi düzeltildi. Astra'nın iki turdaki 117 belgesinin hepsi beklenen kararı veriyor |

Turların ayrıntılı bulguları [sürüm geçmişinde](#sürüm-geçmişi) (v2.0.0 değişiklikleri) yazılıdır.

Öteki sınamalar:

- **Kasten bozma:** hasta adı, ondalık cümle bölme, Markdown temizliği ve boş sayfa eşiği kasten bozulunca testler kırmızıya döner.
- **PDF kalibrasyonu:** kelime kutusu/punto oranı yazı tipine göre ölçüldü: Helvetica 0,925 · Times 0,900 · Courier 0,786. Betik bu yüzden tek bir punto değil, bir punto aralığı tahmin eder.
- **Hız** (22 Kasım 2026, geliştirme makinesi, Python 3): 1,9 MB'lık gerçek Fransızca ders notu v2.0.1'de yaklaşık 4,4 sn, v2.1.0'da yaklaşık 3,2 sn.

## Kanıt

Üç quoteproof araştırması yapıldı: 23 başlık, 872 bulgu, 567'si kaynağında otomatik doğrulandı.

- **Elle açılan kaynaklar:** kurala giren kritik bilgiler ayrıca kaynağında açıldı. Bunlar arasında ISMP, FDA, NHMRC, PEP 8, python.org, Merck Veterinary Manual ve bpac NZ var. Mevzuat tarafında 6098 m. 647, 6100 m. 450, 6102 m. 1533 ve 6101 m. 1 de açıldı.
- **Açılamayanlar:** kaynağı açılamayan bilgi ENGEL ya da HATA kuralı yapılmadı.

Ayrıntılar: [`docs/kanitlar.md`](docs/kanitlar.md), ölçek ve karar modeli [`references/ogretim.md`](references/ogretim.md).

## Kardeş beceri: Durulaç

Sınaç dil sadeleştirmez; o iş kardeş becerisi [Durulaç](https://github.com/mesutbsdgn/turkce-ai-durulac)'ındır. İkisi birlikte kuruluysa önce Durulaç Türkçe açıklamayı sadeleştirir, sonra Sınaç ölçer.

## Sınırları

- Yazımı ve yapıyı denetler; dozun, tanının, kanun yorumunun ya da tarihsel bilginin doğru olduğunu kanıtlamaz.
- Tıbbi, eczacılık, veteriner ya da hukuki görüş değildir.
- Alan tespiti sözlük tabanlıdır; sağlık içi alt alanda (hemşirelik, eczacılık, tıp) ve karma belgede yanılabilir. `alan:` ya da `--alan` ile düzeltilir.
- İngilizce desteği alan tespitini ve sağlık güvenlik kurallarını kapsar; uyarı ve öneri mesajları Türkçedir.
- Doz hesabı ve lab dönüşümü kuralları yapıya bakar (kilo + kiloya göre doz + sonuç; aynı analitin iki birimli değeri) ama her cümle kalıbını yakalamaz: son görülmemiş kümede 25 bulgunun 1'i kaçtı, 1 belgede yanlış ENGEL çıktı. Derişim (mg/mL) ve bölme aritmetiği denetlenmez. Bulgu yokluğu hesabın doğru olduğunu göstermez.
- **Açık iş:** regresyon ve altın kümeleri modellerin yazdığı belgelerden oluşuyor; bağımsız öğretmen ve uzmanların etiketlediği gerçek ders notlarından bir altın küme henüz yok.
- **Ölçme geçerliği sınanmadı:** 8 boyutun öğretim kalitesini ayırt ettiği öğretmen değerlendirmesi ve öğrenci sonuçlarıyla sınanmadı; toplam puan yalnız göstergedir.

## Sürüm geçmişi

| Sürüm | Tarih | Değişiklik |
|---|---|---|
| v1.0.0 | 22 Kas 2026 | İlk yayın. Durulaç'ın `+ogretim` kipinden (v1.7–1.9) ayrı beceri olarak çıkarıldı, Sınaç adını aldı |
| v2.1.0 | 22 Kas 2026 | Dile duyarlı alan tespiti (Türkçe ve İngilizce), alan grupları, yeni sağlık kuralları. Değişiklikler aşağıda |
| v2.1.1 | 23 Kas 2026 | Sınama bulgularının düzeltmesi: ünite/kg dozları, düzyazıda ve tabloda doz hesabı, lab dönüşümü eşlemesi, hasta kimliği varyantları, tarihî kişi ve öğretici örnek yanlış ENGEL'leri, hız. Ölçüm: [v2.1.1 sınaması](#v211-sınaması-ve-düzeltmesi-23-kasım-2026) |
| v2.0.1 | 22 Kas 2026 | CI: Python 3.10 ve 3.13 (GitHub Ubuntu 26.04 imajında 3.9 yok); kod değişmedi |
| v2.0.0 | 22 Kas 2026 | GPT-6.1 Sol, Qwen4 Max, Fable 5.2, Gemini 4 Argon (iki tur) ve GPT-6.2 Astra (iki tur) incelemeleri sonrası. Değişiklikler aşağıda |

<details>
<summary>v2.1.0'daki değişiklikler</summary>

- **Alan tespiti:** birim dil tahmini (tr, en, fr; yetersizse belge diline düşer); Türkçe listeler yalnız Türkçe, İngilizce
  listeler yalnız İngilizce birimde; Fransızca birimler alan puanına katılmaz; kod blokları yalnız bilgisayara katkı verir.
  Çıktıda `belge_dili` ve `grup`.
- **Sözlük:** alan başına `sozcukler`, `obekler`, `sozcukler_en`, `obekler_en`, `kisaltmalar`; model üretimi, çapraz
  inceleme ve yerel süzgeçle. Toplam: Türkçe sözcük 2355, Türkçe öbek 1499, İngilizce sözcük 2680, İngilizce öbek 1536,
  kısaltma 374.
- **Alan grupları:** sağlık, sayısal-fen, sosyal-beşerî, dil-genel; eşik altında kalan sağlık belgesi `tıp` olur.
- **Yeni kurallar:**
  - İngilizce birimde "1,000 mg" binlik ayırıcı;
  - kolesterol ve trigliserit dönüşümü (PubChem: kolesterol C27H46O 386,7 g/mol, CID 5997; triolein 885,4 g/mol, CID 5497163);
  - tablo satırında ve düzyazıda doz hesabı; düzyazıda lab dönüşümü;
  - öğretici yanlış örnek ENGEL değil UYARI;
  - yaş kalıbının yanındaki ad-soyad vaka bağlamında ENGEL.
- **Ölçüm ve test:** 190 test (211 karşı örnek, 3 altın küme, 75 belge); iki görülmemiş küme önce açık bulmak için
  kullanıldı, sonra regresyon kümesi oldu. Fransızca derlemde `dil` tanıma 340'tan 357'ye çıktı.

</details>

<details>
<summary>v2.0.0'daki değişiklikler</summary>

- **Karar ve düzeyler:** üç durumlu karar; ENGEL / HATA / UYARI düzeyleri.
- **Kontrol katmanları:** risk taraması alandan bağımsız çalışıyor; hasta kimliği ortak çekirdeğe taşındı; bölüm
  alanları eklendi.
- **Çıktı:** her bulgu satır numarası ve kural kimliği taşıyor; gerekçeli susturma var.
- **Yeni ve düzeltilen kontroller:**
  - doz yazımı kalın yazı, kod, tablo, LaTeX ve mg/kg içinde de aranıyor;
  - doz ve birim dönüşümü aritmetiği denetleniyor;
  - doz–birim boşluğu, çocuk dozunda azami doz ve "gerektiğinde" talimatı eklendi.
- **Ölçüm ve düzeltme:**
  - PDF yazı boyu punto aralığı olarak ölçülüyor ve vektör çizimli sayfa boş sayılmıyor;
  - `--duzelt` yedek alıyor ve formüle dokunmuyor.
- **Yanlış alarmlar giderildi:** mülga kanun artık UYARI; ayrıca p = 0,05, U/L, EKG ve dil alıştırmasındaki örnek
  e-posta yanlış alarm vermiyor.
- **Fable 5.2 sonrası:** satır tabanlı metin hazırlığı (".5 mg", satır numarası, satır susturması), tablo başlığı birimi,
  binlik ayırıcı, düzey/ilaç bağlamı, sıkı öğretici ve kurmaca işareti, sıkı frontmatter, bütün TC adayları, PDF içeriği,
  olumsuz elle değer reddi, bütün bulgularda maskeleme, ReDoS ve karesel süre düzeltmeleri (2 MB belge ~12 sn).
- **Argon sonrası:** "Hasta: Göğüs Ağrısı" ve tablo başlığı hasta adı sayılmıyor; aynı satırda iki derişim ve "100 mg için
  50 mL SF" seyreltmesi doz hatası sayılmıyor; besin tablosu ve idrar çıkışı doz sayılmıyor. ".5-1 mg", "5,0 ve 10 mg",
  "1,0-2 g", satırın başındaki ilaç adıyla "5,0 mL", 2000 sonrası iki haneli doğum yılı, ters yönlü lab dönüşümü
  (mmol/L = mg/dL) yakalanıyor. Bitişik "2g", "10U" ilaç bağlamında uyarı; tartımda "0,50 mg" uyarı değil. Kısaltma taraması her satıra bakıyor; ikinci kısaltma listesi risk taramasında. `dil: tr-fr`
  kabul ediliyor; uzun metinde alan eşiği uzunlukla artıyor (Fransızca dergi artık "bilgisayar" sayılmıyor).
- **Hız:** uzun rakam dizisinde karesel süren sayı desenleri (SAYI, mg/kg, OCR, veri) yalnız sayının başından eşleşiyor; doz
  taraması ondalıksız satırları atlıyor. 1,3 MB gerçek belge 17–20 sn; 100 000 haneli patolojik girdiler < 1 sn (önce > 2 dk).
- **Argon ikinci tur** (karar, susturma, `--duzelt` bölümü; 6,5/10): 9 iddiadan 7'si gerçek çıktı, düzeltildi: CRLF dosyada
  `--duzelt` kod bloğunu bozuyordu; satır içi koddaki `$` dışarıdaki `$` ile formül sayılıp kod bozuluyordu; "--- 2026",
  "???", "2026 (bekliyor)" geçerli denetim sayılıyordu; susturmada gerekçedeki "1–3" ayraç sanılıyordu; kod örneğindeki
  susturma yorumu gerçekten susturuyordu; aynı örnek ikinci paragrafta ilk satırın susturmasıyla susuyordu; `hedef: yok`
  geçerli `sinav:`'ı yutuyordu. Ayrıca susturulan ENGEL/HATA boyuta tam puan getirmiyor, `--dil EN` kabul, `--duzelt`ten
  sonra eski PDF ölçülmüyor, pdftotext UTF-8 okunuyor.
- **GPT-6.2 Astra sınaması** (son aday; kopya üzerinde, 44 gerçekçi belge, beklentiler önceden yazılı): 4/10. 18 belgede
  karar farklıydı; Claude hepsini yeniden üretti, hepsi gerçekti. Başlıcaları: "0.125 mg = 125 mcg" doğrusu ENGEL,
  bin kat hatalısı temiz çıkıyordu (nokta binlik sanılıyordu); "12 kg × 25 mcg/kg = 3 mg" (birim farklı) ve "8 mg/mL
  … 24 mg = 30 mL" (örtük 1 mL) hesabı denetlenmiyordu; md'deki öğretici UYARI PDF'teki ENGEL'i siliyordu; satıra
  taşan "4,0 / mg", dış borusuz tablo, HTML `<th>Doz (mg)</th>`, `\SI{6,0}{\milli\gram}` kaçıyordu; "kullanmayın"
  başka bir nesneye ait olsa da dozu öğretici sayıyordu; boş satırlar paragraf ayırmadığı için kurmaca işareti bütün
  belgeye yayılıyordu; ISO doğum tarihi, 1930 öncesi doğumlu hasta, küçük harfli ad kaçıyordu; biyografideki doğum
  tarihi ENGEL alıyordu; "incelenmedi" ve "31.02.2025" geçerli denetim, CRLF frontmatter geçersiz sayılıyordu; dört
  ters tırnaklı iç içe çit, çift ters tırnaklı kod ve `equation` ortamı `--duzelt`te korunmuyordu. Claude ayrıca `hedef: A1`
  gibi kısa ama geçerli hedeflerin reddedildiğini buldu. Düzeltmeden sonra Astra'nın 61 beklentisinin hepsi tutuyor.
- **Astra ikinci tur** (56 yeni belge; İngilizce sağlık notu, OCR, uzun tablo, LaTeX, hukuk, kod): yine 4/10, 23 belgede
  karar farklıydı. Claude 22'sini yeniden üretti, hepsi düzeltildi: "1.125" gibi iki türlü okunabilen sayı artık tek yoruma
  zorlanmıyor (ikisi de tutmazsa ENGEL, yalnız biri tutarsa UYARI; belge "decimal point" diyorsa ondalık); kütle sonucu
  hacim yazılan hesap ("… mg/kg = 28 mL") ve bir üst satırdaki derişimle hesap; İngilizce analit adları (glucose…);
  OCR'da "6.0 / MG"; aralık hücresi "2,0–4"; `\qty{6{,}0}{…}`; "idrar çıkışı … ilaç dozu 8,0 mL"; İngilizce doğum
  tarihi ("09 Sep 2016"); "Patient name: not recorded" artık ad değil; kimyada "verilen ölçüm" doz değil; alıntı
  içindeki, kapanmamış çit ve her LaTeX ortamı `--duzelt`te korunuyor; her TODO/FIXME ayrı; İngilizce olumsuz denetim
  ("not reviewed", "not specified") ve iki haneli geçersiz tarih reddediliyor; md satır susturması PDF'teki ENGEL'i
  silmiyor; "Vaka: Ad Soyad" yakalanıyor; "hastane" vaka bağlamı sayılmıyor; satır içi koddaki susturma yorumu sayılmıyor.
  Sonuçta Astra'nın iki turdaki 117 belgesinin hepsi beklenen kararı veriyor.
- **Test ve yayın:** 211 karşı örnek ve GitHub Actions eklendi.

</details>

## Lisans

Kullanım hakkı lisansı: [LICENSE](LICENSE). Telif © 2026 mesutbsdgn.
