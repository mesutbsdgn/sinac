# Sınaç — ölçek, alanlar ve kurallar

Öğrenciye giden belgeleri (ders notu, konu anlatımı, rehber, ezber kitapçığı, kelime listesi, pano) **8 boyutlu**,
kanıta dayalı bir ölçekle denetler, puanlar (her boyut 0–2; ölçülen boyutlar üzerinden), güvenli düzeltmeleri yapar ve
**üç durumlu bir karar** verir. Tek kiptir ama **alanı tanır**: belgenin alanını (32 alan; liste aşağıda) ve biçimini (sözel / görsel)
tespit eder, her alanda aynı kalan **ortak çekirdeğe** o alanın **profilini** ekler. Fransızca ölçeği tıp notuna ya da
görsel atlas çalışmasına uygulanmaz. Fransızca/DELF satırları yalnız **örnek**tir.

Kaynak çalışmalar (hepsi 22.11.2026, quoteproof): öğretim ölçeği (5 başlık, 168 bulgu, 113 doğrulandı), alan
profilleri (6 başlık, 249 bulgu, 151 doğrulandı) ve bilim dalları genişletmesi (12 başlık, 5'i sağlık; 455 bulgu, 303
doğrulandı). Kurala giren kanıt ve Claude'un kaynağında açtıkları: `docs/kanitlar.md`. v2 (22.11.2026): GPT-6.1 Sol ve
Qwen4 Max Preview'ın bağımsız incelemeleri; 32 karşı örneğin hepsi gerçek çıktı, hepsi düzeltildi ve
`scripts/tests/karsi_ornekler.json` regresyon kümesine girdi. Ardından Fable 5.2 53 gerçekçi belgeyle sınadı (3/10);
bulguları düzeltildi, küme 131 kayda çıktı. Son sürümü Gemini 4 Argon kodu okuyarak inceledi (7,5/10); 25 karşı
örneğinin 20'si gerçek çıktı, düzeltildi; küme 154 kayıt.

## Ne zaman açık, ne zaman kapalı

- **Açık:** öğretim amaçlı belge: ders notu, rehber, çalışma kâğıdı, ezber/kelime listesi, sınav hazırlık notu.
  Tetikleyiciler: "ders notunu denetle", "öğretim materyali ölçeği", "bu PDF öğretir mi", "notumu kontrol et".
- **Kapalı:** sözleşme ve dilekçe gibi hukuk belgeleri, edebî eserin kendisi (şiir, öykü), sohbet/mesaj, resmî yazı.
  Akademik makale öğretim materyali değildir (tez modu kullanılır). Hukuk fakültesi ders notu ve edebiyat ders notu
  öğretim materyalidir; Sınaç bunlarda açıktır.
- Sınaç dili sadeleştirmez. Kullanıcı Türkçe açıklamanın sadeleşmesini de isterse önce Durulaç becerisinin
  (`turkce-ai-durulac`) Temizle kipi uygulanır: yalnız Türkçe açıklama düzenlenir; yabancı dildeki örnek cümle, okunuş,
  formül, doz, diş/kanun numarası ve tabloya dokunulmaz. Sonra ölçek çalışır. Durulaç kurulu değilse bu adım atlanır
  ve kullanıcıya söylenir.

## Alan tespiti ve profiller

**Üç katman** (v2):

1. **Ortak çekirdek** (her alanda): yabancı alfabe karışması, yer tutucu, başlık numarası, sayfa göndermesi, kendini
   sınama, alt metin, şekil başlığı, PDF okunaklılığı ve verimliliği; **hasta kimliği** (ad, protokol no, tam doğum
   tarihi; vaka paragrafında telefon/e-posta) ve **TC kimlik sağlamasına uyan sayı**. Dayanağı Sweller, Mayer, Dunlosky;
   kimlikte HIPAA Safe Harbor, BMJ/ICMJE onam kuralları ve kimliksizleştirme yönetmeliği.
2. **Risk taraması** (alandan bağımsız): metinde ilaç/doz örüntüsü (sayı + mg/mcg/mL/ünite, "doz", "ilaç") varsa doz
   yazımı, ISMP kısaltmaları, doz–birim boşluğu, kiloya göre doz ve doz aritmetiği her alanda çalışır. Alan tespiti
   yanılsa bile sağlık güvenlik kontrolleri kapanmaz (Sol bulgu 2).
3. **Alan profili** + **bölüm alanları**: belge ana alanının kontrolleri; karma belgede ≥40 kelimelik bir bölümün en
   güçlü alanı farklıysa onun kontrolleri de çalışır (Sol bulgu 3).

