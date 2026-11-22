# F3 — Dile duyarlı alan tespiti (tasarım, 22 Kasım 2026)

Tasarım: Claude (Opus 5.5). Sözlük üretimi: DeepSeek V4.1 Flash 1017 (Türkçe), Gemini 4 Neon (İngilizce), çapraz
inceleme birbirinin listesine. Uygulama: Sonnet 5.5. Doğrulama: Claude.

## Sorun (ölçüm, `scripts/altin_olc.py`, 40 belge)

| Dil | Doğru karar | Alan tam doğru | Alan grubu doğru | "genel"e düşen |
|---|---|---|---|---|
| tr | 20/20 | 9/20 | 14/20 | 6 |
| en | 18/20 | 5/20 | 8/20 | 12 |

Nedenler: (1) alan başına 13–71 anahtar, çoğu Türkçe; İngilizce karşılık çok az. (2) Kısa belgede (15–60 satır)
eşik 4'e ulaşılamıyor. (3) Türkçe ek zinciri her dile uygulanıyor ("classe" → "class" + e). (4) Tek sözcük
yanıltıcı; alanı asıl öbek ("vital signs", "devir teslim", "ayırıcı tanı") gösteriyor. (5) Alan zayıfsa grup bilgisi
de atılıyor; sağlık belgesi "genel" olunca sağlık elle listesi eklenmiyor.

## Araştırmadan alınanlar (`arastirma/2026-11-22-alan-sozlukleri`, doğrulanmış notlar)

- Yayımlanmış alan listeleri (MAWL 623 sözcük ailesi, CSAVL 904 + 702, EAWL 887, Nursing AWL, PAWL, Law Word List,
  mühendislik listeleri) alan derleminden **sıklık + yayılım** ölçütüyle ve **genel yüksek sıklıklı sözcükler
  dışlanarak** çıkarılmış. → Bizde: genel sözcük ayıklama süzgeci (arka plan derlemi) ve alanlar arası paylaşılan
  sözcüğün ağırlığının bölünmesi (zaten var).
- Sözcük öbekleri (lexical bundles) türe/disipline özgü, "beklenenden sık" çok sözcüklü kalıplar. → Öbek listeleri,
  tek sözcükten yüksek ağırlık.
- Kısa metinde dil tanıma doğruluğu uzunlukla düşer; kısa parçada "güvenilmez" demek yanlış etiketten iyidir.
  → Birim dil tahmini: yeterli işaret yoksa belge diline düş.
- Disiplin sınırları tartışmalı; etiket olasılıksal sunulmalı. → `grup` çıktısı ve destek düzeyi.

Listeler telif ve erişim nedeniyle kopyalanmadı; aynı ilkelerle model üretimi + çapraz inceleme + yerel süzgeç.

## Tasarım

1. **Profil şeması** (`references/ogretim-alanlari.json`), alan başına:
   - `sozcukler` — Türkçe tek sözcük/kök (var olan; genişletilir). Türkçe birimlerde ek zinciriyle eşleşir.
   - `obekler` — Türkçe çok sözcüklü öbek; son sözcük ek alabilir. Ağırlık 2.
   - `sozcukler_en` — İngilizce terim; tam sözcük + çoğul (-s, -es, -ies) ve listede yazılı türevler. Ağırlık 1.
   - `obekler_en` — İngilizce öbek; son sözcük çoğul alabilir. Ağırlık 2.
   - Var olan `sozcukler` içindeki İngilizce öğeler `sozcukler_en`/`obekler_en`'e taşınır.
2. **Birim dil tahmini:** gövde birimlere ayrılır (boş satırla ayrılan paragraf; liste ve tablo satırları tek tek).
   Her birim: Türkçeye özgü harf (ı, ğ, ş, İ) ve Türkçe/İngilizce/Fransızca durak sözcük sayımı → `tr|en|fr|?`.
   İşaret yetersizse (< 3 durak sözcük ve özgü harf yok) belgenin çoğunluk diline düşer. Belge dili = birimlerin
   sözcük ağırlıklı çoğunluğu; çıktıya `belge_dili` yazılır.
3. **Eşleştirme:** `tr` birimde yalnız Türkçe listeler, `en` birimde yalnız İngilizce listeler; `fr` (ve öteki)
   birimler alan puanına katılmaz, yalnız `dil` alanı işaretine katkı verir. Kod blokları ve satır içi kod yalnız
   `bilgisayar` alanına katkı verir (anahtar sözcük `def`, `return`, `import` vb.).
4. **Puan:** sözcük başına min(n, tavan) × paylaşım ağırlığı × (öbekse 2); başlıklar çift sayılır (var olan).
   Eşik: `ALAN_EN_AZ` korunur; birim düzeyindeki sayım kısa belgede yeterli puanı zaten sağlamalı.
5. **Grup:** `_alan_gruplari` = sağlık (tip ve alt alanları + psikoloji), sayısal-fen, sosyal-beşerî, dil-genel.
   En iyi alan eşiğin altındaysa ama grup toplamı eşiği geçiyorsa: sağlık grubunda `tip` seçilir (güvenlik
   kontrolleri ve sağlık elle listesi gelsin; destek "zayıf"), öteki gruplarda `genel` kalır ama `grup` yazılır.
   Çıktıya her zaman `grup` eklenir.
