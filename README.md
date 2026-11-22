<div align="center">

# Sınaç

### Ders notunu sınar: doğru mu, öğretir mi, yayınlanabilir mi?

![test](https://github.com/mesutbsdgn/sinac/actions/workflows/test.yml/badge.svg)

</div>

Adı *sınamak* fiilinden gelir, kardeşi Durulaç'la aynı ekle kurulur. Hem belgeyi sınar hem de ölçeğinin en önemli
boyutunu, öğrencinin kendini sınamasını anlatır.

Ders notunu, konu anlatımını, rehberi ve öğrenci PDF'ini kanıta dayalı bir ölçekle denetleyen Claude becerisi (skill).
PDF verilirse yazı boyu ve sayfa düzeni ölçülür; PDF'in metni de hasta kimliği ve ilaç güvenliği için taranır
(md'de olmayan bulgu "PDF'te" diye işaretlenir; diğer kontroller md üzerinde çalışır).
Belgenin **bilim dalını** ve **görsel/sözel biçimini** kendisi tanır; tıp notunu dil öğrenme ölçeğiyle, görsel bir
anatomi atlasını düz metin ölçeğiyle değerlendirmez. Bulguları **satır numarası** ve kural kimliğiyle verir, üç durumlu
bir karar söyler.

Dil sadeleştirmez; o iş kardeş becerisi [Durulaç](https://github.com/mesutbsdgn/turkce-ai-durulac)'ındır. İkisi
birlikte kuruluysa önce Durulaç Türkçe açıklamayı sadeleştirir, sonra Sınaç ölçer.

## Karar

| Karar | Ne demek | Çıkış kodu |
|---|---|---|
| ⛔ **Yayına engel var** | Hasta güvenliğini ya da belgeyi bozan bir kusur bulundu (aşağıda ENGEL/HATA) | 1 |
| ◐ **Karar için denetim eksik** | Engel yok, ama içerik doğruluğu (`denetim:`) ya da hedef (`hedef:`) elle doğrulanmadı | 3 |
| ✓ **Tanımlı kapsamda uygun** | Engel yok, elle alanlar dolu. İçeriğin doğru olduğu anlamına gelmez | 0 |

Üç düzey: **ENGEL** (hasta güvenliği), **HATA** (yayını bozan biçim kusuru), **UYARI** (düzeltme listesi).

## Ölçek

8 boyut, her biri 0 (hata) · 1 (uyarı) · 2 (temiz). Ölçülemeyen boyut (PDF yoksa verimlilik, `hedef:` yoksa hedefle
uyum…) puanlanmaz; çıktı "11/12 (6/8 boyut ölçüldü)" gibi yazar.

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

## Üç katman

1. **Ortak çekirdek (her alanda):** yapı ve okunaklılık kontrolleri, **hasta kimliği** (ad, protokol no, tam doğum
   tarihi) ve **TC kimlik sağlamasına uyan sayı** (etiketli ya da kişi bağlamında ENGEL, bağlamsız UYARI).
2. **Risk taraması (alandan bağımsız):** metinde ilaç ya da doz geçiyorsa sağlık güvenlik kontrolleri, belge tarih
   notu bile olsa çalışır.
3. **Alan profili:** 32 alanın kendi kontrolleri; karma belgede her bölümün alanı ayrıca eklenir.

| Grup | Alanlar |
|---|---|
| Sağlık (en ayrıntılı) | tıp; diş hekimliği, hemşirelik ve ebelik, eczacılık, veteriner, beslenme, fizyoterapi, acil tıp; psikoloji |
| Sayısal ve fen | matematik, istatistik, fen, fizik, kimya, biyoloji, yer bilimleri, ziraat, mühendislik, bilgisayar, mimarlık |
| Sosyal ve beşerî | hukuk, iktisat ve işletme, tarih, coğrafya, sosyal bilgiler, ilahiyat, edebiyat, felsefe, sanat ve müzik, eğitim |
| Dil ve genel | yabancı dil (fr, en, de, es, it), genel |

**Sağlıkta yayını durduranlar:**

- "5,0 mg", ".5 mg" ya da ",5 mg" doz yazımı. Kalın yazıda, kodda, tablo hücresinde (birim sütun başlığında olsa da), HTML'de, yaygın LaTeX biçimlerinde (`5{,}0`, `\SI{}{}`, `\mathrm{mg}`) ve tam genişlik rakamda da aranır; "5,0 mg/kg", "5,0-10 mg", "40.0 MG" da yakalanır. "1.000 mg" binlik sayılır; "PSA 4,0 ng/mL" gibi düzey ölçümü ve ilaç adı geçmeyen fen föyündeki "25,0 mL" sayılmaz.
- Tutmayan doz hesabı ("20 kg × 5 mg/kg = 1000 mg").
- Tutmayan birim dönüşümü ("Glukoz 90 mg/dL = 50 mmol/L").
- Hasta adı (açık etiketle küçük harfle yazılmışsa da), protokol numarası, tam doğum tarihi (ISO biçimi dahil; vaka
  bağlamı yoksa — biyografi — yalnız UYARI).

**Sağlıkta uyarı verenler:**

- ISMP'nin karıştırılmaya açık kısaltmaları: U, IU, cc, q.d., μg, SC, TIW, D/C, OD/OS/OU, ml, "1:1000".
- Bitişik doz ("10mg", "propranolol20 mg").
- Zaman birimi yazılmamış "mg/kg".
- Çocuk dozunda en yüksek doz yok; "gerektiğinde" talimatında doz aralığı yok.
- Harfli gebelik kategorisi.
- Kaynaksız referans aralığı.
- Güncelliği doğrulanması gereken kılavuz, DSM-IV, yanlış yazılmış tür adı.

Tıp ve yedi sağlık alt alanına ayrıca 11 maddelik ortak sağlık elle listesi eklenir (psikolojide yok).

**Öteki alanlardan örnekler:**

- SI birim yazımı.
- Deney föyünde güvenlik notu.
- "p = 0,000" yazımı.
- Python 2 kullanımı.
- Yürürlükten kalkmış kanun: geçmiş olaya uygulanıyorsa sayılmaz (6101 sayılı Kanun m. 1).
- Künyesiz mahkeme kararı, kaynaksız hadis, kaynaksız alıntı.
- Haritada lejant, ölçek, kuzey oku ya da kaynak eksikliği.

## Kullanım

```bash
python3 ~/.claude/skills/sinac/scripts/ogretim_denetim.py ders-notu.md   # alanı kendisi bulur
python3 scripts/ogretim_denetim.py not.md --pdf not.pdf --alan tip  # PDF ölçümü, alanı zorla
python3 scripts/ogretim_denetim.py not.md --json --yil 2026         # makine okur; değerlendirme yılı sabit
```

Claude'da doğal dille ya da adıyla: "Sınaç, bu farmakoloji notumu denetle", "Bu PDF öğretir mi?", "Hukuk ders notum
güncel mi?"

**Yanlış alarmı susturmak** (gerekçe zorunlu; gerekçesiz susturma engeli kaldırmaz):

```markdown
<!-- sinac: yoksay tip_doz_yazimi — bu sayfa ISMP'nin yanlış yazım örneklerini anlatıyor -->
İlaç 5,0 mg <!-- sinac: yoksay — öğretici yanlış örnek; doğrusu altında -->
```

## Kurulum

```bash
git clone https://github.com/mesutbsdgn/sinac.git ~/.claude/skills/sinac
```

Python 3.9+, yalnız standart kütüphane, ağ yok. PDF ölçümü için isteğe bağlı poppler (`pdftotext`, `pdfimages`,
`pdftoppm`).

## Nasıl sınandı

- **Testler:** 100 test, hepsi geçiyor.
  - `test_ogretim_denetim.py` (61);
  - `test_ozellikler.py` (38): gerçek üretilmiş PDF'lerle yazı boyu, vektör çizim, boş sayfa, PDF içeriği; `--duzelt`, kodlama, susturma, maskeleme, ReDoS;
  - `test_karsi_ornekler.py`: 211 karşı örnek.

  GitHub Actions bu testleri Python 3.10 ve 3.13'te çalıştırır (Ubuntu 26.04 imajında 3.9 yok); Python 3.9.6'da yerelde
  sınandı.
- **Bağımsız inceleme** (22 Kasım 2026): GPT-6.1 Sol ve Qwen4 Max Preview, v1.0'ı yüksek eforla ve salt okunur
  inceledi.
  - Raporlardaki karşı örneklerden 32'si betikte çalıştırıldı ve 32'si de gerçek çıktı.
  - Bunlar v2.0'da düzeltildi ve regresyon kümesine girdi (`scripts/tests/karsi_ornekler.json`).
- **Fable 5.2 testi** (aynı gün, v2.0 adayı): 53 gerçekçi belge yazdı (28'i sağlık); 35'inde kararı etkileyen kusur buldu,
  yayına hazırlık notu 3/10 verdi. Kritik ve yüksek bulguların hepsi yeniden üretildi, düzeltildi ve 55 kayıt olarak kümeye
  eklendi. Kümedeki 131 kaydın her birinde kaynak yazılı ("Sol 5", "Qwen K2", "Fable K3"); kaynağı "TC sağlama", "Hasta
  yaş", "Kiril" olan birkaç kenar örneğini Claude ekledi.
- **Gemini 4 Argon incelemesi** (aynı gün, v2.0 son adayı): kodu okuyarak 7,5/10 verdi. 25 karşı örneğinin 20'si betikte
  gerçek çıktı (3'ü çıkmadı, 2'si kısmen); hepsi düzeltildi ve 23 kayıt olarak kümeye eklendi (toplam 154).
- **Kasten bozma:** hasta adı, ondalık cümle bölme, Markdown temizliği ve boş sayfa eşiği kasten bozulunca testler
  kırmızıya döner.
- **PDF kalibrasyonu:** kelime kutusu/punto oranı yazı tipine göre ölçüldü: Helvetica 0,925 · Times 0,900 ·
  Courier 0,786. Betik bu yüzden tek bir punto değil, bir punto aralığı tahmin eder.

## Kanıt

Üç quoteproof araştırması yapıldı: 23 başlık, 872 bulgu, 567'si kaynağında otomatik doğrulandı.

- **Elle açılan kaynaklar:** kurala giren kritik bilgiler ayrıca kaynağında açıldı. Bunlar arasında ISMP, FDA,
  NHMRC, PEP 8, python.org, Merck Veterinary Manual ve bpac NZ var. Mevzuat tarafında 6098 m. 647, 6100 m. 450,
  6102 m. 1533 ve 6101 m. 1 de açıldı.
- **Açılamayanlar:** kaynağı açılamayan bilgi ENGEL ya da HATA kuralı yapılmadı.

Ayrıntılar: [`docs/kanitlar.md`](docs/kanitlar.md), ölçek ve karar modeli [`references/ogretim.md`](references/ogretim.md).

## Sınırları

- Yazımı ve yapıyı denetler; dozun, tanının, kanun yorumunun ya da tarihsel bilginin doğru olduğunu kanıtlamaz.
- Tıbbi, eczacılık, veteriner ya da hukuki görüş değildir.
- Alan tahmini karma belgede yanılabilir; `alan:` ya da `--alan` ile düzeltilir.
- **Açık iş:** regresyon kümesi iki modelin karşı örneklerinden oluşuyor; bağımsız öğretmen ve uzmanların etiketlediği
  gerçek ders notlarından bir altın küme henüz yok.
- **Ölçme geçerliği sınanmadı:** 8 boyutun öğretim kalitesini ayırt ettiği öğretmen değerlendirmesi ve öğrenci
  sonuçlarıyla sınanmadı; toplam puan yalnız göstergedir.

## Sürüm geçmişi

| Sürüm | Tarih | Değişiklik |
|---|---|---|
| v1.0.0 | 22 Kas 2026 | İlk yayın. Durulaç'ın `+ogretim` kipinden (v1.7–1.9) ayrı beceri olarak çıkarıldı, Sınaç adını aldı |
| v2.0.1 | 22 Kas 2026 | CI: Python 3.10 ve 3.13 (GitHub Ubuntu 26.04 imajında 3.9 yok); kod değişmedi |
| v2.0.0 | 22 Kas 2026 | GPT-6.1 Sol, Qwen4 Max, Fable 5.2, Gemini 4 Argon (iki tur) ve GPT-6.2 Astra (iki tur) incelemeleri sonrası. Değişiklikler aşağıda |

v2.0.0'daki değişiklikler:

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

## Lisans

Kullanım hakkı lisansı: [LICENSE](LICENSE). Telif © 2026 mesutbsdgn.