**Tespit sırası:** `--alan` → frontmatter `alan:` (çıktıda "kullanıcı seçimi") → sözcük puanı. Anahtar sözcükler
`references/ogretim-alanlari.json`'da. Puanlama: bir sözcük en çok 3 kez sayılır; birden çok profilde geçen sözcüğün
ağırlığı bölünür (nüfus: coğrafya + sosyal → ½); aynı profilde başka anahtarla başlayan anahtar atılır (hemşire /
hemşirelik çift sayılmaz). Türkçe ve İngilizce küçük harf ayrı ayrı denenir (İ/ı sorunu). Sondaki ünsüz yumuşar
(çürük → çürüğü), 4 harf ve kısası ek zinciriyle eşleşir (diş → dişçi; gen ≠ genel). Yabancı dil alanı Türkçe harfli
okunuşla (`/…/`) tanınır. En yüksek puan 4'ün altındaysa **genel**. Çıktı "destek: güçlü/orta/zayıf" yazar (kalibre
edilmiş bir olasılık değildir); zayıfsa `alan:` yazmasını önerir.

**Biçim:** frontmatter `bicim: gorsel|sozel` ya da tespit: md'de görsel başına 120 kelimeden az metin, ya da PDF
sayfalarının yarısı görselli ve az metinli (<120 kelime) → **görsel**. Görsel biçimde her alanın elle listesine
`_gorsel` maddeleri eklenir ve 3+ görselde şekil başlığı ("Şekil N") aranır.

**Üst/alt alan:** hemşirelik, eczacılık, veteriner, beslenme, fizyoterapi, acil ve diş hekimliği tıbbın; fizik,
kimya ve biyoloji fenin; istatistik matematiğin alt alanıdır. Alt alan en az 3 puan alır ve üst alan puanının %15'ine ulaşırsa
daha özel olan seçilir (hemşirelik notu tıp sözcüğü de taşır; alt alan aynı güvenlik kontrollerini miras aldığı için
bu seçim düşük risklidir). Alt alanlar üst alanın ortak kontrol grubunu (`@saglik`, `@fen`)
ve sağlıkta ortak elle listesini miras alır.

**TC kimlik:** sağlama algoritmasına uyan 11 haneli sayı etiketliyse ("TC:", "kimlik no"; boşluklu/noktalı biçim de) ya
da 3-3-3-2 gruplu yazılmışsa **ENGEL**dir. Etiketsizse aynı paragrafta kişi/kimlik bağlamı (hasta, öğrenci, vaka, kimlik,
başvuru, kayıt…) varsa ENGEL, yoksa UYARI (22.11.2026 kararı). Harf ya da tireye bitişik rakam dizisi (dosya adı, karma)
aday sayılmaz. Aynı cümlede "sentetik/örnek/sağlama" geçiyorsa UYARI. Sağlamaya uymak sayının gerçek kişiye ait olduğunu kanıtlamaz;
rastgele 11 hanenin yaklaşık %1'i de uyar (Qwen D2).

### Sağlık grubu (`@saglik`) — en ayrıntılı bölüm

Tıp, yedi sağlık alt alanı ve psikolojide birlikte çalışır. **Risk taraması** (satırda ilaç adı ya da doz bağlamıyla
birim görülürse, alan ne olursa olsun) şu sekiz kontrolü çalıştırır: doz yazımı, tehlikeli kısaltma (iki liste),
doz–birim boşluğu, kiloya göre doz, doz aritmetiği, lab birim dönüşümü, gerektiğinde talimatı, çocukta azami doz.
Tarama satır satır ve yan cümle düzeyindedir; her eşleşme ayrı bulgu ve kendi satır numarasıdır. Bağlam kuralları:
birim tablo sütun başlığındaysa hücreye eklenir; "1.000 mg" binlik sayılır ("1,000 mg" belirsiz → UYARI); "düzey,
çukur, çıkış, volüm, sonuç" geçen ve ilaç adı geçmeyen yan cümle doz sayılmaz; fen alanlarında (kimya, fizik…) mL/g
yalnız ilaç bağlamında doz sayılır; öğretici yanlış örnek ancak açık işaretle (❌, "yanlış yazım:", "kullanmayın")
UYARI'ya iner — "yerine", "kaçının" yetmez.
Düzeyler: **ENGEL** (hasta güvenliği; yayını durdurur) · UYARI. Kural yalnız aynı cümlede "yanlış/❌/kullanmayın"
geçiyorsa öğretici yanlış örnek sayılır ve UYARI'ya iner (belge genelindeki bir sözcük susturmaz).

