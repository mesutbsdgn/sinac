---
hedef: Students explain software version numbers and choose float or integer types in Python 3.10
denetim: 2026-11-20 Dr. Alan Brooks (uzman)
---

# Version numbers and number types

## 1. Versions

Version 2.0 of a library is not the same as version 2.10. The last part is a number, not a decimal fraction.

Python 3.10 is newer than Python 3.9.

## 2. Integers and floats

```python
count = 5
voltage = 5.0
ratio = count / 2
print(type(count), type(voltage), ratio)
```

`5` is an integer and `5.0` is a floating-point number. Division with `/` returns a float.

## 3. Rounding

```python
print(round(2.675, 2))
```

Floating-point storage can make the output differ from what you expect by hand.

## 4. Self-check

1. Which is newer: version 1.9 or version 1.10?
2. What does `7 // 2` return?
