# Öğretim Denetçisi — bu depoda çalışan ajanlar için kurallar

- Betik yalnız Python standart kütüphanesiyle çalışır (≥ 3.9); ağ ve dış paket eklenmez. PDF ölçümü isteğe bağlıdır.
- Kaynağı doğrulanmamış kural en çok UYARI ya da elle madde olur, HATA olamaz. Sağlıktaki HATA kuralları (doz yazımı,
  hasta kimliği, TC kimlik no) yalnız birincil kaynakla (ISMP, FDA, yönetmelik) değiştirilir.
- Betik dozun klinik doğruluğunu denetlemez; bunu iddia eden metin yazma.
- Kişisel veri, gerçek hasta bilgisi, yerel yol ya da sunucu adı depoya girmez.

## Test

```bash
python3 -B scripts/test_ogretim_denetim.py
```

Yeni kontrol için olumlu ve olumsuz test yaz; testi kasten bozup kırmızıya döndüğünü gör, geri al.

## Yeni alan

1. `references/ogretim-alanlari.json`: `ad`, `sozcukler` (4 harf ve kısası yalnız tam sözcük eşleşir; "plan", "baz",
   "tür" gibi genel sözcük koyma), isteğe bağlı `ust`, `kontroller` (`@saglik`, `@fen`, `@kaynak`, `@sayisal`), `elle`,
   `sinama_oneri`.
2. Gerekirse `scripts/ogretim_denetim.py` içinde `k_…` işlevi + `KONTROLLER` kaydı; eşik dosya başında sabit.
3. `references/ogretim.md` tablosuna satır ve dayanak; kanıt `docs/kanitlar.md`'ye.
4. Test: `ALAN_ORNEKLERI` tespit örneği + kontrol testi.