| Kontrol (`kural`) | Düzey | Ne yakalar | Dayanak |
|---|---|---|---|
| Doz yazımı (`tip_doz_yazimi`) | **ENGEL** | sondaki sıfır (5,0 mg; 5,0 mg/kg; kalın, kod, tablo, LaTeX içinde de), baştaki sıfırsız ondalık (,5 mg); "g" yalnız ilaç bağlamında (besin lifi sayılmaz); g/dL, mmol/L gibi lab paydası sayılmaz. Ondalık sonu sıfır (0,50 mg) ve OCR şüphesi (5, O mg) UYARI | ISMP 2024: "Mistaken as 10 mg if the decimal point is not seen", "10- to 100-fold overdose" ✓ |
| Doz/dönüşüm aritmetiği (`doz_aritmetigi`, `lab_birim_karisik`) | **ENGEL** | "20 kg × 5 mg/kg = 1000 mg", "100 mg/5 mL; 50 mg = 5 mL", "Glukoz 90 mg/dL = 50 mmol/L" (±%3) | aritmetik; glukoz ÷ 18 (Sacks), kreatinin × 88,4 ✓ |
| Hasta kimliği (`hasta_kimlik`, çekirdek) | **ENGEL** | "Hasta:/Vaka:/Ad soyad:" + ad (büyük/küçük harf), protokol/dosya no (AB-12345 dahil), tam doğum tarihi (ISO dahil; vaka bağlamı ya da sağlık alanı yoksa UYARI; 1930 öncesi yalnız vaka bağlamında); aynı paragrafta (boş satırla ayrılan) "kurmaca/sentetik" → UYARI. Tam yatış tarihi, vakada telefon/e-posta UYARI | HIPAA Safe Harbor; BMJ, ICMJE; kimliksizleştirme yönetmeliği |
| Tehlikeli kısaltma | UYARI | U/u/IU (U/L hariç), cc, q.d., q.o.d., MSO4/MgSO₄, μg; SC/SQ/subq (dozdan sonra da), TIW/tiw, D/C, AD/AS/AU, OD/OS/OU, doz önünde > <, "ml" (→ mL), adrenalin "1:1000" | ISMP 2024 ✓ ("Use SUBQ", "Use mL", "1:1,000" örneği) |
| Doz–birim boşluğu (`saglik_bosluk`) | UYARI | "10mg", "propranolol20 mg"; "2g", "10U", "20mEq" yalnız ilaç/doz bağlamlı yan cümlede ("5G ağı", "2g NaCl tartılır" sayılmaz) | ISMP: "Propranolol20 mg mistaken as propranolol 120 mg" ✓ |
| Kiloya göre doz | UYARI | aynı cümlede zaman birimi yoksa (önce ya da sonra; /day, daily, divided dahil); "mg/kg/d" her zaman | ISMP Kanada ✓; bpac NZ ✓; PSNet vakası (açılamadı) → açıklık kuralı |
| Çocukta azami doz (`cocuk_azami_doz`) | UYARI | çocuk/pediatrik + mg/kg, ama en yüksek doz yok | bpac NZ: "maximum recommended dose" ✓ |
| Gerektiğinde talimatı (`prn_talimat`) | UYARI | "ağrı olursa/gerektiğinde" + doz, ama aralık ya da günlük tavan yok | bpac NZ: "when required", "PRN" ✓ |
| Gebelik kategorisi | UYARI | "gebelik kategorisi X" (veterinerde çalışmaz) | FDA PLLR ✓ (insan reçeteli ilaç etiketi) |
| Lab birim karışması | UYARI | aynı analit iki birimle, belgede dönüşüm ya da doğru eşitlik yoksa | glukoz ÷ 18, kreatinin × 88,4 ✓ |
| Referans aralığı | UYARI | kaynaksız "normal değer/referans aralığı" (tek yer bile) | birim ve aralık birlikte verilir (oto) |
| Kılavuz yılı / yaşı | UYARI | kurum adıyla (ESC, AHA, ERC, GINA, GOLD, KDIGO, ADA, NICE…) aynı cümlede yıl; yerel tarama politikası: 5 yıl, yıllık raporlarda (GINA, GOLD, ADA) 1 sürüm; karşılaştırma/tarihçe cümlesi sayılmaz; `--yil` ile değerlendirme yılı | NHMRC ✓ (5 yıl evrensel süre değildir; "güncelliği doğrulanmalı" der) |
| Eski tanı sürümü | UYARI | DSM-IV/III (DSM-5 anılmıyorsa) | DSM-5-TR 2022 (oto); ICD-10 bilerek yok |
| Tür adı | UYARI | "Escherichia Coli", küçük harfli cins, "E.coli", italik olmayan bilimsel ad | ICZN (oto) |
| p değeri | UYARI | p = 0,000 / .0000 / 0 (0,05 sayılmaz) | APA, CASRAI (oto) |
| Tanımsız kısaltma | UYARI | ≥2 kez kullanılan 3+ kısaltma; EKG, MR, BT, TSH, CRP gibi standartlar sayılmaz; "ABC: açılım" ancak baş harfler tutuyorsa tanım sayılır | ISMP "avoid abbreviating drug names" |

