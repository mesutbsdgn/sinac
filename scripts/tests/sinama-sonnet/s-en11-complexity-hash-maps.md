---
hedef: Compare the time and space complexity of common algorithms and explain how a hash map handles collisions and resizing.
denetim: 2026-11-21 Ignatius Calloway (uzman)
---

# Data Structures: Complexity and Hash Maps

## 1. Big-O in one table

| Operation | Time (typical) | Notes |
|---|---|---|
| Array index access | O(1) | Direct address calculation |
| Linear search | O(n) | One pass |
| Binary search (sorted) | O(log n) | At most 20 steps for 1,000,000 items |
| Hash map lookup | O(1) average | O(n) in the worst case |
| Quick sort | O(n log n) average | O(n²) worst case |
| Merge sort | O(n log n) | Always |

## 2. Space complexity of the algorithms (to be completed)

- TODO: add the amortized-analysis proof for dynamic arrays
- Dynamic array append is O(1) amortized because capacity doubles when it fills.

| Structure | Extra space for n items |
|---|---|
| Linked list | O(n) |
| Hash map | O(n) |
| Merge sort | ??? |

## 3. Hash map basics

A hash map stores key–value pairs. A **hash function** turns the key into an integer, and that integer, taken modulo the table size, selects a bucket.

```python
class SimpleMap:
    MAX_LOAD = .75

    def __init__(self):
        self.buckets = [[] for _ in range(8)]
        self.size = 0

    def _index(self, key):
        return hash(key) % len(self.buckets)

    def put(self, key, value):
        bucket = self.buckets[self._index(key)]
        for pair in bucket:
            if pair[0] == key:
                pair[1] = value
                return
        bucket.append([key, value])
        self.size += 1
        if self.size / len(self.buckets) > self.MAX_LOAD:
            self._grow()

    def _grow(self):
        old = self.buckets
        self.buckets = [[] for _ in range(len(old) * 2)]
        self.size = 0
        for bucket in old:
            for key, value in bucket:
                self.put(key, value)

    def get(self, key, default=None, timeout=5.0):
        for k, v in self.buckets[self._index(key)]:
            if k == key:
                return v
        return default
```

The `timeout` argument is unused here; it only shows that a default of `5.0` is written with a leading digit.

## 4. Collisions and the load factor

- Two keys can land in the same bucket (a collision). This implementation uses **chaining**: each bucket is a list.
- The load factor is items ÷ buckets. Java's `HashMap` resizes at 0.75; Python's dictionary uses a different open-addressing scheme and resizes earlier.
- Doubling the table spreads items again (rehashing), which costs O(n) once but keeps the average lookup O(1).

## 5. Worked example

Table size 8, load limit 0.75. After the sixth key the load is 6 ÷ 8 = 0.75, not above the limit. The seventh key makes it 0.875, so the table grows to 16 buckets.

## Self-test

1. Why is hash-map lookup O(1) only on average?
2. How many comparisons does binary search need on 1,000,000 sorted items at most?
3. After how many inserts does an 8-bucket table with limit 0.75 resize?
4. What is the difference between chaining and open addressing?
