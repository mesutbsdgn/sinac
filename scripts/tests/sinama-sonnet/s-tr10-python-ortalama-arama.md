---
hedef: Python'da ortalama hesabı, ikili arama ve kayan noktalı sayı yuvarlama davranışını doğru uygulamak.
denetim:
---

# Python ile Temel Algoritmalar: Ortalama, İkili Arama, Kayan Nokta

Bu hafta üç küçük konu var: bir listenin ortalaması, sıralı dizide ikili arama ve ondalık sayıların bilgisayardaki davranışı.

## 1. Ortalama

```python
def ortalama(liste):
    if not liste:
        raise ValueError("liste boş olamaz")
    return sum(liste) / len(liste)

print(ortalama([4, 8, 15, 16, 23, 42]))   # 18.0
```

`/` işlemi Python 3'te her zaman `float` döndürür; tam bölme için `//` kullanılır.

## 2. İkili arama

Dizi **sıralı** olmalıdır. Her adımda arama aralığı yarıya iner.

```python
def ikili_arama(dizi, hedef):
    sol, sag = 0, len(dizi) - 1
    while sol <= sag:
        orta = (sol + sag) // 2
        if dizi[orta] == hedef:
            return orta
        if dizi[orta] < hedef:
            sol = orta + 1
        else:
            sag = orta - 1
    return -1

sayilar = [2, 5, 8, 12, 16, 23, 38, 56, 72, 91]
print(ikili_arama(sayilar, 23))   # 5
print(ikili_arama(sayilar, 7))    # -1
```

| Dizi uzunluğu | En çok karşılaştırma |
|---|---|
| 10 | 4 |
| 1.000 | 10 |
| 1.000.000 | 20 |

Doğrusal arama aynı işi ortalama n/2 adımda yapar; ikili aramanın maliyeti O(log n)'dir.

## 3. Kayan noktalı sayılar

Bilgisayar ondalık sayıları ikilik tabanda saklar; bazı değerler tam yazılamaz.

```python
print(0.1 + 0.2 == 0.3)          # False
print(abs((0.1 + 0.2) - 0.3) < 1e-9)   # True
print(round(2.5), round(3.5))    # 2 4  (yarıya en yakın çifte yuvarlama)
```

Eşitlik yerine **tolerans** karşılaştırması yapılır.

### Örnek: ağırlıklı ortalama

```python
agirlik = .5
vize, final = 70, 90
esik = .75
sonuc = agirlik * vize + (1 - agirlik) * final
print(sonuc, sonuc >= 60)   # 80.0 True
```

Burada `agirlik` ve `esik` değerleri yarım ve üçte dört anlamına gelir; Python bu yazımı kabul eder ama okunabilirlik için `0.5` yazmak daha iyi bir alışkanlıktır.

## 4. Sık hatalar

- Boş listede `sum(liste) / len(liste)` yapıp sıfıra bölmek.
- Sıralanmamış dizide ikili arama çalıştırmak.
- `orta = (sol + sag) / 2` yazıp ondalıklı indeks elde etmek; doğrusu `//`.
- Para hesabında `float` kullanmak; bunun için `decimal` modülü tercih edilir.

## Kendini sına

1. `ikili_arama` hangi koşulda -1 döndürür?
2. 1.000.000 elemanlı sıralı dizide en çok kaç karşılaştırma gerekir?
3. `0.1 + 0.2 == 0.3` neden `False` verir?
4. Boş liste için `ortalama` fonksiyonu nasıl davranır?
