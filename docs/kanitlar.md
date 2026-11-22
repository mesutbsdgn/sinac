# Sınaç — kanıt özeti (22.11.2026)

Araştırma: quoteproof, 6 başlık (tıp, diş hekimliği, matematik, tarih/sosyal, coğrafya/harita, görsel materyal),
DeepSeek/Qwen çalışanları, 67 bağımsız kaynak, 249 bulgu: 151 doğrulandı · 15 kısmen · 43 bulunamadı (sentezden
çıkarıldı) · 40 erişilemedi. Ham notlar oturum klasöründeydi, kalıcı değil; kurala giren kanıt aşağıda.

**Claude kaynağında açtı** işareti (✓): alıntı Claude tarafından sayfada ayrıca arandı ve bulundu.

## Kurala giren kanıt

| Kural | Kaynak | Alıntı (özgün dil) | |
|---|---|---|---|
| Tıp: sondaki sıfır yok | [ISMP Error-Prone Abbreviations List, 2024](https://www.ismp.org/system/files/resources/2024-04/ISMP_ErrorProneAbbreviation_List.pdf) | "Do not use trailing zeros for doses expressed in whole numbers" | ✓ |
| Tıp: baştaki sıfır, U/IU, qd, cc, μg→mcg | aynı liste | "leading zero", "qd", "cc", "mcg" maddeleri listede | ✓ |
| Tıp: ilaç adını kısaltma | aynı liste | "To prevent confusion, avoid abbreviating drug names entirely." | oto |
| Tıp: kılavuz tarihi | [NHMRC, Updating](https://www.nhmrc.gov.au/guidelinesforguidelines/updating) | "it is important that the date of last review is clearly marked" | ✓ |
| Tıp: kendini sınama ve aralıklı tekrar | [Trumble ve ark. 2023, BMC Med Educ](https://pmc.ncbi.nlm.nih.gov/articles/PMC11078833/) | "Distributed practice and retrieval practice are effective at improving academic grades in health professions education." | oto |
| Diş: tek numara sistemi | [Al-Johany 2016](https://pmc.ncbi.nlm.nih.gov/articles/PMC5110463/) | "important to teach all three common TNS (FDI, Palmer and Universal) to students but that only one system should be used in order to avoid confusion" | ✓ |
| Diş: FDI = ISO 3950 | [ISO/ANSI/ADA 3950-2010 önizleme](https://webstore.ansi.org/) · Wikipedia | "a system for designating teeth or areas of the oral cavity using two digits" | oto |
| Matematik: çözülmüş örnek | [Barbieri ve ark. 2023, Educ Psychol Rev](https://www.danamillercotto.com/uploads/4/7/7/2/47725475/barbieri_et_al__2023__we_meta-analysis.pdf) | "the average effect size of worked examples on mathematics performance outcomes was medium with g = 0.48" | ✓ |
| Matematik: örnek–problem dönüşümlü, quiz | [IES pratik kılavuzu 2007](https://ies.ed.gov/ncee/wwc/Docs/PracticeGuide/20072004.pdf) | "Interleave worked example solutions …" · "Use quizzing with active retrieval of information" | oto |
| Coğrafya: harita öğeleri | [BBC Bitesize](https://www.bbc.co.uk/bitesize/guides/z6j6fg8/revision/2) | "Maps should have a:" (title, scale, north arrow, key) | ✓ |
| Coğrafya: kaynak ve yıl | [Time & Spatial](https://www.timeandspatial.com/study/map-design/sources-methods-dates-and-credits) | "Name each source, with the provider and the year or date" | oto |
| Coğrafya: kuzey oku | National Geographic Education | "If only one arrow is used, the arrow usually points north." | oto |
| Görsel: renk tek taşıyıcı değil | [WCAG 2.2, SC 1.4.1](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color) | "Color is not used as the only visual means of conveying information" | oto |
| Görsel: kontrast | WCAG 2.2 SC 1.4.3 / 1.4.11 | metin 4.5:1, büyük metin ve grafik öğe 3:1 | oto |
| Görsel: süs görsel zararlı | Rey 2012 meta-analizi (Tislar & Steelman 2021 aktarımı, PMC8442593) | "weighted mean effect size of d = 0.30" (hatırlama) | oto |
| Görsel: etiket yanında | eddl.tru.ca (Mayer bitişiklik özeti); Noetel ve ark. 2021 meta-meta-analiz | "The largest benefits were for … temporal/spatial contiguity, and signaling." | oto |
| Tarih: kendini sınama | Frontiers (ilkokul tarih metni) | test %67,0 · yeniden okuma %48,6 | oto |

`oto` = quoteproof `dogrula.py` alıntıyı sayfada buldu; Claude ayrıca açmadı.

## Açılamayan kaynaklar — kurala alınmadı

- ICA "4 Map Design" (icaci.org): bağlantı reddedildi. Başlıkta yıl, lejant eksiksizliği alıntıları denetlenemedi.
- Rohrer ve ark. 2020 (karışık alıştırma, %61 / %38, d = 0,83): USF sunucusu kapalı, APA sayfası JavaScript.
- Shekelle ve ark. 2001 JAMA (kılavuzların yarısı 5,8 yılda eskir): 403 ve PubMed çerez duvarı.
- Joint Commission "Do Not Use" sayfası: 403. Aynı maddeler ISMP listesinde doğrulandı.

## Kurala alınmayan bulgular

- Tall Man harf yazımı: ISMP'ye göre kanıt çelişkili.
- Anki/flashcard: gözlemsel ilişki var, sistematik derlemede kanıt kesinliği "çok düşük".
- Tanım → teorem → örnek sırası: kanıt çelişkili (yalnız ELLE öneri).
- Doz ile birim arasında boşluk: bu araştırmada alıntı bulunamadı; v2.0 incelemesinde Claude ISMP sayfasında doğruladı ve
  `saglik_bosluk` kuralı eklendi (aşağıda).
- Kalıcılık ve transfer (diş simülasyonu, 3B model): uzun vadeli kanıt zayıf; ölçeğe girmedi.

---

# Bilim dalları genişletmesi (22.11.2026)

Araştırma: quoteproof, 12 başlık (5'i sağlık: ilaç yazımı, lab/birim, mahremiyet/güncellik, sağlık meslekleri,
eczacılık-veteriner-beslenme; ayrıca psikoloji-istatistik, mühendislik-fizik-kimya, biyoloji-yer-ziraat, bilgisayar,
hukuk, iktisat-işletme, beşerî bilimler-sanat). DeepSeek/Qwen çalışanları; 455 bulgu: 303 doğrulandı · 18 kısmen ·
51 bulunamadı · 77 erişilemedi · 6 kanıt yok.

## Claude kaynağında açtı (✓)

| Kural | Kaynak | Alıntı |
|---|---|---|
| TIW, OD/OS/OU, SUBQ, `<` işareti | [ISMP 2024](https://www.ismp.org/system/files/resources/2024-04/ISMP_ErrorProneAbbreviation_List.pdf) | "Mistaken as 3 times a day or twice in a week" · "Mistaken as OD, OS, OU" · "Use SUBQ" · "misread as 40" · "10- to 100-fold overdose" |
| Harfli gebelik kategorisi | [FDA PLLR](https://www.fda.gov/drugs/labeling-information-drug-products/pregnancy-and-lactation-labeling-resources) | "The PLLR removes pregnancy letter categories" |
| Kiloya göre doz | [ISMP Kanada 2016](https://ismpcanada.ca/wp-content/uploads/ISMPCSB2016-09-WeightBasedDoseErrors.pdf) · [bpac NZ](https://bpac.org.nz/bpj/2010/july/docs/BPJ_29_errors_guide_pages_8-18.pdf) | "Provide the weight and dose per unit weight" · "maximum recommended dose", "40 kg" |
| Kreatinin dönüşümü | [Pottel ve ark., PMC10628758](https://pmc.ncbi.nlm.nih.gov/articles/PMC10628758/) | "divided by 88.4" |
| Kedide parasetamol | [Merck Veterinary Manual](https://www.merckvetmanual.com/toxicology/toxicoses-from-human-analgesics/toxicoses-from-human-analgesics-in-animals) | "40–50 mg/kg" |
| Python 2 | [python.org](https://www.python.org/doc/sunset-python-2/) | "no longer supported" |
| PEP 8 satır | [PEP 8](https://peps.python.org/pep-0008/) | "Limit all lines to a maximum of 79 characters" |
| Mülga kanunlar | mevzuat.gov.tr (mevzuat MCP) | 6098 m. 647 "818 sayılı Borçlar Kanunu yürürlükten kaldırılmıştır"; 6100 m. 450 "1086 sayılı … tümüyle yürürlükten kaldırılmıştır"; 6102 m. 1533 "6762 sayılı Türk Ticaret Kanunu yürürlükten kaldırılmıştır" |

## Otomatik doğrulanan (oto), kurala ya da elle listesine giren

BIPM SI Broşürü (birim küçük harf, sayı-birim "always" boşluk, sembole çoğul eki yok) · NIST SP 811 (°C'den önce boşluk) ·
APA Style (p için baştaki sıfır yok, iki-üç ondalık) · CASRAI ("p value is … not zero") · APA JARS (etki büyüklüğü ve GA) ·
ICZN (cins büyük, tür küçük, italik) · HGNC (gen italik, protein düz) · ICS çizelgesi 2026/06 · EPA etiket kılavuzu
("Percentage application rates should never be used alone") · EMA ve AB 2019/6 arınma süresi tanımı · EFSA (1 MJ =
238.83 kcal) · DSM-5-TR 18 Mart 2022 (psychiatry.org) · ICD-11 1 Ocak 2022 (WHO) · NANDA-I 2024–2026 · ERC beş yılda
bir güncelleme · HIPAA Safe Harbor · BMJ ve ICMJE hasta onamı · GMC anonimleştirilmiş kayıt · kimliksizleştirme
yönetmeliği (mevzuat.gov.tr) · FSEK 70 yıl (mevzuat.gov.tr) · Yargıtay karar arama künye alanları · ISMP 2024 yüksek
riskli ilaçlar listesi (traneksamik asit eklendi) · Getty CDWA çekirdek künye.

## Açılamayan / kurala alınmayan

- PSNet "mg/kg/d" vakası (403): kontrol yalnız UYARI ve açıklık kuralı (kaynağı açılamadı) olarak kaldı.
- JNC 7'nin yerini alan kılavuz (AHA sayfası açılamadı): kural çıkarıldı.
- KVKK karar sayfaları: açılamadı; kişisel veri kuralı HIPAA, BMJ, ICMJE ve yönetmeliğe dayandı.
- 765 (TCK), 743 (MK), 1412 (CMUK): yürürlük kanunlarının (5252, 4722, 5320) metni açılamadı → yalnız UYARI.
- Madrid Kodu (IAPT) sayfası açılamadı: yalnız elle listesinde.
- ISMP 2024 listesinde artık olmayan HS, BT, x3d: kuraldan çıkarıldı.
- Tall Man, Anki, öğrenme stilleri, grafik kullanımının öğrenmeyi kendiliğinden artırması: kanıt çelişkili ya da zayıf.

---

# v2.0 — bağımsız inceleme ve yeni kanıt (22.11.2026)

**İnceleme:** GPT-6.1 Sol (`dagit sol-oku`, yüksek efor, 11 dk) ve Qwen4 Max Preview (`dagit q4-oku`, yüksek efor,
13 dk) v1.0'ı salt okunur inceledi. Claude iki rapordan 32 karşı örneği betikte çalıştırdı; 32'si de gerçek çıktı.
Hepsi düzeltildi; örnekler `scripts/tests/karsi_ornekler.json`'a girdi (her kayıtta kaynak: "Sol 5", "Qwen K2"…).

## Claude kaynağında açtı (✓)

| Kural | Kaynak | Alıntı |
|---|---|---|
| Doz–birim boşluğu | [ISMP 2024](https://www.ismp.org/system/files/resources/2024-04/ISMP_ErrorProneAbbreviation_List.pdf) | "adequate space" · "Propranolol20 mg mistaken as propranolol 120 mg" |
| ml → mL | aynı liste | "Use mL" |
| Oranla derişim | aynı liste | "EPINEPHrine 1:1,000; 1:10,000; 1:100,000" örneği |
| PEP 8 ekip sınırı | [PEP 8](https://peps.python.org/pep-0008/) | "up to 99 characters" |
| Çocukta azami doz, PRN | [bpac NZ](https://bpac.org.nz/bpj/2010/july/docs/BPJ_29_errors_guide_pages_8-18.pdf) | "maximum recommended dose" · "when required" · "PRN" |
| Mülga kanun UYARI'ya indi | [6101 sayılı Kanun](https://mgm.adalet.gov.tr/Resimler/SayfaDokuman/181020191506586101.pdf) | m. 1: "türk borçlar kanununun yürürlüğe girdiği tarihten önceki fiil ve işlemlere … kural olarak o kanun hükümleri uygulanır" |

## Ölçüm (Claude)

PDF kelime kutusu / punto oranı, yalnız standart kütüphaneyle üretilen tek sayfalı PDF'lerde (7–12 pt, 14 satır)
poppler `pdftotext -bbox` ile: Helvetica 0,925 · Times-Roman 0,900 · Courier 0,786 (her puntoda aynı). Testte yeniden
üretilir: `scripts/test_ozellikler.py` `GercekPdf.test_kalibrasyon_orani`.

## İncelemenin kabul edilmeyen ya da ertelenen önerileri

- Alan ağırlıklı puan ve risk ağırlıkları: kanıt olmadan yeni keyfîlik katmanı (Sol'un da uyarısı); toplam ağırlıksız.
- HbA1c NGSP/IFCC dönüşümü (Qwen O1): birincil kaynakla doğrulanmadı, eklenmedi.
- Kiloya dayalı hesapta ağırlık değişkeni eksikliği, tablo başlığı–birim ilişkisi: yapısal ayrıştırma ister; açık iş.
- Altın küme ve ölçme geçerliği (öğretmen etiketi, öğrenci sonucu): otomatikleştirilemez; açık iş.

---

# v2.0 — Fable 5.2 bağımsız sınaması (22.11.2026)

Fable 5.2 (Claude ajanı, salt okunur) 53 gerçekçi belge (28 sağlık), ~150 tek satırlık varyant, 17 performans girdisi
yazdı; 35 belgede kararı etkileyen kusur buldu, "yayına hazırlık" 3/10. Claude 10 kritik ve 17 yüksek bulgunun hepsini
betikte yeniden üretti; hepsi gerçekti. Düzeltmeler ve 55 yeni karşı örnek (kaynak: "Fable K1…Y12") eklendi.

Başlıca kök nedenler: (1) kontroller cümle üzerinde çalışıyordu (".5 mg" ve "D.T." noktada bölünüyordu; satır numarası
ve satır susturması yanlış satıra düşüyordu) → satır tabanlı hazırlık; (2) metin normalleştirme eksikti (NFKC, HTML
varlığı, LaTeX `{,}`, tablo başlığı birimi); (3) istisnalar tek sözcükle tetikleniyordu ("yerine", "sentetik", "test")
→ açık işaret ya da aynı ifade; (4) bağlamsız örüntüler (mL, dosya no, "Vaka:") → ilaç/vaka bağlamı; (5) sınırsız
düzenli ifadeler (`[^)]*`, `\s*…\s*`) → sınırlı nicelik ve düzenli ifadesiz susturma ayrıştırıcısı; her bölümde yeniden
derlenen desenler → önbellek ve sözcük sayacı.

Ölçülen süre (bu Mac): 2 MB gerçekçi md 60 sn+ → ~12 sn; 3 KB susturma ReDoS girdisi 60 sn+ → ~0 sn; kapanmamış
`<!--`, `<style`, `![`, `\frac{` ile 150–280 KB tek satır 7–26 sn → ≤ 2,2 sn.

Kabul edilmeyen/ertelenen: rastgele 11 hanenin ~%1'inin TC sağlamasına uyması (etiketsiz sayıda da ENGEL kalıyor;
öğrenci no/barkod yanlış alarmı olası — belgede yazılı); `--alan` ile bölüm alanlarının kapanması (bilinçli, SKILL.md'de
yazılı).

---

# v2.0 — Gemini 4 Argon incelemesi (22.11.2026)

Gemini 4 Argon (Antigravity, salt okunur, yüksek efor) bütün dosyaları istemde okudu; araç çalıştıramadı. İstem
`ogretim_denetim.py`'nin 1235. satırında kesildi; bu yüzden `denetle()` sonrası, `--duzelt` ve `main` incelenmedi.
Not: 7,5/10. Claude 25 karşı örneğin hepsini betikte çalıştırdı: 20'si gerçek, 2'si kısmen (uyarı düzeyi), 3'ü çıkmadı
("fayda" → jeoloji, "Ancak Borçlar Kanunu", "126 mg/dL ya da 11,1 mmol/L" ENGEL'i). Gerçek olanlar düzeltildi ve
"Argon …" kaynaklı 21 kayıt, Claude'un yazdığı 2 karşıt kayıtla ("Hasta: Başak Demir", "Hasta adı: Ateş Kaya": klinik
kök listesi ad kaçırmasın) kümeye girdi.

Claude'un aynı turda Fransızca belgelerde bulduğu iki ek hata: ses dosyası adındaki onaltılık karmada (`…915022fdf7f`)
TC sağlamasına uyan rakam dizisi ENGEL alıyordu (artık harf/tireye bitişik dizi aday değil); `dil: tr-fr` reddediliyordu.

Kabul edilmeyen/ertelenen (sonra kapatılanlar işaretli): `ONDALIK_SONU_SIFIR` (0,50 mg) UYARI'sı kalır, ISMP tam sayı
kuralı genişletilmedi; tartım/hazırlama bağlamında artık uyarı yok (A3, kapandı). Etiketsiz TC adayı: Mesut'un kararıyla
(seçenek b) kişi bağlamı yoksa UYARI (A4, kapandı); karar öncesi ölçüm: ~/Documents/03_PROJELER altındaki 25 067 md
dosyasında sağlamaya uyan etiketsiz aday 0. Bitişik "2g", "10U", "20mEq" yalnız ilaç/doz bağlamında UYARI (A2, kapandı).
Ayrıca A1: uzun rakam dizisinde karesel süren 4 sayı deseni düzeltildi ("." + 100 000 hane: > 2 dk → < 1 sn). Kalan: kısaltma tanımında baş harf eşleşmesi (HT, KT); satır numarasının ilk eşleşmeye düşmesi;
dile duyarlı alan tespiti (İngilizce/Fransızca çift dil fazına, YOL_HARITASI F3).

## Argon ikinci tur — kesik kalan bölüm (22.11.2026)

İlk turda istem kesildiği için görülmeyen bölüm (susturma, karar/puan, `--duzelt`, `main`; ~21 KB) Argon'a ayrıca verildi.
Not 6,5/10. Claude 9 iddiayı çalıştırdı: 7'si gerçek (yukarıdaki README maddesi), 2'si çıkmadı (BOM'lu dosyada
frontmatter korunuyor; "14pt sonra 8pt" düzeltiliyor). Uygulanan küçük ek öneriler: susturulan ENGEL/HATA'nın boyutu en
çok 1 puan; `--dil` küçük harfe; pdftotext `-enc UTF-8`; reddedilen elle değeri metin çıktısında. Uygulanmayan: görsel
olup PDF ölçülmeyen belgede Okunaklılık'ın ölçülmüş sayılması (alt metin ve şekil başlığı kontrolleri bu boyutu gerçekten
ölçüyor; bilinçli). Not: dagit "salt okunur koşuda ağaç değişti" uyardı; değişen 4 dosyanın hepsi Claude'un aynı saniyedeki
belge düzenlemesiydi (Argon araçsız çalıştı).

## GPT-6.2 Astra sınaması (22.11.2026)

Fable 5.2 kotası 26 Kasım'a kadar dolu olduğu için son aday sınaması Mesut'un isteğiyle GPT-6.2 Astra'ya verildi (Codex,
yüksek efor, Sınaç'ın kopyasında; yalnız `_sinama/` altına yazdı, başlangıçtaki 16 dosyanın SHA-256'sı değişmedi). Astra
44 gerçekçi belge yazıp beklentiyi önceden kaydetti; 18'inde karar farklıydı, not 4/10. Claude 18 bulgunun hepsini asıl
depoda yeniden üretti; hepsi gerçekti (ayrıntı README "İnceleme geçmişi"). Düzeltmeden sonra Astra'nın 61 beklentisi
(ek ve eş belgeler dahil) tutuyor; 21 kayıt kümeye girdi (188). Kalan küçük nokta: yinelenen başlık numarası uyarısı ilk
geçtiği satırı gösteriyor.

### Astra ikinci tur

Düzeltilmiş sürüm yeni bir kopyada Astra'ya yeniden verildi: önceki 44 belge 44/44 tuttu; 56 yeni belgenin 23'ünde karar
farklıydı (4/10). Claude 22'sini yeniden üretti (biri, 5b, çıkmadı); hepsi düzeltildi, 23 kayıt kümeye girdi (211).
Düzeltmeden sonra iki turun 117 belgesi beklenen kararı veriyor. Tasarım kararı: noktalı üç haneli sayı ("1.125")
belirsizdir; iki yorumdan biri tutuyorsa ENGEL değil UYARI verilir (belirsizlikte sayısal düzeltme önerilmez).
Bilinen sınır: düzenli ifade tabanlı denetim her yeni bağımsız turda yeni varyant bulunmasına açıktır; Sınaç yayın
kararını kolaylaştırır, uzman/elle denetimin yerine geçmez (SKILL.md, README "Sınırları").
