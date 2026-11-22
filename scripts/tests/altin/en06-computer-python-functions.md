---
hedef: Students write a small Python function with a parameter and a return value
denetim: 2026-11-20 Dr. Alan Brooks (uzman)
---

# Python functions

## 1. Environment

This note uses Python 3.10. Check your version with `python --version`.

## 2. Defining a function

```python
def square(x):
    return x * x

print(square(4))  # 16
```

## 3. Parameters and return values

Each function receives one pаrameter and returns a value.

Parameters are names in the definition; arguments are the actual values passed in the call.

## 4. Default values

```python
def greet(name="world"):
    return "hello " + name
```

## 5. Common mistakes

- Forgetting `return` makes the function give back `None`.
- Using a mutable default such as an empty list can cause surprising shared state.

## 6. Self-check

1. Write a function that adds two numbers.
2. What does a function return if it has no return statement?