Alt alana özgü: **diş** (FDI/Universal karışması; Al-Johany 2016 ✓), **hemşirelik** (bakım planında tanı/amaç/girişim/
değerlendirme eksikliği; NANDA-I 2024–2026), **veteriner** (türü yazılmamış doz; gıda hayvanında arınma süresi yok;
Merck: kedide parasetamol 40–50 mg/kg ✓; AB 2019/6), **beslenme** ("kalori" yerine kcal; besine hastalık tedavi/önleme
özelliği), **fizyoterapi** (FITT öğesi eksik egzersiz reçetesi; ACSM FITT-VP), **acil** (kılavuz yaşı; ERC 2025),
**psikoloji** (sağlık grubunun tamamı; DSM-IV, p = 0,000).

### Öteki alanlar

| Alan | OTO kontroller | Dayanak |
|---|---|---|
| Yabancı dil | dil bilgisi terimi > 12, hedef dışı dil > 8, uzun okunuş > %15, okunuşsuz yabancı metin | Nation, Sweller, DELF ızgarası |
| Matematik · İstatistik | çözülmüş örnek yok; soru–cevap kapsamı ("5 sorudan 1'inin cevabı var"); istatistikte p = 0,000 | Barbieri 2023 g = 0,48 ✓; IES; APA "p value is … not zero" (oto), baştaki sıfırsız p (APA) |
| Fen · Fizik · Kimya · Biyoloji | SI sembolü yanlış (Kg, Km, gr, lt, KW; Mt megaton, Sn kalay sayılmaz); sayı-birim bitişik (5kg, 20°C); deneyde güvenlik notu yok; çözülmüş örnek; tür adı (biyoloji) | BIPM SI Broşürü: küçük harf, "always" boşluk (oto); GHS H/P ifadeleri; ICZN |
| Mühendislik | SI kuralları, cevapsız problem, yılsız veri | BIPM; NIST SP 811 (oto) |
| Yer bilimleri · Ziraat | yılsız veri; harita öğeleri; SI; ziraatte deney/ilaçlama güvenliği, tür adı | ICS çizelgesi 2026/06 (oto); EPA etiket kılavuzu "Percentage application rates should never be used alone" (oto) |
| Bilgisayar | dil etiketi olmayan kod bloğu; Python 2; sürümsüz kod örneği; 99 karakteri aşan Python satırı | python.org "Python 2 is no longer supported" ✓; PEP 8 "79 characters", ekip anlaşmasıyla "up to 99 characters" ✓ |
| Hukuk | yürürlükten kalkmış kanun (818, 1086, 6762, 765, 743, 1412; "(818)" biçimi de) → **UYARI**: "zaman bakımından uygulamayı incele"; aynı cümlede karşılaştırma, geçmiş tarih ya da "mülga" geçiyorsa sayılmaz; numarasız kanun adı; künyesiz mahkeme kararı; kaynaksız alıntı | Kaldırılma: 6098 m. 647, 6100 m. 450, 6102 m. 1533 (Claude açtı). HATA değil, çünkü 6101 sayılı Kanun m. 1'e göre TBK'dan önceki işlemlere kural olarak o zamanki kanun uygulanır ✓ (Sol bulgu 12) |
| İktisat · İşletme | yılsız veri; çözülmüş örnek; kaynak | TÜİK baz yılı; KGK TFRS (oto) |
| Tarih · Coğrafya · Sosyal | kaynağı belirsiz otorite; kaynak yok; yüzyıl yazımı; yılsız veri; harita öğeleri | Wineburg; BBC Bitesize ✓; Time & Spatial |
| İlahiyat | kaynaksız hadis; sure/âyet numarasız meal; kaynaksız alıntı | Türkçe yayınlarda "Bakara, 2/211" düzeni (oto) |
| Edebiyat · Felsefe | kaynaksız doğrudan alıntı (önünde ya da ardında künye yoksa; "> " alıntı bloğu dahil); kaynakça boş; [n] atfının kaynakçada karşılığı yok | Chicago, MLA künye ögeleri (oto) |
| Sanat · Mimarlık | künyesiz eser görseli; ölçeksiz teknik çizim | Getty CDWA çekirdek künye; ISO 128 / ISO 5455 (oto); FSEK 70 yıl (mevzuat.gov.tr, oto) |
| Eğitim bilimleri | kaynağı belirsiz otorite; kaynak yok | — (yalnız genel kurallar) |
| Genel | yalnız ortak çekirdek | — |

✓ = Claude kaynağında ayrıca açtı; (oto) = quoteproof otomatik doğrulaması alıntıyı sayfada buldu.

Tıpta doz yazımı ENGEL'dir, çünkü ISMP bu iki biçimi 10–100 kat doz hatasının kaynağı sayar ve hiç kullanılmamasını
ister. ISMP kuralı reçete içindir; öğrenci notuna uygulandığını ölçen çalışma bulunamadı. Gerekçe: not, öğrencinin yazma
alışkanlığını kurar.

