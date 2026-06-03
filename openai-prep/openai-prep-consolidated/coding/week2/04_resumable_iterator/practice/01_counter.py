"""
Bare-minimum custom iterator.

GOAL: Counter(n) yields 0, 1, 2, ..., n-1, then raises StopIteration.

You're proving you can write `__iter__` + `__next__` from memory. This is the
smallest possible iterator — everything else in this folder builds on it.

When working, expect output:
  list:  [0, 1, 2, 3, 4]
  manual: 0
  manual: 1
  manual: 2
  exhausted as expected
  reset: 0
  reset: 1

Three rules to get right:
  1. __iter__ returns self (this iterator IS the iterator)
  2. __next__ either returns the next item OR raises StopIteration
  3. Returning None on exhaustion is a BUG — the protocol is "raise to signal"
"""


class Counter:
    def __init__(self, n: int) -> None:
        self.i = 0
        self.n = n

    def __iter__(self):
        return self

    def __next__(self) -> int:
        if self. i == self.n :
            raise StopIteration
        num = self.i
        self.i += 1
        return num

    def reset(self)->None:
        self.i = 0





def main() -> None:
    # Used by `for` loops and `list()`
    print("list: ", list(Counter(5)))

    # Used by `next(...)`
    it = Counter(3)
    print("manual:", next(it))
    print("manual:", next(it))
    print("manual:", next(it))
    try:
        next(it)
    except StopIteration:
        print("exhausted as expected")

    # Verify reset works (will fail until you implement reset)
    it = Counter(3)
    next(it); next(it)
    it.reset()
    print("reset:", next(it))
    print("reset:", next(it))


if __name__ == "__main__":
    main()
