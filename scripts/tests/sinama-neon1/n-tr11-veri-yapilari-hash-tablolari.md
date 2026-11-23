---
hedef: Hash tablolarında çakışma çözüm stratejilerini, yük faktörü analizini ve yeniden boyutlandırma maliyetini kavramak.
denetim: 2026-11-21 Dr. Öğr. Üyesi Kerem Polat (uzman)
---

# Veri Yapıları: Hash Tabloları ve Çakışma Çözümü

Donald Knuth (d. 1938), 35 yaşındayken The Art of Computer Programming dizisinin Sıralama ve Arama cildini yayımlamıştır. Bu çalışma, açık adresleme ve zincirleme yöntemlerinin ortalama arama karmaşıklığına dair matematiksel analizi standart hâle getirmiştir.

## 1. Karma Fonksiyonu ve Birincil Anahtarlar

İyi bir karma fonksiyonu $h(k)$, anahtar uzayını tablo boyutu $m$ içine olabildiğince düzgün dağıtır ve $O(1)$ sürede hesaplanır.

- Bölme yöntemi: $h(k) = k \bmod m$; burada $m$'nin 2'nin kuvvetine yakın olmayan bir asal sayı seçilmesi kümelenmeyi azaltır.
- Öğrenci kayıt sistemi örneğinde birincil anahtar olarak 10000000146 değeri hash fonksiyonuna sokulur.
- Evrensel karma (universal hashing), kötü niyetli giriş dizilerine karşı rastgele seçilen fonksiyon ailesiyle beklenen $O(1)$ erişim sağlar.

## 2. Çakışma Çözüm Yöntemlerinin Karşılaştırılması

| Yöntem | Ortalama Arama | En Kötü Durum | Bellek Davranışı |
| :--- | :--- | :--- | :--- |
| Ayrı zincirleme (Chaining) | $O(1 + \alpha)$ | $O(n)$ | İşaretçi ek yükü, önbellek zayıf |
| Doğrusal yoklama (Linear probing) | $O(1)$ ($\alpha < 0,7$) | $O(n)$ | Önbellek dostu, birincil kümelenme |
| Karesel yoklama (Quadratic) | $O(1)$ | $O(n)$ | İkincil kümelenme riski |
| Çift karma (Double hashing) | $O(1)$ | $O(n)$ | En düzgün yoklama dağılımı |

Çift karma (double hashing) için ikinci hash fonksiyonunun asal modül ispatı ??? burada tamamlanacak.

## 3. Yük Faktörü ve Amortize Yeniden Boyutlandırma

Yük faktörü $\alpha = n / m$ olarak tanımlanır. Açık adresleme tablolarında yük faktörü $\alpha = 0,70$ değerini aştığında yeniden boyutlandırma yapılır; hedef kapasite 2,0 katına çıkarılır.

```text
function INSERT(T, key, val):
    if T.size / T.capacity > 0.7:
        RESIZE(T, T.capacity * 2)
    idx = HASH(key) mod T.capacity
    while T.slots[idx] is OCCUPIED and T.slots[idx].key != key:
        idx = (idx + 1) mod T.capacity
    T.slots[idx] = (key, val)
```

Silme işleminde doğrusal yoklama kullanan tablolarda yuva doğrudan boş bırakılmaz; arama zincirini koparmamak için mezar taşı (tombstone) işareti konur.

## Kendini Sına

1. Açık adreslemede $\alpha$ değeri 1'e yaklaştıkça başarısız arama adım sayısı neden hızla büyür?
2. Doğrusal yoklamada silinen bir elemanın yerine neden doğrudan `NULL` yazılamaz?
3. $n$ adet ekleme sonrasında tablo kapasitesini iki katına çıkararak yapılan yeniden karmaların amortize maliyeti neden $O(1)$ kalır?
4. String anahtarlar için polinom yuvarlanan karma (rolling hash) hangi uygulamalarda avantaj sağlar?