Yeni alan eklemek: `ogretim-alanlari.json`'a anahtar sözcük, kontrol adları (betikteki `KONTROLLER`), elle listesi ve
sınama önerisi yaz; gerekçesini bu tabloya ekle. Kaynağı olmayan alan kuralı yalnız UYARI ya da ELLE olabilir.

## İş akışı

1. Belgeyi oku; hedef dili, seviyeyi ve hedefi (sınav görevi ya da öğrenme hedefi) belirle.
2. Dil sadeleştirmesi de istendiyse Durulaç Temizle'yi yalnız Türkçe açıklamaya uygula (tür: "öğretim materyali");
   istenmediyse metne dokunma.
3. `python3 <beceri kökü>/scripts/ogretim_denetim.py BELGE.md [--pdf BELGE.pdf] [--alan AD] [--yil YYYY] --json`.
   Yalnız PDF geldiyse önce `pdftotext -layout` ile md çıkar. PDF verildiğinde metni de kimlik ve ilaç güvenliği için
   taranır.
4. Kullanıcıya ver: karar, alan ve destek, ölçülen boyut sayısı ve puan tablosu, **bütün ENGEL/HATA bulguları satır
   numarasıyla**, ilk 5 uyarı, elle bekleyen maddeler, alanın elle listesi.
5. **Betik çalışmazsa puan uydurma:** çalışmadığını söyle, elle kontrol listesini uygula, puan verme.

## Karar modeli (v2)

| Karar | Ne zaman | Çıkış kodu |
|---|---|---|
| **yayına engel var** | en az bir ENGEL (hasta güvenliği: doz yazımı, doz/dönüşüm aritmetiği, hasta kimliği, TC no) ya da HATA (biçim: Kiril karışması, uzun Latin sözcükte Yunan harfi, TODO, çok küçük yazı, gerçekten boş sayfa, sayfa tavanı) | 1 |
| **karar için denetim eksik** | engel yok ama elle maddeler boş (`denetim:` ya da `hedef:`) | 3 |
| **tanımlı kapsamda uygun** | engel yok, elle maddeler dolu | 0 |

Dosya/kullanım hatası 2. "Uygun", içeriğin doğru olduğu anlamına gelmez; yalnız denetimin tanımlı kapsamında engel
bulunmadığını söyler. Elle alanların dolu olması da denetimin yapıldığını kanıtlamaz; yazanın beyanıdır (Sol bulgu 1).

**Ölçülmeyen boyut puanlanmaz:** Hedefle uyum (`hedef:` boşsa), Verimlilik (PDF yoksa ya da metin katmanı yoksa),
Okunaklılık (PDF ve görsel yoksa), Kendini sınama (`tur:` sınama istemiyorsa) "ölçülmedi" olur ve paydaya girmez.
Çıktı "X/Y (k/8 boyut ölçüldü)" yazar.

**Konum ve susturma:** her bulgu `kural` kimliği ve bulunabildiyse `satir` taşır; kimlik örnekleri maskelenir.
Yanlış alarm gerekçeyle susturulur: belge düzeyi `<!-- sinac: yoksay KURAL — gerekçe -->`, satır düzeyi aynı satırda
`<!-- sinac: yoksay — gerekçe -->`. Gerekçesiz ya da 10 karakterden kısa gerekçeli susturma UYARI'yı susturur, ENGEL/HATA'yı
susturmaz. Susturulanlar
çıktıda gerekçesiyle listelenir.

## Ölçek — 8 boyut

Puan: **2** temiz · **1** uyarı · **0** hata. **OTO** = betik ölçer; **ELLE** = üreten ajan kontrol eder ve frontmatter'a yazar.

