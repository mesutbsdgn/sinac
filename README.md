# Öğretim Denetçisi (ogretim-denetci)

Ders notunu, konu anlatımını, rehberi ve öğrenci PDF'ini kanıta dayalı bir ölçekle denetleyen Claude becerisi (skill).
Belgenin **bilim dalını** ve **görsel/sözel biçimini** kendisi tanır; tıp notunu dil öğrenme ölçeğiyle, görsel bir
anatomi atlasını düz metin ölçeğiyle değerlendirmez. Sonunda "yayınlanabilir mi" kararı verir.

Dil sadeleştirmez; o iş kardeş becerisi [Durulaç](https://github.com/mesutbsdgn/turkce-ai-durulac)'ındır. İkisi
birlikte kuruluysa önce Durulaç Türkçe açıklamayı sadeleştirir, sonra denetçi ölçer.

## Ölçek

8 boyut, her biri 0 (hata) · 1 (uyarı) · 2 (temiz); toplam /16. Otomatik denetimde **HATA** varsa belge yayınlanamaz.

| Boyut | Örnek otomatik kontrol |
|---|---|
| Doğruluk | yabancı alfabe harfi karışması, TODO, geçerli TC kimlik no, doz yazımı, mülga kanun |
| Hedefle uyum | elle (frontmatter `hedef:`) |
| Seviye | tanımsız kısaltma, dil bilgisi terimi yoğunluğu |
| Ezber ve kavrama | uzun cümle, okunuşsuz yabancı metin, yüzyıl yazımı karışıklığı |
| Okunaklılık | PDF'te yazı boyu (8 pt altı hata), boş sayfa, alt metinsiz görsel, harita öğeleri |
| Sıra ve akış | başlık numarası, sayfa göndermesi, çözülmüş örnek |
| Kendini sınama | test bölümü, cevapsız alıştırma |
| Verimlilik | sayfa tavanı, yarım sayfa oranı |

## 32 alan

| Grup | Alanlar |
|---|---|
| Sağlık (en ayrıntılı) | tıp; diş hekimliği, hemşirelik ve ebelik, eczacılık, veteriner, beslenme, fizyoterapi, acil tıp; psikoloji |
| Sayısal ve fen | matematik, istatistik, fen, fizik, kimya, biyoloji, yer bilimleri, ziraat, mühendislik, bilgisayar, mimarlık |
| Sosyal ve beşerî | hukuk, iktisat ve işletme, tarih, coğrafya, sosyal bilgiler, ilahiyat, edebiyat, felsefe, sanat ve müzik, eğitim |
| Dil ve genel | yabancı dil (fr, en, de, es, it), genel |

**Sağlıkta:** "5,0 mg" / ",5 mg" doz yazımı, hasta adı ve protokol numarası yayını durdurur. ISMP'nin karıştırılmaya
açık kısaltmaları, zaman birimi yazılmamış "mg/kg", harfli gebelik kategorisi (FDA 2015'te kaldırdı), dönüşümsüz iki
birim, kaynaksız referans aralığı, yılsız ya da 5 yıldan eski kılavuz, DSM-IV, yanlış yazılmış tür adı uyarı verir.
Her sağlık alanına 10 maddelik elle kontrol listesi eklenir.

## Kullanım

```bash
python3 scripts/ogretim_denetim.py ders-notu.md                    # alanı kendisi bulur
python3 scripts/ogretim_denetim.py not.md --pdf not.pdf --alan tip # PDF ölçümü, alanı zorla
python3 scripts/ogretim_denetim.py not.md --json
```

Claude'da doğal dille: "Bu farmakoloji notumu denetle", "Bu PDF öğretir mi?", "Hukuk ders notum güncel mi?"

## Kurulum

```bash
git clone <depo-adresi> ~/.claude/skills/ogretim-denetci
```

Python 3.9+, yalnız standart kütüphane. PDF ölçümü için isteğe bağlı poppler (`pdftotext`, `pdfimages`).

## Kanıt

Üç quoteproof araştırması (23 başlık, 872 bulgu, 567'si kaynağında otomatik doğrulandı); kurala giren kritik bilgiler
(ISMP, FDA, NHMRC, mevzuat.gov.tr, PEP 8, Merck Veterinary Manual…) ayrıca elle açıldı. Kaynağı açılamayan bilgi HATA
kuralı yapılmadı. Ayrıntı: [`docs/kanitlar.md`](docs/kanitlar.md), ölçek: [`references/ogretim.md`](references/ogretim.md).

## Sınırları

- Yazımı ve yapıyı denetler; dozun, tanının, kanun yorumunun ya da tarihsel bilginin doğru olduğunu kanıtlamaz.
- Tıbbi, eczacılık, veteriner ya da hukuki görüş değildir.
- Alan tahmini karma belgede yanılabilir; `alan:` ya da `--alan` ile düzeltilir.

## Sürüm geçmişi

| Sürüm | Tarih | Değişiklik |
|---|---|---|
| v1.0.0 | 22 Kas 2026 | Durulaç'ın `+ogretim` kipinden (v1.7–1.9) ayrı beceri olarak çıkarıldı |

## Lisans

Kullanım hakkı lisansı: [LICENSE](LICENSE). Telif © 2026 mesutbsdgn.