6. **Alt alan:** var olan üst/alt mantığı korunur; zengin listeler alt alanı ayırır.
7. **Sayı biçimi dile duyarlı:** `en` birimde `1,000` binlik ayırıcıdır (doz yazımı ENGEL'i yok); `tr` birimde
   virgül ondalıktır (değişmez).
8. **Lab dönüşümü:** kolesterol (mg/dL × 0,02586 = mmol/L) ve trigliserit (× 0,01129) eklenir; düzey, katsayının
   birincil kaynakta açılmasına bağlıdır.
9. **Tablo doz hesabı:** başlığında kilo (kg), kiloya göre doz (mg/kg) ve doz (mg) sütunları olan tabloda her satırın
   çarpımı denetlenir.

## Doğrulama planı

- 100 test + 211 karşı örnek + yeni testler (sabotajla kırmızıya döndüğü gösterilir).
- Altın küme (40, geliştirme kümesi): hedef her dilde alan grubu ≥ 18/20, karar 40/40, yanlış ENGEL 0.
- **Görülmemiş küme:** Gemini 4 Neon'un yazdığı 20 yeni belge (geliştirmede kullanılmaz); asıl rapor bu kümedir.
- Fransızca derlem (368 md): öncesi `dil` 340, `genel` 19; sonrası `dil` oranı düşmemeli, yeni ENGEL çıkmamalı.

## Sonuç (22 Kasım 2026)

v2.1.0 olarak uygulandı. Ölçüm `scripts/altin_olc.py` ile yapıldı; beklentiler betik çalıştırılmadan önce yazıldı.
"Grup doğru" = sağlık/sayısal-fen/sosyal-beşerî/dil-genel grubu doğru ve alan "genel" değil. Testler: 190 (61 + 38 + 89
+ karşı örnek 1 + altın 1; 211 karşı örnek, 3 altın küme, 75 belge), hepsi geçiyor.

| Küme | Yazan | Belge | Sürüm | Alan doğru | Grup doğru | Karar doğru | Kaçan ENGEL | Yanlış ENGEL |
|---|---|---|---|---|---|---|---|---|
| Geliştirme (`tests/altin`) | Sonnet 5.5 | 40 (20 tr, 20 en) | v2.0.1 | 14 (tr 9, en 5) | 22 (tr 14, en 8) | 38 | 2 | 1 |
| | | | v2.1.0 | 28 (tr 15, en 13) | 38 (tr 19, en 19) | 40 | 0 | 0 |
| Görülmemiş 1 (`tests/gorulmemis-gemini`) | Gemini 4 Neon | 20 (10/10) | v2.0.1 | 15 (tr 10, en 5) | — | 17 | — | — |
| | | | v2.1.0 ilk geçiş (kural düzeltmesinden önce) | 17 | 20 | 18 | 3 | 2 (1 belge) |
| | | | v2.1.0 son | 17 | 20 | 20 | 0 | 0 |
| Görülmemiş 2 (`tests/gorulmemis-deepseek`) | DeepSeek V4.1 Flash | 15 (7 tr, 8 en) | v2.0.1 | 4 (6'sı "genel") | — | 10 | — | — |
| | | | v2.1.0 ilk geçiş | 8 | 14 | 11 | 4 | 0 |
| | | | v2.1.0 son | 8 | 14 | 15 | 0 | 0 |

Dürüstlük notları:

- İki görülmemiş küme ilk geçişte kural açığı bulmak için kullanıldı, sonra düzeltildi; "son" satırları artık görülmemiş
  sayılmaz, regresyon kümesidir. Asıl genelleme ölçüsü "ilk geçiş" satırlarıdır.
- Kalan alan hatalarının çoğu sağlık içi alt alan karışıklığıdır (hemşirelik, eczacılık ve tıp; hepsi aynı sağlık
  kontrollerini alır) ve karma belgelerdir (sağlık + istatistik, fizik + kimya).
- DeepSeek kümesinde 15 belge var (dördüncü parti çıktı sınırında kesildi). DeepSeek tüm belgelerde frontmatter'a
  "denetime:" yazmıştı; ölçümden önce "denetim:" olarak düzeltildi.
- Üç küme de modellerce yazıldı; öğretmen ya da uzman etiketli gerçek altın küme hâlâ yok.
- Fransızca derlem (368 gerçek ders notu): `dil` olarak tanınan 340 → 357, "genel" 19 → 5; ENGEL artan belge 0; v2.0.1'deki
  tek yanlış ENGEL (kurgu karakterin doğum tarihi) gitti. Hız: 1,9 MB gerçek belge ~4,4 sn → ~3,2 sn; kısa not ~0,2 sn.

Sözlük (toplam): Türkçe sözcük 2355 (önce 718, hepsi Türkçe ve İngilizce karışık), Türkçe öbek 1499, İngilizce sözcük
2680, İngilizce öbek 1536, kısaltma 374. Çapraz incelemede 416 + 283 öğe çıkarıldı.
