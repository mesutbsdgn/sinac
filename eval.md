# Öğretim Denetçisi — son okuma

Raporu teslim etmeden önce her maddeye evet/hayır de; hayırsa düzelt.


- Tür kapısına baktım mı; belge gerçekten öğretim materyali mi (hukuk, edebî, sohbet, resmî yazıda kapalı)?
- Betiğin tespit ettiği alanı ve güveni söyledim mi; güven düşükse ya da alan yanlışsa kullanıcıya sordum ya da `alan:` ile düzelttim mi? Dil profilinin kurallarını (okunuş, hedef dışı dil) dil dışı bir belgeye uygulamadım mı?
- Tıp ve diş notunda ilaç adı, doz, birim ve diş numarasını Temizle sırasında değiştirmedim mi; doz HATA'sını kendim düzeltmek yerine kullanıcıya gösterdim mi?
- Sağlık alanında (tıp, hemşirelik, eczacılık, veteriner, beslenme, fizyoterapi, acil, diş) betiğin 'yayınlanamaz' dediği doz, hasta kimliği ya da TC kimlik bulgusunu yumuşatmadan ilettim mi? Betiğin dozun klinik doğruluğunu denetlemediğini ve doz/endikasyonun güncel kaynakla elle karşılaştırılması gerektiğini söyledim mi?
- Alanın elle listesini (sağlıkta 10 ortak madde + alan maddeleri) kullanıcıya verdim mi; doldurulmamış maddeyi 'tamam' saymadım mı?
- Hukuk notunda mülga kanun uyarısını, eski kanun bilerek karşılaştırılıyorsa gereksiz yere tekrar etmedim mi?
- Temizle'yi yalnız Türkçe açıklamaya uyguladım mı; yabancı örnek cümleye, okunuşa (`/…/`), tabloya, kutu simgesine ve kasıtlı tekrar eden iskelete dokunmadım mı?
- `ogretim_denetim.py` gerçekten çalıştı mı; tablodaki puanlar ve bulgular betik çıktısından mı geliyor (çalışmadıysa puan vermedim, bunu söyledim mi)?
- PDF ölçülmediyse okunaklılık ve verimliliği "ölçülmedi" diye mi bildirdim, 2 puan saymadım mı?
- HATA varsa kararı "yayınlanamaz" diye mi verdim; UYARI'ları düzeltme listesine koydum mu?
- `--duzelt` dışında kendi düzeltmemi anlam değiştirmeden ve bulgu satırındaki öneriye göre mi yaptım; PDF'in yeniden üretilmesi gerektiğini söyledim mi?
- Doğruluk ve hedef uyumu ELLE maddelerini (frontmatter `denetim:`, `hedef:`/`sinav:`) boşsa açıkça bekleyen diye mi gösterdim; otomatik puanı "doğru" kanıtı gibi sunmadım mı?
- Kaynağında doğrulanmamış bir eşiği (satır uzunluğu, satır aralığı) kural gibi önermedim mi?