| # | Boyut | Ölçüt | OTO ölçüm ve eşik | ELLE |
|---|---|---|---|---|
| 1 | **Doğruluk** | Dil, çeviri, okunuş doğru; kaynaksız örnek işaretli | Kiril karışması → HATA; Yunan karışması sayısal/fen/sağlık alanlarında sembol sayılır, ötekilerde 4+ harfli Latin sözcükte HATA, kısa sözcükte UYARI; `TODO`/`FIXME`/`???` → HATA; sağlık ENGEL'leri | Bağımsız bir modele denetlet; `denetim: 2026-11-22 sonnet` |
| 2 | **Hedefle uyum** | Belge hangi sınav görevine / öğrenme hedefine hizmet ediyor; gerçek görev tipleri var; kelime sınırı güvenli | — | `hedef:` (ya da `sinav:`) alanı; görev tipleriyle karşılaştır |
| 3 | **Seviye** | Acemide terim yerine sade açıklama; hedef dışı dil yok; sayfada tek yeni kavram | Dil: dil bilgisi terimi > 12, hedef dışı açıklama dili (ör. Fransızca belgede İngilizce) > 8 → UYARI; tıp/diş/fen: 3+ tanımsız kısaltma → UYARI | Sayfada tek yeni kavram |
| 4 | **Ezber ve kavrama** | Kısa cümle, tekrar eden iskelet, tutarlı yazım; dilde okunuş/karşılık yanında | Dil: uzun okunuş > %15, okunuşsuz yabancı metin → UYARI; tarih: yüzyıl yazımı karışık → UYARI | Belgeler arası aynı ifade aynı mı |
| 5 | **Okunaklılık** | Gövde ≥ 11 pt, tablo ≥ 9 pt; boş sayfa yok | PDF kelime kutusu yüksekliğinden punto aralığı (aşağıda): en iyimser tahmin < 7 pt → HATA, en kötümser < 9 pt → UYARI; metinsiz sayfa çizim içermiyorsa (pdftoppm) HATA, doğrulanamıyorsa UYARI; metin katmanı yoksa ölçülmedi | — |
| 6 | **Sıra ve akış** | Harita → seç → kur → uygula → sına; düz başlık numarası; sayfa numarasına gönderme yok | Ek numara (3.5+), aynı numara iki kez, geriye giden numara → UYARI; "s. 6'daki" türü gönderme → UYARI | Mantıksal sıra |
| 7 | **Kendini sınama** | Her konu kapalı kitap sınamayla biter; cevap ayrı; boşluk sayısı cevapla uyumlu | Güçlü işaret ("kendini dene", "bakmadan", "cevap anahtarı", "dilsiz harita") ya da zayıf işaret ("test", "sınav", "alıştırma") + soru izi (?, ___, numaralı madde) yoksa UYARI; "testosteron" sayılmaz | Cevap anahtarı ayrı, boşluklar uyumlu |
| 8 | **Verimlilik** | Sayfa içerikle orantılı; yarım sayfa az; aynı kural tekrar anlatılmıyor | `sayfa_tavan` aşıldı → HATA; tavan yoksa 16+ sayfa → UYARI; %40'tan az dolu sayfa oranı > %20 → UYARI (son sayfa sayılmaz) | Aynı kural iki kez anlatılmış mı |

Eşikler `scripts/ogretim_denetim.py` başında sabittir; değişiklik bu tabloyla birlikte yapılır.

### Eşiklerin gerekçesi ve sınırı

- PDF'teki ölçüm **kelime kutusu yüksekliğinin ortancasıdır**, punto değildir. Kendi ürettiğimiz PDF'lerde (poppler
  `pdftotext -bbox`) kutu/punto oranı yazı tipine göre değişti: Helvetica 0,925 · Times 0,900 · Courier 0,786. Betik bu
  yüzden bir **punto aralığı** hesaplar (kutu ÷ 0,925 … kutu ÷ 0,786). HATA ancak en iyimser tahmin bile 7 pt'nin
  altındaysa; UYARI en kötümser tahmin 9 pt'nin altındaysa. Önceki sürümdeki "kutu < 8 pt → HATA" kuralı Helvetica
  8,5 pt'yi bile hata sayıyordu (Sol bulgu 15); kaldırıldı. Testler: `scripts/test_ozellikler.py` `GercekPdf`.
- Yarım sayfa tek başına hata değildir: ünite sonu bilerek boş bırakılabilir. Oran %20'yi aşarsa düzen sorunudur.
- Otomatik denetim **doğruluğu kanıtlamaz**; yalnız ölçülebilen kusurları yakalar.

## Dayanak ilkeleri

