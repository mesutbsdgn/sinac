---
hedef: Öğrenci Python 3.10'da for ve while döngüsüyle toplam hesaplayan kısa program yazar
denetim: 2026-11-20 Dr. Öğr. Üyesi Kaan Yıldırım (uzman)
---

# Python: döngüler

## 1. Ortam

Bu not Python 3.10 için yazılmıştır. Sürüm 2.0 değil, 3.10 ya da üstü kullanın.

## 2. for döngüsü

```python
toplam = 0
for sayi in range(1, 6):
    toplam += sayi
print(toplam)  # 15
```

## 3. while döngüsü

```python
voltaj = 5.0
adim = 0
while voltaj > 1.0:
    voltaj = voltaj - 1.0
    adim += 1
print(adim)  # 4
```

## 4. match-case örneği

Python 3.10 ile eklenen `match` ifadesi çok dallı seçimi okunur kılar.

## 5. Sık hatalar

- `range(1, 6)` altı dahil değildir; son değer 5'tir.
- `while` içinde değişkeni güncellemeyi unutmak sonsuz döngüye yol açar.

## 6. Kendini sına

1. 1'den 10'a kadar çiftlerin toplamını yazan bir döngü kur.
2. Yukarıdaki while kodu kaç kez döner?