| İlke | Ne söylüyor | Belgeye etkisi | Kaynak |
|---|---|---|---|
| **Bilişsel yük** (Sweller) | Bölünmüş dikkat ve gereksizlik öğrenmeyi düşürür; acemiye önce çözülmüş örnek; **uzman ters etkisi**: acemiye yarayan tam destek ileri öğrencide yük olur | Örnek kuralın yanında; aynı kural iki kez anlatılmaz; "çözülmüş → yarım çözümlü → çözümsüz"; acemiye tam destek, seviye yükseldikçe azalt | Chandler & Sweller 1992; Sweller, van Merriënboer & Paas 2019 (Educ. Psychol. Rev. 31) |
| **Mayer çoklu ortam** | Tutarlılık, işaretleme, mekânsal bitişiklik, bölümleme. Etkiler Mayer derlemelerinde orta-büyük, bağımsız meta-analizlerde daha küçük: **yönü tutarlı, büyüklüğü koşullu** | Süs yok; vurgu az ve anlamlı; açıklama ilgili yerin yanında; bölümler kısa | Mayer 2021 (Multimedia Learning); Rey ve ark. 2019 (bölümleme meta-analizi) |
| **Etkili teknikler** (Dunlosky 2013) | On teknikten yalnız **kendini sınama** ve **aralıklı tekrar** yüksek fayda; yeniden okuma ve vurgulama düşük *(elle doğrulandı)* | Her konu kapalı kitap sınamayla biter; tekrar günlere yayılır; "tekrar oku" çalışma sayılmaz | Dunlosky ve ark. 2013 (Psychol. Sci. Public Interest 14/1) |
| **Kelime** (Nation) | Kelimeyi bilmek = biçim–anlam–kullanım; seçim sıklığa göre; başlangıçta ana dil karşılığı en etkili anlam yolu | Kelime cümle/kalıp içinde; her yabancı ögenin yanında ana dil karşılığı ve okunuşu | Nation 2001/2013 (Learning Vocabulary in Another Language) |
| **Kalıp** (Lewis; Boers) | Kalıplar tek parça öğrenilir ve üretim turunda pekişir | Selamlaşma/tanıtma gibi kalıplar bütün verilir; her kalıba en az bir üretim turu | Lewis 1993; Boers & Lindstromberg 2012 |
| **İkili kodlama** (Paivio) | Görsel somut kelimede ek bellek katmanı verir; çevirinin yerini tutmaz | Görsel yalnız somut kelimede; süs görsel yok | Clark & Paivio 1991 |
| **Sınav ızgarası** *(örnek: DELF A1 / CEFR A1)* | Yazma: form (10 puan) + en az **40 kelimelik** mesaj (15 puan; 5 ölçüt). **19 kelime ve altı = 0 puan** *(elle doğrulandı)* | Sınav belgesinde görev tipleri, kelime sayısı ve hitap/veda kuralı açık; metin sınırın güvenle üstünde | FEI DELF A1 Grille PE; CEFR Companion Volume 2020 |
| **Okunabilirlik** | Kılavuzlar en küçük okunur gövde boyunda 12 pt basılıda birleşiyor; tabloda 8 pt altı "çok küçük" | Tablet PDF'inde gövde ≥ 11 pt, tablo ≥ 9 pt; 8 pt altı yayın yok; tablo sade | Australian Government Style Manual — Tables; RNIB/WCAG özetleri |

### Doğrulanamadı — kurala ALINMADI

- Alan araştırması (22.11.2026; quoteproof, 6 başlık, 67 bağımsız kaynak, 249 bulgu, 151 otomatik doğrulandı; kanıt
  özeti `docs/kanitlar.md`): ICA harita tasarımı belgesi (başlıkta yıl, lejant eksiksizliği), Rohrer 2020
  karışık alıştırma denemesi (%61 / %38), Shekelle 2001 kılavuz eskime süresi (5,8 yıl) ve Joint Commission yasaklı
  kısaltma sayfası kaynağında açılamadı. Bunlara dayanan kural yok; harita ve kılavuz kuralları doğrulanan başka
  kaynaklara (BBC, Time & Spatial, NHMRC, ISMP) dayanır. Karışık alıştırma yalnız ELLE maddedir.
- Bilim dalları genişletmesinde açılamayan ya da doğrulanamayanlar: PSNet "mg/kg/d" vakası (403), JNC 7'nin yerini
  alan kılavuz (kural çıkarıldı), KVKK karar sayfaları (kural HIPAA/BMJ/ICMJE ve yönetmeliğe dayandı), 765, 743 ve
  1412 sayılı kanunların kaldırılma hükmü (yürürlük kanunlarının metni açılamadı → yalnız UYARI), Madrid Kodu sayfası
  (yalnız ELLE madde), ISMP 2024'te artık bulunmayan HS, BT, x3d (kuraldan çıkarıldı).
- Tall Man harf yazımı (benzer ilaç adları) için kanıt çelişkili (ISMP); kural yapılmadı. Tıp öğrencisinin Anki
  kullanımı için kanıt kesinliği "çok düşük"; ölçek yalnız genel kendini sınama ilkesini kullanır.
- Satır uzunluğu 45–90 karakter ve satır aralığı puntonun 1,2–1,45 katı önerileri kaynağında doğrulanamadı.
- Satır aralığının okuma başarısını değil yalnız tercihi etkilediği bulgusu tek kaynaklı.

Bu değerler öneri olarak anılabilir ama betik eşiği ya da HATA/UYARI gerekçesi yapılmaz.

## Elle kontrol listesi — yayından önce

- [ ] **Doğruluk:** içerik bağımsız bir modele ya da uzmana okutuldu (kimlik içeren belgede yalnız kimlik çıkarıldıktan
      sonra ya da yerel modelle); frontmatter `denetim: TARİH MODEL` (tarih zorunlu; "yok/henüz" reddedilir).
      `denetim:` boşsa Doğruluk en çok 1 puan alır
- [ ] **Hedef:** hangi sınav görevine / öğrenme hedefine hizmet ettiği frontmatter'da: `hedef:` (ya da `sinav:`);
      gerçek görev tipleri ve kelime sınırı var (örnek: DELF A1 mesajı ≥ 40 kelime, güvenli hedef 60+)
- [ ] **Çözülmüş örnek önce:** kural → çözülmüş örnek → yarım çözümlü → kendin yap
- [ ] **Kendini sınama:** konu sonunda kapalı kitap bölümü; cevaplar ayrı yerde; boşluk sayısı cevapla uyumlu
- [ ] **Aralıklı tekrar:** belge ya da program konuya günler sonra dönüşü söylüyor
- [ ] **Tekrar yok:** aynı kural iki yerde anlatılmıyor
- [ ] **Ortak dil:** aşağıdaki şablon kullanıldı

## Ortak dil şablonu — bütün belgelerde aynı

| Öğe | Standart |
|---|---|
| Cümle şeması | **KİM** (mavi) · **FİİL** (kırmızı) · **GERİSİ** (yeşil); renk her belgede aynı anlama gelir |
| Üç sütun | **Yabancı · Okunuş · Türkçe** (ezber tablosu); Türkçe sütunu kapatılıp kendini sınamaya uygun |
| Okunuş | Türkçe harfle, eğik çizgi arasında: `/jö mapel/` *(örnek, Fransızca)*; IPA yalnız Türkçede olmayan ses için |
| Kutular | 🪤 tuzak · 💡 püf nokta · ✍️ yazma / kaynağı yazara ait · 🎤 konuşma · ❓ soru · ✅ kendini dene |
| Başlık numarası | Düz: 1, 1.1, 1.2, 2 …; ek numara (3.5+) yok; araya bölüm girerse yeniden numarala |
| Gönderme | Sayfa numarası değil bölüm numarası/adı ("3.2'deki tablo") |
| Dosya adı | `NN-Ad.pdf`; `-v2`, `-eski`, tarih eki yok; yeni sürüm aynı adın üzerine |
| Frontmatter | `tur:` · `baslik:` · isteğe bağlı `sayfa_tavan:` · `not_sayfasi:` · `denetim:` · `hedef:`/`sinav:` |

`alan:` (genel, dil, tip, dis, hemsirelik, eczacilik, veteriner, beslenme, fizyoterapi, acil, psikoloji, matematik,
istatistik, fen, fizik, kimya, biyoloji, yer_bilimleri, ziraat, bilgisayar, muhendislik, mimarlik, hukuk, iktisat, tarih,
cografya, sosyal, ilahiyat, edebiyat, felsefe, sanat, egitim) ve `bicim:` (gorsel, sozel) tespiti geçer;
`dil:` yabancı dil alanında öğretilen dili verir.

`tur:` değerleri betikte kullanılır: `konu-anlatimi`, `rehber`, `pano`, `ders-notu` (ya da boş) kendini sınama bölümü ister;
`indeks`, `yonetim` okunuş aramaz; `kilavuz` sayfa göndermesine izinlidir.

## `--duzelt` neyi yapar, neyi yapmaz

Önce `BELGE.md.bak` yedeği alır. Kod bloğu, satır içi kod, `$…$` formül ve frontmatter'a dokunmaz.
1. Latin harfle karışık yazılmış sözcükte Kiril benzer harf (`е а о р с …`) → Latin karşılığı.
2. Yunan benzer harf yalnız sayısal/fen/sağlık dışı alanda, en az 4 harfli ve çoğunluğu Latin olan sözcükte → Latin
   (Δt, ρgV, 2πr, α = 30° korunur; Sol bulgu 16, Qwen K3).
3. `html`/`body` font-size 8,5 pt altı → 9 pt (sayfa düzeni değişebilir; PDF'e bak).

Ötekiler bulgu satırındaki öneriyle ELLE düzeltilir. PDF yeniden üretilmelidir; betik PDF üretmez.

## Açık işler (otomatikleştirilemeyen)

- **Altın küme:** bağımsız öğretmen ve alan uzmanlarının etiketlediği gerçek ders notları (şu anki regresyon kümesi
  iki modelin karşı örnekleridir; gerçek öğretmen etiketi değildir). Kontrol başına kesinlik/duyarlılık buna bağlı.
- **Ölçme geçerliği:** 8 boyutun ve toplam puanın gerçekten öğretim kalitesini ayırt ettiği, öğretmen değerlendirmesi
  ve öğrenci öğrenme sonuçlarıyla sınanmadı. Toplam puan bu yüzden ağırlıksız ve yalnız gösterge.
- **Tablo bağlamı:** analit adı başlık satırında, birimi alt satırda olan lab tablolarında ilişki kurulamıyor.
- **Gerçek yazı tipi boyutu:** gömülü yazı tiplerinde punto aralığı Helvetica/Times/Courier kalibrasyonuna dayanır.
